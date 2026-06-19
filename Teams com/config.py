"""
Configuration module for Team Collaboration Platform.

This file holds ALL the settings for the app:
- Where's the database?
- What's the SECRET_KEY?
- How big can files be?
- etc.

Why separate config file?
- Change settings without touching code
- Easy to have different settings for dev/testing/production
- Keeps secrets out of main code
"""

# Import os to read files and environment
import os
# Import dotenv to load .env file (contains SECRET_KEY and other secrets)
from dotenv import load_dotenv

# Read the .env file (this file has passwords, keys, etc)
load_dotenv()

# Resolve paths once so default database location is stable.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, 'instance', 'team_collab.db')
DEFAULT_DB_URI = f"sqlite:///{DEFAULT_DB_PATH.replace(os.sep, '/')}"


def _normalize_database_url(raw_db_url):
    """Return a stable absolute DB URL for sqlite file paths.

    Why: a relative URL like sqlite:///team_collab.db depends on the terminal
    working directory, which can make the app appear to "lose" data between runs.
    """
    if not isinstance(raw_db_url, str) or not raw_db_url.strip():
        return DEFAULT_DB_URI

    db_url = raw_db_url.strip()

    # Keep non-sqlite URLs unchanged.
    if not db_url.startswith('sqlite:///'):
        return db_url

    # Keep in-memory sqlite unchanged.
    if db_url == 'sqlite:///:memory:':
        return db_url

    sqlite_target = db_url.replace('sqlite:///', '', 1)
    normalized_target = sqlite_target.replace('\\', '/').strip()

    # Already absolute (Windows drive path or Unix absolute path).
    if os.path.isabs(sqlite_target):
        abs_path = sqlite_target
    else:
        # For relative sqlite targets, anchor inside an instance directory.
        # Prefer existing files first to avoid splitting data across locations.
        filename = os.path.basename(normalized_target) or 'team_collab.db'
        candidates = [
            os.path.join(BASE_DIR, 'instance', filename),
            os.path.join(PROJECT_ROOT, 'instance', filename)
        ]

        existing = next((path for path in candidates if os.path.exists(path)), None)
        abs_path = existing or candidates[0]

    return f"sqlite:///{abs_path.replace(os.sep, '/')}"


class Config:
    """Base configuration - settings used by ALL environments (dev, test, prod)"""
    
    # ===== SECURITY =====
    # SECRET_KEY is like a password for the app (used to sign session cookies)
    # Read from .env file (never put in code!)
    # If no .env file: use default (only for development!)
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # ===== DATABASE =====
    # Where does the database live?
    # sqlite:///team_collab.db means: SQLite file named team_collab.db
    # Read from .env file if it exists, otherwise use default
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        DEFAULT_DB_URI
    )
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(SQLALCHEMY_DATABASE_URI)
    # Don't warn about modifications to models
    # (cleaner output when running)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ===== SESSION SETTINGS (login cookies) =====
    # How long does a user stay logged in?
    # 24 * 60 * 60 = 24 hours (in seconds)
    PERMANENT_SESSION_LIFETIME = 24 * 60 * 60
    
    # Send cookie over HTTPS only? (False for dev, True for production)
    # HTTPS is encrypted, HTTP is not
    SESSION_COOKIE_SECURE = False
    
    # Can JavaScript read the session cookie?
    # True = JavaScript CAN'T read it (more secure!)
    # Blocks XSS attacks from stealing sessions
    SESSION_COOKIE_HTTPONLY = True
    
    # Only send cookie to OUR website, not other sites
    # Prevents CSRF (Cross-Site Request Forgery) attacks
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # ===== FILE UPLOAD SETTINGS =====
    # What's the maximum file size users can upload?
    # 16 * 1024 * 1024 = 16MB (in bytes)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # Where do we save uploaded files?
    # os.path.dirname(__file__) = current file's folder
    # So: /project/uploads/ folder
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    
    # Which file types are allowed?
    # Blocks dangerous files like .exe, .js, etc
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'zip'}
    
    # ===== PAGINATION =====
    # How many items per page when showing lists?
    # (messages, files, notifications, etc)
    ITEMS_PER_PAGE = 20
    
    # ===== APPLICATION LIMITS =====
    # Name of the app (used in templates, emails, etc)
    APP_NAME = 'Team Collaboration Platform'
    
    # Maximum message length (5000 characters)
    # Prevents users from sending huge messages
    MAX_MESSAGE_LENGTH = 5000
    
    # Maximum team name length (100 characters)
    MAX_TEAM_NAME_LENGTH = 100
    
    # Maximum username length (50 characters)
    MAX_USERNAME_LENGTH = 50


class DevelopmentConfig(Config):
    """Development configuration (local machine)"""
    # Debug mode ON = auto-reload when code changes, detailed errors
    DEBUG = True
    # Not in testing mode
    TESTING = False


class TestingConfig(Config):
    """Testing configuration (automated tests)"""
    # We're in testing mode
    TESTING = True
    # Use in-memory database for tests (faster, no files)
    # ':memory:' means database only exists while test runs
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    # Don't check CSRF tokens in tests (they're annoying to setup)
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration (live server)"""
    # Debug mode OFF = faster, errors don't show details
    DEBUG = False
    # Not in testing mode
    TESTING = False
    # Only send cookies over HTTPS (encrypted)
    # Prevents attackers from stealing sessions
    SESSION_COOKIE_SECURE = True
    

# Dictionary mapping environment names to config classes
# This is how we decide which settings to use
config = {
    'development': DevelopmentConfig,  # Local machine: debug ON
    'testing': TestingConfig,          # Automated tests: in-memory database
    'production': ProductionConfig,    # Live server: debug OFF, secure cookies
    'default': DevelopmentConfig       # If not specified, use development
}

def get_config():
    """
    Get the right configuration based on FLASK_ENV environment variable.
    
    This function reads FLASK_ENV from .env file:
    - If FLASK_ENV=development: returns DevelopmentConfig
    - If FLASK_ENV=production: returns ProductionConfig
    - If FLASK_ENV=testing: returns TestingConfig
    - If not set: defaults to DevelopmentConfig
    """
    # Read the FLASK_ENV variable (defaults to 'development' if not found)
    env = os.getenv('FLASK_ENV', 'development')
    # Look up the environment in the config dictionary
    # Return the config class for that environment
    # If environment not found, use default
    return config.get(env, config['default'])
