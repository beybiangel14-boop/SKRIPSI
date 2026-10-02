from flask import Blueprint, render_template, session, redirect, url_for
from controllers.auth import login_required
from models import Pelanggan, Transaksi, SegmentasiHasil
from utils.db import db
from sqlalchemy import func, literal
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required()
def index():
    # 1. Hitung Statistik Utama
    total_pelanggan = Pelanggan.query.count()
    total_transaksi = Transaksi.query.count()
    
    # Total Omzet
    total_omzet = db.session.query(func.sum(Transaksi.total_transaksi)).scalar() or 0.0
    
    # Statistik Cluster
    loyal_count = SegmentasiHasil.query.filter_by(cluster=0).count()
    aktif_count = SegmentasiHasil.query.filter_by(cluster=1).count()
    nonaktif_count = SegmentasiHasil.query.filter_by(cluster=2).count()
    
    # 2. Top 5 Pelanggan Terbaik
    # Bisa berdasarkan skor RFM tertinggi atau total pembelanjaan (monetary) tertinggi.
    # Di sini kita ambil berdasarkan total monetary di hasil segmentasi, atau jika belum berjalan, berdasarkan akumulasi transaksi.
    top_pelanggan = []
    has_segmentasi = SegmentasiHasil.query.filter(SegmentasiHasil.cluster != -1).count() > 0
    
    if has_segmentasi:
        top_pelanggan = db.session.query(
            Pelanggan.nama_pelanggan,
            SegmentasiHasil.segmentasi,
            SegmentasiHasil.score_rfm,
            SegmentasiHasil.monetary
        ).join(SegmentasiHasil, Pelanggan.id == SegmentasiHasil.pelanggan_id)\
         .filter(SegmentasiHasil.cluster != -1)\
         .order_by(SegmentasiHasil.score_rfm.desc(), SegmentasiHasil.monetary.desc())\
         .limit(5).all()
    else:
        # Fallback jika belum pernah dijalankan segmentasi
        top_pelanggan = db.session.query(
            Pelanggan.nama_pelanggan,
            literal('Belum Ada').label('segmentasi'),
            literal(0.0).label('score_rfm'),
            func.sum(Transaksi.total_transaksi).label('monetary')
        ).join(Transaksi, Pelanggan.id == Transaksi.pelanggan_id)\
         .group_by(Pelanggan.id)\
         .order_by(func.sum(Transaksi.total_transaksi).desc())\
         .limit(5).all()

    # 3. Data Omzet Bulanan untuk Chart.js (Format: YYYY-MM)
    monthly_sales = db.session.query(
        func.date_format(Transaksi.tanggal_transaksi, '%Y-%m').label('bulan'),
        func.sum(Transaksi.total_transaksi).label('total')
    ).group_by('bulan')\
     .order_by('bulan')\
     .limit(12).all()
     
    sales_labels = [s.bulan for s in monthly_sales]
    sales_data = [float(s.total) for s in monthly_sales]
    
    # Definisikan nama bulan bahasa indonesia untuk label chart jika mau lebih rapi
    bulan_indo = {
        '01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr', '05': 'Mei', '06': 'Jun',
        '07': 'Jul', '08': 'Ags', '09': 'Sep', '10': 'Okt', '11': 'Nov', '12': 'Des'
    }
    formatted_labels = []
    for label in sales_labels:
        try:
            thn, bln = label.split('-')
            formatted_labels.append(f"{bulan_indo[bln]} {thn}")
        except:
            formatted_labels.append(label)

    # 4. Arahkan ke template berdasarkan role pengguna
    role = session.get('role')
    if role == 'owner':
        return render_template('dashboard/owner.html',
                               total_pelanggan=total_pelanggan,
                               total_transaksi=total_transaksi,
                               total_omzet=total_omzet,
                               loyal_count=loyal_count,
                               aktif_count=aktif_count,
                               nonaktif_count=nonaktif_count,
                               top_pelanggan=top_pelanggan,
                               sales_labels=formatted_labels,
                               sales_data=sales_data)
    else:
        # Default: operator
        return render_template('dashboard/admin.html',
                               total_pelanggan=total_pelanggan,
                               total_transaksi=total_transaksi,
                               total_omzet=total_omzet,
                               loyal_count=loyal_count,
                               aktif_count=aktif_count,
                               nonaktif_count=nonaktif_count,
                               top_pelanggan=top_pelanggan,
                               sales_labels=formatted_labels,
                               sales_data=sales_data)
