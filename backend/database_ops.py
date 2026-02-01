import re
import pymysql
import bcrypt
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Credentials(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    user_id: Optional[int] = None
    email: Optional[EmailStr] = None

# Helper functions

def is_valid_email(email: str) -> bool:
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None

def is_strong_password(password: str) -> bool:
    if len(password) < 6:
        return False
    if not re.search(r"[A-Z]", password):  # uppercase
        return False
    if not re.search(r"[0-9]", password):  # digit
        return False
    return True

def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def image_to_blob(image_path: str) -> bytes:
    with open(image_path, "rb") as f:
        return f.read()

def get_db_connection():
    return pymysql.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="dissertation_201652981",
        cursorclass=pymysql.cursors.DictCursor,
    )

# User Operations


def insert_user(email: str, password: str):
    hashed_password = hash_password(password)
    query = """
        INSERT INTO users (email, hashed_password)
        VALUES (%s, %s)
    """
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (email, hashed_password))
        connection.commit()
        # cursor is still valid here because "with connection.cursor()" scope ended
        # only after commit; we keep lastrowid
        last_id = cursor.lastrowid
    return last_id

def update_user(user_id: int, email: str = None, password: str = None):
    fields = []
    params = []

    if email is not None:
        fields.append("email = %s")
        params.append(email)

    if password is not None:
        hashed_password = hash_password(password)
        fields.append("hashed_password = %s")
        params.append(hashed_password)

    if not fields:
        return False

    params.append(user_id)

    query = f"""
        UPDATE users
        SET {', '.join(fields)}, updated_at = NOW()
        WHERE user_id = %s
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, tuple(params))
        connection.commit()
    return True

def delete_user(user_id: int):
    query = "DELETE FROM users WHERE user_id = %s"

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (user_id,))
        connection.commit()

    return True

def insert_avatar(user_id: int, image_path: str, mime_type: str, description: str = None):
    image_data = image_to_blob(image_path)

    query = """
        INSERT INTO user_avatars (user_id, image_data, mime_type, description)
        VALUES (%s, %s, %s, %s)
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (user_id, image_data, mime_type, description))
        connection.commit()
        last_id = cursor.lastrowid

    return last_id

def update_avatar(
    avatar_id: int,
    image_path: str = None,
    mime_type: str = None,
    description: str = None,
    is_active: bool = None,
):
    fields = []
    params = []

    if image_path is not None:
        image_data = image_to_blob(image_path)
        fields.append("image_data = %s")
        params.append(image_data)

    if mime_type is not None:
        fields.append("mime_type = %s")
        params.append(mime_type)

    if description is not None:
        fields.append("description = %s")
        params.append(description)

    if is_active is not None:
        fields.append("is_active = %s")
        params.append(is_active)

    if not fields:
        return False

    params.append(avatar_id)

    query = f"""
        UPDATE user_avatars
        SET {', '.join(fields)}
        WHERE avatar_id = %s
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, tuple(params))
        connection.commit()

    return True

def delete_avatar(avatar_id: int):
    query = "DELETE FROM user_avatars WHERE avatar_id = %s"

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (avatar_id,))
        connection.commit()

    return True


def _login_logic(email: str, password: str) -> dict:
    if not is_valid_email(email):
        return {"success": False, "error": "Invalid email format."}
    
    if not is_strong_password(password):
        return {
            "success": False,
            "error": "Password must be at least 6 characters long, contain a number and an uppercase letter.",
        }

    query = "SELECT * FROM users WHERE email = %s"
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (email,))
            user = cursor.fetchone()

    if user is None:
        return {"success": False, "error": "Invalid email or password."}

    if not bcrypt.checkpw(
        password.encode("utf-8"),
        user["hashed_password"].encode("utf-8"),
    ):
        return {"success": False, "error": "Invalid email or password."}

    return {
        "success": True,
        "message": "Login successful.",
        "user_id": user["user_id"],
        "email": user["email"],
    }

def _register_logic(email: str, password: str) -> dict:
    if not is_valid_email(email):
        return {"success": False, "error": "Invalid email format."}

    if not is_strong_password(password):
        return {
            "success": False,
            "error": "Password must be at least 6 characters long, contain a number and an uppercase letter.",
        }

    query = "SELECT * FROM users WHERE email = %s"

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (email,))
            existing_user = cursor.fetchone()

    if existing_user is not None:
        return {"success": False, "error": "Email already in use."}

    user_id = insert_user(email, password)

    return {
        "success": True,
        "message": "User registered successfully.",
        "user_id": user_id,
    }

# FastAPI endpoints


@app.post("/api/login", response_model=AuthResponse)
def login(credentials: Credentials):
    result = _login_logic(credentials.email, credentials.password)
    if not result["success"]:
        # You can either return 200 with success=False, or raise 400; for Angular
        # it’s often simpler to always return 200 and check "success"
        return AuthResponse(**result)
    return AuthResponse(**result)

@app.post("/api/register", response_model=AuthResponse)
def register_user(credentials: Credentials):
    result = _register_logic(credentials.email, credentials.password)
    return AuthResponse(**result)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None


@app.put("/api/user/{user_id}", response_model=AuthResponse)
def update_user_endpoint(user_id: int, update: UserUpdate):
    # Validate inputs
    if update.email is not None and not is_valid_email(update.email):
        return AuthResponse(success=False, error="Invalid email format.")
    if update.password is not None and not is_strong_password(update.password):
        return AuthResponse(
            success=False,
            error="Password must be at least 6 characters long, contain a number and an uppercase letter.",
        )

    success = update_user(user_id, update.email, update.password)
    if not success:
        return AuthResponse(success=False, error="Update failed.")
    return AuthResponse(success=True, message="User updated successfully.", user_id=user_id, email=update.email)