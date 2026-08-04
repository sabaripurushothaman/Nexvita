# app/routes/__init__.py - made available as routes package

from .auth import auth_bp
from .dashboard import dashboard_bp
from .patient import patient_bp
from .health import health_bp
from .ai import ai_bp
from .sos import sos_bp
from .hospital import hospital_bp
from .admin import admin_bp
from .reminders import reminders_bp

__all__ = [
    'auth_bp', 'dashboard_bp', 'patient_bp', 'health_bp',
    'ai_bp', 'sos_bp', 'hospital_bp', 'admin_bp', 'reminders_bp'
]