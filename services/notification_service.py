"""
services/notification_service.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Real SMS notification delivery via Twilio.

Required environment variables (only when SMS is needed):
    TWILIO_ACCOUNT_SID    – starts with "AC..."
    TWILIO_AUTH_TOKEN     – 32-character hex token
    TWILIO_PHONE_NUMBER   – E.164 format, e.g. +15551234567

Phone number normalisation:
    Numbers stored in the DB without a leading '+' are treated as Indian (IN)
    numbers and prefixed with +91.  To support other countries, store numbers
    in E.164 format in the database (e.g. +14155552671).

If credentials are absent or invalid, send_sms() returns a structured dict
with honest error information so callers can report it faithfully to the user.
"""

import os
import re
import logging

logger = logging.getLogger(__name__)

# ── Common Twilio error-code meanings ─────────────────────────────────────
# https://www.twilio.com/docs/api/errors
_TWILIO_ERROR_HINTS = {
    20003: 'Twilio credentials are invalid. Check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN.',
    20008: 'Twilio credentials are invalid (suspended or incorrect).',
    21211: 'Invalid destination phone number. Verify the number is in E.164 format (e.g. +919629333508).',
    21212: 'Invalid destination phone number.',
    21214: 'Destination is not a mobile number.',
    21217: 'Phone number does not appear to be a real number.',
    21408: 'Permission denied. The destination country/number may be blocked on your Twilio account.',
    21606: 'Twilio "from" number is not enabled for SMS. Check TWILIO_PHONE_NUMBER.',
    21610: 'Destination number has opted out of SMS.',
    21614: 'Invalid mobile number — number is not SMS-capable.',
    21705: 'Destination number not verified on a Twilio Trial account. '
           'Verify the number at https://console.twilio.com/us1/develop/phone-numbers/manage/verified',
    30001: 'Message queue is full — try again.',
    30002: 'Twilio account suspended.',
    30003: 'Destination number is unreachable.',
    30004: 'Destination number has blocked SMS.',
    30005: 'Destination number is unknown — may be invalid or unallocated.',
    30006: 'Destination number is a landline or non-SMS number.',
    30007: 'Message filtered (possible spam classification).',
    30008: 'Unknown delivery error.',
}


def _hint_for_code(code: int) -> str:
    """Return a human-readable hint for a Twilio error code (no secret data)."""
    return _TWILIO_ERROR_HINTS.get(code, f'Twilio error {code}.')


def normalise_phone(raw: str) -> str | None:
    """
    Normalise a raw phone number string to E.164 format.

    Rules:
      - If already starts with '+' → validate and return as-is.
      - If starts with '91' and is 12 digits → prepend '+'.
      - If is 10 digits (Indian mobile) → prepend '+91'.
      - Anything else → return None (invalid).

    Never raises; returns None on failure.
    """
    if not raw or not isinstance(raw, str):
        return None

    # Strip whitespace, dashes, dots, parentheses, spaces
    cleaned = re.sub(r'[\s\-\.\(\)]', '', raw.strip())

    if not cleaned:
        return None

    # Already E.164
    if cleaned.startswith('+'):
        digits = cleaned[1:]
        if digits.isdigit() and 7 <= len(digits) <= 15:
            return cleaned
        return None

    # Strip leading zeros (some users type 0XXXXXXXXXX)
    stripped = cleaned.lstrip('0')

    # 10-digit Indian mobile (starts with 6-9)
    if len(stripped) == 10 and stripped[0] in '6789' and stripped.isdigit():
        return '+91' + stripped

    # 12-digit with country code 91 (no +)
    if len(stripped) == 12 and stripped.startswith('91') and stripped.isdigit():
        return '+' + stripped

    # Generic: if all digits and reasonable length, try +91 prefix
    if stripped.isdigit() and 10 <= len(stripped) <= 15:
        return '+' + stripped

    return None


