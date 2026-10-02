import os
from dotenv import load_dotenv

# Muat file .env jika ada
load_dotenv()

class Config:
    # Kunci rahasia untuk session Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'skripsi_safira_secret_key_12983719283')
    
    # Konfigurasi Database MySQL (Laragon default: root, password kosong)
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'ikan_giling_rfm')
    
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Konfigurasi Upload atau Tambahan lainnya jika diperlukan
    DEBUG = True
