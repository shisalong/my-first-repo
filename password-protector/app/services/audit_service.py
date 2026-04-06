"""
audit_service.py — Audit Logging Service
==========================================
PURPOSE:
    Records every significant action in the application to the audit_log table.
    This creates a complete trail of "who did what and when" for security
    and accountability purposes.

WHAT GETS AUDITED:
    ┌──────────────────┬──────────────────────────────────────────────┐
    │ Action           │ When it's logged                             │
    ├──────────────────┼──────────────────────────────────────────────┤
    │ LOGIN            │ Admin successfully logs in                   │
    │ LOGIN_FAILED     │ Someone enters wrong credentials             │
    │ MFA_VERIFIED     │ Admin passes the TOTP check                  │
    │ MFA_FAILED       │ Someone enters wrong TOTP code               │
    │ ADD_PASSWORD     │ A new password is saved                      │
    │ VIEW_PASSWORD    │ Admin reveals (decrypts) a stored password   │
    │ DELETE_PASSWORD  │ A password is deleted                        │
    │ EXPORT           │ Data is exported to CSV/JSON/encrypted file  │
    └──────────────────┴──────────────────────────────────────────────┘

WHY AUDIT LOGGING MATTERS:
    1. Security: Detect brute-force login attempts (many LOGIN_FAILED entries)
    2. Accountability: Know exactly who deleted a password and when
    3. Compliance: Many security standards require audit trails
    4. Debugging: Trace the sequence of events that led to an issue

DUAL LOGGING:
    Every action is logged in TWO places:
    1. Database (audit_log table) — viewable in the Audit Log GUI page
    2. File (logs/app.log) — via the Python logger for system-level debugging
"""

import math

from app.db.connection import execute_count, execute_query
from app.db.queries import (
    COUNT_AUDIT,
    COUNT_FILTER_AUDIT,
    FILTER_AUDIT,
    INSERT_AUDIT,
    SELECT_ALL_AUDIT,
    SELECT_AUDIT,
)
from app.utils.constants import PAGE_SIZE
from app.utils.helpers import setup_logger

logger = setup_logger(__name__)

# All valid audit action types.
# Used by the Audit Log page's filter dropdown.
ACTIONS = [
    "LOGIN",
    "LOGIN_FAILED",
    "MFA_VERIFIED",
    "MFA_FAILED",
    "ADD_PASSWORD",
    "VIEW_PASSWORD",
    "DELETE_PASSWORD",
    "EXPORT",
]


def log_action(action: str, details: str, performed_by: str):
    """Record an action in the audit_log database table.

    This function is called from GUI pages and services whenever a
    significant event occurs. It writes to BOTH the database and the log file.

    Args:
        action:       One of the ACTIONS constants (e.g., "LOGIN", "ADD_PASSWORD").
        details:      Human-readable description (e.g., "Added password for site 'Gmail'").
        performed_by: The admin username who performed the action.

    Example:
        log_action("ADD_PASSWORD", "Added password for site 'Gmail', user 'john'.", "admin")
        # This creates a row in audit_log AND writes to logs/app.log
    """
    execute_query(INSERT_AUDIT, (action, details, performed_by))
    logger.info(f"Audit: {action} by {performed_by} - {details}")


def get_audit_logs(page: int = 1, action_filter: str = None) -> tuple[list[dict], int]:
    """Fetch paginated audit logs, optionally filtered by action type.

    Args:
        page:          Page number (1-based).
        action_filter: If provided, only return logs matching this action type.
                       If None, return all logs.

    Returns:
        Tuple of:
        - list[dict]: Audit log rows for this page. Each dict has keys:
          id, action, details, performed_by, performed_at
        - int: Total number of pages.

    Example:
        # Get all logs, page 1
        rows, total_pages = get_audit_logs(page=1)

        # Get only LOGIN events, page 1
        rows, total_pages = get_audit_logs(page=1, action_filter="LOGIN")
    """
    offset = (page - 1) * PAGE_SIZE
    if action_filter:
        # Filtered query — only rows where action matches
        rows = execute_query(FILTER_AUDIT, (action_filter, PAGE_SIZE, offset), fetch=True)
        total = execute_count(COUNT_FILTER_AUDIT, (action_filter,))
    else:
        # Unfiltered — all audit logs
        rows = execute_query(SELECT_AUDIT, (PAGE_SIZE, offset), fetch=True)
        total = execute_count(COUNT_AUDIT)
    total_pages = math.ceil(total / PAGE_SIZE) if total > 0 else 1
    return rows, total_pages


def get_all_audit_logs() -> list[dict]:
    """Fetch ALL audit logs without pagination.

    Returns:
        List of all audit log rows from the database.
    """
    return execute_query(SELECT_ALL_AUDIT, fetch=True)
