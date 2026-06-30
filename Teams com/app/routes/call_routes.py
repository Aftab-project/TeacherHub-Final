"""
Video call routes and WebSocket handlers.

This module handles:
1. Initiating calls (HTTP POST)
   - 1-to-1 calls: /calls/<callee_id>/initiate
   - Group calls: /calls/group/<team_id>/initiate (NEW)
2. Call state management (accept, reject, end)
3. Call history tracking
4. Transcript storage (speech-to-text segments)
5. AI summary generation from transcripts

WebRTC Signaling Flow (1-to-1):
1. Caller posts /calls/<callee_id>/initiate
2. Server creates Call record (status='pending'), notifies callee
3. Callee gets notification, joins call room
4. Browser loads room.html, connects via Socket.IO
5. WebRTC peer exchange happens via Socket.IO (offer/answer/ICE candidates)
6. Video streams flow peer-to-peer (no server relay)
7. Either user posts /calls/<token>/end to close

Group Call Flow:
1. Caller posts /calls/group/<team_id>/initiate
2. Server validates: team exists, user is member, 2-8 participants
3. Creates Call with call_type='group', team_id={id}
4. Creates CallParticipant records for each participant (including caller)
5. Sends notifications to all participants
6. Returns call_token so caller can navigate to call room
7. Other participants get "incoming call" notification
8. Each joins the call room at /calls/room/<token>
9. All participate in same WebRTC mesh (everyone-to-everyone)
"""

from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from datetime import datetime
import uuid

from app.models import db, User, Call, Notification, CallTranscript, CallParticipant, Team

# ===== BLUEPRINT SETUP =====
# All routes under this blueprint have prefix /calls
call_routes = Blueprint('calls', __name__, url_prefix='/calls')

# ===== ACTIVE CALLS TRACKING =====
# In-memory cache for active calls: {call_token: {call_id, status, created_at, ...}}
# Useful for quick lookups without database query
active_calls = {}


# ===== 1-TO-1 CALL INITIATION =====
@call_routes.route('/<int:callee_id>/initiate', methods=['POST'])
@login_required
def initiate_call(callee_id):
    """
    Start a 1-to-1 video call to another user.
    
    Endpoint: POST /calls/<callee_id>/initiate
    
    Parameters:
    - callee_id: User ID of the person we want to call
    
    Response (201 Created):
    {
        'call_id': int,                    # Database record ID
        'call_token': str(uuid),           # Unique session identifier
        'status': 'pending',               # Call not yet accepted
        'caller': 'alice',                 # Current user's username
        'callee': 'bob'                    # Other user's username
    }
    """
    # ===== VALIDATION =====
    # Check if the other user exists
    callee = User.query.get(callee_id)
    if not callee:
        return jsonify({'error': 'User not found'}), 404
    
    # Can't call yourself
    if current_user.id == callee_id:
        return jsonify({'error': 'Cannot call yourself'}), 400
    
    # ===== CREATE CALL RECORD =====
    # Generate unique token for this call session
    call_token = str(uuid.uuid4())
    
    # Create call in database
    call = Call(
        caller_id=current_user.id,         # Who initiated
        callee_id=callee_id,               # Who's being called
        call_token=call_token,             # Session identifier
        status='pending'                   # Waiting for callee to accept/reject
    )
    
    db.session.add(call)

    # ===== NOTIFY CALLEE =====
    # Create notification for incoming call
    incoming_notification = Notification(
        user_id=callee_id,
        type='incoming_call',              # Type of notification
        title=f'Incoming call from {current_user.username}',
        message='You have an incoming video call.',
        related_id=call.id,                # Link to the call
        is_read=False
    )
    db.session.add(incoming_notification)
    db.session.commit()
    
    # ===== TRACK IN MEMORY =====
    # Store in active calls for fast lookup
    active_calls[call_token] = {
        'call_id': call.id,
        'caller_id': current_user.id,
        'callee_id': callee_id,
        'status': 'pending',
        'created_at': datetime.utcnow()
    }
    
    return jsonify({
        'call_id': call.id,
        'call_token': call_token,
        'status': 'pending',
        'caller': current_user.username,
        'callee': callee.username
    }), 201


