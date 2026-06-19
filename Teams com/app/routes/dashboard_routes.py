"""
Dashboard routes for Team Collaboration Platform.

This module powers high-level user views:
1. Main dashboard page
2. Global search page
3. Notifications page
4. Small API endpoint for unread notification count
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, Team, Message, DirectMessage, Channel, Notification, TeamInvitation, Task, Call, CallParticipant

# ===== BLUEPRINT SETUP =====
# Team Com lives under /team-com so it integrates as a section of Teacher Hub.
bp = Blueprint('dashboard', __name__, url_prefix='/team-com')


def _notification_fallback_url(notification_id):
    """Fallback anchor for notifications page when a specific target cannot be resolved."""
    return f"{url_for('dashboard.notifications')}#notification-{notification_id}"


def _resolve_notification_target(notification):
    """Map a notification to the most specific destination URL available."""
    fallback_url = _notification_fallback_url(notification.id)

    # No related object means we can only route back to this notification row.
    if not notification.related_id:
        return fallback_url

    # Channel mention notifications point to a message inside a channel timeline.
    if notification.type == 'mentioned':
        message = Message.query.get(notification.related_id)
        if message and message.channel and message.channel.team in current_user.teams:
            return f"{url_for('messages.view_channel', channel_id=message.channel_id)}#message-{message.id}"
        return fallback_url

    # Direct message notifications point to the 1-to-1 thread with the other user.
    if notification.type == 'direct_message':
        dm = DirectMessage.query.get(notification.related_id)
        if dm and (dm.sender_id == current_user.id or dm.recipient_id == current_user.id):
            other_user_id = dm.sender_id if dm.sender_id != current_user.id else dm.recipient_id
            return f"{url_for('messages.view_dm', user_id=other_user_id)}#dm-{dm.id}"
        return fallback_url

    # Task notifications open the specific task.
    if notification.type in {'task_assigned', 'task_updated'}:
        task = Task.query.get(notification.related_id)
        if task and task.team in current_user.teams:
            return url_for('tasks.view_task', task_id=task.id)
        return fallback_url

    # Team-level notifications open the team workspace.
    if notification.type in {'team_member_joined', 'team_invite_accepted', 'team_invite_declined'}:
        team = Team.query.get(notification.related_id)
        if team and team in current_user.teams:
            return url_for('teams.view_team', team_id=team.id)
        return fallback_url

    # Team invitation notifications remain on notifications page where Accept/Decline actions live.
    if notification.type == 'team_invite':
        return fallback_url

    # Call-related notifications route either to active room or history.
    if notification.type in {'incoming_call', 'group_call', 'call_rejected', 'missed_call'}:
        call = Call.query.get(notification.related_id)
        if not call:
            return url_for('calls.call_history')

        if call.call_type == 'group':
            is_participant = CallParticipant.query.filter_by(
                call_id=call.id,
                user_id=current_user.id
            ).first()
            if is_participant and call.status in {'pending', 'active'}:
                return url_for('calls.call_room', call_token=call.call_token)
            return url_for('calls.call_history')

        is_one_to_one_participant = current_user.id in {call.caller_id, call.callee_id}
        if is_one_to_one_participant and call.status in {'pending', 'active'}:
            return url_for('calls.call_room', call_token=call.call_token)
        return url_for('calls.call_history')

    return fallback_url


@bp.route('/')
@bp.route('/dashboard')
@login_required
def index():
    """
    Main dashboard - shows user's teams and recent messages.
    
    Displays:
    - User's teams (with member count)
    - Recent messages across teams
    - Unread notifications count
    - Direct messages
    """
    
    # Teams current user belongs to (many-to-many relationship)
    user_teams = current_user.teams
    
    # Count unread notifications for header badge
    unread_count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()
    
    # Count unread private messages for dashboard indicators
    unread_dms = DirectMessage.query.filter_by(
        recipient_id=current_user.id,
        is_read=False
    ).count()
    
    # Pull recent channel messages from teams current user can access
    recent_messages = Message.query.filter(
        Message.channel.has(
            Channel.team.has(
                Team.members.any(id=current_user.id)
            )
        )
    ).order_by(Message.created_at.desc()).limit(20).all()
    
    return render_template(
        'dashboard/index.html',
        teams=user_teams,
        recent_messages=recent_messages,
        unread_notifications=unread_count,
        unread_dms=unread_dms
    )


@bp.route('/search')
@login_required
def search():
    """
    Search across messages, files, and tasks.
    
    Query parameters:
    - q: search query
    - type: 'messages', 'files', 'tasks', or 'all'
    """
    
    # Read search query and optional scope
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    results = {}
    
    # Keep UX clean and avoid noisy searches
    if len(query) < 2:
        return render_template('dashboard/search.html', query=query, results=results)
    
    # Search only message content user is authorized to see
    if search_type in ['messages', 'all']:
        messages = Message.query.filter(
            Message.channel.has(
                Channel.team.has(
                    Team.members.any(id=current_user.id)
                )
            ),
            Message.content.ilike(f'%{query}%')
        ).order_by(Message.created_at.desc()).limit(20).all()
        results['messages'] = messages
    
    # TODO: Search files and tasks
    
    return render_template('dashboard/search.html', query=query, results=results)


@bp.route('/notifications')
@login_required
def notifications():
    """Get user's notifications."""
    # Load latest notifications first
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).all()

    # Build lookup of pending invitation objects referenced by team_invite notifications
    pending_invite_ids = {
        n.related_id for n in notifications if n.type == 'team_invite' and n.related_id
    }
    invite_map = {}
    if pending_invite_ids:
        invites = TeamInvitation.query.filter(
            TeamInvitation.id.in_(pending_invite_ids),
            TeamInvitation.status == 'pending'
        ).all()
        invite_map = {inv.id: inv for inv in invites}

    # Precompute navigation links so each notification row can open its exact destination.
    notification_links = {
        n.id: _resolve_notification_target(n)
        for n in notifications
    }

    # Viewing notifications page implies "read"
    Notification.query.filter_by(user_id=current_user.id).update({'is_read': True})
    db.session.commit()

    return render_template(
        'dashboard/notifications.html',
        notifications=notifications,
        invite_map=invite_map,
        notification_links=notification_links
    )


@bp.route('/api/notifications/unread')
@login_required
def api_unread_notifications():
    """API: Get count of unread notifications."""
    # Lightweight endpoint polled by UI badge counters
    unread = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()
    
    return jsonify({'unread_count': unread})
