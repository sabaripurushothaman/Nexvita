"""
test_production_login.py

Regression tests for the Render production post-login HTTP 500.

Root cause: db.create_all() was not called on app startup, so on a fresh
Render PostgreSQL database all tables were missing. Every query after login
crashed with: psycopg2.errors.UndefinedTable / sqlalchemy.exc.OperationalError

Fix: create_app() now calls db.create_all() after blueprints are registered
(and therefore after all models are imported and present in SQLAlchemy metadata).

These tests verify:
  1. db.create_all() creates all required tables on a fresh DB
  2. POST /auth/login succeeds (302 redirect to dashboard)
  3. GET /dashboard/ returns 200 (not 500)
  4. Reminder query in context processor does not crash
  5. load_user works after redirect
"""
import os
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def fresh_app():
    """Create an app instance against a fresh in-memory SQLite database,
    simulating a brand-new Render/PostgreSQL deployment with no existing tables.
    """
    os.environ.setdefault('FLASK_CONFIG', 'testing')
    # Remove DATABASE_URL so we fall back to in-memory SQLite (fresh, empty)
    os.environ.pop('DATABASE_URL', None)

    from app import create_app
    application = create_app('testing')
    application.config['WTF_CSRF_ENABLED'] = False
    return application


@pytest.fixture()
def client(fresh_app):
    return fresh_app.test_client()


@pytest.fixture()
def test_user(fresh_app):
    """Create a User + Patient for login tests."""
    with fresh_app.app_context():
        from database.db import db
        from models import User, Patient

        # Clean slate
        db.session.query(Patient).delete()
        db.session.query(User).delete()
        db.session.commit()

        u = User(
            username='prodregression',
            email='prodreg@nexvita.test',
            first_name='Prod',
            last_name='Regression',
        )
        u.set_password('ProdTest1234!')
        db.session.add(u)
        db.session.flush()
        p = Patient(user_id=u.id)
        db.session.add(p)
        db.session.commit()
        yield {'email': u.email, 'password': 'ProdTest1234!', 'id': u.id}

        # Cleanup
        db.session.query(Patient).filter_by(user_id=u.id).delete()
        db.session.query(User).filter_by(id=u.id).delete()
        db.session.commit()


# ---------------------------------------------------------------------------
# Phase 4 — Database Investigation
# ---------------------------------------------------------------------------

class TestDatabaseInit:
    """Verify that db.create_all() creates all required tables on a fresh DB."""

    REQUIRED_TABLES = {
        'users',
        'patients',
        'health_records',
        'reminders',
        'emergency_contacts',
        'ai_history',
        'hospitals',
    }

    def test_all_tables_exist_after_create_app(self, fresh_app):
        """db.create_all() in create_app() must create all 7 tables."""
        with fresh_app.app_context():
            from database.db import db
            from sqlalchemy import inspect
            existing = set(inspect(db.engine).get_table_names())
            missing = self.REQUIRED_TABLES - existing
            assert not missing, (
                f"Tables missing from fresh DB: {missing}. "
                "This is the Render production 500 root cause."
            )

    def test_users_table_has_required_columns(self, fresh_app):
        with fresh_app.app_context():
            from database.db import db
            from sqlalchemy import inspect
            cols = {c['name'] for c in inspect(db.engine).get_columns('users')}
            assert 'id' in cols
            assert 'email' in cols
            assert 'password_hash' in cols
            assert 'is_active' in cols

    def test_reminders_table_exists(self, fresh_app):
        """Specifically check reminders — the context_processor queries this table."""
        with fresh_app.app_context():
            from database.db import db
            from sqlalchemy import inspect
            assert 'reminders' in inspect(db.engine).get_table_names()

    def test_health_records_has_flexible_columns(self, fresh_app):
        """The flexible columns added in the only migration must be present."""
        with fresh_app.app_context():
            from database.db import db
            from sqlalchemy import inspect
            cols = {c['name'] for c in inspect(db.engine).get_columns('health_records')}
            # New flexible columns
            assert 'title' in cols
            assert 'severity' in cols
            assert 'result_value' in cols
            assert 'attachment_path' in cols


