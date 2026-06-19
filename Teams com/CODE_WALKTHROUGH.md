# Code Walkthrough - Teacher Explanation

**This document walks through actual code with explanations of WHAT happens and WHY**

---

## 1. Entry Point: app.py

```python
# This is where the whole application starts!
# Think of it like the "main" function in Java or C++

from dotenv import load_dotenv  # Load settings from .env file
from app import create_app  # Import the app factory

load_dotenv()  # Read .env file (SECRET_KEY, DATABASE_URL, etc)

app = create_app()  # Create Flask app with all configuration

if __name__ == '__main__':
    # Only run if this file is executed directly (not imported)
    # This prevents the app running if another file imports this
    
    from app import socketio  # Get the SocketIO object for real-time features
    
    # Start the server with SocketIO support
    # SocketIO is needed for video call signaling (WebRTC negotiation)
    socketio.run(
        app,
        host='0.0.0.0',  # Listen on all network interfaces
        port=5000,        # Use port 5000 (http://localhost:5000)
        debug=True        # Auto-reload when code changes
    )
```

**What happens when you run: `python app.py`**
1. `.env` file loaded (contains SECRET_KEY, DATABASE settings)
2. Flask app created with all extensions initialized
3. Database tables created if they don't exist
4. Default roles created (admin, member)
5. All blueprints (routes) registered
6. Server starts listening on port 5000
7. You can now open `http://localhost:5000` in browser

---

## 2. Configuration: config.py

```python
# Think of config.py as the "settings" file for the app
# It controls behavior without needing to change code

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ===== SECURITY SETTINGS =====
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    # ^^ This SECRET_KEY is like a password for the app
    # Used to sign session cookies and CSRF tokens
    # If someone gets this key, they can forge sessions!
    # NEVER commit to Git - always use .env file
    
    # ===== DATABASE SETTINGS =====
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'sqlite:///team_collab.db'
    )
    # ^^ Where's the database?
    # "sqlite:///team_collab.db" means:
    #   - sqlite = use SQLite
    #   - :/// = local file
    #   - team_collab.db = filename
    # This creates a single file containing ALL data
    # Perfect for dev/learning! (PostgreSQL for production)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # ^^ Tell SQLAlchemy to NOT warn about model changes
    # Cleaner output, less noise
    
    # ===== SESSION SETTINGS =====
    PERMANENT_SESSION_LIFETIME = 24 * 60 * 60  # 24 hours in seconds
    # ^^ How long until user is logged out?
    # 24 hours means: if user doesn't refresh, they stay logged in
    # After 24 hours, they have to login again
    # Security vs convenience tradeoff
    
    SESSION_COOKIE_HTTPONLY = True
    # ^^ This is REALLY important!
    # Prevents JavaScript from accessing session cookie
    # Blocks XSS (Cross-Site Scripting) attacks
    # Attacker can't steal session with JavaScript
    
    SESSION_COOKIE_SAMESITE = 'Lax'
    # ^^ Prevents CSRF (Cross-Site Request Forgery)
    # Cookie only sent to our site, not to other sites
    # Blocks fake forms from tricking users
    
    # ===== FILE UPLOAD SETTINGS =====
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB maximum
    # ^^ Don't allow files larger than 16MB
    # Prevents user from crashing server with huge files
    
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    # ^^ Where to save uploaded files?
    # This creates: /project/uploads/ folder
    
    ALLOWED_EXTENSIONS = {
        'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif',  # Documents & images
        'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',  # Office files
        'zip'  # Archives
    }
    # ^^ Whitelist of allowed file types
    # Blocks: .exe (viruses), .js (malicious scripts), etc
    # WHY? User could upload virus!
    # This whitelist protects the system
    
    # ===== PAGINATION =====
    ITEMS_PER_PAGE = 20
    # ^^ Show 20 items per page in lists
    # Why not show all? 
    # - Database is faster (query fewer rows)
    # - Page loads faster
    # - Less confusing for user (not 1000 items to scroll)
    
    # ===== LIMITS =====
    MAX_MESSAGE_LENGTH = 5000
    MAX_TEAM_NAME_LENGTH = 100
    MAX_USERNAME_LENGTH = 50
    # ^^ All have limits to prevent database bloat


class DevelopmentConfig(Config):
    # Inherits everything from Config, but:
    DEBUG = True    # Auto-reload on code changes
    TESTING = False  # Not in test mode


class ProductionConfig(Config):
    # For live server:
    DEBUG = False  # Don't expose errors to users
    SESSION_COOKIE_SECURE = True  # Only send over HTTPS (not HTTP)
    # This forces HTTPS, preventing session theft


# Select config based on environment variable
config = {
    'development': DevelopmentConfig,  # Local machine
    'testing': TestingConfig,          # Automated tests
    'production': ProductionConfig,    # Live server
}
```

