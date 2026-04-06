"""
export_service.py — Data Export Service
========================================
PURPOSE:
    Exports all stored passwords to external files in three formats:
    1. CSV  — Comma-separated values (opens in Excel/Google Sheets)
    2. JSON — JavaScript Object Notation (structured data format)
    3. Encrypted — Fernet-encrypted binary file (password-protected)

EXPORT FLOW:
    ┌──────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
    │ Database │────→│ Decrypt all  │────→│ Format as   │────→│ Write to │
    │ (encrypted│    │ passwords    │     │ CSV/JSON/   │     │ file     │
    │ passwords)│    │ (plain text) │     │ encrypted   │     │          │
    └──────────┘     └──────────────┘     └─────────────┘     └──────────┘

SECURITY WARNING:
    CSV and JSON exports contain PLAIN TEXT passwords! These files should be:
    - Stored securely or deleted after use
    - Never committed to Git or shared over email
    - The encrypted export option is recommended for sharing/backup

HOW ENCRYPTED EXPORT WORKS:
    1. All passwords are decrypted and formatted as JSON
    2. The admin provides an "export password" (separate from their login password)
    3. A new Fernet key is derived from the export password using PBKDF2
    4. The JSON data is encrypted with this new key
    5. The encrypted bytes are written to a .enc file
    6. To decrypt later, you need the same export password + the .salt file
"""

import csv
import json

from app.services.crypto_service import encrypt_for_export
from app.services.password_service import decrypt_password, get_all_passwords
from app.utils.helpers import setup_logger

logger = setup_logger(__name__)


def _prepare_rows() -> list[dict]:
    """Fetch all passwords from DB and decrypt them for export.

    This is a private helper function (prefixed with _) used by all three
    export functions. It:
    1. Fetches all encrypted passwords from the database
    2. Decrypts each password
    3. Returns a clean list of dicts ready for CSV/JSON formatting

    Returns:
        List of dicts with keys: id, site_name, username, password, created_at.
        Note: 'password' here is the DECRYPTED plain text (not 'encrypted_password').
    """
    rows = get_all_passwords()
    result = []
    for r in rows:
        result.append(
            {
                "id": r["id"],
                "site_name": r["site_name"],
                "username": r["username"],
                # Decrypt the password from ciphertext to plain text
                "password": decrypt_password(r["encrypted_password"]),
                # Convert datetime to string for JSON serialization
                "created_at": str(r["created_at"]),
            }
        )
    return result


def export_csv(filepath: str):
    """Export all passwords to a CSV file.

    CSV (Comma-Separated Values) is a simple text format that can be opened
    in Excel, Google Sheets, or any text editor.

    Output example:
        id,site_name,username,password,created_at
        1,Gmail,john@gmail.com,MyP@ssw0rd,2025-01-15 10:30:00

    Args:
        filepath: Full path where the CSV file will be saved.
                  Chosen by the admin via a file dialog in the GUI.
    """
    rows = _prepare_rows()
    # newline="" prevents extra blank lines on Windows
    # encoding="utf-8" supports international characters
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "site_name", "username", "password", "created_at"])
        writer.writeheader()  # Write the column names as the first row
        writer.writerows(rows)  # Write all data rows
    logger.info(f"Exported {len(rows)} records to CSV: {filepath}")


def export_json(filepath: str):
    """Export all passwords to a JSON file.

    JSON (JavaScript Object Notation) is a structured data format widely used
    in programming. It's human-readable and easy to parse programmatically.

    Output example:
        [
          {
            "id": 1,
            "site_name": "Gmail",
            "username": "john@gmail.com",
            "password": "MyP@ssw0rd",
            "created_at": "2025-01-15 10:30:00"
          }
        ]

    Args:
        filepath: Full path where the JSON file will be saved.
    """
    rows = _prepare_rows()
    with open(filepath, "w", encoding="utf-8") as f:
        # indent=2 makes the JSON human-readable (pretty-printed)
        # default=str handles datetime objects that aren't JSON-serializable
        json.dump(rows, f, indent=2, default=str)
    logger.info(f"Exported {len(rows)} records to JSON: {filepath}")


def export_encrypted(filepath: str, export_password: str):
    """Export all passwords to an encrypted binary file.

    This is the most secure export option. The file is encrypted with a
    password the admin provides, so it can be safely stored or transferred.

    To decrypt the file later, you would need:
    1. The export password
    2. The .salt file from the project root
    3. A Python script using the same PBKDF2 + Fernet logic

    Args:
        filepath:        Full path where the .enc file will be saved.
        export_password: The password to encrypt the export with.
    """
    rows = _prepare_rows()
    # Convert the list of dicts to a JSON string
    data = json.dumps(rows, default=str)
    # Encrypt the JSON string using a key derived from the export password
    encrypted = encrypt_for_export(data, export_password)
    # Write raw encrypted bytes (not text) to the file
    with open(filepath, "wb") as f:
        f.write(encrypted)
    logger.info(f"Exported {len(rows)} records to encrypted file: {filepath}")
