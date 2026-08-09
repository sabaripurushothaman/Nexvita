from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from database.db import db
from models import User, Patient, HealthRecord, Reminder
from datetime import datetime, timedelta
from sqlalchemy import func
import json

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    # Get user's patient profile
    patient = Patient.query.filter_by(user_id=current_user.id).first()

    # Get recent health records
    recent_records = []
    if patient:
        recent_records = HealthRecord.query.filter_by(user_id=current_user.id)\
            .order_by(HealthRecord.record_date.desc())\
            .limit(5).all()

    # Calculate some statistics for the dashboard
    total_records = HealthRecord.query.filter_by(user_id=current_user.id).count()

    # Get latest vitals if available
    latest_vitals = {}
    if recent_records:
        latest = recent_records[0]
        if latest.systolic_bp and latest.diastolic_bp:
            latest_vitals['blood_pressure'] = f"{latest.systolic_bp}/{latest.diastolic_bp}"
        if latest.heart_rate:
            latest_vitals['heart_rate'] = f"{latest.heart_rate} bpm"
        if latest.temperature:
            latest_vitals['temperature'] = f"{latest.temperature}°C"
        if latest.weight:
            latest_vitals['weight'] = f"{latest.weight} kg"
        if latest.height:
            latest_vitals['height'] = f"{latest.height} cm"
        if latest.bmi:
            latest_vitals['bmi'] = f"{latest.bmi}"

    # Get data for charts (last 7 days)
    week_ago = datetime.now() - timedelta(days=7)
    weekly_records = HealthRecord.query.filter(
        HealthRecord.user_id == current_user.id,
        HealthRecord.record_date >= week_ago
    ).order_by(HealthRecord.record_date).all()

    # Prepare data for charts — every dataset MUST be the same length as labels.
    # Use None for missing vitals so Chart.js renders a gap rather than
    # shifting data points to the wrong x-position.
    dates        = [r.record_date.strftime('%Y-%m-%d') for r in weekly_records]
    systolic_bp  = [r.systolic_bp  if r.systolic_bp  else None for r in weekly_records]
    diastolic_bp = [r.diastolic_bp if r.diastolic_bp else None for r in weekly_records]
    heart_rate   = [r.heart_rate   if r.heart_rate   else None for r in weekly_records]
    weight       = [float(r.weight) if r.weight else None for r in weekly_records]

    chart_data = {
        'labels': dates,
        'datasets': [
            {
                'label': 'Systolic BP',
                'data': systolic_bp,
                'borderColor': 'red',
                'fill': False
            },
            {
                'label': 'Diastolic BP',
                'data': diastolic_bp,
                'borderColor': 'blue',
                'fill': False
            },
            {
                'label': 'Heart Rate',
                'data': heart_rate,
                'borderColor': 'green',
                'fill': False
            },
            {
                'label': 'Weight (kg)',
                'data': weight,
                'borderColor': 'orange',
                'fill': False
            }
        ]
    }

    upcoming_reminders = (
        Reminder.query
        .filter_by(user_id=current_user.id, is_active=True)
        .order_by(Reminder.reminder_time)
        .limit(4)
        .all()
    )

    return render_template('dashboard/index.html',
                         patient=patient,
                         recent_records=recent_records,
                         total_records=total_records,
                         latest_vitals=latest_vitals,
                         chart_data=json.dumps(chart_data),
                         upcoming_reminders=upcoming_reminders)

@dashboard_bp.route('/profile')
@login_required
def profile():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    return render_template('dashboard/profile.html', patient=patient, user=current_user)


@dashboard_bp.route('/chart-data')
@login_required
def chart_data_api():
    """JSON endpoint — returns chart data for a given number of days.
    Used by the period tab buttons (7 Days / 1 Month / 3 Months).
    """
    # Sanitise: only allow the three valid period values
    try:
        days = int(request.args.get('days', 7))
    except (ValueError, TypeError):
        days = 7
    if days not in (7, 30, 90):
        days = 7

    since = datetime.now() - timedelta(days=days)
    records = (
        HealthRecord.query
        .filter(
            HealthRecord.user_id == current_user.id,
            HealthRecord.record_date >= since,
        )
        .order_by(HealthRecord.record_date)
        .all()
    )

    dates        = [r.record_date.strftime('%Y-%m-%d') for r in records]
    systolic_bp  = [r.systolic_bp  if r.systolic_bp  else None for r in records]
    diastolic_bp = [r.diastolic_bp if r.diastolic_bp else None for r in records]
    heart_rate   = [r.heart_rate   if r.heart_rate   else None for r in records]
    weight       = [float(r.weight) if r.weight else None for r in records]

    return jsonify({
        'labels': dates,
        'period_days': days,
        'datasets': [
            {'label': 'Systolic BP',  'data': systolic_bp,  'borderColor': 'red',    'fill': False},
            {'label': 'Diastolic BP', 'data': diastolic_bp, 'borderColor': 'blue',   'fill': False},
            {'label': 'Heart Rate',   'data': heart_rate,   'borderColor': 'green',  'fill': False},
            {'label': 'Weight (kg)',  'data': weight,       'borderColor': 'orange', 'fill': False},
        ],
    })