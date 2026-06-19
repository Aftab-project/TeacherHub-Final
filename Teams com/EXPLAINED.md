# Teacher Feature Hub - Complete Explanation Guide

**Written for: University Supervisor/Examiner**  
**Purpose: Understand the entire project architecture and how it works**

---

## 🎯 Project Overview

**What is this?**  
A web-based team collaboration platform inspired by Microsoft Teams. It lets teachers and students create teams, chat, share files, manage tasks, and conduct video calls - all from one website.

**Why build it?**  
Final-year Computer Science project to demonstrate:
- Full-stack web development skills
- Database design and relationships
- User authentication and authorization
- Real-time communication (WebRTC for video calls)
- Responsive web design

**Technology Stack:**
- **Backend**: Python Flask (lightweight, educational)
- **Database**: SQLite with SQLAlchemy ORM (type-safe)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (no frameworks)
- **Real-time**: Socket.IO for WebRTC signaling
- **Security**: Password hashing, CSRF protection, input validation

---

## 📊 How Everything is Connected

### Database Schema (10 Tables)

```
┌─────────────────────────────────────────┐
│              USERS TABLE                │
│  - username (unique login)              │
│  - password_hash (never plaintext!)     │
│  - email                                │
│  - profile info (name, bio, picture)   │
└─────────────────────────────────────────┘
              ↓         ↓         ↓
          creates    owns      sends
          │          │         │
          ↓          ↓         ↓
    ┌─────────────────────────────────────────┐
    │          TEAMS TABLE                    │
    │  - team_name (e.g., "Computer Sci")     │
    │  - team_code (invite code, 8 chars)     │
    │  - description                          │
    │  - owner_id (who created it)            │
    └─────────────────────────────────────────┘
              ↓              ↓
          contains      managed by
              │              │
              ↓              ↓
    ┌──────────────────┐  ┌──────────────────┐
    │ CHANNELS TABLE   │  │ TEAM_MEMBERS     │
    │ (conversations)  │  │ (join table)     │
    │ - general        │  │ - user_id        │
    │ - random         │  │ - team_id        │
    │ - announcements  │  │ - role_id        │
    └──────────────────┘  │ - joined_at      │
            ↓             └──────────────────┘
       contains
            │
            ↓
    ┌──────────────────────┐
    │  MESSAGES TABLE      │
    │  (channel messages)  │
    │  - content           │
    │  - sender_id         │
    │  - created_at        │
    └──────────────────────┘

Also connected:
- DIRECT_MESSAGES (private 1-to-1 chats)
- FILES (shared file metadata)
- TASKS (project tasks with status)
- NOTIFICATIONS (event alerts)
- CALLS (video call history)
- CALL_PARTICIPANTS (group call tracking)
```

**Key Concept: Why relationships matter**
- Users belong to many Teams (many-to-many)
- Teams have many Channels (one-to-many)
- Channels have many Messages (one-to-many)
- This structure prevents data duplication and ensures integrity

---

## 🔐 Security - How We Keep Data Safe

### 1. **Authentication (Login)**
```
User types password → Hashed with PBKDF2 → Compare with stored hash
Never store plaintext passwords! ✓
```

**How it works:**
1. User enters username + password
2. We hash the password (one-way encryption)
3. We compare it to what's in the database
4. If it matches, create a session (like a ticket)
5. User keeps session ticket in cookie
6. Each request checks: "Does this session ticket exist?"

**Why this is secure:**
- Even if database is stolen, passwords are useless (one-way hash)
- Session tickets expire after 24 hours
- `httponly` flag prevents JavaScript from stealing cookies

### 2. **Authorization (Access Control)**

```
Is user logged in? → No → Redirect to login
↓ Yes
Is user in this team? → No → Show error
↓ Yes
Is user admin (if admin action)? → No → Show error
↓ Yes
Allow action ✓
```

**Example: Editing team settings**
- Only the team owner (admin) can edit settings
- We check: `if current_user_id == team.owner_id`
- If not, show error message

