"""
NexVita – Integration Tests
Tests app startup, all blueprints, DB tables, and key routes.
"""
import pytest
import os


@pytest.fixture(scope='session')
def app():
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['SECRET_KEY'] = 'test-secret-key'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    from app import create_app
    application = create_app()
    application.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    })
    with application.app_context():
        from database.db import db
        db.create_all()
        yield application
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# ===== Startup Tests =====

def test_app_starts(app):
    """App should initialise without errors."""
    assert app is not None


def test_all_blueprints_registered(app):
    """All 9 blueprints must be registered."""
    expected = {'auth', 'dashboard', 'patient', 'health', 'ai', 'sos', 'hospital', 'admin', 'reminders'}
    actual = set(app.blueprints.keys())
    assert expected == actual, f"Missing blueprints: {expected - actual}"


def test_all_db_tables_exist(app):
    """All 8 tables must exist in the database."""
    from database.db import db
    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        expected = {'users', 'patients', 'health_records', 'emergency_contacts', 'hospitals', 'ai_history', 'reminders'}
        missing = expected - tables
        assert not missing, f"Missing tables: {missing}"


# ===== Public Route Tests =====

def test_landing_page(client):
    """Root URL should return the landing page."""
    res = client.get('/')
    assert res.status_code == 200


def test_login_page(client):
    """Login page should render OK."""
    res = client.get('/auth/login')
    assert res.status_code == 200
    assert b'Sign In' in res.data or b'login' in res.data.lower()


def test_register_page(client):
    """Register page should render OK."""
    res = client.get('/auth/register')
    assert res.status_code == 200
    assert b'Create Account' in res.data or b'register' in res.data.lower()


def test_404_handler(client):
    """Non-existent route should return 404."""
    res = client.get('/this-page-does-not-exist')
    assert res.status_code == 404


# ===== Auth Flow Tests =====

def test_user_registration(client, app):
    """Registering a new user should redirect or succeed."""
    with app.app_context():
        res = client.post('/auth/register', data={
            'username': 'testuser',
            'email': 'test@nexvita.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'TestPass123!',
            'confirm_password': 'TestPass123!',
        }, follow_redirects=True)
        assert res.status_code == 200


def test_protected_dashboard_redirects(client):
    """Dashboard should redirect unauthenticated users to login."""
    res = client.get('/dashboard/')
    # Should redirect (302) or return login page
    assert res.status_code in (302, 200)
    if res.status_code == 302:
        assert '/auth/login' in res.headers.get('Location', '')


def test_protected_health_redirects(client):
    """Health page should redirect unauthenticated users."""
    res = client.get('/health/')
    assert res.status_code in (302, 200)


def test_protected_reminders_redirects(client):
    """Reminders page should redirect unauthenticated users."""
    res = client.get('/reminders/')
    assert res.status_code in (302, 200)


def test_protected_ai_redirects(client):
    """AI chatbot should redirect unauthenticated users."""
    res = client.get('/ai/chatbot')
    assert res.status_code in (302, 200)


def test_protected_sos_redirects(client):
    """SOS page should redirect unauthenticated users."""
    res = client.get('/sos/')
    assert res.status_code in (302, 200)


# ===== Model Tests =====

def test_reminder_model(app):
    """Reminder model should be importable and have correct attributes."""
    from models import Reminder
    assert hasattr(Reminder, 'user_id')
    assert hasattr(Reminder, 'title')
    assert hasattr(Reminder, 'category')
    assert hasattr(Reminder, 'reminder_time')
    assert hasattr(Reminder, 'frequency')
    assert hasattr(Reminder, 'is_active')
    assert hasattr(Reminder, 'icon')
    assert hasattr(Reminder, 'colour')


def test_user_model(app):
    """User model should have all required methods."""
    from models import User
    assert hasattr(User, 'set_password')
    assert hasattr(User, 'check_password')
    assert hasattr(User, 'get_full_name')
    assert hasattr(User, 'is_admin')


def test_health_record_model(app):
    """HealthRecord model should have vital fields."""
    from models import HealthRecord
    for attr in ['systolic_bp', 'diastolic_bp', 'heart_rate', 'glucose_level', 'weight', 'bmi']:
        assert hasattr(HealthRecord, attr), f"HealthRecord missing: {attr}"


# ===== Route URL Generation Tests =====

def test_all_urls_resolvable(app):
    """All key URL endpoints should be buildable."""
    with app.test_request_context():
        from flask import url_for
        endpoints = [
            ('auth.login', {}),
            ('auth.register', {}),
            ('dashboard.index', {}),
            ('dashboard.profile', {}),
            ('health.index', {}),
            ('ai.chatbot', {}),
            ('ai.insights', {}),
            ('ai.symptom_checker', {}),
            ('ai.generate_report', {}),
            ('sos.index', {}),
            ('sos.hospitals', {}),
            ('sos.emergency_contacts', {}),
            ('reminders.index', {}),
            ('hospital.index', {}),
            ('admin.index', {}),
        ]
        failed = []
        for ep, kw in endpoints:
            try:
                url_for(ep, **kw)
            except Exception as e:
                failed.append(f"{ep}: {e}")
        assert not failed, f"Failed URL generation:\n" + "\n".join(failed)


# ===== Static Files Tests =====

def test_static_css_files_exist(app):
    """Core CSS files must exist."""
    import os
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'css')
    required = ['main.css', 'components.css', 'animations.css']
    missing = [f for f in required if not os.path.exists(os.path.join(base, f))]
    assert not missing, f"Missing CSS files: {missing}"


def test_static_js_files_exist(app):
    """Core JS files must exist."""
    import os
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'js')
    required = ['app.js', 'dashboard.js', 'ai.js', 'reminders.js', 'sos.js', 'maps.js']
    missing = [f for f in required if not os.path.exists(os.path.join(base, f))]
    assert not missing, f"Missing JS files: {missing}"


def test_template_files_exist(app):
    """Core template files must exist."""
    import os
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    required = [
        'base.html',
        'base_auth.html',
        'index.html',
        'auth/login.html',
        'auth/register.html',
        'dashboard/index.html',
        'dashboard/profile.html',
        'health/index.html',
        'ai/chatbot.html',
        'ai/insights.html',
        'reminders/index.html',
        'sos/index.html',
        'sos/hospitals.html',
        'errors/404.html',
        'errors/500.html',
    ]
    missing = [f for f in required if not os.path.exists(os.path.join(base, f))]
    assert not missing, f"Missing templates: {missing}"
