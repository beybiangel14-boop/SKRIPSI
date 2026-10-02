from fpdf import FPDF
from datetime import datetime

class PDFReport(FPDF):
    def __init__(self, title_text):
        super().__init__()
        self.title_text = title_text

    def header(self):
        # Judul Utama Formal
        self.set_font('helvetica', 'B', 12)
        self.set_text_color(33, 37, 41)
        self.cell(0, 6, self.title_text.upper(), ln=True, align='C')
        
        # Subjudul
        self.set_font('helvetica', '', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, 'Sistem Informasi Segmentasi Pelanggan Toko Agen Ikan Giling', ln=True, align='C')
        self.ln(2)
        
        # Garis Pembatas Header
        self.set_draw_color(33, 37, 41)
        self.set_line_width(0.4)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_line_width(0.2)
        self.ln(4)

    def footer(self):
        # Posisi 1.5 cm dari bawah
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f'Halaman {self.page_no()}/{{nb}} - Agen Ikan Giling Palembang', align='C')


def draw_section_bar(pdf, title):
    """Menggambar banner bagian dengan latar belakang abu-abu terang dan aksen garis biru di sisi kiri."""
    pdf.ln(2)
    curr_x = pdf.get_x()
    curr_y = pdf.get_y()
    
    # Background abu-abu lembut
    pdf.set_fill_color(241, 245, 249)
    pdf.rect(curr_x, curr_y, 190, 7.5, 'F')
    
    # Aksen bar biru di sisi kiri
    pdf.set_fill_color(13, 110, 253)
    pdf.rect(curr_x, curr_y, 3.5, 7.5, 'F')
    
    # Teks Bagian
    pdf.set_xy(curr_x + 6, curr_y + 1.2)
    pdf.set_font('helvetica', 'B', 8.5)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(180, 5, title, ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)


def generate_segmentasi_pdf(hasil_list, summary_data=None):
    pdf = PDFReport('Laporan Hasil Segmentasi Pelanggan')
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Metadata Ringkasan (Key-Value)
    if summary_data:
        pdf.set_font('helvetica', '', 8.5)
        meta_items = [
            ('Periode Data Transaksi', ': Semua Riwayat Transaksi'),
            ('Tanggal Cetak', f": {summary_data.get('tgl_cetak', datetime.now().strftime('%d-%m-%Y'))}"),
            ('Total Pelanggan', f": {summary_data.get('total_pelanggan', len(hasil_list))} Orang"),
            ('Total Transaksi', f": {summary_data.get('total_transaksi', '-')} Transaksi"),
            ('Total Omzet Penjualan', f": Rp {summary_data.get('total_omzet', 0):,.0f}"),
        ]
        
        for label, val in meta_items:
            pdf.set_font('helvetica', '', 8.5)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(50, 4.5, label, ln=False)
            pdf.set_font('helvetica', 'B', 8.5)
            pdf.set_text_color(33, 37, 41)
            pdf.cell(0, 4.5, val, ln=True)
        pdf.ln(2)

    # Bagian 1: Hasil Segmentasi Pelanggan
    draw_section_bar(pdf, 'Bagian 1: Hasil Segmentasi & Pengelompokan Pelanggan')
    
    # Header Tabel (Dark Slate/Charcoal dengan teks putih)
    pdf.set_font('helvetica', 'B', 8)
    pdf.set_fill_color(33, 37, 41) # Dark #212529
    pdf.set_text_color(255, 255, 255)
    pdf.set_draw_color(200, 205, 210)
    
    pdf.cell(8, 7.5, 'No', border=1, align='C', fill=True)
    pdf.cell(52, 7.5, 'Nama Pelanggan', border=1, align='L', fill=True)
    pdf.cell(24, 7.5, 'Recency', border=1, align='C', fill=True)
    pdf.cell(24, 7.5, 'Frequency', border=1, align='C', fill=True)
    pdf.cell(37, 7.5, 'Total Belanja (Rp)', border=1, align='R', fill=True)
    pdf.cell(15, 7.5, 'Cluster', border=1, align='C', fill=True)
    pdf.cell(30, 7.5, 'Status Segmentasi', border=1, align='C', fill=True)
    pdf.ln()
    
    # Isi Tabel
    pdf.set_font('helvetica', '', 8)
    pdf.set_text_color(30, 30, 30)
    
    for i, h in enumerate(hasil_list, 1):
        fill = (i % 2 == 0)
        pdf.set_fill_color(248, 250, 252)
        
        pdf.cell(8, 6.5, str(i), border=1, align='C', fill=fill)
        pdf.cell(52, 6.5, h.nama_pelanggan[:28], border=1, align='L', fill=fill)
        pdf.cell(24, 6.5, f"{h.recency} hari", border=1, align='C', fill=fill)
        pdf.cell(24, 6.5, f"{h.frequency} kali", border=1, align='C', fill=fill)
        pdf.cell(37, 6.5, f"Rp {h.monetary:,.0f}", border=1, align='R', fill=fill)
        pdf.cell(15, 6.5, f"C{h.cluster + 1}", border=1, align='C', fill=fill)
        pdf.cell(30, 6.5, h.segmentasi, border=1, align='C', fill=fill)
        pdf.ln()
        
    return pdf.output()


