# Frontend Explanation - HTML, CSS, JavaScript

**This explains: How users see and interact with the website**

---

## 1. Page Structure: Jinja2 Template Inheritance

### Base Template (`templates/base.html`)

```html
<!DOCTYPE html>
<html>
<head>
    <!-- All pages inherit this navigation and styling -->
    <title>{% block title %}Team Hub{% endblock %}</title>
    
    <!-- CSS styling -->
    <link rel="stylesheet" href="/static/css/style.css">
    
    <!-- Font -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans" rel="stylesheet">
    <!-- ^^ Plus Jakarta Sans font used throughout -->
</head>
<body>
    <!-- Navigation bar (appears on EVERY page) -->
    <nav class="navbar">
        <a href="/dashboard" class="logo">
            <span class="logo-icon">TH</span>
            <span class="logo-text">Team Hub</span>
        </a>
        
        <!-- Navigation links -->
        <ul class="nav-links">
            <li><a href="/dashboard">Dashboard</a></li>
            <li><a href="/teams">Teams</a></li>
            <li><a href="/messages/direct">Private Chat</a></li>
            <li><a href="/calls/history">Call History</a></li>
            <li><a href="/notifications">Notifications</a></li>
        </ul>
        
        <!-- User menu -->
        <div class="user-menu">
            <span>👤 {{ current_user.username }}</span>
            <a href="/auth/logout">Logout</a>
        </div>
    </nav>
    
    <!-- Main content area (different for each page) -->
    <main class="content">
        {% block content %}
            (Child template puts content here)
        {% endblock %}
    </main>
    
    <!-- Flash messages (errors, success, etc) -->
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash flash-{{ category }}">
                    {{ message }}
                </div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    
    <!-- JavaScript loaded at bottom (better performance) -->
    <script src="/static/js/main.js"></script>
</body>
</html>

<!-- 
Why inherit from base.html?
- DRY principle: Don't Repeat Yourself
- Navigation appears on every page without copying code
- Change navigation once = changes everywhere
- All pages have consistent styling
-->
```

### Child Template Example (`templates/teams/view.html`)

```html
<!-- This page extends base.html -->
{% extends "base.html" %}

<!-- Set page title -->
{% block title %}{{ team.name }} - Team Hub{% endblock %}

<!-- Content for this page -->
{% block content %}
<div class="team-container">
    <h1>{{ team.name }}</h1>
    
    <!-- Call button (NEW!) -->
    <button onclick="startGroupCall({{ team.id }})" class="btn btn-primary">
        📞 Start Group Call
    </button>
    <!-- ^^ When clicked, starts a video call with all team members -->
    
    <!-- Channels -->
    <div class="channels-list">
        {% for channel in team.channels %}
            <a href="/messages/channel/{{ channel.id }}" class="channel-link">
                # {{ channel.name }}
            </a>
        {% endfor %}
    </div>
</div>
{% endblock %}

<!--
How template variables work:
- {{ team.name }} = Python variable "team.name"
- {% for channel in team.channels %} = Loop through channels
- {% if user.is_admin %} = Conditional rendering
- Flask automatically escapes HTML (XSS protection)
-->
```

---

## 2. HTML Forms - How Data Gets to Backend

### Example: Sending a Message

```html
<!-- User sees this form -->
<form action="/messages/channel/{{ channel.id }}/send" method="POST" id="messageForm">
    <!-- CSRF token (security!) -->
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <!-- ^^ This prevents fake forms from other websites posting to our server -->
    
    <!-- Message input -->
    <input 
        type="text" 
        name="content" 
        placeholder="Type a message..." 
        required
        maxlength="5000"
    >
    <!-- ^^ maxlength on client-side, but we also check on server (defense in depth) -->
    
    <!-- Send button -->
    <button type="submit" class="btn btn-primary">Send</button>
</form>

<script>
// Prevent page reload, send via AJAX instead
document.getElementById('messageForm').addEventListener('submit', async (e) => {
    e.preventDefault()  // Don't reload page
    
    const formData = new FormData(this)
    
    const response = await fetch(
        '/messages/channel/{{ channel.id }}/send',
        {
            method: 'POST',
            body: formData
        }
    )
    
    const data = await response.json()
    
    if (data.success) {
        // Message sent! Update UI
        this.reset()  // Clear input
        loadMessages()  // Reload message list
    } else {
        alert('Error: ' + data.error)
    }
})
</script>

<!--
Flow:
1. User types message
2. User clicks Send button
3. JavaScript prevents page reload (e.preventDefault())
4. JavaScript sends AJAX POST request with message content
5. Backend processes, saves to database, returns JSON
6. JavaScript clears input box and reloads messages
7. New message appears without page reload ✓
-->
```

