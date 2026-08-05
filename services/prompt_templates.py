"""
prompt_templates.py — AI prompt construction for NexVita Health Assistant.
Builds system prompt, user context block, and per-feature user prompts.
"""
from datetime import date


# ── Emergency keywords — triggers immediate referral message ───
EMERGENCY_KEYWORDS = [
    'chest pain', 'heart attack', 'stroke', 'difficulty breathing',
    'can\'t breathe', 'cannot breathe', 'severe bleeding', 'unconscious',
    'loss of consciousness', 'passing out', 'seizure', 'anaphylaxis',
    'severe allergic reaction', 'suicidal', 'want to die', 'kill myself',
    'overdose', 'poisoning', 'choking', 'severe head injury', 'paralysis',
]

EMERGENCY_RESPONSE = """\
## 🚨 Emergency Alert

Based on your message, you may be describing **emergency symptoms** that require **immediate medical attention**.

**Please act immediately:**
- 🏥 **Go to the nearest emergency room** right away
- 📞 **Call emergency services: 112 (India) / 911 (US)** immediately
- 📲 **Use the SOS feature** in NexVita to alert your emergency contacts

---
> ⚠️ **Do NOT wait.** Emergency symptoms require professional medical care immediately.
> NexVita AI cannot provide emergency medical assistance.
"""


# ── Master system prompt ────────────────────────────────────────
SYSTEM_PROMPT = """\
You are **NexVita AI Health Assistant** — a knowledgeable, empathetic, and responsible medical AI built into the NexVita healthcare platform.

## Your Role
You assist users with:
- General healthcare questions and medical education
- Interpreting and explaining their personal health records
- Symptom analysis and triage guidance
- Medication information and interactions
- Nutrition and dietary advice
- Fitness and exercise recommendations
- Mental wellness and stress management
- Preventive health and screening reminders

## Formatting Rules (STRICT)
- **Always** respond using structured Markdown
- Use `##` and `###` headings to organise sections
- Use bullet lists (`-`) for multiple items
- Use **bold** for key terms and values
- Use tables for comparisons (e.g., normal vs. abnormal ranges)
- Use `>` blockquotes for important notices and disclaimers
- Keep responses thorough but scannable — no wall-of-text paragraphs
- Typical response length: 200–500 words

## Safety Rules (MANDATORY)
1. **Never diagnose** — always say "this may indicate" or "this could be consistent with"
2. **Never prescribe** — provide only general dosage information from standard references
3. **Always recommend** consulting a healthcare professional for any clinical decision
4. For any question about diagnosis, medication, or treatment: **always include the medical disclaimer**
5. For emergency symptoms (chest pain, stroke, difficulty breathing, severe bleeding, loss of consciousness, suicidal thoughts, overdose): **immediately recommend emergency services**
6. For mental health distress: **always recommend professional support and helpline numbers**

## Medical Disclaimer (append to clinical responses)
> ⚕️ **Medical Disclaimer:** This information is for educational purposes only and does not constitute medical advice, diagnosis, or treatment. Always consult a qualified healthcare professional for personal medical guidance.

## Response Structure Template
For clinical questions, use this structure:
```
## Overview
(Brief 1-2 sentence summary)

## Key Information
(Core facts, bullet points)

## Recommendations
(Actionable steps)

## When to See a Doctor
(Red flags and when to seek care)

> ⚕️ Medical Disclaimer
```

## Personalisation
- When user health data is provided, reference it directly
- Compare their values to normal ranges (e.g., "Your BP of 142/92 is above the normal range of <120/80")
- Acknowledge their chronic conditions and allergies in recommendations
- Be encouraging and supportive — not alarming
"""


