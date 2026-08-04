# app/utils/__init__.py - made available as utils package

from .security import (
    generate_password_hash,
    check_password_hash,
    generate_token,
    verify_token,
)
from .validators import (
    validate_email,
    validate_password,
    validate_phone,
    validate_date,
)
from .helpers import (
    flash_errors,
    serialize_model,
    paginate_query,
    calculate_age,
    calculate_bmi,
    validate_json_response,
    format_date,
    format_datetime,
)
from .location import (
    get_user_location,
    calculate_distance,  # canonical name (was aliased as get_distance – fixed)
)
from .constants import (
    USER_ROLES,
    HEALTH_RECORD_TYPES,
    BLOOD_TYPES,
    GENDER_OPTIONS,
)

# Alias for backward-compatibility with any code that used 'get_distance'
get_distance = calculate_distance

__all__ = [
    # security
    'generate_password_hash', 'check_password_hash', 'generate_token', 'verify_token',
    # validators
    'validate_email', 'validate_password', 'validate_phone', 'validate_date',
    # helpers
    'flash_errors', 'serialize_model', 'paginate_query', 'calculate_age',
    'calculate_bmi', 'validate_json_response', 'format_date', 'format_datetime',
    # location
    'get_user_location', 'calculate_distance', 'get_distance',
    # constants
    'USER_ROLES', 'HEALTH_RECORD_TYPES', 'BLOOD_TYPES', 'GENDER_OPTIONS',
]