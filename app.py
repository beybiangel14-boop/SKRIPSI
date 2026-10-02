from flask import Flask, redirect, url_for, session
import pymysql
from config import Config
from utils.db import db

# 1. Cek atau Buat Database MySQL Secara Otomatis di Host
# Laragon default: host='localhost', user='root', password=''
try:
    conn = pymysql.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        port=int(Config.DB_PORT)
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}`")
    conn.commit()
    cursor.close()
    conn.close()
    print(f"[*] Database '{Config.DB_NAME}' berhasil divalidasi/dibuat.")
except Exception as e:
    print(f"[!] Peringatan: Gagal memvalidasi database secara otomatis: {e}")
    print("[*] Pastikan MySQL Laragon/XAMPP Anda sudah berjalan.")

# 2. Inisialisasi Flask App
app = Flask(__name__)
app.config.from_object(Config)

# Inisialisasi database SQLAlchemy
db.init_app(app)

# 3. Import & Registrasi Blueprints (Controllers)
from controllers.auth import auth_bp
from controllers.dashboard import dashboard_bp
from controllers.pelanggan import pelanggan_bp
from controllers.transaksi import transaksi_bp
from controllers.segmentasi import segmentasi_bp
from controllers.laporan import laporan_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(pelanggan_bp)
app.register_blueprint(transaksi_bp)
app.register_blueprint(segmentasi_bp)
app.register_blueprint(laporan_bp)

# Root route: Arahkan ke dashboard jika login, jika tidak ke login page
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.login'))

# 4. Sinkronisasi DB & Seeding Akun Default saat Startup
with app.app_context():
    try:
        db.create_all()
        print("[*] Tabel database berhasil disinkronisasi.")
        
        # Import model User untuk seeding data
        from models import User
        
        # Seed Operator (username: admin, password: admin123)
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            print("[+] Akun default Operator berhasil didaftarkan (Pass: admin123).")
            
        # Seed Owner (username: owner, password: owner123)
        owner_user = User.query.filter_by(username='owner').first()
        if not owner_user:
            owner = User(username='owner', role='owner')
            owner.set_password('owner123')
            db.session.add(owner)
            print("[+] Akun default Owner berhasil didaftarkan (Pass: owner123).")
            
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[!] Gagal menyinkronkan/menyemai database: {e}")

if __name__ == "__main__":
    app.run(debug=True)