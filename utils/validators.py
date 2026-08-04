import re
from datetime import datetime

def validate_email(email):
    """Validate an email address."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate a password (at least 8 chars, contains letter and number)."""
    if not password or len(password) < 8:
        return False
    # Check for at least one letter and one number
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_letter and has_digit

def validate_phone(phone):
    """Validate a phone number."""
    if not phone:
        return False
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    # Check if it's a valid length (10-15 digits)
    return 10 <= len(digits) <= 15

def validate_date(date_string, format='%Y-%m-%d'):
    """Validate a date string."""
    try:
        datetime.strptime(date_string, format)
        return True
    except ValueError:
        return False

def validate_patient_id(patient_id):
    """Validate a patient ID format."""
    if not patient_id:
        return False
    # Assuming patient ID is alphanumeric, 3-10 characters
    pattern = r'^[A-Za-z0-9]{3,10}$'
    return re.match(pattern, patient_id) is not None

def validate_height(height):
    """Validate height in cm."""
    try:
        h = float(height)
        return 50 <= h <= 300  # Reasonable range for human height in cm
    except ValueError:
        return False

def validate_weight(weight):
    """Validate weight in kg."""
    try:
        w = float(weight)
        return 2 <= w <= 500  # Reasonable range for human weight in kg
    except ValueError:
        return False

def validate_blood_pressure(systolic, diastolic):
    """Validate blood pressure readings."""
    try:
        s = int(systolic)
        d = int(diastolic)
        return 50 <= s <= 300 and 30 <= d <= 200
    except ValueError:
        return False

def validate_heart_rate(hr):
    """Validate heart rate."""
    try:
        h = int(hr)
        return 30 <= h <= 250  # Reasonable range for heart rate
    except ValueError:
        return False

def validate_temperature(temp):
    """Validate temperature in Celsius."""
    try:
        t = float(temp)
        return 30 <= t <= 45  # Reasonable range for body temperature in Celsius
    except ValueError:
        return False

def validate_oxygen_saturation(oxygen):
    """Validate oxygen saturation percentage."""
    try:
        o = float(oxygen)
        return 70 <= o <= 100  # Reasonable range for SpO2
    except ValueError:
        return False

def validate_bmi(bmi):
    """Validate BMI."""
    try:
        b = float(bmi)
        return 10 <= b <= 100  # Reasonable range for BMI
    except ValueError:
        return False

def is_strong_password(password):
    """Check if password is strong (min 12 chars, upper, lower, digit, special)."""
    if not password or len(password) < 12:
        return False
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?/' for c in password)
    return has_upper and has_lower and has_digit and has_special