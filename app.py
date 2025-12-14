import json
import time
import random
import glob
import os
from flask import Flask, session, jsonify, render_template, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

with open("./.env", "r") as f:
    env = json.load(f)

app = Flask(__name__)
app.config["SECRET_KEY"] = env["SECRET_KEY"]

users = {}
sessions = {}
data = {}

def generate_id(name_of=""):
    return name_of + "_" + time.time() + str( random.randint(0, 99999) )

def create_session(user:User):
    new_session = {
        "id" : generate_id("session"),
        "username" : user.data["email"]
    }

    user.active_sessions.append(new_session["id"])
    sessions["id"] = new_session
    return new_session

def find_user_from_session():
    # see if session cookie in sessions (as id)
    cookie = session.get("cookie")

    if cookie and cookie in sessions.keys():
        linked_session = sessions[cookie]
        username = linked_session["username"]
        if username in users.keys():
            user = users[username]
            if cookie in user["active_sessions"]:
                return user
            else:
                del sessions["cookie"]
    return None

def save_sessions():
    with open("./data/users_and_sessions.json", "w") as f:
        json.dump({
            "users" : users,
            "sessions" : sessions
        }, f)
    return

def load_sessions():
    global users
    global sessions
    if os.path.exists("./data/users_and_sessions.json"):
        with open("./data/users_and_sessions.json", "r") as f:
            users, sessions = json.load(f).values()
    else:
        print("./data/users_and_sessions.json does not exist: will not load data.")
    return

def needs_user(func): # decorator to check that the client is logged in
    def wrapper(*args, **kwargs):
        user = find_user_from_session() # will use flask session 
        if user:
            return func(user, *args, **kwargs)
        return redirect(url_for("login"))
    return wrapper


class User():
    def __init__(self, email, password):
        self.data = {
            "id" : generate_id("user")
            "email" : email,
            "password_hash" : generate_password_hash(password),
            "active_sessions" : [],
            "encrypt_data_with_hash" : False
        }
        return

    @staticmethod
    def from_json(data):
        user = User()
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
                print(f"[{user['email']}] {session_id} not found in sessions, skipping."

        self.data["active_sessions"] = []

        save_sessions()
        return

@app.route("/login", methods = ["POST", "GET"])
def _login():
    if request.method == "GET":
        render_template("login.html")
    elif request.method == "POST":
        pass # handle login here, and set session["cookie"] to the new_session id

if __name__ == "__main__":
    load_sessions()
    app.run(port=8077, host="0.0.0.0")
