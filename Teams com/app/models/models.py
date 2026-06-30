"""
Database models for Team Collaboration Platform.

This file defines all database tables as Python classes.
Each class = one database table.
Each class variable = one column in the table.

Why SQLAlchemy ORM?
- Write Python code instead of SQL
- Prevents SQL injection (automatic!)
- Easier to understand
- Type-safe
- Can easily test

Database Tables (10 total):
- User: Who is using the app?
- Team: What groups/teams exist?
- TeamMember: Who's in which team?
- Channel: Conversation channels
- Message: Messages in channels
- DirectMessage: Private 1-on-1 messages
- File: Uploaded files
- Task: Project tasks
- Notification: Event notifications
- Call: Video calls (1-to-1 or group)
- CallParticipant: Who's in a group call?
"""

# Import SQLAlchemy (database)
from flask_sqlalchemy import SQLAlchemy
# Import UserMixin (adds is_authenticated, is_active, etc for Flask-Login)
from flask_login import UserMixin
# Import password hashing tools
from werkzeug.security import generate_password_hash, check_password_hash
# Import datetime for timestamps
from datetime import datetime, timedelta
# Import json (not used much but available)
import json

# Create the SQLAlchemy database object
# This is used by all models to define columns and relationships
db = SQLAlchemy()


class User(UserMixin, db.Model):
    """
    User model - represents one person registered in the system.
    
    Example:
    - john_doe can login with username='john' and password='secret123'
    - john_doe can be in multiple teams
    - john_doe can send messages, tasks, etc.
    """
    
    # Table name in database
    __tablename__ = 'users'
    
    # ===== IDENTIFICATION =====
    # Unique ID for this user (primary key = unique identifier)
    # Auto-generated: first user gets id=1, second gets id=2, etc.
    id = db.Column(db.Integer, primary_key=True)
    
    # ===== LOGIN CREDENTIALS =====
    # Username for login (must be unique - no two users with same username!)
    # index=True means: create database index (faster searches)
    username = db.Column(
        db.String(50),      # Maximum 50 characters
        unique=True,        # No duplicates allowed
        nullable=False,     # MUST provide this (can't be empty)
        index=True          # Create index for faster queries
    )
    
    # Email address (must be unique)
    email = db.Column(
        db.String(120),     # Maximum 120 characters
        unique=True,        # No duplicates
        nullable=False,     # Required
        index=True          # Indexed
    )
    
    # Password stored as HASH (never plaintext!)
    # Example: password 'hello123' becomes: $pbkdf2-sha256$xxx$yyy
    # Even if database stolen, password is useless (one-way hash)
    password_hash = db.Column(
        db.String(255),     # Hashes are long (~100 chars)
        nullable=False      # Required
    )
    
    # ===== PROFILE INFORMATION =====
    # User's first name (optional)
    first_name = db.Column(db.String(100))
    
    # User's last name (optional)
    last_name = db.Column(db.String(100))
    
    # Path to user's profile picture file (e.g., '/uploads/john_profile.jpg')
    profile_picture = db.Column(db.String(255))
    
    # User's bio/description (e.g., "Computer Science student")
    # Text = can be very long
    bio = db.Column(db.Text)
    
    # ===== ACCOUNT STATUS =====
    # Is this account active? (True = active, False = deactivated)
    # Could implement soft deletes: set to False instead of actually deleting
    is_active = db.Column(
        db.Boolean,         # True or False
        default=True,       # New users are active by default
        nullable=False      # Must have a value
    )
    
    # ===== TIMESTAMPS =====
    # When was this account created?
    # default=datetime.utcnow = automatically set to current time when created
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,  # Auto-set on creation
        nullable=False
    )
    
    # When was this account last updated?
    # default and onupdate = automatically update timestamp on changes
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,   # Auto-set on creation
        onupdate=datetime.utcnow   # Auto-update on every change
    )
    
    # ===== RELATIONSHIPS =====
    # What teams is this user in?
    # secondary='team_members' = use TeamMember table to connect
    # This creates a many-to-many relationship
    # One user can be in many teams, one team can have many users
    teams = db.relationship(
        'Team',                           # Related model
        secondary='team_members',         # Join table
        back_populates='members',         # Two-way relationship
        overlaps='team_members,user,team'  # Shared join table path
    )
    
    # What messages did this user send?
    # One user can send many messages
    messages = db.relationship(
        'Message',
        back_populates='sender',
        foreign_keys='Message.sender_id'  # Which field in Message points to User?
    )
    
    # Direct messages sent by this user
    direct_messages_sent = db.relationship(
        'DirectMessage',
        back_populates='sender',
        foreign_keys='DirectMessage.sender_id'
    )
    
    # Direct messages received by this user
    direct_messages_received = db.relationship(
        'DirectMessage',
        back_populates='recipient',
        foreign_keys='DirectMessage.recipient_id'
    )
    # Tasks assigned to this user
    tasks = db.relationship(
        'Task',
        back_populates='assigned_to',
        foreign_keys='Task.assigned_to_id'
    )
    # Tasks created by this user
    tasks_created = db.relationship(
        'Task',
        back_populates='creator',
        foreign_keys='Task.created_by_id'
    )
    # Notifications for this user
    notifications = db.relationship('Notification', back_populates='user')
    # TeamMember records for this user
    team_members = db.relationship(
        'TeamMember',
        back_populates='user',
        overlaps='teams,members'
    )
    
    def set_password(self, password):
        """
        Hash the password and store it.
        
        This is called when user creates account or changes password.
        The password is converted to a hash (one-way encryption).
        Even if database is stolen, passwords are useless!
        
        Example:
        user = User(username='john')
        user.set_password('mySecret123')
        # Now password_hash = '$pbkdf2-sha256$29000$abc123...'
        # Original password is NOT stored anywhere!
        """
        # Use werkzeug to hash the password
        # This creates a one-way hash that can't be reversed
        # werkzeug.security uses PBKDF2 algorithm (industry standard)
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """
        Check if entered password matches stored hash.
        
        This is called during login.
        We hash the entered password and compare to stored hash.
        
        Example:
        user = User.query.filter_by(username='john').first()
        if user.check_password('mySecret123'):
            print('Login successful!')
        else:
            print('Wrong password!')
        
        Returns:
            True if password matches, False if not
        """
        # Hash the entered password and compare to stored hash
        # Returns True if they match, False if not
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        """
        String representation of User (for debugging).
        
        When you print(user), this determines what prints.
        Example: print(user) outputs: <User john>
        """
        return f'<User {self.username}>'


