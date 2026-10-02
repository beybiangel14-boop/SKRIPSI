from datetime import datetime
from utils.db import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'owner'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Pelanggan(db.Model):
    __tablename__ = 'pelanggan'
    
    id = db.Column(db.Integer, primary_key=True)
    nama_pelanggan = db.Column(db.String(100), nullable=False)
    nomor_hp = db.Column(db.String(20), nullable=False)
    alamat = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships (Cascades when pelanggan is deleted)
    transaksi = db.relationship('Transaksi', backref='pelanggan', cascade='all, delete-orphan', lazy=True)
    segmentasi = db.relationship('SegmentasiHasil', backref='pelanggan', uselist=False, cascade='all, delete-orphan', lazy=True)


class Transaksi(db.Model):
    __tablename__ = 'transaksi'
    
    id = db.Column(db.Integer, primary_key=True)
    tanggal_transaksi = db.Column(db.Date, nullable=False)
    pelanggan_id = db.Column(db.Integer, db.ForeignKey('pelanggan.id', ondelete='CASCADE'), nullable=False)
    jumlah_kg = db.Column(db.Numeric(10, 2), nullable=False)
    harga_per_kg = db.Column(db.Numeric(10, 2), nullable=False)
    total_transaksi = db.Column(db.Numeric(15, 2), nullable=False)
    metode_pembayaran = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def calculate_total(self):
        self.total_transaksi = self.jumlah_kg * self.harga_per_kg


class SegmentasiHasil(db.Model):
    __tablename__ = 'segmentasi_hasil'
    
    id = db.Column(db.Integer, primary_key=True)
    pelanggan_id = db.Column(db.Integer, db.ForeignKey('pelanggan.id', ondelete='CASCADE'), unique=True, nullable=False)
    recency = db.Column(db.Integer, nullable=False) # Hari sejak transaksi terakhir
    frequency = db.Column(db.Integer, nullable=False) # Jumlah transaksi
    monetary = db.Column(db.Numeric(15, 2), nullable=False) # Total nominal belanja
    score_rfm = db.Column(db.Numeric(5, 2), nullable=False) # Skor RFM terhitung
    cluster = db.Column(db.Integer, nullable=False) # 0, 1, 2
    segmentasi = db.Column(db.String(50), nullable=False) # 'Pelanggan Loyal', 'Pelanggan Aktif', 'Pelanggan Non Aktif'
    tanggal_perhitungan = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
