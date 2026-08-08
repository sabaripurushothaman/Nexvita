"""
routes/sos.py
~~~~~~~~~~~~~~
SOS emergency blueprint.

Key fixes vs. original:
- trigger_sos now accepts JSON body with latitude/longitude from the browser
- Calls EmergencyService which uses real SMS (Twilio) and returns honest status
- Returns a structured JSON response that the frontend processes faithfully
- All legacy .query.get() replaced with db.session.get()
- emergency-contacts CRUD kept intact
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from database.db import db
from models import User, Patient, EmergencyContact, Hospital
from services.emergency_service import EmergencyService
from services.hospital_service import HospitalService
from utils.helpers import flash_errors
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

sos_bp = Blueprint('sos', __name__, url_prefix='/sos')


# ------------------------------------------------------------------ #
# Main SOS page
# ------------------------------------------------------------------ #

@sos_bp.route('/')
@login_required
def index():
    """SOS landing page. Nearby hospitals are loaded client-side via JS."""
    patient  = Patient.query.filter_by(user_id=current_user.id).first()
    contacts = EmergencyContact.query.filter_by(user_id=current_user.id).all()
    # hospitals are loaded dynamically by sos.js after geolocation
    return render_template('sos/index.html',
                           patient=patient,
                           contacts=contacts)


# ------------------------------------------------------------------ #
# Emergency Contacts CRUD
# ------------------------------------------------------------------ #

@sos_bp.route('/emergency-contacts')
@login_required
def emergency_contacts():
    patient  = Patient.query.filter_by(user_id=current_user.id).first()
    contacts = EmergencyContact.query.filter_by(user_id=current_user.id).all()
    return render_template('sos/emergency_contacts.html',
                           patient=patient, contacts=contacts)


@sos_bp.route('/emergency-contacts/add', methods=['GET', 'POST'])
@login_required
def add_emergency_contact():
    if request.method == 'POST':
        name          = request.form.get('name', '').strip()
        relationship  = request.form.get('relationship', '').strip()
        phone_primary = request.form.get('phone_primary', '').strip()
        phone_secondary = request.form.get('phone_secondary', '').strip()
        email         = request.form.get('email', '').strip()
        address       = request.form.get('address', '').strip()
        is_primary    = 'is_primary' in request.form

        if not name or not phone_primary:
            flash('Name and primary phone number are required.', 'danger')
            return render_template('sos/add_emergency_contact.html')

        if is_primary:
            EmergencyContact.query.filter_by(
                user_id=current_user.id, is_primary=True
            ).update({'is_primary': False})

        contact = EmergencyContact(
            user_id=current_user.id,
            name=name,
            relationship=relationship,
            phone_primary=phone_primary,
            phone_secondary=phone_secondary,
            email=email,
            address=address,
            is_primary=is_primary,
        )
        db.session.add(contact)
        db.session.commit()
        flash('Emergency contact added successfully!', 'success')
        return redirect(url_for('sos.emergency_contacts'))

    return render_template('sos/add_emergency_contact.html')


@sos_bp.route('/emergency-contacts/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_emergency_contact(id):
    contact = db.session.get(EmergencyContact, id)
    if contact is None or contact.user_id != current_user.id:
        flash('Access denied or contact not found.', 'danger')
        return redirect(url_for('sos.emergency_contacts'))

    if request.method == 'POST':
        is_primary = 'is_primary' in request.form
        if is_primary:
            EmergencyContact.query.filter_by(
                user_id=current_user.id, is_primary=True
            ).filter(EmergencyContact.id != id).update({'is_primary': False})

        contact.name            = request.form.get('name', '').strip()
        contact.relationship    = request.form.get('relationship', '').strip()
        contact.phone_primary   = request.form.get('phone_primary', '').strip()
        contact.phone_secondary = request.form.get('phone_secondary', '').strip()
        contact.email           = request.form.get('email', '').strip()
        contact.address         = request.form.get('address', '').strip()
        contact.is_primary      = is_primary
        contact.updated_at      = datetime.utcnow()
        db.session.commit()
        flash('Emergency contact updated successfully!', 'success')
        return redirect(url_for('sos.emergency_contacts'))

    return render_template('sos/edit_emergency_contact.html', contact=contact)


@sos_bp.route('/emergency-contacts/delete/<int:id>', methods=['POST'])
@login_required
def delete_emergency_contact(id):
    contact = db.session.get(EmergencyContact, id)
    if contact is None or contact.user_id != current_user.id:
        flash('Access denied or contact not found.', 'danger')
        return redirect(url_for('sos.emergency_contacts'))

    db.session.delete(contact)
    db.session.commit()
    flash('Emergency contact deleted successfully!', 'success')
    return redirect(url_for('sos.emergency_contacts'))


# ------------------------------------------------------------------ #
# Hospitals page (nearby – dynamic)
# ------------------------------------------------------------------ #

@sos_bp.route('/hospitals')
@login_required
def hospitals():
    """Nearby hospitals shell page – data loaded client-side."""
    return render_template('sos/hospitals.html')


# ------------------------------------------------------------------ #
# *** SOS Trigger ***
# ------------------------------------------------------------------ #

@sos_bp.route('/trigger-sos', methods=['POST'])
@login_required
def trigger_sos():
    """
    Trigger an SOS alert.

    Expects JSON body:
      { "latitude": <float|null>, "longitude": <float|null> }

    Returns JSON:
      {
        "success": bool,
        "message": str,
        "sms_configured": bool,
        "no_contacts": bool,
        "location_available": bool,
        "maps_link": str|null,
        "contacts_notified": [...],
        "contacts_failed": [...],
        "timestamp": str
      }
    """
    data = request.get_json(silent=True) or {}
    raw_lat = data.get('latitude')
    raw_lng = data.get('longitude')

    # Build location dict only when valid coordinates were provided
    location = None
    location_available = False
    if raw_lat is not None and raw_lng is not None:
        try:
            lat = float(raw_lat)
            lng = float(raw_lng)
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                location = {'latitude': lat, 'longitude': lng}
                location_available = True
        except (TypeError, ValueError):
            pass

    # Fetch this user's emergency contacts (active only)
    contacts = EmergencyContact.query.filter_by(user_id=current_user.id).all()

    if not contacts:
        logger.info('SOS triggered by user %d with no emergency contacts', current_user.id)
        return jsonify({
            'success': False,
            'message': 'No emergency contacts configured. Please add an emergency contact first.',
            'no_contacts': True,
            'sms_configured': False,
            'location_available': location_available,
            'maps_link': None,
            'contacts_notified': [],
            'contacts_failed': [],
            'timestamp': datetime.utcnow().isoformat(),
        })

    logger.info('SOS triggered by user %d | location=%s | contacts=%d',
                current_user.id, location, len(contacts))

    emergency_service = EmergencyService()
    result = emergency_service.send_sos_alert(
        user_id=current_user.id,
        location=location,
        contacts=contacts,
    )

    # Ensure location_available is present in result
    result['location_available'] = location_available
    return jsonify(result)


# ------------------------------------------------------------------ #
# Location Sharing
# ------------------------------------------------------------------ #

@sos_bp.route('/location')
@login_required
def location_sharing():
    """Location sharing stub – redirects to SOS index."""
    flash('Share your location by pressing the SOS button or using the Share Location button on the SOS page.', 'info')
    return redirect(url_for('sos.index'))


# ------------------------------------------------------------------ #
# Dev Diagnostic — safe Twilio config check (no secrets exposed)
# ------------------------------------------------------------------ #

@sos_bp.route('/diagnostic')
@login_required
def diagnostic():
    """
    Return a JSON diagnostic showing which Twilio variables are set.
    NEVER exposes credential values — only booleans + masked strings.

    Useful for diagnosing "SMS delivery is not configured" messages.
    """
    from services.notification_service import NotificationService
    import os

    ns = NotificationService()

    sid_raw  = os.environ.get('TWILIO_ACCOUNT_SID',  '')
    tok_raw  = os.environ.get('TWILIO_AUTH_TOKEN',   '')
    num_raw  = os.environ.get('TWILIO_PHONE_NUMBER', '')

    def mask(s, visible=4):
        """Show only first `visible` chars, mask the rest."""
        s = s.strip()
        if not s: return '(not set)'
        if len(s) <= visible: return '*' * len(s)
        return s[:visible] + '*' * (len(s) - visible)

    contacts = EmergencyContact.query.filter_by(user_id=current_user.id).all()
    contact_info = []
    for c in contacts:
        from services.notification_service import normalise_phone
        phone = (c.phone_primary or '').strip()
        normalised = normalise_phone(phone)
        contact_info.append({
            'name'         : c.name,
            'phone_raw'    : phone,
            'phone_e164'   : normalised,
            'phone_valid'  : normalised is not None,
            'is_primary'   : c.is_primary,
        })

    result = {
        'twilio': {
            'account_sid_set'   : bool(sid_raw.strip()),
            'account_sid_prefix': mask(sid_raw),
            'auth_token_set'    : bool(tok_raw.strip()),
            'phone_number_set'  : bool(num_raw.strip()),
            'phone_number_mask' : mask(num_raw),
            'is_configured'     : ns.is_configured,
            'missing_vars'      : ns.missing_vars(),
        },
        'emergency_contacts': {
            'count'   : len(contacts),
            'contacts': contact_info,
        },
        'diagnosis': (
            'Ready to send SMS' if ns.is_configured and any(c['phone_valid'] for c in contact_info)
            else 'SMS not configured' if not ns.is_configured
            else 'No valid E.164 phone numbers in contacts'
        ),
    }
    return jsonify(result)


# ------------------------------------------------------------------ #
# Manual Test SMS — sends ONE real SMS to primary contact (dev tool)
# ------------------------------------------------------------------ #

@sos_bp.route('/test-sms', methods=['POST'])
@login_required
def test_sms():
    """
    Send a real test SMS to the authenticated user's primary emergency contact.
    For development/verification use only.

    POST body (optional JSON):
      { "phone": "+919629333508" }   -- override destination

    Returns JSON with delivery result including Twilio message SID on success.
    NEVER exposes auth token.
    """
    from services.notification_service import NotificationService, normalise_phone
    import os

    ns = NotificationService()
    if not ns.is_configured:
        return jsonify({
            'success': False,
            'error': 'Twilio not configured. Missing: ' + ', '.join(ns.missing_vars()),
            'missing_vars': ns.missing_vars(),
        }), 400

    data = request.get_json(silent=True) or {}

    # Determine target phone
    override_phone = (data.get('phone') or '').strip()
    if override_phone:
        target_phone = normalise_phone(override_phone)
        target_name  = 'Override (manual test)'
    else:
        contact = (
            EmergencyContact.query.filter_by(user_id=current_user.id, is_primary=True).first()
            or EmergencyContact.query.filter_by(user_id=current_user.id).first()
        )
        if not contact:
            return jsonify({
                'success': False,
                'error': 'No emergency contacts configured.',
            }), 400
        target_phone = normalise_phone(contact.phone_primary or '')
        target_name  = contact.name

    if not target_phone:
        return jsonify({
            'success': False,
            'error': f'Phone number "{override_phone or (contact.phone_primary if contact else "")}" is not valid E.164.',
        }), 400

    user_display = (
        current_user.get_full_name() if (current_user.first_name and current_user.last_name)
        else current_user.username
    )

    test_message = (
        f'[NexVita TEST] This is a test SOS message for {user_display}. '
        f'If you received this, SMS delivery is working correctly. '
        f'No emergency action is required.'
    )

    result = ns.send_sms(target_phone, test_message)

    response = {
        'success'            : result['success'],
        'target_name'        : target_name,
        'target_phone'       : target_phone,
        'sms_configured'     : result['sms_configured'],
        'provider_message_id': result.get('provider_message_id'),   # Twilio SID
        'error'              : result.get('error'),
        'error_code'         : result.get('error_code'),
    }

    status_code = 200 if result['success'] else 500
    return jsonify(response), status_code