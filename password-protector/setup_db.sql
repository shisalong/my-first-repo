-- =============================================================================
-- FILE: setup_db.sql
-- PURPOSE: Creates the MySQL database, application user, and all required
--          tables for the Password Protect application.
--
-- HOW TO RUN:
--   mysql -u root -p < setup_db.sql
--
-- WHAT THIS SCRIPT DOES:
--   1. Creates a new database called 'password_protect_db'
--   2. Creates a MySQL user 'admin' with password 'admin123**'
--   3. Grants that user full access to the database
--   4. Creates three tables: admin_users, passwords, audit_log
--
-- IMPORTANT:
--   - You must run this as the MySQL root user (or a user with CREATE privileges)
--   - This script is idempotent (safe to run multiple times) due to IF NOT EXISTS
--   - Works on both Windows and macOS (MySQL 8.1)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- STEP 1: Create the database
-- CHARACTER SET utf8mb4 = supports emojis and all international characters
-- COLLATE utf8mb4_unicode_ci = case-insensitive comparison for text
-- -----------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS password_protect_db
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- STEP 2: Create the application-level MySQL user
-- This is the user the Python app uses to connect to MySQL.
-- 'admin'@'localhost' means this user can ONLY connect from the same machine.
-- This is a security best practice — no remote connections allowed.
-- -----------------------------------------------------------------------------
CREATE USER IF NOT EXISTS 'pwd_protect'@'localhost' IDENTIFIED BY 'admin123**';

-- Grant all privileges on our specific database only (not all databases)
GRANT ALL PRIVILEGES ON password_protect_db.* TO 'pwd_protect'@'localhost';

-- FLUSH PRIVILEGES tells MySQL to reload the grant tables so changes take effect
FLUSH PRIVILEGES;

-- Switch to our database for the table creation statements below
USE password_protect_db;

-- -----------------------------------------------------------------------------
-- STEP 3: Create the 'admin_users' table
-- PURPOSE: Stores the admin user account that logs into the Tkinter app.
--
-- COLUMNS:
--   id             - Auto-incrementing primary key (unique identifier)
--   username       - The admin's login name (max 30 chars, must be unique)
--   password_hash  - The bcrypt-hashed password (NEVER store plain text passwords!)
--   totp_secret    - The TOTP secret key for MFA (used by Google Authenticator)
--                    NULL if MFA is disabled
--   created_at     - Timestamp of when the admin was created (auto-filled by MySQL)
--
-- WHY bcrypt?
--   bcrypt is a one-way hashing algorithm designed for passwords. Even if someone
--   steals the database, they cannot reverse the hash to get the original password.
--
-- WHY TOTP?
--   TOTP (Time-based One-Time Password) adds a second factor of authentication.
--   The user must provide both their password AND a 6-digit code from their phone.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(30) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    totp_secret VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- STEP 4: Create the 'passwords' table
-- PURPOSE: Stores the encrypted credentials that the admin manages.
--
-- COLUMNS:
--   id                  - Auto-incrementing primary key
--   site_name           - The website or service name (e.g., "Gmail", "GitHub")
--   username            - The username/email for that site
--   encrypted_password  - The Fernet-encrypted password (NOT plain text!)
--   created_at          - When this record was added
--
-- SECURITY NOTE:
--   The 'encrypted_password' column stores Fernet-encrypted ciphertext.
--   Fernet uses AES-128-CBC encryption with HMAC-SHA256 for authentication.
--   The encryption key is derived from the admin's master password using PBKDF2.
--   Even if the database is compromised, passwords cannot be read without the key.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS passwords (
    id INT AUTO_INCREMENT PRIMARY KEY,
    site_name VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    encrypted_password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- STEP 5: Create the 'audit_log' table
-- PURPOSE: Records every action performed in the application for accountability.
--
-- COLUMNS:
--   id           - Auto-incrementing primary key
--   action       - The type of action (e.g., "LOGIN", "ADD_PASSWORD", "EXPORT")
--   details      - Human-readable description of what happened
--   performed_by - Which admin user performed the action
--   performed_at - When the action occurred (auto-filled by MySQL)
--
-- WHY AUDIT LOGGING?
--   Audit logs are essential for security. They let you:
--   - Track who did what and when
--   - Detect unauthorized access attempts (failed logins)
--   - Comply with security policies
--   - Debug issues by reviewing the history of actions
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action VARCHAR(50) NOT NULL,
    details TEXT,
    performed_by VARCHAR(30) NOT NULL,
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
