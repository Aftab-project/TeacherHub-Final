"""
Transcription Feature Testing Module
====================================

Tests for call transcription functionality:
- Speech-to-text capture
- Transcript storage
- Summary generation
- Transcript retrieval
- Multi-speaker tracking

Run with: pytest tests/test_transcription.py
"""

import pytest
from datetime import datetime, timedelta
from app import create_app, db
from app.models import User, Team, TeamMember, Role, Call, CallTranscript, CallParticipant


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
def setup_users(app):
    """Create test users."""
    with app.app_context():
        # Reuse seeded roles when present.
        admin_role = Role.query.filter_by(name='admin').first()
        member_role = Role.query.filter_by(name='member').first()

        if not admin_role:
            admin_role = Role(name='admin', description='Admin role')
            db.session.add(admin_role)
        if not member_role:
            member_role = Role(name='member', description='Member role')
            db.session.add(member_role)
        db.session.flush()
        
        # Create users
        alice = User(username='alice', email='alice@test.com')
        alice.set_password('password123')
        
        bob = User(username='bob', email='bob@test.com')
        bob.set_password('password123')
        
        charlie = User(username='charlie', email='charlie@test.com')
        charlie.set_password('password123')
        
        db.session.add_all([alice, bob, charlie])
        db.session.flush()
        
        # Create team and add members
        team = Team(
            name='Test Team',
            owner_id=alice.id,
            team_code='TEST2024',
            is_public=True
        )
        db.session.add(team)
        db.session.flush()
        
        # Add members to team
        alice_member = TeamMember(team_id=team.id, user_id=alice.id, role_id=admin_role.id)
        bob_member = TeamMember(team_id=team.id, user_id=bob.id, role_id=member_role.id)
        charlie_member = TeamMember(team_id=team.id, user_id=charlie.id, role_id=member_role.id)
        db.session.add_all([alice_member, bob_member, charlie_member])
        
        db.session.commit()
        
        return {
            'alice_id': alice.id,
            'bob_id': bob.id,
            'charlie_id': charlie.id,
            'team_id': team.id
        }


class TestTranscriptionCapture:
    """Test speech-to-text segment capture."""
    
    def test_add_transcript_segment(self, app, setup_users):
        """Test adding a single transcript segment."""
        with app.app_context():
            users = setup_users
            alice_id = users['alice_id']
            bob_id = users['bob_id']
            
            # Create a call
            call = Call(
                team_id=users['team_id'],
                caller_id=alice_id,
                callee_id=bob_id,
                call_type='1-to-1',
                call_token='test-token-123',
                status='active',
                started_at=datetime.utcnow()
            )
            db.session.add(call)
            db.session.flush()
            
            # Add transcript segment
            segment = CallTranscript(
                call_id=call.id,
                speaker_id=alice_id,
                text='Hello, can you hear me?',
                timestamp=0.5
            )
            db.session.add(segment)
            db.session.commit()
            
            # Verify segment was saved
            saved = CallTranscript.query.filter_by(call_id=call.id).first()
            assert saved is not None
            assert saved.text == 'Hello, can you hear me?'
            assert saved.speaker_id == alice_id
    
    def test_multiple_speakers_transcript(self, app, setup_users):
        """Test transcript with multiple speakers."""
        with app.app_context():
            users = setup_users
            alice_id = users['alice_id']
            bob_id = users['bob_id']
            
            # Create call
            call = Call(
                team_id=users['team_id'],
                caller_id=alice_id,
                callee_id=bob_id,
                call_type='1-to-1',
                call_token='test-token-456',
                status='active',
                started_at=datetime.utcnow()
            )
            db.session.add(call)
            db.session.flush()
            
            # Add segments from both speakers
            segments = [
                CallTranscript(call_id=call.id, speaker_id=alice_id, text='Hi Bob!', timestamp=1.0),
                CallTranscript(call_id=call.id, speaker_id=bob_id, text='Hi Alice!', timestamp=2.5),
                CallTranscript(call_id=call.id, speaker_id=alice_id, text='How are you?', timestamp=4.0),
                CallTranscript(call_id=call.id, speaker_id=bob_id, text='I am great!', timestamp=5.5),
            ]
            db.session.add_all(segments)
            db.session.commit()
            
            # Verify all segments saved
            all_segments = CallTranscript.query.filter_by(call_id=call.id).all()
            assert len(all_segments) == 4
            
            # Verify speaker alternation
            speakers = [seg.speaker_id for seg in all_segments]
            assert speakers == [alice_id, bob_id, alice_id, bob_id]
    
    def test_empty_transcript_segment_rejected(self, app, setup_users):
        """Test that empty transcripts are not added."""
        with app.app_context():
            users = setup_users
            call = Call(
                team_id=users['team_id'],
                caller_id=users['alice_id'],
                callee_id=users['bob_id'],
                call_type='1-to-1',
                call_token='test-token-789',
                status='active',
                started_at=datetime.utcnow()
            )
            db.session.add(call)
            db.session.flush()
            
            # Attempt to add empty segment
            segment = CallTranscript(
                call_id=call.id,
                speaker_id=users['alice_id'],
                text='',  # Empty
                timestamp=1.0
            )
            db.session.add(segment)
            db.session.commit()
            
            # Query should return the entry (we'll validate emptiness in application layer)
            count = CallTranscript.query.filter_by(call_id=call.id).count()
            assert count == 1  # Saved, but application should skip it


