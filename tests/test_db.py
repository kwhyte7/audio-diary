from psycopg.types.json import Jsonb

import db


class FakeCursor:
    def __init__(self):
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()

    def cursor(self):
        return self.cursor_obj

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_save_document_wraps_content_in_jsonb(monkeypatch):
    """Regression test: a Quill dict must be adapted to jsonb, not '%s'."""
    conn = FakeConnection()
    monkeypatch.setattr(db, "get_conn", lambda: conn)

    content = {"ops": [{"insert": "hello"}]}
    db.save_document("user1", "doc1", content, "My doc")

    sql, params = conn.cursor_obj.executed[0]

    assert isinstance(params[0], Jsonb)
    assert params[0].obj == content
    assert params[1] == "My doc"
    assert params[2] == "My doc"
    assert params[4] == "doc1"
    assert params[5] == "user1"


def test_save_document_keeps_existing_name_when_name_is_empty(monkeypatch):
    conn = FakeConnection()
    monkeypatch.setattr(db, "get_conn", lambda: conn)

    db.save_document("user1", "doc1", {"ops": []}, "")

    sql, params = conn.cursor_obj.executed[0]
    assert params[1] == ""
    assert params[2] == ""
    assert "CASE WHEN %s = '' THEN name ELSE %s END" in sql


def test_create_document_inserts_rows(monkeypatch):
    conn = FakeConnection()
    monkeypatch.setattr(db, "get_conn", lambda: conn)

    db.create_document("user1", "doc1", "My doc")

    sql, params = conn.cursor_obj.executed[0]
    assert "INSERT INTO documents" in sql
    assert params[0] == "doc1"
    assert params[1] == "user1"
    assert params[2] == "My doc"
