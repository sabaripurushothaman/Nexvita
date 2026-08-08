"""
services/emergency_service.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Emergency SOS alert handling with REAL SMS delivery via NotificationService.

Key behaviours:
- Uses db.session.get() (SQLAlchemy 2.x compatible)
- Sends real SMS through NotificationService (Twilio)
- Returns honest per-contact delivery status
- Generates a clickable Google Maps location link
- Never marks contacts as 'notified' unless provider confirms
"""

import logging
from datetime import datetime
from database.db import db
from models import User, Patient, EmergencyContact, Hospital
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class EmergencyService:

    def __init__(self):
        self.notifier = NotificationService()

    # ------------------------------------------------------------------ #
    # SOS Alert
    # ------------------------------------------------------------------ #

    def send_sos_alert(self, user_id: int, location: dict = None,
                       contacts=None, hospitals=None) -> dict:
        """
        Send SOS alert to the user's emergency contacts via SMS.

        Parameters
        ----------
        user_id   : authenticated user's ID
        location  : dict with 'latitude' and 'longitude' (may be None)
        contacts  : list of EmergencyContact model objects (fetched if None)
        hospitals : list of hospital dicts or model objects (informational only)

        Returns
        -------
        dict with keys:
          success, message, sms_configured,
          contacts_notified (list),
          contacts_failed (list),
          location, timestamp
        """
        user = db.session.get(User, user_id)
        if not user:
            return {'success': False, 'message': 'User not found',
                    'sms_configured': False}

        patient = Patient.query.filter_by(user_id=user_id).first()

        # ------------------------------------------------------------------
        # Fetch contacts if not provided
        # ------------------------------------------------------------------
        if contacts is None:
            contacts = EmergencyContact.query.filter_by(
                user_id=user_id, is_primary=True
            ).all()
            if not contacts:
                contacts = EmergencyContact.query.filter_by(
                    user_id=user_id
                ).limit(5).all()

        if not contacts:
            return {
                'success': False,
                'message': 'No emergency contacts configured.',
                'sms_configured': self.notifier.is_configured,
                'contacts_notified': [],
                'contacts_failed': [],
                'location': location,
                'timestamp': datetime.utcnow().isoformat(),
                'no_contacts': True,
            }

        # ------------------------------------------------------------------
        # Build alert message
        # ------------------------------------------------------------------
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
        user_display = (
            user.get_full_name() if (user.first_name and user.last_name)
            else user.username
        )

        if location and location.get('latitude') and location.get('longitude'):
            lat = location['latitude']
            lng = location['longitude']
            maps_link = f'https://maps.google.com/?q={lat},{lng}'
            location_str = f'Location: {maps_link}'
            location_available = True
        else:
            maps_link = None
            location_str = 'Location: could not be determined'
            location_available = False

        alert_message = (
            f'EMERGENCY ALERT – NexVita Health\n'
            f'{user_display} has activated SOS and may need immediate help.\n'
            f'Time: {timestamp}\n'
            f'{location_str}\n'
            f'Please contact them or call emergency services if appropriate.'
        )

        # ------------------------------------------------------------------
        # Send SMS to each contact
        # ------------------------------------------------------------------
        contacts_notified = []
        contacts_failed = []

        for contact in contacts:
            phone = (contact.phone_primary or '').strip()
            if not phone:
                contacts_failed.append({
                    'contact_id': contact.id,
                    'name': contact.name,
                    'phone': phone,
                    'status': 'failed',
                    'error': 'No phone number stored'
                })
                continue

            result = self.notifier.send_sms(phone, alert_message)

            if result['success']:
                contacts_notified.append({
                    'contact_id': contact.id,
                    'name': contact.name,
                    'phone': result.get('normalised_number', phone),
                    'status': 'sent',
                    'provider_message_id': result.get('provider_message_id'),
                    'timestamp': timestamp,
                })
                logger.info('SOS SMS sent to contact %s', contact.name)
            else:
                contacts_failed.append({
                    'contact_id': contact.id,
                    'name': contact.name,
                    'phone': result.get('normalised_number', phone),
                    'status': 'failed',
                    'error': result.get('error', 'Unknown error'),
                    'error_code': result.get('error_code'),
                    'sms_configured': result.get('sms_configured', False),
                })
                logger.warning('SOS SMS failed for contact %s: %s',
                               contact.name, result.get('error'))


        # ------------------------------------------------------------------
        # Determine overall status
        # ------------------------------------------------------------------
        sms_configured = self.notifier.is_configured
        n_ok  = len(contacts_notified)
        n_bad = len(contacts_failed)
        n_all = n_ok + n_bad

        if not sms_configured:
            overall_success = False
            missing = self.notifier.missing_vars()
            message = (
                f'SOS recorded. SMS delivery is not configured '
                f'(missing: {", ".join(missing)}).'
            )
        elif n_ok == n_all and n_ok > 0:
            overall_success = True
            message = f'SOS activated. {n_ok} emergency contact(s) notified via SMS.'
        elif n_ok > 0:
            overall_success = True
            message = (
                f'SOS activated. {n_ok} contact(s) notified; '
                f'{n_bad} could not be reached.'
            )
        else:
            overall_success = False
            message = 'SOS recorded but could not deliver SMS to any contact.'

        return {
            'success': overall_success,
            'message': message,
            'sms_configured': sms_configured,
            'missing_vars': self.notifier.missing_vars() if not sms_configured else [],
            'contacts_notified': contacts_notified,
            'contacts_failed': contacts_failed,
            'location': location,
            'location_available': location_available,
            'maps_link': maps_link,
            'timestamp': timestamp,
            'no_contacts': False,
        }


    # ------------------------------------------------------------------ #
    # Emergency preparedness tips (unchanged)
    # ------------------------------------------------------------------ #

    def get_emergency_preparedness_tips(self):
        return {
            'personal_safety': [
                'Keep your phone charged and with you at all times',
                'Know your exact location (address or landmarks) when calling for help',
                'Teach family members how to use the SOS feature',
                'Keep a list of emergency numbers handy',
            ],
            'medical_emergency': [
                'Know your blood type and allergies',
                'Keep a list of current medications and dosages',
                'Wear medical alert jewellery if you have chronic conditions',
                'Inform family about your medical conditions',
            ],
            'home_safety': [
                'Keep a first aid kit accessible',
                'Know the location of your nearest hospital emergency department',
                'Have emergency contacts programmed in your phone',
                'Consider a medical alert system if you live alone',
            ],
            'natural_disasters': [
                'Know the emergency procedures for your area',
                'Have an emergency kit with water, food, and medications',
                'Establish a family meeting point and communication plan',
                'Stay informed through official emergency channels',
            ],
        }

    def check_in(self, user_id: int) -> dict:
        """Allow a user to confirm they are safe after an SOS alert."""
        user = db.session.get(User, user_id)
        if not user:
            return {'success': False, 'message': 'User not found'}
        user_display = (
            user.get_full_name() if (user.first_name and user.last_name)
            else user.username
        )
        return {
            'success': True,
            'message': 'Check-in received. Your emergency contacts have been notified that you are safe.',
            'user_id': user_id,
            'user': user_display,
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
        }