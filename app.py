from flask import Flask, render_template, redirect, url_for
from config import config, startup_diagnostics
from database.db import db
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_cors import CORS
import os
from dotenv import load_dotenv
from utils.helpers import format_date, format_datetime, calculate_age
from utils.constants import USER_ROLES, HEALTH_RECORD_TYPES, BLOOD_TYPES

# Load environment variables
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

def create_app(config_name=None):
    """Application factory pattern."""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)  # side-effect only; return value not needed
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Enable CORS
    CORS(app)

    # Register blueprints
    from routes import auth_bp, dashboard_bp, patient_bp, health_bp, ai_bp, sos_bp, hospital_bp, admin_bp, reminders_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(sos_bp)
    app.register_blueprint(hospital_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reminders_bp)

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return db.session.get(User, int(user_id))

    # Register template context processors
    @app.context_processor
    def utility_processor():
        from flask_login import current_user
        active_reminders = 0
        try:
            if current_user and current_user.is_authenticated:
                from models import Reminder
                active_reminders = Reminder.query.filter_by(
                    user_id=current_user.id, is_active=True
                ).count()
        except Exception:
            pass
        return dict(
            format_date=format_date,
            format_datetime=format_datetime,
            calculate_age=calculate_age,
            USER_ROLES=USER_ROLES,
            HEALTH_RECORD_TYPES=HEALTH_RECORD_TYPES,
            BLOOD_TYPES=BLOOD_TYPES,
            active_reminders=active_reminders
        )

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Root landing page
    @app.route('/')
    def landing():
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return render_template('index.html')

    # Create uploads directory if it doesn't exist
    uploads_dir = os.path.join(basedir, 'uploads')
    try:
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
    except OSError:
        pass

    return app

# For running the app directly
app = create_app()
if __name__ == '__main__':
    startup_diagnostics()  # only print diagnostics when run directly, not on Gunicorn import
    app.run(debug=True, host='0.0.0.0', port=5000)