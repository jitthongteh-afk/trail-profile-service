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


class ProfileUpdateError(Exception):
    """Represent an expected profile update error."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


ERROR_MESSAGES = {
    50040: "A positive UserID is required.",
    50041: "Username is required.",
    50042: "One or more fields exceed their maximum supported length.",
    50043: "User profile not found.",
    50044: "Username or email already exists.",
}


def update_profile(
    connection,
    user_id: int,
    *,
    username: str,
    first_name: str | None,
    last_name: str | None,
    email: str | None,
    location: str | None,
    profile_photo: str | None,
) -> dict:
    """Replace editable fields. The caller must commit or roll back."""
    try:
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                """
                EXEC CW2.sp_UpdateUserProfile
                    @UserID = ?,
                    @Username = ?,
                    @FirstName = ?,
                    @LastName = ?,
                    @Email = ?,
                    @Location = ?,
                    @ProfilePhoto = ?;
                """,
                (
                    user_id,
                    username,
                    first_name,
                    last_name,
                    email,
                    location,
                    profile_photo,
                ),
            )

            if cursor.description is None:
                raise RuntimeError("Updated profile result set is missing.")

            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()

            while cursor.nextset():
                if cursor.description is not None:
                    cursor.fetchall()

            if len(rows) != 1:
                raise RuntimeError("Expected one updated profile.")

            profile = dict(zip(columns, rows[0]))

    except pyodbc.Error as error:
        error_text = " ".join(str(part) for part in error.args)

        for code, message in ERROR_MESSAGES.items():
            if re.search(rf"\({code}\)", error_text):
                raise ProfileUpdateError(code, message) from error

        raise

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
    }


def test_successful_update():
    suffix = uuid4().hex

    with closing(get_connection()) as connection:
        try:
            original = create_profile(connection, f"Before_{suffix}")
            user_id = original["user_id"]

            fields = {
                "username": f"After_{suffix}",
                "first_name": "Test",
                "last_name": "User",
                "email": f"{suffix}@example.com",
                "location": "Kuala Lumpur",
                "profile_photo": "https://example.com/avatar.png",
            }

            updated = update_profile(connection, user_id, **fields)

            require(updated["user_id"] == user_id, "User ID changed.")
            for field, value in fields.items():
                require(
                    updated[field] == value,
                    f"Unexpected value for {field}.",
                )

            require(
                updated["role"] == original["role"],
                "The role changed unexpectedly.",
            )
            require(
                updated["created_date"] == original["created_date"],
                "The creation date changed unexpectedly.",
            )

            # Read the table directly to verify the database update.
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    """
                    SELECT Username, FirstName, LastName, Email,
                           Location, ProfilePhoto
                    FROM CW2.USER_PROFILE
                    WHERE UserID = ?;
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()
                require(row is not None, "Updated profile is missing.")
                require(
                    tuple(row) == tuple(fields.values()),
                    "Stored values do not match the update.",
                )

            cleared = update_profile(
                connection,
                user_id,
                username=fields["username"],
                first_name=None,
                last_name=None,
                email=None,
                location=None,
                profile_photo=None,
            )

            for field in (
                "first_name",
                "last_name",
                "email",
                "location",
                "profile_photo",
            ):
                require(
                    cleared[field] is None,
                    f"{field} was not cleared.",
                )
        finally:
            connection.rollback()

        with closing(connection.cursor()) as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM CW2.USER_PROFILE WHERE UserID = ?;",
                (user_id,),
            )
            remaining = cursor.fetchone()[0]

        connection.rollback()
        require(remaining == 0, "The test profile was not rolled back.")

    print("PASS | Update profile | Database values verified")
    print("PASS | Protected fields | Role and creation date unchanged")
    print("PASS | Clear optional fields | NULL values returned")
    print("PASS | Rollback cleanup | Remaining test profiles: 0")


def test_rejected_update(test_name: str, expected_code: int):
    with closing(get_connection()) as connection:
        try:
            profile = create_profile(
                connection,
                f"Test_{uuid4().hex}",
            )
            user_id = profile["user_id"]
            username = profile["username"]

            if test_name == "Invalid user ID":
                user_id = 0

            elif test_name == "Blank username":
                username = " \t\r\n "

            elif test_name == "Username too long":
                username = "A" * 51

            elif test_name == "Missing profile":
                # Delete only this temporary profile inside the transaction.
                with closing(connection.cursor()) as cursor:
                    cursor.execute(
                        "DELETE FROM CW2.USER_PROFILE WHERE UserID = ?;",
                        (user_id,),
                    )

            elif test_name == "Duplicate username":
                other = create_profile(
                    connection,
                    f"Other_{uuid4().hex}",
                )
                username = other["username"]

            else:
                raise RuntimeError(f"Unknown test: {test_name}")

            try:
                update_profile(
                    connection,
                    user_id,
                    username=username,
                    first_name=None,
                    last_name=None,
                    email=None,
                    location=None,
                    profile_photo=None,
                )
            except ProfileUpdateError as error:
                require(
                    error.code == expected_code,
                    f"{test_name}: unexpected error code {error.code}.",
                )
                result_message = str(error)
            else:
                raise RuntimeError(
                    f"{test_name}: update unexpectedly succeeded."
                )
        finally:
            connection.rollback()

    print(f"PASS | {test_name} | {expected_code} | {result_message}")


def main():
    try:
        test_successful_update()

        for test_name, expected_code in (
            ("Invalid user ID", 50040),
            ("Blank username", 50041),
            ("Username too long", 50042),
            ("Missing profile", 50043),
            ("Duplicate username", 50044),
        ):
            test_rejected_update(test_name, expected_code)

    except (
        pyodbc.Error,
        RuntimeError,
        ProfileCreationError,
        ProfileUpdateError,
    ) as error:
        print(f"FAIL | {error}")
        raise SystemExit(1)

    print("All profile update tests passed.")


if __name__ == "__main__":
    main()