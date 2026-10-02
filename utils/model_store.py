"""
Penyimpanan & pemuatan artefak model K-Means (JSON) + registry di tabel ml_models.

Artefak ditulis ke folder models_ml/model_v{N}.json dan dicatat ke database
dengan satu model berstatus aktif pada satu waktu.

Alur:
  fit_model() dari core_ml -> save_model() -> models_ml/model_v1.json + baris MlModel
  Flask (skoring)          -> load_active_model() -> score_with_model()
  Retrain                  -> fit_model() lagi -> save_model() versi berikutnya
"""
import json
import os
from datetime import datetime

from utils.db import db
from models import MlModel

# Folder artefak model, terletak di root aplikasi (selevel app.py)
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models_ml')


def save_model(artifact, alasan='manual'):
    """
    Simpan artefak sebagai versi baru, nonaktifkan versi lama, tandai versi ini aktif.

    Mengembalikan (versi: int, file_path: str). Membutuhkan app context (db session).
    """
    os.makedirs(MODEL_DIR, exist_ok=True)

    last = MlModel.query.order_by(MlModel.versi.desc()).first()
    versi = (last.versi + 1) if last else 1

    filename = f'model_v{versi}.json'
    abs_path = os.path.join(MODEL_DIR, filename)

    artifact = dict(artifact)
    artifact['versi'] = versi
    artifact['disimpan_pada'] = datetime.utcnow().isoformat(timespec='seconds')

    with open(abs_path, 'w', encoding='utf-8') as f:
        json.dump(artifact, f, ensure_ascii=False, indent=2)

    # Satu model aktif: nonaktifkan semua, aktifkan yang baru
    MlModel.query.update({MlModel.is_active: False})
    rel_path = os.path.join('models_ml', filename)
    row = MlModel(
        versi=versi,
        file_path=rel_path,
        is_active=True,
        tanggal_latih=datetime.utcnow(),
        n_samples=artifact.get('n_samples', 0),
        k=artifact.get('k', 3),
        silhouette=artifact.get('metrics', {}).get('silhouette', 0.0),
        alasan=alasan,
        threshold_snapshot=json.dumps(artifact.get('thresholds', {})),
    )
    db.session.add(row)
    db.session.commit()

    return versi, rel_path


def load_active_model():
    """
    Muat artefak model aktif.

    Mengembalikan (artifact: dict | None, row: MlModel | None).
    Jika file hilang/tidak terbaca, model dianggap tidak ada (None, row).
    """
    row = MlModel.query.filter_by(is_active=True).order_by(MlModel.versi.desc()).first()
    if not row:
        return None, None

    abs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), row.file_path)
    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            artifact = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None, row

    return artifact, row


def model_info_dict(row):
    """Ringkasan model untuk ditampilkan ke template (aman untuk Jinja)."""
    if not row:
        return None
    return {
        'versi': row.versi,
        'tanggal_latih': row.tanggal_latih,
        'n_samples': row.n_samples,
        'k': row.k,
        'silhouette': float(row.silhouette) if row.silhouette is not None else None,
        'alasan': row.alasan,
    }