---

## 3. CSS Styling - Visual Design

### Color Scheme (Obsidian & Amber)

```css
/* Root variables - used throughout the app */
:root {
    /* Primary colors */
    --primary-dark: #1C1917;      /* Obsidian (dark backgrounds) */
    --primary-accent: #D97706;    /* Amber (buttons, highlights) */
    --primary-light: #5B5BD6;     /* Indigo (secondary accent) */
    
    /* Neutral colors */
    --bg-light: #FAF9F7;          /* Warm cream (page background) */
    --text-dark: #374151;         /* Dark gray (readable text) */
    --text-light: #9CA3AF;        /* Light gray (secondary text) */
    --border-color: #E5E7EB;      /* Light border */
    
    /* Status colors */
    --success: #10B981;           /* Green (success messages) */
    --error: #EF4444;             /* Red (errors) */
    --warning: #F59E0B;           /* Yellow (warnings) */
    --info: #3B82F6;              /* Blue (info) */
}

/* Why CSS variables?
   - Change color once, updates everywhere
   - Easy to create themes (light/dark mode)
   - Readable: --primary-accent instead of #D97706
*/

/* Button styling */
.btn {
    padding: 12px 24px;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    cursor: pointer;
    transition: all 0.3s ease;  /* Smooth animations */
    /* ^^ When button changes, transition smoothly */
}

.btn-primary {
    background: linear-gradient(135deg, var(--primary-accent), #EC4899);
    /* ^^ Gradient = two colors blended diagonally */
    color: white;
    font-weight: 600;
}

.btn-primary:hover {
    transform: translateY(-2px);  /* Move up slightly */
    box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);  /* Drop shadow */
    /* ^^ Gives 3D depth effect when hovering */
}

.btn-primary:active {
    transform: translateY(0);  /* Move back down when clicked */
}

/* Responsive design */
@media (max-width: 768px) {
    /* On mobile screens (< 768px width): */
    
    .container {
        padding: 16px;  /* Smaller padding on mobile */
    }
    
    .btn {
        padding: 10px 16px;  /* Smaller buttons */
        font-size: 14px;
    }
    
    /* Single column layout instead of multiple columns */
    .grid {
        grid-template-columns: 1fr;  /* 1 column on mobile */
    }
}

@media (min-width: 1024px) {
    /* On desktop (> 1024px width): */
    
    .grid {
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        /* ^^ Auto-fit 3+ columns on desktop */
    }
}
```

### Layout Example: Message List

```css
/* Container for messages */
.messages-container {
    display: flex;           /* Use flexbox layout */
    flex-direction: column;  /* Stack vertically */
    gap: 16px;              /* Space between items */
    max-height: 600px;      /* Don't make too tall */
    overflow-y: auto;       /* Scrollable if too many messages */
}

/* Individual message */
.message {
    background: white;
    border-left: 4px solid var(--primary-accent);  /* Accent bar */
    padding: 16px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* Message sender name (bold) */
.message-sender {
    font-weight: 700;
    color: var(--primary-dark);
    margin-bottom: 8px;
}

/* Message content */
.message-content {
    color: var(--text-dark);
    line-height: 1.5;  /* Spacing between lines */
    word-wrap: break-word;  /* Break long words */
}

/* Message timestamp (smaller, gray) */
.message-time {
    font-size: 12px;
    color: var(--text-light);
    margin-top: 8px;
}

/* Hover effect */
.message:hover {
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);  /* Stronger shadow */
    transform: translateX(2px);  /* Slight shift right */
}

/*
Why these styles?
- Flexbox: Easy responsive layout
- Gap: Spacing without margins
- overflow-y: auto: Scrollable message list
- Border-left: Visual indicator of messages
- Hover effects: Gives feedback to user
*/
```

