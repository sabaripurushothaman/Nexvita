"""
Health Records Blueprint — Dynamic Medical Records Management
Routes: index, add, edit, delete, view, duplicate, timeline,
        charts, chart_data (API), export, upload, download
"""
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, jsonify, send_from_directory, current_app)
from flask_login import login_required, current_user
from database.db import db
from models import Patient, HealthRecord
from utils.constants import (HEALTH_CATEGORIES, HEALTH_RECORD_PRESET_TYPES,
                              SEVERITY_LEVELS, RECORD_STATUS,
                              ALLOWED_ATTACHMENT_EXTENSIONS)
from datetime import datetime, date
import json
import os
import uuid

health_bp = Blueprint('health', __name__, url_prefix='/health')


# ── Helpers ────────────────────────────────────────────────────────────────

def _safe_float(val):
    try:
        return float(val) if val else None
    except (ValueError, TypeError):
        return None


def _safe_int(val):
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None


def _parse_date(val):
    if not val:
        return None
    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d'):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def _user_upload_dir():
    """Return (and create) the per-user upload directory."""
    try:
        base = os.path.join(current_app.root_path, 'uploads', 'health',
                            str(current_user.id))
        os.makedirs(base, exist_ok=True)
        return base
    except OSError:
        import tempfile
        base = os.path.join(tempfile.gettempdir(), 'uploads', 'health',
                            str(current_user.id))
        os.makedirs(base, exist_ok=True)
        return base


def _allowed_file(filename):
    if '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in ALLOWED_ATTACHMENT_EXTENSIONS


def _record_from_form(record, form):
    """Populate a HealthRecord from form data (used by both add and edit)."""
    record.record_type  = form.get('record_type', 'custom').strip() or 'custom'
    record.title        = form.get('title', '').strip() or None
    record.category     = form.get('category', 'custom').strip() or 'custom'
    record.description  = form.get('description', '').strip() or None
    record.result_value = form.get('result_value', '').strip() or None
    record.result_unit  = form.get('result_unit', '').strip() or None
    record.severity     = form.get('severity', 'normal') or 'normal'
    record.status       = form.get('status', 'active') or 'active'
    record.doctor_name  = form.get('doctor_name', '').strip() or None
    record.hospital_name= form.get('hospital_name', '').strip() or None
    record.record_date  = _parse_date(form.get('record_date')) or datetime.utcnow()
    record.follow_up_date = _parse_date(form.get('follow_up_date'))
    record.notes        = form.get('notes', '').strip() or None
    record.is_private   = 'is_private' in form

    # Tags — comma-separated string → JSON list
    raw_tags = form.get('tags', '')
    if raw_tags:
        tags = [t.strip() for t in raw_tags.split(',') if t.strip()]
        record.set_tags_list(tags)
    else:
        record.set_tags_list([])

    # Legacy vital fields (still accepted from the form for backward compat)
    record.systolic_bp       = _safe_int(form.get('systolic_bp'))
    record.diastolic_bp      = _safe_int(form.get('diastolic_bp'))
    record.heart_rate        = _safe_int(form.get('heart_rate'))
    record.temperature       = _safe_float(form.get('temperature'))
    record.respiratory_rate  = _safe_int(form.get('respiratory_rate'))
    record.oxygen_saturation = _safe_float(form.get('oxygen_saturation'))
    record.weight            = _safe_float(form.get('weight'))
    record.height            = _safe_float(form.get('height'))
    record.glucose_level     = _safe_float(form.get('glucose_level'))
    record.cholesterol_total = _safe_float(form.get('cholesterol_total'))
    record.hdl_cholesterol   = _safe_float(form.get('hdl_cholesterol'))
    record.ldl_cholesterol   = _safe_float(form.get('ldl_cholesterol'))
    record.triglycerides     = _safe_float(form.get('triglycerides'))

    # Auto-calculate BMI from weight + height
    w = record.weight
    h = record.height
    if w and h and float(h) > 0:
        h_m = float(h) / 100
        record.bmi = round(float(w) / (h_m ** 2), 2)
    else:
        record.bmi = None

    return record


