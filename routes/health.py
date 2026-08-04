from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from database.db import db
from models import User, Patient, HealthRecord
from utils.helpers import flash_errors
from datetime import datetime
import json

health_bp = Blueprint('health', __name__, url_prefix='/health')


@health_bp.route('/')
@login_required
def index():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    page = request.args.get('page', 1, type=int)
    records = HealthRecord.query.filter_by(user_id=current_user.id)\
        .order_by(HealthRecord.record_date.desc())\
        .paginate(page=page, per_page=15, error_out=False)
    return render_template('health/index.html', records=records, patient=patient)


@health_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_record():
    patient = Patient.query.filter_by(user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        record_type = request.form.get('record_type', '').strip()
        if not record_type:
            flash('Record type is required.', 'danger')
            return render_template('health/add_record.html', patient=patient)

        def safe_float(val):
            try:
                return float(val) if val else None
            except ValueError:
                return None

        def safe_int(val):
            try:
                return int(val) if val else None
            except ValueError:
                return None

        weight = safe_float(request.form.get('weight'))
        height = safe_float(request.form.get('height'))

        record = HealthRecord(
            user_id=current_user.id,
            record_type=record_type,
            recorded_by=current_user.id,
            systolic_bp=safe_int(request.form.get('systolic_bp')),
            diastolic_bp=safe_int(request.form.get('diastolic_bp')),
            heart_rate=safe_int(request.form.get('heart_rate')),
            temperature=safe_float(request.form.get('temperature')),
            respiratory_rate=safe_int(request.form.get('respiratory_rate')),
            oxygen_saturation=safe_float(request.form.get('oxygen_saturation')),
            weight=weight,
            height=height,
            glucose_level=safe_float(request.form.get('glucose_level')),
            cholesterol_total=safe_float(request.form.get('cholesterol_total')),
            hdl_cholesterol=safe_float(request.form.get('hdl_cholesterol')),
            ldl_cholesterol=safe_float(request.form.get('ldl_cholesterol')),
            triglycerides=safe_float(request.form.get('triglycerides')),
            symptoms=request.form.get('symptoms', '').strip() or None,
            diagnosis=request.form.get('diagnosis', '').strip() or None,
            treatment=request.form.get('treatment', '').strip() or None,
            medications=request.form.get('medications', '').strip() or None,
            notes=request.form.get('notes', '').strip() or None,
            is_private='is_private' in request.form,
        )

        # Auto-calculate BMI
        if weight and height and height > 0:
            height_m = height / 100
            record.bmi = round(weight / (height_m ** 2), 2)

        db.session.add(record)
        db.session.commit()
        flash('Health record added successfully!', 'success')
        return redirect(url_for('health.index'))

    return render_template('health/add_record.html', patient=patient)


@health_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_record(id):
    record = HealthRecord.query.get_or_404(id)
    if record.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('health.index'))

    patient = Patient.query.filter_by(user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        def safe_float(val):
            try:
                return float(val) if val else None
            except ValueError:
                return None

        def safe_int(val):
            try:
                return int(val) if val else None
            except ValueError:
                return None

        record.record_type = request.form.get('record_type', record.record_type).strip()
        record.systolic_bp = safe_int(request.form.get('systolic_bp'))
        record.diastolic_bp = safe_int(request.form.get('diastolic_bp'))
        record.heart_rate = safe_int(request.form.get('heart_rate'))
        record.temperature = safe_float(request.form.get('temperature'))
        record.respiratory_rate = safe_int(request.form.get('respiratory_rate'))
        record.oxygen_saturation = safe_float(request.form.get('oxygen_saturation'))
        record.weight = safe_float(request.form.get('weight'))
        record.height = safe_float(request.form.get('height'))
        record.glucose_level = safe_float(request.form.get('glucose_level'))
        record.cholesterol_total = safe_float(request.form.get('cholesterol_total'))
        record.hdl_cholesterol = safe_float(request.form.get('hdl_cholesterol'))
        record.ldl_cholesterol = safe_float(request.form.get('ldl_cholesterol'))
        record.triglycerides = safe_float(request.form.get('triglycerides'))
        record.symptoms = request.form.get('symptoms', '').strip() or None
        record.diagnosis = request.form.get('diagnosis', '').strip() or None
        record.treatment = request.form.get('treatment', '').strip() or None
        record.medications = request.form.get('medications', '').strip() or None
        record.notes = request.form.get('notes', '').strip() or None
        record.is_private = 'is_private' in request.form
        record.updated_at = datetime.utcnow()

        # Recalculate BMI
        if record.weight and record.height and float(record.height) > 0:
            h_m = float(record.height) / 100
            record.bmi = round(float(record.weight) / (h_m ** 2), 2)
        else:
            record.bmi = None

        db.session.commit()
        flash('Health record updated successfully!', 'success')
        return redirect(url_for('health.index'))

    return render_template('health/edit_record.html', record=record, patient=patient)


@health_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_record(id):
    record = HealthRecord.query.get_or_404(id)
    if record.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    db.session.delete(record)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Health record deleted'})


@health_bp.route('/view/<int:id>')
@login_required
def view_record(id):
    record = HealthRecord.query.get_or_404(id)
    if record.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('health.index'))
    patient = Patient.query.filter_by(user_id=current_user.id).first_or_404()
    return render_template('health/view_record.html', record=record, patient=patient)


@health_bp.route('/charts')
@login_required
def charts():
    patient = Patient.query.filter_by(user_id=current_user.id).first_or_404()
    records = HealthRecord.query.filter_by(user_id=current_user.id)\
        .order_by(HealthRecord.record_date).limit(50).all()

    dates = [r.record_date.strftime('%Y-%m-%d') for r in records]
    systolic_bp = [r.systolic_bp for r in records if r.systolic_bp is not None]
    diastolic_bp = [r.diastolic_bp for r in records if r.diastolic_bp is not None]
    heart_rate = [r.heart_rate for r in records if r.heart_rate is not None]
    weight = [float(r.weight) for r in records if r.weight is not None]

    chart_data = {
        'labels': dates,
        'datasets': [
            {'label': 'Systolic BP (mmHg)', 'data': systolic_bp,
             'borderColor': 'rgba(255, 99, 132, 1)', 'backgroundColor': 'rgba(255, 99, 132, 0.2)',
             'fill': False, 'borderWidth': 2},
            {'label': 'Diastolic BP (mmHg)', 'data': diastolic_bp,
             'borderColor': 'rgba(54, 162, 235, 1)', 'backgroundColor': 'rgba(54, 162, 235, 0.2)',
             'fill': False, 'borderWidth': 2},
            {'label': 'Heart Rate (bpm)', 'data': heart_rate,
             'borderColor': 'rgba(75, 192, 192, 1)', 'backgroundColor': 'rgba(75, 192, 192, 0.2)',
             'fill': False, 'borderWidth': 2},
            {'label': 'Weight (kg)', 'data': weight,
             'borderColor': 'rgba(255, 206, 86, 1)', 'backgroundColor': 'rgba(255, 206, 86, 0.2)',
             'fill': False, 'borderWidth': 2},
        ]
    }

    return render_template('health/charts.html', chart_data=chart_data, patient=patient)