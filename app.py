#!/usr/bin/env python3

import json
import time
import random
import glob
import os
import shutil
from functools import wraps
from transcribe import transcribe
from flask import Flask, session, jsonify, render_template, redirect, url_for, request
from werkzeug.security import generate_password_hash, check_password_hash

with open("./.env", "r") as f:
    env = json.load(f)

app = Flask(__name__)
app.config["SECRET_KEY"] = env["SECRET_KEY"]

users = {}
sessions = {}
data = {}
documents = {}

def generate_id(name_of=""):
    return name_of + "_" + str(time.time()).replace(".","") + str( random.randint(0, 99999) )

def create_session(user):
    new_session = {
        "id" : generate_id("session"),
        "username" : user.data["email"]
    }

    user.data["active_sessions"].append(new_session["id"])
    sessions[new_session["id"]] = new_session
    return new_session

def find_user_from_session():
    # see if session cookie in sessions (as id)
    cookie = session.get("cookie")

    if cookie and cookie in sessions.keys():
        linked_session = sessions[cookie]
        username = linked_session["username"]
        if username in users.keys():
            user = users[username]
            if cookie in user.data["active_sessions"]:
                return user
            else:
                del sessions["cookie"]
    return None

def save_users_and_sessions():
    with open("./data/users_and_sessions.json", "w") as f:
        json.dump({
            "users" : {k:v.serialise() for k,v in users.items()},
            "sessions" : sessions
        }, f)
    return

def load_users_and_sessions():
    global users
    global sessions
    if os.path.exists("./data/users_and_sessions.json"):
        with open("./data/users_and_sessions.json", "r") as f:
            #users, sessions = json.load(f).values()
            data = json.load(f)
            users = {k:User.from_json(v) for k,v in data["users"].items()}
            sessions = data["sessions"]
    else:
        print("./data/users_and_sessions.json does not exist: will not load data.")
    return

def needs_user(func): # decorator to check that the client is logged in
    @wraps(func)
    def wrapper(*args, **kwargs):
        user = find_user_from_session() # will use flask session 
        if user:
            return func(user, *args, **kwargs)
        return redirect(url_for("_login"))
    
    return wrapper

class User():
    def __init__(self, email, password):
        self.data = {
            "id" : generate_id("user"),
            "email" : email,
            "password_hash" : generate_password_hash(password),
            "active_sessions" : [],
            "documents" : [],
            "encrypt_data_with_hash" : False
        }
        return

    @staticmethod
    def from_json(data):
        user = User("email", "password")
        user.data = data
        return user

    def serialise(self):
        return self.data

    def login_with_password(self, password):
        if check_password_hash(self.data["password_hash"], password):
            new_session = create_session(self)
            save_sessions() # the browser will save it client side
        return new_session

    def logout(self):
        for session_id in self.data["active_sessions"]:
            if session_id in sessions:
                del sessions[session_id]
            else:
                print(f"[{user['email']}] {session_id} not found in sessions, skipping.")

        self.data["active_sessions"] = []

        save_sessions()
        return

    def get_folder_path(self):
        path = f"./data/{self.data['id']}"
        os.makedirs(path, exist_ok=True)
        return path

    def get_document_path(self, document_id):
        path = os.path.join(self.get_folder_path(), document_id)
        os.makedirs(path, exist_ok=True)
        return path

    def delete_document_path(self, document_id):
        shutil.rmtree(self.get_document_path(document_id))
        return

    def get_document_recording_path(self, document_id):
        path = os.path.join(self.get_document_path(document_id), "recordings")
        os.makedirs(path, exist_ok=True)
        return path

    def get_document_ids(self):
        return [os.path.basename(os.path.dirname(path)) for path in glob.glob(os.path.join(self.get_folder_path(), "*/"))]
    
    def get_documents(self):
        docs = {}

        for document_id in self.get_document_ids():
            docs[document_id] = self.load_document_meta(document_id)

        return docs 

    def new_document(self, name):
        document_id = generate_id("document")
        document_path = self.get_document_path(document_id)
        with open(os.path.join(document_path, "doc.json"), "w") as f:
            f.write("{}")

        with open(os.path.join(document_path, "meta.json"), "w") as f:
            json.dump({"name" : name, "description" : "", "creation" : time.time(), "last_modified" : time.time()}, f)

        return
    
    def load_document_meta(self, document_id):
        
        with open(os.path.join(self.get_document_path(document_id), "meta.json")) as f:
            return json.load(f)

    def load_document(self, document_id):
        document_path = self.get_document_path(document_id)
        
        with open(os.path.join(document_path, "meta.json")) as f:
            meta = json.load(f)

        with open(os.path.join(document_path, "doc.json")) as f:
            data = json.load(f)

        return {"meta" : meta, "data" : data}

    def save_document(self, document_id, json_content, name=""):
        document_path = self.get_document_path(document_id)
        
        with open(os.path.join(document_path, "meta.json")) as f:
            meta = json.load(f)

        if name:
            meta["name"] = name

        meta["last_modified"] = time.time()

        with open(os.path.join(document_path, "meta.json"), "w") as f:
            json.dump(meta, f)

        with open(os.path.join(document_path, "doc.json"), "w") as f:
            json.dump(json_content, f)

        return