**Key Takeaway:** Config keeps all settings in one place. Change DATABASE_URL in .env = changes database. No need to edit code!

---

## 3. App Factory: app/__init__.py

```python
# This is the "brain" of the app - it sets up Flask and all extensions

from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO
from config import get_config
from app.models import db, User, Role

# Create SocketIO before app (needed for initialization)
socketio = SocketIO(cors_allowed_origins="*")
# ^^ SocketIO enables real-time communication
# cors_allowed_origins="*" means allow requests from any origin
# (In production, restrict this!)


def create_app():
    # This function creates and sets up the Flask app
    # Why a function instead of creating app directly?
    # - Can create multiple app instances (one for tests, one for dev, one for prod)
    # - Cleaner testing
    # - Professional Flask pattern
    
    # ===== CREATE APP =====
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), '../templates'),
        static_folder=os.path.join(os.path.dirname(__file__), '../static')
    )
    # ^^ Create Flask app instance
    # Tell Flask where HTML templates are: /templates/
    # Tell Flask where CSS/JS are: /static/
    
    # ===== LOAD CONFIG =====
    config = get_config()  # Read from environment
    app.config.from_object(config)
    # ^^ Apply all settings from config.py
    # Now app knows: database location, secret key, limits, etc
    
    # ===== INITIALIZE EXTENSIONS =====
    db.init_app(app)  # Connect SQLAlchemy to this app
    # ^^ Before this, db didn't know which Flask app to use
    # After this, db knows
    
    # Setup Flask-Login (user authentication)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Go to login page if not authenticated
    login_manager.login_message = 'Please log in to access this page.'
    # ^^ If user tries to access protected page without logging in,
    # Flask-Login redirects to login page with this message
    
    @login_manager.user_loader
    def load_user(user_id):
        # This function is called automatically by Flask-Login
        # When user has a session, this loads their User object from database
        # IMPORTANT: Happens on EVERY request
        # If user deleted, returns None (logs them out)
        return User.query.get(int(user_id))
    
    # ===== CREATE DATABASE =====
    with app.app_context():  # Need app context to access database
        # Check which tables exist
        inspector = sa_inspect(db.engine)
        existing = inspector.get_table_names()
        
        # Create any missing tables
        for table in db.metadata.sorted_tables:
            if table.name not in existing:
                table.create(bind=db.engine)
        # ^^ This lets us add new models without manually running migrations!
        # Just define model → Flask creates table automatically
        
        # Handle schema changes (adding new columns to existing tables)
        with db.engine.connect() as conn:
            cols = [c['name'] for c in inspector.get_columns('calls')]
            if 'summary' not in cols:
                # If 'summary' column doesn't exist, add it
                conn.execute(db.text('ALTER TABLE calls ADD COLUMN summary TEXT'))
                conn.commit()
            # ^^ This is a LIGHTWEIGHT migration
            # For production, use Alembic (Flask-Migrate)
        
        # Create default roles if they don't exist
        if Role.query.count() == 0:
            # Only create if no roles exist yet
            admin_role = Role(
                name='admin',
                description='Team administrator with full permissions'
            )
            member_role = Role(
                name='member',
                description='Regular team member'
            )
            db.session.add(admin_role)
            db.session.add(member_role)
            db.session.commit()
            print("✓ Default roles created: Admin, Member")
    
    # Create uploads folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # ^^ Before we can save files, we need a folder
    # exist_ok=True means: don't error if folder already exists
    
    # ===== REGISTER BLUEPRINTS (Routes) =====
    # Blueprints are like modules/packages of routes
    # Each blueprint handles one feature:
    from app.routes import auth_routes, team_routes, message_routes, ...
    
    app.register_blueprint(auth_routes.bp)      # /auth/* routes
    app.register_blueprint(team_routes.bp)      # /teams/* routes
    app.register_blueprint(message_routes.bp)   # /messages/* routes
    app.register_blueprint(file_routes.bp)      # /files/* routes
    app.register_blueprint(task_routes.bp)      # /tasks/* routes
    app.register_blueprint(call_routes.call_routes)  # /calls/* routes
    # ^^ When user visits /auth/login, Flask checks auth_routes
    # When user visits /teams/1, Flask checks team_routes
    # etc
    
    # ===== INITIALIZE SOCKETIO =====
    socketio.init_app(app, async_mode='threading')
    # ^^ Connect SocketIO to this Flask app
    # async_mode='threading' = use threads for real-time events
    # (vs 'gevent' which needs gevent server)
    
    # Register WebRTC signaling handlers
    from app.socket_events import register_socket_events
    register_socket_events(socketio)
    # ^^ These handle: offer, answer, ice-candidate (WebRTC events)
    
    # ===== ERROR HANDLERS =====
    @app.errorhandler(404)
    def not_found(error):
        # User tried to visit page that doesn't exist
        return {'error': 'Resource not found'}, 404
        # ^^ Return JSON, not HTML (API-style error)
    
    @app.errorhandler(500)
    def internal_error(error):
        # Server error (bug in our code)
        db.session.rollback()  # IMPORTANT: Cancel any pending database changes
        # ^^ If database transaction was in progress, undo it
        # Prevents corrupting data if error happens mid-transaction
        return {'error': 'Internal server error'}, 500
    
    return app  # Return the configured app
```

