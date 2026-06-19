"""
Socket.IO event handlers for WebRTC signaling.

Important concept:
- Media (audio/video) is peer-to-peer via WebRTC
- This server only relays negotiation messages (signaling)

Events handled:
1) join_call      -> user joins socket room scoped by call token
2) webrtc_offer   -> forward SDP offer to peer(s)
3) webrtc_answer  -> forward SDP answer to peer(s)
4) ice_candidate  -> forward network candidate to peer(s)
5) end_call_signal-> notify peers that call ended
"""

from flask_socketio import join_room, emit
from app.models import Call


def register_socket_events(socketio):
    """Register all socket event handlers."""

    # ===== JOIN CALL ROOM =====
    # Client sends: {call_token, user_id}
    # Server validates and joins socket room named by call_token

    @socketio.on('join_call')
    def handle_join_call(data):
        """Join a socket room for a call token."""
        # Pull required fields from incoming payload
        call_token = data.get('call_token')
        user_id = data.get('user_id')

        # Basic payload validation
        if not call_token or not user_id:
            emit('call_error', {'message': 'Missing call token or user id'})
            return

        # Ensure call exists in database
        call = Call.query.filter_by(call_token=call_token).first()
        if not call:
            emit('call_error', {'message': 'Call not found'})
            return

        # Ensure only call participants can join the room
        if user_id not in [call.caller_id, call.callee_id]:
            emit('call_error', {'message': 'Unauthorized call participant'})
            return

        # Join socket room so future emits can be scoped to this call
        join_room(call_token)
        # Notify others in room that a participant joined
        emit('participant_joined', {'user_id': user_id}, room=call_token, include_self=False)

    # ===== RELAY SDP OFFER =====
    # Caller usually sends this first in WebRTC negotiation
    @socketio.on('webrtc_offer')
    def handle_webrtc_offer(data):
        """Relay SDP offer to the other participant in the room."""
        call_token = data.get('call_token')
        offer = data.get('offer')
        sender_id = data.get('sender_id')

        # Validate critical payload fields
        if not call_token or not offer:
            emit('call_error', {'message': 'Invalid offer payload'})
            return

        # Forward offer to everyone else in this room (excluding sender)
        emit('webrtc_offer', {
            'offer': offer,
            'sender_id': sender_id
        }, room=call_token, include_self=False)

    # ===== RELAY SDP ANSWER =====
    # Callee sends answer in response to offer
    @socketio.on('webrtc_answer')
    def handle_webrtc_answer(data):
        """Relay SDP answer to the other participant in the room."""
        call_token = data.get('call_token')
        answer = data.get('answer')
        sender_id = data.get('sender_id')

        # Validate critical payload fields
        if not call_token or not answer:
            emit('call_error', {'message': 'Invalid answer payload'})
            return

        # Forward answer to other participant(s)
        emit('webrtc_answer', {
            'answer': answer,
            'sender_id': sender_id
        }, room=call_token, include_self=False)

    # ===== RELAY ICE CANDIDATES =====
    # Both peers may emit many candidates during connectivity checks
    @socketio.on('ice_candidate')
    def handle_ice_candidate(data):
        """Relay ICE candidate to the other participant in the room."""
        call_token = data.get('call_token')
        candidate = data.get('candidate')
        sender_id = data.get('sender_id')

        # Validate payload shape
        if not call_token or not candidate:
            emit('call_error', {'message': 'Invalid ICE candidate payload'})
            return

        # Forward candidate to peers in same call room
        emit('ice_candidate', {
            'candidate': candidate,
            'sender_id': sender_id
        }, room=call_token, include_self=False)

    # ===== END CALL SIGNAL =====
    # Inform all other peers to close their local call UI/streams
    @socketio.on('end_call_signal')
    def handle_end_call_signal(data):
        """Notify peer that call has ended."""
        call_token = data.get('call_token')
        sender_id = data.get('sender_id')

        # Ignore invalid payload silently
        if not call_token:
            return

        # Broadcast end signal to room except sender
        emit('call_ended', {'sender_id': sender_id}, room=call_token, include_self=False)
