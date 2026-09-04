from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from core.db import get_db_connection, now_local
import io
import zipfile
from datetime import datetime
import os

sales_bp = Blueprint('sales', __name__)

@sales_bp.route('/export/db')
@login_required
def export_db():
    db_file = current_app.config['DB_FILE']
    if os.path.exists(db_file):
        return send_file(db_file, as_attachment=True, download_name=f"SekiPOS_Backup_{datetime.now().strftime('%Y%m%d')}.db", mimetype='application/x-sqlite3')
    return "Error: Database file not found", 404

@sales_bp.route('/export/images')
@login_required
def export_images():
    cache_dir = current_app.config['CACHE_DIR']
    if not os.path.exists(cache_dir) or not os.listdir(cache_dir):
        return "No images found to export", 404

    memory_file = io.BytesIO()
    
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(cache_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zf.write(file_path, arcname=file)
    
    memory_file.seek(0)
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f"SekiPOS_Images_{datetime.now().strftime('%Y%m%d')}.zip"
    )

@sales_bp.route('/sales')
@login_required
def sales():
    selected_date = request.args.get('date')
    payment_method = request.args.get('payment_method')
    page = request.args.get('page', 1, type=int)
    per_page = 100

    with get_db_connection() as conn:
        cur = conn.cursor()
        
        target_date = selected_date if selected_date else now_local()[:10]
        
        daily_query = "SELECT SUM(total) FROM sales WHERE date(date) = ?"
        week_query = "SELECT SUM(total) FROM sales WHERE date(date) >= date(?, '-7 days')"
        month_query = "SELECT SUM(total) FROM sales WHERE substr(date, 1, 7) = ?"
        
        daily_params = [target_date]
        week_params = [target_date]
        month_params = [target_date[:7]]
        
        if payment_method:
            daily_query += " AND payment_method = ?"
            week_query += " AND payment_method = ?"
            month_query += " AND payment_method = ?"
            
            daily_params.append(payment_method)
            week_params.append(payment_method)
            month_params.append(payment_method)
        
        stats = {
            "daily": cur.execute(daily_query, tuple(daily_params)).fetchone()[0] or 0,
            "week": cur.execute(week_query, tuple(week_params)).fetchone()[0] or 0,
            "month": cur.execute(month_query, tuple(month_params)).fetchone()[0] or 0
        }
        
        base_query = "FROM sales WHERE 1=1"
        params = []

        if selected_date:
            base_query += " AND date(date) = ?"
            params.append(selected_date)
        if payment_method:
            base_query += " AND payment_method = ?"
            params.append(payment_method)
            
        stats_query = f"SELECT COUNT(*), SUM(total) {base_query}"
        count_res, sum_res = cur.execute(stats_query, tuple(params)).fetchone()
        
        total_count = count_res or 0
        total_sum = sum_res or 0
        total_pages = (total_count + per_page - 1) // per_page
        
        filtered_stats = {
            "total": total_sum,
            "count": total_count
        }

        offset = (page - 1) * per_page
        data_query = f"SELECT id, date, total, payment_method {base_query} ORDER BY date DESC LIMIT ? OFFSET ?"
        
        sales_data = cur.execute(data_query, tuple(params) + (per_page, offset)).fetchall()
        
    return render_template('sales.html', 
                           active_page='sales', 
                           user=current_user, 
                           sales=sales_data, 
                           stats=stats, 
                           filtered_stats=filtered_stats,
                           selected_date=selected_date,
                           selected_payment=payment_method,
                           current_page=page,
                           total_pages=total_pages)

@sales_bp.route('/api/sale/<int:sale_id>')
@login_required
def get_sale_details(sale_id):
    with get_db_connection() as conn:
        items = conn.execute('SELECT barcode, name, price, quantity, subtotal FROM sale_items WHERE sale_id = ?', (sale_id,)).fetchall()
        
    item_list = [{"barcode": i[0], "name": i[1], "price": i[2], "qty": i[3], "subtotal": i[4]} for i in items]
    return jsonify(item_list), 200

@sales_bp.route('/api/sale/<int:sale_id>', methods=['DELETE'])
@login_required
def reverse_sale(sale_id):
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            items = cur.execute('SELECT barcode, quantity FROM sale_items WHERE sale_id = ?', (sale_id,)).fetchall()
            
            for barcode, qty in items:
                cur.execute('UPDATE products SET stock = stock + ? WHERE barcode = ?', (qty, barcode))
                
            cur.execute('DELETE FROM sale_items WHERE sale_id = ?', (sale_id,))
            cur.execute('DELETE FROM sales WHERE id = ?', (sale_id,))
            
            conn.commit()
            
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        print(f"Reverse Sale Error: {e}")
        return jsonify({"error": str(e)}), 500