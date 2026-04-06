# Password Protect

Secure password manager built with Python, Tkinter, and MySQL 8.1.

## Features

- Admin login with TOTP-based MFA (Google Authenticator / Microsoft Authenticator)
- Add, view, and delete stored passwords with pagination
- AES-256 encryption (Fernet) for all stored passwords
- Audit logging for all actions (login, CRUD, export)
- Export to CSV, JSON, or encrypted file
- Configurable via `.env` file
- Cross-platform: Windows and macOS (M4)

## Prerequisites

- Python 3.11+
- MySQL 8.1
- [uv](https://docs.astral.sh/uv/) package manager

## Setup

### 1. Clone and install dependencies

```bash
git clone https://gitlab.com/7000015136/py-pwd-protect.git
cd py-pwd-protect
uv sync
```

### 2. Create the database

Run the SQL setup script as MySQL root:

**Windows:**
```bash
mysql -u root -p < setup_db.sql
```

**macOS:**
```bash
mysql -u root -p < setup_db.sql
```

If MySQL is not running, start it first:
- Windows: `net start mysql81` (or via Services app)
- macOS: `brew services start mysql`

This creates:
- Database: `password_protect_db`
- User: `admin`@`localhost` with password `admin123**`
- Tables: `admin_users`, `passwords`, `audit_log`

### 3. Configure environment

The `.env` file is included in the repository with working defaults.
Edit it if your MySQL setup differs:

Key settings:
- `MFA_ENABLED` — Enable/disable TOTP MFA (`true`/`false`)
- `PAGE_SIZE` — Records per page (default: 10)
- `DB_*` — Database connection settings

### 4. Create admin user

```bash
uv run python create_admin.py
```

Follow the prompts to set username, password, and scan the MFA QR code.

**Full interactive session:**

```
=== Password Protect - Admin Setup ===

Enter admin username: admin
Enter admin password: ********
Confirm password: ********

--- MFA Setup ---
TOTP Secret: JBSWY3DPEHPK3PXP
Provisioning URI: otpauth://totp/PasswordProtect:admin?secret=JBSWY3DP...
Scan the QR code below with your authenticator app:

  (ASCII QR code appears here)

Enter the 6-digit code from your authenticator to verify: 482901
MFA verified successfully!

Admin user 'admin' created successfully!
```

**Notes:**
- Password input is hidden (no characters shown while typing)
- If `MFA_ENABLED=false` in `.env`, the MFA setup steps are skipped
- The QR code can be scanned with Google Authenticator or Microsoft Authenticator
- You can also manually enter the TOTP Secret into your authenticator app

### 5. Run the app

```bash
uv run python main.py
```

## Project Structure

```
py-pwd-protect/
├── main.py                 # App entry point
├── create_admin.py         # CLI admin setup
├── decrypt_export.py       # CLI decrypt exported .enc files
├── setup_db.sql            # Database setup script
├── .env                    # Configuration
├── app/
│   ├── gui/                # Tkinter pages
│   │   ├── login_page.py
│   │   ├── mfa_page.py
│   │   ├── dashboard.py
│   │   ├── add_password.py
│   │   ├── view_passwords.py
│   │   ├── delete_passwords.py
│   │   ├── audit_page.py
│   │   └── export_page.py
│   ├── db/                 # Database layer
│   │   ├── connection.py
│   │   └── queries.py
│   ├── services/           # Business logic
│   │   ├── auth_service.py
│   │   ├── crypto_service.py
│   │   ├── password_service.py
│   │   ├── audit_service.py
│   │   └── export_service.py
│   └── utils/              # Helpers & constants
│       ├── constants.py
│       └── helpers.py
└── logs/                   # Daily rolling logs
```

## Decrypt Exported Files

To decrypt a `.enc` file exported from the app:

```bash
uv run python decrypt_export.py
```

The script will prompt you interactively:

```
=== Password Protect — Decrypt Exported File ===

Path to .enc file: C:\Users\Documents\passwords_export.enc
Export password: ********

Decrypted 3 password(s):

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

Save to file? (y/n): y
Output file path (e.g., decrypted.json): decrypted.json
Saved to decrypted.json
```

**How to provide the file path:**
- Type the full path: `C:\Users\Documents\export.enc`
- Or drag and drop the `.enc` file into the terminal (auto-pastes the path)
- Paths with spaces work as-is, surrounding quotes are stripped automatically

**You will need:**
- The `.enc` file path
- The export password you used during export
- The `.salt` file from the project root (must be the same one from when the export was created)

## Password Standards

- 8-64 characters
- At least 1 uppercase, 1 lowercase, 1 digit, 1 special character
- No spaces

## License

MIT
