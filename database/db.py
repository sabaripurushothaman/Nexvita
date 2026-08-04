from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
import os

# Define naming convention for constraints
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=naming_convention)
db = SQLAlchemy(metadata=metadata)

def init_db(app):
    db.init_app(app)
    with app.app_context():
        # Import all models here to ensure they are registered
        from models import user, patient, health_record, emergency_contact, hospital, ai_history
        db.create_all()