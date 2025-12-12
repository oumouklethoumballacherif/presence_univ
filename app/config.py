import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-prod'
    
    # Server configuration for URL generation
    SERVER_NAME = '127.0.0.1:5000'
    PREFERRED_URL_SCHEME = 'http'
    
    # Database
    # Default to sqlite or override in config_local.py for MySQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email Configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = ('UIR Présence', os.environ.get('MAIL_USERNAME'))
    
    # Token expiration
    PASSWORD_TOKEN_EXPIRY = timedelta(hours=24)
    
    # QR Code refresh interval (seconds)
    QR_REFRESH_INTERVAL = 15
    
    # Late threshold (minutes)
    LATE_THRESHOLD_MINUTES = 20
    
    # Rattrapage rules
    RATTRAPAGE_CM_TD_THRESHOLD = 0.5  # 50% absences allowed (aligned with visual warning)
    RATTRAPAGE_TP_THRESHOLD = 2  # 2 absences

    # Colors
    COLORS = {
        'primary': '#163A59',
        'secondary': '#5F7340',
        'accent': '#A1A621',
        'highlight': '#D9CB04',
        'background': '#F2F2F2'
    }

# Try to load local configuration
try:
    from .config_local import LocalConfig
    for key, value in LocalConfig.__dict__.items():
        if not key.startswith('__'):
            setattr(Config, key, value)
except ImportError:
    pass
