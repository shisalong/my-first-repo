"""
queries.py — SQL Query Constants
=================================
PURPOSE:
    Stores ALL SQL queries used by the application as named string constants.
    No SQL is written anywhere else in the codebase — it's all centralized here.

WHY CENTRALIZE QUERIES?
    1. Easy to find and modify any query in one place
    2. Prevents duplicate/inconsistent SQL scattered across files
    3. Makes code review easier — all DB interactions are visible here
    4. Services just import the constant they need: from app.db.queries import INSERT_PASSWORD

PARAMETERIZED QUERIES:
    All queries use %s placeholders instead of string formatting.
    The actual values are passed separately via execute_query(query, params).
    This prevents SQL injection attacks (see connection.py for details).

NAMING CONVENTION:
    - GET_*    = SELECT a single record
    - SELECT_* = SELECT multiple records (with pagination)
    - COUNT_*  = COUNT queries for pagination math
    - INSERT_* = INSERT new records
    - UPDATE_* = UPDATE existing records
    - DELETE_* = DELETE records
    - FILTER_* = SELECT with a WHERE filter
"""

# =============================================================================
# ADMIN USER QUERIES
# Used by: auth_service.py, create_admin.py
# =============================================================================

# Fetch an admin user by username (for login authentication)
# Returns all columns so we can check password_hash and totp_secret
GET_ADMIN = "SELECT * FROM admin_users WHERE username = %s"

# Create a new admin user (used by create_admin.py CLI script)
# Parameters: (username, bcrypt_hashed_password, totp_secret_or_null)
INSERT_ADMIN = """
    INSERT INTO admin_users (username, password_hash, totp_secret)
    VALUES (%s, %s, %s)
"""

# Update the TOTP secret for an existing admin (for MFA re-enrollment)
# Parameters: (new_totp_secret, admin_id)
UPDATE_TOTP_SECRET = "UPDATE admin_users SET totp_secret = %s WHERE id = %s"

# =============================================================================
# PASSWORD CRUD QUERIES
# Used by: password_service.py
# =============================================================================

# Store a new encrypted password
# Parameters: (site_name, username, fernet_encrypted_password)
INSERT_PASSWORD = """
    INSERT INTO passwords (site_name, username, encrypted_password)
    VALUES (%s, %s, %s)
"""

# Fetch passwords with pagination (newest first)
# LIMIT = how many rows to return (PAGE_SIZE from .env)
# OFFSET = how many rows to skip (calculated as (page - 1) * PAGE_SIZE)
# Parameters: (limit, offset)
# Example: Page 1 with PAGE_SIZE=10 → LIMIT 10 OFFSET 0
#          Page 2 with PAGE_SIZE=10 → LIMIT 10 OFFSET 10
SELECT_PASSWORDS = """
    SELECT id, site_name, username, encrypted_password, created_at
    FROM passwords ORDER BY created_at DESC LIMIT %s OFFSET %s
"""

# Count total passwords (for calculating total_pages in pagination)
# total_pages = ceil(total_count / PAGE_SIZE)
COUNT_PASSWORDS = "SELECT COUNT(*) FROM passwords"

# Search passwords by site_name OR username using LIKE pattern matching
# LIKE '%gmail%' matches any string containing "gmail" (case-insensitive in MySQL)
# Parameters: (search_pattern, search_pattern, limit, offset)
SEARCH_PASSWORDS = """
    SELECT id, site_name, username, encrypted_password, created_at
    FROM passwords WHERE site_name LIKE %s OR username LIKE %s
    ORDER BY created_at DESC LIMIT %s OFFSET %s
"""

# Count search results for pagination
# Parameters: (search_pattern, search_pattern)
COUNT_SEARCH_PASSWORDS = """
    SELECT COUNT(*) FROM passwords WHERE site_name LIKE %s OR username LIKE %s
"""

# Delete a single password by its ID
# Parameters: (password_id,)
DELETE_PASSWORD = "DELETE FROM passwords WHERE id = %s"

# Fetch a single password by ID (used to verify it exists before deleting)
# Parameters: (password_id,)
GET_PASSWORD_BY_ID = "SELECT * FROM passwords WHERE id = %s"

# Fetch ALL passwords without pagination (used for data export)
SELECT_ALL_PASSWORDS = """
    SELECT id, site_name, username, encrypted_password, created_at FROM passwords
    ORDER BY created_at DESC
"""

# =============================================================================
# AUDIT LOG QUERIES
# Used by: audit_service.py
# =============================================================================

# Record a new audit log entry
# Parameters: (action_type, details_text, admin_username)
INSERT_AUDIT = """
    INSERT INTO audit_log (action, details, performed_by)
    VALUES (%s, %s, %s)
"""

# Fetch audit logs with pagination (newest first)
# Parameters: (limit, offset)
SELECT_AUDIT = """
    SELECT id, action, details, performed_by, performed_at
    FROM audit_log ORDER BY performed_at DESC LIMIT %s OFFSET %s
"""

# Count total audit log entries
COUNT_AUDIT = "SELECT COUNT(*) FROM audit_log"

# Fetch audit logs filtered by action type (e.g., only "LOGIN" events)
# Parameters: (action_type, limit, offset)
FILTER_AUDIT = """
    SELECT id, action, details, performed_by, performed_at
    FROM audit_log WHERE action = %s ORDER BY performed_at DESC LIMIT %s OFFSET %s
"""

# Count filtered audit logs
# Parameters: (action_type,)
COUNT_FILTER_AUDIT = "SELECT COUNT(*) FROM audit_log WHERE action = %s"

# Fetch ALL audit logs without pagination (for potential future export)
SELECT_ALL_AUDIT = """
    SELECT id, action, details, performed_by, performed_at FROM audit_log
    ORDER BY performed_at DESC
"""
