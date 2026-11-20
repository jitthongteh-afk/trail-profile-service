from getpass import getpass

import httpx


AUTHENTICATOR_URL = (
    "https://web.socem.plymouth.ac.uk/COMP2001/auth/api/users"
)


class AuthenticationServiceError(Exception):
    """Raised when the external authentication service cannot be used."""


def parse_authentication_result(payload: object) -> bool:
    """Accept only the expected authentication response format."""
    if payload == ["Verified", "True"]:
        return True

    if payload == ["Verified", "False"]:
        return False

    raise AuthenticationServiceError(
        "Authentication service returned an unexpected response."
    )


def verify_credentials(email: str, password: str) -> bool:
    """Verify credentials without storing or logging the password."""
    email = email.strip()

    if not email or not password:
        return False

    try:
        with httpx.Client(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=False,
            verify=True,
        ) as client:
            response = client.post(
                AUTHENTICATOR_URL,
                json={
                    "email": email,
                    "password": password,
                },
                headers={"Accept": "application/json"},
            )

    except httpx.TimeoutException:
        raise AuthenticationServiceError(
            "Authentication service timed out. Please try again."
        ) from None

    except httpx.RequestError:
        raise AuthenticationServiceError(
            "Unable to connect to the authentication service."
        ) from None

    if response.status_code != 200:
        raise AuthenticationServiceError(
            "Authentication service returned HTTP "
            f"{response.status_code}."
        )

    try:
        payload = response.json()
    except ValueError:
        raise AuthenticationServiceError(
            "Authentication service returned invalid JSON."
        ) from None

    return parse_authentication_result(payload)


def main():
    print("External authentication check")
    print("Credentials will be sent to the course authentication service.")

    try:
        email = input("Email: ").strip()
        password = getpass("Password: ")

        verified = verify_credentials(email, password)

    except (KeyboardInterrupt, EOFError):
        print("\nAuthentication check cancelled.")
        raise SystemExit(130)

    except AuthenticationServiceError as error:
        print(f"ERROR | {error}")
        raise SystemExit(2)

    finally:
        # Remove the local reference after the authentication attempt.
        # This does not guarantee secure erasure from process memory.
        password = None

    if verified:
        print("VERIFIED | Credentials accepted.")
    else:
        print("REJECTED | Invalid email or password.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()