from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from controllers.auth import login_required
from models import Transaksi, Pelanggan
from utils.db import db
from datetime import datetime

transaksi_bp = Blueprint('transaksi', __name__, url_prefix='/transaksi')

@transaksi_bp.route('/')
@login_required(roles=['admin', 'owner'])
def index():
    transaksi_list = Transaksi.query.order_by(Transaksi.tanggal_transaksi.desc(), Transaksi.id.desc()).all()
    return render_template('transaksi/index.html', transaksi_list=transaksi_list)

@transaksi_bp.route('/tambah', methods=['GET', 'POST'])
@login_required(roles=['admin'])
def tambah():
    pelanggan_list = Pelanggan.query.order_by(Pelanggan.nama_pelanggan).all()
    
    if request.method == 'POST':
        tanggal_str = request.form.get('tanggal_transaksi')
        pelanggan_id = request.form.get('pelanggan_id')
        jumlah_kg = request.form.get('jumlah_kg')
        harga_per_kg = request.form.get('harga_per_kg')
        metode_pembayaran = request.form.get('metode_pembayaran')
        
        # Validasi input
        if not tanggal_str or not pelanggan_id or not jumlah_kg or not harga_per_kg or not metode_pembayaran:
            flash('Semua field wajib diisi!', 'danger')
            return redirect(url_for('transaksi.tambah'))
            
        try:
            tanggal_transaksi = datetime.strptime(tanggal_str, '%Y-%m-%d').date()
            jumlah = float(jumlah_kg)
            harga = float(harga_per_kg)
            
            transaksi_baru = Transaksi(
                tanggal_transaksi=tanggal_transaksi,
                pelanggan_id=int(pelanggan_id),
                jumlah_kg=jumlah,
                harga_per_kg=harga,
                metode_pembayaran=metode_pembayaran
            )
            # Hitung total belanja otomatis
            transaksi_baru.calculate_total()
            
            db.session.add(transaksi_baru)
            db.session.commit()
            flash('Data transaksi berhasil ditambahkan.', 'success')
            return redirect(url_for('transaksi.index'))
            
        except ValueError as ve:
            flash(f'Format angka atau tanggal tidak valid: {ve}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat menyimpan transaksi: {e}', 'danger')
            
    return render_template('transaksi/form.html', action='Tambah', transaksi=None, pelanggan_list=pelanggan_list)

@transaksi_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required(roles=['admin'])
def edit(id):
    transaksi = Transaksi.query.get(id)
    if not transaksi:
        flash('Transaksi tidak ditemukan.', 'danger')
        return redirect(url_for('transaksi.index'))
        
    pelanggan_list = Pelanggan.query.order_by(Pelanggan.nama_pelanggan).all()
    
    if request.method == 'POST':
        tanggal_str = request.form.get('tanggal_transaksi')
        pelanggan_id = request.form.get('pelanggan_id')
        jumlah_kg = request.form.get('jumlah_kg')
        harga_per_kg = request.form.get('harga_per_kg')
        metode_pembayaran = request.form.get('metode_pembayaran')
        
        if not tanggal_str or not pelanggan_id or not jumlah_kg or not harga_per_kg or not metode_pembayaran:
            flash('Semua field wajib diisi!', 'danger')
            return redirect(url_for('transaksi.edit', id=id))
            
        try:
            transaksi.tanggal_transaksi = datetime.strptime(tanggal_str, '%Y-%m-%d').date()
            transaksi.pelanggan_id = int(pelanggan_id)
            transaksi.jumlah_kg = float(jumlah_kg)
            transaksi.harga_per_kg = float(harga_per_kg)
            transaksi.metode_pembayaran = metode_pembayaran
            
            # Hitung kembali total belanja otomatis
            transaksi.calculate_total()
            
            db.session.commit()
            flash('Data transaksi berhasil diperbarui.', 'success')
            return redirect(url_for('transaksi.index'))
            
        except ValueError as ve:
            flash(f'Format angka atau tanggal tidak valid: {ve}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat memperbarui transaksi: {e}', 'danger')
            
    return render_template('transaksi/form.html', action='Edit', transaksi=transaksi, pelanggan_list=pelanggan_list)

@transaksi_bp.route('/hapus/<int:id>', methods=['POST'])
@login_required(roles=['admin'])
def hapus(id):
    transaksi = Transaksi.query.get(id)
    if not transaksi:
        flash('Transaksi tidak ditemukan.', 'danger')
        return redirect(url_for('transaksi.index'))
        
    try:
        db.session.delete(transaksi)
        db.session.commit()
        flash('Transaksi berhasil dihapus.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan saat menghapus transaksi: {e}', 'danger')
        
    return redirect(url_for('transaksi.index'))