def _build_query(user_id):
    """Build a filtered, searched HealthRecord query from request.args."""
    q = HealthRecord.query.filter_by(user_id=user_id)

    # Search
    search = request.args.get('q', '').strip()
    if search:
        like = f'%{search}%'
        q = q.filter(
            db.or_(
                HealthRecord.title.ilike(like),
                HealthRecord.record_type.ilike(like),
                HealthRecord.doctor_name.ilike(like),
                HealthRecord.hospital_name.ilike(like),
                HealthRecord.description.ilike(like),
                HealthRecord.tags.ilike(like),
            )
        )

    # Filters
    cat = request.args.get('category', '')
    if cat:
        q = q.filter(HealthRecord.category == cat)

    sev = request.args.get('severity', '')
    if sev:
        q = q.filter(HealthRecord.severity == sev)

    status = request.args.get('status', '')
    if status:
        q = q.filter(HealthRecord.status == status)

    date_from = _parse_date(request.args.get('date_from', ''))
    if date_from:
        q = q.filter(HealthRecord.record_date >= date_from)

    date_to = _parse_date(request.args.get('date_to', ''))
    if date_to:
        q = q.filter(HealthRecord.record_date <= date_to)

    return q


# ── Routes ─────────────────────────────────────────────────────────────────

@health_bp.route('/')
@login_required
def index():
    """Main page — stats dashboard + searchable table + timeline toggle."""
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    page    = request.args.get('page', 1, type=int)
    view    = request.args.get('view', 'table')          # table | timeline

    base_q  = _build_query(current_user.id)
    records = base_q.order_by(HealthRecord.record_date.desc())\
                    .paginate(page=page, per_page=15, error_out=False)

    # Dashboard stats
    all_records = HealthRecord.query.filter_by(user_id=current_user.id)
    total       = all_records.count()
    critical    = all_records.filter(HealthRecord.severity == 'critical').count()
    today       = date.today()
    follow_ups  = all_records.filter(
        HealthRecord.follow_up_date >= datetime.combine(today, datetime.min.time())
    ).count()

    # Category breakdown
    category_counts = {}
    for rec in all_records.all():
        cat = rec.category or 'custom'
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Most frequent category
    most_frequent = max(category_counts, key=category_counts.get) \
                    if category_counts else None

    return render_template(
        'health/index.html',
        records=records,
        patient=patient,
        view=view,
        total=total,
        critical=critical,
        follow_ups=follow_ups,
        most_frequent=most_frequent,
        category_counts=category_counts,
        HEALTH_CATEGORIES=HEALTH_CATEGORIES,
        HEALTH_RECORD_PRESET_TYPES=HEALTH_RECORD_PRESET_TYPES,
        SEVERITY_LEVELS=SEVERITY_LEVELS,
        RECORD_STATUS=RECORD_STATUS,
        # Pass filters back to template
        search_query=request.args.get('q', ''),
        filter_category=request.args.get('category', ''),
        filter_severity=request.args.get('severity', ''),
        filter_status=request.args.get('status', ''),
        filter_date_from=request.args.get('date_from', ''),
        filter_date_to=request.args.get('date_to', ''),
    )


@health_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_record():
    """Add a new health record."""
    patient = Patient.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        record = HealthRecord(user_id=current_user.id, recorded_by=current_user.id)
        _record_from_form(record, request.form)

        db.session.add(record)
        db.session.flush()  # get record.id before file upload

        # File upload
        f = request.files.get('attachment')
        if f and f.filename and _allowed_file(f.filename):
            ext = f.filename.rsplit('.', 1)[1].lower()
            safe_name = f'{uuid.uuid4().hex}.{ext}'
            save_path = os.path.join(_user_upload_dir(), safe_name)
            f.save(save_path)
            record.attachment_path = os.path.join('health', str(current_user.id), safe_name)
            record.attachment_name = f.filename

        db.session.commit()
        flash('Health record added successfully!', 'success')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'record': record.to_dict()})
        return redirect(url_for('health.index'))

    return render_template(
        'health/index.html',
        show_add_modal=True,
        patient=patient,
        HEALTH_CATEGORIES=HEALTH_CATEGORIES,
        HEALTH_RECORD_PRESET_TYPES=HEALTH_RECORD_PRESET_TYPES,
        SEVERITY_LEVELS=SEVERITY_LEVELS,
        RECORD_STATUS=RECORD_STATUS,
    )


