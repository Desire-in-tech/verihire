"""Employer signup and login. Passwords are stored only as hashes."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from Backend.auth import require_employer
from Backend.database import db

router = APIRouter(prefix="/api/auth", tags=["auth"])

_MIN_PASSWORD = 12


class SignupRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=_MIN_PASSWORD, max_length=200)
    display_name: str = Field(min_length=1, max_length=80)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


def _normalize_email(email: str) -> str:
    cleaned = email.strip().lower()
    if " " in cleaned or cleaned.count("@") != 1:
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    local, domain = cleaned.split("@", 1)
    if not local or "." not in domain:
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    return cleaned


def _public_employer(employer: dict[str, str], token: str) -> dict:
    return {
        "token": token,
        "employer": {
            "id": employer["employer_id"],
            "email": employer["email"],
            "display_name": employer["display_name"],
        },
    }


def _is_duplicate(exc: BaseException) -> bool:
    if isinstance(exc, sqlite3.IntegrityError):
        return True
    return exc.__class__.__name__ in {"IntegrityError", "UniqueViolation"}


@router.post("/signup")
async def signup(body: SignupRequest):
    email = _normalize_email(body.email)
    display_name = body.display_name.strip()
    if not display_name:
        raise HTTPException(status_code=422, detail="Enter a display name")
    try:
        employer = db.store.create_employer(
            email=email,
            password=body.password,
            display_name=display_name,
        )
    except Exception as exc:
        if _is_duplicate(exc):
            raise HTTPException(status_code=409, detail="An account with that email already exists") from exc
        raise HTTPException(status_code=500, detail="Account creation failed") from exc
    token = db.store.create_session(employer["employer_id"])
    return _public_employer(employer, token)


@router.post("/login")
async def login(body: LoginRequest):
    email = _normalize_email(body.email)
    employer = db.store.authenticate(email, body.password)
    if employer is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = db.store.create_session(employer["employer_id"])
    return _public_employer(employer, token)


@router.get("/me")
async def me(employer: dict = Depends(require_employer)):
    return {
        "id": employer["employer_id"],
        "email": employer["email"],
        "display_name": employer["display_name"],
    }
