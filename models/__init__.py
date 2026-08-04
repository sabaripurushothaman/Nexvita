# app/models/__init__.py
# This file makes the models directory a Python package
# and can be used to import models conveniently

from .user import User
from .patient import Patient
from .health_record import HealthRecord
from .emergency_contact import EmergencyContact
from .hospital import Hospital
from .ai_history import AIHistory
from .reminder import Reminder

__all__ = ['User', 'Patient', 'HealthRecord', 'EmergencyContact', 'Hospital', 'AIHistory', 'Reminder']