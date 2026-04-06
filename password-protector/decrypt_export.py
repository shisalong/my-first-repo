"""
decrypt_export.py — CLI Script to Decrypt Exported .enc Files
===============================================================
PURPOSE:
    Decrypts a .enc file that was exported from the Password Protect app
    using the "Export Encrypted" feature on the Export Data page.

HOW TO RUN:
    uv run python decrypt_export.py

REQUIREMENTS:
    - The .enc file exported from the app
    - The export password you entered when exporting
    - The .salt file from the project root (must be the SAME .salt that
      existed when the export was created)

HOW IT WORKS:
    1. Prompts for the path to the .enc file
    2. Prompts for the export password (hidden input)
    3. Derives the same Fernet key using PBKDF2(password + .salt)
    4. Decrypts the file contents
    5. Saves the decrypted JSON to a file you choose

    The decrypted output is a JSON array of all passwords:
    [
      {
        "id": 1,
        "site_name": "Gmail",
        "username": "john@gmail.com",
        "password": "MyP@ssw0rd",
        "created_at": "2025-01-15 10:30:00"
      },
      ...
    ]
"""

import base64
import getpass
import json
import os
import sys

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Path to the .salt file at project root (same salt used during export)
_SALT_FILE = os.path.join(os.path.dirname(__file__), ".salt")


def _load_salt() -> bytes:
    """Load the salt from the .salt file.

    Returns:
        16 bytes of salt data.

    Raises:
        SystemExit: If the .salt file is missing.
    """
    path = os.path.normpath(_SALT_FILE)
    if not os.path.exists(path):
        print("ERROR: .salt file not found at project root.")
        print("The .salt file must be the same one that existed when the export was created.")
        print("Without it, decryption is impossible.")
        sys.exit(1)
    with open(path, "rb") as f:
        return f.read()


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive the Fernet key from the export password + salt.

    Uses the same PBKDF2 parameters as crypto_service.py to produce
    an identical key.

    Args:
        password: The export password entered during export.
        salt: The salt bytes from the .salt file.

    Returns:
        32-byte URL-safe base64-encoded Fernet key.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def main():
    print("=== Password Protect — Decrypt Exported File ===\n")

    # Step 1: Get the .enc file path
    enc_path = input("Path to .enc file: ").strip().strip('"')
    if not os.path.exists(enc_path):
        print(f"ERROR: File not found: {enc_path}")
        sys.exit(1)

    # Step 2: Get the export password (hidden input)
    password = getpass.getpass("Export password: ")
    if not password:
        print("ERROR: Password cannot be empty.")
        sys.exit(1)

    # Step 3: Load salt and derive key
    salt = _load_salt()
    key = _derive_key(password, salt)
    fernet = Fernet(key)

    # Step 4: Read and decrypt
    with open(enc_path, "rb") as f:
        encrypted_data = f.read()

    try:
        decrypted = fernet.decrypt(encrypted_data).decode()
    except InvalidToken:
        print("ERROR: Decryption failed. Wrong password or different .salt file.")
        sys.exit(1)

    # Step 5: Pretty-print and optionally save
    data = json.loads(decrypted)
    print(f"\nDecrypted {len(data)} password(s):\n")
    print(json.dumps(data, indent=2))

    # Ask to save
    save = input("\nSave to file? (y/n): ").strip().lower()
    if save == "y":
        out_path = input("Output file path (e.g., decrypted.json): ").strip().strip('"')
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
