import os

import pytest

from app import create_app, db
from app.models import (
    Channel,
    FaceStudent,
    Message,
    Role,
    Team,
    TeamMember,
    User,
)


@pytest.fixture
def app():
    original_env = os.environ.get("FLASK_ENV")
    os.environ["FLASK_ENV"] = "testing"

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with app.app_context():
        db.drop_all()
        db.create_all()

        # App startup seeds roles before this fixture resets the DB,
        # so create them again for every isolated test database.
        if not Role.query.filter_by(name="admin").first():
            db.session.add(Role(name="admin", description="Team administrator with full permissions"))
        if not Role.query.filter_by(name="member").first():
            db.session.add(Role(name="member", description="Regular team member"))
        db.session.commit()

        yield app
        db.session.remove()
        db.drop_all()

    if original_env is None:
        os.environ.pop("FLASK_ENV", None)
    else:
        os.environ["FLASK_ENV"] = original_env


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed_users(app):
    with app.app_context():
        alice = User(username="alice", email="alice@test.local")
        alice.set_password("password123")

        bob = User(username="bob", email="bob@test.local")
        bob.set_password("password123")

        eve = User(username="eve", email="eve@test.local")
        eve.set_password("password123")

        db.session.add_all([alice, bob, eve])
        db.session.commit()

        return {"alice": alice.id, "bob": bob.id, "eve": eve.id}


@pytest.fixture
def seed_team_data(app, seed_users):
    with app.app_context():
        admin_role = Role.query.filter_by(name="admin").first()
        member_role = Role.query.filter_by(name="member").first()

        team = Team(
            name="Secure Team",
            description="Team for authorization tests",
            owner_id=seed_users["alice"],
            team_code="SECURE01",
            is_public=True,
        )
        db.session.add(team)
        db.session.flush()

        channel = Channel(
            name="general",
            team_id=team.id,
            created_by_id=seed_users["alice"],
        )
        db.session.add(channel)
        db.session.flush()

        db.session.add_all(
            [
                TeamMember(team_id=team.id, user_id=seed_users["alice"], role_id=admin_role.id),
                TeamMember(team_id=team.id, user_id=seed_users["bob"], role_id=member_role.id),
            ]
        )

        message = Message(
            content="Owned by Alice",
            channel_id=channel.id,
            sender_id=seed_users["alice"],
        )
        db.session.add(message)

        db.session.commit()

        return {
            "team_id": team.id,
            "channel_id": channel.id,
            "message_id": message.id,
        }


@pytest.fixture
def seed_face_record(app, seed_users):
    with app.app_context():
        row = FaceStudent(
            user_id=seed_users["alice"],
            class_name="CS101",
            name="Student One",
            email="student.one@test.local",
            photo_data_url="data:image/png;base64,abc",
            descriptor_json="[0.1, 0.2, 0.3]",
        )
        db.session.add(row)
        db.session.commit()


@pytest.fixture
def login(client):
    def _login(username_or_email, password="password123"):
        return client.post(
            "/auth/login",
            data={"username_or_email": username_or_email, "password": password},
            follow_redirects=False,
        )

    return _login
