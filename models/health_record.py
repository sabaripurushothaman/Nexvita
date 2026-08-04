from datetime import datetime
from database.db import db


class HealthRecord(db.Model):
    __tablename__ = 'health_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    record_type = db.Column(db.String(50), nullable=False)  # vital, lab, medication, etc.
    record_date = db.Column(db.DateTime, default=datetime.utcnow)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # who recorded it
    systolic_bp = db.Column(db.Integer)
    diastolic_bp = db.Column(db.Integer)
    heart_rate = db.Column(db.Integer)          # bpm
    temperature = db.Column(db.Numeric(4, 1))   # Celsius
    respiratory_rate = db.Column(db.Integer)    # breaths per minute
    oxygen_saturation = db.Column(db.Numeric(5, 2))  # percentage
    weight = db.Column(db.Numeric(5, 2))        # kg
    height = db.Column(db.Numeric(5, 2))        # cm
    bmi = db.Column(db.Numeric(4, 2))           # body mass index
    glucose_level = db.Column(db.Numeric(5, 2)) # mg/dL
    cholesterol_total = db.Column(db.Numeric(5, 2))  # mg/dL
    hdl_cholesterol = db.Column(db.Numeric(5, 2))    # mg/dL
    ldl_cholesterol = db.Column(db.Numeric(5, 2))    # mg/dL
    triglycerides = db.Column(db.Numeric(5, 2)) # mg/dL
    symptoms = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    treatment = db.Column(db.Text)
    medications = db.Column(db.Text)
    notes = db.Column(db.Text)
    is_private = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Explicit relationship for the recorder (recorded_by FK)
    # The 'user' backref is declared on User.health_records via foreign_keys='HealthRecord.user_id'
    recorder = db.relationship(
        'User',
        foreign_keys=[recorded_by],
        backref=db.backref('recorded_health_records', lazy='dynamic')
    )

    def __repr__(self):
        return f'<HealthRecord {self.record_type} on {self.record_date}>'