---

## 4. JavaScript - User Interactivity

### Form Validation (Client-side)

```javascript
// Validate registration form BEFORE sending to server
function validateRegistrationForm(form) {
    const username = form.username.value.trim()
    const email = form.email.value.trim()
    const password = form.password.value
    const passwordConfirm = form.password_confirm.value
    
    // Check username
    if (username.length < 3) {
        alert('Username must be at least 3 characters')
        return false  // Don't submit form
    }
    
    // Check email format
    if (!email.includes('@')) {
        alert('Enter a valid email address')
        return false
    }
    
    // Check password length
    if (password.length < 8) {
        alert('Password must be at least 8 characters')
        return false
    }
    
    // Check passwords match
    if (password !== passwordConfirm) {
        alert('Passwords do not match')
        return false
    }
    
    // All checks passed, submit form
    return true
}

// Use in HTML:
// <form onsubmit="return validateRegistrationForm(this)">

/*
Why validate on client-side?
- Fast feedback (no server round-trip)
- Better user experience
- Saves server resources

But ALWAYS validate on server too!
- User could bypass JavaScript
- Defense in depth
*/
```

### Sending Messages (AJAX)

```javascript
async function sendMessage(channelId) {
    // Get message from input
    const messageInput = document.getElementById('messageInput')
    const content = messageInput.value.trim()
    
    // Validate
    if (!content) {
        alert('Message cannot be empty')
        return
    }
    
    if (content.length > 5000) {
        alert('Message too long (max 5000 characters)')
        return
    }
    
    try {
        // Show loading state
        const button = event.target
        button.disabled = true
        button.textContent = 'Sending...'
        
        // Send to server via AJAX (no page reload)
        const response = await fetch(
            `/messages/channel/${channelId}/send`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: content,
                    // CSRF token for security
                    'csrf_token': document.querySelector('input[name="csrf_token"]').value
                })
            }
        )
        
        // Parse response
        const data = await response.json()
        
        if (!response.ok) {
            // Server returned error
            alert(`Error: ${data.error}`)
            return
        }
        
        // Success! Clear input
        messageInput.value = ''
        
        // Reload messages to show new one
        loadMessages(channelId)
        
    } catch (error) {
        // Network error
        console.error('Failed to send message:', error)
        alert('Network error. Try again.')
    } finally {
        // Restore button
        button.disabled = false
        button.textContent = 'Send'
    }
}

/*
What's happening:
1. Get message from input
2. Validate on client-side (quick)
3. Show loading state (feedback to user)
4. Send AJAX request (no reload)
5. Check response status
6. If error: show error message
7. If success: clear input and reload messages
8. Handle network errors gracefully
*/
```

### Video Call JavaScript

