"""
ai_service.py — NexVita Real AI Health Assistant
Provider: Google Gemini (google-genai SDK v2.x)
Requires: GEMINI_API_KEY in .env
"""
import os
import time
import hashlib
import json
import logging
from datetime import datetime, date
from threading import Lock

from database.db import db
from models import User, Patient, HealthRecord, AIHistory
from services.prompt_templates import (
    SYSTEM_PROMPT, EMERGENCY_RESPONSE,
    build_user_context, format_history_for_gemini,
    build_symptom_prompt, build_risk_prompt,
    build_recommendations_prompt, build_report_prompt,
    is_emergency,
)

logger = logging.getLogger(__name__)

# ── Simple in-memory cache ──────────────────────────────────────
_cache: dict[str, tuple[str, float]] = {}  # {key: (response, expires_at)}
_cache_lock = Lock()
CACHE_TTL = 300  # 5 minutes for identical queries

# ── Simple in-memory rate limiter ───────────────────────────────
_rate_counters: dict[int, list[float]] = {}  # {user_id: [timestamps]}
_rate_lock = Lock()
RATE_LIMIT_PER_MIN = 20


def _check_rate_limit(user_id: int) -> bool:
    """Return True if the user is within their rate limit."""
    now = time.time()
    with _rate_lock:
        timestamps = _rate_counters.get(user_id, [])
        # Keep only timestamps within last 60 seconds
        timestamps = [t for t in timestamps if now - t < 60]
        if len(timestamps) >= RATE_LIMIT_PER_MIN:
            _rate_counters[user_id] = timestamps
            return False
        timestamps.append(now)
        _rate_counters[user_id] = timestamps
        return True


def _cache_get(key: str) -> str | None:
    with _cache_lock:
        entry = _cache.get(key)
        if entry and time.time() < entry[1]:
            return entry[0]
        _cache.pop(key, None)
        return None


def _cache_set(key: str, value: str) -> None:
    with _cache_lock:
        _cache[key] = (value, time.time() + CACHE_TTL)


def _make_cache_key(prefix: str, text: str) -> str:
    return prefix + ':' + hashlib.md5(text.encode()).hexdigest()


# ── Gemini client factory ───────────────────────────────────────
def _get_gemini_client():
    """Return a configured Gemini Client, or raise if not configured."""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY is not set in environment variables.')
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError:
        raise RuntimeError(
            'google-genai package not installed. Run: pip install google-genai'
        )


def _is_configured() -> bool:
    return bool(os.environ.get('GEMINI_API_KEY'))


MODEL = 'gemini-3.5-flash'   # Confirmed working with this API key


# ── Error messages ──────────────────────────────────────────────
def _api_error_response(error: Exception) -> str:
    err_str = str(error).lower()
    if 'api_key' in err_str or 'api key' in err_str or 'credential' in err_str:
        return (
            "## ⚠️ AI Service Not Configured\n\n"
            "The Gemini API key is missing or invalid.\n\n"
            "**To enable the AI assistant:**\n"
            "1. Get a free API key from [Google AI Studio](https://aistudio.google.com)\n"
            "2. Add `GEMINI_API_KEY=your_key` to your `.env` file\n"
            "3. Restart the server\n\n"
            "> Your key is never shared and stays on your server."
        )
    if 'quota' in err_str or 'rate' in err_str or 'limit' in err_str:
        return (
            "## ⏳ Rate Limit Reached\n\n"
            "The AI service has reached its quota limit. "
            "Please wait a minute and try again.\n\n"
            "> If this persists, check your Google AI Studio quota."
        )
    return (
        "## ⚠️ AI Service Unavailable\n\n"
        "I'm having trouble connecting right now. Please try again in a moment.\n\n"
        "> If the issue persists, please contact NexVita support."
    )


