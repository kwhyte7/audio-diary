#!/usr/bin/env python3

import json
import time
import random
import glob
import os
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
    return name_of + "_" + str(time.time()) + str( random.randint(0, 99999) )

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
    def wrapper(*args, **kwargs):
        user = find_user_from_session() # will use flask session 
        if user:
            return func(user, *args, **kwargs)
        return redirect(url_for("_login"))
    
    return wrapper

class DocumentManager():
    def __init__(self, path):
        return

    @staticmethod
    def new(self, document_id):
        return

    @staticmethod
    def from_json(self, document_id):
        # so this will just really track the path mainly, then will have many functions that stem from that
        return

    def save_recording(self):
        # just save recording into a folder where:
        # > recordingDate/ 
        # >> audio.mp3 >> transcription.txt
        return

    def transcribe_raw_recording(self):
        # use faster-whisper to transcribe, then save for recordingDate/transcription.txt
        return

    def clean_transcription(self):
        # use the specified model to clean up the transcription. Will have more in settings.yml for modelname, system prompt & kwargs like temperature & seed.
        return

    # we're also going to want to be able to access the actual .md (are we going to use MD editor instad of quill?



class User():
    def __init__(self, email, password):
        self.data = {
            "id" : generate_id("user"),
            "email" : email,
            "password_hash" : generate_password_hash(password),
            "active_sessions" : [],
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
        path = f"./data/user_{self.user.data['id']}",
        os.mkdirs(path, exist_ok=True)
        return path

    def get_document_folder_path(self, document_id):
        path = f"{self.get_folder_path()}/document_{document_id}"
        os.mkdirs(path, exist_ok=True)
        return path

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
    return render_template("index.html")

if __name__ == "__main__":
    load_users_and_sessions()
    app.run(port=8077, host="localhost", debug=True)