### 3. **Data Protection**

| Threat | Prevention |
|--------|-----------|
| SQL Injection | Use SQLAlchemy ORM (parameterized queries) |
| XSS (JavaScript injection) | Jinja2 auto-escapes HTML |
| CSRF (fake form submissions) | Flask-WTF tokens on every form |
| Unauthorized file access | Check user is in team before downloading |
| Large file uploads | Max 16MB limit, whitelist file types |

---

## 👤 User Registration & Login Flow

### Registration (New User Signup)

```
1. User visits /register page
2. User fills form: username, email, password
3. Frontend sends POST to /auth/register
4. Backend checks:
   - Username not taken?
   - Email not taken?
   - Password strong enough?
5. If valid: Create user record (password hashed!)
6. Redirect to login page
7. User logs in with credentials
```

**Code in `app/routes/auth_routes.py`:**
```python
# When user registers:
user = User(username=form.username.data, email=form.email.data)
user.set_password(form.password.data)  # Hashes password using PBKDF2
db.session.add(user)
db.session.commit()  # Save to database
```

**Why this is safe:**
- Password hashed before storing → even we can't see it
- Email verified later (can add 2FA in future)
- Username must be unique → prevents duplicates

---

## 🏢 Teams & Channels - Organizing Conversations

### How Teams Work

```
Team Created
    ↓
Auto-create "general" channel
    ↓
Users join team (via invite code or admin invite)
    ↓
Users added to team_members table
    ↓
Users can see all team channels
    ↓
Users can send messages to channels
```

### Team Invite Code

**Why?**  
- Easy way for new members to join
- No need for admin to manually add everyone
- 8 random characters (e.g., "K3DM9XLZ")

**How it works:**
```
1. Team created with random code
2. User gets code (from team page)
3. New user enters code on /join-team page
4. System checks: Code exists? Is team active?
5. Add user to team_members table
6. Done! User can now see team's messages
```

**Database query:**
```python
team = Team.query.filter_by(team_code='K3DM9XLZ').first()
# Find user
user = User.query.filter_by(username='john').first()
# Add user to team
tm = TeamMember(team_id=team.id, user_id=user.id, role_id=member_role.id)
db.session.add(tm)
db.session.commit()
```

### Channels

**What are channels?**  
Separate conversation threads within a team (like Discord or Slack)

**Example:**
- Team: "Computer Science Class"
  - Channel 1: #general (main discussion)
  - Channel 2: #announcements (teacher posts important news)
  - Channel 3: #project-help (students ask questions)

**Why organize this way?**
- Reduces message clutter
- Users can mute channels they don't follow
- Easy to find specific conversation topics

---

## 💬 Messaging - How Conversations Work

### Channel Messages (Team Conversations)

```
User types message in #general
        ↓
Clicks Send button
        ↓
JavaScript sends POST /messages/send
        ↓
Backend checks:
  - Is user logged in?
  - Is user in this team?
  - Is message not empty?
        ↓
Create Message record:
  - content: "Hello everyone!"
  - channel_id: 1
  - sender_id: current_user.id
  - created_at: now
        ↓
Save to database
        ↓
Page refreshes/updates with new message
```

**Code flow in `app/routes/message_routes.py`:**
```python
@bp.route('/messages/channel/<int:channel_id>/send', methods=['POST'])
@login_required  # Must be logged in
def send_message(channel_id):
    channel = Channel.query.get(channel_id)
    if not channel:
        return error("Channel not found")
    
    # Check user is in the team
    team = channel.team
    if not current_user in team.members:
        return error("You're not in this team")
    
    message_text = request.form.get('content')
    if not message_text:
        return error("Message can't be empty")
    
    # Create and save message
    msg = Message(
        content=message_text,
        channel_id=channel_id,
        sender_id=current_user.id
    )
    db.session.add(msg)
    db.session.commit()
    
    return {"success": True, "message_id": msg.id}
```

