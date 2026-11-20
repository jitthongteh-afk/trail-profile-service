"""Check the local SQL login over TCP, then write Docker runtime configuration."""
import getpass
import os
from contextlib import closing
from pathlib import Path

import pyodbc

from app.db import get_connection


def main():
    target = Path(__file__).resolve().parent / ".env.docker"
    if target.exists():
        answer = input("Replace existing .env.docker? Type YES to continue: ")
        if answer != "YES":
            print("Configuration unchanged.")
            return
    port_text = input("SQL Server TCP port [1433]: ").strip() or "1433"
    if not port_text.isdecimal() or not 1 <= int(port_text) <= 65535:
        raise ValueError("Enter a port number between 1 and 65535.")
    password = getpass.getpass("Password for SQL login profile_service_login: ")
    if not password.strip() or any(c in password for c in ("\r", "\n", "\x00")):
        raise ValueError("The password must be nonempty and contain no line breaks.")
    settings = {
        "DB_AUTH": "sql",
        "DB_DRIVER": "ODBC Driver 18 for SQL Server",
        "DB_SERVER": f"host.docker.internal,{int(port_text)}",
        "DB_DATABASE": "Assessment1DB",
        "DB_USERNAME": "profile_service_login",
        "DB_PASSWORD": password,
        "DB_ENCRYPT": "yes",
        "DB_TRUST_SERVER_CERTIFICATE": "yes",
        "DB_CONNECTION_TIMEOUT": "5",
        "DB_QUERY_TIMEOUT": "10",
    }
    previous = {key: os.environ.get(key) for key in settings}
    try:
        os.environ.update(settings)
        os.environ["DB_SERVER"] = f"tcp:127.0.0.1,{int(port_text)}"
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute("SELECT DB_NAME(), ORIGINAL_LOGIN();")
                row = cursor.fetchone()
                if row[0] != "Assessment1DB" or row[1] != "profile_service_login":
                    raise ValueError("Connected to an unexpected database or login.")
                cursor.execute("SELECT TOP (1) UserID FROM CW2.vw_UserProfile;")
                cursor.fetchone()
        text = "".join(f"{key}={value}\n" for key, value in settings.items())
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            output.write(text)
        print("PASS | SQL login connected over local TCP and read the CW2 profile view.")
        print("Created .env.docker. Keep this file private; do not commit or upload it.")
        print("Docker-to-host connectivity still needs the container connection check.")
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":
    try:
        main()
    except pyodbc.Error as error:
        code = str(error.args[0]) if error.args else "unknown"
        code = code if len(code) == 5 and code.isalnum() else "configuration"
        print(f"FAIL | SQL connection or query failed (SQLSTATE: {code}).")
        print("Check TCP/IP, the server restart, SQL login credentials and CW2 grants.")
        print("No new Docker configuration was written.")
        raise SystemExit(1)
    except (ValueError, OSError) as error:
        print(f"FAIL | {error}")
        raise SystemExit(1)
    except (KeyboardInterrupt, EOFError):
        print("\nConfiguration cancelled.")
        raise SystemExit(1)
