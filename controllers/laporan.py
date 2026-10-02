from datetime import datetime
from flask import Blueprint, render_template, Response, flash, redirect, url_for
from controllers.auth import login_required
from models import Pelanggan, Transaksi, SegmentasiHasil
from utils.db import db
from utils.core_ml import MinMaxScalerPure, KMeansPure, calculate_silhouette_score
from utils.pdf_builder import (
    generate_pelanggan_pdf,
    generate_transaksi_pdf,
    generate_segmentasi_pdf,
    generate_ranking_pdf
)

BULAN_INDO = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
    5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
    9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
}

laporan_bp = Blueprint('laporan', __name__, url_prefix='/laporan')

@laporan_bp.route('/')
@login_required(roles=['admin', 'owner'])
def index():
    total_pelanggan = Pelanggan.query.count()
    total_transaksi = Transaksi.query.count()
    rfm_records = SegmentasiHasil.query.filter(SegmentasiHasil.cluster != -1).all()
    has_segmentasi = len(rfm_records) > 0
    
    loyal_count = SegmentasiHasil.query.filter_by(cluster=0).count()
    aktif_count = SegmentasiHasil.query.filter_by(cluster=1).count()
    nonaktif_count = SegmentasiHasil.query.filter_by(cluster=2).count()
    total_clustered = loyal_count + aktif_count + nonaktif_count

    pct_loyal = round((loyal_count / total_clustered * 100), 1) if total_clustered > 0 else 0
    pct_aktif = round((aktif_count / total_clustered * 100), 1) if total_clustered > 0 else 0
    pct_nonaktif = round((nonaktif_count / total_clustered * 100), 1) if total_clustered > 0 else 0

    # Rata-rata RFM per Cluster
    cluster_means = {
        0: {'r': 0, 'f': 0, 'm': 0},
        1: {'r': 0, 'f': 0, 'm': 0},
        2: {'r': 0, 'f': 0, 'm': 0}
    }
    silhouette_score = 0.0

    if has_segmentasi:
        for c in range(3):
            c_recs = [r for r in rfm_records if r.cluster == c]
            if c_recs:
                cluster_means[c]['r'] = round(sum(r.recency for r in c_recs) / len(c_recs), 1)
                cluster_means[c]['f'] = round(sum(r.frequency for r in c_recs) / len(c_recs), 1)
                cluster_means[c]['m'] = round(sum(float(r.monetary) for r in c_recs) / len(c_recs), 0)

        # Calculate Silhouette Score
        valid_items = [r for r in rfm_records if r.frequency > 0]
        if valid_items:
            r_vals = [float(x.recency) for x in valid_items]
            f_vals = [float(x.frequency) for x in valid_items]
            m_vals = [float(x.monetary) for x in valid_items]

            scaler_r = MinMaxScalerPure().fit(r_vals)
            scaler_f = MinMaxScalerPure().fit(f_vals)
            scaler_m = MinMaxScalerPure().fit(m_vals)

            X_norm = [
                [
                    scaler_r.transform([float(x.recency)])[0],
                    scaler_f.transform([float(x.frequency)])[0],
                    scaler_m.transform([float(x.monetary)])[0]
                ] for x in valid_items
            ]
            km = KMeansPure(n_clusters=3).fit(X_norm)
            silhouette_score = calculate_silhouette_score(X_norm, km.labels_)

    now = datetime.now()
    tgl_cetak = f"{now.day} {BULAN_INDO.get(now.month, '')} {now.year}"
    total_omzet = db.session.query(db.func.sum(Transaksi.total_transaksi)).scalar() or 0

    hasil_list = db.session.query(
        Pelanggan.nama_pelanggan,
        SegmentasiHasil.recency,
        SegmentasiHasil.frequency,
        SegmentasiHasil.monetary,
        SegmentasiHasil.cluster,
        SegmentasiHasil.segmentasi,
        SegmentasiHasil.tanggal_perhitungan
    ).join(SegmentasiHasil, Pelanggan.id == SegmentasiHasil.pelanggan_id)\
     .filter(SegmentasiHasil.cluster != -1)\
     .order_by(SegmentasiHasil.cluster, Pelanggan.nama_pelanggan).all()

    return render_template(
        'laporan/index.html',
        total_pelanggan=total_pelanggan,
        total_transaksi=total_transaksi,
        total_omzet=total_omzet,
        tgl_cetak=tgl_cetak,
        has_segmentasi=has_segmentasi,
        loyal_count=loyal_count,
        aktif_count=aktif_count,
        nonaktif_count=nonaktif_count,
        pct_loyal=pct_loyal,
        pct_aktif=pct_aktif,
        pct_nonaktif=pct_nonaktif,
        cluster_means=cluster_means,
        silhouette_score=silhouette_score,
        hasil_list=hasil_list
    )