class Role(db.Model):
    """
    Role model - represents a permission level in a team.
    
    Example roles:
    - Admin: Can delete team, kick members, change settings
    - Member: Can see channels, post messages, that's it
    
    Why separate table for roles?
    - Keeps code organized
    - Easy to add new roles later (moderator, viewer, etc)
    - Prevents duplicating role info
    """
    
    __tablename__ = 'roles'
    
    # Unique ID for this role
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    
    # Role name (must be unique)
    # Examples: 'admin', 'member', 'moderator'
    name = db.Column(
        db.String(50),  # Maximum 50 characters
        unique=True,    # No two roles with same name!
        nullable=False  # Must provide a name
    )
    
    # Description of what this role can do
    # Example: 'Full access to team settings and members'
    description = db.Column(db.Text)
    
    # Which team members have this role?
    # One role can be assigned to many team members
    team_members = db.relationship('TeamMember', back_populates='role')
    
    def __repr__(self):
        """String representation for debugging."""
        return f'<Role {self.name}>'


class Team(db.Model):
    """
    Team model - represents a team/workspace.
    
    Example:
    - Team name: "Engineering Team"
    - Team code: "ENG2024"
    - Members: [alice, bob, charlie]
    - Channels: [#general, #announcements, #random]
    
    This is the main container for collaboration.
    Users join teams to access channels, share files, assign tasks, etc.
    """
    
    __tablename__ = 'teams'
    
    # ===== IDENTIFICATION =====
    # Unique ID for this team
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    
    # Team name (e.g., "Engineering Team")
    # Not unique - multiple teams can have similar names
    name = db.Column(
        db.String(100),     # Maximum 100 characters
        nullable=False      # Required
    )
    
    # Team description (e.g., "For engineering department")
    # Can be very long
    description = db.Column(db.Text)
    
    # ===== OWNERSHIP & PRIVACY =====
    # Who owns this team? (Foreign key to User)
    # If owner deletes account, this reference breaks
    owner_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),  # Points to User.id
        nullable=False              # Must have an owner
    )
    
    # Team invite code (e.g., "ENG2024")
    # Users can join by entering this code
    # Must be unique (no two teams with same code!)
    team_code = db.Column(
        db.String(10),  # 8-10 character code
        unique=True,    # No duplicates
        nullable=False, # Required
        index=True      # Indexed for fast searches
    )
    
    # Is this team publicly discoverable?
    # True = anyone can see it in team search
    # False = only with invite code
    is_public = db.Column(
        db.Boolean,
        default=False  # Private by default
    )
    
    # When was this team created?
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,  # Auto-set to now
        nullable=False
    )
    
    # When was this team last updated?
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,    # Auto-set to now
        onupdate=datetime.utcnow    # Auto-update on changes
    )
    
    # ===== RELATIONSHIPS =====
    # Who owns this team? (one-to-one with User)
    # Query result: team.owner returns the User object
    owner = db.relationship(
        'User',
        foreign_keys=[owner_id]  # Which field is the foreign key?
    )
    
    # Who is in this team? (many-to-many with User through TeamMember)
    # Query result: team.members returns list of User objects
    members = db.relationship(
        'User',
        secondary='team_members',  # Join table
        back_populates='teams',      # Two-way relationship
        overlaps='team_members,user,team'
    )
    
    # What channels are in this team? (one-to-many with Channel)
    # Query result: team.channels returns list of Channel objects
    # cascade='all, delete-orphan' = if team is deleted, delete its channels too
    channels = db.relationship(
        'Channel',
        back_populates='team',
        cascade='all, delete-orphan'  # Delete channels when team deleted
    )
    
    # What files are shared in this team?
    files = db.relationship(
        'File',
        back_populates='team',
        cascade='all, delete-orphan'  # Delete files when team deleted
    )
    
    # What tasks are in this team?
    tasks = db.relationship(
        'Task',
        back_populates='team',
        cascade='all, delete-orphan'  # Delete tasks when team deleted
    )
    
    # What team members are in this team? (join table records)
    team_members = db.relationship(
        'TeamMember',
        back_populates='team',
        cascade='all, delete-orphan',  # Delete team members when team deleted
        overlaps='members,teams'
    )
    
    def __repr__(self):
        """String representation for debugging."""
        return f'<Team {self.name}>'


