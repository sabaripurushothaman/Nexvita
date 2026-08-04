from datetime import datetime
import uuid
from database.db import db


class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    patient_id = db.Column(db.String(20), unique=True, nullable=False, default=lambda: Patient.generate_patient_id())
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(20))
    blood_type = db.Column(db.String(5))
    height_cm = db.Column(db.Numeric(5, 2))
    weight_kg = db.Column(db.Numeric(5, 2))
    allergies = db.Column(db.Text)
    chronic_conditions = db.Column(db.Text)
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(100))
    primary_physician = db.Column(db.String(100))
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def generate_patient_id():
        """Auto-generate a unique patient ID in the format PAT-XXXXXXXX."""
        return 'PAT-' + str(uuid.uuid4())[:8].upper()

    def __repr__(self):
        return f'<Patient {self.patient_id}>'