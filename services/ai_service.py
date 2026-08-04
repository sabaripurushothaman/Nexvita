import os
from datetime import datetime, date
from database.db import db
from models import User, Patient, HealthRecord
from utils.helpers import validate_json_response
import json


class AIService:
    def __init__(self):
        """Initialize OpenAI client. Falls back to mock mode when no API key is set."""
        self.api_key = os.environ.get('OPENAI_API_KEY')
        self.use_mock = not bool(self.api_key)

        if not self.use_mock:
            try:
                import openai
                self._openai = openai
                self._openai.api_key = self.api_key
            except ImportError:
                # openai package not installed; degrade gracefully
                self.use_mock = True
                self._openai = None
        else:
            self._openai = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_response(self, user_message, user_id):
        """Get a response from the AI chatbot."""
        if self.use_mock:
            return self._mock_chat_response(user_message)

        try:
            user = User.query.get(user_id)
            patient = Patient.query.filter_by(user_id=user_id).first() if user else None
            recent_records = (
                HealthRecord.query.filter_by(user_id=user_id)
                .order_by(HealthRecord.record_date.desc())
                .limit(5).all()
            ) if user else []

            context = self._build_health_context(user, patient, recent_records)

            response = self._openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are a helpful health assistant for NexVita. "
                            f"Use the following context about the user: {context}"
                        ),
                    },
                    {"role": "user", "content": user_message},
                ],
                max_tokens=150,
                temperature=0.7,
            )
            return response.choices[0].message["content"].strip()
        except Exception:
            return self._mock_chat_response(user_message)

    def analyze_symptoms(self, symptoms, user_id):
        """Analyze symptoms and provide a preliminary assessment."""
        if self.use_mock:
            return self._mock_symptom_analysis(symptoms)

        try:
            user = User.query.get(user_id)
            patient = Patient.query.filter_by(user_id=user_id).first() if user else None
            recent_records = (
                HealthRecord.query.filter_by(user_id=user_id)
                .order_by(HealthRecord.record_date.desc())
                .limit(10).all()
            ) if user else []

            context = self._build_health_context(user, patient, recent_records)

            prompt = (
                f"Based on the following user health context and symptoms, provide a preliminary analysis:\n"
                f"Context: {context}\n"
                f"Symptoms: {symptoms}\n\n"
                f"Please provide:\n"
                f"1. Possible conditions (list up to 3)\n"
                f"2. Recommended next steps (when to see a doctor, emergency signs)\n"
                f"3. Self-care suggestions\n"
                f"4. Disclaimer that this is not medical advice\n\n"
                f"Keep the response concise and helpful."
            )

            response = self._openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a medical AI assistant. Provide helpful, "
                            "preliminary health information based on symptoms and user health data."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.5,
            )
            return response.choices[0].message["content"].strip()
        except Exception:
            return self._mock_symptom_analysis(symptoms)

    def assess_health_risk(self, patient, recent_records, user_id):
        """Assess health risks based on user data."""
        if self.use_mock:
            return self._mock_health_risk_assessment(patient, recent_records)

        try:
            context = self._build_health_context(None, patient, recent_records)

            prompt = (
                f"Based on the following patient data and recent health records, assess potential health risks:\n"
                f"Patient Data: {context}\n\n"
                f"Please provide:\n"
                f"1. Risk level (low, medium, high) for common conditions (diabetes, hypertension, heart disease)\n"
                f"2. Key risk factors identified\n"
                f"3. Recommended preventive measures\n"
                f"4. Suggested follow-up actions"
            )

            response = self._openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a medical AI assistant specializing in "
                            "preventive health and risk assessment."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=250,
                temperature=0.5,
            )
            return response.choices[0].message["content"].strip()
        except Exception:
            return self._mock_health_risk_assessment(patient, recent_records)

    def get_personalized_recommendations(self, patient, recent_records, user_id):
        """Generate personalized health recommendations."""
        if self.use_mock:
            return self._mock_personalized_recommendations(patient, recent_records)

        try:
            context = self._build_health_context(None, patient, recent_records)

            prompt = (
                f"Based on the following patient data and recent health records, "
                f"generate personalized health recommendations:\n"
                f"Patient Data: {context}\n\n"
                f"Please provide recommendations in these categories:\n"
                f"1. Nutrition and diet\n"
                f"2. Exercise and physical activity\n"
                f"3. Sleep and stress management\n"
                f"4. Preventive screenings and check-ups\n"
                f"5. Lifestyle modifications\n\n"
                f"Make the recommendations specific, actionable, and tailored to the user's profile."
            )

            response = self._openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a medical AI assistant specializing in personalized "
                            "health recommendations and lifestyle medicine."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=400,
                temperature=0.6,
            )
            return response.choices[0].message["content"].strip()
        except Exception:
            return self._mock_personalized_recommendations(patient, recent_records)

    def generate_health_report(self, patient, health_records, ai_history, user_id):
        """Generate a comprehensive health report."""
        if self.use_mock:
            return self._mock_health_report(patient, health_records, ai_history)

        try:
            user = User.query.get(user_id) if user_id else None
            context = self._build_health_context(user, patient, health_records[:10])

            records_summary = []
            for record in health_records[:20]:
                records_summary.append({
                    'date': record.record_date.strftime('%Y-%m-%d'),
                    'type': record.record_type,
                    'systolic_bp': record.systolic_bp,
                    'diastolic_bp': record.diastolic_bp,
                    'heart_rate': record.heart_rate,
                    'weight': float(record.weight) if record.weight else None,
                    'glucose': float(record.glucose_level) if record.glucose_level else None,
                    'notes': record.notes or 'No additional notes',
                })

            prompt = (
                f"Generate a comprehensive health report for the following user:\n"
                f"User Context: {context}\n\n"
                f"Recent Health Records: {json.dumps(records_summary, indent=2)}\n\n"
                f"Please include:\n"
                f"1. Executive summary of overall health status\n"
                f"2. Trends in vital signs (if available)\n"
                f"3. Notable health events or patterns\n"
                f"4. Areas of concern or improvement\n"
                f"5. Personalized recommendations for the next 3-6 months\n"
                f"6. Suggested goals and targets\n\n"
                f"Format the report in a clear, professional manner easy for the user to understand."
            )

            response = self._openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a medical AI assistant specialized in generating "
                            "comprehensive health reports from user health data."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.5,
            )
            return response.choices[0].message["content"].strip()
        except Exception:
            return self._mock_health_report(patient, health_records, ai_history)

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _build_health_context(self, user, patient, recent_records):
        """Build a context string from user data for the AI prompt."""
        context_parts = []

        if user:
            context_parts.append(f"User: {user.username} ({user.email})")
            context_parts.append(f"Role: {user.role}")

        if patient:
            context_parts.append(f"Patient ID: {patient.patient_id}")
            if patient.date_of_birth:
                context_parts.append(f"Date of Birth: {patient.date_of_birth}")
                context_parts.append(
                    f"Age: {self._calculate_age_from_dob(patient.date_of_birth)}"
                )
            if patient.gender:
                context_parts.append(f"Gender: {patient.gender}")
            if patient.blood_type:
                context_parts.append(f"Blood Type: {patient.blood_type}")
            if patient.height_cm:
                context_parts.append(f"Height: {patient.height_cm} cm")
            if patient.weight_kg:
                context_parts.append(f"Weight: {patient.weight_kg} kg")
            if patient.allergies:
                context_parts.append(f"Allergies: {patient.allergies}")
            if patient.chronic_conditions:
                context_parts.append(f"Chronic Conditions: {patient.chronic_conditions}")

        if recent_records:
            context_parts.append("Recent Health Records:")
            for record in recent_records[:5]:
                record_str = (
                    f"- {record.record_type} on "
                    f"{record.record_date.strftime('%Y-%m-%d')}"
                )
                if record.systolic_bp and record.diastolic_bp:
                    record_str += f", BP: {record.systolic_bp}/{record.diastolic_bp} mmHg"
                if record.heart_rate:
                    record_str += f", HR: {record.heart_rate} bpm"
                if record.temperature:
                    record_str += f", Temp: {record.temperature}°C"
                if record.weight:
                    record_str += f", Weight: {record.weight} kg"
                if record.glucose_level:
                    record_str += f", Glucose: {record.glucose_level} mg/dL"
                context_parts.append(record_str)

        return " | ".join(context_parts)

    def _calculate_age_from_dob(self, dob):
        """Calculate age from date of birth."""
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    # ------------------------------------------------------------------
    # Mock responses (used when OpenAI is not configured)
    # ------------------------------------------------------------------

    def _mock_chat_response(self, user_message):
        return (
            f"I'm a mock AI assistant. You said: '{user_message}'. "
            f"In a real implementation, I would use OpenAI to provide a personalized "
            f"health response based on your medical history."
        )

    def _mock_symptom_analysis(self, symptoms):
        return f"""Mock Symptom Analysis for: {symptoms}

Possible Conditions:
1. Common cold
2. Seasonal allergies
3. Mild flu

Recommended Next Steps:
- Monitor symptoms for 24-48 hours
- Stay hydrated and rest
- Seek medical attention if symptoms worsen or persist beyond 3 days
- Emergency signs: difficulty breathing, chest pain, high fever (>103°F)

Self-care Suggestions:
- Over-the-counter pain relievers for fever or discomfort
- Warm fluids and rest
- Use a humidifier if congestion is present

Disclaimer: This is not medical advice. Please consult with a healthcare professional for proper diagnosis and treatment."""

    def _mock_health_risk_assessment(self, patient, recent_records):
        return """Mock Health Risk Assessment:

Risk Level: Low to Moderate

Key Risk Factors Identified:
- Limited recent health data available
- Age and lifestyle factors not fully assessed

Recommended Preventive Measures:
- Schedule regular check-ups with your primary care physician
- Maintain a balanced diet rich in fruits, vegetables, and whole grains
- Engage in regular physical activity (150 minutes moderate exercise per week)
- Get adequate sleep (7-9 hours per night)
- Manage stress through relaxation techniques

Suggested Follow-up:
- Complete a comprehensive health profile in the app
- Consider annual blood work and vital signs screening
- Follow up with healthcare provider for personalized risk assessment"""

    def _mock_personalized_recommendations(self, patient, recent_records):
        return """Mock Personalized Health Recommendations:

Nutrition and Diet:
- Increase vegetable intake to at least 3 servings per day
- Choose whole grains over refined carbohydrates
- Limit processed foods and added sugars
- Stay hydrated with 8 glasses of water daily

Exercise and Physical Activity:
- Start with 30 minutes of brisk walking, 5 days per week
- Include strength training exercises 2 times per week
- Incorporate flexibility and balance exercises

Sleep and Stress Management:
- Aim for 7-9 hours of quality sleep each night
- Establish a consistent sleep schedule
- Practice relaxation techniques like deep breathing or meditation

Preventive Screenings and Check-ups:
- Annual physical examination
- Blood pressure check every 6 months
- Cholesterol screening every 4-6 years
- Diabetes screening every 3 years (starting at age 45, or earlier if risk factors)

Lifestyle Modifications:
- Quit smoking if applicable
- Limit alcohol consumption to moderate levels
- Maintain a healthy weight through diet and exercise"""

    def _mock_health_report(self, patient, health_records, ai_history):
        return f"""Mock Comprehensive Health Report for Patient ID: {patient.patient_id if patient else 'N/A'}

EXECUTIVE SUMMARY:
This is a mock health report generated for demonstration purposes. In a real implementation, this would contain a comprehensive analysis of your health data.

HEALTH RECORDS OVERVIEW:
Total Records: {len(health_records)}
AI Interactions: {len(ai_history)}

RECOMMENDATIONS:
1. Continue regular health monitoring through the NexVita app
2. Schedule regular check-ups with your healthcare provider
3. Maintain a balanced diet and regular exercise routine
4. Track your vital signs consistently
5. Use the AI health assistant for personalized health guidance

NEXT STEPS:
- Update your health profile with any recent changes
- Set health goals for the next 3-6 months
- Review your reports regularly to track progress

Note: This report is for informational purposes only and does not constitute medical advice."""