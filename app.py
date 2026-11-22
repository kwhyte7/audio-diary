#!/usr/bin/env python3

import os
import random
import shutil
import time
from functools import wraps

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

import db
from transcribe import transcribe

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "somesecretkey")


def generate_id(name_of=""):
    return (
        name_of
        + "_"
        + str(time.time()).replace(".", "")
        + str(random.randint(0, 99999))
    )


def find_user_from_session():
    """Return the logged-in user row, or None."""
    session_id = session.get("cookie")
    if not session_id:
        return None

    session_row = db.get_session(session_id)
    if session_row is None:
        return None

    return db.get_user_by_id(session_row["user_id"])


def needs_user(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user = find_user_from_session()
        if user:
            return func(user, *args, **kwargs)
        return redirect(url_for("_login"))

    return wrapper


# --------------------------------------------------------------------------
# Filesystem helpers for audio recordings
# --------------------------------------------------------------------------


def get_user_folder(user_id):
    path = f"./data/{user_id}"
    os.makedirs(path, exist_ok=True)
    return path


def get_document_path(user_id, document_id):
    path = os.path.join(get_user_folder(user_id), document_id)
    os.makedirs(path, exist_ok=True)
    return path


def get_recording_path(user_id, document_id):
    path = os.path.join(get_document_path(user_id, document_id), "recordings")
    os.makedirs(path, exist_ok=True)
    return path


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------


@app.route("/login", methods=["POST", "GET"])
def _login():
    if request.method == "GET":
        return render_template("login.html")

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required."})

    user = db.get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "message": "Invalid email or password."})

    new_session_id = generate_id("session")
    db.create_session(new_session_id, user["id"])
    session["cookie"] = new_session_id

    return jsonify({"success": True, "message": "Successfully logged in."})


@app.route("/signup", methods=["POST", "GET"])
def _signup():
    if request.method == "GET":
        return render_template("signup.html")

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required."})

    if len(password) < 8:
        return jsonify(
            {"success": False, "message": "Password must be at least 8 characters."}
        )

    if db.get_user_by_email(email) is not None:
        return jsonify(
            {"success": False, "message": "That email is already in use."}
        )

    user_id = generate_id("user")
    db.create_user(user_id, email, generate_password_hash(password))

    # Log the new user straight in so /signup can redirect home.
    new_session_id = generate_id("session")
    db.create_session(new_session_id, user_id)
    session["cookie"] = new_session_id

    return jsonify({"success": True, "message": f"Account created for {email}."})


@app.route("/logout")
def _logout():
    session_id = session.get("cookie")
    if session_id:
        db.delete_session(session_id)
    session.pop("cookie", None)
    return redirect(url_for("_login"))


# --------------------------------------------------------------------------
# Pages and documents
# --------------------------------------------------------------------------


@app.route("/", methods=["POST", "GET"])
@needs_user
def _index(user):
    return render_template("index.html")


@app.route("/documents", methods=["GET"])
@needs_user
def _documents(user):
    return db.get_documents(user["id"])


@app.route("/documents/new", methods=["POST"])
@needs_user
def _documents_new_doc_name(user):
    doc_name = request.get_data(as_text=True).strip()
    if not doc_name:
        doc_name = "Untitled document"

    document_id = generate_id("document")
    db.create_document(user["id"], document_id, doc_name)
    return jsonify({"success": True, "id": document_id})


@app.route("/documents/load/<doc_id>")
@needs_user
def _documents_load_doc_id(user, doc_id):
    document = db.load_document(user["id"], doc_id)
    if document is None:
        return jsonify({"error": "Document not found"}), 404
    return document


@app.route("/documents/delete/<doc_id>", methods=["DELETE"])
@needs_user
def _document_delete_doc_id(user, doc_id):
    db.delete_document(user["id"], doc_id)
    shutil.rmtree(get_document_path(user["id"], doc_id), ignore_errors=True)
    return "success"


@app.route("/documents/save/<doc_id>", methods=["POST"])
@needs_user
def _document_save_doc_id(user, doc_id):
    data = request.get_json(silent=True) or {}
    quilldata = data.get("content")
    namedata = (data.get("name") or "").strip()

    if quilldata is None:
        return jsonify({"error": "Missing content"}), 400

    db.save_document(user["id"], doc_id, quilldata, namedata)
    return "success"


@app.route("/documents/edit")
@needs_user
def _documents_edit(user):
    return render_template("editor.html")


@app.route("/record", methods=["GET", "POST"])
@needs_user
def _record(user):
    return render_template("client-side-recorder.html")


@app.route("/upload/recordings/<doc_id>", methods=["POST"])
@needs_user
def _upload_audio(user, doc_id):
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    file = request.files["audio"]
    if not file or not file.filename:
        return jsonify({"error": "No file selected"}), 400

    file_extension = (
        "." in file.filename and file.filename.split(".")[-1].lower()
    ) or "wav"

    recording_id = generate_id("recording")
    audio_filename = f"{recording_id}.{file_extension}"
    filepath = get_recording_path(user["id"], doc_id)
    audio_filepath = os.path.join(filepath, audio_filename)
    file.save(audio_filepath)

    raw_transcription = transcribe(audio_filepath)
    with open(os.path.join(filepath, f"{recording_id}.txt"), "w") as f:
        f.write(raw_transcription)

    return jsonify({"content": raw_transcription, "success": True}), 200


@app.route("/upload/recording/<doc_id>", methods=["POST"])
@needs_user
def _upload_audio_singular(user, doc_id):
    # Older recorder page uses the singular path; keep it working.
    return _upload_audio(user, doc_id)


if __name__ == "__main__":
    db.init_db()
    app.run(host="0.0.0.0", debug=False, port=8082)
