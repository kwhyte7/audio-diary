"""PostgreSQL storage layer.

This replaces the old JSON-file storage. Everything except raw audio files
now lives in Postgres: users, sessions and documents. Audio recordings stay
on the filesystem because they're binary blobs; their transcriptions are
written next to the audio files and the document text is stored in Postgres.
"""

import os
import time

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/audio_diary",
)


def get_conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db(retries=30, delay=2):
    """Create tables if they don't exist yet.

    Retries a few times so the app container can start before Postgres has
    finished booting in docker-compose.
    """
    for attempt in range(1, retries + 1):
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS users (
                            id TEXT PRIMARY KEY,
                            email TEXT UNIQUE NOT NULL,
                            password_hash TEXT NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS sessions (
                            id TEXT PRIMARY KEY,
                            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS documents (
                            id TEXT PRIMARY KEY,
                            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                            name TEXT NOT NULL DEFAULT '',
                            description TEXT NOT NULL DEFAULT '',
                            content JSONB NOT NULL DEFAULT '{}'::jsonb,
                            creation DOUBLE PRECISION NOT NULL,
                            last_modified DOUBLE PRECISION NOT NULL
                        )
                        """
                    )
                    cur.execute(
                        "CREATE INDEX IF NOT EXISTS idx_documents_user_id "
                        "ON documents(user_id)"
                    )
                    cur.execute(
                        "CREATE INDEX IF NOT EXISTS idx_sessions_user_id "
                        "ON sessions(user_id)"
                    )
            return
        except psycopg.OperationalError as exc:
            print(f"[db] waiting for postgres ({attempt}/{retries}): {exc}")
            time.sleep(delay)

    raise RuntimeError("could not connect to postgres")


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------


def create_user(user_id, email, password_hash):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (id, email, password_hash) VALUES (%s, %s, %s)",
                (user_id, email, password_hash),
            )


def get_user_by_email(email):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            return cur.fetchone()


def get_user_by_id(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cur.fetchone()


# --------------------------------------------------------------------------
# Sessions
# --------------------------------------------------------------------------


def create_session(session_id, user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (id, user_id) VALUES (%s, %s)",
                (session_id, user_id),
            )


def get_session(session_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM sessions WHERE id = %s", (session_id,))
            return cur.fetchone()


def delete_session(session_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE id = %s", (session_id,))


# --------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------


def create_document(user_id, document_id, name):
    now = time.time()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents
                    (id, user_id, name, description, content, creation, last_modified)
                VALUES (%s, %s, %s, '', '{}'::jsonb, %s, %s)
                """,
                (document_id, user_id, name, now, now),
            )


def get_documents(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, description, creation, last_modified
                FROM documents
                WHERE user_id = %s
                """,
                (user_id,),
            )
            rows = cur.fetchall()

    return {
        row["id"]: {
            "name": row["name"],
            "description": row["description"],
            "creation": row["creation"],
            "last_modified": row["last_modified"],
        }
        for row in rows
    }


def load_document(user_id, document_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT name, description, content, creation, last_modified
                FROM documents
                WHERE id = %s AND user_id = %s
                """,
                (document_id, user_id),
            )
            row = cur.fetchone()

    if row is None:
        return None

    return {
        "meta": {
            "name": row["name"],
            "description": row["description"],
            "creation": row["creation"],
            "last_modified": row["last_modified"],
        },
        "data": row["content"],
    }


def save_document(user_id, document_id, content, name=""):
    now = time.time()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE documents
                SET content = %s,
                    name = CASE WHEN %s = '' THEN name ELSE %s END,
                    last_modified = %s
                WHERE id = %s AND user_id = %s
                """,
                (content, name, name, now, document_id, user_id),
            )


def delete_document(user_id, document_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM documents WHERE id = %s AND user_id = %s",
                (document_id, user_id),
            )
