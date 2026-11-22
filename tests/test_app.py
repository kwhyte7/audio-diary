import pytest

import app


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


def test_signup_accepts_valid_email_and_creates_session(client, monkeypatch):
    created = {}

    monkeypatch.setattr(app.db, "get_user_by_email", lambda email: None)

    def fake_create_user(uid, email, password_hash):
        created["user_id"] = uid
        created["email"] = email

    def fake_create_session(session_id, uid):
        created["session_id"] = session_id

    monkeypatch.setattr(app.db, "create_user", fake_create_user)
    monkeypatch.setattr(app.db, "create_session", fake_create_session)

    res = client.post(
        "/signup", json={"email": "me@example.com", "password": "password123"}
    )
    data = res.get_json()

    assert data["success"] is True
    assert created["email"] == "me@example.com"
    assert "user_id" in created
    assert "session_id" in created


def test_signup_rejects_existing_email(client, monkeypatch):
    monkeypatch.setattr(
        app.db,
        "get_user_by_email",
        lambda email: {"id": "u1", "email": email, "password_hash": "x"},
    )

    res = client.post(
        "/signup", json={"email": "me@example.com", "password": "password123"}
    )
    data = res.get_json()

    assert data["success"] is False
    assert "already in use" in data["message"]


def test_save_document_passes_content_to_db(client, monkeypatch):
    monkeypatch.setattr(
        app, "find_user_from_session", lambda: {"id": "u1", "email": "me@example.com"}
    )

    captured = {}

    def fake_save(uid, doc_id, content, name):
        captured.update(uid=uid, doc_id=doc_id, content=content, name=name)

    monkeypatch.setattr(app.db, "save_document", fake_save)

    res = client.post(
        "/documents/save/doc1",
        json={"content": {"ops": [{"insert": "hi"}]}, "name": "My doc"},
    )

    assert res.status_code == 200
    assert captured["uid"] == "u1"
    assert captured["doc_id"] == "doc1"
    assert captured["content"] == {"ops": [{"insert": "hi"}]}
    assert captured["name"] == "My doc"
