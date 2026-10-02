from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from controllers.auth import login_required
from models import Pelanggan, Transaksi, SegmentasiHasil, SegmentasiRiwayat
from utils.db import db
from utils.core_ml import (
    calculate_rfm, MinMaxScalerPure,
    calculate_elbow_method, fit_model, score_with_model, check_retrain
)
from utils.model_store import save_model, load_active_model, model_info_dict
from datetime import datetime, timedelta

segmentasi_bp = Blueprint('segmentasi', __name__, url_prefix='/segmentasi')


def _simpan_snapshot(rfm_results, model_versi):
    """Simpan snapshot hasil clustering ke tabel riwayat (satu batch = satu waktu)."""
    ts = datetime.utcnow()
    for item in rfm_results:
        if item.get('cluster', -1) != -1:
            db.session.add(SegmentasiRiwayat(
                pelanggan_id=item['id'],
                cluster=item['cluster'],
                segmentasi=item['segmentasi'],
                model_versi=model_versi,
                tanggal_snapshot=ts,
            ))


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

                # Upsert: perbarui baris yang ada, tambahkan yang baru.
                # TIDAK menghapus seluruh hasil lama agar riwayat & model tetap valid.
                existing = {r.pelanggan_id: r for r in SegmentasiHasil.query.all()}
                for item in rfm_results:
                    rec = existing.get(item['id'])
                    if rec:
                        rec.recency = item['recency']
                        rec.frequency = item['frequency']
                        rec.monetary = item['monetary']
                        rec.score_rfm = item['score_rfm']
                        rec.tanggal_perhitungan = datetime.utcnow()
                    else:
                        db.session.add(SegmentasiHasil(
                            pelanggan_id=item['id'],
                            recency=item['recency'],
                            frequency=item['frequency'],
                            monetary=item['monetary'],
                            score_rfm=item['score_rfm'],
                            cluster=-1,
                            segmentasi='Belum Dicluster',
                            tanggal_perhitungan=datetime.utcnow(),
                        ))
                # Data RFM berubah -> label cluster lama tidak berlaku, wajib skoring ulang
                SegmentasiHasil.query.update({
                    SegmentasiHasil.cluster: -1,
                    SegmentasiHasil.segmentasi: 'Belum Dicluster',
                })
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

                # Skoring memakai model tersimpan; jika belum ada -> training model pertama
                artifact, model_row = load_active_model()
                if artifact is None:
                    artifact = fit_model(rfm_list, alasan='pertama_kali')
                    versi, _ = save_model(artifact, alasan='pertama_kali')
                    flash(f'Model pertama (v{versi}) berhasil dilatih & disimpan!', 'success')
                else:
                    versi = model_row.versi
                    flash('Pelanggan berhasil di-skoring menggunakan model tersimpan!', 'success')

                clustered_results = score_with_model(rfm_list, artifact)

                for item in clustered_results:
                    hasil_db = SegmentasiHasil.query.filter_by(pelanggan_id=item['id']).first()
                    if hasil_db:
                        hasil_db.cluster = item['cluster']
                        hasil_db.segmentasi = item['segmentasi']
                        hasil_db.tanggal_perhitungan = datetime.utcnow()

                _simpan_snapshot(clustered_results, versi)
                db.session.commit()
                flash('Proses Clustering K-Means berhasil diselesaikan!', 'success')
                return redirect(url_for('segmentasi.analisis', periode=periode, show_elbow=1 if show_elbow else 0))

            except Exception as e:
                db.session.rollback()
                flash(f'Terjadi kesalahan saat memproses K-Means: {e}', 'danger')

        elif action == 'retrain':
            if session.get('role') != 'admin':
                flash('Hanya Operator yang dapat melakukan retrain model.', 'danger')
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

                # Retrain: fit ulang model dari data terkini (scaler + sentroid baru)
                old_artifact, _ = load_active_model()
                perlu, alasan, _info = check_retrain(old_artifact, rfm_list)
                alasan_simpan = 'threshold' if perlu else 'manual'

                artifact = fit_model(rfm_list, alasan=alasan_simpan)
                versi, _ = save_model(artifact, alasan=alasan_simpan)

                clustered_results = score_with_model(rfm_list, artifact)
                for item in clustered_results:
                    hasil_db = SegmentasiHasil.query.filter_by(pelanggan_id=item['id']).first()
                    if hasil_db:
                        hasil_db.cluster = item['cluster']
                        hasil_db.segmentasi = item['segmentasi']
                        hasil_db.tanggal_perhitungan = datetime.utcnow()

                _simpan_snapshot(clustered_results, versi)
                db.session.commit()

                sil = artifact.get('metrics', {}).get('silhouette', 0.0)
                flash(f'Model v{versi} berhasil dilatih ulang (Silhouette: {sil:.4f}, alasan: {alasan_simpan})!', 'success')
                return redirect(url_for('segmentasi.analisis', periode=periode, show_elbow=1 if show_elbow else 0))

            except Exception as e:
                db.session.rollback()
                flash(f'Terjadi kesalahan saat retrain model: {e}', 'danger')

    # Fetch RFM DB records
    rfm_records = SegmentasiHasil.query.join(Pelanggan).order_by(Pelanggan.nama_pelanggan).all()
    has_rfm = len(rfm_records) > 0
    has_kmeans = SegmentasiHasil.query.filter(SegmentasiHasil.cluster != -1).count() > 0

    # Model aktif (artefak + registry)
    active_artifact, active_row = load_active_model()
    model_info = model_info_dict(active_row)

    # LANGKAH 2 Data (RFM Metrics)
    avg_recency = 0
    avg_frequency = 0
    avg_monetary = 0
    if has_rfm:
        avg_recency = round(sum(r.recency for r in rfm_records) / len(rfm_records), 1)
        avg_frequency = round(sum(r.frequency for r in rfm_records) / len(rfm_records), 1)
        avg_monetary = round(sum(float(r.monetary) for r in rfm_records) / len(rfm_records), 0)

    # LANGKAH 3 Data (Normalisasi Data RFM)
    # Skala yang ditampilkan = skala yang DIPAKAI clustering:
    #   - jika model aktif ada -> pakai scaler artefak (pasti konsisten dengan sentroid)
    #   - jika belum ada model -> fit dari pelanggan bertransaksi (pelanggan tanpa transaksi dikecualikan,
    #     konsisten dengan core_ml yang hanya meng-cluster pelanggan frequency > 0)
    rfm_normalized = []
    norm_stats = {'r_min': 0, 'r_max': 0, 'f_min': 0, 'f_max': 0, 'm_min': 0, 'm_max': 0}
    norm_from_model = False

    if has_rfm:
        clustered_recs = [r for r in rfm_records if r.frequency > 0]

        if active_artifact and active_artifact.get('scaler'):
            sp = active_artifact['scaler']
            norm_stats = {
                'r_min': sp['r']['min'], 'r_max': sp['r']['max'],
                'f_min': sp['f']['min'], 'f_max': sp['f']['max'],
                'm_min': sp['m']['min'], 'm_max': sp['m']['max'],
            }
            norm_from_model = True
        elif clustered_recs:
            scaler_r = MinMaxScalerPure().fit([float(r.recency) for r in clustered_recs])
            scaler_f = MinMaxScalerPure().fit([float(r.frequency) for r in clustered_recs])
            scaler_m = MinMaxScalerPure().fit([float(r.monetary) for r in clustered_recs])
            norm_stats = {
                'r_min': scaler_r.min_val, 'r_max': scaler_r.max_val,
                'f_min': scaler_f.min_val, 'f_max': scaler_f.max_val,
                'm_min': scaler_m.min_val, 'm_max': scaler_m.max_val,
            }

        r_diff = (norm_stats['r_max'] - norm_stats['r_min']) or 1.0
        f_diff = (norm_stats['f_max'] - norm_stats['f_min']) or 1.0
        m_diff = (norm_stats['m_max'] - norm_stats['m_min']) or 1.0

        for r in clustered_recs:
            r_norm = (float(r.recency) - norm_stats['r_min']) / r_diff
            f_norm = (float(r.frequency) - norm_stats['f_min']) / f_diff
            m_norm = (float(r.monetary) - norm_stats['m_min']) / m_diff
            rfm_normalized.append({
                'pelanggan_id': r.pelanggan_id,
                'nama_pelanggan': r.pelanggan.nama_pelanggan,
                'recency': r.recency,
                'frequency': r.frequency,
                'monetary': float(r.monetary),
                'r_norm': round(r_norm, 4),
                'f_norm': round(f_norm, 4),
                'm_norm': round(m_norm, 4),
                'num_r': float(r.recency) - norm_stats['r_min'],
                'r_diff': r_diff,
                'num_f': float(r.frequency) - norm_stats['f_min'],
                'f_diff': f_diff,
                'num_m': float(r.monetary) - norm_stats['m_min'],
                'm_diff': m_diff,
            })

    # Data RFM sebagai dict (untuk Elbow on-demand & evaluasi retrain)
    rfm_list_dict = [{
        'recency': r.recency,
        'frequency': r.frequency,
        'monetary': float(r.monetary)
    } for r in rfm_records] if has_rfm else []

    # LANGKAH 4 Data (Elbow Method)
    # Prioritas: metrik tersimpan di artefak model (tanpa komputasi ulang per render).
    # Jika belum ada model dan user menekan tombol Elbow -> hitung on-demand sekali.
    elbow_res = None
    if active_artifact and (active_artifact.get('metrics') or {}).get('elbow'):
        elbow_res = active_artifact['metrics']['elbow']
    elif show_elbow and has_rfm:
        elbow_res = calculate_elbow_method(rfm_list_dict, max_k=6)

    # LANGKAH 5 Data (K-Means & Silhouette Score)
    # Silhouette diambil dari artefak (dihitung saat training), bukan dihitung ulang tiap render.
    silhouette_score = 0.0
    if active_artifact and (active_artifact.get('metrics') or {}).get('silhouette'):
        silhouette_score = active_artifact['metrics']['silhouette']

    cluster_means = {0: {'r': 0, 'f': 0, 'm': 0}, 1: {'r': 0, 'f': 0, 'm': 0}, 2: {'r': 0, 'f': 0, 'm': 0}}
    if has_kmeans:
        for c in range(3):
            c_recs = [r for r in rfm_records if r.cluster == c]
            if c_recs:
                cluster_means[c]['r'] = round(sum(r.recency for r in c_recs) / len(c_recs), 1)
                cluster_means[c]['f'] = round(sum(r.frequency for r in c_recs) / len(c_recs), 1)
                cluster_means[c]['m'] = round(sum(float(r.monetary) for r in c_recs) / len(c_recs), 0)

    # Evaluasi ambang batas retrain
    retrain_perlu = False
    retrain_alasan = []
    retrain_info = {}
    if active_artifact and has_rfm:
        retrain_perlu, retrain_alasan, retrain_info = check_retrain(active_artifact, rfm_list_dict)

    # Riwayat snapshot & migrasi segmen (dibandingkan 2 batch snapshot terakhir)
    snapshot_history = []
    migrasi_list = []
    ts_list = [row[0] for row in db.session.query(SegmentasiRiwayat.tanggal_snapshot).distinct()
               .order_by(SegmentasiRiwayat.tanggal_snapshot.desc()).limit(10).all()]
    if ts_list:
        for ts in ts_list:
            rows = SegmentasiRiwayat.query.filter_by(tanggal_snapshot=ts).all()
            counts = {0: 0, 1: 0, 2: 0}
            for r in rows:
                counts[r.cluster] = counts.get(r.cluster, 0) + 1
            snapshot_history.append({
                'tanggal': ts,
                'versi': rows[0].model_versi if rows else None,
                'total': len(rows),
                'c0': counts[0], 'c1': counts[1], 'c2': counts[2],
            })

        if len(ts_list) >= 2:
            latest_rows = SegmentasiRiwayat.query.filter_by(tanggal_snapshot=ts_list[0]).all()
            prev_rows = SegmentasiRiwayat.query.filter_by(tanggal_snapshot=ts_list[1]).all()
            prev_map = {r.pelanggan_id: r.cluster for r in prev_rows}
            for r in latest_rows:
                old = prev_map.get(r.pelanggan_id)
                if old is not None and old != r.cluster:
                    migrasi_list.append({
                        'nama': r.pelanggan.nama_pelanggan if r.pelanggan else '-',
                        'dari': old,
                        'ke': r.cluster,
                    })

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
        norm_from_model=norm_from_model,
        elbow_res=elbow_res,
        silhouette_score=silhouette_score,
        cluster_means=cluster_means,
        loyal_count=loyal_count,
        aktif_count=aktif_count,
        nonaktif_count=nonaktif_count,
        last_run=last_run,
        model_info=model_info,
        retrain_perlu=retrain_perlu,
        retrain_alasan=retrain_alasan,
        retrain_info=retrain_info,
        snapshot_history=snapshot_history,
        migrasi_list=migrasi_list,
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
