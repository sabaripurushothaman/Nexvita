from datetime import datetime
from database.db import db
import json


class HealthRecord(db.Model):
    __tablename__ = 'health_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    record_type = db.Column(db.String(50), nullable=False)  # legacy + new type key
    record_date = db.Column(db.DateTime, default=datetime.utcnow)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # ── Legacy vital columns — PRESERVED for AI/Insights service ──────────
    systolic_bp        = db.Column(db.Integer)
    diastolic_bp       = db.Column(db.Integer)
    heart_rate         = db.Column(db.Integer)
    temperature        = db.Column(db.Numeric(4, 1))
    respiratory_rate   = db.Column(db.Integer)
    oxygen_saturation  = db.Column(db.Numeric(5, 2))
    weight             = db.Column(db.Numeric(5, 2))
    height             = db.Column(db.Numeric(5, 2))
    bmi                = db.Column(db.Numeric(4, 2))
    glucose_level      = db.Column(db.Numeric(5, 2))
    cholesterol_total  = db.Column(db.Numeric(5, 2))
    hdl_cholesterol    = db.Column(db.Numeric(5, 2))
    ldl_cholesterol    = db.Column(db.Numeric(5, 2))
    triglycerides      = db.Column(db.Numeric(5, 2))
    symptoms           = db.Column(db.Text)
    diagnosis          = db.Column(db.Text)
    treatment          = db.Column(db.Text)
    medications        = db.Column(db.Text)
    notes              = db.Column(db.Text)
    is_private         = db.Column(db.Boolean, default=False)
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at         = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── New flexible columns — additive, all nullable ──────────────────────
    title              = db.Column(db.String(200))            # human-readable name
    category           = db.Column(db.String(50))             # e.g. 'vital_signs', 'laboratory'
    description        = db.Column(db.Text)                   # free-text description
    result_value       = db.Column(db.String(200))            # primary result, e.g. "120/80"
    result_unit        = db.Column(db.String(50))             # e.g. "mmHg", "mg/dL"
    severity           = db.Column(db.String(20))             # normal/mild/moderate/severe/critical
    status             = db.Column(db.String(20))             # active/resolved/monitoring/chronic
    doctor_name        = db.Column(db.String(200))            # attending physician
    hospital_name      = db.Column(db.String(200))            # facility
    follow_up_date     = db.Column(db.DateTime)               # next appointment
    tags               = db.Column(db.Text)                   # JSON array ["diabetes","hypertension"]
    attachment_path    = db.Column(db.String(500))            # relative path to file
    attachment_name    = db.Column(db.String(200))            # original filename

    # ── Relationships ──────────────────────────────────────────────────────
    recorder = db.relationship(
        'User',
        foreign_keys=[recorded_by],
        backref=db.backref('recorded_health_records', lazy='dynamic')
    )

    # ── Helper Methods ─────────────────────────────────────────────────────

    def get_tags_list(self):
        """Return tags as a Python list."""
        if not self.tags:
            return []
        try:
            return json.loads(self.tags)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_tags_list(self, tags_list):
        """Store tags from a Python list."""
        self.tags = json.dumps(tags_list) if tags_list else None

    def get_display_title(self):
        """Best human-readable title for this record."""
        if self.title:
            return self.title
        return self.record_type.replace('_', ' ').title()

    def get_display_value(self):
        """Primary display value — uses new field first, falls back to legacy vitals."""
        if self.result_value:
            unit = f' {self.result_unit}' if self.result_unit else ''
            return f'{self.result_value}{unit}'
        # Legacy vital fallbacks
        if self.systolic_bp and self.diastolic_bp:
            return f'{self.systolic_bp}/{self.diastolic_bp} mmHg'
        if self.heart_rate:
            return f'{self.heart_rate} bpm'
        if self.glucose_level:
            return f'{float(self.glucose_level):.1f} mg/dL'
        if self.weight:
            return f'{float(self.weight):.1f} kg'
        if self.temperature:
            return f'{float(self.temperature):.1f} °C'
        if self.bmi:
            return f'BMI {float(self.bmi):.1f}'
        return '—'

    def get_category_meta(self):
        """Return category display metadata dict."""
        from utils.constants import HEALTH_CATEGORIES
        return HEALTH_CATEGORIES.get(
            self.category or 'custom',
            HEALTH_CATEGORIES['custom']
        )

    def get_severity_badge(self):
        """Return CSS badge class for current severity."""
        badge_map = {
            'normal':   'badge-success',
            'mild':     'badge-info',
            'moderate': 'badge-warning',
            'severe':   'badge-danger',
            'critical': 'badge-danger',
        }
        return badge_map.get(self.severity or 'normal', 'badge-neutral')

    def get_status_badge(self):
        """Return CSS badge class for current status."""
        badge_map = {
            'active':     'badge-info',
            'resolved':   'badge-success',
            'monitoring': 'badge-warning',
            'chronic':    'badge-danger',
        }
        return badge_map.get(self.status or 'active', 'badge-neutral')

    def to_dict(self):
        """Serialise record to a dict (for JSON API responses)."""
        return {
            'id':             self.id,
            'record_type':    self.record_type,
            'title':          self.get_display_title(),
            'category':       self.category,
            'record_date':    self.record_date.isoformat() if self.record_date else None,
            'result_value':   self.result_value,
            'result_unit':    self.result_unit,
            'severity':       self.severity,
            'status':         self.status,
            'doctor_name':    self.doctor_name,
            'hospital_name':  self.hospital_name,
            'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None,
            'tags':           self.get_tags_list(),
            'display_value':  self.get_display_value(),
            'has_attachment': bool(self.attachment_path),
            'attachment_name': self.attachment_name,
            # Legacy vitals for chart endpoints
            'systolic_bp':    self.systolic_bp,
            'diastolic_bp':   self.diastolic_bp,
            'heart_rate':     self.heart_rate,
            'glucose_level':  float(self.glucose_level) if self.glucose_level else None,
            'weight':         float(self.weight) if self.weight else None,
            'bmi':            float(self.bmi) if self.bmi else None,
            'temperature':    float(self.temperature) if self.temperature else None,
        }

    def __repr__(self):
        return f'<HealthRecord {self.get_display_title()} on {self.record_date}>'