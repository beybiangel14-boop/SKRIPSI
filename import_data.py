import csv
import sys
from datetime import datetime
from app import app
from models import Pelanggan, Transaksi
from utils.db import db

def parse_date(date_str):
    # Mencoba beberapa format tanggal yang umum digunakan di Excel
    for fmt in ('%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y'):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Format tanggal tidak dikenali: {date_str}")

def import_csv(csv_filepath):
    print(f"[*] Memulai import data dari file: {csv_filepath}")
    
    with app.app_context():
        try:
            with open(csv_filepath, mode='r', encoding='utf-8-sig') as f:
                # Membaca sampel file untuk mendeteksi delimiter secara otomatis (koma atau titik koma)
                sample = f.read(2048)
                f.seek(0)
                
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
                except Exception:
                    # Jika gagal mendeteksi, gunakan koma sebagai default
                    class DefaultDialect(csv.excel):
                        delimiter = ','
                    dialect = DefaultDialect
                
                reader = csv.DictReader(f, dialect=dialect)
                
                # Dapatkan header kolom
                headers = reader.fieldnames
                if not headers:
                    print("[!] File CSV kosong atau tidak memiliki header.")
                    return
                    
                print(f"[*] Kolom terdeteksi: {headers}")
                
                # Map nama kolom secara fleksibel (case-insensitive & pencocokan kata kunci)
                col_name_map = {}
                for h in headers:
                    h_clean = h.strip().lower()
                    if 'nama' in h_clean and 'pelanggan' in h_clean:
                        col_name_map['nama'] = h
                    elif 'tanggal' in h_clean:
                        col_name_map['tanggal'] = h
                    elif 'berat' in h_clean:
                        col_name_map['berat'] = h
                    elif 'harga' in h_clean:
                        col_name_map['harga'] = h
                    elif 'total' in h_clean or 'bayar' in h_clean:
                        col_name_map['total'] = h

                # Validasi kolom wajib minimal
                required_keys = ['nama', 'tanggal', 'berat', 'harga']
                missing_keys = [k for k in required_keys if k not in col_name_map]
                if missing_keys:
                    print(f"[!] Gagal: Kolom berikut tidak ditemukan di CSV: {missing_keys}")
                    print("[*] Pastikan header CSV memiliki kolom dengan kata kunci: 'Nama Pelanggan', 'Tanggal Transaksi', 'Berat', 'Harga'")
                    return
                
                count_pelanggan_baru = 0
                count_transaksi = 0
                
                for idx, row in enumerate(reader, start=2):
                    nama_val = row[col_name_map['nama']].strip()
                    if not nama_val:
                        continue # Skip baris kosong
                    
                    # 1. Cari atau buat Pelanggan (untuk menghindari duplikasi jika nama sudah ada)
                    pelanggan = Pelanggan.query.filter_by(nama_pelanggan=nama_val).first()
                    if not pelanggan:
                        pelanggan = Pelanggan(
                            nama_pelanggan=nama_val,
                            nomor_hp='-',
                            alamat='-'
                        )
                        db.session.add(pelanggan)
                        db.session.flush() # Mendapatkan ID pelanggan agar bisa langsung dipakai untuk transaksi
                        count_pelanggan_baru += 1
                        print(f"[+] Menambahkan pelanggan baru: {nama_val}")
                    
                    # 2. Ambil dan bersihkan data transaksi
                    tanggal_str = row[col_name_map['tanggal']]
                    
                    # Bersihkan angka dari karakter Rp, titik ribuan, atau spasi
                    berat_str = row[col_name_map['berat']].replace('Rp', '').replace(' ', '').strip()
                    harga_str = row[col_name_map['harga']].replace('Rp', '').replace(' ', '').strip()
                    
                    # Mengatasi format desimal Indonesia (koma) menjadi titik untuk float python
                    if ',' in berat_str and '.' not in berat_str:
                        berat_str = berat_str.replace(',', '.')
                    elif '.' in berat_str and ',' in berat_str:
                        # Kasus seperti 1.000,50 -> hilangkan titik ribuan, ganti koma dengan titik desimal
                        berat_str = berat_str.replace('.', '').replace(',', '.')
                        
                    if ',' in harga_str and '.' not in harga_str:
                        harga_str = harga_str.replace(',', '.')
                    elif '.' in harga_str and ',' in harga_str:
                        harga_str = harga_str.replace('.', '').replace(',', '.')

                    # Hapus titik ribuan murni (misal 27.000 menjadi 27000)
                    if '.' in harga_str and len(harga_str.split('.')[-1]) == 3:
                        harga_str = harga_str.replace('.', '')
                    if '.' in berat_str and len(berat_str.split('.')[-1]) == 3:
                        # Jaga-jaga jika berat diinput ribuan tanpa koma desimal
                        berat_str = berat_str.replace('.', '')
                    
                    # Cari total bayar jika ada di kolom
                    total_str = None
                    if 'total' in col_name_map:
                        total_str = row[col_name_map['total']].replace('Rp', '').replace(' ', '').strip()
                        if ',' in total_str and '.' not in total_str:
                            total_str = total_str.replace(',', '.')
                        elif '.' in total_str and ',' in total_str:
                            total_str = total_str.replace('.', '').replace(',', '.')
                        if '.' in total_str and len(total_str.split('.')[-1]) == 3:
                            total_str = total_str.replace('.', '')
                    
                    try:
                        tanggal_transaksi = parse_date(tanggal_str)
                        jumlah_kg = float(berat_str)
                        harga_per_kg = float(harga_str)
                        
                        transaksi_baru = Transaksi(
                            tanggal_transaksi=tanggal_transaksi,
                            pelanggan_id=pelanggan.id,
                            jumlah_kg=jumlah_kg,
                            harga_per_kg=harga_per_kg,
                            metode_pembayaran='Tunai' # Set default ke 'Tunai'
                        )
                        
                        if total_str:
                            transaksi_baru.total_transaksi = float(total_str)
                        else:
                            transaksi_baru.calculate_total()
                            
                        db.session.add(transaksi_baru)
                        count_transaksi += 1
                    except Exception as row_err:
                        print(f"[!] Baris {idx} ({nama_val}): Gagal memasukkan transaksi ({row_err})")
                        continue
                
                db.session.commit()
                print("\n[*] Proses Impor Selesai!")
                print(f"    - Pelanggan baru ditambahkan: {count_pelanggan_baru}")
                print(f"    - Transaksi berhasil diinput : {count_transaksi}")
                
        except FileNotFoundError:
            print(f"[!] Gagal: File '{csv_filepath}' tidak ditemukan.")
        except Exception as e:
            db.session.rollback()
            print(f"[!] Terjadi kesalahan umum: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Penggunaan: python import_data.py <nama_file_csv>")
        sys.exit(1)
        
    csv_file = sys.argv[1]
    import_csv(csv_file)
