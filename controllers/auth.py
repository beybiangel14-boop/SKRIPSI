from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from functools import wraps
from models import User
from utils.db import db

auth_bp = Blueprint('auth', __name__)

def login_required(roles=None):
    """
    Decorator untuk membatasi akses route hanya untuk user yang sudah login
    dan memiliki role yang sesuai (operator/owner).
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Anda harus login terlebih dahulu.', 'warning')
                return redirect(url_for('auth.login'))
            if roles and session.get('role') not in roles:
                flash('Anda tidak memiliki hak akses untuk halaman tersebut.', 'danger')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Jika sudah login, langsung ke dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            role_label = 'OPERATOR' if user.role == 'admin' else 'OWNER'
            flash(f'Selamat datang kembali, {user.username}! Anda login sebagai {role_label}.', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash('Username atau Password salah. Silakan coba lagi.', 'danger')
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Anda berhasil logout dari sistem.', 'success')
    return redirect(url_for('auth.login'))
