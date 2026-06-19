# Design Decisions - Team Collaboration Platform

## Architecture Decisions

### 1. Flask Framework
**Decision:** Use Flask instead of Django
**Rationale:**
- Simpler, more lightweight for learning projects
- Better for understanding web fundamentals
- Easier to customize and extend
- Excellent documentation
- Suitable for final-year undergraduate projects

**Trade-offs:**
- Django would provide more built-in features (ORM, admin panel, etc.)
- Flask requires more manual setup but provides better learning experience

---

### 2. SQLAlchemy ORM
**Decision:** Use SQLAlchemy ORM instead of raw SQL
**Rationale:**
- Type-safe database queries
- Automatic SQL injection prevention
- Easier relationship management
- Supports multiple database backends
- Better for testing and migration

**Trade-offs:**
- Slightly less control over queries
- Small performance overhead (negligible for this project size)

---

### 3. SQLite Database
**Decision:** Use SQLite instead of PostgreSQL/MySQL
**Rationale:**
- No external database server required
- Perfect for development and testing
- Easy to backup and distribute
- Sufficient for team collaboration platform scope
- Aligns with student project requirements

**Trade-offs:**
- Not suitable for large-scale production use
- Limited concurrency support
- Migration path required for production deployment

---

### 4. Session-based Authentication
**Decision:** Use Flask-Login with session-based authentication
**Rationale:**
- Standard for web applications
- User-friendly (no token management)
- Secure with httponly cookies
- CSRF protection out of the box
- Simpler than JWT for traditional web apps

**Trade-offs:**
- Not suitable for distributed systems
- Limited for mobile app support
- Would need JWT for API-first architecture

---

### 5. Blueprint-based Routing
**Decision:** Use Flask blueprints to organize routes
**Rationale:**
- Modular code structure
- Easier to test and maintain
- Clear separation of concerns
- Scales well as application grows
- Professional industry practice

**Trade-offs:**
- Slightly more boilerplate code
- Requires understanding of blueprint registration

---

### 6. Template-based Frontend
**Decision:** Use Jinja2 templates with vanilla CSS/JavaScript
**Rationale:**
- No build process required
- Easy for students to understand and modify
- Faster development iteration
- XSS protection built-in via Jinja2
- Reduces complexity compared to SPA frameworks

**Trade-offs:**
- No reactive UI framework
- Less sophisticated interactivity compared to React/Vue
- Requires full page reloads for some operations

---

## Data Model Decisions

### 1. Many-to-Many Relationship with Explicit Join Table
**Decision:** Use TeamMember join table instead of simple many-to-many
**Rationale:**
- Need to store role information (admin, member)
- Need to track when user joined team
- Enables future features (permissions, team history)
- More flexible for access control

**Benefit:** Role-based access control built into the schema

---

### 2. Separate Tables for Channel and Direct Messages
**Decision:** Use separate Message and DirectMessage tables
**Rationale:**
- Different schema requirements
- Clearer separation of concerns
- Different access control patterns
- Easier to query and archive

**Trade-off:** Code duplication for message handling (acceptable for clarity)

---

### 3. Task Model with Two Foreign Keys to User
**Decision:** Separate assigned_to and created_by relationships
**Rationale:**
- Need to track task creator for notifications
- Need to track assignee for task assignment
- Enable filtering by creator or assignee
- Support delegation workflow

**Technical Challenge:** Requires explicit foreign_keys specification in SQLAlchemy

---

### 4. File Metadata Storage
**Decision:** Store file metadata in database, files on disk
**Rationale:**
- Separate concerns (data vs files)
- Easier to track file permissions
- Database queries don't require disk access
- Can implement soft deletes
- Easier to implement access controls

**Storage Strategy:**
- Files stored in `uploads/` folder
- Timestamped filenames to prevent collisions
- Original filename stored in database for display

---

## Security Decisions

### 1. Password Hashing
**Decision:** Use werkzeug.security.generate_password_hash
**Rationale:**
- Industry standard (PBKDF2)
- Automatic salt generation
- No plaintext storage
- Built into Flask ecosystem

**Implementation:**
```python
def set_password(self, password):
    self.password_hash = generate_password_hash(password)

def check_password(self, password):
    return check_password_hash(self.password_hash, password)
```

---

### 2. Session Management
**Decision:** Use Flask-Login with session cookies
**Rationale:**
- httponly flag prevents JavaScript access
- Secure flag in production (HTTPS only)
- SameSite=Lax prevents CSRF
- Automatic session timeout

**Configuration:**
```python
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False  # True in production
SESSION_COOKIE_SAMESITE = 'Lax'
PERMANENT_SESSION_LIFETIME = 24 * 60 * 60  # 24 hours
```

---

### 3. CSRF Protection
**Decision:** Use Flask-WTF with token validation
**Rationale:**
- Built-in form protection
- Post-Redirect-Get pattern for state changes
- Tokens generated per session

---

### 4. Input Validation
**Decision:** Validate all user inputs server-side
**Rationale:**
- Client-side validation can be bypassed
- Consistent with security best practices
- Prevents edge cases

**Validation Types:**
- Length validation (username, team name, messages)
- Format validation (email format)
- Uniqueness validation (username, email, team codes)
- Content validation (file types, message length)

---

### 5. Access Control
**Decision:** Implement role-based access control (RBAC)
**Rationale:**
- Team admin vs member distinction
- Clear permission model
- Scalable for future feature additions