# ── Core helper: single Gemini generate call ───────────────────
def _generate(system_instruction: str, prompt: str,
               history: list[dict] | None = None,
               max_tokens: int = 1024) -> str:
    """
    Call Gemini API using the google-genai SDK.
    history: list of {'role': 'user'|'model', 'parts': [str]} dicts.
    """
    from google import genai
    from google.genai import types

    client = _get_gemini_client()

    # Build contents from history + new message
    contents = []
    if history:
        for turn in history:
            contents.append(
                types.Content(
                    role=turn['role'],
                    parts=[types.Part.from_text(text=p) for p in turn['parts']]
                )
            )
    contents.append(
        types.Content(role='user', parts=[types.Part.from_text(text=prompt)])
    )

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        max_output_tokens=max_tokens,
        temperature=0.7,
        safety_settings=[
            types.SafetySetting(
                category='HARM_CATEGORY_DANGEROUS_CONTENT',
                threshold='BLOCK_ONLY_HIGH'
            ),
            types.SafetySetting(
                category='HARM_CATEGORY_HARASSMENT',
                threshold='BLOCK_ONLY_HIGH'
            ),
            types.SafetySetting(
                category='HARM_CATEGORY_HATE_SPEECH',
                threshold='BLOCK_ONLY_HIGH'
            ),
            types.SafetySetting(
                category='HARM_CATEGORY_SEXUALLY_EXPLICIT',
                threshold='BLOCK_ONLY_HIGH'
            ),
        ]
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=config,
    )
    return response.text.strip()


