from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from database.db import db
from models import Reminder
from datetime import datetime

reminders_bp = Blueprint('reminders', __name__, url_prefix='/reminders')

CATEGORIES = ['medicine', 'water', 'appointment', 'checkup', 'exercise', 'other']
FREQUENCIES = ['once', 'daily', 'weekly', 'monthly']


@reminders_bp.route('/')
@login_required
def index():
    """List all reminders, grouped by category."""
    category_filter = request.args.get('category', 'all')
    query = Reminder.query.filter_by(user_id=current_user.id)
    if category_filter != 'all' and category_filter in CATEGORIES:
        query = query.filter_by(category=category_filter)
    reminders = query.order_by(Reminder.reminder_time).all()

    # Count per category for filter tabs
    counts = {}
    for cat in CATEGORIES:
        counts[cat] = Reminder.query.filter_by(user_id=current_user.id, category=cat).count()
    counts['all'] = Reminder.query.filter_by(user_id=current_user.id).count()

    return render_template(
        'reminders/index.html',
        reminders=reminders,
        categories=CATEGORIES,
        frequencies=FREQUENCIES,
        category_filter=category_filter,
        counts=counts
    )


@reminders_bp.route('/add', methods=['POST'])
@login_required
def add():
    """Create a new reminder."""
    title = request.form.get('title', '').strip()
    category = request.form.get('category', 'other')
    reminder_time_str = request.form.get('reminder_time', '')
    frequency = request.form.get('frequency', 'once')
    notes = request.form.get('notes', '').strip()

    if not title:
        flash('Reminder title is required.', 'danger')
        return redirect(url_for('reminders.index'))

    if category not in CATEGORIES:
        category = 'other'

    try:
        reminder_time = datetime.strptime(reminder_time_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        reminder_time = datetime.utcnow()

    reminder = Reminder(
        user_id=current_user.id,
        title=title,
        category=category,
        reminder_time=reminder_time,
        frequency=frequency,
        notes=notes or None,
        is_active=True,
    )
    db.session.add(reminder)
    db.session.commit()
    flash('Reminder added successfully!', 'success')
    return redirect(url_for('reminders.index'))


@reminders_bp.route('/toggle/<int:id>', methods=['POST'])
@login_required
def toggle(id):
    """Toggle a reminder active/inactive — returns JSON."""
    reminder = Reminder.query.get_or_404(id)
    if reminder.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    reminder.is_active = not reminder.is_active
    reminder.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True, 'is_active': reminder.is_active})


@reminders_bp.route('/edit/<int:id>', methods=['POST'])
@login_required
def edit(id):
    """Edit an existing reminder."""
    reminder = Reminder.query.get_or_404(id)
    if reminder.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('reminders.index'))

    reminder.title = request.form.get('title', reminder.title).strip()
    cat = request.form.get('category', reminder.category)
    reminder.category = cat if cat in CATEGORIES else reminder.category
    freq = request.form.get('frequency', reminder.frequency)
    reminder.frequency = freq if freq in FREQUENCIES else reminder.frequency
    reminder.notes = request.form.get('notes', '').strip() or None
    reminder_time_str = request.form.get('reminder_time', '')
    try:
        reminder.reminder_time = datetime.strptime(reminder_time_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        pass
    reminder.updated_at = datetime.utcnow()
    db.session.commit()
    flash('Reminder updated successfully!', 'success')
    return redirect(url_for('reminders.index'))


@reminders_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """Delete a reminder."""
    reminder = Reminder.query.get_or_404(id)
    if reminder.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    db.session.delete(reminder)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Reminder deleted'})