@laporan_bp.route('/pelanggan/pdf')
@login_required(roles=['admin', 'owner'])
def pelanggan_pdf():
    pelanggan_list = Pelanggan.query.order_by(Pelanggan.nama_pelanggan).all()
    if not pelanggan_list:
        flash('Data pelanggan kosong, tidak dapat mengekspor PDF.', 'warning')
        return redirect(url_for('laporan.index'))
        
    pdf_bytes = generate_pelanggan_pdf(pelanggan_list)
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': 'inline; filename=laporan_pelanggan.pdf'}
    )


@laporan_bp.route('/transaksi/pdf')
@login_required(roles=['admin', 'owner'])
def transaksi_pdf():
    transaksi_list = Transaksi.query.order_by(Transaksi.tanggal_transaksi.desc()).all()
    if not transaksi_list:
        flash('Data transaksi kosong, tidak dapat mengekspor PDF.', 'warning')
        return redirect(url_for('laporan.index'))
        
    pdf_bytes = generate_transaksi_pdf(transaksi_list)
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': 'inline; filename=laporan_transaksi.pdf'}
    )


@laporan_bp.route('/segmentasi/pdf')
@login_required(roles=['admin', 'owner'])
def segmentasi_pdf():
    hasil_list = db.session.query(
        Pelanggan.nama_pelanggan,
        SegmentasiHasil.recency,
        SegmentasiHasil.frequency,
        SegmentasiHasil.monetary,
        SegmentasiHasil.cluster,
        SegmentasiHasil.segmentasi,
        SegmentasiHasil.tanggal_perhitungan
    ).join(SegmentasiHasil, Pelanggan.id == SegmentasiHasil.pelanggan_id)\
     .filter(SegmentasiHasil.cluster != -1)\
     .order_by(SegmentasiHasil.cluster, Pelanggan.nama_pelanggan).all()
     
    if not hasil_list:
        flash('Data hasil segmentasi kosong. Silakan lakukan proses segmentasi terlebih dahulu.', 'warning')
        return redirect(url_for('laporan.index'))
    
    now = datetime.now()
    tgl_cetak = f"{now.day} {BULAN_INDO.get(now.month, '')} {now.year}"
    total_pelanggan = Pelanggan.query.count()
    total_transaksi = Transaksi.query.count()
    total_omzet = db.session.query(db.func.sum(Transaksi.total_transaksi)).scalar() or 0

    summary_data = {
        'tgl_cetak': tgl_cetak,
        'total_pelanggan': total_pelanggan,
        'total_transaksi': total_transaksi,
        'total_omzet': total_omzet
    }
        
    pdf_bytes = generate_segmentasi_pdf(hasil_list, summary_data)
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': 'inline; filename=laporan_segmentasi.pdf'}
    )


@laporan_bp.route('/ranking/pdf')
@login_required(roles=['admin', 'owner'])
def ranking_pdf():
    ranking_list = db.session.query(
        Pelanggan.nama_pelanggan,
        SegmentasiHasil.segmentasi,
        SegmentasiHasil.score_rfm,
        SegmentasiHasil.monetary
    ).join(SegmentasiHasil, Pelanggan.id == SegmentasiHasil.pelanggan_id)\
     .filter(SegmentasiHasil.cluster != -1)\
     .order_by(SegmentasiHasil.score_rfm.desc(), SegmentasiHasil.monetary.desc()).all()
     
    if not ranking_list:
        flash('Data ranking kosong. Silakan lakukan proses segmentasi terlebih dahulu.', 'warning')
        return redirect(url_for('laporan.index'))
        
    pdf_bytes = generate_ranking_pdf(ranking_list)
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': 'inline; filename=laporan_ranking_pelanggan.pdf'}
    )
