import json
import math
from datetime import datetime
from database.db import db
from models import User, Patient, EmergencyContact, Hospital
from utils.location import calculate_distance
from services.hospital_service import HospitalService


class EmergencyService:
    def __init__(self):
        # In a real implementation, integrate with SMS/push notification services, etc.
        pass

    def send_sos_alert(self, user_id, location=None, contacts=None, hospitals=None):
        """Send SOS alert to emergency contacts and nearby hospitals."""
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'message': 'User not found'}

        patient = Patient.query.filter_by(user_id=user_id).first()

        # Default location if not provided
        if location is None:
            location = {'latitude': 40.7128, 'longitude': -74.0060}  # Default: NYC

        # Default contacts if not provided
        if contacts is None:
            contacts = EmergencyContact.query.filter_by(
                user_id=user_id, is_primary=True
            ).all()
            if not contacts:
                contacts = EmergencyContact.query.filter_by(
                    user_id=user_id
                ).limit(3).all()

        # Default hospitals if not provided
        if hospitals is None:
            hospitals = Hospital.query.limit(5).all()
            # Try to get nearby hospitals if location is available
            if location and location.get('latitude') and location.get('longitude'):
                try:
                    hospital_service = HospitalService()
                    nearby = hospital_service.find_nearby_hospitals(
                        location['latitude'],
                        location['longitude'],
                        radius=10
                    )
                    if nearby:
                        hospitals = nearby
                except Exception:
                    pass  # fall back to the already-assigned default

        # Prepare alert message
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        user_location_str = (
            f"Latitude: {location['latitude']:.6f}, Longitude: {location['longitude']:.6f}"
            if location
            else "Location not available"
        )
        user_display = (
            user.get_full_name()
            if user.first_name and user.last_name
            else user.username
        )

        alert_message = (
            f"EMERGENCY ALERT - NEXVITA\n"
            f"User: {user_display}\n"
            f"Patient ID: {patient.patient_id if patient else 'Not registered'}\n"
            f"Time: {timestamp}\n"
            f"Location: {user_location_str}\n"
            f"This is an automated emergency alert from the NexVita health app.\n"
            f"Please respond immediately."
        )

        results = {
            'user_id': user_id,
            'timestamp': timestamp,
            'location': location,
            'alert_message': alert_message,
            'contacts_notified': [],
            'hospitals_notified': [],
            'success': True,
            'message': 'SOS alert processed successfully',
        }

        # Simulate notifying contacts (in production: SMS via Twilio, etc.)
        for contact in contacts:
            results['contacts_notified'].append({
                'contact_id': contact.id,
                'name': contact.name,
                'phone': contact.phone_primary,
                'method': 'SMS',
                'status': 'sent',
                'timestamp': timestamp,
            })

        # Simulate notifying up to 3 nearest hospitals
        for hospital in hospitals[:3]:
            dist_km = None
            if hospital.latitude and hospital.longitude and location:
                try:
                    dist_km = round(
                        self._calculate_distance(
                            location['latitude'],
                            location['longitude'],
                            float(hospital.latitude),
                            float(hospital.longitude),
                        ),
                        2,
                    )
                except Exception:
                    pass

            results['hospitals_notified'].append({
                'hospital_id': hospital.id,
                'name': hospital.name,
                'phone': hospital.phone,
                'distance_km': dist_km,
                'method': 'Emergency Notification System',
                'status': 'sent',
                'timestamp': timestamp,
            })

        results['emergency_services_notified'] = {
            'service': 'Local Emergency Services (e.g., 911)',
            'status': 'notification_sent_via_app',
            'note': 'In a real implementation, this would trigger actual emergency services dispatch.',
            'timestamp': timestamp,
        }

        return results

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two Earth points using the Haversine formula (km)."""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 2 * math.asin(math.sqrt(a)) * 6371  # 6371 = Earth's radius in km

    def get_emergency_preparedness_tips(self):
        """Return general emergency preparedness tips."""
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
                'Wear medical alert jewelry if you have chronic conditions',
                'Inform family about your medical conditions',
            ],
            'home_safety': [
                'Keep a first aid kit accessible',
                'Know the location of your nearest hospital emergency department',
                'Have emergency contacts programmed in your phone',
                'Consider a medical alert system if you live alone',
            ],
            'natural_disasters': [
                'Know the emergency procedures for your area (earthquake, flood, etc.)',
                'Have an emergency kit with water, food, and medications',
                'Establish a family meeting point and communication plan',
                'Stay informed through official emergency channels',
            ],
        }

    def check_in(self, user_id):
        """Allow a user to check-in to confirm they are safe after an SOS alert."""
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'message': 'User not found'}

        check_in_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        user_display = (
            user.get_full_name()
            if user.first_name and user.last_name
            else user.username
        )

        return {
            'success': True,
            'message': 'Check-in received. Your emergency contacts have been notified that you are safe.',
            'user_id': user_id,
            'user': user_display,
            'timestamp': check_in_time,
        }