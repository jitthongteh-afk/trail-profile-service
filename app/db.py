"""SQL Server connections for Windows development and Docker deployment."""
import os
from contextlib import closing

import pyodbc


def _value(name, default=None):
    value = os.environ.get(name, default)
    if value is None or not value.strip():
        raise pyodbc.InterfaceError(f"Missing database setting: {name}.")
    if any(character in value for character in ("\x00", "\r", "\n")):
        raise pyodbc.InterfaceError(f"Invalid database setting: {name}.")
    return value


def _quote(value):
    """Escape an ODBC attribute, including passwords with semicolons or braces."""
    return "{" + value.replace("}", "}}") + "}"


def _yes_no(name, default):
    value = _value(name, default).strip().lower()
    if value not in {"yes", "no"}:
        raise pyodbc.InterfaceError(f"{name} must be yes or no.")
    return value


def _timeout(name, default):
    try:
        value = int(_value(name, str(default)))
    except ValueError:
        raise pyodbc.InterfaceError(f"{name} must be an integer.") from None
    if not 1 <= value <= 120:
        raise pyodbc.InterfaceError(f"{name} must be between 1 and 120.")
    return value


def build_connection_string():
    """Read runtime configuration without logging credentials."""
    mode = _value("DB_AUTH", "windows" if os.name == "nt" else "sql").lower()
    default_server = "LAPTOP-CH330V7N" if mode == "windows" else None
    attributes = [
        "DRIVER=" + _quote(_value("DB_DRIVER", "ODBC Driver 18 for SQL Server")),
        "SERVER=" + _quote(_value("DB_SERVER", default_server)),
        "DATABASE=" + _quote(_value("DB_DATABASE", "Assessment1DB")),
        "Encrypt=" + _yes_no("DB_ENCRYPT", "yes"),
        "TrustServerCertificate=" + _yes_no(
            "DB_TRUST_SERVER_CERTIFICATE", "yes" if mode == "windows" else "no"
        ),
    ]
    if mode == "windows":
        attributes.append("Trusted_Connection=yes")
    elif mode == "sql":
        attributes.extend([
            "UID=" + _quote(_value("DB_USERNAME")),
            "PWD=" + _quote(_value("DB_PASSWORD")),
        ])
    else:
        raise pyodbc.InterfaceError("DB_AUTH must be windows or sql.")
    return ";".join(attributes) + ";"


def get_connection():
    connection = pyodbc.connect(
        build_connection_string(),
        timeout=_timeout("DB_CONNECTION_TIMEOUT", 5),
        autocommit=False,
    )
    try:
        connection.timeout = _timeout("DB_QUERY_TIMEOUT", 10)
    except Exception:
        connection.close()
        raise
    return connection


def test_connection():
    """Verify the connection and display the local profile records."""
    with closing(get_connection()) as connection:
        with closing(connection.cursor()) as cursor:
            cursor.execute("SELECT DB_NAME();")
            print(f"Connected to database: {cursor.fetchone()[0]}")
            cursor.execute(
                "SELECT UserID, Username, RoleName "
                "FROM CW2.vw_UserProfile ORDER BY UserID;"
            )
            for row in cursor.fetchall():
                print(f"UserID={row.UserID} | Username={row.Username} | Role={row.RoleName}")


if __name__ == "__main__":
    try:
        test_connection()
    except pyodbc.Error as error:
        # Driver messages may include connection details; show only SQLSTATE.
        state = str(error.args[0]) if error.args else "unknown"
        state = state if len(state) == 5 and state.isalnum() else "configuration"
        print(f"Database connection or query failed (SQLSTATE: {state}).")
        print("Check the database settings, SQL login, TCP port and CW2 permissions.")
        raise SystemExit(1)