```javascript
// When user clicks "Start Group Call" button
async function startGroupCall(teamId) {
    try {
        // Send request to backend
        const response = await fetch(
            `/calls/group/${teamId}/initiate`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            }
        )
        
        const data = await response.json()
        
        if (!response.ok) {
            // Something went wrong
            alert(data.error || 'Failed to start group call')
            return
        }
        
        // Backend returns: call_token, team_name, participants
        console.log('Group call started!')
        console.log('Call token:', data.call_token)
        console.log('Participants:', data.participants)
        
        // Redirect to call room
        window.location.href = `/calls/room/${data.call_token}`
        // ^^ User now sees the group video call interface
        
    } catch (error) {
        console.error('Error starting call:', error)
        alert('Failed to start group call')
    }
}

// In the call room page: setup WebRTC
class VideoCallClient {
    constructor(callToken, callType) {
        this.callToken = callToken
        this.callType = callType  // 'one-to-one' or 'group'
        
        // Get video elements
        this.localVideo = document.getElementById('localVideo')
        this.remoteVideo = document.getElementById('remoteVideo')
        
        // For group calls: array of remote videos
        this.remoteVideos = {}  // { user_id: videoElement }
        
        // WebRTC peer connection
        this.peerConnection = null
        
        // Connect to Socket.IO for signaling
        this.socket = io()
        this.setupSocketListeners()
    }
    
    setupSocketListeners() {
        // When another user sends offer (wants to connect)
        this.socket.on('offer', async (data) => {
            console.log('Received offer from:', data.from)
            // Create peer connection and send answer back
            await this.handleOffer(data)
        })
        
        // When we receive answer to our offer
        this.socket.on('answer', async (data) => {
            console.log('Received answer')
            // Complete connection setup
            this.peerConnection.setRemoteDescription(
                new RTCSessionDescription(data.answer)
            )
        })
        
        // ICE candidate (address information for connection)
        this.socket.on('ice-candidate', (data) => {
            if (data.candidate) {
                this.peerConnection.addIceCandidate(
                    new RTCIceCandidate(data.candidate)
                )
            }
        })
    }
    
    async startCall() {
        try {
            // Request camera/microphone access
            const stream = await navigator.mediaDevices.getUserMedia({
                video: true,
                audio: true
            })
            
            // Show our video
            this.localVideo.srcObject = stream
            
            // Create WebRTC connection with remote user(s)
            this.peerConnection = new RTCPeerConnection({
                iceServers: [
                    { urls: 'stun:stun.l.google.com:19302' },
                    { urls: 'stun:stun1.l.google.com:19302' }
                ]
                /* ^^ STUN servers: help find our public IP address
                   Needed for peer-to-peer connection through NAT/firewall */
            })
            
            // Add our stream to connection
            stream.getTracks().forEach(track => {
                this.peerConnection.addTrack(track, stream)
            })
            
            // When we get remote stream
            this.peerConnection.ontrack = (event) => {
                console.log('Received remote stream')
                this.remoteVideo.srcObject = event.streams[0]
            }
            
            // When we find our public address (ICE candidate)
            this.peerConnection.onicecandidate = (event) => {
                if (event.candidate) {
                    // Send to other user via Socket.IO
                    this.socket.emit('ice-candidate', {
                        to: this.remoteUserId,
                        candidate: event.candidate
                    })
                }
            }
            
            // Create offer and send to other user
            const offer = await this.peerConnection.createOffer()
            await this.peerConnection.setLocalDescription(offer)
            
            this.socket.emit('offer', {
                to: this.remoteUserId,
                offer: offer
            })
            
        } catch (error) {
            console.error('Error starting call:', error)
            if (error.name === 'NotAllowedError') {
                alert('Please allow camera/microphone access')
            }
        }
    }
}

// In HTML:
// <script>
//   const client = new VideoCallClient('token-123', 'group')
//   client.startCall()
// </script>

/*
How WebRTC works:
1. Each browser creates RTCPeerConnection
2. Exchanges "offer" and "answer" via Socket.IO (signaling)
3. Exchanges ICE candidates (public addresses)
4. Direct peer-to-peer connection established
5. Video/audio streams flow directly between peers
6. Not through server (server only helps negotiate)
7. Better performance, lower latency ✓
*/
```

---

## 5. Responsive Design - Mobile to Desktop

### Mobile Layout (< 768px)

```css
/* Single column on mobile */
.team-container {
    display: grid;
    grid-template-columns: 1fr;  /* 1 column */
    gap: 16px;
    padding: 16px;
}

.navbar {
    flex-direction: column;  /* Stack vertically */
    padding: 8px;
}

.messages-list {
    max-height: 400px;  /* Smaller on mobile */
    font-size: 14px;    /* Smaller text */
}

/* Large touch targets (min 44px for accessibility) */
.btn {
    padding: 12px;
    min-height: 44px;
    width: 100%;  /* Full width on mobile */
}
```

### Desktop Layout (> 1024px)

