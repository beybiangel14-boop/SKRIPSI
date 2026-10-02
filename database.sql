-- Database: ikan_giling_rfm
CREATE DATABASE IF NOT EXISTS `ikan_giling_rfm`;
USE `ikan_giling_rfm`;

-- 1. Tabel Users
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `password` VARCHAR(255) NOT NULL,
    `role` ENUM('admin', 'owner') NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Tabel Pelanggan
CREATE TABLE IF NOT EXISTS `pelanggan` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `nama_pelanggan` VARCHAR(100) NOT NULL,
    `nomor_hp` VARCHAR(20) NOT NULL,
    `alamat` TEXT NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Tabel Transaksi
CREATE TABLE IF NOT EXISTS `transaksi` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `tanggal_transaksi` DATE NOT NULL,
    `pelanggan_id` INT NOT NULL,
    `jumlah_kg` DECIMAL(10,2) NOT NULL,
    `harga_per_kg` DECIMAL(10,2) NOT NULL,
    `total_transaksi` DECIMAL(15,2) GENERATED ALWAYS AS (jumlah_kg * harga_per_kg) STORED,
    `metode_pembayaran` VARCHAR(50) NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`pelanggan_id`) REFERENCES `pelanggan`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Tabel Hasil Segmentasi
CREATE TABLE IF NOT EXISTS `segmentasi_hasil` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `pelanggan_id` INT NOT NULL UNIQUE,
    `recency` INT NOT NULL,
    `frequency` INT NOT NULL,
    `monetary` DECIMAL(15,2) NOT NULL,
    `score_rfm` DECIMAL(5,2) NOT NULL,
    `cluster` INT NOT NULL,
    `segmentasi` VARCHAR(50) NOT NULL,
    `tanggal_perhitungan` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`pelanggan_id`) REFERENCES `pelanggan`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
