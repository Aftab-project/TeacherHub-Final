from app.models import FaceStudent, Message


def test_registration_and_login_flow(client):
    register_response = client.post(
        "/auth/register",
        data={
            "username": "newuser",
            "email": "newuser@test.local",
            "first_name": "New",
            "last_name": "User",
            "password": "password123",
            "password_confirm": "password123",
        },
        follow_redirects=False,
    )
    assert register_response.status_code == 302
    assert "/auth/login" in register_response.headers["Location"]

    login_response = client.post(
        "/auth/login",
        data={"username_or_email": "newuser", "password": "password123"},
        follow_redirects=False,
    )
    assert login_response.status_code == 302


def test_login_required_route_protection(client):
    response = client.get("/teams/", follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_team_membership_authorization_guard(client, login, seed_team_data):
    login("eve")

    response = client.get(f"/teams/{seed_team_data['team_id']}", follow_redirects=False)
    assert response.status_code == 302
    assert "/teams/" in response.headers["Location"]


def test_message_edit_delete_ownership_guard(client, login, seed_team_data):
    login("bob")

    edit_response = client.post(
        f"/messages/{seed_team_data['message_id']}/edit",
        data={"content": "Attempted overwrite"},
        follow_redirects=False,
    )
    assert edit_response.status_code == 403

    delete_response = client.post(
        f"/messages/{seed_team_data['message_id']}/delete",
        follow_redirects=False,
    )
    assert delete_response.status_code == 403


def test_message_owner_can_edit_and_delete(client, login, app, seed_team_data):
    login("alice")

    edit_response = client.post(
        f"/messages/{seed_team_data['message_id']}/edit",
        data={"content": "Updated by owner"},
        follow_redirects=False,
    )
    assert edit_response.status_code == 200

    with app.app_context():
        edited = Message.query.get(seed_team_data["message_id"])
        assert edited.content == "Updated by owner"

    delete_response = client.post(
        f"/messages/{seed_team_data['message_id']}/delete",
        follow_redirects=False,
    )
    assert delete_response.status_code == 200

    with app.app_context():
        deleted = Message.query.get(seed_team_data["message_id"])
        assert deleted is None


def test_attendance_sync_valid_payload(client, login, app, seed_users):
    login("alice")

    payload = {
        "studentsByClass": {
            "CS102": [
                {
                    "name": "Student A",
                    "email": "a@test.local",
                    "photoDataUrl": "data:image/png;base64,AAAA",
                    "descriptor": [0.1, 0.2, 0.3],
                }
            ]
        }
    }

    response = client.put("/api/face-students/sync", json=payload)
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["saved"] == 1

    with app.app_context():
        rows = FaceStudent.query.filter_by(class_name="CS102").all()
        assert len(rows) == 1


def test_attendance_sync_malformed_payload_rejected_without_data_loss(
    client, login, app, seed_face_record, seed_users
):
    login("alice")

    response = client.put("/api/face-students/sync", json={"studentsByClass": "bad"})
    assert response.status_code == 400

    with app.app_context():
        rows = FaceStudent.query.filter_by(class_name="CS101").all()
        assert len(rows) == 1
