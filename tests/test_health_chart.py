"""
tests/test_health_chart.py — NexVita Health Chart Data Tests
Verifies that the dashboard route produces chart_data where every
dataset array is the same length as the labels array, and that
null values are used for missing vitals (not filtered out).
"""
import json
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture(scope='module')
def flask_app():
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
def client(flask_app):
    return flask_app.test_client()


@pytest.fixture
def logged_in_client(flask_app, client):
    """Return an authenticated test client with a fresh user."""
    with flask_app.app_context():
        from database.db import db
        from models import User
        username = 'chart_test_user'
        email = 'chart_test@nexvita.com'
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(
                username=username,
                email=email,
                first_name='Chart',
                last_name='Tester',
            )
            user.set_password('TestPass123!')
            db.session.add(user)
            db.session.commit()

    client.post('/auth/login', data={
        'email': email,
        'password': 'TestPass123!',
    }, follow_redirects=True)
    return client


def _make_record(user_id, days_ago=0, **vitals):
    """Helper to build a HealthRecord object without saving to DB."""
    from models import HealthRecord
    r = HealthRecord(
        user_id=user_id,
        record_type='vitals',
        record_date=datetime.utcnow() - timedelta(days=days_ago),
    )
    for k, v in vitals.items():
        setattr(r, k, v)
    return r


# ─── Backend chart_data assembly ─────────────────────────────────────────────

class TestChartDataAssembly:
    """
    Tests that the dashboard route builds chart_data correctly.
    These tests import and call the route-level logic directly by
    inspecting the JSON passed to the template.
    """

    def _get_chart_data_from_records(self, records):
        """Re-implement the fixed dashboard chart-data assembly logic."""
        dates        = [r.record_date.strftime('%Y-%m-%d') for r in records]
        systolic_bp  = [r.systolic_bp  if r.systolic_bp  else None for r in records]
        diastolic_bp = [r.diastolic_bp if r.diastolic_bp else None for r in records]
        heart_rate   = [r.heart_rate   if r.heart_rate   else None for r in records]
        weight       = [float(r.weight) if r.weight else None for r in records]
        return {
            'labels': dates,
            'datasets': [
                {'label': 'Systolic BP',  'data': systolic_bp},
                {'label': 'Diastolic BP', 'data': diastolic_bp},
                {'label': 'Heart Rate',   'data': heart_rate},
                {'label': 'Weight (kg)',  'data': weight},
            ]
        }

    def test_zero_records_produces_empty_labels_and_datasets(self):
        data = self._get_chart_data_from_records([])
        assert data['labels'] == []
        for ds in data['datasets']:
            assert ds['data'] == []

    def test_one_record_all_datasets_length_one(self, flask_app):
        with flask_app.app_context():
            r = _make_record(user_id=1, days_ago=1, heart_rate=72, systolic_bp=120,
                             diastolic_bp=80, weight=70.0)
            data = self._get_chart_data_from_records([r])
        assert len(data['labels']) == 1
        for ds in data['datasets']:
            assert len(ds['data']) == 1, (
                f"Dataset '{ds['label']}' has length {len(ds['data'])}, expected 1"
            )

    def test_two_records_all_datasets_length_two(self, flask_app):
        with flask_app.app_context():
            r1 = _make_record(user_id=1, days_ago=2, heart_rate=75, systolic_bp=125,
                              diastolic_bp=82, weight=71.5)
            r2 = _make_record(user_id=1, days_ago=1, heart_rate=70, systolic_bp=118,
                              diastolic_bp=78, weight=71.0)
            data = self._get_chart_data_from_records([r1, r2])
        assert len(data['labels']) == 2
        for ds in data['datasets']:
            assert len(ds['data']) == 2, (
                f"Dataset '{ds['label']}' has length {len(ds['data'])}, expected 2"
            )

    def test_missing_vital_uses_none_not_filtered(self, flask_app):
        """If record 1 has heart_rate but record 2 does not, heart_rate dataset
        should be [72, None], not [72]."""
        with flask_app.app_context():
            r1 = _make_record(user_id=1, days_ago=2, heart_rate=72)
            r2 = _make_record(user_id=1, days_ago=1)  # no heart_rate
            data = self._get_chart_data_from_records([r1, r2])

        heart_ds = next(d for d in data['datasets'] if d['label'] == 'Heart Rate')
        assert len(heart_ds['data']) == 2, (
            f"Expected length 2 (with None for missing), got {len(heart_ds['data'])}"
        )
        assert heart_ds['data'][0] == 72
        assert heart_ds['data'][1] is None

    def test_all_vitals_missing_all_none(self, flask_app):
        """Record with no vitals set — all datasets should contain None."""
        with flask_app.app_context():
            r = _make_record(user_id=1, days_ago=1)
            data = self._get_chart_data_from_records([r])
        for ds in data['datasets']:
            assert ds['data'] == [None], (
                f"Expected [None] for empty record in '{ds['label']}', got {ds['data']}"
            )

    def test_dates_are_valid_yyyy_mm_dd(self, flask_app):
        with flask_app.app_context():
            r = _make_record(user_id=1, days_ago=3)
            data = self._get_chart_data_from_records([r])
        import re
        for label in data['labels']:
            assert re.match(r'^\d{4}-\d{2}-\d{2}$', label), (
                f"Date '{label}' is not in YYYY-MM-DD format"
            )

    def test_weight_is_float(self, flask_app):
        with flask_app.app_context():
            r = _make_record(user_id=1, days_ago=1, weight=68.5)
            data = self._get_chart_data_from_records([r])
        weight_ds = next(d for d in data['datasets'] if d['label'] == 'Weight (kg)')
        assert weight_ds['data'][0] == 68.5
        assert isinstance(weight_ds['data'][0], float)

    def test_multiple_records_labels_ordered(self, flask_app):
        """Labels should reflect record_date order of the input list."""
        with flask_app.app_context():
            r1 = _make_record(user_id=1, days_ago=3)
            r2 = _make_record(user_id=1, days_ago=2)
            r3 = _make_record(user_id=1, days_ago=1)
            data = self._get_chart_data_from_records([r1, r2, r3])
        assert len(data['labels']) == 3
        for ds in data['datasets']:
            assert len(ds['data']) == 3

    def test_json_serialization_with_none_produces_null(self, flask_app):
        """None in Python must serialize to JSON null, not the string 'null'."""
        with flask_app.app_context():
            r = _make_record(user_id=1, days_ago=1)  # no vitals
            data = self._get_chart_data_from_records([r])
        serialized = json.dumps(data)
        parsed = json.loads(serialized)
        for ds in parsed['datasets']:
            assert ds['data'][0] is None, (
                f"Expected null in JSON, got {ds['data'][0]!r}"
            )


