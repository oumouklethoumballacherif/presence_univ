import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uir-presence-secret-key-2024'
    
    # Database
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost:3306/presences_univ'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email Configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'balla33cherif@gmail.com'
    MAIL_PASSWORD = 'boyf sath nlti omdb'
    MAIL_DEFAULT_SENDER = ('UIR Présence', 'balla33cherif@gmail.com')
    
    # Token expiration
    PASSWORD_TOKEN_EXPIRY = timedelta(hours=24)
    
    # QR Code refresh interval (seconds)
    QR_REFRESH_INTERVAL = 15
    
    # Rattrapage rules
    RATTRAPAGE_CM_TD_THRESHOLD = 0.25  # 25% absences
    RATTRAPAGE_TP_THRESHOLD = 2  # 2 absences

    # Colors
    COLORS = {
        'primary': '#163A59',
        'secondary': '#5F7340',
        'accent': '#A1A621',
        'highlight': '#D9CB04',
        'background': '#F2F2F2'
    }