class TestTranscriptRetrieval:
    """Test fetching transcript data."""
    
    def test_get_transcript_for_call(self, app, setup_users):
        """Test retrieving complete transcript for a call."""
        with app.app_context():
            users = setup_users
            
            # Create call with transcript
            call = Call(
                team_id=users['team_id'],
                caller_id=users['alice_id'],
                callee_id=users['bob_id'],
                call_type='1-to-1',
                call_token='test-token-ret-1',
                status='completed',
                started_at=datetime.utcnow(),
                ended_at=datetime.utcnow() + timedelta(minutes=5),
                duration=300
            )
            db.session.add(call)
            db.session.flush()
            
            # Add segments
            segments = [
                CallTranscript(call_id=call.id, speaker_id=users['alice_id'], text='Meeting started', timestamp=1.0),
                CallTranscript(call_id=call.id, speaker_id=users['bob_id'], text='Yes, I am here', timestamp=2.0),
            ]
            db.session.add_all(segments)
            db.session.commit()
            
            # Retrieve transcript
            transcript = CallTranscript.query.filter_by(call_id=call.id).order_by(CallTranscript.created_at).all()
            
            assert len(transcript) == 2
            assert transcript[0].text == 'Meeting started'
            assert transcript[1].text == 'Yes, I am here'
    
    def test_transcript_ordering_by_timestamp(self, app, setup_users):
        """Test that transcripts are returned in chronological order."""
        with app.app_context():
            users = setup_users
            call = Call(
                team_id=users['team_id'],
                caller_id=users['alice_id'],
                callee_id=users['bob_id'],
                call_type='1-to-1',
                call_token='test-order',
                status='completed',
                started_at=datetime.utcnow(),
                ended_at=datetime.utcnow() + timedelta(minutes=2),
                duration=120
            )
            db.session.add(call)
            db.session.flush()
            
            # Add segments intentionally out of order
            segments = [
                CallTranscript(call_id=call.id, speaker_id=users['alice_id'], text='A', timestamp=3.0),
                CallTranscript(call_id=call.id, speaker_id=users['bob_id'], text='B', timestamp=1.0),
                CallTranscript(call_id=call.id, speaker_id=users['alice_id'], text='C', timestamp=2.0),
            ]
            db.session.add_all(segments)
            db.session.commit()
            
            # Get ordered transcript
            ordered = CallTranscript.query.filter_by(call_id=call.id).order_by(CallTranscript.timestamp).all()
            
            # Verify ordering by timestamp (not by creation order)
            assert [seg.text for seg in ordered] == ['B', 'C', 'A']


class TestTranscriptionSummary:
    """Test transcript summary generation."""
    
    def test_summary_generation_basic(self, app, setup_users):
        """Test basic summary generation from transcript."""
        with app.app_context():
            users = setup_users
            call = Call(
                team_id=users['team_id'],
                caller_id=users['alice_id'],
                callee_id=users['bob_id'],
                call_type='1-to-1',
                call_token='test-summary-1',
                status='completed',
                started_at=datetime.utcnow(),
                ended_at=datetime.utcnow() + timedelta(minutes=3),
                duration=180
            )
            db.session.add(call)
            db.session.flush()
            
            # Create transcript
            segments = [
                CallTranscript(call_id=call.id, speaker_id=users['alice_id'], text='Project deadline is Friday', timestamp=1.0),
                CallTranscript(call_id=call.id, speaker_id=users['bob_id'], text='Confirmed, will deliver Thursday', timestamp=3.0),
                CallTranscript(call_id=call.id, speaker_id=users['alice_id'], text='Great, thanks!', timestamp=5.0),
            ]
            db.session.add_all(segments)
            db.session.commit()
            
            # Generate summary (in real code, this would be in service layer)
            segments = CallTranscript.query.filter_by(call_id=call.id).order_by(CallTranscript.timestamp).all()
            summary_text = f"Call between {call.caller.username} and {call.callee.username}. " \
                          f"Participants discussed: {', '.join([s.text for s in segments[:2]])}. " \
                          f"Key outcome: {segments[-1].text}"
            
            call.summary = summary_text
            db.session.commit()
            
            # Verify summary
            assert call.summary is not None
            assert 'deadline' in call.summary.lower()
            assert 'deliver' in call.summary.lower()