class TeamMember(db.Model):
    """
    TeamMember model - join table linking Users to Teams with roles.
    
    Why a join table?
    - One user can be in many teams
    - One team can have many users
    - Need to track WHEN user joined
    - Need to track WHAT ROLE user has (admin vs member)
    
    Example:
    - alice joins Team A as admin
    - alice joins Team B as member
    - bob joins Team A as member
    - charlie joins Team A as admin
    
    This creates TeamMember records:
    - (Team A, alice, admin, joined 2024-01-01)
    - (Team B, alice, member, joined 2024-01-15)
    - (Team A, bob, member, joined 2024-01-10)
    - (Team A, charlie, admin, joined 2024-01-01)
    """
    
    __tablename__ = 'team_members'
    
    # ===== IDENTIFICATION =====
    # Unique ID for this membership record
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    
    # ===== RELATIONSHIPS =====
    # Which team is this membership for?
    team_id = db.Column(
        db.Integer,
        db.ForeignKey('teams.id'),  # Points to Team.id
        nullable=False              # Required
    )
    
    # Which user is this membership for?
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),  # Points to User.id
        nullable=False              # Required
    )
    
    # What role does this user have in this team?
    # (admin = full control, member = regular permissions)
    role_id = db.Column(
        db.Integer,
        db.ForeignKey('roles.id'),  # Points to Role.id
        nullable=False              # Required
    )
    
    # ===== TIMESTAMPS =====
    # When did this user join the team?
    joined_at = db.Column(
        db.DateTime,
        default=datetime.utcnow  # Auto-set to now
    )
    
    # ===== RELATIONSHIPS =====
    # The Team this membership belongs to
    team = db.relationship(
        'Team',
        back_populates='team_members',
        overlaps='members,teams'
    )
    
    # The User this membership belongs to
    user = db.relationship(
        'User',
        back_populates='team_members',
        overlaps='members,teams'
    )
    
    # The Role this user has in this team
    role = db.relationship(
        'Role',
        back_populates='team_members'
    )
    
    # ===== CONSTRAINTS =====
    # Prevent duplicate memberships
    # A user can only have one membership per team
    __table_args__ = (
        db.UniqueConstraint(
            'team_id',
            'user_id',
            name='unique_team_user'
        ),
    )


