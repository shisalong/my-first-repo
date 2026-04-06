"""
login_page.py — Admin Login Page
==================================
PURPOSE:
    The first page the user sees. Provides username/password authentication.
    On successful login, initializes the encryption engine and routes to
    either the MFA page (if enabled) or directly to the Dashboard.

UI LAYOUT:
    ┌─────────────────────────────────────┐
    │         Password Protect            │
    │           Admin Login               │
    │                                     │
    │  Username: [___________________]    │
    │  Password: [___________________]    │
    │  ☐ Show password                    │
    │                                     │
    │  (error message in red)             │
    │         [ Login ]                   │
    └─────────────────────────────────────┘

FLOW:
    1. User enters username + password
    2. _login() validates inputs are not empty
    3. Calls auth_service.authenticate() to check credentials against DB
    4. If valid → init_crypto(password) to set up the encryption engine
    5. If MFA enabled → navigate to MfaPage
    6. If MFA disabled → navigate to Dashboard

KEY CONCEPT — init_crypto():
    The admin's login password is ALSO used to derive the encryption key
    for all stored passwords. This means:
    - No separate "master key" to manage
    - The encryption key only exists in memory while the app is running
    - Logging out effectively destroys the key
"""

import tkinter as tk
from tkinter import messagebox, ttk

from app.services.audit_service import log_action
from app.services.auth_service import authenticate, is_mfa_enabled
from app.services.crypto_service import init_crypto
from app.utils.helpers import setup_logger

logger = setup_logger(__name__)


class LoginPage(ttk.Frame):
    """Login page frame with username/password form.

    Args:
        parent:     The container frame from main.py (self.container).
        controller: The App instance from main.py (for navigation and state).
    """

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._build_ui()

    def _build_ui(self):
        """Build the login form UI elements.

        Uses place(relx=0.5, rely=0.5, anchor="center") to center the form
        both horizontally and vertically in the window, regardless of window size.
        """
        # Wrapper frame centered in the page
        wrapper = ttk.Frame(self)
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        # Title and subtitle
        ttk.Label(wrapper, text="Password Protect", font=("Helvetica", 20, "bold")).pack(pady=(0, 20))
        ttk.Label(wrapper, text="Admin Login", font=("Helvetica", 14)).pack(pady=(0, 15))

        # Username field
        ttk.Label(wrapper, text="Username").pack(anchor="w")
        self.username_var = tk.StringVar()  # StringVar links the Entry widget to a variable
        self.username_entry = ttk.Entry(wrapper, textvariable=self.username_var, width=35)
        self.username_entry.pack(pady=(0, 10))

        # Password field (show="*" masks the input)
        ttk.Label(wrapper, text="Password").pack(anchor="w")
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(wrapper, textvariable=self.password_var, width=35, show="*")
        self.password_entry.pack(pady=(0, 5))

        # Show/hide password toggle checkbox
        self.show_pwd_var = tk.BooleanVar()
        ttk.Checkbutton(wrapper, text="Show password", variable=self.show_pwd_var, command=self._toggle_password).pack(
            anchor="w", pady=(0, 15)
        )

        # Error message label (hidden until an error occurs)
        self.error_label = ttk.Label(wrapper, text="", foreground="red")
        self.error_label.pack()

        # Login button
        ttk.Button(wrapper, text="Login", command=self._login).pack(pady=10, ipadx=20)

        # Pressing Enter in the password field triggers login
        self.password_entry.bind("<Return>", lambda e: self._login())

    def _toggle_password(self):
        """Toggle password visibility based on the checkbox state."""
        self.password_entry.config(show="" if self.show_pwd_var.get() else "*")

    def _login(self):
        """Handle the login button click.

        Steps:
            1. Clear any previous error message
            2. Validate that both fields are filled
            3. Call authenticate() to verify credentials against DB
            4. On failure: show error + log the failed attempt
            5. On success: init crypto engine, log success, navigate forward
        """
        self.error_label.config(text="")
        username = self.username_var.get().strip()
        password = self.password_var.get()

        # Basic empty-field validation
        if not username or not password:
            self.error_label.config(text="Username and password are required.")
            return

        # Authenticate against the database
        try:
            user = authenticate(username, password)
        except Exception as e:
            logger.error(f"Login error: {e}")
            messagebox.showerror("Error", f"Database error: {e}")
            return

        if user is None:
            # Authentication failed — show error and log the attempt
            self.error_label.config(text="Invalid username or password.")
            log_action("LOGIN_FAILED", f"Failed login for '{username}'", username)
            return

        # Authentication successful!
        # Initialize the encryption engine with the admin's password
        # This derives the Fernet key used to encrypt/decrypt stored passwords
        init_crypto(password)
        self.controller.set_user(user)
        log_action("LOGIN", f"User '{username}' logged in.", username)

        # Route to MFA page if enabled AND user has a TOTP secret configured
        if is_mfa_enabled() and user.get("totp_secret"):
            self.controller.show_frame("MfaPage", user=user)
        else:
            self.controller.show_frame("Dashboard")

    def on_show(self, **kwargs):
        """Called when navigating TO this page. Resets the form fields."""
        self.username_var.set("")
        self.password_var.set("")
        self.error_label.config(text="")
        self.username_entry.focus()  # Auto-focus the username field
