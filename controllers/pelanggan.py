from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from controllers.auth import login_required
from models import Pelanggan, Transaksi, SegmentasiHasil
from utils.db import db
from sqlalchemy import func

pelanggan_bp = Blueprint('pelanggan', __name__, url_prefix='/pelanggan')

@pelanggan_bp.route('/')
@login_required(roles=['admin', 'owner'])
def index():
    # Mengambil semua pelanggan
    pelanggan_list = Pelanggan.query.order_by(Pelanggan.nama_pelanggan).all()
    return render_template('pelanggan/index.html', pelanggan_list=pelanggan_list)

@pelanggan_bp.route('/tambah', methods=['GET', 'POST'])
@login_required(roles=['admin'])
def tambah():
    if request.method == 'POST':
        nama = request.form.get('nama_pelanggan')
        nomor_hp = request.form.get('nomor_hp')
        alamat = request.form.get('alamat')
        
        # Validasi
        if not nama or not nomor_hp or not alamat:
            flash('Semua field wajib diisi!', 'danger')
            return redirect(url_for('pelanggan.tambah'))
            
        pelanggan_baru = Pelanggan(nama_pelanggan=nama, nomor_hp=nomor_hp, alamat=alamat)
        try:
            db.session.add(pelanggan_baru)
            db.session.commit()
            flash(f'Pelanggan {nama} berhasil ditambahkan.', 'success')
            return redirect(url_for('pelanggan.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat menyimpan data: {e}', 'danger')
            
    return render_template('pelanggan/form.html', action='Tambah', pelanggan=None)

@pelanggan_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required(roles=['admin'])
def edit(id):
    pelanggan = Pelanggan.query.get(id)
    if not pelanggan:
        flash('Pelanggan tidak ditemukan.', 'danger')
        return redirect(url_for('pelanggan.index'))
        
    if request.method == 'POST':
        nama = request.form.get('nama_pelanggan')
        nomor_hp = request.form.get('nomor_hp')
        alamat = request.form.get('alamat')
        
        if not nama or not nomor_hp or not alamat:
            flash('Semua field wajib diisi!', 'danger')
            return redirect(url_for('pelanggan.edit', id=id))
            
        pelanggan.nama_pelanggan = nama
        pelanggan.nomor_hp = nomor_hp
        pelanggan.alamat = alamat
        
        try:
            db.session.commit()
            flash(f'Data pelanggan {nama} berhasil diperbarui.', 'success')
            return redirect(url_for('pelanggan.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat memperbarui data: {e}', 'danger')
            
    return render_template('pelanggan/form.html', action='Edit', pelanggan=pelanggan)

@pelanggan_bp.route('/hapus/<int:id>', methods=['POST'])
@login_required(roles=['admin'])
def hapus(id):
    pelanggan = Pelanggan.query.get(id)
    if not pelanggan:
        flash('Pelanggan tidak ditemukan.', 'danger')
        return redirect(url_for('pelanggan.index'))
        
    nama = pelanggan.nama_pelanggan
    try:
        db.session.delete(pelanggan)
        db.session.commit()
        flash(f'Pelanggan {nama} berhasil dihapus beserta seluruh riwayat transaksi.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan saat menghapus data: {e}', 'danger')
        
    return redirect(url_for('pelanggan.index'))

@pelanggan_bp.route('/riwayat')
@login_required(roles=['admin'])
def riwayat_pilih():
    # Halaman untuk memilih pelanggan yang ingin dilihat riwayatnya
    pelanggan_list = Pelanggan.query.order_by(Pelanggan.nama_pelanggan).all()
    return render_template('pelanggan/riwayat_pilih.html', pelanggan_list=pelanggan_list)

@pelanggan_bp.route('/riwayat/<int:id>')
@login_required(roles=['admin', 'owner'])
def riwayat(id):
    pelanggan = Pelanggan.query.get(id)
    if not pelanggan:
        flash('Pelanggan tidak ditemukan.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    # Hitung total transaksi dan total pembelian
    total_transaksi = len(pelanggan.transaksi)
    total_pembelian = sum(float(t.total_transaksi) for t in pelanggan.transaksi)
    total_kg = sum(float(t.jumlah_kg) for t in pelanggan.transaksi)
    
    # Riwayat transaksi terurut tanggal terbaru
    transaksi_list = Transaksi.query.filter_by(pelanggan_id=id).order_by(Transaksi.tanggal_transaksi.desc()).all()
    
    # Detail cluster jika sudah berjalan
    segmentasi = SegmentasiHasil.query.filter_by(pelanggan_id=id).first()
    
    return render_template('pelanggan/riwayat.html',
                           pelanggan=pelanggan,
                           total_transaksi=total_transaksi,
                           total_pembelian=total_pembelian,
                           total_kg=total_kg,
                           transaksi_list=transaksi_list,
                           segmentasi=segmentasi)
