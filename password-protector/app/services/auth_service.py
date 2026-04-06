"""
auth_service.py — Authentication & MFA Service
================================================
PURPOSE:
    Handles the two-step authentication process:
    1. Username + Password verification (using bcrypt)
    2. TOTP MFA verification (using pyotp / Google Authenticator)

AUTHENTICATION FLOW:
    ┌──────────────────────────────────────────────────────────────────┐
    │  Step 1: Password Check                                         │
    │  ┌─────────┐    ┌──────────┐    ┌──────────────┐               │
    │  │ User    │───→│ bcrypt   │───→│ DB stored    │               │
    │  │ types   │    │ checkpw  │    │ password_hash│               │
    │  │ "Admin1"│    │          │    │ "$2b$12..."  │               │
    │  └─────────┘    └──────────┘    └──────────────┘               │
    │                  Match? → Step 2                                │
    │                                                                  │
    │  Step 2: TOTP Check (if MFA_ENABLED=true)                       │
    │  ┌─────────┐    ┌──────────┐    ┌──────────────┐               │
    │  │ User    │───→│ pyotp    │───→│ DB stored    │               │
    │  │ enters  │    │ verify   │    │ totp_secret  │               │
    │  │ "482901"│    │          │    │ "JBSWY3DP.."│               │
    │  └─────────┘    └──────────┘    └──────────────┘               │
    │                  Match? → Dashboard                             │
    └──────────────────────────────────────────────────────────────────┘

WHAT IS bcrypt?
    bcrypt is a password hashing algorithm specifically designed for passwords.
    Unlike MD5 or SHA256, bcrypt is intentionally SLOW (to prevent brute-force).
    It also includes a random "salt" in every hash, so two users with the same
    password get different hashes.

    Example:
        Password: "Admin1!"
        Hash: "$2b$12$LJ3m5ZQnJPKSqX8Y..." (60 characters, different every time)

    bcrypt.checkpw() re-hashes the input and compares it to the stored hash.
    It NEVER decrypts the hash — hashing is one-way.

WHAT IS TOTP?
    TOTP = Time-based One-Time Password
    - The server and the authenticator app share a SECRET KEY
    - Both use the current time + the secret to generate the same 6-digit code
    - The code changes every 30 seconds
    - valid_window=1 means we accept codes from 30 seconds ago too (clock skew)
"""

import bcrypt
import pyotp

from app.db.connection import execute_query
from app.db.queries import GET_ADMIN
from app.utils.constants import MFA_ENABLED
from app.utils.helpers import setup_logger

logger = setup_logger(__name__)


def authenticate(username: str, password: str) -> dict | None:
    """Verify admin credentials against the database.

    Steps:
        1. Look up the user in admin_users table by username
        2. If not found → return None (login failed)
        3. If found → compare the provided password against the stored bcrypt hash
        4. If match → return the user dict; if not → return None

    Args:
        username: The admin username entered in the login form.
        password: The plain text password entered in the login form.

    Returns:
        dict: The user record from DB (id, username, password_hash, totp_secret, created_at)
              if authentication succeeds.
        None: If username not found or password doesn't match.
    """
    # Query the database for this username
    rows = execute_query(GET_ADMIN, (username,), fetch=True)
    if not rows:
        logger.warning(f"Login failed: user '{username}' not found.")
        return None

    user = rows[0]  # First (and only) matching row

    # bcrypt.checkpw compares the plain password against the stored hash.
    # Both must be bytes, so we .encode() the strings.
    # This is a ONE-WAY check — we never "decrypt" the hash.
    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        logger.warning(f"Login failed: wrong password for '{username}'.")
        return None

    logger.info(f"User '{username}' authenticated successfully.")
    return user


def verify_totp(secret: str, code: str) -> bool:
    """Verify a 6-digit TOTP code from the authenticator app.

    Args:
        secret: The TOTP secret key stored in the database for this user.
        code:   The 6-digit code the user entered from their authenticator app.

    Returns:
        True if the code is valid (matches current or previous 30-second window).
        False if the code is invalid or expired.
    """
    totp = pyotp.TOTP(secret)
    # valid_window=1 accepts the current code AND the previous one
    # This handles slight clock differences between server and phone
    return totp.verify(code, valid_window=1)


def is_mfa_enabled() -> bool:
    """Check if MFA is enabled in the .env configuration.

    Returns:
        True if MFA_ENABLED=true in .env, False otherwise.
    """
    return MFA_ENABLED


def generate_totp_secret() -> str:
    """Generate a new random TOTP secret key.

    This is a base32-encoded string like "JBSWY3DPEHPK3PXP".
    Used when creating a new admin user in create_admin.py.

    Returns:
        Random base32 string suitable for TOTP.
    """
    return pyotp.random_base32()


def get_totp_uri(secret: str, username: str) -> str:
    """Generate a TOTP provisioning URI for QR code generation.

    This URI follows the otpauth:// protocol that authenticator apps understand.
    When encoded as a QR code and scanned, the app automatically adds the account.

    Example URI:
        otpauth://totp/PasswordProtect:admin?secret=JBSWY3DP...&issuer=PasswordProtect

    Args:
        secret:   The TOTP secret key.
        username: The admin username (shown in the authenticator app).

    Returns:
        otpauth:// URI string.
    """
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name="PasswordProtect")
