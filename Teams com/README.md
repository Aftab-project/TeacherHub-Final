# Team Collaboration Platform

A modern, web-based team collaboration platform inspired by Microsoft Teams, built with Flask and SQLite.

## Summary

This project is a full-stack collaboration platform for university group work and team communication. It includes authentication, team and channel management, direct and channel messaging, file sharing, task tracking, notifications, and call/transcription-related workflows in a modular Flask application.

## How To Run

Use these steps from the `Teams com/` folder:

```bash
# 1) Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) (Optional but recommended) create environment file
copy .env.example .env

# 4) Start the app
python app.py
```

Open `http://localhost:5000` in your browser.

## Features

### ✅ Implemented Features

#### Phase 1: Foundation
- ✅ User authentication system (registration, login, logout)
- ✅ Secure password hashing
- ✅ User profiles with customizable information
- ✅ Session management with Flask-Login
- ✅ Database models for all core entities

#### Phase 2: Teams & Channels
- ✅ Create and manage teams
- ✅ Join teams via invitation codes
- ✅ Team member management
- ✅ Role-based access control (Admin, Member)
- ✅ Team channels for organized discussions
- ✅ Team settings and customization

#### Phase 3: Messaging
- ✅ Channel messaging with message history
- ✅ Direct messaging between users
- ✅ Message editing and deletion
- ✅ @mention system with notifications
- ✅ Message search functionality
- ✅ Pagination for message history

#### Phase 4: File Sharing
- ✅ File upload to teams and channels
- ✅ File download functionality
- ✅ File metadata tracking
- ✅ File permission management
- ✅ File type validation (configurable)

#### Phase 5: Task Management
- ✅ Create tasks with descriptions
- ✅ Task assignment to team members
- ✅ Status tracking (todo, in_progress, done)
- ✅ Priority levels (low, medium, high)
- ✅ Task due dates
- ✅ Task notifications

#### Phase 6: Notifications
- ✅ Real-time notification system
- ✅ Mention notifications
- ✅ Task assignment notifications
- ✅ Team member join notifications
- ✅ Notification history and management

#### Phase 7: User Interface
- ✅ Responsive design (mobile, tablet, desktop)
- ✅ Teams-inspired dark/light neutral theme
- ✅ Clean, modern UI components
- ✅ Intuitive navigation
- ✅ Flash messages for user feedback

#### Phase 8: Search
- ✅ Message search across teams
- ✅ Keyword-based searching
- ✅ Search result pagination

### 🎯 Planned Future Features

- AI Assistant (conversation summarization, FAQ)
- Advanced permissions system
- File preview functionality
- Message reactions and threading
- Scheduled messages
- Team analytics dashboard
- Video/voice call integration
- Mobile app
- API documentation
- Admin dashboard

## Project Structure

```
Teams/
├── app.py                 # Main application entry point
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── app/
│   ├── __init__.py        # Flask app factory
│   ├── models/
│   │   ├── models.py      # Database models
│   │   └── __init__.py
│   ├── routes/
│   │   ├── auth_routes.py        # Authentication
│   │   ├── dashboard_routes.py   # Dashboard
│   │   ├── team_routes.py        # Team management
│   │   ├── message_routes.py     # Messaging
│   │   ├── file_routes.py        # File handling
│   │   ├── task_routes.py        # Task management
│   │   └── __init__.py
├── templates/             # HTML templates
│   ├── base.html         # Base layout
│   ├── auth/            # Authentication templates
│   ├── dashboard/       # Dashboard templates
│   ├── teams/           # Team templates
│   ├── messages/        # Message templates
│   ├── files/           # File templates
│   └── tasks/           # Task templates
├── static/              # Static files
│   ├── css/
│   │   └── style.css    # Main stylesheet
│   ├── js/              # JavaScript files
│   └── images/          # Image assets
└── uploads/             # Uploaded files

```

## Installation

### 1. Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### 2. Set Up Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy and edit .env file
cp .env.example .env

