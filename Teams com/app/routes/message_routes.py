"""
Message routes for Team Collaboration Platform.

This module handles all chat flows:
1. Channel messages (team-wide conversation)
2. Direct messages (private 1-to-1)
3. Edit/delete operations with authorization checks
4. Mention detection and notification creation
5. Message search APIs
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, Message, DirectMessage, Channel, Team, User, Notification
from datetime import datetime

# ===== BLUEPRINT SETUP =====
# All endpoints in this file are under /messages/*
bp = Blueprint('messages', __name__, url_prefix='/messages')


def get_recent_dm_contacts(user_id, limit=30):
    """Get recent DM contacts with last message and unread count."""

    # Pull all DMs involving this user, newest first
    dms = DirectMessage.query.filter(
        (DirectMessage.sender_id == user_id) | (DirectMessage.recipient_id == user_id)
    ).order_by(DirectMessage.created_at.desc()).all()

    contacts = []
    seen = set()

    for dm in dms:
        # Determine the "other person" in this DM row
        other_id = dm.recipient_id if dm.sender_id == user_id else dm.sender_id
        if other_id in seen:
            continue

        other_user = User.query.get(other_id)
        if not other_user:
            continue

        # Count unread messages from this specific contact
        unread_count = DirectMessage.query.filter_by(
            recipient_id=user_id,
            sender_id=other_id,
            is_read=False
        ).count()

        contacts.append({
            'user': other_user,
            'last_message': dm,
            'unread_count': unread_count
        })
        seen.add(other_id)

        # Stop once we hit requested limit
        if len(contacts) >= limit:
            break

    return contacts


@bp.route('/direct')
@login_required
def direct_hub():
    """Private chat hub: recent conversations + user discovery."""

    query = request.args.get('q', '').strip()
    results = []

    # Optional user search in DM hub
    if len(query) >= 2:
        results = User.query.filter(
            (User.username.ilike(f'%{query}%')) |
            (User.first_name.ilike(f'%{query}%')) |
            (User.last_name.ilike(f'%{query}%'))
        ).filter(User.id != current_user.id).limit(15).all()

    # Sidebar list of recent conversation partners
    contacts = get_recent_dm_contacts(current_user.id)

    return render_template(
        'messages/direct_hub.html',
        contacts=contacts,
        results=results,
        query=query
    )


@bp.route('/channel/<int:channel_id>')
@login_required
def view_channel(channel_id):
    """
    View channel and messages.
    
    Authorization: Only members of team owning channel can view
    """
    
    channel = Channel.query.get_or_404(channel_id)
    team = channel.team
    
    # Check if user is team member
    if team not in current_user.teams:
        flash('You do not have access to this channel.', 'error')
        return redirect(url_for('dashboard.index'))
    
    # Fetch messages newest-first then reverse for chat-like chronological display
    page = request.args.get('page', 1, type=int)
    messages = Message.query.filter_by(channel_id=channel_id).order_by(
        Message.created_at.desc()
    ).paginate(page=page, per_page=50)
    
    # Pagination query returns descending; reverse list for UI
    messages.items.reverse()
    
    return render_template(
        'messages/channel.html',
        channel=channel,
        team=team,
        messages=messages
    )


@bp.route('/channel/<int:channel_id>/send', methods=['POST'])
@login_required
def send_message(channel_id):
    """
    Send a message to a channel.
    
    Validation:
    - Content required and not empty
    - Content must be < 5000 characters (config)
    - User must be team member
    
    Process:
    1. Validate input
    2. Create Message record
    3. Check for mentions and create notifications
    4. Return success response
    """
    
    channel = Channel.query.get_or_404(channel_id)
    team = channel.team
    
    # Authorization: must belong to team that owns this channel
    if team not in current_user.teams:
        return jsonify({'error': 'Unauthorized'}), 403
    
    content = request.form.get('content', '').strip()
    
    # Validation
    if not content:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    if len(content) > 5000:
        return jsonify({'error': 'Message too long (max 5000 characters)'}), 400
    
    # ===== CREATE MESSAGE =====
    message = Message(
        content=content,
        channel_id=channel_id,
        sender_id=current_user.id
    )
    db.session.add(message)
    db.session.flush()  # Get message ID
    
    # ===== HANDLE @MENTIONS =====
    # Example: "hey @alice please review"
    # -> notify user alice
    mentioned_users = find_mentions(content)
    for user in mentioned_users:
        if user.id != current_user.id:  # Don't notify self
            notification = Notification(
                user_id=user.id,
                type='mentioned',
                title=f'You were mentioned in #{channel.name}',
                message=f'{current_user.username} mentioned you: {content[:50]}...',
                related_id=message.id
            )
            db.session.add(notification)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message_id': message.id,
        'created_at': message.created_at.isoformat()
    })


@bp.route('/<int:message_id>/edit', methods=['POST'])
@login_required
def edit_message(message_id):
    """
    Edit a message (only by sender).
    
    Limitations:
    - Only sender can edit
    - Only recently sent messages can be edited (could add time limit)
    """
    
    message = Message.query.get_or_404(message_id)
    
    # Authorization: only sender
    if message.sender_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    content = request.form.get('content', '').strip()
    
    if not content or len(content) > 5000:
        return jsonify({'error': 'Invalid content'}), 400
    
    # Save edited content and mark as edited for transparency
    message.content = content
    message.is_edited = True
    message.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/<int:message_id>/delete', methods=['POST'])
@login_required
def delete_message(message_id):
    """Delete a message (only by sender or admin)."""
    
    message = Message.query.get_or_404(message_id)
    
    # Authorization
    if message.sender_id != current_user.id:
        # Could check if user is admin, but for now only sender can delete
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Hard-delete row from database
    db.session.delete(message)
    db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/direct/<int:user_id>')
@login_required
def view_dm(user_id):
    """
    View direct message conversation with another user.
    """
    
    other_user = User.query.get_or_404(user_id)
    
    if other_user.id == current_user.id:
        return redirect(url_for('dashboard.index'))
    
    # Get both directions of conversation in one query
    messages = DirectMessage.query.filter(
        ((DirectMessage.sender_id == current_user.id) & (DirectMessage.recipient_id == user_id)) |
        ((DirectMessage.sender_id == user_id) & (DirectMessage.recipient_id == current_user.id))
    ).order_by(DirectMessage.created_at.asc()).all()
    
    # Mark incoming unread messages from this user as read
    DirectMessage.query.filter_by(
        recipient_id=current_user.id,
        sender_id=user_id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()
    
    # Keep contact list visible in DM page sidebar
    contacts = get_recent_dm_contacts(current_user.id)

    return render_template(
        'messages/direct.html',
        other_user=other_user,
        messages=messages,
        contacts=contacts
    )


@bp.route('/direct/<int:user_id>/send', methods=['POST'])
@login_required
def send_dm(user_id):
    """Send a direct message to another user."""
    
    recipient = User.query.get_or_404(user_id)
    
    if recipient.id == current_user.id:
        return jsonify({'error': 'Cannot message yourself'}), 400
    
    content = request.form.get('content', '').strip()
    
    if not content or len(content) > 5000:
        return jsonify({'error': 'Invalid content'}), 400
    
    # Create DM row
    dm = DirectMessage(
        content=content,
        sender_id=current_user.id,
        recipient_id=user_id
    )
    
    # Notify recipient that a new private message arrived
    notification = Notification(
        user_id=user_id,
        type='direct_message',
        title=f'New message from {current_user.username}',
        message=content[:50],
        related_id=dm.id
    )
    
    db.session.add(dm)
    db.session.add(notification)
    db.session.commit()
    
    return redirect(url_for('messages.view_dm', user_id=user_id))


def find_mentions(content):
    """
    Find @mentions in message content.
    
    Returns list of mentioned User objects.
    
    Why return User objects?
    - Can immediately check if they exist
    - Can create notifications with user IDs
    - Handles case-insensitive matching
    """
    import re
    
    # Find @username patterns, where username is made of word chars
    mentions = re.findall(r'@(\w+)', content)
    
    # Resolve usernames to User objects that actually exist
    users = []
    for username in mentions:
        user = User.query.filter_by(username=username).first()
        if user:
            users.append(user)
    
    return users


@bp.route('/api/messages/search')
@login_required
def api_search_messages():
    """API: Search messages in accessible channels."""
    
    query = request.args.get('q', '').strip()
    team_id = request.args.get('team_id', type=int)
    
    if len(query) < 2:
        return jsonify([])
    
    # Restrict search to channels user can access
    q = Message.query.filter(
        Message.channel.has(
            Channel.team.has(
                Team.members.any(id=current_user.id)
            )
        ),
        Message.content.ilike(f'%{query}%')
    )
    
    # Optional scope: single team
    if team_id:
        q = q.filter(Message.channel.has(Channel.team_id == team_id))
    
    # Return newest 20 matches
    messages = q.order_by(Message.created_at.desc()).limit(20).all()
    
    return jsonify([{
        'id': m.id,
        'content': m.content[:100],
        'sender': m.sender.username,
        'channel': m.channel.name,
        'created_at': m.created_at.isoformat()
    } for m in messages])
