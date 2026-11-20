import argparse
import json
import logging
import re
from contextlib import closing

import pyodbc
from fastapi import APIRouter, Depends, HTTPException, Path

from app.db import get_connection


logger = logging.getLogger("uvicorn.error")

router = APIRouter(
    prefix="/profiles",
    tags=["Profiles"],
)


class ProfileNotFoundError(Exception):
    """Raised when the requested profile does not exist."""


def read_result_set(cursor):
    """Convert the current result set into dictionaries."""
    if cursor.description is None:
        raise RuntimeError("Expected a database result set.")

    column_names = [column[0] for column in cursor.description]

    return [
        dict(zip(column_names, row))
        for row in cursor.fetchall()
    ]


def read_profile(user_id: int) -> dict:
    """Read a profile for an already-authorized caller or local testing."""
    if user_id <= 0:
        raise ValueError("A positive user ID is required.")

    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    "EXEC CW2.sp_ReadUserProfile @UserID = ?;",
                    (user_id,),
                )

                profiles = read_result_set(cursor)

                if not cursor.nextset():
                    raise RuntimeError("Activity preferences result set is missing.")

                preferences = read_result_set(cursor)

                if not cursor.nextset():
                    raise RuntimeError("Saved trails result set is missing.")

                saved_trails = read_result_set(cursor)

                # Consume any remaining results and surface database errors.
                while cursor.nextset():
                    if cursor.description is not None:
                        cursor.fetchall()

    except pyodbc.Error as error:
        error_text = " ".join(str(part) for part in error.args)

        if re.search(r"\(50011\)", error_text):
            raise ProfileNotFoundError("User profile not found.") from error

        raise

    if not profiles:
        raise ProfileNotFoundError("User profile not found.")

    if len(profiles) != 1:
        raise RuntimeError("Expected exactly one user profile.")

    profile = profiles[0]

    statistics = None

    if profile["TotalHikes"] is not None:
        statistics = {
            "total_hikes": profile["TotalHikes"],
            "total_distance_km": str(profile["TotalDistance"]),
            "total_duration_minutes": profile["TotalDuration"],
        }

    return {
        "user_id": profile["UserID"],
        "username": profile["Username"],
        "first_name": profile["FirstName"],
        "last_name": profile["LastName"],
        "email": profile["Email"],
        "location": profile["Location"],
        "profile_photo": profile["ProfilePhoto"],
        "role": {
            "role_id": profile["RoleID"],
            "role_name": profile["RoleName"],
        },
        "created_date": profile["CreatedDate"].isoformat(),
        "statistics": statistics,
        "preferred_activities": [
            {
                "activity_id": activity["ActivityID"],
                "activity_name": activity["ActivityName"],
            }
            for activity in preferences
        ],
        "saved_trails": [
            {"trail_id": trail["TrailID"]}
            for trail in saved_trails
        ],
    }


def require_profile_access():
    """Keep profile access closed until authentication is implemented."""
    raise HTTPException(
        status_code=503,
        detail="Profile access is unavailable until authentication is configured.",
    )


@router.get(
    "/{user_id}",
    dependencies=[Depends(require_profile_access)],
    responses={
        404: {"description": "User profile not found."},
        503: {"description": "Authentication or database service unavailable."},
    },
)
def get_profile(user_id: int = Path(..., gt=0)):
    """Return a profile after authentication and authorization."""
    try:
        return read_profile(user_id)

    except ProfileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="User profile not found.",
        ) from None

    except (pyodbc.Error, RuntimeError):
        logger.exception("Failed to retrieve user profile.")
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve user profile.",
        ) from None


def main():
    """Run a local database read test without starting an HTTP endpoint."""
    parser = argparse.ArgumentParser(
        description="Test profile retrieval directly against the local database."
    )
    parser.add_argument("user_id", type=int)
    arguments = parser.parse_args()

    try:
        result = read_profile(arguments.user_id)

    except (ValueError, ProfileNotFoundError) as error:
        print(f"Profile read failed: {error}")
        raise SystemExit(1)

    except (pyodbc.Error, RuntimeError) as error:
        print(f"Database read failed: {error}")
        raise SystemExit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()