def generate_pelanggan_pdf(pelanggan_list):
    pdf = PDFReport('Laporan Data Pelanggan')
    pdf.alias_nb_pages()
    pdf.add_page()
    
    draw_section_bar(pdf, 'Bagian 1: Daftar Data Pelanggan')
    
    # Header Tabel
    pdf.set_font('helvetica', 'B', 8.5)
    pdf.set_fill_color(33, 37, 41)
    pdf.set_text_color(255, 255, 255)
    pdf.set_draw_color(200, 205, 210)
    
    pdf.cell(10, 7.5, 'No', border=1, align='C', fill=True)
    pdf.cell(50, 7.5, 'Nama Pelanggan', border=1, align='L', fill=True)
    pdf.cell(40, 7.5, 'Nomor HP', border=1, align='C', fill=True)
    pdf.cell(90, 7.5, 'Alamat', border=1, align='L', fill=True)
    pdf.ln()
    
    # Isi Tabel
    pdf.set_font('helvetica', '', 8.5)
    pdf.set_text_color(30, 30, 30)
    for i, p in enumerate(pelanggan_list, 1):
        alamat_singkat = p.alamat[:45] + '...' if len(p.alamat) > 45 else p.alamat
        fill = (i % 2 == 0)
        pdf.set_fill_color(248, 250, 252)
        
        pdf.cell(10, 6.5, str(i), border=1, align='C', fill=fill)
        pdf.cell(50, 6.5, p.nama_pelanggan[:26], border=1, align='L', fill=fill)
        pdf.cell(40, 6.5, p.nomor_hp, border=1, align='C', fill=fill)
        pdf.cell(90, 6.5, alamat_singkat, border=1, align='L', fill=fill)
        pdf.ln()
        
    return pdf.output()


