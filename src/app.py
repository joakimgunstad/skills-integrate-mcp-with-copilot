"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import json
import secrets
import threading
import time
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
import os
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

TEACHERS_FILE = Path(__file__).with_name("teachers.json")
SESSION_COOKIE = "teacher_session"
SESSION_DURATION_SECONDS = 8 * 60 * 60
PASSWORD_HASH_ITERATIONS = 310_000
teacher_sessions: dict[str, tuple[str, float]] = {}
session_lock = threading.Lock()


class TeacherLogin(BaseModel):
    username: str
    password: str


def create_teacher_record(username: str, password: str) -> dict[str, str | int]:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return {
        "username": username,
        "salt": salt.hex(),
        "password_hash": password_hash.hex(),
        "iterations": PASSWORD_HASH_ITERATIONS,
    }


def load_teacher_records() -> list[dict[str, str | int]]:
    try:
        contents = TEACHERS_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []

    try:
        data = json.loads(contents)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Teacher credentials file contains invalid JSON") from exc

    records = data.get("teachers") if isinstance(data, dict) else None
    if not isinstance(records, list):
        raise RuntimeError("Teacher credentials file must contain a teachers list")

    for record in records:
        if not isinstance(record, dict) or not all(
            isinstance(record.get(key), expected_type)
            for key, expected_type in (
                ("username", str),
                ("salt", str),
                ("password_hash", str),
                ("iterations", int),
            )
        ):
            raise RuntimeError("Teacher credentials file contains an invalid record")
    return records


def verify_teacher_credentials(username: str, password: str) -> bool:
    for record in load_teacher_records():
        if record["username"] != username:
            continue
        try:
            salt = bytes.fromhex(record["salt"])
            expected_hash = bytes.fromhex(record["password_hash"])
        except ValueError as exc:
            raise RuntimeError("Teacher credentials file contains an invalid hash") from exc

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            record["iterations"],
        )
        return hmac.compare_digest(actual_hash, expected_hash)
    return False


def get_teacher_session(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE)
    if token is None:
        return None

    with session_lock:
        session = teacher_sessions.get(token)
        if session is None:
            return None
        username, expires_at = session
        if expires_at <= time.time():
            del teacher_sessions[token]
            return None
        return username


def require_teacher(request: Request) -> str:
    username = get_teacher_session(request)
    if username is None:
        raise HTTPException(status_code=401, detail="Teacher login required")
    return username


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.post("/auth/login")
def login_teacher(credentials: TeacherLogin, request: Request, response: Response):
    if not verify_teacher_credentials(credentials.username, credentials.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_urlsafe(32)
    with session_lock:
        teacher_sessions[token] = (
            credentials.username,
            time.time() + SESSION_DURATION_SECONDS,
        )
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_DURATION_SECONDS,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        path="/",
    )
    return {"username": credentials.username}


@app.get("/auth/session")
def get_auth_session(request: Request):
    username = get_teacher_session(request)
    return {"authenticated": username is not None, "username": username}


@app.post("/auth/logout")
def logout_teacher(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token is not None:
        with session_lock:
            teacher_sessions.pop(token, None)
    response.delete_cookie(key=SESSION_COOKIE, path="/", samesite="lax")
    return {"message": "Logged out"}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup", dependencies=[Depends(require_teacher)])
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete(
    "/activities/{activity_name}/unregister",
    dependencies=[Depends(require_teacher)],
)
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
