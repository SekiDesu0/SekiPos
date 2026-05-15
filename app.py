import os
import sys
import sqlite3
import requests
from flask import send_file
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import mimetypes
import time
import uuid
from datetime import datetime
import zipfile
import io
import webview
import threading

# --- PYINSTALLER WINDOWED MODE FIX ---
# If running as a compiled exe, redirect stdout/stderr so Flask doesn't crash
if getattr(sys, 'frozen', False) and sys.platform == "win32":
    # Force output to a real file instead of the console
    log_file = os.path.join(os.path.dirname(sys.executable), 'seki_crash.log')
    sys.stdout = open(log_file, 'w', encoding='utf-8')
    sys.stderr = sys.stdout

# from dotenv import load_dotenv

# load_dotenv()

# MP_ACCESS_TOKEN = os.getenv('MP_ACCESS_TOKEN')
# MP_TERMINAL_ID = os.getenv('MP_TERMINAL_ID')

# --- PATH HELPERS FOR PYINSTALLER ---
def get_bundled_path(relative_path):
    """Path for read-only files packed inside the .exe (templates, static)"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def get_persistent_path(relative_path):
    """Path for read/write files that must survive reboots (db, cache)"""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

# --- FLASK INIT ---
app = Flask(
    __name__,
    template_folder=get_bundled_path('templates'),
    static_folder=get_bundled_path('static')
)
app.config['SECRET_KEY'] = 'seki_super_secret_key_99' # Change this if you have actual friends
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- AUTH SETUP (Do not delete this) ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- DIRECTORY SETUP ---
DB_DIR = get_persistent_path('db')
os.makedirs(DB_DIR, exist_ok=True)
DB_FILE = os.path.join(DB_DIR, "pos_database.db")

CACHE_DIR = get_persistent_path(os.path.join('static', 'cache'))
os.makedirs(CACHE_DIR, exist_ok=True)

# --- MODELS ---
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

# --- DATABASE LOGIC ---
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users 
                        (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)''')
        
        # Updated table definition
        conn.execute('''CREATE TABLE IF NOT EXISTS products 
                        (barcode TEXT PRIMARY KEY, 
                         name TEXT, 
                         price REAL, 
                         image_url TEXT, 
                         stock REAL DEFAULT 0, 
                         unit_type TEXT DEFAULT 'unit')''')
        
        # Add these two tables for sales history
        conn.execute('''CREATE TABLE IF NOT EXISTS sales 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         date TEXT DEFAULT CURRENT_TIMESTAMP, 
                         total REAL, 
                         payment_method TEXT)''')
                         
        conn.execute('''CREATE TABLE IF NOT EXISTS sale_items 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         sale_id INTEGER, 
                         barcode TEXT, 
                         name TEXT, 
                         price REAL, 
                         quantity REAL, 
                         subtotal REAL,
                         FOREIGN KEY(sale_id) REFERENCES sales(id))''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS dicom 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         name TEXT UNIQUE, 
                         amount REAL DEFAULT 0, 
                         notes TEXT,
                         image_url TEXT,
                         last_updated TEXT DEFAULT CURRENT_TIMESTAMP)''')
        
        # Default user logic remains same...
        user = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
        if not user:
            hashed_pw = generate_password_hash('choripan1234')
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('admin', hashed_pw))
        conn.commit()

@login_manager.user_loader
def load_user(user_id):
    with sqlite3.connect(DB_FILE) as conn:
        user = conn.execute('SELECT id, username FROM users WHERE id = ?', (user_id,)).fetchone()
    return User(user[0], user[1]) if user else None

def download_image(url, barcode):
    if not url or not url.startswith('http'): 
        return url
        
    try:
        headers = {'User-Agent': 'SekiPOS/1.2'}
        # Use stream=True to check headers before downloading the whole file
        with requests.get(url, headers=headers, stream=True, timeout=5) as r:
            r.raise_for_status()
            
            # Detect extension from Content-Type header
            content_type = r.headers.get('content-type')
            ext = mimetypes.guess_extension(content_type) or '.jpg'
            
            local_filename = f"{barcode}{ext}"
            local_path = os.path.join(CACHE_DIR, local_filename)
            
            # Save the file
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            return f"/static/cache/{local_filename}"
    except Exception as e:
        print(f"Download failed: {e}")
    return url

def fetch_from_openfoodfacts(barcode):
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    try:
        headers = {'User-Agent': 'SekiPOS/1.0'}
        resp = requests.get(url, headers=headers, timeout=5).json()
        
        if resp.get('status') == 1:
            p = resp.get('product', {})
            name = p.get('product_name_es') or p.get('product_name') or p.get('brands', 'Unknown')
            imgs = p.get('selected_images', {}).get('front', {}).get('display', {})
            img_url = imgs.get('es') or imgs.get('en') or p.get('image_url', '')
            
            if img_url:
                local_img = download_image(img_url, barcode)
                return {"name": name, "image": local_img}
            return {"name": name, "image": None}
            
    except Exception as e:
        print(f"API Error: {e}")
    return None

# --- ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_in = request.form.get('username')
        pass_in = request.form.get('password')
        with sqlite3.connect(DB_FILE) as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (user_in,)).fetchone()
        if user and check_password_hash(user[2], pass_in):
            login_user(User(user[0], user[1]))
            return redirect(url_for('inventory'))
        flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def defaultRoute():
    return redirect(url_for('inventory'))

@app.route('/inventory')
@login_required
def inventory():
    with sqlite3.connect(DB_FILE) as conn:
        products = conn.execute('SELECT * FROM products').fetchall()
    return render_template('inventory.html', active_page='inventory', products=products, user=current_user)

@app.route("/checkout")
@login_required
def checkout():
    with sqlite3.connect(DB_FILE) as conn:
        # Fetching the same columns the scanner expects
        products = conn.execute('SELECT barcode, name, price, image_url, stock, unit_type FROM products').fetchall()
    return render_template("checkout.html", active_page='checkout', user=current_user, products=products)

@app.route('/dicom')
@login_required
def dicom():
    with sqlite3.connect(DB_FILE) as conn:
        debtors = conn.execute('SELECT id, name, amount, notes, datetime(last_updated, "localtime"), image_url FROM dicom ORDER BY amount DESC').fetchall()
    return render_template('dicom.html', active_page='dicom', user=current_user, debtors=debtors)

@app.route('/sales')
@login_required
def sales():
    selected_date = request.args.get('date')
    payment_method = request.args.get('payment_method')
    page = request.args.get('page', 1, type=int)
    per_page = 100

    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        
        # 1. Calculate the top 3 cards (Now respecting the payment method!)
        target_date = selected_date if selected_date else cur.execute("SELECT date('now', 'localtime')").fetchone()[0]
        
        daily_query = "SELECT SUM(total) FROM sales WHERE date(date, 'localtime') = ?"
        week_query = "SELECT SUM(total) FROM sales WHERE date(date, 'localtime') >= date('now', 'localtime', '-7 days')"
        month_query = "SELECT SUM(total) FROM sales WHERE strftime('%Y-%m', date, 'localtime') = strftime('%Y-%m', 'now', 'localtime')"
        
        daily_params = [target_date]
        week_params = []
        month_params = []
        
        # If a payment method is selected, inject it into the top card queries
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
        
        # 2. Dynamic query builder for the main table and pagination
        base_query = "FROM sales WHERE 1=1"
        params = []

        if selected_date:
            base_query += " AND date(date, 'localtime') = ?"
            params.append(selected_date)
        if payment_method:
            base_query += " AND payment_method = ?"
            params.append(payment_method)
            
        # Get total count and sum for the current table filters BEFORE applying limit/offset
        stats_query = f"SELECT COUNT(*), SUM(total) {base_query}"
        count_res, sum_res = cur.execute(stats_query, tuple(params)).fetchone()
        
        total_count = count_res or 0
        total_sum = sum_res or 0
        total_pages = (total_count + per_page - 1) // per_page
        
        filtered_stats = {
            "total": total_sum,
            "count": total_count
        }

        # Fetch the actual 100 rows for the current page
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


@app.route("/upsert", methods=["POST"])
@login_required
def upsert():
    d = request.form
    barcode = d['barcode']
    
    try:
        price = float(d['price'])
        stock = float(d.get('stock', 0)) # New field
    except (ValueError, TypeError):
        price = 0.0
        stock = 0.0

    unit_type = d.get('unit_type', 'unit') # New field (unit or kg)
    final_image_path = download_image(d['image_url'], barcode)
    
    with sqlite3.connect(DB_FILE) as conn:
        # Updated UPSERT query
        conn.execute('''INSERT INTO products (barcode, name, price, image_url, stock, unit_type) 
                        VALUES (?,?,?,?,?,?)
                        ON CONFLICT(barcode) DO UPDATE SET 
                        name=excluded.name, 
                        price=excluded.price, 
                        image_url=excluded.image_url,
                        stock=excluded.stock,
                        unit_type=excluded.unit_type''',
                     (barcode, d['name'], price, final_image_path, stock, unit_type))
        conn.commit()
    return redirect(url_for('inventory'))

@app.route('/delete/<barcode>', methods=['POST'])
@login_required
def delete(barcode):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('DELETE FROM products WHERE barcode = ?', (barcode,))
        conn.commit()
    # Clean up cache
    img_p = os.path.join(CACHE_DIR, f"{barcode}.jpg")
    if os.path.exists(img_p): os.remove(img_p)
    socketio.emit('product_deleted', {"barcode": barcode})
    return redirect(url_for('inventory'))

@app.route('/scan', methods=['GET'])
def scan():
    barcode = request.args.get('content', '').replace('{content}', '')
    if not barcode: 
        return jsonify({"status": "error", "message": "empty barcode"}), 400
    
    with sqlite3.connect(DB_FILE) as conn:
        # Fixed: Selecting all 6 necessary columns
        p = conn.execute('SELECT barcode, name, price, image_url, stock, unit_type FROM products WHERE barcode = ?', (barcode,)).fetchone()
    
    if p:
        # Now matches the 6 columns in the SELECT statement
        barcode_val, name, price, image_path, stock, unit_type = p        
        
        if image_path and image_path.startswith('/static/'):
            clean_path = image_path.split('?')[0].lstrip('/')
            if not os.path.exists(clean_path):
                ext_data = fetch_from_openfoodfacts(barcode_val)
                if ext_data and ext_data.get('image'):
                    image_path = ext_data['image']
                    with sqlite3.connect(DB_FILE) as conn:
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
    
    # 2. Product not in DB, try external API
    ext = fetch_from_openfoodfacts(barcode)
    if ext:
        # We found it externally, but it's still a 404 relative to our local DB
        external_data = {
            "barcode": barcode, 
            "name": ext['name'], 
            "image": ext['image'],
            "source": "openfoodfacts"
        }
        socketio.emit('scan_error', external_data)
        return jsonify({"status": "not_found", "data": external_data}), 404
    
    # 3. Truly not found anywhere
    socketio.emit('scan_error', {"barcode": barcode})
    return jsonify({"status": "not_found", "data": {"barcode": barcode}}), 404

@app.route('/static/cache/<path:filename>')
def serve_cache(filename):
    return send_from_directory(CACHE_DIR, filename)

@app.route('/bulk_price_update', methods=['POST'])
@login_required
def bulk_price_update():
    data = request.get_json()
    barcodes = data.get('barcodes', [])
    new_price = data.get('new_price')

    if not barcodes or new_price is None:
        return jsonify({"error": "Missing data"}), 400

    try:
        with sqlite3.connect(DB_FILE) as conn:
            # Use executemany for efficiency
            params = [(float(new_price), b) for b in barcodes]
            conn.executemany('UPDATE products SET price = ? WHERE barcode = ?', params)
            conn.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Bulk update failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/bulk_delete', methods=['POST'])
@login_required
def bulk_delete():
    data = request.get_json()
    barcodes = data.get('barcodes', [])

    if not barcodes:
        return jsonify({"error": "No barcodes provided"}), 400

    try:
        with sqlite3.connect(DB_FILE) as conn:
            # Delete records from DB
            conn.execute(f'DELETE FROM products WHERE barcode IN ({",".join(["?"]*len(barcodes))})', barcodes)
            conn.commit()
        
        # Clean up cache for each deleted product
        for barcode in barcodes:
            # This is a bit naive as it only checks .jpg, but matches your existing delete logic
            img_p = os.path.join(CACHE_DIR, f"{barcode}.jpg")
            if os.path.exists(img_p): 
                os.remove(img_p)
                
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Bulk delete failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/upload_image', methods=['POST'])
@login_required
def upload_image():
    if 'image' not in request.files or 'barcode' not in request.form:
        return jsonify({"error": "Missing data"}), 400
    file = request.files['image']
    barcode = request.form['barcode']
    if file.filename == '' or not barcode:
        return jsonify({"error": "Invalid data"}), 400

    filename = f"{barcode}.jpg"
    filepath = os.path.join(CACHE_DIR, filename)
    file.save(filepath)
    timestamp = int(time.time())
    return jsonify({"status": "success", "image_url": f"/static/cache/{filename}?t={timestamp}"}), 200

@app.route('/api/scale/weight', methods=['POST'])
def update_scale_weight():
    data = request.get_json()
    
    # Assuming the scale sends {"weight": 1250} (in grams)
    weight_grams = data.get('weight', 0)
    
    # Optional: Convert to kg if you prefer
    weight_kg = round(weight_grams / 1000, 3)

    # Broadcast to all connected clients via SocketIO
    socketio.emit('scale_update', {
        "grams": weight_grams,
        "kilograms": weight_kg,
        "timestamp": time.time()
    })
    
    return jsonify({"status": "received"}), 200


@app.route('/api/checkout', methods=['POST'])
@login_required
def process_checkout():
    try:
        data = request.get_json()
        cart = data.get('cart', [])
        payment_method = data.get('payment_method', 'efectivo')
        
        if not cart:
            return jsonify({"error": "Cart is empty"}), 400
            
        # Recalculate total on the server because the frontend is a liar
        total = sum(item.get('subtotal', 0) for item in cart)
        
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            
            # Let SQLite handle the exact UTC timestamp internally
            cur.execute('INSERT INTO sales (date, total, payment_method) VALUES (CURRENT_TIMESTAMP, ?, ?)', (total, payment_method))
            sale_id = cur.lastrowid
            
            # Record each item and deduct stock
            for item in cart:
                cur.execute('''INSERT INTO sale_items (sale_id, barcode, name, price, quantity, subtotal)
                               VALUES (?, ?, ?, ?, ?, ?)''', 
                            (sale_id, item['barcode'], item['name'], item['price'], item['qty'], item['subtotal']))
                
                # Deduct from inventory (Manual products will safely be ignored here)
                cur.execute('UPDATE products SET stock = stock - ? WHERE barcode = ?', (item['qty'], item['barcode']))
                
            conn.commit()
            
        return jsonify({"status": "success", "sale_id": sale_id}), 200
        
    except Exception as e:
        print(f"Checkout Error: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/sale/<int:sale_id>')
@login_required
def get_sale_details(sale_id):
    with sqlite3.connect(DB_FILE) as conn:
        items = conn.execute('SELECT barcode, name, price, quantity, subtotal FROM sale_items WHERE sale_id = ?', (sale_id,)).fetchall()
        
    # Format it as a neat list of dictionaries for JavaScript to digest
    item_list = [{"barcode": i[0], "name": i[1], "price": i[2], "qty": i[3], "subtotal": i[4]} for i in items]
    return jsonify(item_list), 200

@app.route('/api/sale/<int:sale_id>', methods=['DELETE'])
@login_required
def reverse_sale(sale_id):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            
            # 1. Get the items and quantities from the receipt
            items = cur.execute('SELECT barcode, quantity FROM sale_items WHERE sale_id = ?', (sale_id,)).fetchall()
            
            # 2. Add the stock back to the inventory
            for barcode, qty in items:
                # This safely ignores manual products since their fake barcodes won't match any row
                cur.execute('UPDATE products SET stock = stock + ? WHERE barcode = ?', (qty, barcode))
                
            # 3. Destroy the evidence
            cur.execute('DELETE FROM sale_items WHERE sale_id = ?', (sale_id,))
            cur.execute('DELETE FROM sales WHERE id = ?', (sale_id,))
            
            conn.commit()
            
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        print(f"Reverse Sale Error: {e}")
        return jsonify({"error": str(e)}), 500
    


@app.route('/api/dicom/update', methods=['POST'])
@login_required
def update_dicom():
    data = request.get_json()
    name = data.get('name', '').strip()
    amount = float(data.get('amount', 0))
    notes = data.get('notes', '')
    image_url = data.get('image_url', '')
    action = data.get('action')
    
    if not name or amount <= 0:
        return jsonify({"error": "Nombre y monto válidos son requeridos"}), 400
        
    if action == 'add':
        amount = -amount

    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute('''INSERT INTO dicom (name, amount, notes, image_url, last_updated) 
                           VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                           ON CONFLICT(name) DO UPDATE SET 
                           amount = amount + excluded.amount,
                           notes = excluded.notes,
                           image_url = CASE WHEN excluded.image_url != "" THEN excluded.image_url ELSE dicom.image_url END,
                           last_updated = CURRENT_TIMESTAMP''', (name, amount, notes, image_url))
        conn.commit()
    return jsonify({"status": "success"}), 200

@app.route('/api/dicom/<int:debtor_id>', methods=['DELETE'])
@login_required
def delete_dicom(debtor_id):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute('DELETE FROM dicom WHERE id = ?', (debtor_id,))
            conn.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    new_password = request.form.get('password')
    profile_pic = request.form.get('profile_pic')
    
    with sqlite3.connect(DB_FILE) as conn:
        if new_password and len(new_password) > 0:
            hashed_pw = generate_password_hash(new_password)
            conn.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_pw, current_user.id))
        
        if profile_pic:
            conn.execute('UPDATE users SET profile_pic = ? WHERE id = ?', (profile_pic, current_user.id))
        conn.commit()
    
    flash('Configuración actualizada')
    return redirect(request.referrer)

@app.route('/export/db')
@login_required
def export_db():
    if os.path.exists(DB_FILE):
        return send_file(DB_FILE, as_attachment=True, download_name=f"SekiPOS_Backup_{datetime.now().strftime('%Y%m%d')}.db", mimetype='application/x-sqlite3')
    return "Error: Database file not found", 404

@app.route('/export/images')
@login_required
def export_images():
    if not os.path.exists(CACHE_DIR) or not os.listdir(CACHE_DIR):
        return "No images found to export", 404

    # Create an in-memory byte stream to hold the zip data
    memory_file = io.BytesIO()
    
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(CACHE_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                # Store files using their names only to avoid nesting inside the zip
                zf.write(file_path, arcname=file)
    
    memory_file.seek(0)
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f"SekiPOS_Images_{datetime.now().strftime('%Y%m%d')}.zip"
    )


from datetime import datetime

@app.route('/gastos')
@login_required
def gastos():
    # Default to the current month if no filter is applied
    selected_month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        
        # Auto-create the table so it doesn't crash on first load
        cur.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT NOT NULL,
                amount INTEGER NOT NULL
            )
        ''')
        
        # Calculate totals for the selected month
        sales_total = cur.execute("SELECT SUM(total) FROM sales WHERE strftime('%Y-%m', date, 'localtime') = ?", (selected_month,)).fetchone()[0] or 0
        expenses_total = cur.execute("SELECT SUM(amount) FROM expenses WHERE strftime('%Y-%m', date, 'localtime') = ?", (selected_month,)).fetchone()[0] or 0
        
        # Fetch the expense list
        expenses_list = cur.execute("SELECT id, date, description, amount FROM expenses WHERE strftime('%Y-%m', date, 'localtime') = ? ORDER BY date DESC", (selected_month,)).fetchall()
        
    return render_template('gastos.html', 
                           active_page='gastos', 
                           user=current_user,
                           sales_total=sales_total,
                           expenses_total=expenses_total,
                           net_profit=sales_total - expenses_total,
                           expenses=expenses_list,
                           selected_month=selected_month)

@app.route('/api/gastos', methods=['POST'])
@login_required
def add_gasto():
    data = request.get_json()
    desc = data.get('description')
    amount = data.get('amount')
    
    if not desc or not amount:
        return jsonify({"error": "Faltan datos"}), 400
        
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO expenses (description, amount) VALUES (?, ?)", (desc, int(amount)))
        conn.commit()
    return jsonify({"success": True})

@app.route('/api/gastos/<int:gasto_id>', methods=['DELETE'])
@login_required
def delete_gasto(gasto_id):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM expenses WHERE id = ?", (gasto_id,))
        conn.commit()
    return jsonify({"success": True})


# @app.route('/process_payment', methods=['POST'])
# @login_required
# def process_payment():
#     data = request.get_json()
#     total_amount = data.get('total')
    
#     if not total_amount or total_amount <= 0:
#         return jsonify({"error": "Invalid amount"}), 400

#     url = "https://api.mercadopago.com/v1/orders"
    
#     headers = {
#         "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
#         "Content-Type": "application/json",
#         "X-Idempotency-Key": str(uuid.uuid4())
#     }
    
#     # MP Point API often prefers integer strings for CLP or exact strings
#     # We use int() here if you are dealing with CLP (no cents)
#     formatted_amount = str(int(float(total_amount)))

#     payload = {
#         "type": "point",
#         "external_reference": f"ref_{int(time.time())}",
#         "description": "Venta SekiPOS",
#         "expiration_time": "PT16M",
#         "transactions": {
#             "payments": [
#                 {
#                     "amount": formatted_amount
#                 }
#             ]
#         },
#         "config": {
#             "point": {
#                 "terminal_id": MP_TERMINAL_ID,
#                 "print_on_terminal": "no_ticket"
#             },
#             "payment_method": {
#                 "default_type": "credit_card"
#             }
#         },
#         "integration_data": {
#             "platform_id": "dev_1234567890",
#             "integrator_id": "dev_1234567890"
#         },
#         "taxes": [
#             {
#                 "payer_condition": "payment_taxable_iva"
#             }
#         ]
#     }

#     try:
#         # Verify the payload in your terminal if it fails again
#         response = requests.post(url, json=payload, headers=headers)
        
#         if response.status_code != 201 and response.status_code != 200:
#             print(f"DEBUG MP ERROR: {response.text}")
            
#         return jsonify(response.json()), response.status_code
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @app.route('/api/mp-webhook', methods=['POST'])
# def webhook_notify():
#     data = request.get_json()
#     action = data.get('action', 'unknown')
#     # Emitimos a todos los clientes conectados
#     socketio.emit('payment_update', {
#         "status": action,
#         "id": data.get('data', {}).get('id')
#     })
#     return jsonify({"status": "ok"}), 200

def start_server():
    # Use socketio.run instead of default app.run
    #socketio.run(app, host='127.0.0.1', port=5000)
    socketio.run(app, host='127.0.0.1', port=5000, log_output=False, allow_unsafe_werkzeug=True)
    
def run_standalone():
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()
    
    # GIVE FLASK 2 SECONDS TO BOOT UP BEFORE OPENING THE BROWSER
    time.sleep(2)
    
    webview.create_window('SekiPOS', 'http://127.0.0.1:5000', width=1366, height=768, resizable=True, fullscreen=False, min_size=(800, 600), maximized=True)
    
    # private_mode=False is the magic flag that allows localStorage to survive.
    # It saves data to %APPDATA%\pywebview on Windows.
    webview.start(private_mode=False)
    
if __name__ == '__main__':
    
    init_db()
    
    # For standalone desktop app with embedded browser, use
    #run_standalone()
    
    # For docker or traditional server deployment, comment out run_standalone() and uncomment the line below:
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