# ===== GROUP CALL INITIATION (NEW FEATURE) =====
@call_routes.route('/group/<int:team_id>/initiate', methods=['POST'])
@login_required
def initiate_group_call(team_id):
    """
    Start a group video call for a team (INTRODUCED FOR GROUP CALLING FEATURE).
    
    Endpoint: POST /calls/group/<team_id>/initiate
    
    Parameters:
    - team_id: Which team to call
    
    Optional JSON body:
    {
        'participant_ids': [1, 2, 3, ...]   # Specific users, or empty for all team members
    }
    
    Response (201 Created):
    {
        'call_id': int,
        'call_token': str(uuid),
        'call_type': 'group',
        'status': 'pending',
        'team_id': int,
        'team_name': 'Frontend Team',
        'participants': [
            {'id': 1, 'username': 'alice'},
            {'id': 2, 'username': 'bob'},
            ...
        ]
    }
    
    How group calls work:
    1. Each participant gets their own CallParticipant record (join table)
    2. All participants will see each other's video in a grid layout
    3. Limited to 2-8 participants per call (configurable)
    4. Supports mesh topology: everyone-to-everyone peer connections
    """
    # ===== VALIDATE TEAM =====
    # Does the team exist?
    team = Team.query.filter_by(id=team_id).first()
    if not team:
        return jsonify({'error': 'Team not found'}), 404
    
    # ===== VALIDATE CALLER IS TEAM MEMBER =====
    # Can only start calls if you're in the team
    from app.models import TeamMember
    is_member = TeamMember.query.filter_by(
        team_id=team_id,
        user_id=current_user.id
    ).first()
    
    if not is_member:
        return jsonify({'error': 'You are not a member of this team'}), 403
    
    # ===== GET PARTICIPANT LIST =====
    # Get the JSON body (optional)
    data = request.get_json(silent=True) or {}
    participant_ids = data.get('participant_ids', [])
    
    if not participant_ids:
        # If no specific list given, invite all team members except the caller
        team_members = TeamMember.query.filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id != current_user.id  # Don't include ourselves
        ).all()
        participant_ids = [tm.user_id for tm in team_members]
    
    # Check if there are any participants at all
    if not participant_ids:
        return jsonify({'error': 'No other team members to call'}), 400
    
    # ===== REMOVE CALLER FROM PARTICIPANT LIST =====
    # In case caller was included in participant_ids
    participant_ids = [pid for pid in participant_ids if pid != current_user.id]
    
    if not participant_ids:
        return jsonify({'error': 'No valid participants'}), 400
    
    # ===== VALIDATE PARTICIPANT COUNT (MAX 8) =====
    # Group calls support up to 8 participants
    # This limit ensures WebRTC mesh remains performant
    if len(participant_ids) > 8:
        return jsonify({'error': 'Group call limited to 8 participants'}), 400
    
    # ===== VALIDATE EACH PARTICIPANT =====
    # For each person we want to add:
    # 1. Check they exist
    # 2. Check they're in the team
    for pid in participant_ids:
        participant = User.query.filter_by(id=pid).first()
        if not participant:
            return jsonify({'error': f'User {pid} not found'}), 404
        
        is_team_member = TeamMember.query.filter_by(
            team_id=team_id,
            user_id=pid
        ).first()
        if not is_team_member:
            return jsonify({'error': f'User {pid} is not a team member'}), 403
    
    # ===== CREATE GROUP CALL RECORD =====
    # Generate unique token
    call_token = str(uuid.uuid4())
    
    # Create Call record with call_type='group'
    call = Call(
        team_id=team_id,                   # Which team this call is in
        caller_id=current_user.id,         # Who initiated the call
        call_type='group',                 # This is a group call
        call_token=call_token,             # Session ID
        status='pending'                   # Waiting for participants to join
    )
    
    db.session.add(call)
    db.session.flush()  # Get the call.id without committing yet
    
    # ===== ADD CALLER AS FIRST PARTICIPANT =====
    # The person who started the call is also a participant
    caller_participant = CallParticipant(
        call_id=call.id,
        user_id=current_user.id
    )
    db.session.add(caller_participant)
    
    # ===== ADD OTHER PARTICIPANTS =====
    # For each person to invite:
    # 1. Add CallParticipant record so we know they're part of this call
    # 2. Create notification so they see the incoming call
    for pid in participant_ids:
        # Add as participant
        participant = CallParticipant(
            call_id=call.id,
            user_id=pid
        )
        db.session.add(participant)
        
        # Notify them about the incoming group call
        notification = Notification(
            user_id=pid,
            type='group_call',                 # This is a GROUP call notification
            title=f'Group call in {team.name} from {current_user.username}',
            message=f'Join the group call in {team.name}',
            related_id=call.id,                # Link to the call
            is_read=False
        )
        db.session.add(notification)
    
    # Commit all changes
    db.session.commit()
    
    # ===== TRACK IN MEMORY =====
    # Store in active calls
    active_calls[call_token] = {
        'call_id': call.id,
        'team_id': team_id,
        'initiator_id': current_user.id,
        'participant_ids': [current_user.id] + participant_ids,  # All including caller
        'status': 'pending',
        'created_at': datetime.utcnow(),
        'call_type': 'group'
    }
    
    # ===== BUILD RESPONSE =====
    # Create list of all participants (caller + others)
    participants_list = []
    for pid in [current_user.id] + participant_ids:
        user = User.query.filter_by(id=pid).first()
        if user:
            participants_list.append({'id': pid, 'username': user.username})
    
    return jsonify({
        'call_id': call.id,
        'call_token': call_token,
        'status': 'pending',
        'call_type': 'group',
        'team_id': team_id,
        'team_name': team.name,
        'initiator': current_user.username,
        'participants': participants_list
    }), 201


