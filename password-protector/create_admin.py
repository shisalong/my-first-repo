"""
create_admin.py — CLI Script to Create the Admin User
=======================================================
PURPOSE:
    This is a command-line script (NOT part of the GUI) that creates the
    single admin user who can log into the Password Protect application.

HOW TO RUN:
    uv run python create_admin.py

WHAT IT DOES (step by step):
    1. Prompts for a username (validated against the same rules as the GUI)
    2. Checks if that username already exists in the database
    3. Prompts for a password (hidden input, validated against password standards)
    4. Asks to confirm the password (must match)
    5. Hashes the password using bcrypt (one-way, irreversible)
    6. If MFA is enabled in .env:
       a. Generates a random TOTP secret key
       b. Creates a QR code in the terminal (ASCII art)
       c. User scans the QR code with Google Authenticator / Microsoft Authenticator
       d. User enters the 6-digit code to verify the setup works
    7. Saves the admin user to the admin_users table

WHY A SEPARATE SCRIPT?
    - The admin must exist BEFORE the GUI app can be used (chicken-and-egg problem)
    - CLI is simpler for initial setup — no GUI needed
    - Can be run on servers without a display (headless environments)
    - Same script works on Windows and macOS

WHY bcrypt FOR PASSWORD HASHING?
    bcrypt is specifically designed for password storage:
    - It's intentionally slow (prevents brute-force attacks)
    - It includes a random salt in every hash (prevents rainbow table attacks)
    - The hash is one-way — you can verify a password but never recover it

    Example:
        Password: "Admin1!"
        bcrypt hash: "$2b$12$LJ3m5ZQnJPKSqX8Y..." (different every time due to salt)

WHY QR CODE IN TERMINAL?
    The QR code encodes a URI like:
        otpauth://totp/PasswordProtect:admin?secret=JBSWY3DP...&issuer=PasswordProtect

    When scanned by an authenticator app, it automatically adds the account.
    The ASCII QR code works in any terminal — no image viewer needed.
"""

import getpass
import sys

import bcrypt
import pyotp
import qrcode

from app.db.connection import execute_query
from app.db.queries import GET_ADMIN, INSERT_ADMIN
from app.utils.constants import MFA_ENABLED
from app.utils.helpers import validate_password, validate_username


def main():
    print("=== Password Protect - Admin Setup ===\n")

    # -------------------------------------------------------------------------
    # STEP 1: Get and validate the username
    # Loop until a valid username is entered
    # -------------------------------------------------------------------------
    while True:
        username = input("Enter admin username: ").strip()
        ok, msg = validate_username(username)
        if ok:
            break
        print(f"  Error: {msg}")

    # -------------------------------------------------------------------------
    # STEP 2: Check if this username already exists in the database
    # We only allow ONE admin user, so duplicates are rejected
    # -------------------------------------------------------------------------
    existing = execute_query(GET_ADMIN, (username,), fetch=True)
    if existing:
        print(f"Admin user '{username}' already exists. Exiting.")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # STEP 3: Get and validate the password
    # getpass.getpass() hides the input (no characters shown while typing)
    # Loop until a valid password is entered AND confirmed
    # -------------------------------------------------------------------------
    while True:
        password = getpass.getpass("Enter admin password: ")
        ok, errors = validate_password(password)
        if ok:
            # Password meets all standards — now confirm it
            confirm = getpass.getpass("Confirm password: ")
            if password == confirm:
                break
            print("  Passwords do not match.")
        else:
            # Show all validation errors
            print("  Password errors:")
            for e in errors:
                print(f"    - {e}")

    # -------------------------------------------------------------------------
    # STEP 4: Hash the password with bcrypt
    # bcrypt.gensalt() generates a random salt
    # bcrypt.hashpw() combines the password + salt and hashes them
    # .decode() converts bytes to string for database storage
    # -------------------------------------------------------------------------
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    # -------------------------------------------------------------------------
    # STEP 5: Set up TOTP MFA (if enabled in .env)
    # -------------------------------------------------------------------------
    totp_secret = None
    if MFA_ENABLED:
        # Generate a random base32 secret (e.g., "JBSWY3DPEHPK3PXP")
        totp_secret = pyotp.random_base32()

        # Create the provisioning URI that authenticator apps understand
        uri = pyotp.TOTP(totp_secret).provisioning_uri(name=username, issuer_name="PasswordProtect")

        print("\n--- MFA Setup ---")
        print(f"TOTP Secret: {totp_secret}")
        print(f"Provisioning URI: {uri}")
        print("Scan the QR code below with your authenticator app:\n")

        # Generate and print an ASCII QR code in the terminal
        # box_size=1 and border=1 keep it small enough to fit in a terminal
        qr = qrcode.QRCode(box_size=1, border=1)
        qr.add_data(uri)
        qr.make()
        qr.print_ascii(invert=True)  # invert=True for better visibility on dark terminals

        # Verify the setup by asking the user to enter a code from their app
        # This ensures the QR code was scanned correctly
        while True:
            code = input("\nEnter the 6-digit code from your authenticator to verify: ").strip()
            if pyotp.TOTP(totp_secret).verify(code, valid_window=1):
                print("MFA verified successfully!")
                break
            print("Invalid code. Try again.")

    # -------------------------------------------------------------------------
    # STEP 6: Save the admin user to the database
    # -------------------------------------------------------------------------
    execute_query(INSERT_ADMIN, (username, password_hash, totp_secret))
    print(f"\nAdmin user '{username}' created successfully!")


if __name__ == "__main__":
    main()