### Direct Messages (Private Chats)

```
User clicks "Message" on another user's profile
        ↓
Opens 1-on-1 chat
        ↓
User types message
        ↓
Creates DirectMessage record:
  - content: message text
  - sender_id: current user
  - recipient_id: other user
  - is_read: false (until recipient opens it)
        ↓
Other user sees notification
        ↓
Clicks notification → Opens chat
        ↓
Message marked as read
```

**Key difference from channel messages:**
- Only between 2 people (not team-wide)
- Private (no one else can see)
- Tracks if read or not

---

## 📁 File Sharing - How Uploads Work

### Upload Security (Important!)

```
User selects file to upload
        ↓
Frontend checks:
  - File type allowed? (not .exe, .zip, etc)
  - File size < 16MB?
        ↓
User clicks Upload
        ↓
Backend checks AGAIN:
  - File type allowed?
  - File size < 16MB?
  - User is in team?
        ↓
Save file to /uploads folder
        ↓
Create File record in database:
  - filename: original name
  - filepath: where we saved it
  - file_size: how big
  - mime_type: image/jpeg, etc
  - uploaded_by_id: who uploaded
  - team_id: which team
        ↓
Return to user with success message
```

**Why check twice (frontend AND backend)?**
- Frontend check: Fast feedback to user
- Backend check: Security! User could bypass frontend
- Always validate on server-side

**Allowed file types:**
```
Documents: .pdf, .doc, .docx, .xls, .xlsx, .ppt, .pptx, .txt
Images: .png, .jpg, .jpeg, .gif
Archives: .zip
```

**How downloads work:**
```
User clicks download button
        ↓
Backend checks: Is user in the team where file is shared?
        ↓
If yes: Send file to user
If no: Show "Access denied" error
```

---

## ✅ Task Management - Tracking Work

### Creating & Managing Tasks

```
Teacher creates task:
  - Title: "Submit Assignment 1"
  - Description: "Due next Friday"
  - Assigned to: "Student Group A"
  - Priority: High
  - Due date: June 15, 2026
  - Status: Todo
        ↓
Task stored in database
        ↓
Student receives notification: "New task assigned to you"
        ↓
Student clicks on task
        ↓
Status changed: Todo → In Progress → Done
        ↓
Each status change sends notification to creator
        ↓
Task appears in history with completion timestamp
```

**Task Statuses:**
- `todo`: Not started
- `in_progress`: Currently working on it
- `done`: Completed

**Why this helps:**
- Teacher can track who's done what
- Students know exactly what they need to do
- Creates accountability and organization

---

## 🔔 Notifications - Stay Updated

### Types of Notifications

| Event | Notification |
|-------|-----------|
| Someone mentions you (@username) | "John mentioned you in #general" |
| Task assigned to you | "New task: Submit Project Report" |
| Someone sends you a DM | "Sarah sent you a private message" |
| Task status updated | "Task: Assignment 1 status changed to Done" |
| Team invitation received | "You've been invited to 'Engineering Team'" |
| New group call | "Group call in Engineering Team" |

**How it works:**
```
Event happens (mention, task assign, etc)
        ↓
Create Notification record:
  - user_id: who should see it
  - type: what kind of event
  - title: "You were mentioned"
  - message: "John mentioned you in #general"
  - related_id: message ID for linking
  - is_read: false (not read yet)
        ↓
User clicks notification bell
        ↓
Shows list of unread notifications
        ↓
User clicks notification → Goes to that message/task
        ↓
Mark notification as read
```

---

## 📞 Video Calling - Real-Time Communication

### How Video Calls Work (1-to-1)

```
User clicks "Call" on another user's profile
        ↓
Create Call record:
  - caller_id: user initiating
  - callee_id: person being called
  - status: pending
  - call_token: unique session ID
        ↓
Send notification to other user: "John is calling you"
        ↓
Their browser rings (notification sound + popup)
        ↓
User clicks Answer or Reject
        ↓
If Answer:
  - status changes to: active
  - Both browsers open call room
  - WebRTC negotiates peer-to-peer connection
  - Video streams setup
        ↓
If Reject:
  - status changes to: rejected
  - Caller gets "Call rejected" message
        ↓
Call ends:
  - Calculate duration
  - Save call transcripts
  - Generate summary
  - Change status to: completed
```

