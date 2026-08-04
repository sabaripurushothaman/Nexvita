from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from database.db import db
from models import User, Patient, HealthRecord
from utils.helpers import flash_errors
from datetime import datetime
import json

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')


@patient_bp.route('/profile')
@login_required
def profile():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    return render_template('patient/profile.html', patient=patient, user=current_user)


@patient_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    patient = Patient.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        # Personal info (User model)
        fn = request.form.get('first_name', '').strip()
        ln = request.form.get('last_name', '').strip()
        if fn: current_user.first_name = fn
        if ln: current_user.last_name  = ln

        email = request.form.get('email', '').strip()
        if email and email != current_user.email:
            existing = User.query.filter_by(email=email).first()
            if existing and existing.id != current_user.id:
                flash('Email already in use.', 'danger')
                return redirect(url_for('dashboard.profile'))
            current_user.email = email

        if patient:
            dob_str = request.form.get('date_of_birth', '').strip()
            if dob_str:
                try:
                    patient.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Invalid date of birth format.', 'warning')

            gender     = request.form.get('gender', '').strip()
            blood_type = request.form.get('blood_type', '').strip()
            phone      = request.form.get('phone', '').strip()
            if gender:     patient.gender     = gender
            if blood_type: patient.blood_type = blood_type
            if phone:      patient.phone      = phone

            patient.allergies  = request.form.get('allergies', '').strip()
            patient.address    = request.form.get('address', '').strip()
            patient.city       = request.form.get('city', '').strip()
            patient.state      = request.form.get('state', '').strip()
            patient.country    = request.form.get('country', '').strip()
            patient.updated_at = datetime.utcnow()

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('dashboard.profile'))

    return render_template('patient/edit_profile.html', patient=patient, user=current_user)