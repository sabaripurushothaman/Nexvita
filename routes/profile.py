from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, User
from utils.validators import validate_email, validate_username
from utils.helpers import sanitize_input
from datetime import datetime
import logging
import re

profile_bp = Blueprint('profile', __name__)
logger = logging.getLogger(__name__)

@profile_bp.route('', methods=['GET'])
@login_required
def get_profile():
    """Get current user's profile"""
    try:
        # Update last activity timestamp
        current_user.last_activity = datetime.utcnow()
        db.session.commit()

        logger.info(f"Profile retrieved for user {current_user.id}")
        return jsonify({
            'user': current_user.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error fetching profile for user {current_user.id}: {str(e)}")
        return jsonify({'error': 'Failed to fetch profile', 'details': str(e)}), 500

@profile_bp.route('', methods=['PUT'])
@login_required
def update_profile():
    """Update current user's profile"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Sanitize input
        username = sanitize_input(data.get('username', '').strip()) if data.get('username') else None
        email = sanitize_input(data.get('email', '').strip().lower()) if data.get('email') else None
        full_name = sanitize_input(data.get('full_name', '').strip()) if data.get('full_name') else None
        gender = sanitize_input(data.get('gender', '').strip()) if data.get('gender') else None
        phone_number = sanitize_input(data.get('phone_number', '').strip()) if data.get('phone_number') else None
        date_of_birth = data.get('date_of_birth')
        bio = sanitize_input(data.get('bio', '').strip()) if data.get('bio') else None
        website = sanitize_input(data.get('website', '').strip()) if data.get('website') else None
        location = sanitize_input(data.get('location', '').strip()) if data.get('location') else None

        # Validate if provided
        if username is not None:
            if not username:
                return jsonify({'error': 'Username cannot be empty'}), 400
            if not validate_username(username):
                return jsonify({'error': 'Username must be 3-20 characters, letters and numbers only'}), 400

        if email is not None:
            if not email:
                return jsonify({'error': 'Email cannot be empty'}), 400
            if not validate_email(email):
                return jsonify({'error': 'Invalid email format'}), 400

        # Check username uniqueness if changed
        if username is not None and username != current_user.username:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                return jsonify({'error': 'Username already exists'}), 400

        # Check email uniqueness if changed
        if email is not None and email != current_user.email:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                return jsonify({'error': 'Email already registered'}), 400

        # Update fields if provided
        if username is not None:
            current_user.username = username
        if email is not None:
            current_user.email = email
        if full_name is not None:  # Allow empty string to clear the field
            current_user.full_name = full_name if full_name else None
        if gender is not None:
            current_user.gender = gender if gender else None
        if phone_number is not None:
            current_user.phone_number = phone_number if phone_number else None
        if date_of_birth is not None:
            if date_of_birth == '':
                current_user.date_of_birth = None
            else:
                try:
                    current_user.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        if bio is not None:
            # Limit bio length
            if len(bio) > 500:
                return jsonify({'error': 'Bio must be less than 500 characters'}), 400
            current_user.bio = bio if bio else None
        if website is not None:
            # Validate URL format if provided
            if website and not re.match(r'^https?://[\w\-._~:/?#[\]@!$&'\''()*+,;=]+$', website):
                return jsonify({'error': 'Invalid URL format'}), 400
            current_user.website = website if website else None
        if location is not None:
            # Limit location length
            if len(location) > 100:
                return jsonify({'error': 'Location must be less than 100 characters'}), 400
            current_user.location = location if location else None

        # Update timestamp
        current_user.updated_at = datetime.utcnow()

        # Save changes
        db.session.commit()

        logger.info(f"Profile updated for user {current_user.id}")

        return jsonify({
            'message': 'Profile updated successfully',
            'user': current_user.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating profile for user {current_user.id}: {str(e)}")
        return jsonify({'error': 'Profile update failed', 'details': str(e)}), 500

@profile_bp.route('/<int:user_id>', methods=['GET'])
@login_required
def get_user_profile(user_id):
    """Get a specific user's profile (only if authorized)"""
    try:
        # Only allow users to view their own profile
        # In a real app, you might have admin roles or specific permissions
        if current_user.id != user_id:
            # Check if user has permission to view other profiles (e.g., admin, doctor)
            # For now, we'll restrict to own profile only
            return jsonify({'error': 'Unauthorized access'}), 403

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        logger.info(f"Profile {user_id} retrieved for user {current_user.id}")
        return jsonify({
            'user': user.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error fetching profile {user_id} for user {current_user.id}: {str(e)}")
        return jsonify({'error': 'Failed to fetch user profile', 'details': str(e)}), 500

@profile_bp.route('/deactivate', methods=['POST'])
@login_required
def deactivate_account():
    """Deactivate current user's account"""
    try:
        # Soft delete - just deactivate the account
        current_user.is_active = False
        current_user.deactivated_at = datetime.utcnow()
        current_user.updated_at = datetime.utcnow()

        # Logout the user
        from flask_login import logout_user
        logout_user()

        db.session.commit()

        logger.info(f"Account deactivated for user {current_user.id}")
        return jsonify({
            'message': 'Account deactivated successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deactivating account for user {current_user.id}: {str(e)}")
        return jsonify({'error': 'Failed to deactivate account', 'details': str(e)}), 500

@profile_bp.route('/activate', methods=['POST'])
@login_required
def activate_account():
    """Reactivate current user's account"""
    try:
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        current_user.is_active = True
        current_user.deactivated_at = None
        current_user.activated_at = datetime.utcnow()
        current_user.updated_at = datetime.utcnow()

        db.session.commit()

        logger.info(f"Account activated for user {current_user.id}")
        return jsonify({
            'message': 'Account activated successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error activating account for user {current_user.id}: {str(e)}")
        return jsonify({'error': 'Failed to activate account', 'details': str(e)}), 500

@profile_bp.route('/delete', methods=['DELETE'])
@login_required
def delete_account():
    """Permanently delete current user's account"""
    try:
        user_id = current_user.id
        username = current_user.username

        # Delete user (cascade will handle related records if configured)
        db.session.delete(current_user)
        db.session.commit()

        # Logout will be handled by frontend after this response
        logger.info(f"Account permanently deleted for user {user_id} ({username})")
        return jsonify({
            'message': 'Account deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting account for user {current_user.id}: {str(e)}")
        return jsonify({'error': 'Failed to delete account', 'details': str(e)}), 500

@profile.bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change current user's password"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if not current_password:
            return jsonify({'error': 'Current password is required'}), 400

        if not new_password:
            return jsonify({'error': 'New password is required'}), 400

        if not confirm_password:
            return jsonify({'error': 'Please confirm your new password'}), 400

        if new_password != confirm_password:
            return jsonify({'error': 'New password and confirmation do not match'}), 400

        # Verify current password
        if not current_user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401

        # Validate new password strength
        from utils.validators import validate_password
        if not validate_password(new_password):
            return jsonify({
                'error': 'New password must be at least 8 characters with uppercase, lowercase, number, and special character'
            }), 400

        # Set new password
        current_user.set_password(new_password)
        current_user.password_changed_at = datetime.utcnow()
        current_user.updated_at = datetime.utcnow()

        db.session.commit()

        logger.info(f"Password changed for user {current_user.id}")
        return jsonify({
            'message': 'Password changed successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error changing password for user {current_user.id}: {str(e)}")
        return jsonify({'error': 'Failed to change password', 'details': str(e)}), 500

@profile_bp.route('/activity', methods=['GET'])
@login_required
def get_activity_log():
    """Get user's recent activity log"""
    try:
        # This would typically query an activity log table
        # For now, we'll return basic account information
        activity = {
            'last_login': current_user.last_login.isoformat() if current_user.last_login else None,
            'last_activity': current_user.last_activity.isoformat() if current_user.last_activity else None,
            'created_at': current_user.created_at.isoformat() if current_user.created_at else None,
            'updated_at': current_user.updated_at.isoformat() if current_user.updated_at else None,
            'password_changed_at': current_user.password_changed_at.isoformat() ages current_user.password_changed_at else None,
            'is_active': current_user.is_active,
            'login_count': getattr(current_user, 'login_count', 0)  # Assuming this field exists
        }

        logger.info(f"Activity log retrieved for user {current_user.id}")
        return jsonify({
            'activity': activity
        }), 200

    except Exception as e:
        logger.error(f"Error fetching activity log for user {current_user.id}: {str(e)}")
        return jsonify({'error': 'Failed to fetch activity log', 'details': str(e)}), 500

@profile_bp.route('/export', methods=['GET'])
@login_required
def export_profile_data():
    """Export user's profile data"""
    try:
        # In a real implementation, this would generate a downloadable file
        # For now, we'll return the data as JSON
        user_data = current_user.to_dict()

        # Remove sensitive information
        sensitive_fields = ['password_hash', 'reset_token', 'verification_token']
        for field in sensitive_fields:
            user_data.pop(field, None)

        logger.info(f"Profile data exported for user {current_user.id}")
        return jsonify({
            'exported_at': datetime.utcnow().isoformat(),
            'user_data': user_data
        }), 200

    except Exception as e:
        logger.error(f"Error exporting profile data for user {current_user.id}: {str(e)}")
        return jsonify({'error': 'Failed to export profile data', 'details': str(e)}), 500