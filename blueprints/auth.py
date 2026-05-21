from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from core.db import get_db_connection

auth_bp = Blueprint('auth', __name__)

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    with get_db_connection() as conn:
        user = conn.execute('SELECT id, username FROM users WHERE id = ?', (user_id,)).fetchone()
    return User(user[0], user[1]) if user else None

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_in = request.form.get('username')
        pass_in = request.form.get('password')
        with get_db_connection() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (user_in,)).fetchone()
        if user and check_password_hash(user[2], pass_in):
            login_user(User(user[0], user[1]))
            return redirect(url_for('inventory.inventory'))
        flash('Invalid credentials.')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    new_password = request.form.get('password')
    profile_pic = request.form.get('profile_pic')
    
    with get_db_connection() as conn:
        if new_password and len(new_password) > 0:
            hashed_pw = generate_password_hash(new_password)
            conn.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_pw, current_user.id))
        
        if profile_pic:
            conn.execute('UPDATE users SET profile_pic = ? WHERE id = ?', (profile_pic, current_user.id))
        conn.commit()
    
    flash('Configuración actualizada')
    return redirect(request.referrer)

def init_login_manager(app):
    login_manager.init_app(app)