# ── User context block builder ─────────────────────────────────
def build_user_context(user, patient, recent_records):
    """
    Build a structured context string from user/patient data.
    This is injected into every AI request as a separate system block.
    """
    lines = ['[USER HEALTH CONTEXT]']

    if user:
        name = user.first_name or user.username
        lines.append(f'Name: {name}')

    if patient:
        if patient.date_of_birth:
            today = date.today()
            dob = patient.date_of_birth
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            lines.append(f'Age: {age}')
        if patient.gender:
            lines.append(f'Gender: {patient.gender}')
        if patient.blood_type:
            lines.append(f'Blood Type: {patient.blood_type}')
        if patient.height_cm:
            lines.append(f'Height: {patient.height_cm} cm')
        if patient.weight_kg:
            w = float(patient.weight_kg)
            lines.append(f'Weight: {w:.1f} kg')
            if patient.height_cm:
                h = float(patient.height_cm) / 100
                bmi = w / (h ** 2)
                lines.append(f'BMI: {bmi:.1f}')
        if patient.allergies:
            lines.append(f'Allergies: {patient.allergies}')
        if patient.chronic_conditions:
            lines.append(f'Chronic Conditions: {patient.chronic_conditions}')
        if patient.primary_physician:
            lines.append(f'Primary Physician: {patient.primary_physician}')

    if recent_records:
        lines.append('Recent Health Records:')
        for rec in recent_records[:8]:
            parts = [f'  - [{rec.record_date.strftime("%Y-%m-%d")}] {rec.get_display_title()}']
            val = rec.get_display_value()
            if val and val != '—':
                parts[0] += f': {val}'
            if rec.severity and rec.severity != 'normal':
                parts[0] += f' (severity: {rec.severity})'
            if rec.status:
                parts[0] += f' [status: {rec.status}]'
            lines.extend(parts)

    lines.append('[/USER HEALTH CONTEXT]')
    return '\n'.join(lines)


# ── Conversation history formatter ─────────────────────────────
def format_history_for_gemini(history_records, max_turns=10):
    """
    Convert AIHistory DB records to Gemini SDK chat history format.
    Returns list of {'role': 'user'|'model', 'parts': [text]} dicts.
    """
    # history_records are in DESC order (newest first) — reverse for chronological
    ordered = list(reversed(history_records))
    # Take last max_turns messages
    ordered = ordered[-max_turns:]

    gemini_history = []
    for rec in ordered:
        role = 'model' if rec.message_type == 'ai' else 'user'
        gemini_history.append({
            'role': role,
            'parts': [rec.content]
        })
    return gemini_history


# ── Per-feature prompt builders ────────────────────────────────

def build_symptom_prompt(symptoms, user_context):
    return f"""\
{user_context}

The user is reporting the following symptoms: **{symptoms}**

Please provide a comprehensive symptom analysis using this structure:

## Symptom Overview
(What the reported symptoms suggest)

## Possible Causes
(List 3–5 possible causes, from most to least common)

## Home Care Suggestions
(Safe self-care measures)

## Hydration & Rest
(Specific advice)

## Warning Signs — Seek Immediate Care If
(Red flag symptoms that require urgent attention)

## When to See a Doctor
(Clear guidance on timing)

> ⚕️ **Important:** This is not a medical diagnosis. Please consult a healthcare professional.
"""


def build_risk_prompt(user_context):
    return f"""\
{user_context}

Please perform a health risk assessment for this user based on their profile and health records.

## Overall Health Risk Summary
(Rate as: Low / Moderate / High — with brief explanation)

## Risk Factors Identified
| Risk Factor | Current Status | Normal Range |
|---|---|---|
(Fill based on available data)

## Condition-Specific Risk
- **Diabetes Risk:** 
- **Hypertension Risk:**
- **Cardiovascular Risk:**

## Recommended Preventive Actions
(Specific, actionable steps)

## Suggested Follow-up Tests / Screenings
(With recommended frequency)

> ⚕️ Medical Disclaimer applies.
"""


def build_recommendations_prompt(user_context):
    return f"""\
{user_context}

Please generate personalised health recommendations for this user.

## 🥗 Nutrition & Diet
(Tailored to their conditions and health data)

## 🏃 Exercise & Physical Activity
(Appropriate for their age, weight, and conditions)

## 😴 Sleep & Stress Management

## 🩺 Preventive Screenings & Check-ups
(With recommended frequency based on age/gender)

## 💊 Medication & Supplement Notes
(General information only — not prescriptive)

## 🎯 Health Goals for the Next 3 Months
(Measurable, achievable targets)

> ⚕️ Medical Disclaimer applies.
"""


def build_report_prompt(user_context, records_summary):
    return f"""\
{user_context}

Health Records Summary (last 20 entries):
{records_summary}

Please generate a comprehensive health report.

## Executive Summary
(Overall health status in 2-3 sentences)

## Vital Signs Trends
(Analyse trends from the records — improving / stable / worsening)

## Notable Patterns & Events
(Any concerning patterns or positive changes)

## Areas of Concern
(What needs attention)

## Positive Achievements
(What has improved)

## Recommendations for Next 3–6 Months
(Specific and actionable)

## Health Goals & Targets
(Measurable targets)

> ⚕️ This report is for informational purposes only and does not constitute medical advice.
"""


def is_emergency(message: str) -> bool:
    """Return True if the message contains emergency keywords."""
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in EMERGENCY_KEYWORDS)
