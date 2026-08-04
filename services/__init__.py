# app/services/__init__.py - made available as services package

from .ai_service import AIService
from .prediction_service import PredictionService
from .emergency_service import EmergencyService
from .hospital_service import HospitalService

__all__ = ['AIService', 'PredictionService', 'EmergencyService', 'HospitalService']