# ---------------------------------------------------------------------------
# Phase 5 — Flask-Login Investigation
# ---------------------------------------------------------------------------

class TestFlaskLoginFlow:
    """Verify the complete login → session → redirect flow."""

    def test_login_post_returns_302(self, client, test_user):
        """POST /auth/login with valid credentials must return 302."""
        r = client.post('/auth/login', data={
            'email': test_user['email'],
            'password': test_user['password'],
        }, follow_redirects=False)
        assert r.status_code == 302, (
            f"Expected 302 redirect after login, got {r.status_code}"
        )

    def test_login_redirects_to_dashboard(self, client, test_user):
        """POST /auth/login must redirect to /dashboard/."""
        r = client.post('/auth/login', data={
            'email': test_user['email'],
            'password': test_user['password'],
        }, follow_redirects=False)
        location = r.headers.get('Location', '')
        assert '/dashboard' in location, (
            f"Expected redirect to /dashboard/, got Location: {location}"
        )

    def test_wrong_password_stays_on_login(self, client, test_user):
        """Invalid credentials must NOT redirect."""
        r = client.post('/auth/login', data={
            'email': test_user['email'],
            'password': 'WrongPassword999!',
        }, follow_redirects=False)
        assert r.status_code == 200, (
            f"Expected 200 (stay on login page) with wrong password, got {r.status_code}"
        )


# ---------------------------------------------------------------------------
# Phase 6 — Post-Login Route (the actual 500 location)
# ---------------------------------------------------------------------------

class TestPostLoginDashboard:
    """Regression test: the dashboard GET must return 200 after login."""

    def test_dashboard_returns_200_after_login(self, client, test_user):
        """
        This is the EXACT regression test for the Render 500.
        1. POST /auth/login
        2. GET /dashboard/
        Must return 200, not 500.
        """
        # Login
        client.post('/auth/login', data={
            'email': test_user['email'],
            'password': test_user['password'],
        }, follow_redirects=False)

        # Follow redirect to dashboard
        r = client.get('/dashboard/', follow_redirects=False)
        assert r.status_code == 200, (
            f"Dashboard returned {r.status_code} after login. "
            "This is the Render post-login 500 regression."
        )

    def test_dashboard_full_redirect_chain_200(self, client, test_user):
        """Test the complete redirect chain with follow_redirects=True."""
        r = client.post('/auth/login', data={
            'email': test_user['email'],
            'password': test_user['password'],
        }, follow_redirects=True)
        assert r.status_code == 200, (
            f"Full login+redirect chain returned {r.status_code}. Expected 200."
        )

    def test_context_processor_reminder_query_does_not_crash(self, client, test_user):
        """The context_processor Reminder.query must not raise on a fresh DB."""
        client.post('/auth/login', data={
            'email': test_user['email'],
            'password': test_user['password'],
        }, follow_redirects=False)
        # Any authenticated page triggers the context_processor
        r = client.get('/dashboard/', follow_redirects=False)
        # If Reminder.query crashes -> 500. We verify it doesn't.
        assert r.status_code != 500, (
            "Dashboard returned 500 — likely the Reminder.query in context_processor crashed."
        )

    def test_unauthenticated_dashboard_redirects_to_login(self, client):
        """Unauthenticated /dashboard/ must redirect to login, not crash."""
        r = client.get('/dashboard/', follow_redirects=False)
        assert r.status_code == 302
        location = r.headers.get('Location', '')
        assert 'login' in location.lower(), (
            f"Unauthenticated /dashboard/ should redirect to login, got: {location}"
        )


# ---------------------------------------------------------------------------
# Phase 7 — app.py load_user
# ---------------------------------------------------------------------------

class TestUserLoader:
    """Verify that load_user works after login redirect."""

    def test_load_user_returns_user(self, fresh_app, test_user):
        with fresh_app.app_context():
            from models import User
            from database.db import db
            u = db.session.get(User, test_user['id'])
            assert u is not None
            assert u.email == test_user['email']
            assert u.is_active is True

    def test_load_user_nonexistent_returns_none(self, fresh_app):
        with fresh_app.app_context():
            from models import User
            from database.db import db
            result = db.session.get(User, 999999)
            assert result is None
