"""
Penyimpanan & pemuatan artefak model K-Means.

PENYIMPANAN UTAMA: payload artefak disimpan di tabel `ml_artifact` (database),
sehingga model tetap tersedia di hosting dengan filesystem read-only/ephemeral.
Registry metadata tetap di `ml_models` (satu model aktif pada satu waktu).

Kompatibilitas mundur: artefak lama berbentuk file (models_ml/model_v1.json
... model_v6.json) tetap dimuat sebagai fallback bila payload DB tidak ada.

Alur:
  fit_model() dari core_ml -> save_model() -> baris ml_artifact + baris ml_models
  Flask (skoring)          -> load_active_model() -> score_with_model()
  Retrain                  -> fit_model() lagi -> save_model() versi berikutnya
  (opsional) export_json=True -> salinan models_ml/model_v{N}.json sebagai lampiran bukti
"""
import json
import os
from datetime import datetime

from utils.db import db
from models import MlModel, MlArtifact

# Folder salinan JSON opsional (hanya ditulis bila export_json=True)
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models_ml')


def save_model(artifact, alasan='manual', export_json=False):
    """
    Simpan artefak sebagai versi baru, nonaktifkan versi lama, tandai versi ini aktif.

    Payload SELALU disimpan ke tabel ml_artifact (database). Jika export_json=True,
    salinan JSON juga ditulis ke models_ml/model_v{N}.json sebagai lampiran bukti
    (dipakai notebook eksperimen; sistem Flask TIDAK menulis file).

    Mengembalikan (versi: int, file_path: str). Membutuhkan app context (db session).
    """
    last = MlModel.query.order_by(MlModel.versi.desc()).first()
    versi = (last.versi + 1) if last else 1

    artifact = dict(artifact)
    artifact['versi'] = versi
    artifact['disimpan_pada'] = datetime.utcnow().isoformat(timespec='seconds')
    payload = json.dumps(artifact, ensure_ascii=False, indent=2)

    # Salinan file HANYA bila diminta eksplisit — default: tidak ada file baru
    rel_path = ''
    if export_json:
        os.makedirs(MODEL_DIR, exist_ok=True)
        filename = f'model_v{versi}.json'
        abs_path = os.path.join(MODEL_DIR, filename)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(payload)
        rel_path = os.path.join('models_ml', filename)

    # Satu model aktif: nonaktifkan semua, aktifkan yang baru
    MlModel.query.update({MlModel.is_active: False})
    db.session.add(MlArtifact(versi=versi, artifact_json=payload))
    db.session.add(MlModel(
        versi=versi,
        file_path=rel_path,
        is_active=True,
        tanggal_latih=datetime.utcnow(),
        n_samples=artifact.get('n_samples', 0),
        k=artifact.get('k', 3),
        silhouette=artifact.get('metrics', {}).get('silhouette', 0.0),
        alasan=alasan,
        threshold_snapshot=json.dumps(artifact.get('thresholds', {})),
    ))
    db.session.commit()

    return versi, rel_path


def load_active_model():
    """
    Muat artefak model aktif.

    Urutan baca: (1) tabel ml_artifact — penyimpanan utama;
    (2) file JSON lama di models_ml/ — fallback kompatibilitas mundur.

    Mengembalikan (artifact: dict | None, row: MlModel | None).
    Jika payload tidak tersedia sama sekali, model dianggap tidak ada (None, row).
    """
    row = MlModel.query.filter_by(is_active=True).order_by(MlModel.versi.desc()).first()
    if not row:
        return None, None

    # 1) Payload dari database
    art_row = db.session.get(MlArtifact, row.versi)
    if art_row is not None:
        try:
            return json.loads(art_row.artifact_json), row
        except json.JSONDecodeError:
            pass  # payload rusak -> coba fallback file di bawah

    # 2) Fallback: artefak lama berbentuk file (model_v1..v6.json)
    if row.file_path:
        abs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), row.file_path)
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                return json.load(f), row
        except (OSError, json.JSONDecodeError):
            pass

    return None, row


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
