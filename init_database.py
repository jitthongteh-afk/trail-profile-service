"""Initialise a fresh Assessment1DB on a local SQL Server instance."""

import argparse
import re
from contextlib import closing
from getpass import getpass
from pathlib import Path

import pyodbc


DATABASE = "Assessment1DB"
LOGIN = "profile_service_login"
SQL_DIR = Path(__file__).resolve().parent / "sql"

# The coursework scripts use GO on its own line as a batch separator.
GO_LINE = re.compile(r"^[ \t]*GO[ \t]*(?:--[^\r\n]*)?\r?$", re.I | re.M)


def setup_files():
    files = []
    for number in range(17):
        matches = sorted(SQL_DIR.glob(f"{number:02d}_*.sql"))
        if len(matches) != 1:
            raise ValueError(
                f"Expected one {number:02d}_*.sql file in {SQL_DIR}, "
                f"found {len(matches)}."
            )
        path = matches[0]
        data = path.read_bytes()
        encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
        files.append((path.name, data.decode(encoding)))
    return files


def execute_batch(cursor, sql):
    cursor.execute(sql)
    # Advance through all results so errors in a later statement are reported.
    while cursor.nextset():
        pass


def initialise(server):
    files = setup_files()
    server_value = "{" + server.replace("}", "}}") + "}"
    connection_string = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server_value};DATABASE=master;"
        "Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;"
    )

    with closing(pyodbc.connect(connection_string, autocommit=True, timeout=10)) as db:
        with closing(db.cursor()) as cursor:
            if cursor.execute("SELECT DB_ID(?)", DATABASE).fetchval() is not None:
                print("SKIPPED | Assessment1DB already exists. No changes were made.")
                return

            login_exists = cursor.execute(
                "SELECT COUNT(*) FROM sys.sql_logins WHERE name = ?", LOGIN
            ).fetchval()

            if not login_exists:
                password = getpass("Choose a password for profile_service_login: ")
                if not 1 <= len(password) <= 128:
                    raise ValueError("The password must contain 1 to 128 characters.")
                if password != getpass("Confirm the SQL login password: "):
                    raise ValueError("The passwords do not match.")

                # Bind the password as a parameter and quote it on SQL Server.
                cursor.execute(
                    """
                    DECLARE @pwd nvarchar(128) = ?;
                    DECLARE @stmt nvarchar(max) =
                        N'CREATE LOGIN [profile_service_login] WITH PASSWORD = '
                        + QUOTENAME(@pwd, '''') + N', CHECK_POLICY = ON;';
                    EXEC sys.sp_executesql @stmt;
                    """,
                    password,
                )
                while cursor.nextset():
                    pass
                print("PASS | Application SQL login created.")
            else:
                print("INFO | Reusing the existing application SQL login.")

            execute_batch(cursor, "CREATE DATABASE [Assessment1DB]")
            execute_batch(cursor, "USE [Assessment1DB]")

            for name, contents in files:
                print(f"Running {name} ...", flush=True)
                for batch in GO_LINE.split(contents):
                    if batch.strip():
                        execute_batch(cursor, batch)
                print(f"PASS | {name}")

            rows = cursor.execute(
                """
                SELECT p.UserID, p.Username, r.RoleName
                FROM CW2.USER_PROFILE AS p
                JOIN CW2.ROLE AS r ON r.RoleID = p.RoleID
                ORDER BY p.UserID
                """
            ).fetchall()
            for user_id, username, role in rows:
                print(f"UserID={user_id} | Username={username} | Role={role}")

            print("PASS | Assessment1DB initialisation completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--server", default="localhost",
        help=r"SQL Server instance, for example localhost or localhost\SQLEXPRESS",
    )
    args = parser.parse_args()
    try:
        initialise(args.server)
    except (OSError, ValueError, pyodbc.Error) as error:
        raise SystemExit(f"FAIL | {error}")