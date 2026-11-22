import db


def test_save_and_load_document_roundtrip(db_session):
    """Regression test: a Quill dict must survive a save/load round-trip."""
    db.create_user("u1", "me@example.com", "hash")
    db.create_document("u1", "doc1", "My doc")

    content = {"ops": [{"insert": "hello"}]}
    db.save_document("u1", "doc1", content, "Renamed doc")

    loaded = db.load_document("u1", "doc1")

    assert loaded is not None
    assert loaded["data"] == content
    assert loaded["meta"]["name"] == "Renamed doc"


def test_save_document_keeps_existing_name_when_name_is_empty(db_session):
    db.create_user("u1", "me@example.com", "hash")
    db.create_document("u1", "doc1", "My doc")

    db.save_document("u1", "doc1", {"ops": []}, "")

    loaded = db.load_document("u1", "doc1")
    assert loaded["meta"]["name"] == "My doc"


def test_get_documents_returns_metadata(db_session):
    db.create_user("u1", "me@example.com", "hash")
    db.create_document("u1", "doc1", "First")
    db.create_document("u1", "doc2", "Second")

    docs = db.get_documents("u1")

    assert set(docs.keys()) == {"doc1", "doc2"}
    assert docs["doc1"]["name"] == "First"
    assert docs["doc2"]["name"] == "Second"


def test_delete_document(db_session):
    db.create_user("u1", "me@example.com", "hash")
    db.create_document("u1", "doc1", "First")

    db.delete_document("u1", "doc1")

    assert db.load_document("u1", "doc1") is None
