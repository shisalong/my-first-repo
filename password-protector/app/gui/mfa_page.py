"""
mfa_page.py — Multi-Factor Authentication Page
================================================
PURPOSE:
    Second step of authentication. After the admin enters correct username/password,
    they must enter a 6-digit TOTP code from their authenticator app.
    Only shown when MFA_ENABLED=true in .env AND the user has a totp_secret.

UI LAYOUT:
    ┌─────────────────────────────────────┐
    │       MFA Verification              │
    │  Enter the 6-digit code from your   │
    │  authenticator app                  │
    │                                     │
    │        [ 4 8 2 9 0 1 ]             │
    │                                     │
    │  (error message in red)             │
    │     [ Verify ]  [ Back ]            │
    └─────────────────────────────────────┘

HOW TOTP WORKS:
    Both the server and the authenticator app share the same secret key.
    Every 30 seconds, both independently generate the same 6-digit code
    using: HMAC-SHA1(secret, current_time / 30)
    The server verifies the user's code matches what it calculated.
    valid_window=1 also accepts the previous 30-second code (clock tolerance).
"""

import tkinter as tk
from tkinter import ttk

from app.services.audit_service import log_action
from app.services.auth_service import verify_totp
from app.utils.helpers import setup_logger

logger = setup_logger(__name__)


class MfaPage(ttk.Frame):
    """MFA verification page for TOTP code entry.

    Attributes:
        user: The authenticated admin's DB record (passed from LoginPage).
              Contains the totp_secret needed for verification.
    """

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.user = None  # Set by on_show() when navigating here
        self._build_ui()

    def _build_ui(self):
        """Build the MFA code entry form."""
        wrapper = ttk.Frame(self)
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(wrapper, text="MFA Verification", font=("Helvetica", 16, "bold")).pack(pady=(0, 15))
        ttk.Label(wrapper, text="Enter the 6-digit code from your authenticator app").pack(pady=(0, 10))

        # Large centered input for the 6-digit code
        self.code_var = tk.StringVar()
        self.code_entry = ttk.Entry(
            wrapper, textvariable=self.code_var, width=20, font=("Helvetica", 16), justify="center"
        )
        self.code_entry.pack(pady=(0, 10))

        self.error_label = ttk.Label(wrapper, text="", foreground="red")
        self.error_label.pack()

        # Verify and Back buttons side by side
        btn_frame = ttk.Frame(wrapper)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Verify", command=self._verify).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Back", command=self._back).pack(side="left", padx=5)

        # Enter key triggers verification
        self.code_entry.bind("<Return>", lambda e: self._verify())

    def _verify(self):
        """Validate the entered TOTP code.

        Checks:
            1. Code must be exactly 6 digits
            2. Code must match the TOTP generated from the user's secret
        """
        self.error_label.config(text="")
        code = self.code_var.get().strip()

        # Input validation: must be exactly 6 digits
        if not code or len(code) != 6 or not code.isdigit():
            self.error_label.config(text="Enter a valid 6-digit code.")
            return

        username = self.user["username"] if self.user else "unknown"

        # Verify the code against the stored TOTP secret
        if verify_totp(self.user["totp_secret"], code):
            log_action("MFA_VERIFIED", "MFA verification successful.", username)
            self.controller.show_frame("Dashboard")
        else:
            self.error_label.config(text="Invalid code. Try again.")
            log_action("MFA_FAILED", "MFA verification failed.", username)

    def _back(self):
        """Return to the login page (cancels MFA)."""
        self.controller.show_frame("LoginPage")

    def on_show(self, user=None, **kwargs):
        """Called when navigating to this page. Receives the user dict from LoginPage."""
        self.user = user or self.controller.current_user
        self.code_var.set("")
        self.error_label.config(text="")
        self.code_entry.focus()
