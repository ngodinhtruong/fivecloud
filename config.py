import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Cấu hình bảo mật
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # Cấu hình database - sử dụng đường dẫn tuyệt đối
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.abspath("instance/ds_reading.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Cấu hình upload
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size 
    
    # Pexels API
    PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY')
    if not PEXELS_API_KEY:
        print("Warning: PEXELS_API_KEY not set in .env file")
    
    # Cache config để lưu avatar URL
    AVATAR_CACHE_TIMEOUT = 3600  # 1 giờ 