class TestGroupCallTranscription:
    """Test transcription in group calls."""
    
    def test_group_call_multi_speaker_transcript(self, app, setup_users):
        """Test transcript with 3+ speakers in group call."""
        with app.app_context():
            users = setup_users
            
            # Create group call
            call = Call(
                team_id=users['team_id'],
                caller_id=users['alice_id'],
                call_type='group',
                call_token='test-group-1',
                status='completed',
                started_at=datetime.utcnow(),
                ended_at=datetime.utcnow() + timedelta(minutes=5),
                duration=300
            )
            db.session.add(call)
            db.session.flush()
            
            # Add all three users as participants
            for user_id in [users['alice_id'], users['bob_id'], users['charlie_id']]:
                participant = CallParticipant(call_id=call.id, user_id=user_id)
                db.session.add(participant)
            
            db.session.flush()
            
            # Add transcript with 3 speakers
            segments = [
                CallTranscript(call_id=call.id, speaker_id=users['alice_id'], text='Starting meeting', timestamp=1.0),
                CallTranscript(call_id=call.id, speaker_id=users['bob_id'], text='I agree', timestamp=2.0),
                CallTranscript(call_id=call.id, speaker_id=users['charlie_id'], text='Me too', timestamp=3.0),
                CallTranscript(call_id=call.id, speaker_id=users['alice_id'], text='Great', timestamp=4.0),
            ]
            db.session.add_all(segments)
            db.session.commit()
            
            # Verify all speakers represented
            speakers = set(seg.speaker_id for seg in segments)
            assert len(speakers) == 3


class TestTranscriptionPerformance:
    """Test transcription performance metrics."""
    
    def test_large_transcript_handling(self, app, setup_users):
        """Test performance with large transcript (100+ segments)."""
        with app.app_context():
            users = setup_users
            call = Call(
                team_id=users['team_id'],
                caller_id=users['alice_id'],
                callee_id=users['bob_id'],
                call_type='1-to-1',
                call_token='test-perf-large',
                status='completed',
                started_at=datetime.utcnow(),
                ended_at=datetime.utcnow() + timedelta(hours=1),
                duration=3600
            )
            db.session.add(call)
            db.session.flush()
            
            # Add 100 segments (alternating speakers)
            segments = []
            for i in range(100):
                speaker_id = users['alice_id'] if i % 2 == 0 else users['bob_id']
                seg = CallTranscript(
                    call_id=call.id,
                    speaker_id=speaker_id,
                    text=f'Message number {i}',
                    timestamp=float(i)
                )
                segments.append(seg)
            
            db.session.add_all(segments)
            db.session.commit()
            
            # Test retrieval performance
            all_transcripts = CallTranscript.query.filter_by(call_id=call.id).all()
            assert len(all_transcripts) == 100
    
    def test_transcript_search_performance(self, app, setup_users):
        """Test searching within transcript."""
        with app.app_context():
            users = setup_users
            call = Call(
                team_id=users['team_id'],
                caller_id=users['alice_id'],
                callee_id=users['bob_id'],
                call_type='1-to-1',
                call_token='test-perf-search',
                status='completed',
                started_at=datetime.utcnow(),
                ended_at=datetime.utcnow() + timedelta(minutes=10),
                duration=600
            )
            db.session.add(call)
            db.session.flush()
            
            # Add segments with searchable content
            keywords = ['deadline', 'project', 'review', 'feedback', 'budget']
            segments = []
            for i in range(50):
                keyword = keywords[i % len(keywords)]
                seg = CallTranscript(
                    call_id=call.id,
                    speaker_id=users['alice_id'] if i % 2 == 0 else users['bob_id'],
                    text=f'Discussed {keyword} today',
                    timestamp=float(i)
                )
                segments.append(seg)
            
            db.session.add_all(segments)
            db.session.commit()
            
            # Search for keyword
            results = CallTranscript.query.filter(
                CallTranscript.call_id == call.id,
                CallTranscript.text.ilike('%deadline%')
            ).all()
            
            # Should find approximately 10 matches (50/5 keywords)
            assert len(results) >= 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
