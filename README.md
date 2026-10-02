# Sistem Segmentasi Pelanggan — RFM + K-Means

Aplikasi web Flask untuk segmentasi pelanggan metode **RFM + K-Means**
(skripsi Safira Azzahra — 2220803049).

## Menjalankan Sistem

### Dengan uv (disarankan)

```bash
uv sync                      # install dependensi runtime saja (20 paket)
uv run python app.py         # jalankan server -> http://127.0.0.1:5000
```

> Catatan: `main.py` tidak ada — entry point sistem adalah **`app.py`**.
> Bila perintah `uv` tidak dikenal, buka terminal baru (PATH belum ter-refresh)
> atau pakai path lengkap `%USERPROFILE%\.local\bin\uv.exe`.

### Dengan venv biasa

```bash
.\venv\Scripts\python.exe app.py
```

## Perintah Lain

```bash
uv run python scratch\blackbox_testing.py   # Black Box Testing (27 test case)
uv sync --group dev                         # install dependensi notebook/dokumen
                                            # (ipykernel, matplotlib, pandas, python-docx)
```

> `uv run` tidak menghapus paket grup dev, tetapi **`uv sync` (tanpa argumen)
> mengembalikan environment ke runtime-saja** — jalankan `uv sync --group dev`
> lagi kapan pun Anda hendak mengerjakan notebook.

- Login: `admin/admin123` (Operator), `owner/owner123` (baca saja).
- Notebook eksperimen: `notebooks/eksperimen_segmentasi.ipynb`
  (jalankan dengan kernel `.venv` setelah `uv sync --group dev`).

## Penyimpanan Model (penting)

| Komponen | Lokasi | Keterangan |
|---|---|---|
| **Payload artefak model** | Tabel **`ml_artifact`** (MySQL) | Sumber utama — tidak bergantung filesystem, aman untuk hosting read-only/ephemeral |
| Registry metadata | Tabel `ml_models` | Versi, Silhouette, alasan retrain, satu model aktif |
| Salinan JSON (opsional) | `models_ml/model_v{N}.json` | Hanya dibuat eksplisit via `save_model(..., export_json=True)` dari notebook — sebagai lampiran bukti |
| Artefak lama v1–v6 | `models_ml/*.json` | Dibaca sebagai **fallback** kompatibilitas mundur |

Alur: notebook/flask melatih (`utils/core_ml.py`) → `save_model()` → payload ke
database → Flask skoring (`load_active_model()` → `score_with_model()`).
Retrain otomatis mengikuti ambang batas (data baru ≥10%, Silhouette <0.35,
drift ≥10%, umur >90 hari).

## Struktur Ringkas

```
app.py                  # entry point
controllers/            # route (auth, pelanggan, transaksi, segmentasi, laporan, ...)
models.py               # tabel SQLAlchemy (pelanggan, transaksi, hasil, riwayat, ml_models, ml_artifact)
utils/core_ml.py        # RFM, MinMax, Elbow, K-Means, cek retrain (pure Python, single source)
utils/model_store.py    # simpan/muat artefak model (database)
notebooks/              # eksperimen & evaluasi angka (identik dengan runtime)
scratch/blackbox_testing.py
models_ml/              # salinan JSON opsional + artefak lama v1-v6
```

## Testing

```bash
uv run python scratch\blackbox_testing.py
# RINGKASAN: 27 LULUS / 0 GAGAL dari 27 test case
```
