import numpy as np
from datetime import datetime, timedelta
from database.db import db
from models import User, Patient, HealthRecord
import json


class PredictionService:
    def __init__(self):
        # Rule-based predictions or ML models
        pass

    def predict_bmi_trend(self, user_id, weeks=4):
        """Predict BMI trend for the next few weeks based on historical data."""
        records = (
            HealthRecord.query.filter_by(user_id=user_id)
            .filter(HealthRecord.bmi.isnot(None))
            .order_by(HealthRecord.record_date.asc())
            .all()
        )

        if len(records) < 2:
            return {
                'prediction': 'Insufficient data for prediction',
                'confidence': 'low',
                'trend': 'stable',
                'current_bmi': None,
                'historical_data': [],
                'projection': []
            }

        dates = [r.record_date for r in records]
        bmi_values = [float(r.bmi) for r in records]

        if len(bmi_values) >= 2:
            x = np.array(range(len(bmi_values)))
            y = np.array(bmi_values)
            coefficients = np.polyfit(x, y, 1)
            slope = coefficients[0]
            intercept = coefficients[1]

            future_weeks = weeks
            future_dates = [dates[-1] + timedelta(weeks=i + 1) for i in range(future_weeks)]
            future_bmi = [slope * (len(bmi_values) + i) + intercept for i in range(future_weeks)]

            if slope > 0.1:
                trend = 'increasing'
                trend_description = 'Your BMI is projected to increase'
            elif slope < -0.1:
                trend = 'decreasing'
                trend_description = 'Your BMI is projected to decrease'
            else:
                trend = 'stable'
                trend_description = 'Your BMI is projected to remain stable'

            y_pred = np.polyval(coefficients, x)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            if len(bmi_values) >= 5 and r_squared > 0.5:
                confidence = 'high'
            elif len(bmi_values) >= 3 and r_squared > 0.3:
                confidence = 'medium'
            else:
                confidence = 'low'

            return {
                'prediction': f'BMI projected to be {future_bmi[-1]:.1f} in {weeks} weeks',
                'trend_description': trend_description,
                'confidence': confidence,
                'trend': trend,
                'current_bmi': round(bmi_values[-1], 1),
                'projected_bmi': round(future_bmi[-1], 1),
                'bmi_change': round(future_bmi[-1] - bmi_values[-1], 1),
                'historical_data': [
                    {'date': d.strftime('%Y-%m-%d'), 'bmi': round(b, 1)}
                    for d, b in zip(dates, bmi_values)
                ],
                'projection': [
                    {'date': d.strftime('%Y-%m-%d'), 'bmi': round(b, 1)}
                    for d, b in zip(future_dates, future_bmi)
                ],
                'technical_details': {
                    'slope_per_week': round(slope, 3),
                    'r_squared': round(r_squared, 3),
                    'data_points': len(bmi_values)
                }
            }
        else:
            return {
                'prediction': 'Insufficient data for prediction',
                'confidence': 'low',
                'trend': 'stable',
                'current_bmi': bmi_values[-1] if bmi_values else None,
                'historical_data': [],
                'projection': []
            }

    def predict_blood_pressure_trend(self, user_id, weeks=4):
        """Predict blood pressure trend for the next few weeks."""
        records = (
            HealthRecord.query.filter_by(user_id=user_id)
            .filter(HealthRecord.systolic_bp.isnot(None), HealthRecord.diastolic_bp.isnot(None))
            .order_by(HealthRecord.record_date.asc())
            .all()
        )

        if len(records) < 2:
            return {
                'prediction': 'Insufficient data for prediction',
                'confidence': 'low',
                'systolic': {'trend': 'stable', 'current': None, 'projection': []},
                'diastolic': {'trend': 'stable', 'current': None, 'projection': []},
                'historical_data': []
            }

        dates = [r.record_date for r in records]
        systolic_values = [float(r.systolic_bp) for r in records]
        diastolic_values = [float(r.diastolic_bp) for r in records]

        def analyze_bp_trend(values, label):
            if len(values) >= 2:
                x = np.array(range(len(values)))
                y = np.array(values)
                coefficients = np.polyfit(x, y, 1)
                slope = coefficients[0]
                intercept = coefficients[1]

                future_weeks = weeks
                future_dates = [dates[-1] + timedelta(weeks=i + 1) for i in range(future_weeks)]
                future_values = [slope * (len(values) + i) + intercept for i in range(future_weeks)]

                if abs(slope) < 0.5:
                    trend = 'stable'
                elif slope > 0:
                    trend = 'increasing'
                else:
                    trend = 'decreasing'

                y_pred = np.polyval(coefficients, x)
                ss_res = np.sum((y - y_pred) ** 2)
                ss_tot = np.sum((y - np.mean(y)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

                if len(values) >= 5 and r_squared > 0.5:
                    confidence = 'high'
                elif len(values) >= 3 and r_squared > 0.3:
                    confidence = 'medium'
                else:
                    confidence = 'low'

                return {
                    'trend': trend,
                    'current': round(values[-1], 1),
                    'projected': round(future_values[-1], 1),
                    'change': round(future_values[-1] - values[-1], 1),
                    'projection': [
                        {'date': d.strftime('%Y-%m-%d'), 'value': round(v, 1)}
                        for d, v in zip(future_dates, future_values)
                    ],
                    'confidence': confidence,
                    'slope_per_week': round(slope, 3),
                    'r_squared': round(r_squared, 3)
                }
            else:
                return {
                    'trend': 'insufficient_data',
                    'current': round(values[-1], 1) if values else None,
                    'projected': None,
                    'change': None,
                    'projection': [],
                    'confidence': 'low'
                }

        systolic_analysis = analyze_bp_trend(systolic_values, 'systolic')
        diastolic_analysis = analyze_bp_trend(diastolic_values, 'diastolic')

        if systolic_analysis['trend'] == 'increasing' or diastolic_analysis['trend'] == 'increasing':
            overall_trend = 'increasing'
            advice = "Consider monitoring your blood pressure more closely and consult with your healthcare provider."
        elif systolic_analysis['trend'] == 'decreasing' or diastolic_analysis['trend'] == 'decreasing':
            overall_trend = 'decreasing'
            advice = "Your blood pressure trend is improving. Continue with your current management plan."
        else:
            overall_trend = 'stable'
            advice = "Your blood pressure remains stable. Continue regular monitoring."

        return {
            'prediction': f"BP projected to be {systolic_analysis['projected']}/{diastolic_analysis['projected']} in {weeks} weeks",
            'advice': advice,
            'overall_trend': overall_trend,
            'systolic': systolic_analysis,
            'diastolic': diastolic_analysis,
            'historical_data': [
                {
                    'date': d.strftime('%Y-%m-%d'),
                    'systolic': round(s, 1),
                    'diastolic': round(dia, 1)
                }
                for d, s, dia in zip(dates, systolic_values, diastolic_values)
            ]
        }

    def predict_weight_goal_achievement(self, user_id, target_weight, weeks=12):
        """Predict probability of achieving weight goal in specified timeframe."""
        records = (
            HealthRecord.query.filter_by(user_id=user_id)
            .filter(HealthRecord.weight.isnot(None))
            .order_by(HealthRecord.record_date.asc())
            .all()
        )

        if len(records) < 2:
            return {
                'probability': 'Insufficient data',
                'confidence': 'low',
                'message': 'Need at least 2 weight measurements to make a prediction.',
                'recommendation': 'Start tracking your weight regularly to get personalized predictions.'
            }

        dates = [r.record_date for r in records]
        weight_values = [float(r.weight) for r in records]

        current_weight = weight_values[-1]
        weight_change_needed = target_weight - current_weight

        if abs(weight_change_needed) < 0.1:
            return {
                'probability': 100.0,
                'confidence': 'high',
                'message': 'You have already reached your target weight!',
                'current_weight': current_weight,
                'target_weight': target_weight,
                'weight_change_needed': 0.0,
                'weeks_to_goal': 0,
                'recommendation': 'Maintain your current lifestyle to sustain your weight.'
            }

        if len(weight_values) >= 2:
            x = np.array(range(len(weight_values)))
            y = np.array(weight_values)
            coefficients = np.polyfit(x, y, 1)
            slope = coefficients[0]

            weeks_of_data = max(1, (dates[-1] - dates[0]).days / 7)
            weekly_change = slope * (len(weight_values) / weeks_of_data)

            if abs(weekly_change) > 0.01:
                weeks_to_goal = abs(weight_change_needed / weekly_change)
            else:
                weeks_to_goal = float('inf') if weight_change_needed != 0 else 0

            if weeks_to_goal == float('inf'):
                probability = 0.0
            else:
                if weeks_to_goal <= weeks:
                    probability = min(95.0, 70 + (30 * (1 - weeks_to_goal / weeks)))
                else:
                    probability = max(5.0, 70 * (weeks / weeks_to_goal))

            if weight_change_needed > 0 and weekly_change <= 0:
                trend_status = 'moving_away_from_goal'
                advice = "Your current weight trend is moving away from your goal. Consider adjusting your diet and exercise plan."
            elif weight_change_needed < 0 and weekly_change >= 0:
                trend_status = 'moving_away_from_goal'
                advice = "Your current weight trend is moving away from your goal. Consider adjusting your diet and exercise plan."
            elif abs(weekly_change) < 0.1:
                trend_status = 'stable'
                advice = "Your weight is stable. To reach your goal, you'll need to create a calorie deficit/surplus through diet and exercise."
            else:
                trend_status = 'moving_toward_goal'
                advice = "You're on track to reach your goal! Continue with your current plan."

            y_pred = np.polyval(coefficients, x)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            if len(weight_values) >= 8 and r_squared > 0.6:
                confidence = 'high'
            elif len(weight_values) >= 5 and r_squared > 0.3:
                confidence = 'medium'
            else:
                confidence = 'low'

            projection_weights = [current_weight + weekly_change * (i + 1) for i in range(weeks)]
            projection_dates = [dates[-1] + timedelta(weeks=i + 1) for i in range(weeks)]

            return {
                'probability': round(min(95, max(5, probability)), 1),
                'confidence': confidence,
                'trend_status': trend_status,
                'advice': advice,
                'current_weight': round(current_weight, 1),
                'target_weight': target_weight,
                'weight_change_needed': round(weight_change_needed, 1),
                'weeks_to_goal': round(weeks_to_goal, 1) if weeks_to_goal != float('inf') else None,
                'weekly_change_needed': round(weight_change_needed / weeks, 2) if weeks > 0 else 0,
                'current_weekly_change': round(weekly_change, 2),
                'projected_weight': round(projection_weights[-1], 1),
                'projection': [
                    {'date': d.strftime('%Y-%m-%d'), 'weight': round(w, 1)}
                    for d, w in zip(projection_dates, projection_weights)
                ],
                'historical_data': [
                    {'date': d.strftime('%Y-%m-%d'), 'weight': round(w, 1)}
                    for d, w in zip(dates, weight_values)
                ],
                'technical_details': {
                    'slope_per_week': round(weekly_change, 3),
                    'r_squared': round(r_squared, 3),
                    'data_points': len(weight_values)
                }
            }
        else:
            return {
                'probability': 'Insufficient data',
                'confidence': 'low',
                'message': 'Need at least 2 weight measurements to make a prediction.',
                'recommendation': 'Start tracking your weight regularly to get personalized predictions.'
            }

    def predict_diabetes_risk(self, user_id):
        """Predict diabetes risk based on health data."""
        records = (
            HealthRecord.query.filter_by(user_id=user_id)
            .order_by(HealthRecord.record_date.desc())
            .limit(10)
            .all()
        )

        if not records:
            return {
                'risk_level': 'unknown',
                'risk_score': 0,
                'factors': [],
                'recommendations': ['No health data available for risk assessment. Please start tracking your health metrics.'],
                'glucose_stats': {},
                'other_metrics': {}
            }

        risk_score = 0
        factors = []
        recommendations = []

        glucose_records = [r for r in records if r.glucose_level is not None]
        if glucose_records:
            glucose_values = [float(r.glucose_level) for r in glucose_records]
            avg_glucose = sum(glucose_values) / len(glucose_values)

            if avg_glucose >= 126:
                risk_score += 3
                factors.append(f'Elevated average glucose: {avg_glucose:.1f} mg/dL (diabetes range)')
                recommendations.append('Consult with your healthcare provider about diabetes screening and management.')
            elif avg_glucose >= 100:
                risk_score += 2
                factors.append(f'Elevated average glucose: {avg_glucose:.1f} mg/dL (prediabetes range)')
                recommendations.append('Consider lifestyle changes to prevent progression to diabetes.')
            else:
                factors.append(f'Normal average glucose: {avg_glucose:.1f} mg/dL')
        else:
            factors.append('No glucose data available')
            recommendations.append('Consider getting your blood glucose tested.')

        bmi_records = [r for r in records if r.bmi is not None]
        if bmi_records:
            bmi_values = [float(r.bmi) for r in bmi_records]
            latest_bmi = bmi_values[-1]

            if latest_bmi >= 30:
                risk_score += 2
                factors.append(f'Obesity (BMI: {latest_bmi:.1f})')
                recommendations.append('Weight management can significantly reduce diabetes risk.')
            elif latest_bmi >= 25:
                risk_score += 1
                factors.append(f'Overweight (BMI: {latest_bmi:.1f})')
                recommendations.append('Consider gradual weight loss through diet and exercise.')
            else:
                factors.append(f'Healthy weight (BMI: {latest_bmi:.1f})')
        else:
            factors.append('No BMI data available')

        bp_records = [r for r in records if r.systolic_bp is not None and r.diastolic_bp is not None]
        if bp_records:
            systolic_values = [float(r.systolic_bp) for r in bp_records]
            diastolic_values = [float(r.diastolic_bp) for r in bp_records]
            avg_systolic = sum(systolic_values) / len(systolic_values)
            avg_diastolic = sum(diastolic_values) / len(diastolic_values)

            if avg_systolic >= 140 or avg_diastolic >= 90:
                risk_score += 2
                factors.append(f'Hypertension ({avg_systolic:.0f}/{avg_diastolic:.0f})')
                recommendations.append('Blood pressure control is important for diabetes prevention.')
            elif avg_systolic >= 130 or avg_diastolic >= 80:
                risk_score += 1
                factors.append(f'Elevated blood pressure ({avg_systolic:.0f}/{avg_diastolic:.0f})')
                recommendations.append('Monitor your blood pressure regularly.')
            else:
                factors.append(f'Normal blood pressure ({avg_systolic:.0f}/{avg_diastolic:.0f})')
        else:
            factors.append('No blood pressure data available')

        if risk_score >= 7:
            risk_level = 'high'
            risk_percentage = min(85, 50 + (risk_score - 6) * 5)
        elif risk_score >= 4:
            risk_level = 'moderate'
            risk_percentage = min(50, 20 + (risk_score - 3) * 10)
        else:
            risk_level = 'low'
            risk_percentage = max(5, risk_score * 5)

        recommendations.extend([
            'Maintain a healthy weight through balanced diet and regular exercise',
            'Engage in at least 150 minutes of moderate aerobic activity per week',
            'Eat a diet rich in fruits, vegetables, whole grains, and lean proteins',
            'Limit processed foods, sugary drinks, and excessive carbohydrates',
            'Get regular check-ups with your healthcare provider',
            'If you have symptoms like frequent urination, excessive thirst, or unexplained weight loss, seek medical attention'
        ])

        recommendations = list(dict.fromkeys(recommendations))

        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_percentage': round(risk_percentage, 1),
            'factors': factors,
            'recommendations': recommendations,
            'glucose_stats': {
                'average': round(sum([float(r.glucose_level) for r in glucose_records]) / len(glucose_records), 1) if glucose_records else None,
                'minimum': round(min([float(r.glucose_level) for r in glucose_records]), 1) if glucose_records else None,
                'maximum': round(max([float(r.glucose_level) for r in glucose_records]), 1) if glucose_records else None,
                'count': len(glucose_records)
            } if glucose_records else {},
            'other_metrics': {
                'bmi': {
                    'latest': round([float(r.bmi) for r in bmi_records][-1], 1) if bmi_records else None,
                    'average': round(sum([float(r.bmi) for r in bmi_records]) / len(bmi_records), 1) if bmi_records else None,
                    'count': len(bmi_records)
                } if bmi_records else {},
                'blood_pressure': {
                    'systolic_avg': round(sum([float(r.systolic_bp) for r in bp_records]) / len(bp_records), 1) if bp_records else None,
                    'diastolic_avg': round(sum([float(r.diastolic_bp) for r in bp_records]) / len(bp_records), 1) if bp_records else None,
                    'count': len(bp_records)
                } if bp_records else {}
            }
        }

    def get_wellness_score(self, user_id):
        """Calculate a comprehensive wellness score based on multiple health factors."""
        records = (
            HealthRecord.query.filter_by(user_id=user_id)
            .order_by(HealthRecord.record_date.desc())
            .limit(10)
            .all()
        )

        if not records:
            return {
                'score': 0,
                'level': 'no_data',
                'components': {},
                'recommendations': ['Start tracking your health metrics to get a personalized wellness score.']
            }

        scores = {}

        weight_records = [r for r in records if r.weight is not None]
        if len(weight_records) >= 2:
            weights = [float(r.weight) for r in weight_records]
            weight_variance = float(np.var(weights)) if len(weights) > 1 else 0
            activity_score = max(0.0, min(25.0, 25.0 - (weight_variance * 10.0)))
            scores['weight_stability'] = round(activity_score, 1)
        else:
            scores['weight_stability'] = 12.5

        bmi_records = [r for r in records if r.bmi is not None]
        if bmi_records:
            latest_bmi = float(bmi_records[-1].bmi)
            if 18.5 <= latest_bmi <= 24.9:
                nutrition_score = 25.0
            elif 17.0 <= latest_bmi < 18.5 or 25.0 <= latest_bmi <= 27.0:
                nutrition_score = 20.0
            elif 16.0 <= latest_bmi < 17.0 or 27.0 < latest_bmi <= 30.0:
                nutrition_score = 15.0
            else:
                nutrition_score = max(0.0, 25.0 - abs(latest_bmi - 22.0) * 2.0)
            scores['nutrition'] = round(nutrition_score, 1)
        else:
            scores['nutrition'] = 12.5

        bp_records = [r for r in records if r.systolic_bp is not None and r.diastolic_bp is not None]
        if bp_records:
            latest_bp = bp_records[-1]
            systolic = float(latest_bp.systolic_bp)
            diastolic = float(latest_bp.diastolic_bp)

            if 90 <= systolic <= 120 and 60 <= diastolic <= 80:
                bp_score = 25.0
            elif 120 < systolic <= 140 or 80 < diastolic <= 90:
                bp_score = 20.0
            elif 140 < systolic <= 160 or 90 < diastolic <= 100:
                bp_score = 15.0
            else:
                bp_score = max(0.0, 25.0 - ((systolic - 120) + (diastolic - 80)) * 0.1)
            scores['blood_pressure'] = round(min(25.0, max(0.0, bp_score)), 1)
        else:
            scores['blood_pressure'] = 12.5

        hr_records = [r for r in records if r.heart_rate is not None]
        if hr_records:
            latest_hr = float(hr_records[-1].heart_rate)
            if 60 <= latest_hr <= 100:
                hr_score = 25.0
            elif 50 <= latest_hr < 60 or 100 < latest_hr <= 110:
                hr_score = 20.0
            elif 40 <= latest_hr < 50 or 110 < latest_hr <= 120:
                hr_score = 15.0
            else:
                hr_score = max(0.0, 25.0 - abs(latest_hr - 80) * 0.3)
            scores['heart_rate'] = round(min(25.0, max(0.0, hr_score)), 1)
        else:
            scores['heart_rate'] = 12.5

        glucose_records = [r for r in records if r.glucose_level is not None]
        if glucose_records:
            latest_glucose = float(glucose_records[-1].glucose_level)
            if 70 <= latest_glucose <= 99:
                glucose_score = 25.0
            elif 100 <= latest_glucose <= 125:
                glucose_score = 15.0
            else:
                glucose_score = max(0.0, 25.0 - (latest_glucose - 100) * 0.5)
            scores['glucose'] = round(min(25.0, max(0.0, glucose_score)), 1)
        else:
            scores['glucose'] = 12.5

        total_score = sum(scores.values())

        if total_score >= 85:
            level = 'excellent'
        elif total_score >= 70:
            level = 'good'
        elif total_score >= 50:
            level = 'fair'
        else:
            level = 'needs_improvement'

        recommendations = []
        if scores.get('weight_stability', 25) < 15:
            recommendations.append('Focus on maintaining a stable, healthy weight through balanced diet and regular exercise.')
        if scores.get('nutrition', 25) < 15:
            recommendations.append('Improve your nutrition by eating more fruits, vegetables, and whole grains.')
        if scores.get('blood_pressure', 25) < 15:
            recommendations.append('Monitor your blood pressure regularly and consult with your healthcare provider if it is elevated.')
        if scores.get('heart_rate', 25) < 15:
            recommendations.append('Consider discussing your heart rate with your healthcare provider, especially if you have symptoms.')
        if scores.get('glucose', 25) < 15:
            recommendations.append('Monitor your blood glucose levels and maintain a healthy diet to prevent insulin resistance.')

        if not recommendations:
            recommendations.append('Excellent work! Continue maintaining your healthy lifestyle habits.')

        return {
            'score': round(total_score, 1),
            'level': level,
            'components': scores,
            'recommendations': recommendations
        }