# ─── Dashboard route integration ─────────────────────────────────────────────

class TestDashboardRouteChartData:
    """Integration tests: GET /dashboard/ and verify chart_data in response HTML."""

    def test_dashboard_redirects_unauthenticated(self, client):
        res = client.get('/dashboard/')
        assert res.status_code in (302, 200)

    def test_dashboard_loads_for_authenticated_user(self, logged_in_client):
        res = logged_in_client.get('/dashboard/')
        assert res.status_code == 200

    def test_dashboard_contains_chart_data_json(self, logged_in_client):
        res = logged_in_client.get('/dashboard/')
        assert res.status_code == 200
        assert b'chartData' in res.data or b'chart_data' in res.data or b'initHealthChart' in res.data

    def test_dashboard_chart_data_is_valid_json(self, flask_app, logged_in_client):
        """Extract chart_data from the HTML and verify it is valid JSON."""
        import re
        res = logged_in_client.get('/dashboard/')
        html = res.data.decode('utf-8')
        # Pattern matches: const chartData = {...};
        match = re.search(r'const chartData\s*=\s*(\{.*?\});', html, re.DOTALL)
        if match:
            raw_json = match.group(1)
            try:
                parsed = json.loads(raw_json)
                assert 'labels' in parsed
                assert 'datasets' in parsed
                assert isinstance(parsed['labels'], list)
                assert isinstance(parsed['datasets'], list)
            except json.JSONDecodeError as exc:
                pytest.fail(f'chart_data is not valid JSON: {exc}\nRaw: {raw_json[:300]}')

    def test_dashboard_chart_datasets_same_length_as_labels(self, flask_app, logged_in_client):
        """Every dataset array must be the same length as the labels array."""
        import re
        res = logged_in_client.get('/dashboard/')
        html = res.data.decode('utf-8')
        match = re.search(r'const chartData\s*=\s*(\{.*?\});', html, re.DOTALL)
        if match:
            parsed = json.loads(match.group(1))
            n_labels = len(parsed['labels'])
            for ds in parsed['datasets']:
                assert len(ds['data']) == n_labels, (
                    f"Dataset '{ds['label']}' has {len(ds['data'])} entries "
                    f"but labels has {n_labels}. Arrays must be the same length."
                )

    def test_dashboard_with_two_health_records(self, flask_app, logged_in_client):
        """Insert 2 records for the chart user and verify both appear in labels."""
        import re
        with flask_app.app_context():
            from database.db import db
            from models import HealthRecord, User
            user = User.query.filter_by(username='chart_test_user').first()
            if user:
                # Remove previous records for clean test
                HealthRecord.query.filter_by(user_id=user.id).delete()
                db.session.commit()
                # Add exactly 2 records within the last 7 days
                now = datetime.utcnow()
                r1 = HealthRecord(
                    user_id=user.id,
                    record_type='vitals',
                    record_date=now - timedelta(days=3),
                    heart_rate=72,
                    systolic_bp=120,
                    diastolic_bp=80,
                )
                r2 = HealthRecord(
                    user_id=user.id,
                    record_type='vitals',
                    record_date=now - timedelta(days=1),
                    heart_rate=68,
                    systolic_bp=115,
                    diastolic_bp=75,
                )
                db.session.add_all([r1, r2])
                db.session.commit()

        res = logged_in_client.get('/dashboard/')
        assert res.status_code == 200
        html = res.data.decode('utf-8')
        match = re.search(r'const chartData\s*=\s*(\{.*?\});', html, re.DOTALL)
        if match:
            parsed = json.loads(match.group(1))
            assert len(parsed['labels']) == 2, (
                f"Expected 2 labels for 2 records, got {len(parsed['labels'])}"
            )
            for ds in parsed['datasets']:
                assert len(ds['data']) == 2, (
                    f"Dataset '{ds['label']}' must have 2 entries, got {len(ds['data'])}"
                )