class Channel(db.Model):
    """
    Channel model - conversation channels within a team.
    
    Channels allow organizing conversations by topic/purpose.
    
    Fields:
    - name: Channel name (e.g., 'general', 'random')
    - description: Channel purpose
    - team_id: Which team this channel belongs to
    - is_private: Private channels are invite-only
    - created_by_id: User who created the channel
    """
    
    __tablename__ = 'channels'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    is_private = db.Column(db.Boolean, default=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    team = db.relationship('Team', back_populates='channels')
    creator = db.relationship('User', foreign_keys=[created_by_id])
    messages = db.relationship('Message', back_populates='channel', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.UniqueConstraint('team_id', 'name', name='unique_channel_in_team'),
    )


class Message(db.Model):
    """
    Message model - messages posted in channels.
    
    Fields:
    - content: The message text
    - channel_id: Which channel the message is in
    - sender_id: Who sent the message
    - created_at: When the message was posted
    - updated_at: When the message was last edited
    - is_edited: Flag indicating if message was edited
    """
    
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_edited = db.Column(db.Boolean, default=False)
    
    # Relationships
    channel = db.relationship('Channel', back_populates='messages')
    sender = db.relationship('User', back_populates='messages', foreign_keys=[sender_id])
    
    # Performance optimization: indexes for common queries
    __table_args__ = (
        db.Index('ix_message_channel_created', 'channel_id', 'created_at'),
        db.Index('ix_message_sender_created', 'sender_id', 'created_at'),
    )
    
    def __repr__(self):
        return f'<Message {self.id} by {self.sender.username}>'


class DirectMessage(db.Model):
    """
    DirectMessage model - private messages between two users.
    
    Fields:
    - content: Message text
    - sender_id: User sending the message
    - recipient_id: User receiving the message
    - is_read: Whether recipient has read the message
    - created_at: When sent
    """
    
    __tablename__ = 'direct_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    sender = db.relationship(
        'User',
        back_populates='direct_messages_sent',
        foreign_keys=[sender_id]
    )
    recipient = db.relationship(
        'User',
        back_populates='direct_messages_received',
        foreign_keys=[recipient_id]
    )


class File(db.Model):
    """
    File model - metadata for uploaded files.
    
    Why store metadata separately?
    - Track file ownership and sharing
    - Search and filter files
    - Manage permissions
    - Display file info without reading from disk
    
    Fields:
    - filename: Original filename
    - filepath: Path on server
    - file_size: Size in bytes
    - mime_type: Content type (image/png, etc)
    - uploaded_by_id: User who uploaded
    - team_id: Team where file is shared (if team file)
    - channel_id: Channel where file was shared (if channel file)
    """
    
    __tablename__ = 'files'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)  # in bytes
    mime_type = db.Column(db.String(100))
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    uploader = db.relationship('User', foreign_keys=[uploaded_by_id])
    team = db.relationship('Team', back_populates='files')
    channel = db.relationship('Channel', foreign_keys=[channel_id])