### How Group Calling Works (2-8 People)

```
Team has 3 members: Alice, Bob, Charlie
        ↓
Alice clicks "Start Group Call" in team view
        ↓
Backend checks:
  - Alice is in team? ✓
  - Team has 2+ members? ✓
        ↓
Create Call record:
  - call_type: 'group'
  - team_id: 1
  - caller_id: Alice
  - status: pending
        ↓
Create CallParticipant records for all:
  - Call 1 → Alice
  - Call 1 → Bob
  - Call 1 → Charlie
        ↓
Send notifications to Bob and Charlie:
  "Group call started in Team Name"
        ↓
All three open call room page
        ↓
Grid layout shows 3 video boxes
        ↓
WebRTC mesh network:
  - Alice connects to Bob
  - Alice connects to Charlie
  - Bob connects to Charlie
  - Everyone can see everyone ✓
        ↓
Call ends:
  - Record who joined, when they left
  - Calculate individual durations
  - Generate group summary
```

**Why group calls need CallParticipant table:**
- Different participants in different calls
- Track who's actually in the call
- Calculate per-person duration
- Future: Track mute status, role, etc

### Call Transcription (Automatic)

```
During call, browser captures speech
        ↓
Web Speech API converts audio → text
        ↓
Segments sent to CallTranscript table:
  - call_id: 42
  - speaker_id: Alice
  - text: "Let's discuss the project"
  - timestamp: 12:34:56
        ↓
After call ends:
  - Extractive summarization algorithm runs
  - Identifies key sentences
  - Creates summary:
    "Project deadline: Friday. Team assigned..."
        ↓
Summary saved to Call.summary field
```

**Extractive vs Abstractive Summarization:**
- **Extractive**: Pick key sentences as-is (no ML needed) ✓ Used here
- **Abstractive**: Paraphrase and generate new text (needs AI/ML)

We use extractive because:
- Works without external APIs
- Educational - shows algorithm logic
- Suitable for student project

---

## 🎨 Frontend - What Users See

### Page Structure

**Base Template (`templates/base.html`):**
```html
<!DOCTYPE html>
<html>
  <head>
    Navigation Bar (Top)
    Styles from style.css
  </head>
  <body>
    {% block content %}
      (Other pages extend this)
    {% block %}
  </body>
</html>
```

**All pages extend base.html so they have:**
- Consistent navbar
- Same styles
- Same fonts (Plus Jakarta Sans)
- Same color scheme (Obsidian & Amber theme)

### Color Scheme (Obsidian & Amber)

```css
Primary: #1C1917 (Dark obsidian - backgrounds)
Accent: #D97706 (Amber - buttons, links, highlights)
Text: #374151 (Dark gray - readable)
Background: #FAF9F7 (Warm cream - easy on eyes)
```

**Why this scheme?**
- High contrast (readable for everyone)
- Professional look
- Warm tones (not harsh blues)
- Consistent branding

### Responsive Design

```css
Mobile (< 768px):   Single column, touch-friendly buttons
Tablet (768-1024px): Two columns
Desktop (> 1024px):  Three columns
```

**Example: Message list**
```
Mobile:
┌─────────────┐
│   Message   │
│  (full row) │
├─────────────┤
│   Message   │
│  (full row) │
└─────────────┘

Desktop:
┌──────────────┬──────────────┬──────────────┐
│  Message 1   │  Message 2   │  Message 3   │
├──────────────┼──────────────┼──────────────┤
│  Message 4   │  Message 5   │  Message 6   │
└──────────────┴──────────────┴──────────────┘
```

---

## 🛠️ How Data Flows Through the System