class NotificationService:
    """Handles outbound SMS notifications via Twilio."""

    def __init__(self):
        self.account_sid = os.environ.get('TWILIO_ACCOUNT_SID', '').strip()
        self.auth_token  = os.environ.get('TWILIO_AUTH_TOKEN',  '').strip()
        self.from_number = os.environ.get('TWILIO_PHONE_NUMBER', '').strip()

    @property
    def is_configured(self) -> bool:
        """Return True only when all three Twilio credentials are non-empty."""
        return bool(self.account_sid and self.auth_token and self.from_number)

    def missing_vars(self) -> list[str]:
        """Return names of missing Twilio environment variables (no values)."""
        missing = []
        if not self.account_sid: missing.append('TWILIO_ACCOUNT_SID')
        if not self.auth_token:  missing.append('TWILIO_AUTH_TOKEN')
        if not self.from_number: missing.append('TWILIO_PHONE_NUMBER')
        return missing

    def send_sms(self, to_number: str, message: str) -> dict:
        """
        Send a real SMS via Twilio to *to_number*.

        Returns a dict:
          {
            'success'            : bool,
            'sms_configured'     : bool,
            'provider_message_id': str | None   -- Twilio SID on success
            'normalised_number'  : str | None   -- E.164 number used
            'error'              : str | None   -- safe, user-readable reason
            'error_code'         : int | None   -- Twilio numeric code
          }

        Never raises — all exceptions are caught.
        Never logs auth tokens or full SIDs.
        """
        # ── 1. Check configuration ──────────────────────────────────────
        if not self.is_configured:
            missing = self.missing_vars()
            logger.warning(
                'SOS SMS skipped: Twilio not configured. Missing: %s',
                ', '.join(missing)
            )
            return {
                'success': False,
                'sms_configured': False,
                'provider_message_id': None,
                'normalised_number': None,
                'error': f'SMS not configured. Missing environment variables: {", ".join(missing)}',
                'error_code': None,
            }

        # ── 2. Normalise phone number ──────────────────────────────────
        normalised = normalise_phone(to_number)
        if normalised is None:
            logger.warning('SMS skipped: invalid phone number (not logged for privacy).')
            return {
                'success': False,
                'sms_configured': True,
                'provider_message_id': None,
                'normalised_number': None,
                'error': (
                    f'Invalid phone number "{to_number}". '
                    'Store numbers in E.164 format, e.g. +919629333508'
                ),
                'error_code': None,
            }

        # ── 3. Attempt real Twilio delivery ────────────────────────────
        # Import guard: separate from API call so ImportError is clean
        try:
            from twilio.rest import Client
            from twilio.base.exceptions import TwilioRestException
        except ImportError:
            logger.error('twilio package not installed. Run: pip install twilio')
            return {
                'success': False,
                'sms_configured': False,
                'provider_message_id': None,
                'normalised_number': normalised,
                'error': 'Twilio package is not installed. Run: pip install twilio',
                'error_code': None,
            }

        # API call: separate try so TwilioRestException is definitely bound
        try:
            client = Client(self.account_sid, self.auth_token)
            msg = client.messages.create(
                body=message,
                from_=self.from_number,
                to=normalised,
            )

            # Log SID prefix only (last chars obscured)
            sid_safe = msg.sid[:8] + '...' if msg.sid else '?'
            logger.info('SMS sent via Twilio. SID_prefix=%s to=%s', sid_safe, normalised)

            return {
                'success': True,
                'sms_configured': True,
                'provider_message_id': msg.sid,
                'normalised_number': normalised,
                'error': None,
                'error_code': None,
            }

        except TwilioRestException as exc:
            hint = _hint_for_code(exc.code)
            logger.error('Twilio error code=%s msg=%s to=%s', exc.code, exc.msg, normalised)
            return {
                'success': False,
                'sms_configured': True,
                'provider_message_id': None,
                'normalised_number': normalised,
                'error': hint,
                'error_code': exc.code,
            }

        except Exception as exc:
            logger.error('Unexpected error sending SMS to %s: %s', normalised, type(exc).__name__)
            return {
                'success': False,
                'sms_configured': True,
                'provider_message_id': None,
                'normalised_number': normalised,
                'error': f'Unexpected error: {type(exc).__name__}',
                'error_code': None,
            }

