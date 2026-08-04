from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from database.db import db
from models import User, Patient
from utils.validators import validate_email, validate_password
from utils.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember_me = 'remember_me' in request.form

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/login.html')

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'warning')
                return render_template('auth/login.html')
            login_user(user, remember=remember_me)
            user.last_login = datetime.utcnow()
            db.session.commit()
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard.index')
            return redirect(next_page)
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()

        # Validate inputs
        errors = []
        if not username:
            errors.append('Username is required.')
        if not validate_email(email):
            errors.append('A valid email address is required.')
        if not validate_password(password):
            errors.append('Password must be at least 8 characters and contain a letter and a number.')
        if User.query.filter_by(email=email).first():
            errors.append('An account with that email already exists.')
        if User.query.filter_by(username=username).first():
            errors.append('That username is already taken.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('auth/register.html')

        # Create user with role 'patient'
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role='patient',
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # Get user.id before committing

        # Create a patient profile — patient_id auto-generated via model default
        patient = Patient(user_id=user.id)
        db.session.add(patient)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)