### Example: Sending a Channel Message

**User's perspective:**
```
1. Open Teams website
2. Click on "Engineering Team" team
3. Click on "#general" channel
4. Type "Hello team!" in message box
5. Click Send button
6. See message appear in chat
```

**Behind the scenes (Technical):**

```
Step 1-3: User navigates to /messages/channel/1
  → Flask renders templates/messages/channel.html
  → Shows all existing messages in channel
  → Shows message compose box

Step 4-5: User types and clicks Send
  → JavaScript event listener captures click
  → Sends AJAX POST to /messages/channel/1/send
  → Body: {"content": "Hello team!"}

Backend receives POST:
  1. Check if user is logged in (@login_required)
  2. Query database: User.query.get(current_user.id)
  3. Check if channel exists: Channel.query.get(1)
  4. Check if user is in channel's team
  5. Validate message is not empty
  6. Create new Message object:
     msg = Message(
       content="Hello team!",
       channel_id=1,
       sender_id=current_user.id,
       created_at=now()
     )
  7. Add to session: db.session.add(msg)
  8. Commit to database: db.session.commit()
  9. Return JSON: {"status": "success", "message_id": 123}

Frontend receives response:
  1. Check status: success ✓
  2. Create HTML for new message:
     <div class="message">
       <strong>your_username</strong>
       <p>Hello team!</p>
       <span>12:34 PM</span>
     </div>
  3. Insert at bottom of message list
  4. Scroll to show new message
  5. Clear text box
```

**How do multiple users see the message?**
```
User A posts message
  ↓
Saved to database
  ↓
User B refreshes page
  ↓
Backend queries database for all messages
  ↓
Database returns including new message from User A
  ↓
Page displays it
```

**Real-time updates (without refresh):**
```
For future enhancement: Use WebSockets
- User A sends message
- Server broadcasts to all users in channel
- Their pages update instantly (no refresh needed)
```

---

## 📈 User Journey - Common Workflows

### Workflow 1: Teacher Creates a Class Team

```
1. Login to website
2. Click "Create Team"
3. Fill form:
   - Team Name: "Computer Science 101"
   - Description: "Data structures and algorithms"
4. Click Create
5. System auto-creates #general channel
6. Gets team code: "K3DM9XLZ"
7. Teacher shares code with students
8. Students enter code to join
9. Team now has all members
```

### Workflow 2: Student Submits Assignment

```
1. Teacher creates task: "Submit Project"
2. Task appears in #announcements channel
3. Student sees notification: "New task assigned"
4. Student clicks task to see details
5. Student uploads their project file
6. Comments on task: "Submitted!"
7. Marks status: Todo → In Progress → Done
8. Teacher gets notification: "Task completed"
9. Teacher reviews submission
10. Comments back with feedback
```

### Workflow 3: Group Study Session

```
1. Students need to discuss group project
2. Click "Start Group Call" in team
3. All team members get notification
4. Click to join call
5. Can see each other's video
6. Share screens to show code
7. Transcription auto-records discussion
8. After call: Can read transcript summary
9. Record shows who attended and for how long
```

---

## 🧪 Testing - How We Know It Works

### What We Tested

| Feature | How We Test | What We Look For |
|---------|-----------|------------------|
| Registration | Fill form, submit | User created in DB, can login |
| Login | Enter credentials | Session created, redirected to dashboard |
| Team creation | Create team | Team appears in list, invite code generated |
| Joining team | Enter invite code | User added to team, can see messages |
| Sending message | Type and send | Message in database and page |
| File upload | Pick file, upload | File saved, appears in list, can download |
| Task creation | Create task with details | Task appears with correct status |
| Video calling | Click call button | Call room opens, WebRTC ready |

### Manual Testing Process

```
1. Start fresh database (delete old database file)
2. Register new user: "testuser"
3. Create team: "Engineering"
4. Send message: "Hello world"
5. Upload file: Test PDF
6. Create task: "Do homework"
7. Test all buttons and links
8. Check database records created correctly
9. Check no JavaScript errors in console
10. Test on mobile (responsive design)
```