```css
/* Multiple columns on desktop */
.team-container {
    display: grid;
    grid-template-columns: 250px 1fr;  /* Sidebar + content */
    gap: 24px;
    padding: 24px;
    max-width: 1400px;
    margin: 0 auto;
}

.navbar {
    flex-direction: row;  /* Horizontal */
    padding: 16px 24px;
    justify-content: space-between;
}

.messages-list {
    max-height: 800px;
    font-size: 16px;
}

.btn {
    width: auto;  /* Don't stretch on desktop */
    padding: 12px 24px;
}
```

### Tablet Layout (768px - 1024px)

```css
/* Hybrid layout */
.team-container {
    display: grid;
    grid-template-columns: 200px 1fr;  /* Smaller sidebar */
    gap: 16px;
    padding: 16px;
}
```

---

## 6. Common Frontend Patterns

### Pattern 1: Flash Messages

```html
<!-- In base.html template: -->
{% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
        {% for category, message in messages %}
            <div class="flash flash-{{ category }}">
                {{ message }}
                <span onclick="this.parentElement.style.display='none'" class="close">×</span>
            </div>
        {% endfor %}
    {% endif %}
{% endwith %}

<style>
.flash {
    padding: 16px;
    border-radius: 8px;
    margin: 16px;
    animation: slideIn 0.3s ease;  /* Slide in animation */
}

.flash-success {
    background: #D1FAE5;  /* Light green */
    color: #065F46;      /* Dark green text */
    border: 1px solid #6EE7B7;
}

.flash-error {
    background: #FEE2E2;  /* Light red */
    color: #7F1D1D;      /* Dark red text */
    border: 1px solid #FCA5A5;
}

@keyframes slideIn {
    from {
        transform: translateX(-100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}
</style>

/*
How it works:
1. Backend calls flash('Message', 'success')
2. Template displays flash messages
3. CSS styles based on category (success/error)
4. Animation slides in from left
5. User can click × to close
*/
```

### Pattern 2: Loading State

```javascript
async function doSomething() {
    const button = event.target
    const originalText = button.textContent
    
    // Show loading
    button.disabled = true
    button.innerHTML = '<span class="spinner"></span> Loading...'
    
    try {
        const response = await fetch('/api/endpoint')
        const data = await response.json()
        
        // Success
        alert('Done!')
        
    } catch (error) {
        console.error(error)
        alert('Error!')
        
    } finally {
        // Restore button
        button.disabled = false
        button.textContent = originalText
    }
}

<style>
/* Spinner animation */
.spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid #f3f3f3;
    border-top: 2px solid #D97706;  /* Amber */
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
</style>

/*
Why loading states?
- User knows something is happening
- Prevents double-click (button disabled)
- Professional UX
- Reduces confusion
*/
```

### Pattern 3: Modal Dialog

```html
<!-- Modal (hidden by default) -->
<div id="deleteModal" class="modal" style="display: none;">
    <div class="modal-content">
        <h2>Confirm Delete</h2>
        <p>Are you sure? This cannot be undone.</p>
        <div class="modal-buttons">
            <button onclick="closeModal()" class="btn btn-secondary">Cancel</button>
            <button onclick="confirmDelete()" class="btn btn-danger">Delete</button>
        </div>
    </div>
</div>

<style>
.modal {
    position: fixed;  /* Stay in place */
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);  /* Semi-transparent overlay */
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;  /* On top of everything */
}

.modal-content {
    background: white;
    padding: 32px;
    border-radius: 12px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    max-width: 400px;
}
</style>

<script>
function openDeleteModal() {
    document.getElementById('deleteModal').style.display = 'flex'
}

function closeModal() {
    document.getElementById('deleteModal').style.display = 'none'
}

function confirmDelete() {
    // Delete the item
    fetch('/api/delete/123', { method: 'DELETE' })
    closeModal()
}
</script>

/*
Why modals?
- Get user confirmation for dangerous actions
- Prevents accidental deletes
- Modal overlay prevents accidental clicks outside
- Better UX than confirmation dialogs
*/
```

---

## 7. Accessibility - Making Site Usable for Everyone

### Good HTML Practices

