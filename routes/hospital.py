from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from database.db import db
from models import User, Hospital
from services.hospital_service import HospitalService
from utils.helpers import flash_errors
from datetime import datetime

hospital_bp = Blueprint('hospital', __name__, url_prefix='/hospital')

@hospital_bp.route('/')
@hospital_bp.route('/index')
def index():
    # Show list of hospitals with search and filter capabilities
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    city = request.args.get('city', '')
    state = request.args.get('state', '')
    emergency_services = request.args.get('emergency_services', type=bool)

    # Build query
    query = Hospital.query

    if search:
        query = query.filter(
            Hospital.name.contains(search) |
            Hospital.address.contains(search) |
            Hospital.city.contains(search)
        )

    if city:
        query = query.filter(Hospital.city.ilike(f'%{city}%'))

    if state:
        query = query.filter(Hospital.state.ilike(f'%{state}%'))

    if emergency_services is not None:
        query = query.filter(Hospital.emergency_services == emergency_services)

    # Order by name
    query = query.order_by(Hospital.name)

    # Paginate results
    hospitals = query.paginate(page=page, per_page=10, error_out=False)

    # Get unique cities and states for filter dropdowns
    cities = db.session.query(Hospital.city.distinct()).order_by(Hospital.city).all()
    cities = [c[0] for c in cities if c[0]]
    states = db.session.query(Hospital.state.distinct()).order_by(Hospital.state).all()
    states = [s[0] for s in states if s[0]]

    return render_template('hospital/index.html',
                         hospitals=hospitals,
                         search=search,
                         city=city,
                         state=state,
                         emergency_services=emergency_services,
                         cities=cities,
                         states=states)

@hospital_bp.route('/<int:id>')
def detail(id):
    hospital = Hospital.query.get_or_404(id)
    return render_template('hospital/detail.html', hospital=hospital)

@hospital_bp.route('/search')
def search():
    # AJAX endpoint for hospital search
    query = request.args.get('q', '')
    if not query or len(query) < 2:
        return jsonify([])

    hospitals = Hospital.query.filter(
        Hospital.name.contains(query) |
        Hospital.address.contains(query) |
        Hospital.city.contains(query)
    ).limit(10).all()

    results = []
    for hospital in hospitals:
        results.append({
            'id': hospital.id,
            'name': hospital.name,
            'address': hospital.address,
            'city': hospital.city,
            'state': hospital.state,
            'phone': hospital.phone,
            'emergency_services': hospital.emergency_services
        })

    return jsonify(results)

@hospital_bp.route('/nearby')
@login_required
def nearby():
    # Find hospitals near the user's current location
    # Safe default for unbound variables
    latitude = None
    longitude = None
    try:
        hospital_service = HospitalService()
        latitude = request.args.get('lat', type=float)
        longitude = request.args.get('lng', type=float)

        if latitude and longitude:
            hospitals = hospital_service.find_nearby_hospitals(latitude, longitude, radius=10)
        else:
            hospitals = Hospital.query.limit(10).all()
    except Exception:
        hospitals = Hospital.query.limit(10).all()

    return render_template('hospital/nearby.html',
                         hospitals=hospitals,
                         latitude=latitude,
                         longitude=longitude)

@hospital_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    # Only allow admins to add hospitals
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('hospital.index'))

    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        postal_code = request.form.get('postal_code')
        country = request.form.get('country')
        phone = request.form.get('phone')
        email = request.form.get('email')
        website = request.form.get('website')
        emergency_services = 'emergency_services' in request.form
        latitude = request.form.get('latitude', type=float)
        longitude = request.form.get('longitude', type=float)
        rating = request.form.get('rating', type=float)

        hospital = Hospital(
            name=name,
            address=address,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            phone=phone,
            email=email,
            website=website,
            emergency_services=emergency_services,
            latitude=latitude,
            longitude=longitude,
            rating=rating
        )

        db.session.add(hospital)
        db.session.commit()
        flash('Hospital added successfully!', 'success')
        return redirect(url_for('hospital.detail', id=hospital.id))

    return render_template('hospital/add.html')

@hospital_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    # Only allow admins to edit hospitals
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('hospital.index'))

    hospital = Hospital.query.get_or_404(id)

    if request.method == 'POST':
        hospital.name = request.form.get('name')
        hospital.address = request.form.get('address')
        hospital.city = request.form.get('city')
        hospital.state = request.form.get('state')
        hospital.postal_code = request.form.get('postal_code')
        hospital.country = request.form.get('country')
        hospital.phone = request.form.get('phone')
        hospital.email = request.form.get('email')
        hospital.website = request.form.get('website')
        hospital.emergency_services = 'emergency_services' in request.form
        hospital.latitude = request.form.get('latitude', type=float)
        hospital.longitude = request.form.get('longitude', type=float)
        hospital.rating = request.form.get('rating', type=float)
        hospital.updated_at = datetime.utcnow()

        db.session.commit()
        flash('Hospital updated successfully!', 'success')
        return redirect(url_for('hospital.detail', id=hospital.id))

    return render_template('hospital/edit.html', hospital=hospital)

@hospital_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    # Only allow admins to delete hospitals
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('hospital.index'))

    hospital = Hospital.query.get_or_404(id)
    db.session.delete(hospital)
    db.session.commit()
    flash('Hospital deleted successfully!', 'success')
    return redirect(url_for('hospital.index'))