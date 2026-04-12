from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from .crawlers import search_all
from .database_ops import (
    _login_logic as db_login,
    _register_logic as db_register_user,
    get_db_connection,
    update_user,
    is_valid_email,
    is_strong_password,
    insert_search_match,
    get_top_search_words,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchResponse(BaseModel):
    query: str
    key: str
    results: dict

class SearchMatchPayload(BaseModel):
    user_id: int
    search_words: list[str]

class Credentials(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    user_id: Optional[int] = None
    email: Optional[EmailStr] = None

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None

def normalize_query(q: str) -> str:
    import re
    return re.sub(r'[^a-z0-9 ]+', '', q.lower().strip())


@app.post("/api/login", response_model=AuthResponse)
def api_login(creds: Credentials):
    result = db_login(creds.email, creds.password)
    return AuthResponse(**result)

@app.post("/api/register", response_model=AuthResponse)
def api_register(creds: Credentials):
    result = db_register_user(creds.email, creds.password)
    return AuthResponse(**result)

@app.put("/api/user/{user_id}", response_model=AuthResponse)
def update_user_endpoint(user_id: int, update: UserUpdate):
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

@app.get("/api/search", response_model=SearchResponse)
def api_search(q: str):
    key = normalize_query(q)
    results = search_all(q)

    return SearchResponse(
        query=q,
        key=key,
        results={
            "sainsburys":   results.get("sainsburys", []),
            "homebargains": results.get("homebargains", []),
            "morrisons":    results.get("morrisons", []),
        },
    )

@app.post("/api/search-matches")
def save_search_matches(payload: SearchMatchPayload):
    if not payload.search_words:
        return {"success": True, "saved": 0}

    saved = insert_search_match(payload.user_id, payload.search_words)
    return {"success": True, "saved": saved}

@app.get("/api/user/{user_id}/top-searches")
def get_top_searches(user_id: int, limit: int = 5):
    words = get_top_search_words(user_id, limit)
    return {"words": words}