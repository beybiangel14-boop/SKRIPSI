"""Black Box Testing - Sistem Segmentasi Pelanggan (RFM + K-Means Flask).

Menjalankan pengujian fungsional end-to-end via Flask test client
(fitur admin & owner, alur langkah 1-5, retrain, laporan).

Jalankan:  venv\\Scripts\\python.exe scratch\\blackbox_testing.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import app  # noqa: E402

HASIL = []


def check(nomor, nama, kondisi, detail=""):
    status = "LULUS" if kondisi else "GAGAL"
    HASIL.append((nomor, nama, status, detail))
    print(f"[{status}] TC{nomor:02d} - {nama}" + (f" ({detail})" if detail and not kondisi else ""))


def client_login(username, password):
    c = app.test_client()
    r = c.post("/login", data={"username": username, "password": password}, follow_redirects=True)
    return c, r


def main():
    # --- TC01-TC03: Autentikasi ---
    c, r = client_login("admin", "admin123")
    check(1, "Login admin berhasil", r.status_code == 200 and "Dashboard" in r.get_data(as_text=True))

    c2 = app.test_client()
    r = c2.post("/login", data={"username": "admin", "password": "salah"}, follow_redirects=True)
    check(2, "Login password salah ditolak", "tidak valid" in r.get_data(as_text=True) or r.request.path == "/login")

    c3 = app.test_client()
    r = c3.get("/segmentasi/", follow_redirects=True)
    check(3, "Akses tanpa login dialihkan ke login", "/login" in str(r.request.path) or "login" in r.get_data(as_text=True).lower())

    # --- TC04-TC06: Halaman utama & role ---
    r = c.get("/segmentasi/")
    html = r.get_data(as_text=True)
    check(4, "Halaman analisis terbuka (admin)", r.status_code == 200 and "LANGKAH 1" in html)
    check(5, "Kartu status model tampil di Langkah 5", "Status Model K-Means" in html)

    co, _ = client_login("owner", "owner123")
    h_o = co.get("/segmentasi/").get_data(as_text=True)
    check(6, "Owner tidak melihat tombol retrain", "Retrain Model Sekarang" not in h_o and "Latih Model" not in h_o)

    # --- TC07-TC09: Kartu Dataset (semua data, tanpa filter waktu) ---
    r = c.get("/segmentasi/")
    html = r.get_data(as_text=True)
    check(7, "Langkah 1 = kartu Dataset (semua data)",
          "Semua Data Transaksi" in html and "tanpa filter waktu" in html and "Rentang Tanggal Data" in html)

    check(8, "Form filter periode sudah dihapus", '<select name="periode"' not in html)

    r = c.get("/segmentasi/?periode=30_hari")  # parameter lama diabaikan dengan aman
    h = r.get_data(as_text=True)
    check(9, "Parameter lama ?periode diabaikan dengan aman",
          r.status_code == 200 and "Rentang Tanggal Data" in h)

    # --- TC10-TC14: Langkah 1-5 (alur admin) ---
    def post(action):
        return c.post("/segmentasi/", data={"action": action}, follow_redirects=True)

    r = post("hitung_rfm")
    h = r.get_data(as_text=True)
    check(10, "Langkah 2: Hitung RFM (upsert, data utuh)",
          ("dihitung ulang" in h or "berhasil dihitung" in h) and "Tabel Hasil Perhitungan RFM" in h)

    r = post("jalankan_elbow")
    h = r.get_data(as_text=True)
    check(11, "Langkah 4: Grafik Elbow ditampilkan (jujur)", "Grafik Elbow Method ditampilkan" in h and "elbowChart" in h)

    r = post("jalankan_kmeans")
    h = r.get_data(as_text=True)
    check(12, "Langkah 5: Clustering K-Means dijalankan",
          "Clustering K-Means selesai" in h and "Tabel Klasifikasi Segmentasi Pelanggan" in h)

    h = c.get("/segmentasi/").get_data(as_text=True)
    check(13, "Normalisasi (Langkah 3) memakai skala model", "Skala dari model aktif" in h)
    check(14, "Tabel riwayat snapshot & migrasi segmen tampil", "Riwayat Snapshot" in h and "Migrasi Segmen" in h)

    # --- TC15-TC17: Retrain & model ---
    r = post("retrain")
    h = r.get_data(as_text=True)
    check(15, "Retrain manual berhasil", "berhasil dilatih ulang" in h)

    from utils.model_store import load_active_model
    with app.app_context():
        art, row = load_active_model()
    check(16, "Artefak model aktif termuat dari JSON", art is not None and art.get("centroids") and row is not None,
          f"versi={getattr(row, 'versi', None)}")
    check(17, "Ambang batas retrain terpenuhi (sehat)", "semua ambang batas retrain" in h)

    # --- TC18-TC20: Halaman lain ---
    for i, path in enumerate(("/pelanggan/", "/transaksi/", "/laporan/"), start=18):
        rr = c.get(path)
        check(i, f"Halaman {path} terbuka", rr.status_code == 200)

    # --- TC21: Owner akses halaman analisis (baca saja) ---
    r = co.get("/segmentasi/")
    check(21, "Owner dapat melihat halaman analisis", r.status_code == 200)

    # --- TC22: Owner ditolak aksi admin ---
    r = co.post("/segmentasi/", data={"action": "retrain"}, follow_redirects=True)
    h = r.get_data(as_text=True)
    check(22, "Owner ditolak aksi retrain", "Hanya Operator" in h)

    # --- TC23: Auto-rescore — Hitung RFM tidak menghapus hasil segmentasi ---
    r = post("hitung_rfm")
    h = r.get_data(as_text=True)
    check(23, "Hitung RFM: hasil segmentasi TIDAK hilang (auto-rescore)",
          "di-skoring ulang dengan Model v" in h and "Tabel Klasifikasi Segmentasi Pelanggan" in h)

    # --- Ringkasan ---
    lulus = sum(1 for x in HASIL if x[2] == "LULUS")
    gagal = len(HASIL) - lulus
    print("\n" + "=" * 60)
    print(f"RINGKASAN: {lulus} LULUS / {gagal} GAGAL dari {len(HASIL)} test case")
    print("=" * 60)
    for nomor, nama, status, detail in HASIL:
        if status == "GAGAL":
            print(f"  GAGAL TC{nomor:02d}: {nama} {detail}")
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
