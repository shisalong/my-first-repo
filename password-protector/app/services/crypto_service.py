"""
crypto_service.py — Encryption & Decryption Engine
====================================================
PURPOSE:
    Handles ALL encryption and decryption of passwords stored in the database.
    Uses the Fernet symmetric encryption scheme from the 'cryptography' library.

ENCRYPTION EXPLAINED (for college students):
    ┌─────────────────────────────────────────────────────────────────────┐
    │  SYMMETRIC ENCRYPTION = same key to encrypt AND decrypt            │
    │                                                                     │
    │  Plain text: "MyP@ssw0rd"                                          │
    │       ↓ encrypt(key)                                                │
    │  Cipher text: "gAAAAABl..." (unreadable gibberish)                 │
    │       ↓ decrypt(same key)                                           │
    │  Plain text: "MyP@ssw0rd"                                          │
    └─────────────────────────────────────────────────────────────────────┘

HOW THE KEY IS DERIVED:
    We don't use a random key — we DERIVE it from the admin's master password
    using PBKDF2 (Password-Based Key Derivation Function 2).

    Master Password → PBKDF2(password, salt, 480000 iterations) → 32-byte key → Fernet

    WHY PBKDF2?
        - Makes brute-force attacks extremely slow (480,000 iterations)
        - Same password + same salt = same key (deterministic)
        - Different salt = different key (even with same password)

    WHAT IS THE SALT?
        A random 16-byte value stored in the .salt file at project root.
        Generated once on first run, reused forever after.
        Without the salt, you cannot derive the correct key.
        ⚠️ If you lose the .salt file, ALL encrypted passwords become unrecoverable!

SECURITY FLOW:
    1. Admin logs in with password "Admin1!"
    2. login_page.py calls init_crypto("Admin1!")
    3. PBKDF2 derives a 32-byte encryption key from "Admin1!" + salt
    4. Fernet is initialized with that key
    5. All encrypt/decrypt calls use this Fernet instance
    6. When admin logs out, the key is discarded (stays in memory until next login)
"""

import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.utils.helpers import setup_logger

logger = setup_logger(__name__)

# Path to the salt file (project_root/.salt)
# os.path.dirname(__file__) = directory of this file (app/services/)
# "..", ".." navigates up to project root
_SALT_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".salt")

# Module-level Fernet instance. None until init_crypto() is called.
# This is the "engine" that does the actual encryption/decryption.
_fernet: Fernet | None = None


def _get_salt() -> bytes:
    """Load the salt from .salt file, or generate a new one if it doesn't exist.

    The salt is a random 16-byte value that makes the key derivation unique.
    Two users with the same password but different salts will get different keys.

    Returns:
        16 bytes of salt data.

    IMPORTANT:
        The .salt file is critical! If deleted, all previously encrypted
        passwords become permanently unrecoverable. Back it up!
    """
    path = os.path.normpath(_SALT_FILE)
    if os.path.exists(path):
        # Salt already exists — read and return it
        with open(path, "rb") as f:
            return f.read()
    # First run — generate a new random salt and save it
    salt = os.urandom(16)  # 16 cryptographically secure random bytes
    with open(path, "wb") as f:
        f.write(salt)
    return salt


def _derive_key(master_password: str) -> bytes:
    """Derive a Fernet-compatible encryption key from the master password.

    Uses PBKDF2-HMAC-SHA256 with 480,000 iterations.
    The high iteration count makes brute-force attacks impractical:
    - 1 attempt takes ~0.1 seconds
    - Trying 1 billion passwords would take ~3 years

    Args:
        master_password: The admin's login password (plain text).

    Returns:
        32-byte URL-safe base64-encoded key suitable for Fernet.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),  # Hash function used in each iteration
        length=32,  # Output key length in bytes (256 bits)
        salt=_get_salt(),  # Our unique salt from .salt file
        iterations=480_000,  # Number of hash iterations (OWASP recommended)
    )
    # kdf.derive() produces raw bytes; Fernet needs base64-encoded bytes
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))


def init_crypto(master_password: str):
    """Initialize the encryption engine with the admin's master password.

    Called once after successful login. All subsequent encrypt/decrypt calls
    use the Fernet instance created here.

    Args:
        master_password: The admin's login password (used to derive the key).
    """
    global _fernet
    key = _derive_key(master_password)
    _fernet = Fernet(key)
    logger.info("Crypto engine initialized.")


def encrypt(plaintext: str) -> str:
    """Encrypt a plain text password for storage in the database.

    Args:
        plaintext: The password to encrypt (e.g., "MyP@ssw0rd").

    Returns:
        Fernet-encrypted string (e.g., "gAAAAABl..."). Safe to store in DB.

    Raises:
        RuntimeError: If init_crypto() hasn't been called yet.
    """
    if _fernet is None:
        raise RuntimeError("Crypto not initialized. Call init_crypto first.")
    # .encode() converts str to bytes (Fernet works with bytes)
    # .decode() converts the encrypted bytes back to str (for DB storage)
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt an encrypted password retrieved from the database.

    Args:
        ciphertext: The Fernet-encrypted string from the DB.

    Returns:
        The original plain text password.

    Raises:
        RuntimeError: If init_crypto() hasn't been called yet.
        cryptography.fernet.InvalidToken: If the key is wrong or data is corrupted.
    """
    if _fernet is None:
        raise RuntimeError("Crypto not initialized. Call init_crypto first.")
    return _fernet.decrypt(ciphertext.encode()).decode()


def encrypt_for_export(data: str, export_password: str) -> bytes:
    """Encrypt data using a SEPARATE password (for encrypted file export).

    This uses a DIFFERENT key than the main app encryption. The export password
    is provided by the admin at export time, so the exported file can be
    decrypted independently without needing the admin's login password.

    Args:
        data: The JSON string of all passwords to encrypt.
        export_password: The password chosen by the admin for this export.

    Returns:
        Encrypted bytes to write to the .enc file.
    """
    key = _derive_key(export_password)
    f = Fernet(key)
    return f.encrypt(data.encode())
