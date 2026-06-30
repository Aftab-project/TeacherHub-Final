"""
Team routes for Team Collaboration Platform.

Responsibilities in this module:
1. Team CRUD-style actions (create/view/settings)
2. Team membership flows (join, invites, member removal)
3. Team channel creation
4. Invitation accept/decline lifecycle
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import (
    db, Team, TeamMember, Role, Channel, User, Message, Notification, TeamInvitation
)
import string
import random
import re

# ===== BLUEPRINT SETUP =====
# All endpoints in this file are under /teams/*
bp = Blueprint('teams', __name__, url_prefix='/teams')


def generate_team_code(length=8):
    """Generate random team invitation code."""
    # Uppercase letters + digits keeps code short and easy to share verbally
    chars = string.ascii_uppercase + string.digits
    # Retry a few times to avoid collisions on unique team_code.
    for _ in range(10):
        code = ''.join(random.choice(chars) for _ in range(length))
        if not Team.query.filter_by(team_code=code).first():
            return code

    # Fallback in the unlikely case of repeated collisions.
    return ''.join(random.choice(chars) for _ in range(length + 2))


@bp.route('/')
@login_required
def list_teams():
    """List all teams user is a member of."""
    # current_user.teams comes from SQLAlchemy relationship
    teams = current_user.teams
    return render_template('teams/list.html', teams=teams)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_team():
    """
    Create a new team.
    
    Process:
    1. Validate team name and description
    2. Create Team record with current user as owner
    3. Create default 'general' channel
    4. Add owner to team as Admin
    5. Redirect to team page
    
    Why create 'general' channel automatically?
    - Every team should have a default chat channel
    - Consistent user experience
    - Matches Teams/Slack behavior
    """
    
    if request.method == 'POST':
        # Read and normalize form input
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        is_public = request.form.get('is_public') == 'on'
        
        # Validation
        if not name or len(name) < 2 or len(name) > 100:
            flash('Team name must be 2-100 characters.', 'error')
            return redirect(url_for('teams.create_team'))
        
        # ===== CREATE TEAM =====
        team = Team(
            name=name,
            description=description,
            owner_id=current_user.id,
            team_code=generate_team_code(),
            is_public=is_public
        )
        db.session.add(team)
        db.session.flush()  # Gets team.id before final commit
        
        # Every new team starts with #general by default
        general_channel = Channel(
            name='general',
            description='General team discussion',
            team_id=team.id,
            created_by_id=current_user.id
        )
        db.session.add(general_channel)
        
        # Owner is also inserted into TeamMember with admin role
        admin_role = Role.query.filter_by(name='admin').first()
        owner_member = TeamMember(
            team_id=team.id,
            user_id=current_user.id,
            role_id=admin_role.id
        )
        db.session.add(owner_member)
        
        db.session.commit()
        
        flash(f'Team "{name}" created successfully!', 'success')
        return redirect(url_for('teams.view_team', team_id=team.id))
    
    return render_template('teams/create.html')


@bp.route('/<int:team_id>')
@login_required
def view_team(team_id):
    """
    View team details and members.
    
    Authorization: Only team members can view
    """
    
    team = Team.query.get_or_404(team_id)
    
    # Authorization: only members can view team page
    if team not in current_user.teams:
        flash('You are not a member of this team.', 'error')
        return redirect(url_for('teams.list_teams'))
    
    members = TeamMember.query.filter_by(team_id=team_id).all()
    channels = team.channels

    # Determine whether current user can see admin-only controls
    current_tm = TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first()
    is_admin = current_tm and current_tm.role.name == 'admin'

    # Admins can review pending invites they have sent
    pending_invites = TeamInvitation.query.filter_by(
        team_id=team_id, status='pending'
    ).all() if is_admin else []

    return render_template(
        'teams/view.html',
        team=team,
        members=members,
        channels=channels,
        is_admin=is_admin,
        pending_invites=pending_invites
    )


@bp.route('/<int:team_id>/settings', methods=['GET', 'POST'])
@login_required
def team_settings(team_id):
    """
    Team settings - only accessible to admins.
    
    Can update:
    - Team name
    - Team description
    - Public/private visibility
    - Generate new invite code
    """
    
    team = Team.query.get_or_404(team_id)
    
    # Authorization: admin-only settings page
    team_member = TeamMember.query.filter_by(
        team_id=team_id,
        user_id=current_user.id
    ).first()
    
    if not team_member or team_member.role.name != 'admin':
        flash('Only team admins can change settings.', 'error')
        return redirect(url_for('teams.view_team', team_id=team_id))
    
    if request.method == 'POST':
        team.name = request.form.get('name', '').strip()
        team.description = request.form.get('description', '').strip()
        team.is_public = request.form.get('is_public') == 'on'
        
        # Optional action: rotate invite code for security
        if request.form.get('regen_code'):
            team.team_code = generate_team_code()
            flash('Team code regenerated.', 'success')
        
        db.session.commit()
        flash('Team settings updated.', 'success')
        return redirect(url_for('teams.view_team', team_id=team_id))
    
    return render_template('teams/settings.html', team=team)


@bp.route('/<int:team_id>/members')
@login_required
def manage_members(team_id):
    """View and manage team members."""
    
    team = Team.query.get_or_404(team_id)
    
    if team not in current_user.teams:
        flash('You are not a member of this team.', 'error')
        return redirect(url_for('teams.list_teams'))
    
    # Team members list includes role relation for admin/member badges
    members = TeamMember.query.filter_by(team_id=team_id).all()
    
    return render_template('teams/members.html', team=team, members=members)


@bp.route('/<int:team_id>/members/<int:user_id>/remove', methods=['POST'])
@login_required
def remove_member(team_id, user_id):
    """
    Remove a member from team.
    
    Authorization: Admin only
    """
    
    team = Team.query.get_or_404(team_id)
    
    # Check authorization
    current_member = TeamMember.query.filter_by(
        team_id=team_id,
        user_id=current_user.id
    ).first()
    
    if not current_member or current_member.role.name != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    if user_id == team.owner_id:
        return jsonify({'error': 'Cannot remove team owner'}), 400
    
    # Remove membership join-record (not user account)
    member = TeamMember.query.filter_by(
        team_id=team_id,
        user_id=user_id
    ).first_or_404()
    
    db.session.delete(member)
    db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/<int:team_id>/join', methods=['POST'])
@login_required
def join_team(team_id):
    """
    Join a team (if user has valid invite code).
    
    Process:
    1. Verify team exists
    2. Check if user already member
    3. Add user as regular member (not admin)
    4. Create notification
    """
    
    team = Team.query.get_or_404(team_id)
    
    # Allow direct joins only for public teams.
    if not team.is_public:
        flash('This team is private. Use an invite code or invitation.', 'error')
        return redirect(url_for('teams.join_by_code'))

    # Check if already member
    existing = TeamMember.query.filter_by(
        team_id=team_id,
        user_id=current_user.id
    ).first()
    
    if existing:
        flash('You are already a member of this team.', 'info')
        return redirect(url_for('teams.view_team', team_id=team_id))
    
    # Add joining user with default role=member
    member_role = Role.query.filter_by(name='member').first()
    new_member = TeamMember(
        team_id=team_id,
        user_id=current_user.id,
        role_id=member_role.id
    )
    db.session.add(new_member)
    
    # Notify owner so they know team roster changed
    notification = Notification(
        user_id=team.owner_id,
        type='team_member_joined',
        title=f'{current_user.username} joined {team.name}',
        message=f'{current_user.username} has joined your team {team.name}',
        related_id=team_id
    )
    db.session.add(notification)
    
    db.session.commit()
    
    flash(f'You have joined team {team.name}!', 'success')
    return redirect(url_for('teams.view_team', team_id=team_id))


@bp.route('/join-by-code', methods=['GET', 'POST'])
@login_required
def join_by_code():
    """
    Join team using invite code.
    
    Why separate from regular join?
    - Code is like a magic link - no prior team selection needed
    - Matches Teams/Slack experience
    """
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        
        # Normalize to uppercase because generated codes are uppercase
        # and users may type lowercase accidentally
        # Example: abc123ef -> ABC123EF
        # This avoids unnecessary "invalid code" errors.
        # Find team by code
        team = Team.query.filter_by(team_code=code).first()
        
        if not team:
            flash('Invalid team code.', 'error')
            return redirect(url_for('teams.join_by_code'))
        
        # Check if already member
        existing = TeamMember.query.filter_by(
            team_id=team.id,
            user_id=current_user.id
        ).first()
        
        if existing:
            flash('You are already a member of this team.', 'info')
            return redirect(url_for('teams.view_team', team_id=team.id))
        
        # Add user to team as regular member
        member_role = Role.query.filter_by(name='member').first()
        new_member = TeamMember(
            team_id=team.id,
            user_id=current_user.id,
            role_id=member_role.id
        )
        db.session.add(new_member)
        
        # Notify team owner
        notification = Notification(
            user_id=team.owner_id,
            type='team_member_joined',
            title=f'{current_user.username} joined {team.name}',
            message=f'{current_user.username} has joined your team using invite code',
            related_id=team.id
        )
        db.session.add(notification)
        
        db.session.commit()
        
        flash(f'You have joined team {team.name}!', 'success')
        return redirect(url_for('teams.view_team', team_id=team.id))
    
    return render_template('teams/join_by_code.html')


@bp.route('/<int:team_id>/channels/create', methods=['POST'])
@login_required
def create_channel(team_id):
    """Create a new channel in team."""
    
    team = Team.query.get_or_404(team_id)
    
    # Must be team member to create channels
    member = TeamMember.query.filter_by(
        team_id=team_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Normalize channel naming style to lowercase (Slack/Teams-like)
    name = request.form.get('name', '').strip().lower()
    description = request.form.get('description', '').strip()
    
    # Validation
    if not name or len(name) < 2:
        flash('Channel name must be at least 2 characters.', 'error')
        return redirect(url_for('teams.view_team', team_id=team_id))

    if len(name) > 50:
        flash('Channel name must be 50 characters or less.', 'error')
        return redirect(url_for('teams.view_team', team_id=team_id))

    if not re.fullmatch(r'[a-z0-9-]+', name):
        flash('Channel names can only contain lowercase letters, numbers, and hyphens.', 'error')
        return redirect(url_for('teams.view_team', team_id=team_id))
    
    # Check uniqueness within team
    existing = Channel.query.filter_by(
        team_id=team_id,
        name=name
    ).first()
    
    if existing:
        flash('A channel with this name already exists in this team.', 'error')
        return redirect(url_for('teams.view_team', team_id=team_id))
    
    # Insert channel record
    channel = Channel(
        name=name,
        description=description,
        team_id=team_id,
        created_by_id=current_user.id
    )
    db.session.add(channel)
    db.session.commit()
    
    flash(f'Channel #{name} created.', 'success')
    return redirect(url_for('messages.view_channel', channel_id=channel.id))


@bp.route('/<int:team_id>/invite', methods=['POST'])
@login_required
def invite_member(team_id):
    """Send a team invitation to a user (admin only)."""

    team = Team.query.get_or_404(team_id)

    # Only admins can invite
    tm = TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first()
    if not tm or tm.role.name != 'admin':
        flash('Only team admins can send invitations.', 'error')
        return redirect(url_for('teams.view_team', team_id=team_id))

    username = request.form.get('username', '').strip()
    invitee = User.query.filter_by(username=username).first()

    if not invitee:
        flash(f'User "{username}" not found.', 'error')
        return redirect(url_for('teams.view_team', team_id=team_id))

    if invitee.id == current_user.id:
        flash('You cannot invite yourself.', 'error')
        return redirect(url_for('teams.view_team', team_id=team_id))

    # Already a member?
    already = TeamMember.query.filter_by(team_id=team_id, user_id=invitee.id).first()
    if already:
        flash(f'{username} is already a member of this team.', 'info')
        return redirect(url_for('teams.view_team', team_id=team_id))

    # Avoid duplicate pending invites for same team/user pair
    pending = TeamInvitation.query.filter_by(
        team_id=team_id, invitee_id=invitee.id, status='pending'
    ).first()
    if pending:
        flash(f'An invitation is already pending for {username}.', 'info')
        return redirect(url_for('teams.view_team', team_id=team_id))

    # Create invitation record (source of truth)
    invitation = TeamInvitation(
        team_id=team_id,
        inviter_id=current_user.id,
        invitee_id=invitee.id,
        status='pending'
    )
    db.session.add(invitation)
    db.session.flush()  # get invitation.id

    # Notify invitee in notification center
    notification = Notification(
        user_id=invitee.id,
        type='team_invite',
        title=f'{current_user.username} invited you to join {team.name}',
        message=f'You have been invited to join the team "{team.name}". Accept or decline from Notifications.',
        related_id=invitation.id
    )
    db.session.add(notification)
    db.session.commit()

    flash(f'Invitation sent to {username}.', 'success')
    return redirect(url_for('teams.view_team', team_id=team_id))


@bp.route('/invitations/<int:invitation_id>/accept', methods=['POST'])
@login_required
def accept_invitation(invitation_id):
    """Accept a team invitation."""

    invitation = TeamInvitation.query.get_or_404(invitation_id)

    if invitation.invitee_id != current_user.id:
        flash('This invitation is not for you.', 'error')
        return redirect(url_for('dashboard.notifications'))

    if invitation.status != 'pending':
        flash('This invitation has already been responded to.', 'info')
        return redirect(url_for('dashboard.notifications'))

    # Idempotency: if already member, don't duplicate TeamMember row
    already = TeamMember.query.filter_by(
        team_id=invitation.team_id, user_id=current_user.id
    ).first()

    if not already:
        member_role = Role.query.filter_by(name='member').first()
        new_member = TeamMember(
            team_id=invitation.team_id,
            user_id=current_user.id,
            role_id=member_role.id
        )
        db.session.add(new_member)

        # Notify inviter that invite was accepted
        notif = Notification(
            user_id=invitation.inviter_id,
            type='team_invite_accepted',
            title=f'{current_user.username} accepted your invitation',
            message=f'{current_user.username} has joined {invitation.team.name}.',
            related_id=invitation.team_id
        )
        db.session.add(notif)

    # Update invitation status so it cannot be reused
    invitation.status = 'accepted'
    db.session.commit()

    flash(f'You have joined {invitation.team.name}!', 'success')
    return redirect(url_for('teams.view_team', team_id=invitation.team_id))


@bp.route('/invitations/<int:invitation_id>/decline', methods=['POST'])
@login_required
def decline_invitation(invitation_id):
    """Decline a team invitation."""

    invitation = TeamInvitation.query.get_or_404(invitation_id)

    if invitation.invitee_id != current_user.id:
        flash('This invitation is not for you.', 'error')
        return redirect(url_for('dashboard.notifications'))

    if invitation.status != 'pending':
        flash('This invitation has already been responded to.', 'info')
        return redirect(url_for('dashboard.notifications'))

    # Mark invitation as declined (terminal state)
    invitation.status = 'declined'

    # Notify inviter
    notif = Notification(
        user_id=invitation.inviter_id,
        type='team_invite_declined',
        title=f'{current_user.username} declined your invitation',
        message=f'{current_user.username} declined the invitation to join {invitation.team.name}.',
        related_id=invitation.team_id
    )
    db.session.add(notif)
    db.session.commit()

    flash('Invitation declined.', 'info')
    return redirect(url_for('dashboard.notifications'))