**Implementation Pattern:**
```python
# Check team membership
if team not in current_user.teams:
    flash('Unauthorized', 'error')
    redirect(...)

# Check admin role
member = TeamMember.query.filter_by(
    team_id=team_id,
    user_id=current_user.id
).first()

if member.role.name != 'admin':
    return {'error': 'Unauthorized'}, 403
```

---

### 6. File Upload Security
**Decision:** Implement whitelist-based validation
**Rationale:**
- Prevent malicious file uploads
- Prevent arbitrary file execution
- Filename sanitization with werkzeug.security.secure_filename

**Configuration:**
```python
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif',
    'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'zip'
}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
```

---

## UI/UX Decisions

### 1. CSS Framework Approach
**Decision:** Custom CSS with CSS variables instead of Bootstrap/Tailwind
**Rationale:**
- Teaches CSS fundamentals
- Customizable Teams-inspired design
- No external dependencies
- Smaller file size
- Complete control over styling

**Design System:**
- CSS custom properties for consistent theming
- Mobile-first responsive design
- Accessible color contrasts (WCAG AA)

---

### 2. Navigation Structure
**Decision:** Navbar + sidebar alternative layout
**Rationale:**
- Top navbar for branding and user menu
- Main content area for primary content
- Responsive: sidebar collapses on mobile

---

### 3. Flash Messages
**Decision:** Server-side flash messages with CSS animations
**Rationale:**
- User-friendly feedback
- Consistent across application
- No JavaScript required
- Automatic dismissal via CSS animation

**Message Types:**
- success (green)
- error (red)
- info (blue)
- warning (orange)

---

## Scalability Decisions

### 1. Database Indexing
**Decision:** Index frequently queried columns
**Rationale:**
- Improve query performance
- Essential as user base grows

**Indexed Columns:**
- users.username (login queries)
- users.email (registration validation)
- messages.created_at (pagination)
- notifications.is_read, user_id (unread count)
- team_members.team_id, user_id (membership checks)

---

### 2. Message Pagination
**Decision:** Paginate message history (50 per page)
**Rationale:**
- Prevent loading entire conversation history
- Reduce page load times
- Better user experience with large conversations

---

### 3. Notification Queue
**Decision:** Create notifications immediately on events
**Rationale:**
- Simple implementation
- Scalable with database indexing
- Can be migrated to background jobs (Celery) later

---

## Testing Decisions

### 1. Manual Testing Focus
**Decision:** Emphasize manual testing over unit tests
**Rationale:**
- Faster feedback during development
- Better for learning final-year students
- Easier to demonstrate to examiners
- Can add unit tests later

**Test Coverage:**
- Authentication flow (register, login, logout)
- Team CRUD operations
- Channel messaging
- File upload/download
- Task management
- Notification generation

---

### 2. Test Scenarios
**Decision:** Test critical happy paths
**Rationale:**
- Limited time in development
- Focus on core features
- Easy to extend tests

**Critical Paths:**
1. User registration with validation
2. Team creation and member joining
3. Message sending and retrieval
4. File upload and download
5. Task creation and status update

---

## Future Improvement Decisions

### 1. AI Assistant (Phase 9)
**Approach:** Integration point ready
**Rationale:**
- Separate API for easy integration
- Don't over-engineer before MVP
- Can use existing services (OpenAI, Hugging Face)

---

### 2. Real-time Features
**Current:** Polling/refresh based
**Future:** WebSocket implementation
**Rationale:**
- Simpler to implement initially
- WebSocket adds complexity
- Can be added without changing core architecture

---

### 3. Production Deployment
**Current:** Flask development server
**Future:** Gunicorn + Nginx + PostgreSQL
**Rationale:**
- Development server not suitable for production
- SQLite insufficient for concurrent users
- Nginx for static file serving and reverse proxy

---

### 4. API versioning
**Current:** Single monolithic API
**Future:** RESTful API separation
**Rationale:**
- Can add mobile app later
- Third-party integrations
- Microservice architecture if needed

---

## Known Limitations

### 1. SQLAlchemy Relationship Warnings
**Issue:** Many-to-many relationships generate SAWarning
**Rationale:** Expected behavior with explicit join table
**Solution:** Add `overlaps` parameter to suppress warnings (non-critical)

---

### 2. No Real-time Updates
**Limitation:** Users must refresh to see new messages
**Workaround:** Can add JavaScript polling
**Future:** WebSocket implementation

---

### 3. File Storage on Disk
**Limitation:** Not suitable for distributed systems
**Workaround:** Store on local disk for MVP
**Future:** Migrate to cloud storage (S3, Azure Blob)

---

### 4. No Email Notifications
**Limitation:** Only in-app notifications
**Rationale:** Simpler to implement
**Future:** Add email notification service

---

## Documentation Strategy

### 1. Inline Code Comments
- Explain "why" not "what"
- Document complex business logic
- Comment on security decisions

### 2. README.md
- Installation instructions
- Feature list
- Project structure
- Troubleshooting guide

### 3. CHANGELOG.md
- Chronological record of changes
- Feature additions
- Bug fixes
- Breaking changes

### 4. DESIGN_DECISIONS.md
- This document
- Architectural choices
- Trade-offs considered
- Rationale for decisions

---

## Summary

The Team Collaboration Platform is designed with the following principles:

1. **Simplicity First:** Easy to understand and modify
2. **Security by Default:** Security built into the architecture
3. **Scalability Ready:** Foundation for growth without major rewrites
4. **Learning Focused:** Code is readable and educational
5. **Professional Practices:** Industry-standard patterns and technologies

These decisions balance educational value with practical implementation, ensuring the project is both achievable for a final-year student and suitable for demonstration to university examiners.