class Task(db.Model):
    """
    Task model - task items for team project management.
    
    Fields:
    - title: Task title
    - description: Detailed description
    - team_id: Team this task belongs to
    - assigned_to_id: User task is assigned to
    - status: 'todo', 'in_progress', 'done'
    - priority: 'low', 'medium', 'high'
    - due_date: When task is due
    - created_by_id: User who created the task
    - created_at, updated_at: Timestamps
    """
    
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(20), default='todo')  # todo, in_progress, done
    priority = db.Column(db.String(20), default='medium')  # low, medium, high
    due_date = db.Column(db.DateTime)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    team = db.relationship('Team', back_populates='tasks')
    assigned_to = db.relationship('User', back_populates='tasks', foreign_keys=[assigned_to_id])
    creator = db.relationship('User', back_populates='tasks_created', foreign_keys=[created_by_id])


class Notification(db.Model):
    """
    Notification model - tracks events/notifications for users.
    
    Why separate table?
    - Users need to see what's happened while they were away
    - Decouple notification storage from events
    - Allow marking notifications as read
    
    Fields:
    - user_id: Who the notification is for
    - type: Type of event (message, mention, task_assigned, etc)
    - title: Notification title
    - message: Notification message
    - related_id: ID of related object (message ID, team ID, etc)
    - is_read: Whether user has seen this notification
    - created_at: When event occurred
    """
    
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # message, mention, task_assigned, team_invite, etc
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text)
    related_id = db.Column(db.Integer)  # ID of related object (message, team, task, etc)
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = db.relationship('User', back_populates='notifications')
    
    def __repr__(self):
        return f'<Notification {self.type} for user {self.user_id}>'


class CallTranscript(db.Model):
    """
    CallTranscript model - stores live speech-to-text segments and call summary.

    Fields:
    - call_id: The call this transcript belongs to
    - speaker_id: User whose speech was captured
    - text: The transcribed text segment
    - timestamp: When the segment was captured (for ordering)
    - summary: Full extractive summary (stored on the Call row but aggregated here)
    """

    __tablename__ = 'call_transcripts'

    id = db.Column(db.Integer, primary_key=True)
    call_id = db.Column(db.Integer, db.ForeignKey('calls.id'), nullable=False, index=True)
    speaker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.Float, default=0.0, index=True)  # Added for chronological ordering
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    call = db.relationship('Call', foreign_keys=[call_id], backref='transcripts')
    speaker = db.relationship('User', foreign_keys=[speaker_id])

    # Performance optimization: composite indexes for common queries
    __table_args__ = (
        db.Index('ix_call_transcript_timestamp', 'call_id', 'timestamp'),
        db.Index('ix_call_transcript_speaker', 'speaker_id', 'created_at'),
    )

    def __repr__(self):
        return f'<CallTranscript call={self.call_id} speaker={self.speaker_id}>'


class TeamInvitation(db.Model):
    """
    TeamInvitation model - tracks pending invitations to join a team.

    Fields:
    - team_id: Team being invited to
    - inviter_id: Admin who sent the invite
    - invitee_id: User being invited
    - status: pending, accepted, declined
    - created_at: When invitation was sent
    """

    __tablename__ = 'team_invitations'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    inviter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    invitee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, accepted, declined
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    team = db.relationship('Team', foreign_keys=[team_id])
    inviter = db.relationship('User', foreign_keys=[inviter_id])
    invitee = db.relationship('User', foreign_keys=[invitee_id])

    __table_args__ = (
        db.UniqueConstraint('team_id', 'invitee_id', name='unique_team_invitation'),
    )

    def __repr__(self):
        return f'<TeamInvitation {self.inviter_id} -> {self.invitee_id} for team {self.team_id} ({self.status})>'


