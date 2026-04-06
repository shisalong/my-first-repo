"""
connection.py — MySQL Database Connection Layer
================================================
PURPOSE:
    Manages all database connectivity using a CONNECTION POOL pattern.
    Provides two reusable functions that the entire app uses to talk to MySQL:
    - execute_query(): For INSERT, UPDATE, DELETE, and SELECT queries
    - execute_count(): For COUNT(*) queries (used in pagination)

WHAT IS A CONNECTION POOL?
    Instead of opening a new MySQL connection every time we need to run a query
    (which is slow), we create a "pool" of 5 connections at startup. When a
    function needs a connection, it borrows one from the pool, uses it, and
    returns it. This is much faster and more efficient.

    Think of it like a library: instead of buying a new book every time you
    want to read, you borrow one from the library and return it when done.

ARCHITECTURE:
    All other modules (services, GUI) call execute_query() or execute_count().
    They never create connections directly. This centralizes all DB logic here,
    making it easy to change the database configuration in one place.

FLOW:
    Service/GUI → execute_query() → get_connection() → get_pool() → MySQL
"""

from mysql.connector import Error, pooling

from app.utils.constants import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER
from app.utils.helpers import setup_logger

logger = setup_logger(__name__)

# Module-level variable to hold the single connection pool instance.
# Using a global + None check is the SINGLETON pattern — ensures only
# one pool is ever created, no matter how many times get_pool() is called.
_pool = None


def get_pool() -> pooling.MySQLConnectionPool:
    """Get or create the MySQL connection pool (Singleton pattern).

    The pool is created on first call and reused for all subsequent calls.
    Pool size of 5 means up to 5 simultaneous database operations can happen.

    Returns:
        MySQLConnectionPool instance.

    Raises:
        mysql.connector.Error: If MySQL is not running or credentials are wrong.
    """
    global _pool
    if _pool is None:
        try:
            _pool = pooling.MySQLConnectionPool(
                pool_name="pwd_pool",  # Name for identification in logs
                pool_size=5,  # Max 5 concurrent connections
                host=DB_HOST,  # From .env: localhost
                port=DB_PORT,  # From .env: 3306
                database=DB_NAME,  # From .env: password_protect_db
                user=DB_USER,  # From .env: admin
                password=DB_PASSWORD,  # From .env: admin123**
            )
            logger.info("Database connection pool created.")
        except Error as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    return _pool


def get_connection():
    """Borrow a connection from the pool.

    Returns:
        A MySQL connection object. MUST be closed after use (returned to pool).
        Closing a pooled connection doesn't actually disconnect — it returns
        the connection back to the pool for reuse.
    """
    return get_pool().get_connection()


def execute_query(query: str, params: tuple = None, fetch: bool = False):
    """Execute a SQL query with automatic connection management.

    This is the MAIN function used by all services to interact with the database.
    It handles:
    - Borrowing a connection from the pool
    - Executing the query with parameterized values (prevents SQL injection)
    - Committing changes for INSERT/UPDATE/DELETE
    - Fetching results for SELECT queries
    - Rolling back on errors
    - Always returning the connection to the pool (via finally block)

    WHAT IS SQL INJECTION?
        If you build queries with string concatenation like:
            f"SELECT * FROM users WHERE name = '{user_input}'"
        An attacker could input: ' OR '1'='1
        This would return ALL users! Parameterized queries (%s placeholders)
        prevent this by treating user input as data, never as SQL code.

    Args:
        query:  SQL query string with %s placeholders for parameters.
        params: Tuple of values to substitute into the %s placeholders.
        fetch:  If True, return SELECT results. If False, commit and return lastrowid.

    Returns:
        If fetch=True:  List of dicts (each dict = one row, keys = column names)
        If fetch=False: The auto-generated ID of the last inserted row (lastrowid)

    Raises:
        mysql.connector.Error: On any database error (logged before re-raising).

    Examples:
        # INSERT (fetch=False, returns new row ID)
        new_id = execute_query("INSERT INTO passwords (site) VALUES (%s)", ("Gmail",))

        # SELECT (fetch=True, returns list of dicts)
        rows = execute_query("SELECT * FROM passwords WHERE id = %s", (1,), fetch=True)
        # rows = [{"id": 1, "site_name": "Gmail", "username": "user@gmail.com", ...}]
    """
    conn = None
    try:
        conn = get_connection()
        # dictionary=True makes fetchall() return dicts instead of tuples
        # So instead of (1, "Gmail", "user"), you get {"id": 1, "site_name": "Gmail", ...}
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        if fetch:
            result = cursor.fetchall()
            return result
        # For INSERT/UPDATE/DELETE, we must commit to save changes
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        logger.error(f"Query error: {e} | Query: {query}")
        # Rollback undoes any partial changes if the query failed mid-way
        if conn:
            conn.rollback()
        raise
    finally:
        # The finally block ALWAYS runs, even if an exception occurred.
        # This ensures the connection is always returned to the pool.
        if conn:
            conn.close()


def execute_count(query: str, params: tuple = None) -> int:
    """Execute a COUNT(*) query and return the integer result.

    This is a specialized helper for pagination. COUNT queries return a single
    row with a single column (the count), so we extract just that number.

    Args:
        query:  A SQL query like "SELECT COUNT(*) FROM passwords"
        params: Optional tuple of parameters for WHERE clauses.

    Returns:
        Integer count of matching rows.

    Example:
        total = execute_count("SELECT COUNT(*) FROM passwords")
        # total = 42
    """
    conn = None
    try:
        conn = get_connection()
        # No dictionary=True here — we just need the raw number
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        # result is a tuple like (42,), so result[0] gives us 42
        return result[0] if result else 0
    except Error as e:
        logger.error(f"Count query error: {e}")
        raise
    finally:
        if conn:
            conn.close()