**Browser Console Check:**
```
Press F12 → Console tab
Look for: Any red errors?
If no red errors → Good! ✓
```

---

## 🔄 Architecture Overview

### Request-Response Cycle

```
User Action (click button, type, etc)
        ↓
Browser sends HTTP request
  GET /teams/1/members
  POST /messages/send
  etc
        ↓
Flask receives request
  └─ Check if request is valid
  └─ Check if user is logged in
  └─ Check if user has permission
        ↓
Execute business logic
  └─ Query database
  └─ Create/update records
  └─ Calculate values
        ↓
Return response
  - HTML page (render template)
  - JSON data (API)
  - Redirect to another page
        ↓
Browser receives response
  └─ If HTML: Render page
  └─ If JSON: Update page with JavaScript
  └─ If redirect: Navigate to new URL
        ↓
User sees result
```

### Code Organization

```
app.py
  └─ Entry point, runs Flask

config.py
  └─ Settings (database, secret key, etc)

app/__init__.py
  └─ Flask app factory, initialize extensions

app/models/models.py
  └─ Database models (User, Team, Message, etc)
  └─ Relationships between models
  └─ Database schema definition

app/routes/
  ├─ auth_routes.py (login, register, profile)
  ├─ team_routes.py (create team, join, settings)
  ├─ message_routes.py (send message, edit, delete)
  ├─ file_routes.py (upload, download files)
  ├─ task_routes.py (create, assign, complete tasks)
  ├─ call_routes.py (initiate calls, room rendering)
  └─ dashboard_routes.py (home page, overview)

app/socket_events.py
  └─ WebSocket handlers (real-time signaling for calls)

templates/
  ├─ base.html (master layout)
  ├─ auth/ (login, register, profile pages)
  ├─ teams/ (team pages)
  ├─ messages/ (chat pages)
  ├─ files/ (file list)
  ├─ tasks/ (task pages)
  └─ calls/ (call room)

static/
  ├─ css/style.css (all styling)
  ├─ js/video-call.js (WebRTC client code)
  └─ images/ (logos, icons)
```

---

## 🔮 Future Enhancements

### Phase 2 (Recommended)
- Email verification for registration
- Password reset via email
- Screen sharing during calls
- Call recording (save video + audio)
- Advanced search with filters

### Phase 3 (Advanced)
- Mobile apps (iOS, Android)
- Push notifications
- Analytics dashboard
- Admin panel
- API for third-party integrations

### Phase 4 (Research Ideas)
- AI summaries using GPT
- Sentiment analysis of messages
- Suggested group members
- Automatic meeting scheduling
- Real-time collaborative editing

---

## 💡 Key Security Principles Used

### 1. **Defense in Depth**
- Check permissions at frontend (quick feedback)
- Check permissions at backend (actual security)
- Never trust client

### 2. **Least Privilege**
- Users only see their own data
- Students can't see admin functions
- Members can't modify team settings

### 3. **Input Validation**
- Check all user input
- Validate file types and sizes
- Sanitize special characters

### 4. **Secure Defaults**
- Passwords hashed by default
- Sessions expire automatically
- CSRF tokens on all forms
- SQL queries parameterized

### 5. **Fail Securely**
- Errors don't leak sensitive info
- Unknown user? Show "username not found" (not "wrong password")
- File not found? Generic error (not file path)

---

## 📝 How to Explain to Your Supervisor

### Opening Statement

*"I built a web-based collaboration platform like Microsoft Teams. The system has three main layers:*
- *Frontend (what users see): HTML pages with responsive design*
- *Backend (business logic): Flask routes that handle requests*
- *Database (data storage): SQLite with 10 interconnected tables*

*The project demonstrates full-stack development with proper security practices."*

### Key Points to Emphasize

✅ **Security**
- "Passwords are hashed, never stored as plaintext"
- "Every action is checked: Is user logged in? Do they have permission?"
- "Database uses relationships to maintain integrity"