@health_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_record(id):
    """Edit an existing health record."""
    record = HealthRecord.query.get_or_404(id)
    if record.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('health.index'))

    if request.method == 'POST':
        _record_from_form(record, request.form)
        record.updated_at = datetime.utcnow()

        # New file upload (replaces old attachment)
        f = request.files.get('attachment')
        if f and f.filename and _allowed_file(f.filename):
            # Remove old file if exists
            if record.attachment_path:
                old = os.path.join(current_app.root_path, 'uploads', record.attachment_path)
                if os.path.exists(old):
                    os.remove(old)
            ext = f.filename.rsplit('.', 1)[1].lower()
            safe_name = f'{uuid.uuid4().hex}.{ext}'
            save_path = os.path.join(_user_upload_dir(), safe_name)
            f.save(save_path)
            record.attachment_path = os.path.join('health', str(current_user.id), safe_name)
            record.attachment_name = f.filename

        db.session.commit()
        flash('Health record updated successfully!', 'success')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'record': record.to_dict()})
        return redirect(url_for('health.index'))

    patient = Patient.query.filter_by(user_id=current_user.id).first()
    return render_template(
        'health/edit_record.html',
        record=record,
        patient=patient,
        HEALTH_CATEGORIES=HEALTH_CATEGORIES,
        HEALTH_RECORD_PRESET_TYPES=HEALTH_RECORD_PRESET_TYPES,
        SEVERITY_LEVELS=SEVERITY_LEVELS,
        RECORD_STATUS=RECORD_STATUS,
    )


@health_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_record(id):
    """Delete a record (JSON response)."""
    record = HealthRecord.query.get_or_404(id)
    if record.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    # Remove attachment file
    if record.attachment_path:
        fpath = os.path.join(current_app.root_path, 'uploads', record.attachment_path)
        if os.path.exists(fpath):
            os.remove(fpath)

    db.session.delete(record)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Record deleted'})


@health_bp.route('/view/<int:id>')
@login_required
def view_record(id):
    """Full detail view of a single record."""
    record = HealthRecord.query.get_or_404(id)
    if record.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('health.index'))
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    return render_template(
        'health/view_record.html',
        record=record,
        patient=patient,
        HEALTH_CATEGORIES=HEALTH_CATEGORIES,
    )


@health_bp.route('/duplicate/<int:id>', methods=['POST'])
@login_required
def duplicate_record(id):
    """Duplicate a record as today's entry."""
    original = HealthRecord.query.get_or_404(id)
    if original.user_id != current_user.id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
           request.is_json:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        flash('Unauthorized.', 'danger')
        return redirect(url_for('health.index'))

    new_rec = HealthRecord(
        user_id=current_user.id,
        recorded_by=current_user.id,
        record_type=original.record_type,
        title=f'{original.get_display_title()} (copy)',
        category=original.category,
        description=original.description,
        result_value=original.result_value,
        result_unit=original.result_unit,
        severity=original.severity,
        status=original.status,
        doctor_name=original.doctor_name,
        hospital_name=original.hospital_name,
        notes=original.notes,
        tags=original.tags,
        # Legacy vitals
        systolic_bp=original.systolic_bp,
        diastolic_bp=original.diastolic_bp,
        heart_rate=original.heart_rate,
        temperature=original.temperature,
        respiratory_rate=original.respiratory_rate,
        oxygen_saturation=original.oxygen_saturation,
        weight=original.weight,
        height=original.height,
        bmi=original.bmi,
        glucose_level=original.glucose_level,
        cholesterol_total=original.cholesterol_total,
        hdl_cholesterol=original.hdl_cholesterol,
        ldl_cholesterol=original.ldl_cholesterol,
        triglycerides=original.triglycerides,
        record_date=datetime.utcnow(),
    )
    db.session.add(new_rec)
    db.session.commit()

    # Async (fetch) call — return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
       request.content_type == 'application/json':
        return jsonify({'success': True, 'message': 'Record duplicated', 'record': new_rec.to_dict()})

    # Normal form POST — redirect
    flash(f'Record duplicated as "{new_rec.get_display_title()}".', 'success')
    return redirect(url_for('health.index'))



@health_bp.route('/timeline')
@login_required
def timeline():
    """Chronological timeline of all records."""
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    records = HealthRecord.query.filter_by(user_id=current_user.id)\
                .order_by(HealthRecord.record_date.desc()).all()

    # Group by year-month
    grouped = {}
    for rec in records:
        key = rec.record_date.strftime('%B %Y')
        grouped.setdefault(key, []).append(rec)

    return render_template(
        'health/timeline.html',
        grouped=grouped,
        patient=patient,
        HEALTH_CATEGORIES=HEALTH_CATEGORIES,
    )


