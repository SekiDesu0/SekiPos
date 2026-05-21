import os
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from core.db import get_db_connection
from core.utils import download_image
from core.events import socketio

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/inventory')
@login_required
def inventory():
    with get_db_connection() as conn:
        products = conn.execute('SELECT * FROM products').fetchall()
    return render_template('inventory.html', active_page='inventory', products=products, user=current_user)

@inventory_bp.route("/upsert", methods=["POST"])
@login_required
def upsert():
    d = request.form
    barcode = d['barcode']
    
    price_str = d.get('price', '0')
    stock_str = d.get('stock', '0')
    
    try:
        price = float(price_str) if price_str else 0.0
        stock = float(stock_str) if stock_str else 0.0
    except (ValueError, TypeError):
        price = 0.0
        stock = 0.0

    name = d.get('name', '')
    image_url = d.get('image_url', '')
    unit_type = d.get('unit_type', 'unit')
    
    cache_dir = current_app.config['CACHE_DIR']
    final_image_path = download_image(image_url, barcode, cache_dir)
    
    with get_db_connection() as conn:
        conn.execute('''INSERT INTO products (barcode, name, price, image_url, stock, unit_type) 
                        VALUES (?,?,?,?,?,?)
                        ON CONFLICT(barcode) DO UPDATE SET 
                        name=excluded.name, 
                        price=excluded.price, 
                        image_url=excluded.image_url,
                        stock=excluded.stock,
                        unit_type=excluded.unit_type''',
                     (barcode, name, price, final_image_path, stock, unit_type))
        conn.commit()
    return redirect(url_for('inventory.inventory'))

@inventory_bp.route('/delete/<barcode>', methods=['POST'])
@login_required
def delete(barcode):
    cache_dir = current_app.config['CACHE_DIR']
    
    with get_db_connection() as conn:
        conn.execute('DELETE FROM products WHERE barcode = ?', (barcode,))
        conn.commit()
    
    img_p = os.path.join(cache_dir, f"{barcode}.jpg")
    if os.path.exists(img_p): os.remove(img_p)
    if socketio:
        socketio.emit('product_deleted', {"barcode": barcode})
    return redirect(url_for('inventory.inventory'))

@inventory_bp.route('/bulk_price_update', methods=['POST'])
@login_required
def bulk_price_update():
    data = request.get_json()
    barcodes = data.get('barcodes', [])
    new_price = data.get('new_price')

    if not barcodes or new_price is None:
        return jsonify({"error": "Missing data"}), 400

    try:
        with get_db_connection() as conn:
            params = [(float(new_price), b) for b in barcodes]
            conn.executemany('UPDATE products SET price = ? WHERE barcode = ?', params)
            conn.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Bulk update failed: {e}")
        return jsonify({"error": str(e)}), 500

@inventory_bp.route('/bulk_delete', methods=['POST'])
@login_required
def bulk_delete():
    cache_dir = current_app.config['CACHE_DIR']
    
    data = request.get_json()
    barcodes = data.get('barcodes', [])

    if not barcodes:
        return jsonify({"error": "No barcodes provided"}), 400

    try:
        with get_db_connection() as conn:
            conn.execute(f'DELETE FROM products WHERE barcode IN ({",".join(["?"]*len(barcodes))})', barcodes)
            conn.commit()
        
        for barcode in barcodes:
            img_p = os.path.join(cache_dir, f"{barcode}.jpg")
            if os.path.exists(img_p): 
                os.remove(img_p)
                
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Bulk delete failed: {e}")
        return jsonify({"error": str(e)}), 500