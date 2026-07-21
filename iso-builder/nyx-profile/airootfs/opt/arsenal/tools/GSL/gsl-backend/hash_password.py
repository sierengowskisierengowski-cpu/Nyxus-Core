#!/usr/bin/env python3
"""Generate a PBKDF2 password hash for GSL auth.

Usage:
    python3 hash_password.py                # prompts for the password
    python3 hash_password.py 'mypassword'   # takes it as an argument

Copy the printed line into gsl-backend/.env (see .env.example).
"""
import getpass
import sys

from app.auth import hash_password


def main() -> None:
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = getpass.getpass("New GSL password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match.", file=sys.stderr)
            sys.exit(1)
    if not password:
        print("Password must not be empty.", file=sys.stderr)
        sys.exit(1)
    print(f"GSL_AUTH_PASSWORD_HASH={hash_password(password)}")


if __name__ == "__main__":
    main()