**What happens after `create_app()` returns:**
1. Flask knows: where templates are, where database is, what secret key to use
2. Database ready: all tables exist
3. Routes registered: all /auth/, /teams/, etc routes available
4. SocketIO ready: can handle WebSocket connections
5. App ready to receive requests!

---

## 4. Authentication Flow: Detailed Example

### Registration (Sign Up)

**User's browser:**
```html
<!-- User sees this form -->
<form action="/auth/register" method="POST">
    <input name="username" placeholder="Choose username">
    <input name="email" type="email">
    <input name="password" type="password">
    <input name="password_confirm" type="password">
    <button type="submit">Create Account</button>
</form>
```

**Backend processes POST request:**

```python
@bp.route('/auth/register', methods=['POST'])
def register():
    # Extract form data
    username = request.form.get('username')  # Get 'username' field
    password = request.form.get('password')
    
    # ===== VALIDATE INPUT =====
    errors = []
    
    if len(username) < 3:
        errors.append('Username too short')
        # ^^ Check BEFORE database query
        # Save database work if validation fails
    
    # Check if username already taken
    if User.query.filter_by(username=username).first():
        errors.append('Username taken')
        # ^^ Query database: "Is there a user with this username?"
        # If yes (.first() returns user), add error
    
    if errors:
        # Tell user about errors
        for err in errors:
            flash(err, 'error')  # Show error message
        return redirect(url_for('auth.register'))  # Reload form
    
    # ===== CREATE USER =====
    user = User(
        username=username,
        email=email
    )
    user.set_password(password)
    # ^^ This hashes the password using PBKDF2
    # Password is now: $pbkdf2-sha256$29000$xxx...xxx (not plaintext!)
    # Even we can't read it back
    
    # Save to database
    db.session.add(user)      # Mark as "to be inserted"
    db.session.commit()       # Actually insert into database
    # ^^ Transaction: if error happens between add/commit, rollback automatically
    # Database always stays consistent
    
    flash('Account created! Please log in.', 'success')
    return redirect(url_for('auth.login'))  # Go to login page
```

