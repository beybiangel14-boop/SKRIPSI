from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from controllers.auth import login_required
from models import Pelanggan, Transaksi, SegmentasiHasil
from utils.db import db
from utils.core_ml import (
    calculate_rfm, run_kmeans_only, MinMaxScalerPure, KMeansPure,
    calculate_elbow_method, calculate_silhouette_score
)
from datetime import datetime, timedelta

segmentasi_bp = Blueprint('segmentasi', __name__, url_prefix='/segmentasi')


@segmentasi_bp.route('/analisis', methods=['GET', 'POST'])
@segmentasi_bp.route('/', methods=['GET', 'POST'])
@login_required(roles=['admin', 'owner'])
def analisis():
    # 1. Parameter Filter Periode Data (LANGKAH 1)
    periode = request.args.get('periode', 'semua')
    show_elbow = request.args.get('show_elbow', '0') == '1'
    
    # Base Query Transaksi & Pelanggan
    tx_query = Transaksi.query
    if periode == '30_hari':
        tgl_mulai = datetime.now().date() - timedelta(days=30)
        tx_query = tx_query.filter(Transaksi.tanggal_transaksi >= tgl_mulai)
    elif periode == '90_hari':
        tgl_mulai = datetime.now().date() - timedelta(days=90)
        tx_query = tx_query.filter(Transaksi.tanggal_transaksi >= tgl_mulai)
    elif periode == '365_hari':
        tgl_mulai = datetime.now().date() - timedelta(days=365)
        tx_query = tx_query.filter(Transaksi.tanggal_transaksi >= tgl_mulai)

    transaksi_db = tx_query.all()
    pelanggan_db = Pelanggan.query.order_by(Pelanggan.nama_pelanggan).all()

    total_p = len(pelanggan_db)
    total_t = len(transaksi_db)

    # Status Acuan Tanggal
    tanggal_analisis = datetime.now().date()

    # Form Submission Handlers
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'hitung_rfm':
            if session.get('role') != 'admin':
                flash('Hanya Operator yang dapat menghitung nilai RFM.', 'danger')
                return redirect(url_for('segmentasi.analisis', periode=periode))

            if total_p == 0:
                flash('Data pelanggan kosong.', 'danger')
                return redirect(url_for('segmentasi.analisis', periode=periode))

            try:
                pelanggan_list = [{'id': p.id, 'nama_pelanggan': p.nama_pelanggan} for p in pelanggan_db]
                transaksi_list = [{
                    'pelanggan_id': t.pelanggan_id,
                    'tanggal_transaksi': t.tanggal_transaksi,
                    'total_transaksi': float(t.total_transaksi)
                } for t in transaksi_db]

                rfm_results = calculate_rfm(pelanggan_list, transaksi_list, tanggal_analisis)

                db.session.query(SegmentasiHasil).delete()
                for item in rfm_results:
                    hasil_db = SegmentasiHasil(
                        pelanggan_id=item['id'],
                        recency=item['recency'],
                        frequency=item['frequency'],
                        monetary=item['monetary'],
                        score_rfm=item['score_rfm'],
                        cluster=-1,
                        segmentasi='Belum Dicluster',
                        tanggal_perhitungan=datetime.utcnow()
                    )
                    db.session.add(hasil_db)
                db.session.commit()
                flash('Perhitungan RFM berhasil dilakukan & disimpan!', 'success')
                return redirect(url_for('segmentasi.analisis', periode=periode))

            except Exception as e:
                db.session.rollback()
                flash(f'Terjadi kesalahan saat menghitung RFM: {e}', 'danger')

        elif action == 'jalankan_elbow':
            if session.get('role') != 'admin':
                flash('Hanya Operator yang dapat menjalankan Elbow Method.', 'danger')
                return redirect(url_for('segmentasi.analisis', periode=periode))

            rfm_db = SegmentasiHasil.query.all()
            if not rfm_db:
                flash('Data RFM belum dihitung.', 'danger')
                return redirect(url_for('segmentasi.analisis', periode=periode))

            flash('Perhitungan Elbow Method berhasil dijalankan!', 'success')
            return redirect(url_for('segmentasi.analisis', periode=periode, show_elbow=1))

        elif action == 'jalankan_kmeans':
            if session.get('role') != 'admin':
                flash('Hanya Operator yang dapat memproses clustering.', 'danger')
                return redirect(url_for('segmentasi.analisis', periode=periode))

            rfm_db = SegmentasiHasil.query.all()
            if not rfm_db:
                flash('Data RFM belum dihitung.', 'danger')
                return redirect(url_for('segmentasi.analisis', periode=periode))

            try:
                rfm_list = [{
                    'id': r.pelanggan_id,
                    'nama_pelanggan': r.pelanggan.nama_pelanggan,
                    'recency': r.recency,
                    'frequency': r.frequency,
                    'monetary': float(r.monetary),
                    'score_rfm': float(r.score_rfm)
                } for r in rfm_db]

                clustered_results = run_kmeans_only(rfm_list)

                for item in clustered_results:
                    hasil_db = SegmentasiHasil.query.filter_by(pelanggan_id=item['id']).first()
                    if hasil_db:
                        hasil_db.cluster = item['cluster']
                        hasil_db.segmentasi = item['segmentasi']
                        hasil_db.tanggal_perhitungan = datetime.utcnow()

                db.session.commit()
                flash('Proses Clustering K-Means berhasil diselesaikan!', 'success')
                return redirect(url_for('segmentasi.analisis', periode=periode, show_elbow=1 if show_elbow else 0))

            except Exception as e:
                db.session.rollback()
                flash(f'Terjadi kesalahan saat memproses K-Means: {e}', 'danger')

    # Fetch RFM DB records
    rfm_records = SegmentasiHasil.query.join(Pelanggan).order_by(Pelanggan.nama_pelanggan).all()
    has_rfm = len(rfm_records) > 0
    has_kmeans = SegmentasiHasil.query.filter(SegmentasiHasil.cluster != -1).count() > 0

    # LANGKAH 2 Data (RFM Metrics)
    avg_recency = 0
    avg_frequency = 0
    avg_monetary = 0
    if has_rfm:
        avg_recency = round(sum(r.recency for r in rfm_records) / len(rfm_records), 1)
        avg_frequency = round(sum(r.frequency for r in rfm_records) / len(rfm_records), 1)
        avg_monetary = round(sum(float(r.monetary) for r in rfm_records) / len(rfm_records), 0)

    # LANGKAH 3 Data (Normalisasi Data RFM)
    rfm_normalized = []
    norm_stats = {'r_min': 0, 'r_max': 0, 'f_min': 0, 'f_max': 0, 'm_min': 0, 'm_max': 0}

    if has_rfm:
        r_vals = [r.recency for r in rfm_records]
        f_vals = [r.frequency for r in rfm_records]
        m_vals = [float(r.monetary) for r in rfm_records]

        scaler_r = MinMaxScalerPure().fit(r_vals)
        scaler_f = MinMaxScalerPure().fit(f_vals)
        scaler_m = MinMaxScalerPure().fit(m_vals)

        r_norms = scaler_r.transform(r_vals)
        f_norms = scaler_f.transform(f_vals)
        m_norms = scaler_m.transform(m_vals)

        norm_stats = {
            'r_min': scaler_r.min_val,
            'r_max': scaler_r.max_val,
            'f_min': scaler_f.min_val,
            'f_max': scaler_f.max_val,
            'm_min': scaler_m.min_val,
            'm_max': scaler_m.max_val
        }

        for i, r in enumerate(rfm_records):
            r_diff = (scaler_r.max_val - scaler_r.min_val) if scaler_r.max_val != scaler_r.min_val else 1.0
            f_diff = (scaler_f.max_val - scaler_f.min_val) if scaler_f.max_val != scaler_f.min_val else 1.0
            m_diff = (scaler_m.max_val - scaler_m.min_val) if scaler_m.max_val != scaler_m.min_val else 1.0

            rfm_normalized.append({
                'pelanggan_id': r.pelanggan_id,
                'nama_pelanggan': r.pelanggan.nama_pelanggan,
                'recency': r.recency,
                'frequency': r.frequency,
                'monetary': float(r.monetary),
                'r_norm': round(r_norms[i], 4),
                'f_norm': round(f_norms[i], 4),
                'm_norm': round(m_norms[i], 4),
                'num_r': r.recency - scaler_r.min_val,
                'r_diff': r_diff,
                'num_f': r.frequency - scaler_f.min_val,
                'f_diff': f_diff,
                'num_m': float(r.monetary) - scaler_m.min_val,
                'm_diff': m_diff,
            })

    # LANGKAH 4 Data (Elbow Method)
    rfm_list_dict = [{
        'recency': r.recency,
        'frequency': r.frequency,
        'monetary': float(r.monetary)
    } for r in rfm_records] if has_rfm else []
    
    elbow_res = None
    if has_rfm:
        elbow_res = calculate_elbow_method(rfm_list_dict, max_k=6)

    # LANGKAH 5 Data (K-Means & Silhouette Score)
    silhouette_score = 0.0
    cluster_means = {0: {'r': 0, 'f': 0, 'm': 0}, 1: {'r': 0, 'f': 0, 'm': 0}, 2: {'r': 0, 'f': 0, 'm': 0}}

    if has_kmeans:
        valid_items = [item for item in rfm_list_dict if item['frequency'] > 0]
        if valid_items:
            scaler_r = MinMaxScalerPure().fit([x['recency'] for x in valid_items])
            scaler_f = MinMaxScalerPure().fit([x['frequency'] for x in valid_items])
            scaler_m = MinMaxScalerPure().fit([x['monetary'] for x in valid_items])

            X_norm = [
                [
                    scaler_r.transform([x['recency']])[0],
                    scaler_f.transform([x['frequency']])[0],
                    scaler_m.transform([x['monetary']])[0]
                ] for x in valid_items
            ]
            km = KMeansPure(n_clusters=3).fit(X_norm)
            silhouette_score = calculate_silhouette_score(X_norm, km.labels_)

        # Rata-rata per cluster
        for c in range(3):
            c_recs = [r for r in rfm_records if r.cluster == c]
            if c_recs:
                cluster_means[c]['r'] = round(sum(r.recency for r in c_recs) / len(c_recs), 1)
                cluster_means[c]['f'] = round(sum(r.frequency for r in c_recs) / len(c_recs), 1)
                cluster_means[c]['m'] = round(sum(float(r.monetary) for r in c_recs) / len(c_recs), 0)

    # HASIL SEGMENTASI & DISTRIBUSI
    loyal_count = SegmentasiHasil.query.filter_by(cluster=0).count()
    aktif_count = SegmentasiHasil.query.filter_by(cluster=1).count()
    nonaktif_count = SegmentasiHasil.query.filter_by(cluster=2).count()

    last_run = None
    latest_run_rec = SegmentasiHasil.query.order_by(SegmentasiHasil.tanggal_perhitungan.desc()).first()
    if latest_run_rec:
        last_run = latest_run_rec.tanggal_perhitungan

    return render_template(
        'segmentasi/analisis.html',
        periode=periode,
        show_elbow=show_elbow,
        total_p=total_p,
        total_t=total_t,
        has_rfm=has_rfm,
        has_kmeans=has_kmeans,
        rfm_records=rfm_records,
        avg_recency=avg_recency,
        avg_frequency=avg_frequency,
        avg_monetary=avg_monetary,
        rfm_normalized=rfm_normalized,
        norm_stats=norm_stats,
        elbow_res=elbow_res,
        silhouette_score=silhouette_score,
        cluster_means=cluster_means,
        loyal_count=loyal_count,
        aktif_count=aktif_count,
        nonaktif_count=nonaktif_count,
        last_run=last_run
    )


# Legacy route redirects to keep URLs working cleanly
@segmentasi_bp.route('/rfm')
@segmentasi_bp.route('/normalisasi')
@segmentasi_bp.route('/proses')
@segmentasi_bp.route('/hasil')
@segmentasi_bp.route('/ranking')
@segmentasi_bp.route('/strategi')
@login_required(roles=['admin', 'owner'])
def legacy_redirect():
    return redirect(url_for('segmentasi.analisis'))
