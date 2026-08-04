from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from database.db import db
from models import User, AIHistory, Patient, HealthRecord
from services.ai_service import AIService
from services.prediction_service import PredictionService
from utils.helpers import flash_errors
from datetime import datetime
import json

ai_bp = Blueprint('ai', __name__, url_prefix='/ai')


@ai_bp.route('/chatbot')
@login_required
def chatbot():
    # Get conversation history for the user
    history = (
        AIHistory.query.filter_by(user_id=current_user.id)
        .order_by(AIHistory.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template('ai/chatbot.html', history=history)


@ai_bp.route('/chatbot', methods=['POST'])
@login_required
def chat():
    user_message = request.form.get('message') or request.json.get('message')

    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    # Save user message
    user_msg = AIHistory(
        user_id=current_user.id,
        message_type='user',
        content=user_message
    )
    db.session.add(user_msg)
    db.session.commit()

    # Get AI response
    ai_service = AIService()
    ai_response = ai_service.get_response(user_message, current_user.id)

    # Save AI response
    ai_msg = AIHistory(
        user_id=current_user.id,
        message_type='ai',
        content=ai_response
    )
    db.session.add(ai_msg)
    db.session.commit()

    return jsonify({
        'user_message': user_message,
        'ai_response': ai_response,
        'timestamp': datetime.utcnow().isoformat()
    })


@ai_bp.route('/symptom-checker', methods=['GET', 'POST'])
@login_required
def symptom_checker():
    if request.method == 'POST':
        symptoms = request.form.get('symptoms')

        # Analyze symptoms using AI service
        ai_service = AIService()
        analysis = ai_service.analyze_symptoms(symptoms, current_user.id)

        # Save user message
        user_msg = AIHistory(
            user_id=current_user.id,
            message_type='user',
            content=f"Symptom check: {symptoms}"
        )
        db.session.add(user_msg)

        # Save AI response
        ai_msg = AIHistory(
            user_id=current_user.id,
            message_type='ai',
            content=str(analysis)
        )
        db.session.add(ai_msg)
        db.session.commit()

        return render_template(
            'ai/symptom_checker.html',
            analysis=analysis,
            symptoms=symptoms
        )

    return render_template('ai/symptom_checker.html')


@ai_bp.route('/health-risk')
@login_required
def health_risk_assessment():
    # Get user's health data for risk assessment
    patient = Patient.query.filter_by(user_id=current_user.id).first()

    recent_records = (
        HealthRecord.query.filter_by(user_id=current_user.id)
        .order_by(HealthRecord.record_date.desc())
        .limit(10)
        .all()
    )

    ai_service = AIService()
    risk_assessment = ai_service.assess_health_risk(
        patient,
        recent_records,
        current_user.id
    )

    # Save to history
    user_msg = AIHistory(
        user_id=current_user.id,
        message_type='user',
        content="Health risk assessment request"
    )
    db.session.add(user_msg)

    ai_msg = AIHistory(
        user_id=current_user.id,
        message_type='ai',
        content=str(risk_assessment)
    )
    db.session.add(ai_msg)
    db.session.commit()

    return render_template(
        'ai/health_risk.html',
        assessment=risk_assessment,
        patient=patient,
        recent_records=recent_records
    )


@ai_bp.route('/recommendations')
@login_required
def recommendations():
    # Get personalized health recommendations
    patient = Patient.query.filter_by(user_id=current_user.id).first()

    recent_records = (
        HealthRecord.query.filter_by(user_id=current_user.id)
        .order_by(HealthRecord.record_date.desc())
        .limit(10)
        .all()
    )

    ai_service = AIService()
    recommendations = ai_service.get_personalized_recommendations(
        patient,
        recent_records,
        current_user.id
    )

    # Save to history
    user_msg = AIHistory(
        user_id=current_user.id,
        message_type='user',
        content="Request for health recommendations"
    )
    db.session.add(user_msg)

    ai_msg = AIHistory(
        user_id=current_user.id,
        message_type='ai',
        content=str(recommendations)
    )
    db.session.add(ai_msg)
    db.session.commit()

    return render_template(
        'ai/recommendations.html',
        recommendations=recommendations,
        patient=patient
    )


@ai_bp.route('/report')
@login_required
def generate_report():
    # Generate comprehensive health report
    patient = Patient.query.filter_by(user_id=current_user.id).first()

    health_records = (
        HealthRecord.query.filter_by(user_id=current_user.id)
        .order_by(HealthRecord.record_date.desc())
        .all()
    )

    ai_history = (
        AIHistory.query.filter_by(user_id=current_user.id)
        .order_by(AIHistory.created_at.desc())
        .limit(20)
        .all()
    )

    ai_service = AIService()
    report = ai_service.generate_health_report(
        patient,
        health_records,
        ai_history,
        current_user.id
    )

    # Save to history
    user_msg = AIHistory(
        user_id=current_user.id,
        message_type='user',
        content="Health report generation request"
    )
    db.session.add(user_msg)

    ai_msg = AIHistory(
        user_id=current_user.id,
        message_type='ai',
        content=report
    )
    db.session.add(ai_msg)
    db.session.commit()

    return render_template(
        'ai/report.html',
        report=report,
        patient=patient,
        health_records=health_records[:5],
        ai_history=ai_history[:5]
    )


@ai_bp.route('/insights')
@login_required
def insights():
    """Health Insights page — wellness score and trend predictions."""
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    recent_records = (
        HealthRecord.query.filter_by(user_id=current_user.id)
        .order_by(HealthRecord.record_date.desc())
        .limit(20)
        .all()
    )
    prediction_service = PredictionService()
    wellness = prediction_service.get_wellness_score(current_user.id)
    bmi_trend = prediction_service.predict_bmi_trend(current_user.id)
    bp_trend = prediction_service.predict_blood_pressure_trend(current_user.id)
    diabetes_risk = prediction_service.predict_diabetes_risk(current_user.id)
    return render_template(
        'ai/insights.html',
        wellness=wellness,
        bmi_trend=bmi_trend,
        bp_trend=bp_trend,
        diabetes_risk=diabetes_risk,
        patient=patient,
        recent_records=recent_records
    )