```html
<!-- Use semantic HTML -->
<header>
    <h1>Main Title</h1>
    <!-- ^^ h1, h2, etc. structure content for screen readers -->
</header>

<nav>
    <!-- Navigation explicitly marked -->
</nav>

<main>
    <article>
        <!-- Article content -->
    </article>
</main>

<footer>
    <!-- Footer content -->
</footer>

<!-- Form labels -->
<label for="username">Username:</label>
<input id="username" type="text">
<!-- ^^ for= attribute links label to input
     Screen readers read: "Username" before input -->

<!-- Alt text for images -->
<img src="photo.jpg" alt="Team members at meeting">
<!-- ^^ If image doesn't load, alt text shows instead
     Screen readers read this for blind users -->

<!-- Buttons with meaningful text -->
<button>Save</button>      <!-- Good -->
<button>➤</button>         <!-- Bad - arrow means nothing -->

<!-- Links with descriptive text -->
<a href="/docs">Learn more →</a>     <!-- Good -->
<a href="/docs">Click here</a>       <!-- Bad - "click here" not descriptive -->
```

### Keyboard Navigation

```javascript
// Make custom components keyboard accessible

// Space or Enter to activate button
document.getElementById('myButton').addEventListener('keydown', (e) => {
    if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault()
        myButton.click()
    }
})

// Arrow keys to navigate menu
document.getElementById('menu').addEventListener('keydown', (e) => {
    const items = document.querySelectorAll('.menu-item')
    const currentIndex = Array.from(items).indexOf(document.activeElement)
    
    if (e.key === 'ArrowDown') {
        e.preventDefault()
        items[(currentIndex + 1) % items.length].focus()
    } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        items[(currentIndex - 1 + items.length) % items.length].focus()
    }
})

// Esc key to close modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeModal()
    }
})
```

### Color Contrast

```css
/* Good contrast (easy to read) */
.text-dark {
    color: #1C1917;  /* Dark on light background */
    background: #FAF9F7;  /* High contrast ratio */
}

/* Avoid low contrast */
.text-gray {
    color: #D1D5DB;  /* Light gray on white - hard to read!) */
    background: white;
}

/* Use focus styles for keyboard users */
input:focus {
    outline: 3px solid var(--primary-accent);  /* Visible focus */
    outline-offset: 2px;
}

button:focus {
    box-shadow: 0 0 0 3px var(--primary-accent);
}
```

---

## 8. Common Pitfalls to Avoid

### ❌ Pitfall 1: Hardcoded URLs

```javascript
// WRONG - URL not changeable
fetch('http://localhost:5000/api/messages')

// RIGHT - Use relative URLs or variables
fetch('/api/messages')  // Works even if port changes
```

### ❌ Pitfall 2: No Error Handling

```javascript
// WRONG - If something fails, nothing happens
const response = await fetch('/api/data')
const data = response.json()
useData(data)  // Might crash if data is null

// RIGHT - Handle errors
try {
    const response = await fetch('/api/data')
    if (!response.ok) throw new Error(response.statusText)
    const data = await response.json()
    useData(data)
} catch (error) {
    console.error('Failed to load data:', error)
    showErrorMessage('Could not load data. Try again.')
}
```

### ❌ Pitfall 3: No Loading States

```javascript
// WRONG - User doesn't know if it's working
button.onclick = async () => {
    const result = await fetch('/api/slowOperation')
    // Takes 5 seconds, user thinks nothing happened!
}

// RIGHT - Show feedback
button.onclick = async () => {
    button.disabled = true
    button.textContent = 'Processing...'
    
    const result = await fetch('/api/slowOperation')
    
    button.disabled = false
    button.textContent = 'Done!'
}
```

### ❌ Pitfall 4: Trusting User Input

```javascript
// WRONG - XSS vulnerability!
const username = getUserInput()
document.getElementById('welcome').innerHTML = `Welcome ${username}!`
// If username = "<script>alert('hacked')</script>", script runs!

// RIGHT - Use textContent instead of innerHTML
document.getElementById('welcome').textContent = `Welcome ${username}!`
// textContent treats input as text, not HTML
```

---

**End of Frontend Explanation**

*Use this to explain: How users interact with the website, how styling works, how JavaScript adds interactivity, and how we handle edge cases gracefully.*
