import re
from contextlib import closing
from uuid import uuid4

import pyodbc

from app.db import get_connection
from app.profile_create import (
    ProfileCreationError,
    create_profile,
    require,
)


class ProfileDeletionError(Exception):
    """Represent an expected profile deletion error."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


ERROR_MESSAGES = {
    50030: "A positive UserID is required.",
    50031: "User profile not found.",
}


def delete_profile(connection, user_id: int) -> dict:
    """Delete a profile. The caller must commit or roll back."""
    try:
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                "EXEC CW2.sp_DeleteUserProfile @UserID = ?;",
                (user_id,),
            )

            if cursor.description is None:
                raise RuntimeError("Deletion result set is missing.")

            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()

            while cursor.nextset():
                if cursor.description is not None:
                    cursor.fetchall()

            if len(rows) != 1:
                raise RuntimeError("Expected one deletion result.")

            result = dict(zip(columns, rows[0]))

    except pyodbc.Error as error:
        error_text = " ".join(str(part) for part in error.args)

        for code, message in ERROR_MESSAGES.items():
            if re.search(rf"\({code}\)", error_text):
                raise ProfileDeletionError(code, message) from error

        raise

    return {
        "deleted_user_id": result["DeletedUserID"],
        "message": result["ResultMessage"],
    }


def get_record_counts(connection, user_id: int) -> tuple:
    """Count the profile and its related records."""
    with closing(connection.cursor()) as cursor:
        cursor.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM CW2.USER_PROFILE
                 WHERE UserID = ?),
                (SELECT COUNT(*) FROM CW2.USER_STATISTICS
                 WHERE UserID = ?),
                (SELECT COUNT(*) FROM CW2.USER_PREFERRED_ACTIVITY
                 WHERE UserID = ?),
                (SELECT COUNT(*) FROM CW2.SAVED_TRAIL
                 WHERE UserID = ?);
            """,
            (user_id, user_id, user_id, user_id),
        )
        return tuple(cursor.fetchone())


def expect_deletion_error(connection, user_id: int, expected_code: int):
    """Check that deletion returns the expected application error."""
    try:
        delete_profile(connection, user_id)
    except ProfileDeletionError as error:
        require(
            error.code == expected_code,
            f"Unexpected deletion error code: {error.code}.",
        )
    else:
        raise RuntimeError("Deletion unexpectedly succeeded.")


def test_cascade_deletion():
    with closing(get_connection()) as connection:
        try:
            profile = create_profile(
                connection,
                f"DeleteTest_{uuid4().hex}",
            )
            user_id = profile["user_id"]

            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    """
                    SELECT ActivityID
                    FROM CW2.ACTIVITY
                    WHERE ActivityName = ?;
                    """,
                    ("Hiking",),
                )
                activity = cursor.fetchone()
                require(
                    activity is not None,
                    "The Hiking activity is required for this test.",
                )

                cursor.execute(
                    """
                    INSERT INTO CW2.USER_STATISTICS (UserID)
                    VALUES (?);
                    """,
                    (user_id,),
                )
                cursor.execute(
                    """
                    INSERT INTO CW2.USER_PREFERRED_ACTIVITY
                        (UserID, ActivityID)
                    VALUES (?, ?);
                    """,
                    (user_id, activity[0]),
                )
                cursor.execute(
                    """
                    INSERT INTO CW2.SAVED_TRAIL (UserID, TrailID)
                    VALUES (?, ?);
                    """,
                    (user_id, 101),
                )

            before = get_record_counts(connection, user_id)
            require(
                before == (1, 1, 1, 1),
                f"Unexpected counts before deletion: {before}.",
            )

            result = delete_profile(connection, user_id)
            require(
                result["deleted_user_id"] == user_id,
                "The returned user ID does not match.",
            )
            require(
                result["message"] == "Profile deleted successfully.",
                "Unexpected deletion message.",
            )

            after = get_record_counts(connection, user_id)
            require(
                after == (0, 0, 0, 0),
                f"Related records remain after deletion: {after}.",
            )

            # The deleted temporary user is guaranteed to be missing.
            expect_deletion_error(connection, user_id, 50031)
        finally:
            connection.rollback()

        remaining = get_record_counts(connection, user_id)
        connection.rollback()
        require(
            remaining == (0, 0, 0, 0),
            f"Test records remain after rollback: {remaining}.",
        )

    print("PASS | Before deletion | Profile=1 Statistics=1 Preferences=1 SavedTrails=1")
    print("PASS | Delete profile | Returned user ID verified")
    print("PASS | Cascade deletion | Profile=0 Statistics=0 Preferences=0 SavedTrails=0")
    print("PASS | Delete missing profile | 50031 | User profile not found.")
    print("PASS | Rollback cleanup | No test records remain")


def test_invalid_user_id():
    with closing(get_connection()) as connection:
        try:
            expect_deletion_error(connection, 0, 50030)
        finally:
            connection.rollback()

    print("PASS | Invalid user ID | 50030 | A positive UserID is required.")


def main():
    try:
        test_cascade_deletion()
        test_invalid_user_id()

    except (
        pyodbc.Error,
        RuntimeError,
        ProfileCreationError,
        ProfileDeletionError,
    ) as error:
        print(f"FAIL | {error}")
        raise SystemExit(1)

    print("All profile deletion tests passed.")


if __name__ == "__main__":
    main()