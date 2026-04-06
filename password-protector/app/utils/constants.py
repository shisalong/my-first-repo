"""
constants.py — Central Configuration Loader
============================================
PURPOSE:
    This module loads ALL application settings from the .env file and makes them
    available as Python constants. Every other module imports from here instead
    of reading .env directly. This is the "Single Source of Truth" pattern.

HOW IT WORKS:
    1. python-dotenv reads the .env file at project root
    2. os.getenv() reads each value (with a fallback default if missing)
    3. Values are converted to the correct Python type (int, bool, str)
    4. Other modules do: from app.utils.constants import DB_HOST, PAGE_SIZE, etc.

WHY .env FILE?
    - Keeps secrets (DB password) out of source code
    - Easy to change settings without modifying Python code
    - Different settings per environment (dev vs production)
    - .env is listed in .gitignore so it's never committed to Git
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# load_dotenv() reads the .env file and sets the values as environment variables.
# Path(__file__).resolve() gets the absolute path of THIS file (constants.py),
# then .parent.parent.parent navigates up 3 levels to the project root:
#   constants.py -> utils/ -> app/ -> project_root/.env
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


def _bool(val: str) -> bool:
    """Convert a string from .env to a Python boolean.
    .env files only store strings, so 'true' needs to become True.
    Accepts: 'true', '1', 'yes' (case-insensitive) as True.
    Everything else is False.
    """
    return val.lower() in ("true", "1", "yes")


# =============================================================================
# DATABASE SETTINGS
# These are used by app/db/connection.py to connect to MySQL.
# =============================================================================
DB_HOST = os.getenv("DB_HOST", "localhost")  # MySQL server hostname
DB_PORT = int(os.getenv("DB_PORT", "3306"))  # MySQL server port (default: 3306)
DB_NAME = os.getenv("DB_NAME", "password_protect_db")  # Database name
DB_USER = os.getenv("DB_USER", "admin")  # MySQL username
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin123**")  # MySQL password

# =============================================================================
# MFA (Multi-Factor Authentication) SETTINGS
# When True, users must enter a TOTP code after password login.
# Set to 'false' in .env to disable MFA during development/testing.
# =============================================================================
MFA_ENABLED = _bool(os.getenv("MFA_ENABLED", "true"))

# =============================================================================
# PAGINATION
# Controls how many records are shown per page in View/Delete/Audit pages.
# =============================================================================
PAGE_SIZE = int(os.getenv("PAGE_SIZE", "10"))

# =============================================================================
# LOGGING
# LOG_DIR: folder where log files are stored (relative to project root)
# LOG_LEVEL: minimum severity to log (DEBUG < INFO < WARNING < ERROR < CRITICAL)
# =============================================================================
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# =============================================================================
# PASSWORD VALIDATION STANDARDS
# These rules are enforced when adding new passwords AND when creating the admin.
# All configurable via .env so you can adjust without changing code.
# =============================================================================
PWD_MIN_LENGTH = int(os.getenv("PWD_MIN_LENGTH", "8"))  # Minimum password length
PWD_MAX_LENGTH = int(os.getenv("PWD_MAX_LENGTH", "64"))  # Maximum password length
PWD_REQUIRE_UPPER = _bool(os.getenv("PWD_REQUIRE_UPPER", "true"))  # Require A-Z
PWD_REQUIRE_LOWER = _bool(os.getenv("PWD_REQUIRE_LOWER", "true"))  # Require a-z
PWD_REQUIRE_DIGIT = _bool(os.getenv("PWD_REQUIRE_DIGIT", "true"))  # Require 0-9
PWD_REQUIRE_SPECIAL = _bool(os.getenv("PWD_REQUIRE_SPECIAL", "true"))  # Require !@#...
USERNAME_MIN_LENGTH = int(os.getenv("USERNAME_MIN_LENGTH", "3"))  # Min username length
USERNAME_MAX_LENGTH = int(os.getenv("USERNAME_MAX_LENGTH", "30"))  # Max username length

# =============================================================================
# APPLICATION CONSTANTS
# Hard-coded values that don't need to be configurable.
# =============================================================================
APP_NAME = "Password Protect"
SPECIAL_CHARS = "!@#$%^&*()-_=+[]{}|;:',.<>?/`~"  # Allowed special characters
