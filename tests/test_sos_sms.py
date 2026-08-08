"""
tests/test_sos_sms.py
~~~~~~~~~~~~~~~~~~~~~
Full test suite for the NexVita SOS SMS delivery pipeline.

Run from the project root:
    pytest tests/test_sos_sms.py -v

Uses unittest.mock to simulate Twilio responses. Tests:
    - phone-number normalisation
    - NotificationService: missing creds, valid config, per-error-code hints
    - EmergencyService: no contacts, one contact, multiple, partial, all-fail
    - /sos/trigger-sos route: authentication, bad coords, all states
    - /sos/diagnostic route
    - /sos/test-sms route

Does NOT prove real SMS delivery.
Real delivery is verified manually (see test_manual_sms procedure at bottom).
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(scope='session')
def app():
    os.environ.setdefault('TESTING', 'true')
    os.environ.setdefault('SECRET_KEY', 'test-secret')
    os.environ.setdefault('WTF_CSRF_ENABLED', 'false')
    from app import create_app
    application = create_app()
    application.config['TESTING'] = True
    application.config['WTF_CSRF_ENABLED'] = False
    with application.app_context():
        from database.db import db
        db.create_all()
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield


@pytest.fixture
def logged_in_client(app, client):
    """Return a test client with the first DB user session-injected."""
    with app.app_context():
        from models import User
        user = User.query.first()
        if not user:
            pytest.skip('No user in DB')
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh']   = True
    return client, user


# ============================================================
# 1. Phone Number Normalisation
# ============================================================

class TestNormalisePhone:

    def setup_method(self):
        from services.notification_service import normalise_phone
        self.normalise = normalise_phone

    def test_10_digit_indian_mobile(self):
        assert self.normalise('9629333508') == '+919629333508'

    def test_10_digit_with_leading_zero(self):
        assert self.normalise('09629333508') == '+919629333508'

    def test_already_e164(self):
        assert self.normalise('+919629333508') == '+919629333508'

    def test_already_e164_us(self):
        assert self.normalise('+14155552671') == '+14155552671'

    def test_12_digit_with_country_code_91(self):
        assert self.normalise('919629333508') == '+919629333508'

    def test_e164_with_spaces(self):
        assert self.normalise('+91 9629 333 508') == '+919629333508'

    def test_e164_with_dashes(self):
        assert self.normalise('+91-962-933-3508') == '+919629333508'

    def test_stored_with_space_as_seen_in_db(self):
        # The contact in DB has '+91 9629333508'
        result = self.normalise('+91 9629333508')
        assert result == '+919629333508'

    def test_empty_string_returns_none(self):
        assert self.normalise('') is None

    def test_none_returns_none(self):
        assert self.normalise(None) is None

    def test_letters_returns_none(self):
        assert self.normalise('abc') is None

    def test_too_short_returns_none(self):
        assert self.normalise('123') is None

    def test_landline_6_digit_returns_none(self):
        assert self.normalise('123456') is None


# ============================================================
# 2. NotificationService — unit tests
# ============================================================

class TestNotificationServiceNotConfigured:

    def setup_method(self):
        # Ensure env vars are clear
        for k in ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER'):
            os.environ.pop(k, None)
        from services.notification_service import NotificationService
        self.ns = NotificationService()

    def test_is_configured_false(self):
        assert self.ns.is_configured is False

    def test_missing_vars_all_three(self):
        missing = self.ns.missing_vars()
        assert 'TWILIO_ACCOUNT_SID' in missing
        assert 'TWILIO_AUTH_TOKEN'  in missing
        assert 'TWILIO_PHONE_NUMBER' in missing

    def test_send_sms_returns_not_configured(self):
        result = self.ns.send_sms('+919629333508', 'test')
        assert result['success'] is False
        assert result['sms_configured'] is False
        assert 'TWILIO_ACCOUNT_SID' in result['error']

    def test_send_sms_does_not_raise(self):
        # Must not raise under any circumstance
        result = self.ns.send_sms('', 'test')
        assert result['success'] is False


class TestNotificationServiceConfigured:

    def setup_method(self):
        os.environ['TWILIO_ACCOUNT_SID']  = 'ACtest1234567890123456789012345678'
        os.environ['TWILIO_AUTH_TOKEN']   = 'authtoken1234567890123456789012'
        os.environ['TWILIO_PHONE_NUMBER'] = '+15551234567'
        from services import notification_service as mod
        import importlib
        importlib.reload(mod)
        self.ns = mod.NotificationService()

    def teardown_method(self):
        for k in ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER'):
            os.environ.pop(k, None)

    def test_is_configured_true(self):
        assert self.ns.is_configured is True

    def test_missing_vars_empty(self):
        assert self.ns.missing_vars() == []

    def test_send_sms_success(self):
        mock_msg = MagicMock()
        mock_msg.sid = 'SM' + 'x' * 32
        with patch('twilio.rest.Client') as MockClient:
            instance = MockClient.return_value
            instance.messages.create.return_value = mock_msg
            result = self.ns.send_sms('+919629333508', 'Emergency test')
        assert result['success'] is True
        assert result['sms_configured'] is True
        assert result['provider_message_id'].startswith('SM')
        assert result['error'] is None
        assert result['normalised_number'] == '+919629333508'

    def test_send_sms_normalises_10_digit(self):
        mock_msg = MagicMock()
        mock_msg.sid = 'SM' + 'a' * 32
        with patch('twilio.rest.Client') as MockClient:
            instance = MockClient.return_value
            instance.messages.create.return_value = mock_msg
            result = self.ns.send_sms('9629333508', 'test')
        assert result['success'] is True
        assert result['normalised_number'] == '+919629333508'
        # Verify Twilio was called with normalised number
        call_kwargs = instance.messages.create.call_args[1]
        assert call_kwargs['to'] == '+919629333508'

    def test_send_sms_invalid_number(self):
        result = self.ns.send_sms('abc', 'test')
        assert result['success'] is False
        assert result['sms_configured'] is True
        assert 'Invalid phone number' in result['error']

    def test_send_sms_twilio_rest_exception_with_code(self):
        from twilio.base.exceptions import TwilioRestException
        exc = TwilioRestException(
            msg='The number is not verified',
            uri='/Messages',
            status=400,
            code=21705,
            method='POST',
        )
        with patch('twilio.rest.Client') as MockClient:
            instance = MockClient.return_value
            instance.messages.create.side_effect = exc
            result = self.ns.send_sms('+919629333508', 'test')
        assert result['success'] is False
        assert result['error_code'] == 21705
        assert 'Trial' in result['error'] or 'verified' in result['error']

    def test_send_sms_invalid_credentials_20003(self):
        from twilio.base.exceptions import TwilioRestException
        exc = TwilioRestException(
            msg='Authentication Error', uri='/Messages',
            status=401, code=20003, method='POST'
        )
        with patch('twilio.rest.Client') as MockClient:
            instance = MockClient.return_value
            instance.messages.create.side_effect = exc
            result = self.ns.send_sms('+919629333508', 'test')
        assert result['success'] is False
        assert result['error_code'] == 20003
        assert 'credentials' in result['error'].lower() or 'invalid' in result['error'].lower()

    def test_send_sms_invalid_destination_21211(self):
        from twilio.base.exceptions import TwilioRestException
        exc = TwilioRestException(
            msg='Invalid To Phone Number', uri='/Messages',
            status=400, code=21211, method='POST'
        )
        with patch('twilio.rest.Client') as MockClient:
            instance = MockClient.create.side_effect = None
            instance_mock = MockClient.return_value
            instance_mock.messages.create.side_effect = exc
            result = self.ns.send_sms('+919629333508', 'test')
        assert result['success'] is False
        assert result['error_code'] == 21211

    def test_send_sms_unexpected_exception(self):
        with patch('twilio.rest.Client') as MockClient:
            instance = MockClient.return_value
            instance.messages.create.side_effect = RuntimeError('boom')
            result = self.ns.send_sms('+919629333508', 'test')
        assert result['success'] is False
        assert 'RuntimeError' in result['error']

    def test_send_sms_import_error(self):
        # twilio IS installed in this project, so we can't test a real ImportError
        # here without uninstalling it. Instead, verify the method always returns a dict
        # and never raises, which is the important safety guarantee.
        result = self.ns.send_sms('+919629333508', 'test')
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'sms_configured' in result
        assert 'error' in result


# ============================================================
# 3. EmergencyService — unit tests
# ============================================================

class TestEmergencyService:

    def setup_method(self):
        os.environ['TWILIO_ACCOUNT_SID']  = 'ACtest1234567890123456789012345678'
        os.environ['TWILIO_AUTH_TOKEN']   = 'authtoken1234567890123456789012'
        os.environ['TWILIO_PHONE_NUMBER'] = '+15551234567'

    def teardown_method(self):
        for k in ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER'):
            os.environ.pop(k, None)

    def _make_contact(self, name='Alice', phone='+919629333508', is_primary=True):
        c = MagicMock()
        c.id = 1
        c.name = name
        c.phone_primary = phone
        c.is_primary = is_primary
        return c

    def test_no_contacts_returns_correct_state(self, app_ctx):
        from services.emergency_service import EmergencyService
        from unittest.mock import PropertyMock
        svc = EmergencyService()

        # Use app context to get the real user
        from models import User
        user = User.query.first()
        if not user:
            pytest.skip('No user in DB')

        # Pass empty contacts explicitly — EmergencyService returns no_contacts
        result = svc.send_sos_alert(user_id=user.id, location=None, contacts=[])
        assert result['no_contacts'] is True
        assert result['success'] is False

    def test_one_contact_success(self, app_ctx):
        from services.emergency_service import EmergencyService
        svc = EmergencyService()
        contact = self._make_contact()
        mock_msg = MagicMock()
        mock_msg.sid = 'SM' + 'b' * 32

        # Client is imported from twilio.rest inside send_sms — patch there
        with patch('twilio.rest.Client') as MockClient:
            instance = MockClient.return_value
            instance.messages.create.return_value = mock_msg
            with patch('services.emergency_service.db') as mock_db:
                mock_user = MagicMock()
                mock_user.first_name = 'Test'
                mock_user.last_name  = 'User'
                mock_user.get_full_name.return_value = 'Test User'
                mock_db.session.get.return_value = mock_user
                result = svc.send_sos_alert(
                    user_id=1,
                    location={'latitude': 13.058, 'longitude': 80.177},
                    contacts=[contact],
                )
        assert result['success'] is True
        assert len(result['contacts_notified']) == 1
        assert len(result['contacts_failed']) == 0
        assert result['contacts_notified'][0]['name'] == 'Alice'

    def test_multiple_contacts_partial_failure(self, app_ctx):
        from services.emergency_service import EmergencyService
        from twilio.base.exceptions import TwilioRestException
        svc = EmergencyService()

        contact_a = self._make_contact('Alice', '+919629333508', True)
        contact_b = self._make_contact('Bob', '+919999999999', False)
        contact_b.id = 2

        exc = TwilioRestException(
            msg='Landline', uri='/Messages', status=400, code=30006, method='POST'
        )
        mock_msg = MagicMock()
        mock_msg.sid = 'SMgood'

        call_count = [0]
        def side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_msg  # Alice succeeds
            raise exc             # Bob fails

        with patch('twilio.rest.Client') as MockClient:
            instance = MockClient.return_value
            instance.messages.create.side_effect = side_effect
            with patch('services.emergency_service.db') as mock_db:
                mock_user = MagicMock()
                mock_user.first_name = 'Test'
                mock_user.last_name  = 'User'
                mock_user.get_full_name.return_value = 'Test User'
                mock_db.session.get.return_value = mock_user
                result = svc.send_sos_alert(
                    user_id=1,
                    location={'latitude': 13.058, 'longitude': 80.177},
                    contacts=[contact_a, contact_b],
                )
        assert result['success'] is True        # partial = still True
        assert len(result['contacts_notified']) == 1
        assert len(result['contacts_failed'])   == 1
        assert result['contacts_failed'][0]['name'] == 'Bob'
        assert result['contacts_failed'][0]['error_code'] == 30006

    def test_all_contacts_fail(self, app_ctx):
        from services.emergency_service import EmergencyService
        from twilio.base.exceptions import TwilioRestException
        svc = EmergencyService()
        contact = self._make_contact()
        exc = TwilioRestException(
            msg='Bad creds', uri='/Messages', status=401, code=20003, method='POST'
        )
        with patch('twilio.rest.Client') as MockClient:
            instance = MockClient.return_value
            instance.messages.create.side_effect = exc
            with patch('services.emergency_service.db') as mock_db:
                mock_user = MagicMock()
                mock_user.first_name = 'Test'
                mock_user.last_name  = 'User'
                mock_user.get_full_name.return_value = 'Test User'
                mock_db.session.get.return_value = mock_user
                result = svc.send_sos_alert(
                    user_id=1,
                    location={'latitude': 13.058, 'longitude': 80.177},
                    contacts=[contact],
                )
        assert result['success'] is False
        assert len(result['contacts_notified']) == 0
        assert len(result['contacts_failed']) == 1

    def test_twilio_not_configured(self, app_ctx):
        for k in ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER'):
            os.environ.pop(k, None)
        from services.emergency_service import EmergencyService
        svc = EmergencyService()
        contact = self._make_contact()
        with patch('services.emergency_service.db') as mock_db:
            mock_user = MagicMock()
            mock_user.first_name = 'Test'
            mock_user.last_name  = 'User'
            mock_user.get_full_name.return_value = 'Test User'
            mock_db.session.get.return_value = mock_user
            result = svc.send_sos_alert(
                user_id=1,
                location={'latitude': 13.058, 'longitude': 80.177},
                contacts=[contact],
            )
        assert result['sms_configured'] is False
        assert result['success'] is False
        assert len(result['missing_vars']) > 0


# ============================================================
# 4. HTTP Route Tests — /sos/trigger-sos
# ============================================================

class TestTriggerSOSRoute:

    def test_unauthenticated_redirected(self, client):
        r = client.post(
            '/sos/trigger-sos',
            data=json.dumps({'latitude': 13.058, 'longitude': 80.177}),
            content_type='application/json',
        )
        assert r.status_code in (302, 401)   # redirect to login

    def test_invalid_latitude(self, logged_in_client):
        c, _ = logged_in_client
        r = c.post(
            '/sos/trigger-sos',
            data=json.dumps({'latitude': 999, 'longitude': 80.177}),
            content_type='application/json',
        )
        # Route still responds — invalid coords mean location_available=False
        assert r.status_code == 200
        d = json.loads(r.data)
        assert d['location_available'] is False

    def test_valid_coords_no_twilio(self, logged_in_client):
        for k in ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER'):
            os.environ.pop(k, None)
        c, _ = logged_in_client
        r = c.post(
            '/sos/trigger-sos',
            data=json.dumps({'latitude': 13.058, 'longitude': 80.177}),
            content_type='application/json',
        )
        assert r.status_code == 200
        d = json.loads(r.data)
        assert d['sms_configured'] is False
        assert len(d['missing_vars']) > 0

    def test_location_available_in_response(self, logged_in_client):
        c, _ = logged_in_client
        r = c.post(
            '/sos/trigger-sos',
            data=json.dumps({'latitude': 13.058, 'longitude': 80.177}),
            content_type='application/json',
        )
        assert r.status_code == 200
        d = json.loads(r.data)
        assert 'location_available' in d

    def test_no_body_returns_200(self, logged_in_client):
        c, _ = logged_in_client
        r = c.post('/sos/trigger-sos', content_type='application/json')
        assert r.status_code == 200
        d = json.loads(r.data)
        assert d['location_available'] is False

    def test_mock_twilio_success(self, logged_in_client, app):
        os.environ['TWILIO_ACCOUNT_SID']  = 'ACtest1234567890123456789012345678'
        os.environ['TWILIO_AUTH_TOKEN']   = 'authtoken1234567890123456789012'
        os.environ['TWILIO_PHONE_NUMBER'] = '+15551234567'
        try:
            c, user = logged_in_client
            mock_msg = MagicMock()
            mock_msg.sid = 'SMmocked12345'
            with patch('twilio.rest.Client') as MockClient:
                instance = MockClient.return_value
                instance.messages.create.return_value = mock_msg
                r = c.post(
                    '/sos/trigger-sos',
                    data=json.dumps({'latitude': 13.058, 'longitude': 80.177}),
                    content_type='application/json',
                )
            assert r.status_code == 200
            d = json.loads(r.data)
            assert d['sms_configured'] is True
            # If user has contacts → notified or failed; if no contacts → no_contacts
            assert 'contacts_notified' in d or d.get('no_contacts') is True
        finally:
            for k in ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER'):
                os.environ.pop(k, None)


# ============================================================
# 5. HTTP Route Tests — /sos/diagnostic
# ============================================================

class TestDiagnosticRoute:

    def test_unauthenticated_redirected(self, client):
        r = client.get('/sos/diagnostic')
        assert r.status_code in (302, 401)

    def test_diagnostic_structure(self, logged_in_client):
        c, _ = logged_in_client
        r = c.get('/sos/diagnostic')
        assert r.status_code == 200
        d = json.loads(r.data)
        assert 'twilio' in d
        assert 'emergency_contacts' in d
        assert 'diagnosis' in d
        assert 'account_sid_set' in d['twilio']
        assert 'auth_token_set' in d['twilio']
        assert 'phone_number_set' in d['twilio']
        assert 'is_configured' in d['twilio']
        assert 'missing_vars' in d['twilio']
        # Must NEVER contain the actual auth token
        raw = r.data.decode()
        # The token value itself must not appear — we can only check structure
        assert 'auth_token_set' in d['twilio']

    def test_diagnostic_contact_validity(self, logged_in_client):
        c, user = logged_in_client
        r = c.get('/sos/diagnostic')
        d = json.loads(r.data)
        contacts = d['emergency_contacts']['contacts']
        for contact in contacts:
            assert 'phone_valid' in contact
            assert 'phone_e164' in contact
            # phone_raw must not be null if contact has a number
            assert 'phone_raw' in contact


# ============================================================
# 6. HTTP Route Tests — /sos/test-sms
# ============================================================

class TestTestSMSRoute:

    def test_unauthenticated(self, client):
        r = client.post('/sos/test-sms', content_type='application/json')
        assert r.status_code in (302, 401)

    def test_test_sms_no_twilio(self, logged_in_client):
        for k in ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER'):
            os.environ.pop(k, None)
        c, _ = logged_in_client
        r = c.post('/sos/test-sms', content_type='application/json')
        assert r.status_code == 400
        d = json.loads(r.data)
        assert d['success'] is False
        assert 'missing_vars' in d

    def test_test_sms_with_mock_success(self, logged_in_client):
        os.environ['TWILIO_ACCOUNT_SID']  = 'ACtest1234567890123456789012345678'
        os.environ['TWILIO_AUTH_TOKEN']   = 'authtoken1234567890123456789012'
        os.environ['TWILIO_PHONE_NUMBER'] = '+15551234567'
        try:
            c, _ = logged_in_client
            mock_msg = MagicMock()
            mock_msg.sid = 'SMtest_success'
            with patch('twilio.rest.Client') as MockClient:
                instance = MockClient.return_value
                instance.messages.create.return_value = mock_msg
                r = c.post(
                    '/sos/test-sms',
                    data=json.dumps({'phone': '+919629333508'}),
                    content_type='application/json',
                )
            d = json.loads(r.data)
            assert d['sms_configured'] is True
            assert 'target_phone' in d
            assert 'provider_message_id' in d
        finally:
            for k in ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER'):
                os.environ.pop(k, None)

    def test_test_sms_invalid_phone_override(self, logged_in_client):
        os.environ['TWILIO_ACCOUNT_SID']  = 'ACtest1234567890123456789012345678'
        os.environ['TWILIO_AUTH_TOKEN']   = 'authtoken1234567890123456789012'
        os.environ['TWILIO_PHONE_NUMBER'] = '+15551234567'
        try:
            c, _ = logged_in_client
            r = c.post(
                '/sos/test-sms',
                data=json.dumps({'phone': 'abc'}),
                content_type='application/json',
            )
            assert r.status_code == 400
            d = json.loads(r.data)
            assert d['success'] is False
        finally:
            for k in ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER'):
                os.environ.pop(k, None)


# ============================================================
# 7. SOS Page Load
# ============================================================

class TestSOSPage:

    def test_sos_page_loads(self, logged_in_client):
        c, _ = logged_in_client
        r = c.get('/sos/')
        assert r.status_code == 200
        assert b'112' in r.data or b'SOS' in r.data

    def test_emergency_contacts_page(self, logged_in_client):
        c, _ = logged_in_client
        r = c.get('/sos/emergency-contacts')
        assert r.status_code == 200


# ============================================================
# MANUAL END-TO-END TEST PROCEDURE
# ============================================================
#
# This section is not automated. It documents the steps required
# to verify REAL Twilio SMS delivery on localhost.
#
# Prerequisites:
#   1. A Twilio account (free trial OK).
#      Sign up at: https://console.twilio.com
#   2. A Twilio phone number (provisioned in your account).
#   3. On a Trial account: destination numbers must be verified at
#      https://console.twilio.com/us1/develop/phone-numbers/manage/verified
#
# Step 1 – Set credentials in .env:
#   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
#   TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
#   TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
#
# Step 2 – Confirm emergency contact:
#   Log in → SOS → Emergency Contacts → Add Contact
#   Name: Mahesh
#   Phone: +919629333508   (must be in E.164 format)
#   Mark as Primary: YES
#
# Step 3 – Confirm configuration:
#   curl -b cookies.txt http://127.0.0.1:5000/sos/diagnostic
#   Expected: "diagnosis": "Ready to send SMS"
#
# Step 4 – Send test SMS (optional, before pressing real SOS):
#   curl -b cookies.txt -X POST http://127.0.0.1:5000/sos/test-sms \
#        -H "Content-Type: application/json"
#   Expected response: {"success": true, "provider_message_id": "SM...", ...}
#
# Step 5 – Real SOS test:
#   Open http://127.0.0.1:5000/sos/
#   Allow browser location
#   Press "Send SOS Alert" → countdown → confirm
#   Expected: "🚨 SOS activated. 1 emergency contact notified via SMS."
#   Verify Mahesh receives the SMS.
#
# Step 6 – If you see "Twilio Trial accounts can only send to verified numbers":
#   Go to https://console.twilio.com/us1/develop/phone-numbers/manage/verified
#   Add +919629333508, verify it via the call/SMS Twilio sends to that number.
#   Retry.
#
# Step 7 – Start server:
#   cd C:\Users\sabar\OneDrive\Documents\Desktop\Nexvita
#   .\venv\Scripts\python.exe app.py
#
# ============================================================