@health_bp.route('/charts')
@login_required
def charts():
    """Trend charts page."""
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    return render_template('health/charts.html', patient=patient)


@health_bp.route('/api/chart-data')
@login_required
def chart_data():
    """JSON endpoint — returns chart series data for the last N records."""
    limit = request.args.get('limit', 30, type=int)
    records = HealthRecord.query.filter_by(user_id=current_user.id)\
                .order_by(HealthRecord.record_date.asc()).limit(limit).all()

    labels = []
    datasets = {
        'systolic_bp':  [], 'diastolic_bp': [],
        'heart_rate':   [], 'glucose_level': [],
        'weight':       [], 'bmi':           [],
        'temperature':  [], 'oxygen_saturation': [],
    }

    for r in records:
        labels.append(r.record_date.strftime('%b %d'))
        datasets['systolic_bp'].append(r.systolic_bp)
        datasets['diastolic_bp'].append(r.diastolic_bp)
        datasets['heart_rate'].append(r.heart_rate)
        datasets['glucose_level'].append(float(r.glucose_level) if r.glucose_level else None)
        datasets['weight'].append(float(r.weight) if r.weight else None)
        datasets['bmi'].append(float(r.bmi) if r.bmi else None)
        datasets['temperature'].append(float(r.temperature) if r.temperature else None)
        datasets['oxygen_saturation'].append(float(r.oxygen_saturation) if r.oxygen_saturation else None)

    return jsonify({'labels': labels, 'datasets': datasets})


@health_bp.route('/export/<int:id>')
@login_required
def export_record(id):
    """Export a record as plain-text (downloadable)."""
    record = HealthRecord.query.get_or_404(id)
    if record.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    from flask import Response
    lines = [
        f'NexVita Health Record Export',
        f'Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}',
        '─' * 50,
        f'Title:         {record.get_display_title()}',
        f'Type:          {record.record_type}',
        f'Category:      {record.category or "—"}',
        f'Date:          {record.record_date.strftime("%Y-%m-%d %H:%M") if record.record_date else "—"}',
        f'Severity:      {record.severity or "—"}',
        f'Status:        {record.status or "—"}',
        f'Result:        {record.get_display_value()}',
        f'Doctor:        {record.doctor_name or "—"}',
        f'Hospital:      {record.hospital_name or "—"}',
        f'Follow-up:     {record.follow_up_date.strftime("%Y-%m-%d") if record.follow_up_date else "—"}',
        f'Description:   {record.description or "—"}',
        f'Notes:         {record.notes or "—"}',
        f'Tags:          {", ".join(record.get_tags_list()) or "—"}',
        '─' * 50,
        'Vital Readings:',
        f'  Blood Pressure:   {record.systolic_bp}/{record.diastolic_bp} mmHg' if record.systolic_bp else '',
        f'  Heart Rate:       {record.heart_rate} bpm' if record.heart_rate else '',
        f'  Blood Sugar:      {record.glucose_level} mg/dL' if record.glucose_level else '',
        f'  Weight:           {record.weight} kg' if record.weight else '',
        f'  Height:           {record.height} cm' if record.height else '',
        f'  BMI:              {record.bmi}' if record.bmi else '',
        f'  Temperature:      {record.temperature} °C' if record.temperature else '',
    ]
    content = '\n'.join(line for line in lines if line != '')
    fname = f'nexvita_record_{record.id}_{record.record_date.strftime("%Y%m%d")}.txt'
    return Response(
        content,
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename={fname}'}
    )


@health_bp.route('/download/<int:id>')
@login_required
def download_attachment(id):
    """Download the attached file for a record."""
    record = HealthRecord.query.get_or_404(id)
    if record.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    if not record.attachment_path:
        flash('No attachment found for this record.', 'warning')
        return redirect(url_for('health.view_record', id=id))

    upload_base = os.path.join(current_app.root_path, 'uploads')
    rel_dir  = os.path.dirname(record.attachment_path)
    filename = os.path.basename(record.attachment_path)
    return send_from_directory(
        os.path.join(upload_base, rel_dir),
        filename,
        as_attachment=True,
        download_name=record.attachment_name or filename
    )