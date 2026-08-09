"""
tests/test_ai_service.py — NexVita Gemini AI Service Tests
All Gemini API calls are mocked. No real network requests are made.
"""
import os
import pytest
from unittest.mock import patch, MagicMock


# ─── Helpers ────────────────────────────────────────────────────────────────

def _clear_env_key():
    os.environ.pop('GEMINI_API_KEY', None)


def _set_env_key(value='AIzaSyFakeKeyForTesting1234567890abcdef'):
    os.environ['GEMINI_API_KEY'] = value


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


# ─── _is_configured ─────────────────────────────────────────────────────────

class TestIsConfigured:
    def test_returns_false_when_key_absent(self):
        _clear_env_key()
        from services.ai_service import _is_configured
        assert _is_configured() is False

    def test_returns_false_when_key_empty_string(self):
        os.environ['GEMINI_API_KEY'] = ''
        from services.ai_service import _is_configured
        assert _is_configured() is False

    def test_returns_false_when_key_whitespace(self):
        os.environ['GEMINI_API_KEY'] = '   '
        from services.ai_service import _is_configured
        assert _is_configured() is False

    def test_returns_true_when_key_present(self):
        _set_env_key()
        from services.ai_service import _is_configured
        assert _is_configured() is True

    def teardown_method(self, method):
        _clear_env_key()


# ─── AIService.__init__ ──────────────────────────────────────────────────────

class TestAIServiceInit:
    def test_configured_false_without_key(self):
        _clear_env_key()
        from services.ai_service import AIService
        assert AIService().configured is False

    def test_configured_true_with_key(self):
        _set_env_key()
        from services.ai_service import AIService
        assert AIService().configured is True

    def teardown_method(self, method):
        _clear_env_key()


# ─── MODEL constant ─────────────────────────────────────────────────────────

def test_model_name_is_valid():
    from services.ai_service import MODEL
    assert MODEL == 'gemini-2.0-flash', (
        f"Expected 'gemini-2.0-flash', got '{MODEL}'. "
        "gemini-3.5-flash does not exist."
    )


# ─── _get_gemini_client ──────────────────────────────────────────────────────

class TestGetGeminiClient:
    def test_raises_when_key_missing(self):
        _clear_env_key()
        from services.ai_service import _get_gemini_client
        with pytest.raises(RuntimeError, match='missing_configuration'):
            _get_gemini_client()

    def test_raises_when_key_empty(self):
        os.environ['GEMINI_API_KEY'] = ''
        from services.ai_service import _get_gemini_client
        with pytest.raises(RuntimeError, match='missing_configuration'):
            _get_gemini_client()

    def test_returns_client_object_when_sdk_available(self):
        _set_env_key()
        mock_client = MagicMock()
        mock_genai_mod = MagicMock()
        mock_genai_mod.Client.return_value = mock_client
        with patch.dict('sys.modules', {'google': MagicMock(genai=mock_genai_mod), 'google.genai': mock_genai_mod}):
            import importlib
            import services.ai_service as ai_mod
            importlib.reload(ai_mod)
            result = ai_mod._get_gemini_client()
            assert result is mock_client

    def teardown_method(self, method):
        _clear_env_key()


# ─── _classify_error ─────────────────────────────────────────────────────────

class TestClassifyError:
    def setup_method(self, method):
        from services.ai_service import _classify_error
        self.classify = _classify_error

    def test_missing_configuration_runtime(self):
        assert self.classify(RuntimeError('missing_configuration: key not set')) == 'missing_configuration'

    def test_missing_configuration_importerror(self):
        assert self.classify(ImportError('No module named google')) == 'missing_configuration'

    def test_missing_configuration_modulenotfound(self):
        assert self.classify(ModuleNotFoundError('google-genai not found')) == 'missing_configuration'

    def test_authentication_error_api_key(self):
        assert self.classify(Exception('UNAUTHENTICATED: API key not valid')) == 'authentication_error'

    def test_authentication_error_credential(self):
        assert self.classify(Exception('invalid credential provided')) == 'authentication_error'

    def test_authentication_error_401(self):
        assert self.classify(Exception('HTTP 401 unauthorized')) == 'authentication_error'

    def test_invalid_model(self):
        assert self.classify(Exception('model not found: gemini-3.5-flash')) == 'invalid_model'

    def test_invalid_argument(self):
        assert self.classify(Exception('INVALID_ARGUMENT: unknown model')) == 'invalid_model'

    def test_rate_limit_quota(self):
        assert self.classify(Exception('resource_exhausted: quota exceeded')) == 'rate_limit'

    def test_rate_limit_429(self):
        assert self.classify(Exception('HTTP 429 too many requests')) == 'rate_limit'

    def test_network_timeout(self):
        assert self.classify(Exception('connection timeout')) == 'network_error'

    def test_network_ssl(self):
        assert self.classify(Exception('ssl error occurred')) == 'network_error'

    def test_api_error_500(self):
        assert self.classify(Exception('HTTP 500 internal server error')) == 'api_error'

    def test_unknown_fallback(self):
        assert self.classify(Exception('something completely unexpected xyz')) == 'unknown_error'


