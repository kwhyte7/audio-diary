"""PostgreSQL storage layer (SQLAlchemy).

Everything except raw audio files lives in Postgres: users, sessions and
documents. Audio recordings stay on the filesystem because they're binary
blobs; their transcriptions are written next to the audio files.
"""

import os
import time

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Double,
    ForeignKey,
    String,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/audio_diary",
)


def _sqlalchemy_url(url):
    """Use the psycopg3 driver for plain postgresql:// URLs.

    SQLAlchemy defaults `postgresql://` to psycopg2, but we ship psycopg3.
    """
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


engine = create_engine(_sqlalchemy_url(DATABASE_URL), pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()


# JSONB on Postgres, generic JSON on SQLite (used by the tests).
ContentType = JSON().with_variant(JSONB(), "postgresql")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SessionRecord(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False, default="")
    description = Column(String, nullable=False, default="")
    content = Column(ContentType, nullable=False, default=dict)
    creation = Column(Double, nullable=False)
    last_modified = Column(Double, nullable=False)


def init_db(retries=30, delay=2):
    """Create tables if they don't exist yet.

    Retries a few times so the app container can start before Postgres has
    finished booting in docker-compose.
    """
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(engine)
            return
        except Exception as exc:  # noqa: BLE001 - retry any connection error
            print(f"[db] waiting for postgres ({attempt}/{retries}): {exc}")
            time.sleep(delay)

    raise RuntimeError("could not connect to postgres")


def _user_dict(user):
    return {"id": user.id, "email": user.email, "password_hash": user.password_hash}


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------


def create_user(user_id, email, password_hash):
    with SessionLocal() as session:
        session.add(User(id=user_id, email=email, password_hash=password_hash))
        session.commit()


def get_user_by_email(email):
    with SessionLocal() as session:
        user = session.query(User).filter(User.email == email).first()
        return _user_dict(user) if user else None


def get_user_by_id(user_id):
    with SessionLocal() as session:
        user = session.get(User, user_id)
        return _user_dict(user) if user else None


# --------------------------------------------------------------------------
# Sessions
# --------------------------------------------------------------------------


def create_session(session_id, user_id):
    with SessionLocal() as session:
        session.add(SessionRecord(id=session_id, user_id=user_id))
        session.commit()


def get_session(session_id):
    with SessionLocal() as session:
        record = session.get(SessionRecord, session_id)
        return {"id": record.id, "user_id": record.user_id} if record else None


def delete_session(session_id):
    with SessionLocal() as session:
        record = session.get(SessionRecord, session_id)
        if record:
            session.delete(record)
            session.commit()


# --------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------


def create_document(user_id, document_id, name):
    now = time.time()
    with SessionLocal() as session:
        session.add(
            Document(
                id=document_id,
                user_id=user_id,
                name=name,
                description="",
                content={},
                creation=now,
                last_modified=now,
            )
        )
        session.commit()


def get_documents(user_id):
    with SessionLocal() as session:
        docs = session.query(Document).filter(Document.user_id == user_id).all()
        return {
            doc.id: {
                "name": doc.name,
                "description": doc.description,
                "creation": doc.creation,
                "last_modified": doc.last_modified,
            }
            for doc in docs
        }


def load_document(user_id, document_id):
    with SessionLocal() as session:
        doc = (
            session.query(Document)
            .filter(Document.id == document_id, Document.user_id == user_id)
            .first()
        )
        if doc is None:
            return None
        return {
            "meta": {
                "name": doc.name,
                "description": doc.description,
                "creation": doc.creation,
                "last_modified": doc.last_modified,
            },
            "data": doc.content,
        }


def save_document(user_id, document_id, content, name=""):
    now = time.time()
    with SessionLocal() as session:
        doc = (
            session.query(Document)
            .filter(Document.id == document_id, Document.user_id == user_id)
            .first()
        )
        if doc is None:
            return
        doc.content = content
        if name:
            doc.name = name
        doc.last_modified = now
        session.commit()


def delete_document(user_id, document_id):
    with SessionLocal() as session:
        doc = (
            session.query(Document)
            .filter(Document.id == document_id, Document.user_id == user_id)
            .first()
        )
        if doc:
            session.delete(doc)
            session.commit()