class Call(db.Model):
    """
    Call model - records video calls (1-to-1 or group).
    
    Two types of calls:
    
    1. ONE-TO-ONE CALLS:
       - caller_id: Person initiating call (e.g., alice)
       - callee_id: Person receiving call (e.g., bob)
       - team_id: NULL (not a team call)
       - participants: Empty (don't need join table for 2 people)
    
    2. GROUP CALLS:
       - caller_id: Person initiating call (first person to start call)
       - callee_id: NULL (multiple people, not just one receiver)
       - team_id: Which team is having the call?
       - participants: List of CallParticipant records for all members
    
    Why separate caller_id/callee_id from team_id?
    - Backward compatibility with 1-to-1 calls
    - Simple to query: "get all calls initiated by user X"
    """
    
    __tablename__ = 'calls'
    
    # ===== IDENTIFICATION =====
    # Unique ID for this call
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    
    # ===== PARTICIPANTS (1-TO-1 CALLS) =====
    # Who initiated this call?
    # For 1-to-1: alice calls bob, caller_id = alice
    # For group: first person to start, caller_id = first person
    caller_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),  # Points to User.id
        nullable=True,              # Not always present
        index=True                  # Indexed for fast queries
    )
    
    # Who received this call?
    # For 1-to-1: alice calls bob, callee_id = bob
    # For group: NULL (many receivers, not just one)
    callee_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=True,      # NULL for group calls
        index=True
    )
    
    # ===== GROUP CALL INFO =====
    # Which team is this group call in?
    # For 1-to-1: NULL (not a team call)
    # For group: team.id
    team_id = db.Column(
        db.Integer,
        db.ForeignKey('teams.id'),  # Points to Team.id
        nullable=True,              # NULL for 1-to-1 calls
        index=True
    )
    
    # ===== CALL DETAILS =====
    # What type of call? ('one-to-one' or 'group')
    call_type = db.Column(
        db.String(20),
        default='one-to-one',   # Default to 1-to-1
        nullable=False
    )
    
    # What's the current status?
    # pending = waiting for answer
    # active = call in progress
    # completed = call ended normally
    # rejected = receiver said no
    # missed = receiver didn't answer
    status = db.Column(
        db.String(20),
        default='pending',  # Starts as pending
        nullable=False
    )
    
    # Unique token to identify this call session
    # Used for routing WebRTC offers/answers
    # Format: UUID (e.g., '17be809a-fd09-4f44-9af0-9996f3c5836f')
    call_token = db.Column(
        db.String(100),
        unique=True,    # No two calls with same token!
        nullable=False  # Required
    )
    
    # ===== TIMESTAMPS =====
    # When was this call initiated?
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,  # Auto-set to now
        nullable=False,
        index=True  # Indexed for queries like "calls today"
    )
    
    # When did the call START? (when receiver accepted)
    # NULL while still pending (waiting for answer)
    started_at = db.Column(db.DateTime)
    
    # When did the call END?
    # NULL while call is still active
    ended_at = db.Column(db.DateTime)
    
    # How long did the call last? (in seconds)
    # Calculated: (ended_at - started_at).total_seconds()
    duration = db.Column(
        db.Integer,
        default=0  # 0 if still active or never started
    )
    
    # AI-generated summary of call (optional)
    # Could contain: "Discussed project timeline, assigned tasks"
    # Useful for call history and notes
    summary = db.Column(db.Text)
    
    # ===== RELATIONSHIPS =====
    # Who called? (User object, or None if group call)
    caller = db.relationship(
        'User',
        foreign_keys=[caller_id],
        backref='calls_initiated'  # user.calls_initiated = calls they started
    )
    
    # Who was called? (User object, or None if group call)
    callee = db.relationship(
        'User',
        foreign_keys=[callee_id],
        backref='calls_received'   # user.calls_received = calls to them
    )
    
    # Which team? (Team object, or None if 1-to-1)
    team = db.relationship(
        'Team',
        backref='calls'  # team.calls = all calls in that team
    )
    
    # Who participated in this group call?
    # Query result: call.participants returns list of CallParticipant records
    participants = db.relationship(
        'CallParticipant',
        back_populates='call',
        cascade='all, delete-orphan'  # Delete participants when call deleted
    )
    
    def __repr__(self):
        """String representation for debugging."""
        if self.call_type == 'group':
            return f'<Call {self.id}: Group call in team {self.team_id} ({self.status})>'
        return f'<Call {self.id}: {self.caller_id} -> {self.callee_id} ({self.status})>'
    
    def to_dict(self):
        """
        Convert call to dictionary for JSON responses.
        
        This method is used when sending call info to frontend as JSON.
        Handles both 1-to-1 and group calls.
        """
        # Build basic info for both types
        result = {
            'id': self.id,
            'call_type': self.call_type,
            'status': self.status,
            'call_token': self.call_token,
            'created_at': self.created_at.isoformat(),  # Convert datetime to ISO string
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration': self.duration
        }
        
        # Add GROUP CALL info
        if self.call_type == 'group':
            result['team_id'] = self.team_id
            result['team_name'] = self.team.name if self.team else None
            # Get list of participant usernames
            result['participants'] = [p.user.username for p in self.participants]
        
        # Add ONE-TO-ONE CALL info
        else:
            result['caller_id'] = self.caller_id
            result['caller_name'] = self.caller.username
            result['callee_id'] = self.callee_id
            result['callee_name'] = self.callee.username
        
        return result


