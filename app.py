import os
import sqlite3
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import mimetypes

app = Flask(__name__)
app.config['SECRET_KEY'] = 'seki_super_secret_key_99' # Change this if you have actual friends
socketio = SocketIO(app, cors_allowed_origins="*")

# Auth Setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'

DB_FILE = 'db/pos_database.db'
CACHE_DIR = 'static/cache'
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
        conn.execute('''CREATE TABLE IF NOT EXISTS products 
                        (barcode TEXT PRIMARY KEY, name TEXT, price REAL, image_url TEXT)''')
        
        # Default user: admin / Pass: choripan1234
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
    # Check if we already have a cached image even if API fails
    local_filename = f"{barcode}.jpg"
    local_path = os.path.join(CACHE_DIR, local_filename)
    cached_url = f"/static/cache/{local_filename}" if os.path.exists(local_path) else None

    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    try:
        headers = {'User-Agent': 'SekiPOS/1.0'}
        resp = requests.get(url, headers=headers, timeout=5).json()
        
        if resp.get('status') == 1:
            p = resp.get('product', {})
            name = p.get('product_name_es') or p.get('product_name') or p.get('brands', 'Unknown')
            imgs = p.get('selected_images', {}).get('front', {}).get('display', {})
            img_url = imgs.get('es') or imgs.get('en') or p.get('image_url', '')
            local_img = download_image(img_url, barcode)
            return {"name": name, "image": local_img}
            
    except Exception as e:
        print(f"API Error: {e}")

    # If API fails but we have a cache, return the cache with a generic name
    if cached_url:
        return {"name": "Producto Cacheado", "image": cached_url}
        
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
            return redirect(url_for('index'))
        flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user(); return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    with sqlite3.connect(DB_FILE) as conn:
        products = conn.execute('SELECT * FROM products').fetchall()
    return render_template('index.html', products=products, user=current_user)

@app.route('/upsert', methods=['POST'])
@login_required
def upsert():
    d = request.form
    barcode = d['barcode']
    
    try:
        price = float(d['price'])
    except (ValueError, TypeError):
        price = 0.0

    final_image_path = download_image(d['image_url'], barcode)
    
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''INSERT INTO products (barcode, name, price, image_url) VALUES (?,?,?,?)
                        ON CONFLICT(barcode) DO UPDATE SET name=excluded.name, 
                        price=excluded.price, image_url=excluded.image_url''',
                     (barcode, d['name'], price, final_image_path))
        conn.commit()
    return redirect(url_for('index'))

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
    return redirect(url_for('index'))

@app.route('/scan', methods=['GET'])
def scan():
    barcode = request.args.get('content', '').replace('{content}', '')
    if not barcode: return jsonify({"err": "empty"}), 400
    
    with sqlite3.connect(DB_FILE) as conn:
        p = conn.execute('SELECT * FROM products WHERE barcode = ?', (barcode,)).fetchone()
    
    if p:
        socketio.emit('new_scan', {"barcode": p[0], "name": p[1], "price": int(p[2]), "image": p[3]})
        return jsonify({"status": "ok"})
    
    # Not in DB, try external API or Local Cache
    ext = fetch_from_openfoodfacts(barcode)
    if ext:
        socketio.emit('scan_error', {
            "barcode": barcode, 
            "name": ext['name'], 
            "image": ext['image']
        })
    else:
        socketio.emit('scan_error', {"barcode": barcode})
        
    return jsonify({"status": "not_found"}), 404

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

if __name__ == '__main__':
    init_db()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
