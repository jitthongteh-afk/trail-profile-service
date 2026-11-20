import logging
from contextlib import closing

import pyodbc
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.auth import get_current_user
from app.authenticator import (
    AuthenticationServiceError,
    verify_credentials,
)
from app.db import get_connection
from app.profiles import ProfileNotFoundError, read_profile
from app.profile_create import ProfileCreationError, create_profile
from app.profile_update import ProfileUpdateError, update_profile
from app.profile_delete import ProfileDeletionError, delete_profile
from app.profile_preferences import (
    PreferenceError,
    add_preference,
    remove_preference,
)


logger = logging.getLogger("uvicorn.error")

router = APIRouter(
    prefix="/profiles",
    tags=["Profiles"],
    responses={
        401: {"description": "Authentication required or invalid credentials."},
        403: {"description": "Access denied."},
        404: {"description": "Requested resource not found."},
        409: {"description": "Profile, username, email or preference conflict."},
        422: {"description": "Invalid request data."},
        503: {"description": "Required service unavailable."},
    },
)


class CreateProfileRequest(BaseModel):
    """Credentials verify identity; username is the new profile field."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=50)
    email: str = Field(min_length=1, max_length=100)
    password: SecretStr


class UpdateProfileRequest(BaseModel):
    """Supply every editable field; null clears optional fields."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=50)
    first_name: str | None = Field(..., max_length=50)
    last_name: str | None = Field(..., max_length=50)
    email: str | None = Field(..., max_length=100)
    location: str | None = Field(..., max_length=100)
    profile_photo: str | None = Field(..., max_length=255)


class ProfileRegistrationError(Exception):
    """Raised when an authenticated account already has a profile."""

    code = 50062

    def __init__(self):
        super().__init__("This authenticated account already has a profile.")


def require_profile_access(
    user_id: int = Path(..., ge=1, le=2147483647),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Allow Members to access themselves and Admins to access anyone."""
    role_name = current_user["role"]["role_name"]

    if role_name == "Admin":
        return current_user

    if role_name == "Member" and current_user["user_id"] == user_id:
        return current_user

    raise HTTPException(
        status_code=403,
        detail="You do not have permission to access this profile.",
    )


DOMAIN_ERRORS = (
    ProfileCreationError,
    ProfileUpdateError,
    ProfileDeletionError,
    PreferenceError,
    ProfileRegistrationError,
)

ERROR_STATUS_CODES = {
    50022: 409,
    50043: 404,
    50044: 409,
    50031: 404,
    50051: 409,
    50052: 404,
    50054: 404,
    50062: 409,
}


def execute_write(operation, *args, **kwargs):
    """Commit a successful operation or roll back all changes on failure."""
    try:
        with closing(get_connection()) as connection:
            try:
                result = operation(connection, *args, **kwargs)
                connection.commit()
            except Exception:
                connection.rollback()
                raise

        return result

    except DOMAIN_ERRORS as error:
        raise HTTPException(
            status_code=ERROR_STATUS_CODES.get(error.code, 422),
            detail=str(error),
        ) from None

    except pyodbc.Error:
        logger.exception("Profile database operation failed.")
        raise HTTPException(
            status_code=503,
            detail="Unable to complete the database operation.",
        ) from None

    except RuntimeError:
        logger.exception("Unexpected profile operation result.")
        raise HTTPException(
            status_code=500,
            detail="Unable to process the database result.",
        ) from None


def register_verified_profile(
    connection,
    auth_email: str,
    username: str,
) -> dict:
    """Bind a previously verified identity in the caller's transaction."""
    with closing(connection.cursor()) as cursor:
        # Serialize registration attempts for the same identity.
        cursor.execute(
            """
            SELECT UserID
            FROM CW2.USER_IDENTITY WITH (UPDLOCK, HOLDLOCK)
            WHERE AuthEmail = ?;
            """,
            (auth_email,),
        )

        if cursor.fetchone() is not None:
            raise ProfileRegistrationError()

    profile = create_profile(connection, username)

    with closing(connection.cursor()) as cursor:
        cursor.execute(
            """
            INSERT INTO CW2.USER_IDENTITY (AuthEmail, UserID)
            VALUES (?, ?);
            """,
            (auth_email, profile["user_id"]),
        )

    return {
        "profile": profile,
        "message": "Profile created successfully. You can now sign in.",
    }


@router.post("", status_code=201)
def create_user_profile(body: CreateProfileRequest):
    """Verify an external account and create its first local profile."""
    auth_email = body.email.strip()

    try:
        verified = verify_credentials(
            auth_email,
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
        )

    return execute_write(
        register_verified_profile,
        auth_email,
        body.username,
    )


@router.get(
    "/{user_id}",
    dependencies=[Depends(require_profile_access)],
)
def get_profile(user_id: int = Path(..., ge=1, le=2147483647)):
    """Return a profile after checking ownership or administrator access."""
    try:
        return read_profile(user_id)

    except ProfileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="User profile not found.",
        ) from None

    except pyodbc.Error:
        logger.exception("Profile retrieval failed.")
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve user profile.",
        ) from None

    except RuntimeError:
        logger.exception("Unexpected profile retrieval result.")
        raise HTTPException(
            status_code=500,
            detail="Unable to process the database result.",
        ) from None


@router.put(
    "/{user_id}",
    dependencies=[Depends(require_profile_access)],
)
def update_user_profile(
    body: UpdateProfileRequest,
    user_id: int = Path(..., ge=1, le=2147483647),
):
    """Replace editable fields without changing role or login identity."""
    return execute_write(
        update_profile,
        user_id,
        **body.model_dump(),
    )


@router.delete(
    "/{user_id}",
    dependencies=[Depends(require_profile_access)],
)
def delete_user_profile(user_id: int = Path(..., ge=1, le=2147483647)):
    """Delete a profile and its associated records."""
    return execute_write(delete_profile, user_id)


@router.post(
    "/{user_id}/preferences/{activity_id}",
    status_code=201,
    dependencies=[Depends(require_profile_access)],
)
def add_user_preference(
    user_id: int = Path(..., ge=1, le=2147483647),
    activity_id: int = Path(..., ge=1, le=2147483647),
):
    """Add a preference after checking access to the target profile."""
    return execute_write(add_preference, user_id, activity_id)


@router.delete(
    "/{user_id}/preferences/{activity_id}",
    dependencies=[Depends(require_profile_access)],
)
def remove_user_preference(
    user_id: int = Path(..., ge=1, le=2147483647),
    activity_id: int = Path(..., ge=1, le=2147483647),
):
    """Remove a preference after checking access to the target profile."""
    return execute_write(remove_preference, user_id, activity_id)