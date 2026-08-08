import os
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    SQLALCHEMY_DATABASE_URI = db_url or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_ECHO = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-string'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    # Email settings (if needed)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['admin@example.com']
    # Pagination
    POSTS_PER_PAGE = 20
    # AI API keys
    OPENAI_API_KEY  = os.environ.get('OPENAI_API_KEY')
    GEMINI_API_KEY  = os.environ.get('GEMINI_API_KEY')
    AI_PROVIDER     = os.environ.get('AI_PROVIDER', 'gemini')  # 'gemini' | 'openai'
    AI_RATE_LIMIT   = int(os.environ.get('AI_RATE_LIMIT_PER_MIN', '20'))
    AI_CACHE_TTL    = int(os.environ.get('AI_CACHE_TTL', '300'))
    # Map / Places API keys
    GEOAPIFY_API_KEY = os.environ.get('GEOAPIFY_API_KEY', '')
    # -- Hospital provider ------------------------------------------------
    # 'geoapify' = Geoapify Places API -- requires GEOAPIFY_API_KEY (DEFAULT)
    # 'overpass'  = OpenStreetMap Overpass (free, no key, lower data quality)
    # If geoapify is set but GEOAPIFY_API_KEY is empty, falls back to overpass.
    HOSPITALS_PROVIDER   = os.environ.get('HOSPITALS_PROVIDER', 'geoapify')
    HOSPITALS_RADIUS_KM  = int(os.environ.get('HOSPITALS_RADIUS_KM', '10'))
    OVERPASS_TIMEOUT     = int(os.environ.get('OVERPASS_TIMEOUT', '15'))
    # ── SMS / Twilio ────────────────────────────────────────────
    # Get credentials at https://console.twilio.com
    # Leave empty to run without SMS (SOS will be logged but not sent)
    TWILIO_ACCOUNT_SID  = os.environ.get('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN   = os.environ.get('TWILIO_AUTH_TOKEN', '')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')


def startup_diagnostics():
    """
    Print a safe startup summary of key configuration values.
    NEVER prints actual secret values — only boolean presence.
    """
    geo_key    = bool(os.environ.get('GEOAPIFY_API_KEY', '').strip())
    twilio_sid = bool(os.environ.get('TWILIO_ACCOUNT_SID', '').strip())
    twilio_tok = bool(os.environ.get('TWILIO_AUTH_TOKEN', '').strip())
    twilio_num = bool(os.environ.get('TWILIO_PHONE_NUMBER', '').strip())
    provider   = os.environ.get('HOSPITALS_PROVIDER', 'geoapify')
    radius     = os.environ.get('HOSPITALS_RADIUS_KM', '10')

    lines = [
        '',
        '--- NexVita Configuration Diagnostics ----------------------------',
        f'  Geoapify API key    : {"[OK] configured" if geo_key else "[!!] NOT SET - hospital search will use Overpass fallback"}',
        f'  Hospital provider   : {provider}',
        f'  Hospital radius     : {radius} km',
        f'  Twilio SID          : {"[OK] configured" if twilio_sid else "[--] NOT SET"}',
        f'  Twilio token        : {"[OK] configured" if twilio_tok else "[--] NOT SET"}',
        f'  Twilio from number  : {"[OK] configured" if twilio_num else "[--] NOT SET"}',
        f'  SOS SMS delivery    : {"[OK] enabled" if (twilio_sid and twilio_tok and twilio_num) else "[--] disabled (demo mode)"}',
        '------------------------------------------------------------------',
        '',
    ]
    print('\n'.join(lines))

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = False

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}