def generate_transaksi_pdf(transaksi_list):
    pdf = PDFReport('Laporan Data Transaksi Penjualan')
    pdf.alias_nb_pages()
    pdf.add_page()
    
    draw_section_bar(pdf, 'Bagian 1: Riwayat Transaksi Penjualan')
    
    # Header Tabel
    pdf.set_font('helvetica', 'B', 8)
    pdf.set_fill_color(33, 37, 41)
    pdf.set_text_color(255, 255, 255)
    pdf.set_draw_color(200, 205, 210)
    
    pdf.cell(8, 7.5, 'No', border=1, align='C', fill=True)
    pdf.cell(24, 7.5, 'Tanggal', border=1, align='C', fill=True)
    pdf.cell(45, 7.5, 'Nama Pelanggan', border=1, align='L', fill=True)
    pdf.cell(20, 7.5, 'Vol (Kg)', border=1, align='R', fill=True)
    pdf.cell(30, 7.5, 'Harga/Kg', border=1, align='R', fill=True)
    pdf.cell(33, 7.5, 'Total Transaksi', border=1, align='R', fill=True)
    pdf.cell(30, 7.5, 'Metode Bayar', border=1, align='C', fill=True)
    pdf.ln()
    
    # Isi Tabel
    pdf.set_font('helvetica', '', 8)
    pdf.set_text_color(30, 30, 30)
    total_omzet = 0.0
    total_volume = 0.0
    
    for i, t in enumerate(transaksi_list, 1):
        fill = (i % 2 == 0)
        pdf.set_fill_color(248, 250, 252)
        
        total_omzet += float(t.total_transaksi)
        total_volume += float(t.jumlah_kg)
        
        t_date = t.tanggal_transaksi.strftime('%d-%m-%Y') if hasattr(t.tanggal_transaksi, 'strftime') else str(t.tanggal_transaksi)
        
        pdf.cell(8, 6.5, str(i), border=1, align='C', fill=fill)
        pdf.cell(24, 6.5, t_date, border=1, align='C', fill=fill)
        pdf.cell(45, 6.5, t.pelanggan.nama_pelanggan[:22], border=1, align='L', fill=fill)
        pdf.cell(20, 6.5, f"{t.jumlah_kg:,.2f}", border=1, align='R', fill=fill)
        pdf.cell(30, 6.5, f"Rp {t.harga_per_kg:,.0f}", border=1, align='R', fill=fill)
        pdf.cell(33, 6.5, f"Rp {t.total_transaksi:,.0f}", border=1, align='R', fill=fill)
        pdf.cell(30, 6.5, t.metode_pembayaran, border=1, align='C', fill=fill)
        pdf.ln()
        
    # Baris Total
    pdf.set_font('helvetica', 'B', 8)
    pdf.set_fill_color(235, 240, 245)
    pdf.cell(77, 7.5, 'TOTAL', border=1, align='C', fill=True)
    pdf.cell(20, 7.5, f"{total_volume:,.2f} Kg", border=1, align='R', fill=True)
    pdf.cell(30, 7.5, '', border=1, align='R', fill=True)
    pdf.cell(33, 7.5, f"Rp {total_omzet:,.0f}", border=1, align='R', fill=True)
    pdf.cell(30, 7.5, '', border=1, align='C', fill=True)
    pdf.ln()
    
    return pdf.output()


def generate_ranking_pdf(ranking_list):
    pdf = PDFReport('Laporan Ranking Pelanggan Prioritas')
    pdf.alias_nb_pages()
    pdf.add_page()
    
    draw_section_bar(pdf, 'Bagian 1: Leaderboard Prioritas Pelanggan')
    
    # Header Tabel
    pdf.set_font('helvetica', 'B', 8.5)
    pdf.set_fill_color(33, 37, 41)
    pdf.set_text_color(255, 255, 255)
    pdf.set_draw_color(200, 205, 210)
    
    pdf.cell(15, 7.5, 'Rank', border=1, align='C', fill=True)
    pdf.cell(65, 7.5, 'Nama Pelanggan', border=1, align='L', fill=True)
    pdf.cell(45, 7.5, 'Status Segmentasi', border=1, align='C', fill=True)
    pdf.cell(30, 7.5, 'Skor RFM', border=1, align='C', fill=True)
    pdf.cell(35, 7.5, 'Total Belanja (Rp)', border=1, align='R', fill=True)
    pdf.ln()
    
    # Isi Tabel
    pdf.set_font('helvetica', '', 8.5)
    pdf.set_text_color(30, 30, 30)
    for i, r in enumerate(ranking_list, 1):
        fill = (i % 2 == 0)
        pdf.set_fill_color(248, 250, 252)
        
        rank_text = f"#{i}"
        
        pdf.cell(15, 6.5, rank_text, border=1, align='C', fill=fill)
        pdf.cell(65, 6.5, r.nama_pelanggan[:32], border=1, align='L', fill=fill)
        pdf.cell(45, 6.5, r.segmentasi, border=1, align='C', fill=fill)
        pdf.cell(30, 6.5, f"{r.score_rfm:.2f}", border=1, align='C', fill=fill)
        pdf.cell(35, 6.5, f"Rp {r.monetary:,.0f}", border=1, align='R', fill=fill)
        pdf.ln()
        
    return pdf.output()

