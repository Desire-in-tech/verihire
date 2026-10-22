"""Employer identity comes from the session token, never from the client."""

from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException

from Backend.database import db


def require_employer(authorization: Annotated[str | None, Header()] = None) -> dict[str, str]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.split(" ", 1)[1].strip()
    employer = db.store.employer_for_token(token)
    if employer is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return employer
