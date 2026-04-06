"""
helpers.py — Utility Functions (Validation + Logging)
=====================================================
PURPOSE:
    Provides reusable helper functions used across the entire application:
    1. Logger setup with daily rolling log files
    2. Input validation for usernames, passwords, and site names
    3. Password standards text generator for the UI

DESIGN PATTERN:
    These are pure utility functions — they don't depend on any GUI or DB code.
    This makes them easy to test and reuse. Both the CLI (create_admin.py) and
    the GUI (add_password.py) use the same validation functions, ensuring
    consistent rules everywhere.
"""

import logging
import re
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from app.utils.constants import (
    LOG_DIR,
    LOG_LEVEL,
    PWD_MAX_LENGTH,
    PWD_MIN_LENGTH,
    PWD_REQUIRE_DIGIT,
    PWD_REQUIRE_LOWER,
    PWD_REQUIRE_SPECIAL,
    PWD_REQUIRE_UPPER,
    SPECIAL_CHARS,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
)

# =============================================================================
# LOGGING SETUP
# =============================================================================


def setup_logger(name: str) -> logging.Logger:
    """Create and configure a logger with daily rotating file output.

    HOW DAILY ROTATION WORKS:
        - Logs are written to logs/app.log
        - At midnight, the current log is renamed to app.log.2025-01-15 (date suffix)
        - A new empty app.log is created for the new day
        - Old logs are automatically deleted after 30 days (backupCount=30)

    WHY USE __name__ AS THE LOGGER NAME?
        Each module calls setup_logger(__name__), which gives it a unique name
        like 'app.services.auth_service'. This appears in log entries so you
        can trace which module generated each log message.

    WHY CHECK 'if not logger.handlers'?
        Prevents adding duplicate handlers if setup_logger is called multiple
        times for the same module (which happens with Python's import caching).

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        Configured logging.Logger instance.

    Example log output:
        2025-01-15 10:30:45,123 | app.services.auth_service | INFO | User 'admin' authenticated
    """
    # Create the logs/ directory if it doesn't exist
    log_path = Path(LOG_DIR)
    log_path.mkdir(exist_ok=True)

    # Get or create a logger with the given name
    logger = logging.getLogger(name)

    # Only add handlers if this logger hasn't been set up yet
    if not logger.handlers:
        # Set the minimum log level from .env (e.g., "INFO" -> logging.INFO)
        logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

        # TimedRotatingFileHandler rotates the log file at midnight every day
        handler = TimedRotatingFileHandler(
            log_path / "app.log",  # Log file path
            when="midnight",  # Rotate at midnight
            interval=1,  # Every 1 day
            backupCount=30,  # Keep 30 days of old logs
            encoding="utf-8",  # Support international characters
        )
        handler.suffix = "%Y-%m-%d"  # Rotated files get date suffix: app.log.2025-01-15

        # Format: timestamp | module_name | level | message
        formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================


def validate_username(username: str) -> tuple[bool, str]:
    """Validate a username against the configured standards.

    Rules (configurable via .env):
        - Not empty
        - Between USERNAME_MIN_LENGTH and USERNAME_MAX_LENGTH characters
        - Only alphanumeric characters and underscores (regex: ^[a-zA-Z0-9_]+$)

    Args:
        username: The username string to validate.

    Returns:
        Tuple of (is_valid: bool, error_message: str).
        If valid, error_message is an empty string.

    Example:
        >>> validate_username("john_doe")
        (True, "")
        >>> validate_username("ab")
        (False, "Username must be at least 3 characters.")
    """
    if not username:
        return False, "Username is required."
    if len(username) < USERNAME_MIN_LENGTH:
        return False, f"Username must be at least {USERNAME_MIN_LENGTH} characters."
    if len(username) > USERNAME_MAX_LENGTH:
        return False, f"Username must be at most {USERNAME_MAX_LENGTH} characters."
    # re.match checks if the ENTIRE string matches the pattern
    # ^ = start, $ = end, [a-zA-Z0-9_]+ = one or more allowed characters
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username can only contain letters, digits, and underscores."
    return True, ""


def validate_password(password: str) -> tuple[bool, list[str]]:
    """Validate a password against the configured security standards.

    Rules (all configurable via .env):
        - Length between PWD_MIN_LENGTH and PWD_MAX_LENGTH
        - No spaces allowed
        - At least 1 uppercase letter (if PWD_REQUIRE_UPPER is true)
        - At least 1 lowercase letter (if PWD_REQUIRE_LOWER is true)
        - At least 1 digit (if PWD_REQUIRE_DIGIT is true)
        - At least 1 special character (if PWD_REQUIRE_SPECIAL is true)

    Args:
        password: The password string to validate.

    Returns:
        Tuple of (is_valid: bool, errors: list[str]).
        If valid, errors is an empty list.
        If invalid, errors contains all the rules that were violated.

    Example:
        >>> validate_password("weak")
        (False, ["Min 8 characters.", "At least 1 uppercase letter.", ...])
        >>> validate_password("Strong1!")
        (True, [])
    """
    errors = []
    if len(password) < PWD_MIN_LENGTH:
        errors.append(f"Min {PWD_MIN_LENGTH} characters.")
    if len(password) > PWD_MAX_LENGTH:
        errors.append(f"Max {PWD_MAX_LENGTH} characters.")
    if " " in password:
        errors.append("No spaces allowed.")
    # re.search looks for the pattern ANYWHERE in the string (unlike re.match)
    if PWD_REQUIRE_UPPER and not re.search(r"[A-Z]", password):
        errors.append("At least 1 uppercase letter.")
    if PWD_REQUIRE_LOWER and not re.search(r"[a-z]", password):
        errors.append("At least 1 lowercase letter.")
    if PWD_REQUIRE_DIGIT and not re.search(r"\d", password):
        errors.append("At least 1 digit.")
    if PWD_REQUIRE_SPECIAL and not any(c in SPECIAL_CHARS for c in password):
        errors.append("At least 1 special character.")
    return (len(errors) == 0), errors


def get_password_standards_text() -> str:
    """Generate a human-readable text block showing the current password rules.

    This text is displayed on the Add Password page so the admin knows
    what rules to follow before typing. The rules are dynamically built
    from the .env configuration, so if you change the rules, the UI updates.

    Returns:
        Multi-line string with bullet points for each active rule.
    """
    lines = [
        f"• {PWD_MIN_LENGTH}-{PWD_MAX_LENGTH} characters",
        "• No spaces",
    ]
    if PWD_REQUIRE_UPPER:
        lines.append("• At least 1 uppercase letter (A-Z)")
    if PWD_REQUIRE_LOWER:
        lines.append("• At least 1 lowercase letter (a-z)")
    if PWD_REQUIRE_DIGIT:
        lines.append("• At least 1 digit (0-9)")
    if PWD_REQUIRE_SPECIAL:
        lines.append("• At least 1 special character (!@#$%^&*...)")
    return "\n".join(lines)


def validate_site_name(site: str) -> tuple[bool, str]:
    """Validate a site/service name.

    Rules:
        - Not empty or whitespace-only
        - Maximum 255 characters (matches the VARCHAR(255) in the DB)

    Args:
        site: The site name string to validate.

    Returns:
        Tuple of (is_valid: bool, error_message: str).
    """
    if not site or not site.strip():
        return False, "Site name is required."
    if len(site) > 255:
        return False, "Site name must be at most 255 characters."
    return True, ""