✅ **Architecture**
- "Code organized into blueprints (routes) for maintainability"
- "Models define database schema and relationships"
- "Application factory pattern allows testing and flexibility"

✅ **User Experience**
- "Responsive design works on mobile and desktop"
- "Real-time features (WebRTC) for video calls"
- "Notifications keep users informed"

✅ **Education Value**
- "Shows I understand web development fundamentals"
- "Demonstrates best practices (no frameworks bloat)"
- "Modular code easy to understand and extend"

### Technical Depth Questions

**Q: How do you prevent SQL injection?**
A: "I use SQLAlchemy ORM which handles parameterized queries. Even if someone enters malicious SQL, it's treated as data, not code."

**Q: How do you handle user authentication?**
A: "Passwords are hashed with PBKDF2 when stored. When logging in, we hash the input and compare. Sessions last 24 hours for security."

**Q: How do video calls work?**
A: "WebRTC is a browser standard for peer-to-peer video. Socket.IO handles signaling (exchanging connection info). For group calls, we create a mesh network where each person connects to everyone else (max 8 people for scalability)."

**Q: Why SQLite instead of PostgreSQL?**
A: "SQLite is file-based, perfect for a student project. No server setup needed. For production, I'd use PostgreSQL for better concurrency."

---

## 📊 Project Statistics

| Metric | Count |
|--------|-------|
| Database Tables | 10 |
| API Endpoints | 38+ |
| HTML Templates | 21 |
| Python Routes (files) | 7 |
| Lines of CSS | 800+ |
| Lines of JavaScript | 500+ |
| Database Models | 10 |
| Total Code | 4,300+ lines |

---

## 🎓 Learning Outcomes Demonstrated

By building this project, I learned:

1. **Web Development**
   - Client-server architecture
   - HTTP methods (GET, POST, PUT, DELETE)
   - RESTful design principles
   - Form validation and security

2. **Database Design**
   - Entity-relationship modeling
   - Normalization (avoiding data duplication)
   - Foreign keys and integrity
   - SQL queries via ORM

3. **Backend Development**
   - Flask framework
   - Routing and request handling
   - Authentication and authorization
   - Error handling

4. **Frontend Development**
   - HTML semantic markup
   - CSS responsive design
   - JavaScript interactivity
   - Form handling

5. **Real-Time Communication**
   - WebRTC for peer-to-peer video
   - Socket.IO for signaling
   - WebSocket protocol

6. **Security**
   - Password hashing
   - Session management
   - CSRF protection
   - Input validation

7. **Software Engineering**
   - Code organization and modularity
   - Version control (Git)
   - Testing and debugging
   - Documentation

---

## ❓ FAQ - Common Questions

**Q: Why not use React or Vue?**
A: "Vanilla JavaScript teaches web fundamentals better. For a student project, frameworks add unnecessary complexity. I can always add them later if scaling."

**Q: Can this handle 1000 users?**
A: "SQLite works well up to ~100 concurrent users. For 1000+, I'd need:
- PostgreSQL for better concurrency
- Caching layer (Redis)
- Load balancer
- That's scaling knowledge for Phase 2!"

**Q: Is this production-ready?**
A: "Not quite. To deploy:
- Set SECRET_KEY from strong random value
- Use PostgreSQL instead of SQLite
- Enable HTTPS (secure cookies)
- Setup monitoring/logging
- Add rate limiting
But architecturally, it's solid!"

**Q: How do you handle concurrent users?**
A: "Each user gets a session. Database transactions ensure data consistency. For real-time updates, Socket.IO will help in Phase 2."

**Q: What if the database corrupts?**
A: "SQLite is resilient, but in production I'd:
- Regular backups
- Replication across servers
- Transaction logs
- Checksums to detect corruption"

---

**End of Explanation Guide**

*This document should help you explain any part of the project to your teacher. Feel free to reference code files when needed!*
