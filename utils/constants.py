# Application constants

# User roles
USER_ROLES = {
    'admin': 'Administrator',
    'doctor': 'Doctor',
    'patient': 'Patient',
    'user': 'User'
}

# Health record types
HEALTH_RECORD_TYPES = [
    'vital',
    'laboratory',
    'medication',
    'procedure',
    'allergy',
    'immunization',
    'condition',
    'nutrition',
    'exercise',
    'sleep',
    'mental_health',
    'other'
]

# Blood types
BLOOD_TYPES = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']

# Gender options
GENDER_OPTIONS = [
    'male',
    'female',
    'non-binary',
    'prefer_not_to_say',
    'other'
]

# Vital sign ranges (for validation and display)
VITAL_RANGES = {
    'systolic_bp': {'min': 70, 'max': 250, 'unit': 'mmHg'},
    'diastolic_bp': {'min': 40, 'max': 150, 'unit': 'mmHg'},
    'heart_rate': {'min': 30, 'max': 220, 'unit': 'bpm'},
    'temperature': {'min': 30.0, 'max': 45.0, 'unit': '°C'},
    'respiratory_rate': {'min': 5, 'max': 40, 'unit': 'breaths/min'},
    'oxygen_saturation': {'min': 70, 'max': 100, 'unit': '%'},
    'weight': {'min': 2.0, 'max': 500.0, 'unit': 'kg'},
    'height': {'min': 30.0, 'max': 300.0, 'unit': 'cm'},
    'bmi': {'min': 10.0, 'max': 80.0, 'unit': 'kg/m²'},
    'glucose_level': {'min': 20.0, 'max': 600.0, 'unit': 'mg/dL'},
    'cholesterol_total': {'min': 50.0, 'max': 500.0, 'unit': 'mg/dL'},
    'hdl_cholesterol': {'min': 10.0, 'max': 150.0, 'unit': 'mg/dL'},
    'ldl_cholesterol': {'min': 10.0, 'max': 300.0, 'unit': 'mg/dL'},
    'triglycerides': {'min': 10.0, 'max': 500.0, 'unit': 'mg/dL'}
}

# Emergency constants
EMERGENCY_NUMBERS = {
    'us': '911',
    'uk': '999',
    'eu': '112',
    'canada': '911',
    'australia': '000',
    'india': '112'
}

# SOS alert levels
SOS_LEVELS = {
    0: 'low',
    1: 'medium',
    2: 'high',
    3: 'emergency'
}

# AI interaction types
AI_MESSAGE_TYPES = ['user', 'ai', 'system']

# Risk levels
RISK_LEVELS = ['low', 'medium', 'high']

# Wellness levels
WELLNESS_LEVELS = ['excellent', 'good', 'fair', 'needs_improvement']

# Date formats
DATE_FORMATS = {
    'default': '%Y-%m-%d',
    'datetime': '%Y-%m-%d %H:%M:%S',
    'time': '%H:%M:%S',
    'date_only': '%Y-%m-%d',
    'month_year': '%b %Y',
    'day_month': '%d %b'
}

# Pagination defaults
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100

# File upload settings
ALLOWED_EXTENSIONS = {
    'image': {'png', 'jpg', 'jpeg', 'gif'},
    'document': {'pdf', 'doc', 'docx', 'txt'},
    'data': {'csv', 'xls', 'xlsx'}
}

MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# Chart colors (for consistent visualization)
CHART_COLORS = [
    'rgba(255, 99, 132, 0.8)',   # Red
    'rgba(54, 162, 235, 0.8)',   # Blue
    'rgba(255, 206, 86, 0.8)',   # Yellow
    'rgba(75, 192, 192, 0.8)',   # Green
    'rgba(153, 102, 255, 0.8)',  # Purple
    'rgba(255, 159, 64, 0.8)',   # Orange
    'rgba(199, 199, 199, 0.8)',  # Gray
    'rgba(83, 102, 255, 0.8)',   # Indigo
    'rgba(40, 167, 69, 0.8)',    # Green
    'rgba(255, 193, 7, 0.8)'     # Yellow
]

# Notification types
NOTIFICATION_TYPES = [
    'reminder',
    'alert',
    'message',
    'warning',
    'info',
    'success'
]

# Activity levels
ACTIVITY_LEVELS = [
    'sedentary',
    'lightly_active',
    'moderately_active',
    'very_active',
    'extremely_active'
]

# Dietary preferences
DIETARY_PREFERENCES = [
    'none',
    'vegetarian',
    'vegan',
    'gluten_free',
    'dairy_free',
    'nut_allergy',
    'diabetic',
    'heart_healthy',
    'low_sodium',
    'other'
]

# Medical specialties
MEDICAL_SPECIALTIES = [
    'primary_care',
    'cardiology',
    'dermatology',
    'endocrinology',
    'gastroenterology',
    'gynecology',
    'neurology',
    'oncology',
    'ophthalmology',
    'orthopedics',
    'pediatrics',
    'psychiatry',
    'pulmonology',
    'radiology',
    'surgery',
    'other'
]

# Units of measurement
UNITS = {
    'weight': ['kg', 'lbs'],
    'height': ['cm', 'in'],
    'temperature': ['C', 'F'],
    'blood_pressure': ['mmHg'],
    'heart_rate': ['bpm'],
    'respiratory_rate': ['breaths/min'],
    'oxygen_saturation': ['%'],
    'glucose': ['mg/dL', 'mmol/L'],
    'cholesterol': ['mg/dL', 'mmol/L']
}