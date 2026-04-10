import re
import pymysql
import bcrypt
from typing import Optional


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

def insert_search_match(user_id: int, search_words: list[str]) -> int:
    query = """
        INSERT IGNORE INTO searches (user_id, search_word)
        VALUES (%s, %s)
    """
    rows = [(user_id, word.lower().strip()) for word in search_words]

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(query, rows)
        connection.commit()
        saved = cursor.rowcount

    return saved

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