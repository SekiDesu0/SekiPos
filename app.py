import os
import sys
import time
import threading
import urllib.request
import urllib.error

from flask import Flask, redirect, url_for, send_file, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
import webview
from flask_socketio import SocketIO

from core.utils import get_bundled_path, get_persistent_path
from core.db import init_db as init_db_core, get_db_connection
from core.events import socketio

from blueprints.auth import auth_bp, init_login_manager
from blueprints.finance import finance_bp
from blueprints.inventory import inventory_bp
from blueprints.pos import pos_bp
from blueprints.sales import sales_bp

# --- PYINSTALLER WINDOWED MODE FIX ---
if getattr(sys, 'frozen', False) and sys.platform == "win32":
    log_file = os.path.join(os.path.dirname(sys.executable), 'seki_crash.log')
    sys.stdout = open(log_file, 'w', encoding='utf-8')
    sys.stderr = sys.stdout

# --- FLASK INIT ---
app = Flask(
    __name__,
    template_folder=get_bundled_path('templates'),
    static_folder=get_bundled_path('static')
)
app.config['SECRET_KEY'] = 'seki_super_secret_key_99'

# --- DIRECTORY SETUP ---
DB_DIR = get_persistent_path('db')
os.makedirs(DB_DIR, exist_ok=True)
DB_FILE = os.path.join(DB_DIR, "pos_database.db")
app.config['DB_FILE'] = DB_FILE

CACHE_DIR = get_persistent_path(os.path.join('static', 'cache'))
os.makedirs(CACHE_DIR, exist_ok=True)
app.config['CACHE_DIR'] = CACHE_DIR

# --- BLUEPRINT REGISTRATION ---
app.register_blueprint(auth_bp)
app.register_blueprint(finance_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(pos_bp)
app.register_blueprint(sales_bp)

init_login_manager(app)
socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')

# --- DATABASE INITIALIZATION ---
init_db_core(DB_FILE)

# --- ROOT ROUTE ---
@app.route('/')
@login_required
def index():
    return redirect(url_for('inventory.inventory'))

# --- RUN FUNCTION ---
def start_server():
    #time.sleep(60) # Sleep for testing wait_for_server function
    socketio.run(app, host='127.0.0.1', port=5000, log_output=False, allow_unsafe_werkzeug=True)

def wait_for_server(url, timeout=69420, interval=0.5):
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(interval)
    return False

def run_standalone():
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()
    if not wait_for_server('http://127.0.0.1:5000'):
        print('[SekiPOS] Timeout: el servidor no arrancó en 30s', file=sys.stderr)
        return
    webview.create_window('SekiPOS', 'http://127.0.0.1:5000', width=1366, height=768, resizable=True, fullscreen=False, min_size=(800, 600), maximized=True)
    webview.start(private_mode=False)

if __name__ == '__main__':
    run_standalone()  # Uncomment for desktop app, comment for server mode
    #socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True) # Comment for desktop app, uncomment for server mode