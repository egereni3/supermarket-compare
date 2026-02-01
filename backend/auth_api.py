from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from .crawlers import (get_sainsburys_results, get_homebargains_results, get_morrisons_results,)
from .database_ops import _login_logic as db_login, _register_logic as db_register_user

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

def normalize_query(q: str) -> str:
    import re
    return re.sub(r'[^a-z0-9 ]+', '', q.lower().strip())

class Credentials(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    user_id: Optional[int] = None
    email: Optional[EmailStr] = None

@app.post("/api/login", response_model=AuthResponse)
def api_login(creds: Credentials):
    result = db_login(creds.email, creds.password)
    return AuthResponse(**result)

@app.post("/api/register", response_model=AuthResponse)
def api_register(creds: Credentials):
    result = db_register_user(creds.email, creds.password)
    return AuthResponse(**result)

@app.get("/api/search", response_model=SearchResponse)
def api_search(q: str):
    key = normalize_query(q)

    # Call crawlers (sequential; you can parallelize later if needed)
    sains = get_sainsburys_results(q)
    homeb = get_homebargains_results(q)
    morri = get_morrisons_results(q)

    return SearchResponse(
        query=q,
        key=key,
        results={
            "sainsburys": sains,       # list of [name, price]
            "homebargains": homeb,
            "morrisons": morri,
        },
    )