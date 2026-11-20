import hashlib
import logging
import secrets
import time
from contextlib import closing
from threading import Lock

import pyodbc
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.authenticator import (
    AuthenticationServiceError,
    verify_credentials,
)
from app.db import get_connection


logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer = HTTPBearer(auto_error=False)

SESSION_SECONDS = 1800
MAX_SESSIONS = 1000

# Only token hashes and identity references are retained.
_sessions = {}
_session_lock = Lock()


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=1, max_length=100)
    password: SecretStr


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def unauthorized():
    return HTTPException(
        status_code=401,
        detail="Authentication required or session expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def load_identity(auth_email: str):
    """Read current profile and role through the fixed identity mapping."""
    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    """
                    SELECT
                        identity_record.AuthEmail,
                        profile.UserID,
                        profile.Username,
                        role_record.RoleID,
                        role_record.RoleName
                    FROM CW2.USER_IDENTITY AS identity_record
                    INNER JOIN CW2.USER_PROFILE AS profile
                        ON profile.UserID = identity_record.UserID
                    INNER JOIN CW2.ROLE AS role_record
                        ON role_record.RoleID = profile.RoleID
                    WHERE identity_record.AuthEmail = ?;
                    """,
                    (auth_email,),
                )
                row = cursor.fetchone()

    except pyodbc.Error:
        logger.exception("Unable to load authenticated identity.")
        raise HTTPException(
            status_code=503,
            detail="Unable to load user identity.",
        ) from None

    if row is None:
        return None

    return {
        "auth_email": row.AuthEmail,
        "user_id": row.UserID,
        "username": row.Username,
        "role": {
            "role_id": row.RoleID,
            "role_name": row.RoleName,
        },
    }


def issue_session(identity: dict) -> str:
    token = secrets.token_urlsafe(32)
    digest = token_digest(token)
    now = time.monotonic()

    with _session_lock:
        expired = [
            key
            for key, session in _sessions.items()
            if session["expires_at"] <= now
        ]
        for key in expired:
            del _sessions[key]

        if len(_sessions) >= MAX_SESSIONS:
            raise HTTPException(
                status_code=503,
                detail="Session capacity reached. Please try again later.",
            )

        _sessions[digest] = {
            "auth_email": identity["auth_email"],
            "user_id": identity["user_id"],
            "expires_at": now + SESSION_SECONDS,
        }

    return token


def get_session_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    if credentials is None:
        raise unauthorized()

    token = credentials.credentials
    if len(token) > 512:
        raise unauthorized()

    digest = token_digest(token)

    with _session_lock:
        session = _sessions.get(digest)

        if session is None:
            raise unauthorized()

        if session["expires_at"] <= time.monotonic():
            _sessions.pop(digest, None)
            raise unauthorized()

    return digest


def get_current_user(
    session_key: str = Depends(get_session_key),
) -> dict:
    with _session_lock:
        session = _sessions.get(session_key)
        if session is None:
            raise unauthorized()
        session = session.copy()

    identity = load_identity(session["auth_email"])

    # Reject sessions whose profile was deleted or mapping changed.
    if identity is None or identity["user_id"] != session["user_id"]:
        with _session_lock:
            _sessions.pop(session_key, None)
        raise unauthorized()

    # Recheck in case the session expired or was revoked during the query.
    with _session_lock:
        current = _sessions.get(session_key)
        if current is None:
            raise unauthorized()
        if current["expires_at"] <= time.monotonic():
            _sessions.pop(session_key, None)
            raise unauthorized()

    return identity


@router.post(
    "/login",
    responses={
        401: {"description": "Invalid credentials."},
        409: {"description": "No linked local profile."},
        503: {"description": "Authentication or database unavailable."},
    },
)
def login(body: LoginRequest, response: Response):
    email = body.email.strip()

    try:
        verified = verify_credentials(
            email,
            body.password.get_secret_value(),
        )
    except AuthenticationServiceError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from None

    if not verified:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    identity = load_identity(email)
    if identity is None:
        raise HTTPException(
            status_code=409,
            detail="Authenticated account has no linked local profile.",
        )

    token = issue_session(identity)
    response.headers["Cache-Control"] = "no-store"

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": SESSION_SECONDS,
        "user": identity,
    }


@router.get("/me")
def current_identity(
    response: Response,
    user: dict = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "no-store"
    return user


@router.post("/logout")
def logout(
    response: Response,
    session_key: str = Depends(get_session_key),
):
    with _session_lock:
        _sessions.pop(session_key, None)

    response.headers["Cache-Control"] = "no-store"
    return {"message": "Signed out successfully."}