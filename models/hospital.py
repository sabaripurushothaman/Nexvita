from datetime import datetime
from database.db import db


class Hospital(db.Model):
    __tablename__ = 'hospitals'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))
    emergency_services = db.Column(db.Boolean, default=False)
    latitude = db.Column(db.Numeric(10, 8))   # Latitude coordinate
    longitude = db.Column(db.Numeric(11, 8))  # Longitude coordinate
    rating = db.Column(db.Numeric(2, 1))      # Rating out of 5.0
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Hospital {self.name}>'