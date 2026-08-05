# Application constants

# User roles
USER_ROLES = {
    'admin': 'Administrator',
    'doctor': 'Doctor',
    'patient': 'Patient',
    'user': 'User'
}

# Health record types (legacy — kept for backward compat with AI service)
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

# ── New Health Records System ──────────────────────────────────────────────

# Categories with display metadata
HEALTH_CATEGORIES = {
    'vital_signs':     {'label': 'Vital Signs',       'icon': 'activity',        'color': '#3B82F6', 'bg': '#DBEAFE'},
    'laboratory':      {'label': 'Laboratory Tests',  'icon': 'flask-conical',   'color': '#F59E0B', 'bg': '#FEF3C7'},
    'imaging':         {'label': 'Imaging',            'icon': 'scan',            'color': '#7C3AED', 'bg': '#EDE9FE'},
    'diseases':        {'label': 'Diseases',           'icon': 'virus',           'color': '#EF4444', 'bg': '#FEE2E2'},
    'medications':     {'label': 'Medications',        'icon': 'pill',            'color': '#00C897', 'bg': '#E6FBF5'},
    'vaccinations':    {'label': 'Vaccinations',       'icon': 'syringe',         'color': '#10B981', 'bg': '#D1FAE5'},
    'surgeries':       {'label': 'Surgeries',          'icon': 'scissors',        'color': '#EF4444', 'bg': '#FEE2E2'},
    'consultations':   {'label': 'Consultations',      'icon': 'stethoscope',     'color': '#3B82F6', 'bg': '#DBEAFE'},
    'allergies':       {'label': 'Allergies',          'icon': 'alert-triangle',  'color': '#F59E0B', 'bg': '#FEF3C7'},
    'mental_health':   {'label': 'Mental Health',      'icon': 'brain',           'color': '#7C3AED', 'bg': '#EDE9FE'},
    'lifestyle':       {'label': 'Lifestyle',          'icon': 'leaf',            'color': '#00C897', 'bg': '#E6FBF5'},
    'nutrition':       {'label': 'Nutrition',          'icon': 'apple',           'color': '#10B981', 'bg': '#D1FAE5'},
    'custom':          {'label': 'Custom',             'icon': 'folder-open',     'color': '#64748B', 'bg': '#F1F5F9'},
}

# Preset record types for quick selection
HEALTH_RECORD_PRESET_TYPES = [
    # Vital Signs
    {'value': 'blood_pressure',    'label': 'Blood Pressure',    'category': 'vital_signs'},
    {'value': 'heart_rate',        'label': 'Heart Rate',        'category': 'vital_signs'},
    {'value': 'temperature',       'label': 'Temperature',       'category': 'vital_signs'},
    {'value': 'weight_bmi',        'label': 'Weight / BMI',      'category': 'vital_signs'},
    {'value': 'oxygen_saturation', 'label': 'Oxygen Saturation', 'category': 'vital_signs'},
    {'value': 'respiratory_rate',  'label': 'Respiratory Rate',  'category': 'vital_signs'},
    # Laboratory
    {'value': 'blood_sugar',       'label': 'Blood Sugar',       'category': 'laboratory'},
    {'value': 'cholesterol',       'label': 'Cholesterol',       'category': 'laboratory'},
    {'value': 'thyroid',           'label': 'Thyroid Function',  'category': 'laboratory'},
    {'value': 'cbc',               'label': 'CBC / Blood Count', 'category': 'laboratory'},
    {'value': 'urine_test',        'label': 'Urine Test',        'category': 'laboratory'},
    {'value': 'liver_function',    'label': 'Liver Function',    'category': 'laboratory'},
    {'value': 'kidney_function',   'label': 'Kidney Function',   'category': 'laboratory'},
    # Imaging
    {'value': 'xray',              'label': 'X-Ray',             'category': 'imaging'},
    {'value': 'mri',               'label': 'MRI',               'category': 'imaging'},
    {'value': 'ct_scan',           'label': 'CT Scan',           'category': 'imaging'},
    {'value': 'ultrasound',        'label': 'Ultrasound',        'category': 'imaging'},
    {'value': 'ecg',               'label': 'ECG / EKG',         'category': 'imaging'},
    # Diseases / Conditions
    {'value': 'diabetes',          'label': 'Diabetes',          'category': 'diseases'},
    {'value': 'hypertension',      'label': 'Hypertension',      'category': 'diseases'},
    {'value': 'asthma',            'label': 'Asthma',            'category': 'diseases'},
    # Others
    {'value': 'vaccination',       'label': 'Vaccination',       'category': 'vaccinations'},
    {'value': 'surgery',           'label': 'Surgery',           'category': 'surgeries'},
    {'value': 'consultation',      'label': 'Consultation',      'category': 'consultations'},
    {'value': 'eye_checkup',       'label': 'Eye Checkup',       'category': 'consultations'},
    {'value': 'dental',            'label': 'Dental Record',     'category': 'consultations'},
    {'value': 'allergy',           'label': 'Allergy',           'category': 'allergies'},
    {'value': 'medication',        'label': 'Medication',        'category': 'medications'},
    {'value': 'mental_health',     'label': 'Mental Health',     'category': 'mental_health'},
    {'value': 'pregnancy',         'label': 'Pregnancy',         'category': 'consultations'},
    {'value': 'custom',            'label': 'Custom / Other',    'category': 'custom'},
]

# Severity levels
SEVERITY_LEVELS = [
    {'value': 'normal',   'label': 'Normal',   'badge': 'badge-success', 'color': '#10B981'},
    {'value': 'mild',     'label': 'Mild',     'badge': 'badge-info',    'color': '#3B82F6'},
    {'value': 'moderate', 'label': 'Moderate', 'badge': 'badge-warning', 'color': '#F59E0B'},
    {'value': 'severe',   'label': 'Severe',   'badge': 'badge-danger',  'color': '#EF4444'},
    {'value': 'critical', 'label': 'Critical', 'badge': 'badge-danger',  'color': '#DC2626'},
]

# Record status options
RECORD_STATUS = [
    {'value': 'active',     'label': 'Active'},
    {'value': 'resolved',   'label': 'Resolved'},
    {'value': 'monitoring', 'label': 'Monitoring'},
    {'value': 'chronic',    'label': 'Chronic'},
]

# Allowed attachment file extensions
ALLOWED_ATTACHMENT_EXTENSIONS = {
    'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp',
    'doc', 'docx', 'txt', 'csv', 'xls', 'xlsx'
}

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