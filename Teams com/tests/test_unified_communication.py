"""
Unified Communication Features Testing
=======================================

Tests for combined communication features:
- Messaging and calls together
- Real-time notification delivery
- Message-to-call transitions
- Unified search across communications

Run with: pytest tests/test_unified_communication.py
"""

import pytest
from datetime import datetime, timedelta
from app import create_app, db
from app.models import (
    User, Team, TeamMember, Role, Channel, Message, 
    Call, CallTranscript, DirectMessage, Notification
)


@pytest.fixture
def app():
    """Create test app with test database."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def setup_communication_env(app):
    """Setup users, teams, channels for communication tests."""
    with app.app_context():
        # Reuse seeded roles when present.
        admin_role = Role.query.filter_by(name='admin').first()
        member_role = Role.query.filter_by(name='member').first()

        if not admin_role:
            admin_role = Role(name='admin', description='Admin')
            db.session.add(admin_role)
        if not member_role:
            member_role = Role(name='member', description='Member')
            db.session.add(member_role)
        db.session.flush()
        
        # Create users
        users_data = []
        for name in ['alice', 'bob', 'charlie', 'diana']:
            user = User(username=name, email=f'{name}@test.com')
            user.set_password('password123')
            users_data.append(user)
            db.session.add(user)
        
        db.session.flush()
        users_dict = {u.username: u for u in users_data}
        user_ids = {u.username: u.id for u in users_data}
        
        # Create team
        team = Team(
            name='Communication Team',
            owner_id=users_dict['alice'].id,
            team_code='COMM2024',
            is_public=True
        )
        db.session.add(team)
        db.session.flush()
        
        # Add all users to team
        for user in users_data:
            role = admin_role if user == users_dict['alice'] else member_role
            tm = TeamMember(team_id=team.id, user_id=user.id, role_id=role.id)
            db.session.add(tm)
        
        # Create channels
        general = Channel(
            name='general',
            description='General discussion',
            team_id=team.id,
            created_by_id=users_dict['alice'].id
        )
        project = Channel(
            name='project',
            description='Project updates',
            team_id=team.id,
            created_by_id=users_dict['alice'].id
        )
        db.session.add_all([general, project])
        db.session.commit()
        
        return {
            'app': app,
            'users': user_ids,
            'team_id': team.id,
            'channels': {'general': general.id, 'project': project.id}
        }


class TestChannelMessaging:
    """Test channel messaging functionality."""
    
    def test_send_message_to_channel(self, setup_communication_env):
        """Test sending message to channel."""
        env = setup_communication_env
        with env['app'].app_context():
            channel_id = env['channels']['general']
            sender_id = env['users']['alice']
            
            msg = Message(
                content='Hello everyone!',
                channel_id=channel_id,
                sender_id=sender_id
            )
            db.session.add(msg)
            db.session.commit()
            
            # Verify message saved
            saved = Message.query.filter_by(channel_id=channel_id).first()
            assert saved.content == 'Hello everyone!'
            assert saved.sender_id == sender_id
    
    def test_message_history_retrieval(self, setup_communication_env):
        """Test retrieving message history."""
        env = setup_communication_env
        with env['app'].app_context():
            channel_id = env['channels']['general']
            
            # Add multiple messages
            messages = [
                Message(content=f'Message {i}', channel_id=channel_id, sender_id=env['users']['alice'])
                for i in range(10)
            ]
            db.session.add_all(messages)
            db.session.commit()
            
            # Retrieve history
            history = Message.query.filter_by(channel_id=channel_id)\
                .order_by(Message.created_at).all()
            
            assert len(history) == 10
    
    def test_message_edit(self, setup_communication_env):
        """Test editing a message."""
        env = setup_communication_env
        with env['app'].app_context():
            channel_id = env['channels']['general']
            msg = Message(
                content='Original content',
                channel_id=channel_id,
                sender_id=env['users']['alice']
            )
            db.session.add(msg)
            db.session.commit()
            
            # Edit message
            msg.content = 'Edited content'
            msg.is_edited = True
            db.session.commit()
            
            # Verify edit
            saved = Message.query.get(msg.id)
            assert saved.content == 'Edited content'
            assert saved.is_edited is True
    
    def test_message_deletion(self, setup_communication_env):
        """Test deleting a message."""
        env = setup_communication_env
        with env['app'].app_context():
            channel_id = env['channels']['general']
            msg = Message(
                content='To be deleted',
                channel_id=channel_id,
                sender_id=env['users']['alice']
            )
            db.session.add(msg)
            db.session.commit()
            
            msg_id = msg.id
            
            # Delete message
            db.session.delete(msg)
            db.session.commit()
            
            # Verify deletion
            deleted = Message.query.get(msg_id)
            assert deleted is None


class TestDirectMessaging:
    """Test direct messaging between users."""
    
    def test_send_direct_message(self, setup_communication_env):
        """Test sending direct message between users."""
        env = setup_communication_env
        with env['app'].app_context():
            alice_id = env['users']['alice']
            bob_id = env['users']['bob']
            
            dm = DirectMessage(
                content='Hi Bob, this is a DM',
                sender_id=alice_id,
                recipient_id=bob_id
            )
            db.session.add(dm)
            db.session.commit()
            
            # Verify DM saved
            saved = DirectMessage.query.filter_by(sender_id=alice_id).first()
            assert saved.content == 'Hi Bob, this is a DM'
    
    def test_direct_message_read_status(self, setup_communication_env):
        """Test marking direct message as read."""
        env = setup_communication_env
        with env['app'].app_context():
            alice_id = env['users']['alice']
            bob_id = env['users']['bob']
            
            dm = DirectMessage(
                content='Important message',
                sender_id=alice_id,
                recipient_id=bob_id,
                is_read=False
            )
            db.session.add(dm)
            db.session.commit()
            
            # Mark as read
            dm.is_read = True
            db.session.commit()
            
            # Verify
            saved = DirectMessage.query.get(dm.id)
            assert saved.is_read is True
    
    def test_dm_conversation_history(self, setup_communication_env):
        """Test retrieving DM conversation between two users."""
        env = setup_communication_env
        with env['app'].app_context():
            alice_id = env['users']['alice']
            bob_id = env['users']['bob']
            
            # Send messages back and forth
            messages = [
                DirectMessage(content='Hi', sender_id=alice_id, recipient_id=bob_id),
                DirectMessage(content='Hey', sender_id=bob_id, recipient_id=alice_id),
                DirectMessage(content='How are you?', sender_id=alice_id, recipient_id=bob_id),
                DirectMessage(content='Good!', sender_id=bob_id, recipient_id=alice_id),
            ]
            db.session.add_all(messages)
            db.session.commit()
            
            # Get conversation
            conversation = DirectMessage.query.filter(
                db.or_(
                    db.and_(DirectMessage.sender_id == alice_id, DirectMessage.recipient_id == bob_id),
                    db.and_(DirectMessage.sender_id == bob_id, DirectMessage.recipient_id == alice_id)
                )
            ).order_by(DirectMessage.created_at).all()
            
            assert len(conversation) == 4


class TestNotifications:
    """Test unified notification system."""
    
    def test_notification_on_message_mention(self, setup_communication_env):
        """Test notification when user is mentioned."""
        env = setup_communication_env
        with env['app'].app_context():
            alice_id = env['users']['alice']
            bob_id = env['users']['bob']
            channel_id = env['channels']['general']
            
            # Send message with mention
            msg = Message(
                content='@bob please review this',
                channel_id=channel_id,
                sender_id=alice_id
            )
            db.session.add(msg)
            db.session.flush()
            
            # Create notification
            notif = Notification(
                user_id=bob_id,
                type='mention',
                title='alice mentioned you',
                message=f'In general: {msg.content}',
                related_id=msg.id,
                is_read=False
            )
            db.session.add(notif)
            db.session.commit()
            
            # Verify notification
            saved = Notification.query.filter_by(user_id=bob_id).first()
            assert saved.type == 'mention'
    
    def test_notification_on_call(self, setup_communication_env):
        """Test notification for incoming call."""
        env = setup_communication_env
        with env['app'].app_context():
            alice_id = env['users']['alice']
            bob_id = env['users']['bob']
            
            # Create call
            call = Call(
                team_id=env['team_id'],
                caller_id=alice_id,
                callee_id=bob_id,
                call_type='1-to-1',
                call_token='test-notif-call',
                status='pending'
            )
            db.session.add(call)
            db.session.flush()
            
            # Create notification
            notif = Notification(
                user_id=bob_id,
                type='incoming_call',
                title='alice is calling',
                message='You have an incoming video call',
                related_id=call.id,
                is_read=False
            )
            db.session.add(notif)
            db.session.commit()
            
            # Verify
            saved = Notification.query.filter_by(user_id=bob_id).first()
            assert saved.type == 'incoming_call'
    
    def test_notification_read_marking(self, setup_communication_env):
        """Test marking notifications as read."""
        env = setup_communication_env
        with env['app'].app_context():
            bob_id = env['users']['bob']
            
            # Create multiple notifications
            notifs = [
                Notification(
                    user_id=bob_id,
                    type='message',
                    title=f'New message {i}',
                    message='You have a new message',
                    is_read=False
                )
                for i in range(5)
            ]
            db.session.add_all(notifs)
            db.session.commit()
            
            # Mark first 3 as read
            unread = Notification.query.filter_by(user_id=bob_id, is_read=False).limit(3).all()
            for notif in unread:
                notif.is_read = True
            db.session.commit()
            
            # Verify
            still_unread = Notification.query.filter_by(user_id=bob_id, is_read=False).all()
            assert len(still_unread) == 2


class TestMessageToCallTransition:
    """Test transitioning from messaging to calls."""
    
    def test_dm_to_call_flow(self, setup_communication_env):
        """Test starting call from DM conversation."""
        env = setup_communication_env
        with env['app'].app_context():
            alice_id = env['users']['alice']
            bob_id = env['users']['bob']
            
            # Send DM
            dm = DirectMessage(
                content='Can we hop on a quick call?',
                sender_id=alice_id,
                recipient_id=bob_id
            )
            db.session.add(dm)
            db.session.flush()
            
            # Start call from DM
            call = Call(
                team_id=env['team_id'],
                caller_id=alice_id,
                callee_id=bob_id,
                call_type='1-to-1',
                call_token='dm-to-call-123',
                status='pending'
            )
            db.session.add(call)
            db.session.commit()
            
            # Verify both exist and are linked
            saved_dm = DirectMessage.query.get(dm.id)
            saved_call = Call.query.get(call.id)
            
            assert saved_dm is not None
            assert saved_call is not None
            assert saved_call.caller_id == alice_id
    
    def test_channel_mention_to_call(self, setup_communication_env):
        """Test calling user after mention in channel."""
        env = setup_communication_env
        with env['app'].app_context():
            alice_id = env['users']['alice']
            bob_id = env['users']['bob']
            channel_id = env['channels']['general']
            
            # Send message with mention
            msg = Message(
                content='@bob can you help?',
                channel_id=channel_id,
                sender_id=alice_id
            )
            db.session.add(msg)
            db.session.flush()
            
            # Start call
            call = Call(
                team_id=env['team_id'],
                caller_id=alice_id,
                callee_id=bob_id,
                call_type='1-to-1',
                call_token='mention-to-call-456',
                status='active',
                started_at=datetime.utcnow()
            )
            db.session.add(call)
            db.session.flush()
            
            # Add transcript
            transcript = CallTranscript(
                call_id=call.id,
                speaker_id=alice_id,
                text='I mentioned this in the channel',
                timestamp=1.0
            )
            db.session.add(transcript)
            db.session.commit()
            
            # Verify flow
            assert msg.content == '@bob can you help?'
            assert call.status == 'active'
            assert transcript.text == 'I mentioned this in the channel'


class TestUnifiedSearch:
    """Test searching across all communication types."""
    
    def test_search_messages(self, setup_communication_env):
        """Test searching within channel messages."""
        env = setup_communication_env
        with env['app'].app_context():
            channel_id = env['channels']['general']
            alice_id = env['users']['alice']
            
            # Add messages with searchable content
            messages = [
                Message(content='Project deadline is Friday', channel_id=channel_id, sender_id=alice_id),
                Message(content='Budget meeting at 3pm', channel_id=channel_id, sender_id=alice_id),
                Message(content='Project review completed', channel_id=channel_id, sender_id=alice_id),
            ]
            db.session.add_all(messages)
            db.session.commit()
            
            # Search for 'project'
            results = Message.query.filter(
                Message.channel_id == channel_id,
                Message.content.ilike('%project%')
            ).all()
            
            assert len(results) == 2
    
    def test_search_transcripts(self, setup_communication_env):
        """Test searching within call transcripts."""
        env = setup_communication_env
        with env['app'].app_context():
            alice_id = env['users']['alice']
            bob_id = env['users']['bob']
            
            # Create call with transcript
            call = Call(
                team_id=env['team_id'],
                caller_id=alice_id,
                callee_id=bob_id,
                call_type='1-to-1',
                call_token='search-test',
                status='completed',
                started_at=datetime.utcnow(),
                ended_at=datetime.utcnow() + timedelta(minutes=5),
                duration=300
            )
            db.session.add(call)
            db.session.flush()
            
            # Add transcript segments
            segments = [
                CallTranscript(call_id=call.id, speaker_id=alice_id, text='Discussed the budget', timestamp=1.0),
                CallTranscript(call_id=call.id, speaker_id=bob_id, text='Budget approved', timestamp=2.0),
            ]
            db.session.add_all(segments)
            db.session.commit()
            
            # Search for 'budget'
            results = CallTranscript.query.filter(
                CallTranscript.call_id == call.id,
                CallTranscript.text.ilike('%budget%')
            ).all()
            
            assert len(results) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