# ─── _api_error_response ─────────────────────────────────────────────────────

class TestApiErrorResponse:
    def setup_method(self, method):
        from services.ai_service import _api_error_response
        self.fn = _api_error_response

    def test_missing_configuration_returns_setup_message(self):
        result = self.fn(RuntimeError('missing_configuration: key not set'))
        assert isinstance(result, str) and len(result) > 10

    def test_authentication_error_message(self):
        result = self.fn(Exception('UNAUTHENTICATED: api_key invalid 401'))
        assert isinstance(result, str)
        # Must not expose raw exception details
        assert 'UNAUTHENTICATED' not in result

    def test_rate_limit_message(self):
        result = self.fn(Exception('resource_exhausted: quota exceeded'))
        assert 'Rate Limit' in result or 'quota' in result.lower() or 'wait' in result.lower()

    def test_invalid_model_message(self):
        result = self.fn(Exception('model not found: gemini-3.5-flash'))
        assert 'Model' in result or 'model' in result.lower()

    def test_network_error_message(self):
        result = self.fn(Exception('connection timeout'))
        assert 'Connection' in result or 'internet' in result.lower() or 'network' in result.lower()

    def test_unknown_error_generic_message(self):
        result = self.fn(Exception('completely unknown xyz problem'))
        assert 'Service Unavailable' in result or 'trouble' in result.lower()

    def test_response_is_non_empty_string(self):
        result = self.fn(Exception('some error'))
        assert isinstance(result, str) and len(result) > 0

    def test_never_exposes_api_key_value(self):
        _set_env_key('AIzaSyFakeKeyForTesting1234567890abcdef')
        result = self.fn(Exception('auth failed key=AIzaSyFakeKeyForTesting1234567890abcdef'))
        assert 'AIzaSyFakeKeyForTesting1234567890abcdef' not in result
        _clear_env_key()


# ─── AIService.get_response — mocked success ────────────────────────────────

class TestGetResponseMockedSuccess:
    def setup_method(self, method):
        _set_env_key()

    def teardown_method(self, method):
        _clear_env_key()

    def test_returns_string(self, flask_app):
        with flask_app.app_context():
            from services.ai_service import AIService
            svc = AIService()
            with patch('services.ai_service._generate', return_value='Drink more water.'):
                result = svc.get_response('What should I do for headache?', user_id=99999)
        assert isinstance(result, str) and len(result) > 0

    def test_returns_mocked_gemini_content(self, flask_app):
        expected = 'Mocked Gemini response UNIQUE_MARKER_XYZ123'
        with flask_app.app_context():
            from services.ai_service import AIService
            svc = AIService()
            with patch('services.ai_service._generate', return_value=expected):
                result = svc.get_response('Tell me about my health', user_id=99999)
        assert expected in result

    def test_emergency_bypasses_gemini_call(self, flask_app):
        with flask_app.app_context():
            from services.ai_service import AIService, EMERGENCY_RESPONSE
            svc = AIService()
            with patch('services.ai_service._generate') as mock_gen:
                result = svc.get_response('I am having a heart attack!', user_id=99999)
                mock_gen.assert_not_called()
        assert result == EMERGENCY_RESPONSE


# ─── AIService.get_response — unconfigured ───────────────────────────────────

class TestGetResponseUnconfigured:
    def test_returns_setup_message_when_no_key(self, flask_app):
        _clear_env_key()
        with flask_app.app_context():
            from services.ai_service import AIService
            svc = AIService()
            result = svc.get_response('What is my health risk?', user_id=99999)
        assert 'API key' in result or 'Configured' in result or 'Setup' in result
        _clear_env_key()


# ─── AIService.get_response — rate limit ─────────────────────────────────────

