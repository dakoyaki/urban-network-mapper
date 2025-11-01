from flask import Blueprint, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db
from ..models import User
from ..utils.errors import ValidationError

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        raise ValidationError('Email and password are required')
    
    email = data['email'].lower().strip()
    password = data['password']
    role = data.get('role', 'student')
    
    # Validate role
    if role not in ['student', 'instructor', 'admin']:
        raise ValidationError('Invalid role. Must be student, instructor, or admin')
    
    # Check if user already exists
    if User.query.filter_by(email=email).first():
        raise ValidationError('User with this email already exists')
    
    # Create new user
    user = User(
        email=email,
        password_hash=generate_password_hash(password),
        role=role
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'message': 'User created successfully',
        'user': {
            'id': user.id,
            'email': user.email,
            'role': user.role
        }
    }), 201

@bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        raise ValidationError('Email and password are required')
    
    email = data['email'].lower().strip()
    password = data['password']
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not check_password_hash(user.password_hash, password):
        raise ValidationError('Invalid email or password')
    
    login_user(user, remember=data.get('remember', False))
    
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'email': user.email,
            'role': user.role
        }
    })

@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout user"""
    logout_user()
    return jsonify({'message': 'Logout successful'})

@bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current user information"""
    return jsonify({
        'user': {
            'id': current_user.id,
            'email': current_user.email,
            'role': current_user.role,
            'created_at': current_user.created_at.isoformat()
        }
    })

@bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    data = request.get_json()
    
    if not data or not data.get('current_password') or not data.get('new_password'):
        raise ValidationError('Current password and new password are required')
    
    current_password = data['current_password']
    new_password = data['new_password']
    
    # Verify current password
    if not check_password_hash(current_user.password_hash, current_password):
        raise ValidationError('Current password is incorrect')
    
    # Update password
    current_user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    return jsonify({'message': 'Password changed successfully'})
