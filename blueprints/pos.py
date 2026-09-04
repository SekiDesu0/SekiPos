import os
import time
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from core.db import get_db_connection, now_local
from core.openfood import fetch_from_openfoodfacts
from core.events import socketio

pos_bp = Blueprint('pos', __name__)

@pos_bp.route('/checkout')
@login_required
def checkout():
    with get_db_connection() as conn:
        products = conn.execute('SELECT barcode, name, price, image_url, stock, unit_type FROM products').fetchall()
    return render_template("checkout.html", active_page='checkout', user=current_user, products=products)

@pos_bp.route('/scan', methods=['GET'])
def scan():
    barcode = request.args.get('content', '').replace('{content}', '')
    if not barcode: 
        return jsonify({"status": "error", "message": "empty barcode"}), 400
    
    with get_db_connection() as conn:
        p = conn.execute('SELECT barcode, name, price, image_url, stock, unit_type FROM products WHERE barcode = ?', (barcode,)).fetchone()
    
    if p:
        barcode_val, name, price, image_path, stock, unit_type = p        
        
        if image_path and image_path.startswith('/static/'):
            clean_path = image_path.split('?')[0].lstrip('/')
            if not os.path.exists(clean_path):
                cache_dir = current_app.config['CACHE_DIR']
                ext_data = fetch_from_openfoodfacts(barcode_val, cache_dir)
                if ext_data and ext_data.get('image'):
                    image_path = ext_data['image']
                    with get_db_connection() as conn:
                        conn.execute('UPDATE products SET image_url = ? WHERE barcode = ?', (image_path, barcode_val))
                        conn.commit()

        product_data = {
            "barcode": barcode_val, 
            "name": name, 
            "price": int(price), 
            "image": image_path,
            "stock": stock,
            "unit_type": unit_type
        }
        
        socketio.emit('new_scan', product_data)
        return jsonify({"status": "ok", "data": product_data}), 200
    
    cache_dir = current_app.config['CACHE_DIR']
    ext = fetch_from_openfoodfacts(barcode, cache_dir)
    if ext:
        external_data = {
            "barcode": barcode, 
            "name": ext['name'], 
            "image": ext['image'],
            "source": "openfoodfacts"
        }
        socketio.emit('scan_error', external_data)
        return jsonify({"status": "not_found", "data": external_data}), 404
    
    socketio.emit('scan_error', {"barcode": barcode})
    return jsonify({"status": "not_found", "data": {"barcode": barcode}}), 404

@pos_bp.route('/api/checkout', methods=['POST'])
@login_required
def process_checkout():
    try:
        data = request.get_json()
        cart = data.get('cart', [])
        payment_method = data.get('payment_method', 'efectivo')
        
        if not cart:
            return jsonify({"error": "Cart is empty"}), 400
            
        total = sum(item.get('subtotal', 0) for item in cart)
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            cur.execute('INSERT INTO sales (date, total, payment_method) VALUES (?, ?, ?)', (now_local(), total, payment_method))
            sale_id = cur.lastrowid
            
            for item in cart:
                cur.execute('''INSERT INTO sale_items (sale_id, barcode, name, price, quantity, subtotal)
                               VALUES (?, ?, ?, ?, ?, ?)''', 
                            (sale_id, item['barcode'], item['name'], item['price'], item['qty'], item['subtotal']))
                
                cur.execute('UPDATE products SET stock = stock - ? WHERE barcode = ?', (item['qty'], item['barcode']))
                
            conn.commit()
            
        return jsonify({"status": "success", "sale_id": sale_id}), 200
        
    except Exception as e:
        print(f"Checkout Error: {e}")
        return jsonify({"error": str(e)}), 500

@pos_bp.route('/api/scale/weight', methods=['POST'])
def update_scale_weight():
    data = request.get_json()
    
    weight_grams = data.get('weight', 0)
    weight_kg = round(weight_grams / 1000, 3)

    socketio.emit('scale_update', {
        "grams": weight_grams,
        "kilograms": weight_kg,
        "timestamp": time.time()
    })
    
    return jsonify({"status": "received"}), 200