# ── Public AIService class (same interface as before) ───────────
class AIService:
    """
    NexVita AI Health Assistant — powered by Google Gemini.
    All public method signatures preserved for route compatibility.
    """

    def __init__(self):
        self.configured = _is_configured()

    # ──────────────────────────────────────────────────────────
    # 1. Chat response (main chatbot endpoint)
    # ──────────────────────────────────────────────────────────
    def get_response(self, user_message: str, user_id: int) -> str:
        """Get a contextual AI response for the chatbot."""
        # Emergency check — highest priority
        if is_emergency(user_message):
            return EMERGENCY_RESPONSE

        # Rate limit
        if not _check_rate_limit(user_id):
            return (
                "## ⏳ Too Many Messages\n\n"
                f"You've sent more than {RATE_LIMIT_PER_MIN} messages in the last minute. "
                "Please wait a moment before continuing.\n\n"
                "> This limit helps keep the AI service available for all users."
            )

        if not self.configured:
            return self._unconfigured_message()

        try:
            user, patient, recent_records = self._fetch_user_data(user_id)
            user_ctx = build_user_context(user, patient, recent_records)

            # Build full system prompt with user context
            system = SYSTEM_PROMPT + '\n\n' + user_ctx

            # Fetch conversation history for context continuity
            history_records = (
                AIHistory.query.filter_by(user_id=user_id)
                .order_by(AIHistory.created_at.desc())
                .limit(20)
                .all()
            )
            gemini_history = format_history_for_gemini(history_records, max_turns=10)
            # Remove the last user message from history (it's being sent as 'prompt')
            # (The last item in history_records DESC is oldest — we already reversed)
            if gemini_history and gemini_history[-1]['role'] == 'user':
                gemini_history = gemini_history[:-1]

            return _generate(system, user_message, history=gemini_history, max_tokens=800)

        except Exception as exc:
            logger.error('AI chat error: %s', exc, exc_info=True)
            return _api_error_response(exc)

    # ──────────────────────────────────────────────────────────
    # 2. Symptom analysis
    # ──────────────────────────────────────────────────────────
    def analyze_symptoms(self, symptoms: str, user_id: int) -> str:
        """Analyze reported symptoms and provide structured guidance."""
        if is_emergency(symptoms):
            return EMERGENCY_RESPONSE

        if not self.configured:
            return self._unconfigured_message()

        cache_key = _make_cache_key('symptoms', symptoms)
        cached = _cache_get(cache_key)
        if cached:
            return cached

        try:
            user, patient, recent_records = self._fetch_user_data(user_id)
            user_ctx = build_user_context(user, patient, recent_records)
            prompt = build_symptom_prompt(symptoms, user_ctx)
            result = _generate(SYSTEM_PROMPT, prompt, max_tokens=1000)
            _cache_set(cache_key, result)
            return result

        except Exception as exc:
            logger.error('Symptom analysis error: %s', exc, exc_info=True)
            return _api_error_response(exc)

    # ──────────────────────────────────────────────────────────
    # 3. Health risk assessment
    # ──────────────────────────────────────────────────────────
    def assess_health_risk(self, patient, recent_records, user_id: int) -> str:
        """Assess health risks from patient profile and recent records."""
        if not self.configured:
            return self._unconfigured_message()

        try:
            user = User.query.get(user_id)
            user_ctx = build_user_context(user, patient, recent_records)
            prompt = build_risk_prompt(user_ctx)
            return _generate(SYSTEM_PROMPT, prompt, max_tokens=1000)

        except Exception as exc:
            logger.error('Risk assessment error: %s', exc, exc_info=True)
            return _api_error_response(exc)

    # ──────────────────────────────────────────────────────────
    # 4. Personalised recommendations
    # ──────────────────────────────────────────────────────────
    def get_personalized_recommendations(self, patient, recent_records,
                                          user_id: int) -> str:
        """Generate personalised health recommendations."""
        if not self.configured:
            return self._unconfigured_message()

        try:
            user = User.query.get(user_id)
            user_ctx = build_user_context(user, patient, recent_records)
            prompt = build_recommendations_prompt(user_ctx)
            return _generate(SYSTEM_PROMPT, prompt, max_tokens=1000)

        except Exception as exc:
            logger.error('Recommendations error: %s', exc, exc_info=True)
            return _api_error_response(exc)

    # ──────────────────────────────────────────────────────────
    # 5. Comprehensive health report
    # ──────────────────────────────────────────────────────────
    def generate_health_report(self, patient, health_records,
                                 ai_history, user_id: int) -> str:
        """Generate a full health report from all available data."""
        if not self.configured:
            return self._unconfigured_message()

        try:
            user = User.query.get(user_id)
            user_ctx = build_user_context(user, patient, health_records[:10])

            # Summarise records as compact JSON
            records_lines = []
            for rec in health_records[:20]:
                val = rec.get_display_value()
                records_lines.append(
                    f'- [{rec.record_date.strftime("%Y-%m-%d")}] '
                    f'{rec.get_display_title()}: {val}'
                    + (f' ({rec.severity})' if rec.severity else '')
                )
            records_summary = '\n'.join(records_lines) or 'No records available.'

            prompt = build_report_prompt(user_ctx, records_summary)
            return _generate(SYSTEM_PROMPT, prompt, max_tokens=1200)

        except Exception as exc:
            logger.error('Report generation error: %s', exc, exc_info=True)
            return _api_error_response(exc)

    # ──────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────
    def _fetch_user_data(self, user_id: int):
        user = User.query.get(user_id)
        patient = Patient.query.filter_by(user_id=user_id).first() if user else None
        recent_records = (
            HealthRecord.query.filter_by(user_id=user_id)
            .order_by(HealthRecord.record_date.desc())
            .limit(10).all()
        ) if user else []
        return user, patient, recent_records

    def _unconfigured_message(self) -> str:
        return (
            "## 🔧 AI Assistant Setup Required\n\n"
            "The AI assistant needs a **Gemini API key** to function.\n\n"
            "**Setup (takes 2 minutes):**\n"
            "1. Visit [Google AI Studio](https://aistudio.google.com) — it's free\n"
            "2. Click **Get API key** → Create a new key\n"
            "3. Add this line to your `.env` file:\n"
            "   ```\n"
            "   GEMINI_API_KEY=your_api_key_here\n"
            "   ```\n"
            "4. Restart the Flask server\n\n"
            "> The AI will immediately start answering your health questions."
        )