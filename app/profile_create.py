import re
from contextlib import closing
from uuid import uuid4

import pyodbc

from app.db import get_connection


class ProfileCreationError(Exception):
    """Represent an expected profile creation error."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


ERROR_MESSAGES = {
    50020: "Username is required.",
    50021: "Username exceeds the maximum supported length.",
    50022: "Username already exists.",
}


def create_profile(connection, username: str) -> dict:
    """Create a profile. The caller must commit or roll back."""
    try:
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                "EXEC CW2.sp_CreateUserProfile @Username = ?;",
                (username,),
            )

            if cursor.description is None:
                raise RuntimeError("Profile result set is missing.")

            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()

            # Consume remaining results before completing the transaction.
            while cursor.nextset():
                if cursor.description is not None:
                    cursor.fetchall()

            if len(rows) != 1:
                raise RuntimeError("Expected one newly created profile.")

            profile = dict(zip(columns, rows[0]))

    except pyodbc.Error as error:
        error_text = " ".join(str(part) for part in error.args)

        for code, message in ERROR_MESSAGES.items():
            if re.search(rf"\({code}\)", error_text):
                raise ProfileCreationError(code, message) from error

        raise

    return {
        "user_id": profile["UserID"],
        "username": profile["Username"],
        "role": {
            "role_id": profile["RoleID"],
            "role_name": profile["RoleName"],
        },
        "created_date": profile["CreatedDate"].isoformat(),
    }


def require(condition: bool, message: str):
    """Fail the test if a required condition is not satisfied."""
    if not condition:
        raise RuntimeError(message)


def test_successful_creation():
    username = f"Test_{uuid4().hex}"

    with closing(get_connection()) as connection:
        try:
            profile = create_profile(connection, username)

            require(profile["user_id"] > 0, "Invalid generated user ID.")
            require(
                profile["username"] == username,
                "The returned username does not match.",
            )
            require(
                profile["role"]["role_name"] == "Member",
                "New profiles must have the Member role.",
            )
            require(
                bool(profile["created_date"]),
                "The creation date is missing.",
            )

            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM CW2.USER_PROFILE
                    WHERE UserID = ? AND Username = ?;
                    """,
                    (profile["user_id"], username),
                )
                require(
                    cursor.fetchone()[0] == 1,
                    "The new profile was not found in the transaction.",
                )
        finally:
            connection.rollback()

        with closing(connection.cursor()) as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM CW2.USER_PROFILE
                WHERE Username = ?;
                """,
                (username,),
            )
            remaining = cursor.fetchone()[0]

        connection.rollback()
        require(remaining == 0, "The test profile was not rolled back.")

    print("PASS | Create profile | Default role: Member")
    print("PASS | Rollback cleanup | Remaining test profiles: 0")


def test_rejected_creation(
    test_name: str,
    username: str,
    expected_code: int,
    create_existing: bool = False,
):
    with closing(get_connection()) as connection:
        try:
            if create_existing:
                create_profile(connection, username)

            try:
                create_profile(connection, username)
            except ProfileCreationError as error:
                require(
                    error.code == expected_code,
                    f"{test_name}: unexpected error code {error.code}.",
                )
                result_message = str(error)
            else:
                raise RuntimeError(
                    f"{test_name}: creation unexpectedly succeeded."
                )
        finally:
            connection.rollback()

    print(f"PASS | {test_name} | {expected_code} | {result_message}")


def main():
    try:
        test_successful_creation()

        test_rejected_creation(
            "Blank username",
            " \t\r\n ",
            50020,
        )

        test_rejected_creation(
            "Username too long",
            "A" * 51,
            50021,
        )

        test_rejected_creation(
            "Duplicate username",
            f"Test_{uuid4().hex}",
            50022,
            create_existing=True,
        )

    except (pyodbc.Error, RuntimeError, ProfileCreationError) as error:
        print(f"FAIL | {error}")
        raise SystemExit(1)

    print("All profile creation tests passed.")


if __name__ == "__main__":
    main()