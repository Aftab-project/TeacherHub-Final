"""
Authentication routes for Team Collaboration Platform.

This module is responsible for user identity flows:
1. Register a new account
2. Log in and create a session
3. Log out and clear session state
4. View/edit user profiles
5. Search users for mentions/invites

Security notes:
- Passwords are hashed in the User model (PBKDF2 via werkzeug)
- Sensitive routes require authentication via @login_required
- Logout is POST-only (helps avoid accidental/CSRF-triggered logout links)
- Form inputs are validated before writing to the database
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, Team, Role, TeamMember, Channel
import string
import random

# ===== BLUEPRINT SETUP =====
# All routes here will be prefixed with /auth
bp = Blueprint('auth', __name__, url_prefix='/auth')


def generate_team_code(length=8):
    """
    Generate a random team code for invitations.
    
    Why random codes?
    - Short and memorable
    - Hard to guess (random 8-char alphanumeric = 2.8 trillion combinations)
    - No need to track what's taken (collision unlikely)
    """
    # Allowed characters: A-Z + 0-9
    chars = string.ascii_uppercase + string.digits
    # Build a random string of requested length
    return ''.join(random.choice(chars) for _ in range(length))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration endpoint.
    
    GET: Shows registration form
    POST: Processes registration
    
    Validation:
    - Username: required, unique, 3-50 chars
    - Email: required, unique, valid format
    - Password: required, min 8 chars, confirmation must match
    
    Security:
    - Password is hashed before storing
    - Email uniqueness prevents account takeover
    - Username uniqueness for login
    """
    
    # GET: show registration form
    # POST: validate input and create account
    if request.method == 'POST':
        # Read and normalize form values
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # ===== VALIDATION =====
        errors = []
        
        if not username or len(username) < 3 or len(username) > 50:
            errors.append('Username must be 3-50 characters')
        
        if not email or '@' not in email:
            errors.append('Valid email address required')
        
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters')
        
        if password != password_confirm:
            errors.append('Passwords do not match')
        
        # Username/email must be globally unique
        if User.query.filter_by(username=username).first():
            errors.append('Username already taken')
        
        if User.query.filter_by(email=email).first():
            errors.append('Email already registered')
        
        # If anything failed validation, show all errors and return to form
        if errors:
            for error in errors:
                flash(error, 'error')
            return redirect(url_for('auth.register'))
        
        # ===== CREATE USER =====
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        # Hash and store password securely (never store plaintext)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Ask user to log in after account creation
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    # First visit (GET)
    return render_template('auth/register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login endpoint.
    
    GET: Shows login form
    POST: Authenticates user and creates session
    
    Security:
    - Password checked against hash
    - Session created if credentials valid
    - User marked as authenticated
    """
    
    # If already logged in, don't show login page again.
    # Respect ?next=... when present; otherwise go to Teacher Hub home.
    if current_user.is_authenticated:
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('hub.hub_home'))
    
    if request.method == 'POST':
        # Accept either username or email in one input field
        username_or_email = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '')
        
        # Find user by username or email
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        
        # Validate user existence + password hash
        if user and user.check_password(password):
            # Block disabled accounts
            if not user.is_active:
                flash('Account is disabled.', 'error')
                return redirect(url_for('auth.login'))
            
            # Enable persistent login (user stays logged in after browser restart)
            session.permanent = True
            
            # Create login session cookie
            login_user(user, remember=True)
            flash(f'Welcome back, {user.first_name or user.username}!', 'success')
            
            # Respect ?next=... for protected-page redirects
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('hub.hub_home'))
        else:
            flash('Invalid username/email or password.', 'error')
    
    return render_template('auth/login.html')


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    User logout endpoint.
    
    Why POST only?
    - Prevents accidental logout via URL
    - Requires form submission (CSRF token required)
    - More secure than GET
    """
    # Clear authenticated session
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))


@bp.route('/profile/<int:user_id>')
@login_required
def view_profile(user_id):
    """
    View user profile.
    
    Shows user's name, bio, profile picture, teams they're in.
    """
    # Fetch user or return 404
    user = User.query.get_or_404(user_id)
    # Show teams this user belongs to
    teams = user.teams
    
    return render_template('auth/profile.html', user=user, teams=teams)


@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """
    Edit current user's profile.
    
    Can update:
    - First name, last name
    - Bio
    - Profile picture (TODO: file upload)
    """
    
    if request.method == 'POST':
        # Update editable profile fields for current user
        current_user.first_name = request.form.get('first_name', '').strip()
        current_user.last_name = request.form.get('last_name', '').strip()
        current_user.bio = request.form.get('bio', '').strip()
        
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('auth.view_profile', user_id=current_user.id))
    
    # GET: render edit form prefilled with current values
    return render_template('auth/edit_profile.html', user=current_user)


@bp.route('/api/user-search')
@login_required
def api_search_users():
    """
    API endpoint to search for users.
    
    Used for adding team members, direct messaging, etc.
    Returns JSON list of matching users.
    """
    # Read search string from query param
    query = request.args.get('q', '').strip()
    
    # Prevent broad/expensive searches for tiny input
    if len(query) < 2:
        return jsonify([])
    
    # Search by username, first name, or last name (case-insensitive)
    users = User.query.filter(
        (User.username.ilike(f'%{query}%')) | 
        (User.first_name.ilike(f'%{query}%')) |
        (User.last_name.ilike(f'%{query}%'))
    ).filter(User.id != current_user.id).limit(10).all()
    
    # Return minimal payload for UI autocomplete components
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'name': f"{u.first_name} {u.last_name}" if u.first_name else u.username
    } for u in users])