# Edit .env with your settings
# - Set SECRET_KEY to a random string
# - Configure DATABASE_URL if needed
```

### 5. Run the Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

## Usage

### First Time Setup

1. **Register an account**: Visit the registration page and create an account
2. **Create a team**: Go to Dashboard → Create Team
3. **Invite others**: Share your team code or direct link
4. **Start collaborating**: Create channels and messages

### Creating Teams

1. Click "Create Team" on the dashboard
2. Enter team name and optional description
3. Choose privacy settings
4. Invite members using the team code

### Managing Channels

1. Go to your team page
2. Click "Create Channel"
3. Name your channel (lowercase recommended)
4. Start messaging

### Direct Messaging

1. Search for a user
2. Click to open direct message conversation
3. Type and send messages

### File Sharing

1. In any channel or team, use the file upload feature
2. Select your file (up to 16MB)
3. Files are automatically organized and downloadable

### Task Management

1. Go to team → Tasks tab
2. Create new task with title, description, assignee
3. Set priority and due date
4. Track progress through status updates

## Database Schema

### Core Tables

- **users**: User accounts and profiles
- **teams**: Team/workspace information
- **team_members**: User-team relationships with roles
- **channels**: Team channels for conversations
- **messages**: Channel messages
- **direct_messages**: Private user-to-user messages
- **files**: File metadata and sharing
- **tasks**: Task items with status tracking
- **notifications**: User event notifications
- **roles**: Access control roles

### Key Relationships

- Users (many-to-many) ← Teams
- Teams (one-to-many) → Channels
- Channels (one-to-many) → Messages
- Users (one-to-many) → Tasks

## Security Features

### Authentication & Authorization

- ✅ Password hashing with werkzeug.security (PBKDF2)
- ✅ Session management with Flask-Login
- ✅ Role-based access control (RBAC)
- ✅ Team membership verification on all operations
- ✅ CSRF protection with Flask-WTF

### Data Protection

- ✅ Input validation on all forms
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ Secure file upload handling
- ✅ XSS prevention with Jinja2 templating
- ✅ Environment-based configuration

### File Security

- ✅ File type whitelist
- ✅ File size limits (16MB default)
- ✅ Secure filename handling
- ✅ Access control for downloads
- ✅ Files stored outside web root

## Configuration

### Environment Variables

```env
FLASK_ENV          # development, testing, production
SECRET_KEY          # Session encryption key
DATABASE_URL        # Database connection string
PORT               # Server port (default 5000)
MAX_CONTENT_LENGTH  # File upload size limit
```

### Application Constants

Edit `config.py` to customize:

- Session timeout
- File upload limits
- Allowed file types
- Items per page
- Message length limits

## Development

### Code Structure Principles

- **Modular**: Each feature has its own route blueprint
- **DRY**: Reusable components and utilities
- **Separation of Concerns**: Models, routes, templates separate
- **Clear Naming**: Descriptive function and variable names
- **Documented**: Comments explain complex logic

### Adding New Features

1. Define database models in `app/models/models.py`
2. Create route handlers in `app/routes/`
3. Add HTML templates in `templates/`
4. Update `app/__init__.py` to register blueprints
5. Test thoroughly
6. Document changes in CHANGELOG.md

### Testing

The application includes built-in testing for:

- User registration and authentication
- Team creation and membership
- Channel messaging
- File upload and download
- Task management

Manual testing is recommended for UI features.

## Troubleshooting

### Database Issues

```bash
# Reset database (WARNING: deletes all data)
rm team_collab.db
python -c "from app import create_app; app = create_app(); print('Database reset')"
```

### Port Already in Use

```bash
# Run on different port
set PORT=5001
python app.py
```

### Module Not Found

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Performance Considerations

- Messages paginated (50 per page)
- Indexes on frequently queried fields (username, email, team_id)
- Efficient ORM queries with proper relationships
- Static file caching recommended with production server

## Deployment

For production deployment:

1. **Use production process manager** (Gunicorn + reverse proxy)
2. **Enable HTTPS** (required for secure cookies)
3. **Use strong SECRET_KEY**
4. **Configure proper database** (PostgreSQL recommended)
5. **Set up static file serving** (CDN or nginx)
6. **Enable logging and monitoring**
7. **Set FLASK_ENV=production**
8. **Use environment secrets management**
9. **Add health check path** using `/healthz`

Example command (app factory):

```bash
gunicorn --factory --workers 2 --threads 4 --bind 0.0.0.0:5000 app:create_app
```

If you need full WebSocket-heavy traffic for calls, run through a Socket.IO compatible stack and validate call signaling in staging before release.

## Contributing

When contributing:

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Test thoroughly
5. Keep commits focused and well-described

## License

This project is created for educational purposes as part of a final-year Computer Science project.

## Support

For issues or questions:

1. Check existing documentation
2. Review code comments
3. Check CHANGELOG.md for recent changes
4. Test in isolation to identify problems

## Technologies Used

- **Backend**: Flask 3.0.0
- **Database**: SQLAlchemy ORM with SQLite
- **Authentication**: Flask-Login
- **Security**: Werkzeug, Flask-WTF
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Server**: Flask development server (Gunicorn for production)

## Development History

See CHANGELOG.md and DESIGN_DECISIONS.md for:

- All changes made to the project
- Design decisions and their rationale
- Known limitations
- Future improvement ideas

---

**Status**: Phase 6 Complete - Core features implemented and tested

**Last Updated**: 2026-06-12