### Login (Sign In)

**Backend:**

```python
@bp.route('/auth/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Find user by username
    user = User.query.filter_by(username=username).first()
    
    if not user:
        # No user with that username
        flash('Username not found', 'error')
        return redirect(url_for('auth.login'))
    
    # ===== CHECK PASSWORD =====
    if not user.check_password(password):
        # Password doesn't match
        flash('Incorrect password', 'error')
        return redirect(url_for('auth.login'))
    
    # Password correct! Create session
    login_user(user, remember=True)
    # ^^ This creates a session cookie
    # The cookie says: "This browser belongs to user_id=42"
    # Browser stores cookie and sends it with every request
    # Server verifies cookie is valid (hasn't been tampered with)
    
    flash(f'Welcome back, {user.username}!', 'success')
    return redirect(url_for('dashboard.index'))  # Go to dashboard
```

**Why separate username and password checks?**
- For security! (timing attack prevention)
- If we say "username not found", attacker knows which usernames exist
- Better to check both then show generic "credentials incorrect"

---

## 5. Database Query Examples

### Example 1: Find all messages in a channel

```python
# Goal: Show all messages in #general channel

channel_id = 1  # #general is ID 1

# Get the channel
channel = Channel.query.filter_by(id=channel_id).first()

if not channel:
    flash('Channel not found', 'error')
    return redirect(...)

# Get all messages in this channel (newest first)
messages = Message.query.filter_by(channel_id=channel_id)\
    .order_by(Message.created_at.desc())\
    .limit(50)  # Only get 50 most recent (pagination)
    
# ^^ This generates SQL like:
# SELECT * FROM messages 
# WHERE channel_id = 1 
# ORDER BY created_at DESC 
# LIMIT 50
```

### Example 2: Check if user is in team

```python
# Goal: Make sure user can see this team

user_id = current_user.id
team_id = 1

# Check if user is member of team
is_member = TeamMember.query.filter_by(
    user_id=user_id,
    team_id=team_id
).first() is not None

if not is_member:
    flash('You are not a member of this team', 'error')
    return redirect(url_for('dashboard.index'))

# User IS a member, proceed
team = Team.query.get(team_id)
return render_template('teams/view.html', team=team)
```

### Example 3: Create a notification

```python
# Goal: Notify user that someone mentioned them

mentioned_user_id = 5  # User who was mentioned
mentioner_username = 'alice'
message_id = 42

notification = Notification(
    user_id=mentioned_user_id,
    type='mention',
    title=f'{mentioner_username} mentioned you',
    message='in #general: "Hey @Bob, check this out"',
    related_id=message_id  # Link to the message
)

db.session.add(notification)
db.session.commit()

# User #5 now sees a notification
# Clicking it takes them to message #42
```

---

## 6. Request-Response Example: Sending a Message

**User's perspective:**
1. Opens chat
2. Types "Hello team!"
3. Clicks Send

**Behind the scenes:**

```
Browser (Client)
├─ JavaScript detects form submission
├─ Prevents default (no page reload)
├─ Sends AJAX POST request:
│  POST /messages/channel/1/send
│  Body: { "content": "Hello team!" }
└─ Waits for response...
        ↓
Server (Backend)
├─ Flask receives POST request
├─ Calls route handler:
│
│  @bp.route('/messages/channel/<int:channel_id>/send', methods=['POST'])
│  @login_required  # ← Check: Is user logged in?
│  def send_message(channel_id):
│
├─ Checks: Is channel_id valid?
├─ Checks: Is current_user in this team?
├─ Gets message content from request
├─ Validates: Not empty? Not too long?
├─ Creates Message object:
│  msg = Message(
│      content="Hello team!",
│      channel_id=1,
│      sender_id=current_user.id,
│      created_at=datetime.utcnow()
│  )
├─ Inserts into database:
│  db.session.add(msg)
│  db.session.commit()
├─ Checks for mentions: Does message contain @username?
├─ If yes: Create Notification for mentioned user
├─ Returns JSON response:
│  { "success": true, "message_id": 42 }
└─ Sends to browser...
        ↓
Browser (Client)
├─ Receives successful response
├─ Creates HTML for new message:
│  <div class="message">
│    <strong>your_username</strong>
│    <p>Hello team!</p>
│    <span>12:34 PM</span>
│  </div>
├─ Inserts at bottom of message list
├─ Scrolls to show new message
├─ Clears text input box
└─ User sees message appear instantly ✓
```