# ===== GET CALL INFO =====
@call_routes.route('/<call_token>', methods=['GET'])
@login_required
def get_call_info(call_token):
    """
    Fetch information about a specific call.
    
    Endpoint: GET /calls/<call_token>
    """
    # Find the call
    call = Call.query.filter_by(call_token=call_token).first()
    if not call:
        return jsonify({'error': 'Call not found'}), 404
    
    # Check authorization: only participants can view
    if call.caller_id != current_user.id and call.callee_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Return call details
    return jsonify(call.to_dict()), 200


# ===== ACCEPT CALL (CALLEE) =====
@call_routes.route('/<call_token>/accept', methods=['POST'])
@login_required
def accept_call(call_token):
    """
    Accept an incoming 1-to-1 call (callee action).
    
    Endpoint: POST /calls/<call_token>/accept
    
    This changes call status from 'pending' to 'active' and records start time.
    """
    # Find call
    call = Call.query.filter_by(call_token=call_token).first()
    if not call:
        return jsonify({'error': 'Call not found'}), 404
    
    # Only the callee (receiver) can accept
    if call.callee_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Call must still be pending (not already accepted/rejected)
    if call.status not in ['pending']:
        return jsonify({'error': f'Cannot accept call in {call.status} status'}), 400
    
    # ===== UPDATE CALL STATE =====
    call.status = 'active'                 # Call is now active
    call.started_at = datetime.utcnow()    # Record when it started

    # ===== MARK NOTIFICATIONS AS READ =====
    # Mark the "incoming call" notification as read
    Notification.query.filter_by(
        user_id=current_user.id,
        type='incoming_call',
        related_id=call.id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()
    
    # ===== UPDATE IN-MEMORY TRACKING =====
    if call_token in active_calls:
        active_calls[call_token]['status'] = 'active'
    
    return jsonify({
        'status': 'active',
        'started_at': call.started_at.isoformat()
    }), 200


# ===== REJECT CALL (CALLEE) =====
@call_routes.route('/<call_token>/reject', methods=['POST'])
@login_required
def reject_call(call_token):
    """
    Reject an incoming call (callee action).
    
    Endpoint: POST /calls/<call_token>/reject
    
    This marks the call as rejected and notifies the caller.
    """
    # Find call
    call = Call.query.filter_by(call_token=call_token).first()
    if not call:
        return jsonify({'error': 'Call not found'}), 404
    
    # Only callee can reject
    if call.callee_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Call must be pending
    if call.status not in ['pending']:
        return jsonify({'error': f'Cannot reject call in {call.status} status'}), 400
    
    # ===== UPDATE CALL STATE =====
    call.status = 'rejected'               # Mark as rejected
    call.ended_at = datetime.utcnow()      # Record end time

    # ===== NOTIFY CALLER =====
    # Tell the caller that their call was rejected
    rejection_notification = Notification(
        user_id=call.caller_id,
        type='call_rejected',
        title=f'{current_user.username} rejected your call',
        message='Your video call was rejected.',
        related_id=call.id,
        is_read=False
    )
    db.session.add(rejection_notification)

    # ===== MARK CALLEE'S NOTIFICATION AS READ =====
    # Mark the incoming call notification as read for callee
    Notification.query.filter_by(
        user_id=current_user.id,
        type='incoming_call',
        related_id=call.id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()
    
    # ===== CLEANUP IN-MEMORY TRACKING =====
    if call_token in active_calls:
        active_calls[call_token]['status'] = 'rejected'
        del active_calls[call_token]
    
    return jsonify({'status': 'rejected'}), 200


# ===== END CALL =====
@call_routes.route('/<call_token>/end', methods=['POST'])
@login_required
def end_call(call_token):
    """
    End an active or pending call (either participant can call this).
    
    Endpoint: POST /calls/<call_token>/end
    
    Behavior:
    - If still pending: marks as 'missed' (other user didn't answer)
    - If already active: marks as 'completed'
    - Calculates call duration
    - Auto-generates transcript summary if there are segments
    """
    # Find call
    call = Call.query.filter_by(call_token=call_token).first()
    if not call:
        return jsonify({'error': 'Call not found'}), 404
    
    # Must be a participant (caller or callee)
    if call.caller_id != current_user.id and call.callee_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Can only end if pending or active (not already completed/rejected)
    if call.status not in ['pending', 'active']:
        return jsonify({'error': f'Cannot end call in {call.status} status'}), 400
    
    # ===== DETERMINE FINAL STATUS =====
    if call.status == 'pending':
        # Call ended before acceptance = missed call
        call.status = 'missed'
        
        # Figure out who missed the call (not the person ending it)
        missed_recipient_id = call.callee_id if current_user.id == call.caller_id else call.caller_id
        
        # Notify that person about the missed call
        missed_notification = Notification(
            user_id=missed_recipient_id,
            type='missed_call',
            title=f'Missed call from {call.caller.username}',
            message='You missed a video call.',
            related_id=call.id,
            is_read=False
        )
        db.session.add(missed_notification)
    else:
        # Call was active and is being properly ended
        call.status = 'completed'

    # ===== RECORD END TIME =====
    call.ended_at = datetime.utcnow()
    
    # ===== CALCULATE DURATION =====
    # Use started_at if available, otherwise created_at (if call never started)
    start_time = call.started_at or call.created_at
    call.duration = int((call.ended_at - start_time).total_seconds())

    # ===== AUTO-GENERATE SUMMARY =====
    # If there are transcript segments, create a summary
    segments = CallTranscript.query.filter_by(call_id=call.id)\
        .order_by(CallTranscript.created_at).all()
    if segments:
        raw = [{'speaker': s.speaker.username, 'text': s.text} for s in segments]
        call.summary = _build_summary(raw)

    db.session.commit()
    
    # ===== CLEANUP IN-MEMORY TRACKING =====
    if call_token in active_calls:
        active_calls[call_token]['status'] = call.status
        del active_calls[call_token]
    
    return jsonify({
        'status': call.status,
        'duration': call.duration,
        'ended_at': call.ended_at.isoformat()
    }), 200


# ===== CALL HISTORY (HTML PAGE) =====
@call_routes.route('/history', methods=['GET'])
@login_required
def call_history():
    """
    Display call history page for current user.
    
    Endpoint: GET /calls/history
    
    Shows all calls where user was caller or callee.
    """
    # Pagination params
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Query: calls where user is caller OR callee
    calls = Call.query.filter(
        db.or_(
            Call.caller_id == current_user.id,
            Call.callee_id == current_user.id
        )
    ).order_by(Call.created_at.desc()).limit(limit).offset(offset).all()
    
    return render_template('calls/history.html', calls=calls)


# ===== CALL HISTORY (API) =====
@call_routes.route('/history/api', methods=['GET'])
@login_required
def call_history_api():
    """
    Get call history as JSON API response.
    
    Endpoint: GET /calls/history/api
    
    Returns JSON array of calls.
    """
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)

    # Same query as HTML version
    calls = Call.query.filter(
        db.or_(
            Call.caller_id == current_user.id,
            Call.callee_id == current_user.id
        )
    ).order_by(Call.created_at.desc()).limit(limit).offset(offset).all()

    return jsonify({
        'calls': [call.to_dict() for call in calls],
        'total': len(calls)
    }), 200


# ===== GET INCOMING CALLS (POLLING) =====
@call_routes.route('/incoming', methods=['GET'])
@login_required
def incoming_calls():
    """
    Get all pending incoming calls for current user.
    
    Endpoint: GET /calls/incoming
    
    Used by base.html JavaScript (pollIncomingCalls function):
    - Polls every 8 seconds
    - Checks for new pending calls where current_user is callee
    - Returns calls so UI can show "incoming call" toast
    """
    # Find all pending calls where I'm the callee
    pending_calls = Call.query.filter(
        Call.callee_id == current_user.id,
        Call.status == 'pending'
    ).order_by(Call.created_at.desc()).all()
    
    return jsonify({
        'calls': [call.to_dict() for call in pending_calls],
        'count': len(pending_calls)
    }), 200


# ===== DISPLAY CALL ROOM =====
@call_routes.route('/room/<call_token>')
@login_required
def call_room(call_token):
    """
    Display the video call interface (room.html).
    
    Endpoint: GET /calls/room/<call_token>
    
    Handles both 1-to-1 and group calls:
    - 1-to-1: Shows 2 video streams (other + local PiP)
    - Group: Shows grid of all participant videos
    
    Validates user is participant in the call before allowing access.
    """
    # Find the call
    call = Call.query.filter_by(call_token=call_token).first()
    if not call:
        return 'Call not found', 404

    # ===== VALIDATE AUTHORIZATION =====
    if call.call_type == 'group':
        # For group calls: user must be in CallParticipant table
        participant = CallParticipant.query.filter_by(
            call_id=call.id,
            user_id=current_user.id
        ).first()
        if not participant:
            return 'Unauthorized', 403
        
        # Get all OTHER participants (not including current user)
        other_participants = CallParticipant.query.filter(
            CallParticipant.call_id == call.id,
            CallParticipant.user_id != current_user.id
        ).all()
        other_users = [p.user for p in other_participants]
        other_user = None  # Not used in group calls
        is_caller = call.caller_id == current_user.id
    else:
        # For 1-to-1 calls: user must be caller or callee
        if call.caller_id != current_user.id and call.callee_id != current_user.id:
            return 'Unauthorized', 403
        
        # Determine if current user is the caller
        is_caller = call.caller_id == current_user.id
        
        # Get the other person
        other_user = call.callee if is_caller else call.caller
        other_users = []

    # Render the call room template
    return render_template('calls/room.html',
                           call=call,
                           other_user=other_user,
                           other_users=other_users,
                           is_caller=is_caller)


# ===== DISPLAY CALL SUMMARY PAGE =====
@call_routes.route('/<call_token>/summary', methods=['GET'])
@login_required
def call_summary_page(call_token):
    """
    Display post-call summary page with transcript and duration.
    
    Endpoint: GET /calls/<call_token>/summary
    """
    # Find call
    call = Call.query.filter_by(call_token=call_token).first()
    if not call:
        return 'Call not found', 404

    # Only participants can view summary
    if call.caller_id != current_user.id and call.callee_id != current_user.id:
        return 'Unauthorized', 403

    # Get all transcript segments, ordered by time
    segments = CallTranscript.query.filter_by(call_id=call.id)\
        .order_by(CallTranscript.created_at).all()

    # Determine if current user is caller
    is_caller = call.caller_id == current_user.id
    other_user = call.callee if is_caller else call.caller
    
    # ===== FORMAT DURATION =====
    # Convert seconds to "Xm Ys" format
    duration_str = ''
    if call.duration:
        mins = call.duration // 60
        secs = call.duration % 60
        duration_str = f'{mins}m {secs}s' if mins > 0 else f'{secs}s'

    return render_template('calls/summary.html',
                           call=call,
                           other_user=other_user,
                           segments=segments,
                           duration_str=duration_str)


# ===== TRANSCRIPT API: ADD SEGMENT =====
@call_routes.route('/<call_token>/transcript', methods=['POST'])
@login_required
def add_transcript_segment(call_token):
    """
    Append a speech-to-text segment to the call transcript.
    
    Endpoint: POST /calls/<call_token>/transcript
    
    Request body:
    {
        'text': 'What the speaker said'
    }
    
    Called by room.html when user's browser converts speech to text via Web Speech API.
    Saves the text segment so it persists and can be summarized later.
    """
    # Find call
    call = Call.query.filter_by(call_token=call_token).first()
    if not call:
        return jsonify({'error': 'Call not found'}), 404

    # Only participants can add transcript
    if call.caller_id != current_user.id and call.callee_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    # Get JSON body and extract text
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    # Create CallTranscript record
    segment = CallTranscript(
        call_id=call.id,
        speaker_id=current_user.id,        # Who said this
        text=text                          # What they said
    )
    db.session.add(segment)
    db.session.commit()

    return jsonify({'ok': True, 'id': segment.id}), 201


# ===== TRANSCRIPT API: GET ALL SEGMENTS =====
@call_routes.route('/<call_token>/transcript', methods=['GET'])
@login_required
def get_transcript(call_token):
    """
    Fetch transcript segments for a call (optimized with pagination).
    
    Endpoint: GET /calls/<call_token>/transcript?page=1&per_page=50
    
    Optimizations:
    - Uses database indexes on call_id and timestamp
    - Pagination reduces memory usage for large transcripts
    - Compound index lookup: (call_id, timestamp)
    
    Response:
    {
        'segments': [...],
        'total': int,
        'page': int,
        'per_page': int,
        'summary': 'AI-generated summary if available'
    }
    """
    # Find call
    call = Call.query.filter_by(call_token=call_token).first()
    if not call:
        return jsonify({'error': 'Call not found'}), 404

    # Only participants can view
    if call.caller_id != current_user.id and call.callee_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    per_page = min(per_page, 100)  # Cap at 100 per page
    
    # Get transcript segments using indexes (ordered by timestamp for chronological order)
    query = CallTranscript.query.filter_by(call_id=call.id)\
        .order_by(CallTranscript.timestamp)
    
    total = query.count()
    
    segments = query.limit(per_page)\
        .offset((page - 1) * per_page)\
        .all()

    return jsonify({
        'segments': [
            {
                'id': s.id,
                'speaker': s.speaker.username,
                'text': s.text,
                'timestamp': s.timestamp,
                'time': s.created_at.strftime('%H:%M:%S')
            }
            for s in segments
        ],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
        'summary': call.summary or ''
    })


# ===== TRANSCRIPT API: GENERATE SUMMARY =====
@call_routes.route('/<call_token>/summarize', methods=['POST'])
@login_required
def summarize_call(call_token):
    """
    Generate and save an extractive summary from the call transcript.
    
    Endpoint: POST /calls/<call_token>/summarize
    
    Called by room.html when user clicks "âœ¨ Summarize" button.
    Uses word frequency scoring to pick the most important sentences.
    """
    # Find call
    call = Call.query.filter_by(call_token=call_token).first()
    if not call:
        return jsonify({'error': 'Call not found'}), 404

    # Only participants can summarize
    if call.caller_id != current_user.id and call.callee_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    # Get all transcript segments
    segments = CallTranscript.query.filter_by(call_id=call.id)\
        .order_by(CallTranscript.created_at).all()

    # If no transcript, return empty summary
    if not segments:
        return jsonify({'summary': '', 'message': 'No transcript segments found'}), 200

    # Convert segments to format for summary function
    raw = [{'speaker': s.speaker.username, 'text': s.text} for s in segments]
    
    # Generate summary using extractive summarization algorithm
    summary = _build_summary(raw)

    # Save summary to database
    call.summary = summary
    db.session.commit()

    return jsonify({'summary': summary}), 200


# ===== SUMMARY GENERATION ALGORITHM =====
def _build_summary(segments, max_sentences=6):
    """
    Extractive summarization using word frequency scoring.
    
    Algorithm:
    1. Split transcript into sentences
    2. Score each word by frequency (excluding common words)
    3. Score each sentence by average word frequency
    4. Return top N sentences
    
    Why extractive (not generative):
    - No external AI library required
    - Works offline
    - Fast and deterministic
    - Preserves original speaker's wording
    """
    import re
    from collections import Counter

    # Combine all text into one string
    full_text = ' '.join(s['text'] for s in segments)
    if not full_text.strip():
        return ''

    # ===== TOKENIZE INTO SENTENCES =====
    # Split on sentence boundaries (. ! ?)
    sentence_list = re.split(r'(?<=[.!?])\s+', full_text.strip())
    # Clean up and keep only meaningful sentences (8+ chars)
    sentence_list = [s.strip() for s in sentence_list if len(s.strip()) > 8]
    if not sentence_list:
        return full_text[:500]  # Fallback: return first 500 chars

    # ===== BUILD WORD FREQUENCY TABLE =====
    # Define common words to ignore (stopwords)
    stopwords = {
        'the','a','an','is','it','to','of','and','in','on','at','this','that',
        'was','for','are','with','as','by','from','or','be','been','have','has',
        'he','she','they','we','you','i','my','me','him','her','his','their',
        'but','so','if','not','do','did','will','would','could','should','can',
        'just','up','about','into','like','more','what','when','how','there'
    }
    
    # Extract all words (3+ letters, lowercase)
    words = re.findall(r'\b[a-z]{3,}\b', full_text.lower())
    
    # Count frequency, excluding stopwords
    freq = Counter(w for w in words if w not in stopwords)
    if not freq:
        return full_text[:500]
    
    # Normalize frequencies to 0-1 scale
    max_freq = max(freq.values())
    freq = {w: v / max_freq for w, v in freq.items()}

    # ===== SCORE SENTENCES =====
    scored = []
    for sent in sentence_list:
        # Extract words from this sentence
        tokens = re.findall(r'\b[a-z]{3,}\b', sent.lower())
        # Score = sum of word frequencies / number of words
        # (So longer sentences aren't unfairly penalized)
        score = sum(freq.get(t, 0) for t in tokens) / (len(tokens) + 1)
        scored.append((score, sent))

    # ===== SELECT TOP SENTENCES =====
    # Sort by score (highest first)
    scored.sort(key=lambda x: -x[0])
    # Take top N sentences
    top = [s for _, s in scored[:max_sentences]]

    # ===== RESTORE ORIGINAL ORDER =====
    # Summary should flow naturally (original order, not by importance)
    ordered = [s for s in sentence_list if s in top]
    return ' '.join(ordered)