@app.route("/login", methods = ["POST", "GET"])
def _login():
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":

        # get data,
        data = request.json
        email = data["email"]
        password = data["password"]
        # check password
        # check user exists, then password
        if email in users.keys():
            # if user exists, check password is valid
            user = users[email]

            if check_password_hash(user.data["password_hash"], password):
                new_session = create_session(user)
                session["cookie"] = new_session["id"]
                
                save_users_and_sessions()

                return jsonify({"success" : True, "message" : "Successfully logged in"})

        return jsonify({"success" : False, "message" : "Invalid email or password"})
        
@app.route("/signup", methods = ["POST", "GET"])
def _signup():
    if request.method == "GET":
        return render_template("signup.html")
    elif request.method == "POST":
        data = request.json
        
        email = data["email"]
        password = data["password"]

        # ensure there's no existing user with username
        if email in users.keys():
            return jsonify({"success" : False, "message" : "email/username in use. Please choose another."})

        # add to the database 
        new_user = User(email, password)
        users[email] = new_user

        save_users_and_sessions()
        
        return jsonify({"success" : True, "message" : f"account created for {email}"})


@app.route("/", methods = ["POST", "GET"])
@needs_user
def _index(user):
    if request.method == "GET":
        return render_template("index.html")
    elif request.method == "POST":
        # ?
        return

@app.route("/documents", methods = ["GET"])
@needs_user
def _documents(user):
    if request.method == "GET":
        # get user documents
        return user.get_documents()

@app.route("/documents/new", methods=["POST"]) # might want to change this to a POST
@needs_user
def _documents_new_doc_name(user):
    doc_name = request.get_data(as_text=True)
    user.new_document(doc_name)
    return "success"

@app.route("/documents/load/<doc_id>")
@needs_user
def _documents_load_doc_id(user, doc_id):
    return user.load_document(doc_id)

@app.route("/documents/delete/<doc_id>", methods = ["DELETE"])
@needs_user
def _document_delete_doc_id(user, doc_id):
    # write user.delete
    user.delete_document_path(doc_id)
    return "success"

@app.route("/documents/save/<doc_id>", methods=["POST"])
@needs_user
def _document_save_doc_id(user, doc_id):
    if request.method == "POST":
        data = request.json

        quilldata = data["content"]
        namedata = data["name"]

        user.save_document(doc_id, quilldata, namedata)
        return "success"

    return "finished"

@app.route("/documents/edit")
@needs_user
def _documents_edit(user):
    # render_template editor
    # on load, quill load doc ID or something
    return render_template("editor.html")

@app.route("/record", methods=["GET", "POST"])
@needs_user
def _record(user):
    return render_template("client-side-recorder.html")

@app.route("/upload/recordings/<doc_id>", methods=["POST"])
@needs_user
def _upload_audio(user, doc_id):
    if True:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        file = request.files['audio']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file:
            #filename = secure_filename(file.filename)
            file_extension = ("." in file.filename and file.filename.split(".")[-1]) or None
            if file_extension:
                recording_id = generate_id("recording")
                audio_filename = f"{recording_id}.{file_extension}"
                filepath = user.get_document_recording_path(doc_id)
                audio_filepath = os.path.join(filepath, audio_filename)
                file.save(audio_filepath)
                
                # also now transcribe & save raw transcription
                raw_transcription = transcribe(audio_filepath)
                with open(os.path.join(filepath, f"{recording_id}.txt"), "w") as f:
                    f.write(raw_transcription)

                # also now lightly modify transcription & save transcription

                # return modified transcription OR append to document MD

                return jsonify({"content" : raw_transcription, "success" : True}), 200
    else:
        return None
#    except Exception as e:
#        return jsonify({'content': str(e), "success" : False}), 500

if __name__ == "__main__":
    load_users_and_sessions()
    app.run(host="0.0.0.0", debug=False, port=8082)