---

## 7. Video Call Flow: Group Calling

```python
# User clicks "Start Group Call" in team page

@bp.route('/calls/group/<int:team_id>/initiate', methods=['POST'])
@login_required
def initiate_group_call(team_id):
    
    # ===== VALIDATE TEAM =====
    team = Team.query.filter_by(id=team_id).first()
    if not team:
        return {"error": "Team not found"}, 404
    
    # ===== CHECK AUTHORIZATION =====
    # Is current user in this team?
    if current_user not in team.members:
        return {"error": "You are not in this team"}, 403
    
    # ===== GET PARTICIPANTS =====
    # Get all team members except caller
    participants = [
        member for member in team.members 
        if member.id != current_user.id
    ]
    
    # Check we have at least 1 other person
    if not participants:
        return {"error": "No other team members to call"}, 400
    
    # Check limit (max 8 people)
    if len(participants) > 7:  # 7 + caller = 8
        return {
            "error": "Team too large for group call (max 8 people)"
        }, 400
    
    # ===== CREATE CALL =====
    call_token = str(uuid.uuid4())  # Unique ID for this call session
    
    call = Call(
        caller_id=current_user.id,
        call_type='group',           # Mark as group (not one-to-one)
        team_id=team_id,             # Which team?
        status='pending',            # Waiting for people to join
        call_token=call_token
    )
    
    db.session.add(call)
    db.session.commit()
    
    # Get call ID from database (auto-generated)
    call_id = call.id
    
    # ===== ADD PARTICIPANTS =====
    # Create CallParticipant records for everyone
    for participant in participants:
        cp = CallParticipant(
            call_id=call_id,
            user_id=participant.id,
            joined_at=datetime.utcnow()
            # ^^ left_at is NULL because they haven't left yet
        )
        db.session.add(cp)
    
    db.session.commit()
    
    # ===== SEND NOTIFICATIONS =====
    # Tell all participants: "You're being called!"
    for participant in participants:
        notif = Notification(
            user_id=participant.id,
            type='group_call',
            title=f"Group call in {team.name}",
            message=f"{current_user.username} started a group call",
            related_id=call_id
        )
        db.session.add(notif)
    
    db.session.commit()
    
    # ===== RETURN RESPONSE =====
    return {
        "success": True,
        "call_token": call_token,
        "team_name": team.name,
        "participants": [p.username for p in participants]
    }

# Browser receives response, redirects to:
# /calls/room/17be809a-fd09-4f44-9af0-9996f3c5836f

# This page shows:
# - Video grid layout (multiple video boxes)
# - Status: "Group Call - Team Name (3 participants)"
# - Everyone in the call gets WebRTC peer connection setup
```

---

## 8. Security Check Example: Authorization

```python
@bp.route('/teams/<int:team_id>/settings', methods=['POST'])
@login_required  # ← Check 1: User logged in?
def update_team_settings(team_id):
    
    # ===== GET TEAM =====
    team = Team.query.get(team_id)
    if not team:
        flash('Team not found', 'error')
        return redirect(...)
    
    # ===== CHECK PERMISSION =====
    # ← Check 2: Is user the owner (admin)?
    if team.owner_id != current_user.id:
        flash('Only team owner can change settings', 'error')
        return redirect(url_for('teams.view', team_id=team_id))
    
    # ===== VALIDATE INPUT =====
    # ← Check 3: Is input valid?
    new_name = request.form.get('name', '').strip()
    
    if len(new_name) < 1 or len(new_name) > 100:
        flash('Team name must be 1-100 characters', 'error')
        return redirect(...)
    
    # ===== UPDATE =====
    team.name = new_name
    db.session.commit()
    # ^^ Only owner can reach here!
    # Everyone else was rejected earlier
    
    flash('Team settings updated!', 'success')
    return redirect(...)
```