class TestGetResponseRateLimit:
    def test_rate_limit_blocks_after_threshold(self, flask_app):
        _set_env_key()
        with flask_app.app_context():
            from services.ai_service import AIService, RATE_LIMIT_PER_MIN, _rate_counters, _rate_lock
            import time
            svc = AIService()
            unique_user = 88881
            with _rate_lock:
                _rate_counters[unique_user] = [time.time()] * RATE_LIMIT_PER_MIN
            with patch('services.ai_service._generate', return_value='ok'):
                result = svc.get_response('Another message', user_id=unique_user)
        assert 'Too Many Messages' in result or 'Rate' in result or 'limit' in result.lower()
        _clear_env_key()


# ─── AIService.get_response — API errors ─────────────────────────────────────

class TestGetResponseApiErrors:
    def setup_method(self, method):
        _set_env_key()

    def teardown_method(self, method):
        _clear_env_key()

    def test_auth_failure_returns_user_friendly_message(self, flask_app):
        with flask_app.app_context():
            from services.ai_service import AIService
            svc = AIService()
            with patch('services.ai_service._generate',
                       side_effect=Exception('UNAUTHENTICATED: api_key invalid 401')):
                result = svc.get_response('What is blood pressure?', user_id=99999)
        assert isinstance(result, str) and 'UNAUTHENTICATED' not in result

    def test_quota_exceeded_returns_rate_limit_message(self, flask_app):
        with flask_app.app_context():
            from services.ai_service import AIService
            svc = AIService()
            with patch('services.ai_service._generate',
                       side_effect=Exception('resource_exhausted: quota exceeded')):
                result = svc.get_response('What is diabetes?', user_id=99999)
        assert 'Rate Limit' in result or 'quota' in result.lower() or 'wait' in result.lower()

    def test_malformed_response_returns_user_message(self, flask_app):
        with flask_app.app_context():
            from services.ai_service import AIService
            svc = AIService()
            with patch('services.ai_service._generate',
                       side_effect=AttributeError("'NoneType' object has no attribute 'text'")):
                result = svc.get_response('Summarise my records', user_id=99999)
        assert isinstance(result, str) and len(result) > 5

    def test_network_error_returns_connection_message(self, flask_app):
        with flask_app.app_context():
            from services.ai_service import AIService
            svc = AIService()
            with patch('services.ai_service._generate',
                       side_effect=Exception('connection timeout after 30s')):
                result = svc.get_response('Analyse my symptoms', user_id=99999)
        assert 'Connection' in result or 'connection' in result.lower() or 'internet' in result.lower()


# ─── AI chatbot route ────────────────────────────────────────────────────────

class TestAIChatRoute:
    def test_get_redirects_unauthenticated(self, client):
        res = client.get('/ai/chatbot')
        assert res.status_code in (302, 200)
        if res.status_code == 302:
            assert '/auth/login' in res.headers.get('Location', '')

    def test_post_redirects_unauthenticated(self, client):
        res = client.post('/ai/chatbot', json={'message': 'hello'})
        assert res.status_code in (302, 401)

    def test_post_returns_json_structure(self, flask_app, client):
        with flask_app.app_context():
            from database.db import db
            from models import User
            user = User.query.filter_by(username='ai_route_tester').first()
            if not user:
                user = User(
                    username='ai_route_tester',
                    email='ai_route@nexvita.com',
                    first_name='AI',
                    last_name='Tester',
                )
                user.set_password('TestPass123!')
                db.session.add(user)
                db.session.commit()

        client.post('/auth/login', data={
            'email': 'ai_route@nexvita.com',
            'password': 'TestPass123!',
        }, follow_redirects=True)

        with patch('services.ai_service.AIService.get_response',
                   return_value='Mock AI response — systems operational.'):
            res = client.post('/ai/chatbot', json={'message': 'Is my blood pressure normal?'})

        assert res.status_code == 200
        data = res.get_json()
        assert data is not None
        assert 'ai_response' in data
        assert 'user_message' in data
        assert 'timestamp' in data
        assert 'ai_configured' in data
        assert isinstance(data['ai_response'], str)

    def test_post_empty_message_returns_400_or_redirect(self, client):
        res = client.post('/ai/chatbot', json={'message': ''})
        assert res.status_code in (400, 302)

    def test_post_no_message_key_returns_400_or_redirect(self, client):
        res = client.post('/ai/chatbot', json={})
        assert res.status_code in (400, 302)
