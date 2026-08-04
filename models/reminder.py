from datetime import datetime
from database.db import db


class Reminder(db.Model):
    __tablename__ = 'reminders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False, default='other')
    # medicine, water, appointment, checkup, exercise, other
    reminder_time = db.Column(db.DateTime, nullable=False)
    frequency = db.Column(db.String(20), default='once')
    # once, daily, weekly, monthly
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Category-to-icon mapping helper
    CATEGORY_ICONS = {
        'medicine':    'pill',
        'water':       'droplets',
        'appointment': 'calendar',
        'checkup':     'stethoscope',
        'exercise':    'dumbbell',
        'other':       'bell',
    }

    CATEGORY_COLOURS = {
        'medicine':    'primary',
        'water':       'info',
        'appointment': 'warning',
        'checkup':     'success',
        'exercise':    'accent',
        'other':       'neutral',
    }

    @property
    def icon(self):
        return self.CATEGORY_ICONS.get(self.category, 'bell')

    @property
    def colour(self):
        return self.CATEGORY_COLOURS.get(self.category, 'neutral')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'category': self.category,
            'reminder_time': self.reminder_time.isoformat(),
            'frequency': self.frequency,
            'notes': self.notes,
            'is_active': self.is_active,
        }

    def __repr__(self):
        return f'<Reminder {self.title} ({self.category})>'
