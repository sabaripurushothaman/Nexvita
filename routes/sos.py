from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from database.db import db
from models import User, Patient, EmergencyContact, Hospital
from services.emergency_service import EmergencyService
from services.hospital_service import HospitalService
from utils.location import get_user_location, calculate_distance as get_distance
from utils.helpers import flash_errors
from datetime import datetime
import json

sos_bp = Blueprint('sos', __name__, url_prefix='/sos')

@sos_bp.route('/')
@login_required
def index():
    # Get user's patient profile
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    # Get emergency contacts
    contacts = []
    if patient:
        contacts = EmergencyContact.query.filter_by(user_id=current_user.id).all()
    # Get nearby hospitals
    hospitals = []
    try:
        hospital_service = HospitalService()
        user_location = get_user_location()  # This would get user's current location
        if user_location:
            hospitals = hospital_service.find_nearby_hospitals(user_location['latitude'], user_location['longitude'], radius=10)  # 10km radius
    except Exception as e:
        # If location services fail, show all hospitals or none
        hospitals = Hospital.query.limit(10).all()

    return render_template('sos/index.html',
                         patient=patient,
                         contacts=contacts,
                         hospitals=hospitals)

@sos_bp.route('/emergency-contacts')
@login_required
def emergency_contacts():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    contacts = []
    if patient:
        contacts = EmergencyContact.query.filter_by(user_id=current_user.id).all()
    return render_template('sos/emergency_contacts.html',
                         patient=patient,
                         contacts=contacts)

@sos_bp.route('/emergency-contacts/add', methods=['GET', 'POST'])
@login_required
def add_emergency_contact():
    if request.method == 'POST':
        name = request.form.get('name')
        relationship = request.form.get('relationship')
        phone_primary = request.form.get('phone_primary')
        phone_secondary = request.form.get('phone_secondary')
        email = request.form.get('email')
        address = request.form.get('address')
        is_primary = 'is_primary' in request.form

        # If this is set as primary, unset any existing primary contact
        if is_primary:
            EmergencyContact.query.filter_by(user_id=current_user.id, is_primary=True).update({'is_primary': False})

        contact = EmergencyContact(
            user_id=current_user.id,
            name=name,
            relationship=relationship,
            phone_primary=phone_primary,
            phone_secondary=phone_secondary,
            email=email,
            address=address,
            is_primary=is_primary
        )
        db.session.add(contact)
        db.session.commit()
        flash('Emergency contact added successfully!', 'success')
        return redirect(url_for('sos.emergency_contacts'))

    return render_template('sos/add_emergency_contact.html')

@sos_bp.route('/emergency-contacts/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_emergency_contact(id):
    contact = EmergencyContact.query.get_or_404(id)
    # Ensure the contact belongs to the current user
    if contact.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('sos.emergency_contacts'))

    if request.method == 'POST':
        name = request.form.get('name')
        relationship = request.form.get('relationship')
        phone_primary = request.form.get('phone_primary')
        phone_secondary = request.form.get('phone_secondary')
        email = request.form.get('email')
        address = request.form.get('address')
        is_primary = 'is_primary' in request.form

        # If this is set as primary, unset any existing primary contact
        if is_primary:
            EmergencyContact.query.filter_by(user_id=current_user.id, is_primary=True).filter(EmergencyContact.id != id).update({'is_primary': False})

        contact.name = name
        contact.relationship = relationship
        contact.phone_primary = phone_primary
        contact.phone_secondary = phone_secondary
        contact.email = email
        contact.address = address
        contact.is_primary = is_primary
        contact.updated_at = datetime.utcnow()

        db.session.commit()
        flash('Emergency contact updated successfully!', 'success')
        return redirect(url_for('sos.emergency_contacts'))

    return render_template('sos/edit_emergency_contact.html', contact=contact)

@sos_bp.route('/emergency-contacts/delete/<int:id>', methods=['POST'])
@login_required
def delete_emergency_contact(id):
    contact = EmergencyContact.query.get_or_404(id)
    # Ensure the contact belongs to the current user
    if contact.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('sos.emergency_contacts'))

    db.session.delete(contact)
    db.session.commit()
    flash('Emergency contact deleted successfully!', 'success')
    return redirect(url_for('sos.emergency_contacts'))

@sos_bp.route('/hospitals')
@login_required
def hospitals():
    # Get nearby hospitals based on user location
    hospitals = []
    try:
        hospital_service = HospitalService()
        user_location = get_user_location()
        if user_location:
            hospitals = hospital_service.find_nearby_hospitals(user_location['latitude'], user_location['longitude'], radius=20)  # 20km radius
        else:
            # If location not available, show all hospitals
            hospitals = Hospital.query.all()
    except Exception as e:
        # Fallback to showing all hospitals
        hospitals = Hospital.query.all()

    return render_template('sos/hospitals.html',
                         hospitals=hospitals,
                         user_location=get_user_location())

@sos_bp.route('/trigger-sos', methods=['POST'])
@login_required
def trigger_sos():
    # This would be called when user presses the SOS button
    # Get user's current location
    user_location = get_user_location()
    patient = Patient.query.filter_by(user_id=current_user.id).first()

    # Get emergency contacts
    contacts = EmergencyContact.query.filter_by(user_id=current_user.id, is_primary=True).all()
    if not contacts:
        contacts = EmergencyContact.query.filter_by(user_id=current_user.id).limit(3).all()  # Get up to 3 contacts

    # Get nearby hospitals
    hospitals = []
    if user_location:
        hospital_service = HospitalService()
        hospitals = hospital_service.find_nearby_hospitals(user_location['latitude'], user_location['longitude'], radius=10)

    # Send SOS alerts (in a real app, this would send SMS, push notifications, etc.)
    emergency_service = EmergencyService()
    result = emergency_service.send_sos_alert(
        user_id=current_user.id,
        location=user_location,
        contacts=contacts,
        hospitals=hospitals
    )

    if result['success']:
        # Log the SOS event
        sos_log = f"SOS triggered at {datetime.utcnow().isoformat()} for user {current_user.id}"
        # In a real app, you might want to store this in a separate SOS log table
        flash('Emergency alert sent successfully! Help is on the way.', 'success')
    else:
        flash('Failed to send emergency alert. Please try again.', 'danger')

    return jsonify(result)

@sos_bp.route('/location')
@login_required
def location_sharing():
    # Share current location with emergency contacts
    user_location = get_user_location()
    if not user_location:
        flash('Unable to determine your location. Please enable location services.', 'warning')
        return redirect(url_for('sos.index'))

    # In a real app, this would send the location to emergency contacts via SMS or push notification
    # For now, we'll just show it on a map
    return render_template('sos/location_sharing.html',
                         location=user_location)