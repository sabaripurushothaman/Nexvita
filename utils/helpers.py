from flask import flash
import logging
import json
from functools import wraps
from datetime import datetime, date


def flash_errors(form):
    """Flash all errors for a form."""
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", 'error')


def setup_logger(name, log_file, level=logging.INFO):
    """Set up a logger."""
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


def paginate_query(query, page, per_page=20):
    """Paginate a SQLAlchemy query."""
    return query.paginate(page=page, per_page=per_page, error_out=False)


def generate_reset_token():
    """Generate a password reset token."""
    import secrets
    return secrets.token_urlsafe(32)


def generate_verification_code():
    """Generate a verification code."""
    import random
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


def save_picture(form_picture, directory):
    """Save an uploaded picture and return the filename."""
    import os
    import secrets
    from PIL import Image

    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join('static', directory, picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


def send_email(to, subject, template):
    """Send an email (placeholder – integrate with actual email service)."""
    print(f"Sending email to: {to}")
    print(f"Subject: {subject}")
    print(f"Template: {template}")


def calculate_age(dob):
    """Calculate age from a date object or a 'YYYY-MM-DD' string."""
    if isinstance(dob, str):
        birth_date = datetime.strptime(dob, '%Y-%m-%d').date()
    elif isinstance(dob, datetime):
        birth_date = dob.date()
    else:
        birth_date = dob  # already a date object

    today = date.today()
    age = today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )
    return age


def calculate_bmi(weight_kg, height_cm):
    """Calculate BMI from weight in kg and height in cm."""
    try:
        weight = float(weight_kg)
        height = float(height_cm)
        if height <= 0:
            return None
        height_in_meters = height / 100
        bmi = weight / (height_in_meters ** 2)
        return round(bmi, 1)
    except (ValueError, TypeError):
        return None


def calculate_ideal_weight_range(height_cm):
    """Calculate ideal weight range based on height (using BMI 18.5–24.9)."""
    try:
        height = float(height_cm)
        if height <= 0:
            return None
        height_in_meters = height / 100
        min_weight = 18.5 * (height_in_meters ** 2)
        max_weight = 24.9 * (height_in_meters ** 2)
        return {
            'min': round(min_weight, 1),
            'max': round(max_weight, 1)
        }
    except (ValueError, TypeError):
        return None


def get_bmi_category(bmi):
    """Get BMI category based on BMI value."""
    try:
        bmi = float(bmi)
        if bmi < 18.5:
            return "Underweight"
        elif 18.5 <= bmi < 25:
            return "Normal weight"
        elif 25 <= bmi < 30:
            return "Overweight"
        else:
            return "Obese"
    except (ValueError, TypeError):
        return "Unknown"


def get_blood_pressure_category(systolic, diastolic):
    """Get blood pressure category based on readings."""
    try:
        s = int(systolic)
        d = int(diastolic)
        if s < 120 and d < 80:
            return "Normal"
        elif 120 <= s < 130 and d < 80:
            return "Elevated"
        elif (130 <= s < 140) or (80 <= d < 90):
            return "Hypertension Stage 1"
        elif s >= 140 or d >= 90:
            return "Hypertension Stage 2"
        else:
            return "Hypertensive Crisis"
    except (ValueError, TypeError):
        return "Invalid"


def format_date(date_obj, format='%Y-%m-%d'):
    """Format a date object as a string."""
    if date_obj is None:
        return ""
    return date_obj.strftime(format)


def format_datetime(datetime_obj, format='%Y-%m-%d %H:%M:%S'):
    """Format a datetime object as a string."""
    if datetime_obj is None:
        return ""
    return datetime_obj.strftime(format)


def safe_int(value, default=0):
    """Safely convert a value to int."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default=0.0):
    """Safely convert a value to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def truncate_text(text, length=100):
    """Truncate text to a specified length."""
    if not text:
        return ""
    if len(text) <= length:
        return text
    return text[:length] + "..."


def paginate_list(items, page, per_page=10):
    """Paginate a list of items."""
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], len(items)


def serialize_model(model_instance, exclude=None):
    """
    Serialize a SQLAlchemy model instance to a dictionary.
    Excludes fields listed in `exclude`.
    """
    exclude = exclude or []
    result = {}
    for col in model_instance.__table__.columns:
        if col.name not in exclude:
            val = getattr(model_instance, col.name)
            # Convert datetime / date to ISO string for JSON compatibility
            if isinstance(val, (datetime, date)):
                val = val.isoformat()
            result[col.name] = val
    return result


def validate_json_response(response_str):
    """
    Attempt to parse a JSON string; return the parsed object or None on failure.
    Used to safely validate AI responses that are expected to be JSON.
    """
    if not response_str:
        return None
    try:
        return json.loads(response_str)
    except (json.JSONDecodeError, TypeError):
        return None


class PaginationHelper:
    """Helper class for pagination."""

    @staticmethod
    def get_pagination_params(page, per_page, total_items):
        """Get pagination parameters."""
        total_pages = (total_items + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages
        return {
            'page': page,
            'per_page': per_page,
            'total_items': total_items,
            'total_pages': total_pages,
            'has_prev': has_prev,
            'has_next': has_next,
            'prev_num': page - 1 if has_prev else None,
            'next_num': page + 1 if has_next else None
        }