class CallParticipant(db.Model):
    """
    Join table for group calls.
    
    This table tracks WHO is in a group call and WHEN they joined/left.
    
    Example:
    - Call #123 (group call in Engineering Team)
    - CallParticipant: alice joined 2:00pm
    - CallParticipant: bob joined 2:00pm
    - CallParticipant: charlie joined 2:05pm (joined late)
    
    This gives us:
    - Full history of who participated
    - How long each person was in the call
    - Can calculate duration per person
    """
    
    __tablename__ = 'call_participants'
    
    # ===== IDENTIFICATION =====
    # Unique ID for this participant record
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    
    # ===== RELATIONSHIPS =====
    # Which call is this participant in?
    call_id = db.Column(
        db.Integer,
        db.ForeignKey('calls.id'),  # Points to Call.id
        nullable=False,
        index=True  # Indexed for queries like "who's in call 123?"
    )
    
    # Which user is participating?
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),  # Points to User.id
        nullable=False,
        index=True  # Indexed for queries like "what calls is alice in?"
    )
    
    # ===== TIMESTAMPS =====
    # When did this user join the call?
    joined_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,  # Auto-set to now
        nullable=False
    )
    
    # When did this user leave the call?
    # NULL = still in call (hasn't left yet)
    # If set = user left at this time
    left_at = db.Column(db.DateTime)
    
    # ===== RELATIONSHIPS =====
    # The Call this participant is in
    call = db.relationship(
        'Call',
        back_populates='participants'  # Two-way relationship
    )
    
    # The User who is participating
    user = db.relationship(
        'User',
        backref='call_participations'  # user.call_participations = all calls they were in
    )
    
    def __repr__(self):
        """String representation for debugging."""
        return f'<CallParticipant call={self.call_id} user={self.user_id}>'


class FaceStudent(db.Model):
    """
    Persisted face-recognition student record.

    The face-attendance page stores each student's class name, contact details,
    photo preview, and face descriptor here so the roster survives browser restarts.
    """

    __tablename__ = 'face_students'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
        index=True
    )

    class_name = db.Column(db.String(100), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    email = db.Column(db.String(120))
    photo_data_url = db.Column(db.Text, nullable=False)
    descriptor_json = db.Column(db.Text, nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    user = db.relationship('User', backref='face_students')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'class_name', 'name', name='uq_face_student_per_user_class_name'),
    )

    def descriptor_as_list(self):
        """Return the stored descriptor as a plain Python list."""
        try:
            return json.loads(self.descriptor_json)
        except (TypeError, ValueError):
            return []

    def to_dict(self):
        """Serialise the record for the face-attendance API."""
        return {
            'name': self.name,
            'email': self.email or '',
            'className': self.class_name,
            'photoDataUrl': self.photo_data_url,
            'descriptor': self.descriptor_as_list()
        }
