"""
Flask application factory and initialization.

This file sets up the entire Flask app:
- Creates the Flask app instance
- Initializes database
- Sets up login system
- Registers all routes (blueprints)
- Creates default roles

Why an "app factory" function instead of creating app directly?
- Can create multiple app instances (one for dev, one for tests, etc)
- Makes testing easier
- Professional Flask pattern
"""

# Import Flask - the web framework
from flask import Flask, jsonify
# Import LoginManager - handles user login/sessions
from flask_login import LoginManager
# Import SocketIO - enables real-time features (video calls, WebRTC signaling)
from flask_socketio import SocketIO
# Import get_config - reads settings from config.py
from config import get_config
# Import database and models
from app.models import db, User, Role
# Import os - for file/folder operations
import os


# Create SocketIO object (needed BEFORE creating the app)
# This enables real-time communication for video calls
socketio = SocketIO(
    # Allow requests from any website
    # (In production, restrict this to your domain)
    cors_allowed_origins="*"
)


def create_app():
    """
    The app factory function - creates and sets up the Flask app.
    
    This function does everything needed to make the app work:
    1. Creates Flask app
    2. Loads settings from config.py
    3. Sets up database (SQLAlchemy)
    4. Sets up login system (Flask-Login)
    5. Creates database tables
    6. Creates default admin/member roles
    7. Registers all routes (blueprints)
    8. Sets up SocketIO for real-time features
    9. Sets up error handlers
    
    Returns:
        Flask app instance (ready to use!)
    """
    
    # ===== CREATE FLASK APP =====
    # Flask(__name__) creates the app
    # template_folder = where HTML files live
    # static_folder = where CSS/JS files live
    app = Flask(
        __name__,  # App name
        template_folder=os.path.join(os.path.dirname(__file__), '../templates'),  # Find templates folder
        static_folder=os.path.join(os.path.dirname(__file__), '../static')  # Find static folder
    )
    
    # ===== LOAD CONFIGURATION =====
    # Get config object based on environment (dev/test/prod)
    config = get_config()
    # Apply settings to the app
    # Now app knows: database location, secret key, limits, etc.
    app.config.from_object(config)

    # Ensure SQLite target directory exists for integrated instance-based DB path.
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if db_uri.startswith('sqlite:///') and db_uri != 'sqlite:///:memory:':
        sqlite_path = db_uri.replace('sqlite:///', '', 1)
        sqlite_dir = os.path.dirname(sqlite_path)
        if sqlite_dir:
            os.makedirs(sqlite_dir, exist_ok=True)
    
    # ===== SETUP DATABASE =====
    # Initialize SQLAlchemy with this app
    # Now database knows which Flask app to use
    db.init_app(app)
    
    # ===== SETUP LOGIN SYSTEM =====
    # Create the login manager
    login_manager = LoginManager()
    # Connect it to this app
    login_manager.init_app(app)
    
    # Where to redirect if user tries to access protected page without logging in?
    # Redirect to 'auth.login' route
    login_manager.login_view = 'auth.login'
    # Message to show when redirecting to login
    login_manager.login_message = 'Please log in to access this page.'
    # Type of message (for CSS styling)
    login_manager.login_message_category = 'info'
    
    # This function loads a user from database by ID
    # Called automatically by Flask-Login on every request
    # Checks if user still exists, if not logs them out
    @login_manager.user_loader
    def load_user(user_id):
        """Load user from database by their ID."""
        # Query database: find user with this ID
        return User.query.get(int(user_id))

    # ===== SETUP DATABASE TABLES =====
    # We need an "app context" to access database
    with app.app_context():
        # Import inspect tool to examine database
        from sqlalchemy import inspect as sa_inspect
        
        # Get database engine and inspector
        engine = db.engine
        inspector = sa_inspect(engine)
        
        # Get list of existing table names
        existing = inspector.get_table_names()
        
        # Loop through all model tables
        for table in db.metadata.sorted_tables:
            # If this table doesn't exist yet, create it
            if table.name not in existing:
                table.create(bind=engine)
        
        # Handle adding new columns to existing tables
        # (lightweight migration, not a full migration system)
        with engine.connect() as _conn:
            # Get list of all column names in 'calls' table
            cols = [c['name'] for c in inspector.get_columns('calls')]
            # Does the 'summary' column exist?
            if 'summary' not in cols:
                # If not, add it (for call summaries feature)
                _conn.execute(db.text('ALTER TABLE calls ADD COLUMN summary TEXT'))
                # Save the change
                _conn.commit()
        
        # Create any missing default roles (idempotent).
        required_roles = {
            'admin': 'Team administrator with full permissions',
            'member': 'Regular team member'
        }

        created_any_role = False
        for role_name, description in required_roles.items():
            if not Role.query.filter_by(name=role_name).first():
                db.session.add(Role(name=role_name, description=description))
                created_any_role = True

        if created_any_role:
            db.session.commit()
            print("✓ Default roles verified: Admin, Member")
    
    # ===== CREATE UPLOADS FOLDER =====
    # Create /uploads folder if it doesn't exist
    # exist_ok=True means don't error if folder already exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # ===== REGISTER BLUEPRINTS (Routes) =====
    # Import all route modules
    from app.routes import (
        hub_routes,          # Main Teacher Feature Hub routes (/ and static feature pages)
        auth_routes,         # /auth/* routes (login, register, profile)
        team_routes,         # /teams/* routes (create team, join, settings)
        message_routes,      # /messages/* routes (send messages, etc)
        face_routes,         # /api/face-students routes (face attendance persistence)
        file_routes,         # /files/* routes (upload, download)
        task_routes,         # /tasks/* routes (create tasks, assign, etc)
        dashboard_routes,    # /dashboard routes (home page)
        call_routes          # /calls/* routes (video calling)
    )
    
    # Register each blueprint so its routes are available
    app.register_blueprint(hub_routes.bp)           # Main hub routes and Team Com entry path
    app.register_blueprint(auth_routes.bp)          # All /auth/* routes
    app.register_blueprint(team_routes.bp)          # All /teams/* routes
    app.register_blueprint(message_routes.bp)       # All /messages/* routes
    app.register_blueprint(face_routes.bp)          # All /api/face-students routes
    app.register_blueprint(file_routes.bp)          # All /files/* routes
    app.register_blueprint(task_routes.bp)          # All /tasks/* routes
    app.register_blueprint(dashboard_routes.bp)     # All /dashboard routes
    app.register_blueprint(call_routes.call_routes) # All /calls/* routes

    # ===== SETUP SOCKETIO =====
    # Initialize SocketIO for this app
    # async_mode='threading' = use threads (not gevent)
    # This enables real-time features like WebRTC signaling
    socketio.init_app(app, async_mode='threading')

    # Register WebSocket event handlers
    # These handle: 'offer', 'answer', 'ice-candidate' for video calls
    from app.socket_events import register_socket_events
    register_socket_events(socketio)
    
    # ===== ERROR HANDLERS =====
    @app.get('/healthz')
    def healthz():
        """Kubernetes/hosting health probe endpoint."""
        return jsonify({'status': 'ok'}), 200

    # What to do if user tries to access a page that doesn't exist?
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 (not found) errors."""
        # Return JSON error message
        # (could also return HTML template)
        return {'error': 'Resource not found'}, 404
    
    # What to do if there's a server error?
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 (internal server error)."""
        # IMPORTANT: Rollback database transaction if error happens
        # This prevents partial data from being saved
        db.session.rollback()
        # Return error message to user
        return {'error': 'Internal server error'}, 500
    
    # ===== RETURN THE APP =====
    # Return the configured app
    # It's now ready to use!
    return app
