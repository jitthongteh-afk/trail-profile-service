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


class PreferenceError(Exception):
    """Represent an expected activity preference error."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


ERROR_MESSAGES = {
    50050: "Positive UserID and ActivityID values are required.",
    50051: "This activity preference already exists.",
    50052: "The user profile or activity does not exist.",
    50053: "Positive UserID and ActivityID values are required.",
    50054: "Activity preference not found.",
}

STATEMENTS = {
    "add": """
        EXEC CW2.sp_AddUserPreference
            @UserID = ?, @ActivityID = ?;
    """,
    "remove": """
        EXEC CW2.sp_RemoveUserPreference
            @UserID = ?, @ActivityID = ?;
    """,
}


def change_preference(
    connection,
    operation: str,
    user_id: int,
    activity_id: int,
) -> dict:
    """Change a preference. The caller must commit or roll back."""
    if operation not in STATEMENTS:
        raise ValueError("Unsupported preference operation.")

    try:
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                STATEMENTS[operation],
                (user_id, activity_id),
            )

            if cursor.description is None:
                raise RuntimeError("Preference result set is missing.")

            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()

            while cursor.nextset():
                if cursor.description is not None:
                    cursor.fetchall()

            if len(rows) != 1:
                raise RuntimeError("Expected one preference result.")

            result = dict(zip(columns, rows[0]))

    except pyodbc.Error as error:
        error_text = " ".join(str(part) for part in error.args)

        for code, message in ERROR_MESSAGES.items():
            if re.search(rf"\({code}\)", error_text):
                raise PreferenceError(code, message) from error

        raise

    return {
        "user_id": result["UserID"],
        "activity_id": result["ActivityID"],
        "message": result["ResultMessage"],
    }


def add_preference(connection, user_id: int, activity_id: int) -> dict:
    return change_preference(connection, "add", user_id, activity_id)


def remove_preference(connection, user_id: int, activity_id: int) -> dict:
    return change_preference(connection, "remove", user_id, activity_id)


def preference_count(connection, user_id: int, activity_id: int) -> int:
    with closing(connection.cursor()) as cursor:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM CW2.USER_PREFERRED_ACTIVITY
            WHERE UserID = ? AND ActivityID = ?;
            """,
            (user_id, activity_id),
        )
        return cursor.fetchone()[0]


def run_test(test_name: str, expected_code: int | None = None):
    username = f"PrefTest_{uuid4().hex}"

    with closing(get_connection()) as connection:
        try:
            profile = create_profile(connection, username)
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
                row = cursor.fetchone()
                require(
                    row is not None,
                    "The Hiking activity is required for this test.",
                )
                activity_id = row[0]

            if test_name == "Add and remove":
                added = add_preference(connection, user_id, activity_id)
                require(
                    added == {
                        "user_id": user_id,
                        "activity_id": activity_id,
                        "message": "Preference added successfully.",
                    },
                    "Unexpected add result.",
                )
                require(
                    preference_count(connection, user_id, activity_id) == 1,
                    "The preference was not inserted.",
                )

                removed = remove_preference(
                    connection, user_id, activity_id
                )
                require(
                    removed == {
                        "user_id": user_id,
                        "activity_id": activity_id,
                        "message": "Preference removed successfully.",
                    },
                    "Unexpected remove result.",
                )
                require(
                    preference_count(connection, user_id, activity_id) == 0,
                    "The preference was not removed.",
                )
                details = "Count after adding=1; after removing=0"

            else:
                operation = add_preference
                target_user_id = user_id
                target_activity_id = activity_id

                if test_name == "Duplicate preference":
                    add_preference(connection, user_id, activity_id)

                elif test_name == "Missing user":
                    with closing(connection.cursor()) as cursor:
                        cursor.execute(
                            """
                            DELETE FROM CW2.USER_PROFILE
                            WHERE UserID = ?;
                            """,
                            (user_id,),
                        )

                elif test_name == "Invalid add user ID":
                    target_user_id = 0

                elif test_name == "Invalid add activity ID":
                    target_activity_id = 0

                elif test_name == "Invalid remove user ID":
                    operation = remove_preference
                    target_user_id = 0

                elif test_name == "Invalid remove activity ID":
                    operation = remove_preference
                    target_activity_id = 0

                elif test_name == "Missing preference":
                    operation = remove_preference

                else:
                    raise RuntimeError(f"Unknown test: {test_name}")

                try:
                    operation(
                        connection, target_user_id, target_activity_id
                    )
                except PreferenceError as error:
                    require(
                        error.code == expected_code,
                        f"Unexpected error code: {error.code}.",
                    )
                    details = f"{error.code} | {error}"
                else:
                    raise RuntimeError(
                        f"{test_name}: operation unexpectedly succeeded."
                    )
        finally:
            connection.rollback()

        with closing(connection.cursor()) as cursor:
            cursor.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM CW2.USER_PROFILE
                     WHERE UserID = ?),
                    (SELECT COUNT(*) FROM CW2.USER_PREFERRED_ACTIVITY
                     WHERE UserID = ?);
                """,
                (user_id, user_id),
            )
            remaining = tuple(cursor.fetchone())

        connection.rollback()
        require(
            remaining == (0, 0),
            f"Test records remain after rollback: {remaining}.",
        )

    print(f"PASS | {test_name} | {details}")


def main():
    try:
        run_test("Add and remove")

        for test_name, expected_code in (
            ("Duplicate preference", 50051),
            ("Missing user", 50052),
            ("Invalid add user ID", 50050),
            ("Invalid add activity ID", 50050),
            ("Invalid remove user ID", 50053),
            ("Invalid remove activity ID", 50053),
            ("Missing preference", 50054),
        ):
            run_test(test_name, expected_code)

    except (
        pyodbc.Error,
        RuntimeError,
        ValueError,
        ProfileCreationError,
        PreferenceError,
    ) as error:
        print(f"FAIL | {error}")
        raise SystemExit(1)

    print("PASS | Rollback cleanup | No test records remain")
    print("All activity preference tests passed.")


if __name__ == "__main__":
    main()