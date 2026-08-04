from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from database.db import db
from models import User, Patient, HealthRecord, Hospital
from functools import wraps


admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator to restrict access to admin users only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard – overview of system stats."""
    total_users = User.query.count()
    total_patients = Patient.query.count()
    total_records = HealthRecord.query.count()
    total_hospitals = Hospital.query.count()

    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    return render_template(
        'admin/index.html',
        total_users=total_users,
        total_patients=total_patients,
        total_records=total_records,
        total_hospitals=total_hospitals,
        recent_users=recent_users
    )


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """List all users."""
    page = request.args.get('page', 1, type=int)
    users_paginated = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/users.html', users=users_paginated)


@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@login_required
@admin_required
def toggle_user_active(user_id):
    """Toggle a user's active status."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot deactivate your own account'}), 400
    user.is_active = not user.is_active
    db.session.commit()
    status = 'activated' if user.is_active else 'deactivated'
    return jsonify({'success': True, 'message': f'User {status} successfully', 'is_active': user.is_active})


@admin_bp.route('/hospitals')
@login_required
@admin_required
def hospitals():
    """Admin view of all hospitals."""
    hospitals_list = Hospital.query.order_by(Hospital.name).all()
    return render_template('admin/hospitals.html', hospitals=hospitals_list)