**Why 3 checks?**
1. **Authentication**: Is this even a real user?
2. **Authorization**: Does this user have permission?
3. **Validation**: Is the data valid?

All three are needed for security!

---

## 9. Database Transaction Example

```python
# Scenario: Creating a task and notifying the assignee

# ===== START TRANSACTION =====
# Everything between db.session.add() and db.session.commit() is ONE transaction

try:
    # Create task
    task = Task(
        title="Submit Project",
        team_id=1,
        assigned_to_id=5,  # User #5
        created_by_id=current_user.id
    )
    db.session.add(task)
    
    # Create notification
    notification = Notification(
        user_id=5,  # Same user
        type='task_assigned',
        title="New task assigned to you",
        related_id=task.id  # Link to task
    )
    db.session.add(notification)
    
    # ===== COMMIT TRANSACTION =====
    # This writes BOTH to database
    # Either both succeed, or both fail (atomic!)
    db.session.commit()
    
except Exception as e:
    # If anything goes wrong (database error, constraint violation, etc)
    db.session.rollback()  # Undo all changes
    # ^^ Now database is back to how it was
    # Both task AND notification are NOT created
    # Database stays consistent!
    
    flash(f'Error creating task: {str(e)}', 'error')
    return redirect(...)

# Success! Both task and notification in database
flash('Task created!', 'success')
```

**Key concept: ACID Transactions**
- **Atomic**: All or nothing (both succeed or both fail)
- **Consistent**: Database rules always followed
- **Isolated**: Multiple users can't interfere
- **Durable**: Once committed, stays committed (no data loss)

---

## 10. Common Security Mistakes (and how we avoid them)

### ❌ MISTAKE 1: Storing passwords in plaintext

```python
# WRONG! NEVER DO THIS:
user.password = password  # ← Plaintext in database!
db.session.commit()

# If database is stolen, everyone's password is compromised!
```

### ✅ CORRECT: Hash passwords

```python
# RIGHT! Use this:
user.set_password(password)  # Hashes with PBKDF2
# Database now contains: $pbkdf2-sha256$29000$abc123...xyz789
# If database stolen, passwords are useless (one-way hash)
```

### ❌ MISTAKE 2: No authorization check

```python
# WRONG! This lets anyone edit any team:
team = Team.query.get(request.args.get('team_id'))
team.name = "Hacked!"
db.session.commit()  # ← No check if user is owner!
```

### ✅ CORRECT: Check authorization first

```python
# RIGHT! Verify permission:
team = Team.query.get(request.args.get('team_id'))

if team.owner_id != current_user.id:
    return {"error": "Not authorized"}, 403
    # ← Only owner can edit

team.name = "Hacked!"  # Now OK
db.session.commit()
```

### ❌ MISTAKE 3: Trusting user input directly

```python
# WRONG! SQL Injection risk:
query = f"SELECT * FROM users WHERE username = '{username}'"
# If username = "admin' --", this becomes:
# SELECT * FROM users WHERE username = 'admin' --'
# Comment removes the closing quote, changes query!

result = db.engine.execute(query)  # ← Vulnerable!
```

### ✅ CORRECT: Use parameterized queries

```python
# RIGHT! SQLAlchemy handles it:
user = User.query.filter_by(username=username).first()
# Even if username = "admin' --", it's treated as literal data
# SQLAlchemy escapes special characters automatically
```

---

**End of Code Walkthrough**

*Use this to understand WHAT the code does and WHY. Reference it when explaining to your supervisor!*
