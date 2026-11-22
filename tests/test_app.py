import pytest

import app
import db


@pytest.fixture
def client():
    app.app.config["TESTING"] = True
    return app.app.test_client()


def test_is_valid_email():
    assert app.is_valid_email("me@example.com")
    assert not app.is_valid_email("not-an-email")
    assert not app.is_valid_email("me@example")
    assert not app.is_valid_email("me example.com")


def test_signup_rejects_invalid_email(client):
    res = client.post(
        "/signup", json={"email": "not-an-email", "password": "password123"}
    )
    data = res.get_json()

    assert data["success"] is False
    assert "valid email" in data["message"]


def test_signup_accepts_valid_email_and_creates_session(client, db_session):
    res = client.post(
        "/signup", json={"email": "me@example.com", "password": "password123"}
    )
    data = res.get_json()

    assert data["success"] is True
    user = db.get_user_by_email("me@example.com")
    assert user is not None
    assert user["email"] == "me@example.com"


def test_signup_rejects_existing_email(client, db_session):
    db.create_user("u1", "me@example.com", "hash")

    res = client.post(
        "/signup", json={"email": "me@example.com", "password": "password123"}
    )
    data = res.get_json()

    assert data["success"] is False
    assert "already in use" in data["message"]


def test_save_document_end_to_end(client, db_session, monkeypatch):
    """The whole Flask -> db -> JSON column path must work end to end."""
    db.create_user("u1", "me@example.com", "hash")
    db.create_document("u1", "doc1", "My doc")

    monkeypatch.setattr(
        app, "find_user_from_session", lambda: {"id": "u1", "email": "me@example.com"}
    )

    content = {"ops": [{"insert": "hello"}]}
    res = client.post(
        "/documents/save/doc1",
        json={"content": content, "name": "Renamed"},
    )

    assert res.status_code == 200
    loaded = db.load_document("u1", "doc1")
    assert loaded["data"] == content
    assert loaded["meta"]["name"] == "Renamed"
