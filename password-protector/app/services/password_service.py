"""
password_service.py — Password CRUD Business Logic
====================================================
PURPOSE:
    Provides the business logic layer for password management operations:
    - ADD: Encrypt and store a new password
    - VIEW: Retrieve passwords with pagination and search
    - DELETE: Remove a password after verifying it exists
    - DECRYPT: Reveal an encrypted password

ARCHITECTURE (3-Layer Pattern):
    ┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
    │  GUI Layer   │────→│  Service Layer   │────→│   DB Layer   │
    │ (Tkinter)    │     │ (This file)      │     │ (connection) │
    │              │     │                  │     │              │
    │ add_password │     │ Validates logic, │     │ Executes SQL │
    │ .py calls    │     │ encrypts data,   │     │ queries      │
    │ add_password │     │ calculates pages │     │              │
    └─────────────┘     └──────────────────┘     └──────────────┘

    The GUI never talks to the DB directly. The service layer sits in between,
    handling encryption, pagination math, and business rules.

PAGINATION EXPLAINED:
    If you have 25 passwords and PAGE_SIZE=10:
    - Page 1: rows 1-10   (OFFSET 0,  LIMIT 10)
    - Page 2: rows 11-20  (OFFSET 10, LIMIT 10)
    - Page 3: rows 21-25  (OFFSET 20, LIMIT 10)
    - total_pages = ceil(25 / 10) = 3

    The GUI shows "Page 1 / 3" and Prev/Next buttons.
"""

import math

from app.db.connection import execute_count, execute_query
from app.db.queries import (
    COUNT_PASSWORDS,
    COUNT_SEARCH_PASSWORDS,
    DELETE_PASSWORD,
    GET_PASSWORD_BY_ID,
    INSERT_PASSWORD,
    SEARCH_PASSWORDS,
    SELECT_ALL_PASSWORDS,
    SELECT_PASSWORDS,
)
from app.services.crypto_service import decrypt, encrypt
from app.utils.constants import PAGE_SIZE
from app.utils.helpers import setup_logger

logger = setup_logger(__name__)


def add_password(site_name: str, username: str, password: str) -> int:
    """Encrypt and store a new password in the database.

    Flow:
        1. Encrypt the plain text password using Fernet (crypto_service.encrypt)
        2. Store site_name, username, and encrypted_password in the DB
        3. Return the new row's auto-generated ID

    Args:
        site_name: The website/service name (e.g., "Gmail", "GitHub").
        username:  The login username for that site.
        password:  The plain text password to encrypt and store.

    Returns:
        The auto-generated ID of the new database row.
    """
    encrypted = encrypt(password)  # "MyP@ss" → "gAAAAABl..."
    row_id = execute_query(INSERT_PASSWORD, (site_name, username, encrypted))
    logger.info(f"Password added for site '{site_name}', user '{username}'.")
    return row_id


def get_passwords(page: int = 1) -> tuple[list[dict], int]:
    """Fetch a paginated list of passwords (newest first).

    Args:
        page: The page number to fetch (1-based). Default is page 1.

    Returns:
        Tuple of:
        - list[dict]: The password rows for this page. Each dict has keys:
          id, site_name, username, encrypted_password, created_at
        - int: Total number of pages available.

    Example:
        rows, total_pages = get_passwords(page=2)
        # rows = [{id: 11, site_name: "GitHub", ...}, ...] (up to 10 rows)
        # total_pages = 3
    """
    # Calculate OFFSET: page 1 → offset 0, page 2 → offset 10, etc.
    offset = (page - 1) * PAGE_SIZE
    rows = execute_query(SELECT_PASSWORDS, (PAGE_SIZE, offset), fetch=True)
    total = execute_count(COUNT_PASSWORDS)
    # math.ceil rounds UP: ceil(25/10) = 3, ceil(20/10) = 2
    total_pages = math.ceil(total / PAGE_SIZE) if total > 0 else 1
    return rows, total_pages


def search_passwords(query: str, page: int = 1) -> tuple[list[dict], int]:
    """Search passwords by site_name or username with pagination.

    Uses SQL LIKE with wildcards: "%gmail%" matches "Gmail", "gmail.com", etc.

    Args:
        query: The search term entered by the user.
        page:  Page number for paginated results.

    Returns:
        Same format as get_passwords(): (rows, total_pages).
    """
    like = f"%{query}%"  # Wrap in wildcards for partial matching
    offset = (page - 1) * PAGE_SIZE
    rows = execute_query(SEARCH_PASSWORDS, (like, like, PAGE_SIZE, offset), fetch=True)
    total = execute_count(COUNT_SEARCH_PASSWORDS, (like, like))
    total_pages = math.ceil(total / PAGE_SIZE) if total > 0 else 1
    return rows, total_pages


def get_all_passwords() -> list[dict]:
    """Fetch ALL passwords without pagination (used for data export).

    Returns:
        List of all password rows from the database.
    """
    return execute_query(SELECT_ALL_PASSWORDS, fetch=True)


def delete_password(pwd_id: int) -> bool:
    """Delete a password by its ID after verifying it exists.

    We check existence first to provide a meaningful error message
    if the record was already deleted (e.g., by another session).

    Args:
        pwd_id: The database ID of the password to delete.

    Returns:
        True if the password was found and deleted.
        False if no password with that ID exists.
    """
    # First, verify the record exists
    rows = execute_query(GET_PASSWORD_BY_ID, (pwd_id,), fetch=True)
    if not rows:
        return False
    # Record exists — delete it
    execute_query(DELETE_PASSWORD, (pwd_id,))
    logger.info(f"Password id={pwd_id} deleted.")
    return True


def decrypt_password(encrypted: str) -> str:
    """Decrypt an encrypted password for display in the UI.

    This is called when the admin clicks "Reveal Selected Password"
    on the View Passwords page.

    Args:
        encrypted: The Fernet-encrypted string from the database.

    Returns:
        The original plain text password.
    """
    return decrypt(encrypted)
