"""
routes/hospital.py
~~~~~~~~~~~~~~~~~~~
Hospital directory routes + the /api/hospitals/nearby JSON endpoint.

Changes from original:
- Added GET /api/hospitals/nearby  – calls Overpass API, returns JSON
- Fixed url_for('hospital.view') → url_for('hospital.detail') in template
- All legacy Hospital.query.get() → db.session.get()
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from database.db import db
from models import User, Hospital
from services.hospital_service import HospitalService
from utils.helpers import flash_errors
from datetime import datetime

hospital_bp = Blueprint('hospital', __name__, url_prefix='/hospital')


# ------------------------------------------------------------------ #
# Hospital Directory (now client-side dynamic)
# ------------------------------------------------------------------ #

@hospital_bp.route('/')
@hospital_bp.route('/index')
@login_required
def index():
    """
    Hospital directory page.
    The page itself renders a shell; actual hospital data is loaded
    client-side via /api/hospitals/nearby after the browser obtains
    geolocation.
    """
    # Still provide any admin-seeded DB hospitals as a fallback JSON blob
    # (used only when Overpass is unavailable)
    return render_template('hospital/index.html')


@hospital_bp.route('/<int:id>')
@hospital_bp.route('/detail/<int:id>')
def detail(id):
    hospital = db.session.get(Hospital, id)
    if hospital is None:
        flash('Hospital not found.', 'warning')
        return redirect(url_for('hospital.index'))
    return render_template('hospital/detail.html', hospital=hospital)


@hospital_bp.route('/search')
def search():
    """AJAX text search against the local DB."""
    query = request.args.get('q', '')
    if not query or len(query) < 2:
        return jsonify([])

    hospitals = Hospital.query.filter(
        Hospital.name.contains(query) |
        Hospital.address.contains(query) |
        Hospital.city.contains(query)
    ).limit(10).all()

    results = []
    for h in hospitals:
        results.append({
            'id': h.id,
            'name': h.name,
            'address': h.address,
            'city': h.city,
            'state': h.state,
            'phone': h.phone,
            'emergency_services': h.emergency_services
        })
    return jsonify(results)


# ------------------------------------------------------------------ #
# *** NEW *** – Live nearby hospital API endpoint
# ------------------------------------------------------------------ #

@hospital_bp.route('/api/nearby')
@login_required
def api_nearby():
    """
    GET /hospital/api/nearby?lat=<latitude>&lng=<longitude>&radius=<km>

    Returns normalised JSON from OpenStreetMap Overpass API.
    Also registered at /api/hospitals/nearby via app.py for convenience.

    Response schema:
    {
      "success": bool,
      "hospitals": [
        {
          "name": str,
          "address": str,
          "latitude": float,
          "longitude": float,
          "distance_km": float,
          "phone": str,
          "rating": null,
          "open_now": bool | null,
          "place_id": str,
          "maps_url": str,
          "emergency_services": bool
        }
      ],
      "count": int,
      "source": "overpass",
      "error": str | null,
      "attribution": str
    }
    """
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        radius = request.args.get('radius', default=10, type=float)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'hospitals': [], 'count': 0,
                        'error': 'Invalid parameters'}), 400

    # Input validation
    if lat is None or lng is None:
        return jsonify({'success': False, 'hospitals': [], 'count': 0,
                        'error': 'lat and lng parameters are required'}), 400

    if not (-90 <= lat <= 90):
        return jsonify({'success': False, 'hospitals': [], 'count': 0,
                        'error': 'latitude must be between -90 and 90'}), 400

    if not (-180 <= lng <= 180):
        return jsonify({'success': False, 'hospitals': [], 'count': 0,
                        'error': 'longitude must be between -180 and 180'}), 400

    radius = max(1, min(radius, 50))   # clamp 1–50 km

    hospital_service = HospitalService()
    result = hospital_service.find_nearby_hospitals_api(lat, lng, radius_km=radius)
    return jsonify(result)


# ------------------------------------------------------------------ #
# Legacy nearby page (kept for sos/hospitals.html compatibility)
# ------------------------------------------------------------------ #

@hospital_bp.route('/nearby')
@login_required
def nearby():
    """
    Nearby hospitals page (shell – data loaded client-side).
    Accepts optional lat/lng query params to pass as JS hints.
    """
    latitude  = request.args.get('lat',  type=float)
    longitude = request.args.get('lng',  type=float)
    return render_template('hospital/nearby.html',
                           latitude=latitude, longitude=longitude)


# ------------------------------------------------------------------ #
# Admin-only CRUD
# ------------------------------------------------------------------ #

@hospital_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('hospital.index'))

    if request.method == 'POST':
        hospital = Hospital(
            name=request.form.get('name'),
            address=request.form.get('address'),
            city=request.form.get('city'),
            state=request.form.get('state'),
            postal_code=request.form.get('postal_code'),
            country=request.form.get('country') or 'India',
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            website=request.form.get('website'),
            emergency_services='emergency_services' in request.form,
            latitude=request.form.get('latitude', type=float),
            longitude=request.form.get('longitude', type=float),
            rating=request.form.get('rating', type=float),
        )
        db.session.add(hospital)
        db.session.commit()
        flash('Hospital added successfully!', 'success')
        return redirect(url_for('hospital.detail', id=hospital.id))

    return render_template('hospital/add.html')


@hospital_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('hospital.index'))

    hospital = db.session.get(Hospital, id)
    if hospital is None:
        flash('Hospital not found.', 'warning')
        return redirect(url_for('hospital.index'))

    if request.method == 'POST':
        hospital.name              = request.form.get('name')
        hospital.address           = request.form.get('address')
        hospital.city              = request.form.get('city')
        hospital.state             = request.form.get('state')
        hospital.postal_code       = request.form.get('postal_code')
        hospital.country           = request.form.get('country')
        hospital.phone             = request.form.get('phone')
        hospital.email             = request.form.get('email')
        hospital.website           = request.form.get('website')
        hospital.emergency_services = 'emergency_services' in request.form
        hospital.latitude          = request.form.get('latitude',  type=float)
        hospital.longitude         = request.form.get('longitude', type=float)
        hospital.rating            = request.form.get('rating',    type=float)
        hospital.updated_at        = datetime.utcnow()
        db.session.commit()
        flash('Hospital updated successfully!', 'success')
        return redirect(url_for('hospital.detail', id=hospital.id))

    return render_template('hospital/edit.html', hospital=hospital)


@hospital_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('hospital.index'))

    hospital = db.session.get(Hospital, id)
    if hospital is None:
        flash('Hospital not found.', 'warning')
        return redirect(url_for('hospital.index'))

    db.session.delete(hospital)
    db.session.commit()
    flash('Hospital deleted successfully!', 'success')
    return redirect(url_for('hospital.index'))