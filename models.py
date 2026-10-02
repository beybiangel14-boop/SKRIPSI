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


class MlModel(db.Model):
    """Registry model K-Means yang sudah dilatih (payload di tabel ml_artifact, lihat MlArtifact)."""
    __tablename__ = 'ml_models'

    id = db.Column(db.Integer, primary_key=True)
    versi = db.Column(db.Integer, unique=True, nullable=False) # Versi model (model_v1, model_v2, ...)
    file_path = db.Column(db.String(255), nullable=False) # Legacy: path file JSON lama ('' bila payload hanya di DB)
    is_active = db.Column(db.Boolean, nullable=False, default=False) # Hanya satu model aktif
    tanggal_latih = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # Waktu training/retrain
    n_samples = db.Column(db.Integer, nullable=False) # Jumlah pelanggan bertransaksi saat training
    k = db.Column(db.Integer, nullable=False) # Jumlah cluster
    silhouette = db.Column(db.Numeric(5, 4)) # Silhouette Score saat training
    alasan = db.Column(db.String(100), nullable=False) # 'pertama_kali' / 'manual' / 'threshold'
    threshold_snapshot = db.Column(db.Text) # JSON ambang batas retrain yang berlaku saat itu
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class MlArtifact(db.Model):
    """Payload artefak model (JSON) — disimpan di DATABASE, bukan file.

    Alasan: filesystem hosting umumnya read-only/ephemeral sehingga file yang
    dibuat saat runtime bisa hilang; penyimpanan DB membuat model selalu
    tersedia selama database hidup. Tabel BARU (dibuat via db.create_all,
    tanpa ALTER tabel mana pun). Artefak lama di folder models_ml/ tetap
    dimuat sebagai fallback kompatibilitas mundur.
    """
    __tablename__ = 'ml_artifact'

    versi = db.Column(db.Integer, primary_key=True) # 1:1 dengan ml_models.versi
    artifact_json = db.Column(db.Text, nullable=False) # Payload: scaler min/max, centroid, metrics, thresholds
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class SegmentasiRiwayat(db.Model):
    """Snapshot hasil clustering per pelanggan pada setiap kali model dijalankan/dilatih ulang,
    dipakai untuk analisis migrasi segmen antar-periode."""
    __tablename__ = 'segmentasi_riwayat'

    id = db.Column(db.Integer, primary_key=True)
    pelanggan_id = db.Column(db.Integer, db.ForeignKey('pelanggan.id', ondelete='CASCADE'), nullable=False)
    cluster = db.Column(db.Integer, nullable=False) # 0, 1, 2
    segmentasi = db.Column(db.String(50), nullable=False)
    model_versi = db.Column(db.Integer, nullable=False) # Versi model yang menghasilkan snapshot ini
    tanggal_snapshot = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # Waktu snapshot (satu batch = satu waktu)

    pelanggan = db.relationship('Pelanggan', backref=db.backref('riwayat_segmentasi', cascade='all, delete-orphan', lazy=True), lazy=True)
