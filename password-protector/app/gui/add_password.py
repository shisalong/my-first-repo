"""
add_password.py — Add New Password Page
=========================================
PURPOSE:
    Form page for storing a new site credential. Validates all inputs against
    the configured password standards before encrypting and saving to the DB.

UI LAYOUT:
    ┌──────────────────────────────────────────────────────────────┐
    │  Add Password                              [← Dashboard]    │
    │  ──────────────────────────────────────────────────────────  │
    │                                                              │
    │  Site Name: [___________________]   ┌─ Password Standards ─┐│
    │  Username:  [___________________]   │ • 8-64 characters    ││
    │  Password:  [___________________]   │ • No spaces          ││
    │  ☐ Show password                    │ • 1 uppercase (A-Z)  ││
    │  Confirm:   [___________________]   │ • 1 lowercase (a-z)  ││
    │                                     │ • 1 digit (0-9)      ││
    │  (error in red / success in green)  │ • 1 special char     ││
    │       [ Save Password ]             └──────────────────────┘│
    └──────────────────────────────────────────────────────────────┘

VALIDATION CHAIN (all must pass before saving):
    1. Site name: not empty, max 255 chars
    2. Username: 3-30 chars, alphanumeric + underscore only
    3. Password: meets all standards from .env config
    4. Confirm password: must match password field

    If ANY validation fails, the error is shown in red and the save is blocked.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from app.services.audit_service import log_action
from app.services.password_service import add_password
from app.utils.helpers import (
    get_password_standards_text,
    setup_logger,
    validate_password,
    validate_site_name,
    validate_username,
)

logger = setup_logger(__name__)


class AddPasswordPage(ttk.Frame):
    """Page with a form to add a new encrypted password to the database."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._build_ui()

    def _build_ui(self):
        """Build the form layout with input fields and password standards panel."""
        # Header with title and back button
        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=(15, 5))
        ttk.Label(header, text="Add Password", font=("Helvetica", 16, "bold")).pack(side="left")
        ttk.Button(header, text="← Dashboard", command=lambda: self.controller.show_frame("Dashboard")).pack(
            side="right"
        )

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=5)

        # Content area: form on the left, standards panel on the right
        content = ttk.Frame(self)
        content.pack(expand=True, padx=40)

        # --- LEFT SIDE: Input form ---
        form = ttk.Frame(content)
        form.pack(side="left", padx=(0, 30))

        # Site Name field
        ttk.Label(form, text="Site Name").pack(anchor="w", pady=(10, 0))
        self.site_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.site_var, width=35).pack()

        # Username field
        ttk.Label(form, text="Username").pack(anchor="w", pady=(10, 0))
        self.user_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.user_var, width=35).pack()

        # Password field (masked with *)
        ttk.Label(form, text="Password").pack(anchor="w", pady=(10, 0))
        self.pwd_var = tk.StringVar()
        self.pwd_entry = ttk.Entry(form, textvariable=self.pwd_var, width=35, show="*")
        self.pwd_entry.pack()

        # Show/hide toggle for both password fields
        self.show_pwd_var = tk.BooleanVar()
        ttk.Checkbutton(form, text="Show password", variable=self.show_pwd_var, command=self._toggle_pwd).pack(
            anchor="w"
        )

        # Confirm Password field
        ttk.Label(form, text="Confirm Password").pack(anchor="w", pady=(10, 0))
        self.confirm_var = tk.StringVar()
        self.confirm_entry = ttk.Entry(form, textvariable=self.confirm_var, width=35, show="*")
        self.confirm_entry.pack()

        # Error and success message labels
        self.error_label = ttk.Label(form, text="", foreground="red", wraplength=300)
        self.error_label.pack(pady=5)
        self.success_label = ttk.Label(form, text="", foreground="green")
        self.success_label.pack()

        ttk.Button(form, text="Save Password", command=self._save).pack(pady=10, ipadx=15)

        # --- RIGHT SIDE: Password standards info panel ---
        # Dynamically generated from .env config via get_password_standards_text()
        standards = ttk.LabelFrame(content, text="Password Standards", padding=10)
        standards.pack(side="left", anchor="n", pady=10)
        ttk.Label(standards, text=get_password_standards_text(), justify="left", font=("Helvetica", 10)).pack()

    def _toggle_pwd(self):
        """Toggle visibility of both password and confirm fields."""
        show = "" if self.show_pwd_var.get() else "*"
        self.pwd_entry.config(show=show)
        self.confirm_entry.config(show=show)

    def _save(self):
        """Validate all fields and save the encrypted password to the database.

        Validation order: site → username → password standards → password match.
        Stops at the first failure and shows the error message.
        """
        self.error_label.config(text="")
        self.success_label.config(text="")

        site = self.site_var.get().strip()
        username = self.user_var.get().strip()
        password = self.pwd_var.get()
        confirm = self.confirm_var.get()

        # Validate each field in sequence
        ok, msg = validate_site_name(site)
        if not ok:
            self.error_label.config(text=msg)
            return

        ok, msg = validate_username(username)
        if not ok:
            self.error_label.config(text=msg)
            return

        ok, errors = validate_password(password)
        if not ok:
            self.error_label.config(text="\n".join(errors))
            return

        if password != confirm:
            self.error_label.config(text="Passwords do not match.")
            return

        # All validations passed — encrypt and save
        try:
            add_password(site, username, password)
            admin = self.controller.current_user["username"]
            log_action("ADD_PASSWORD", f"Added password for site '{site}', user '{username}'.", admin)
            self.success_label.config(text="Password saved successfully!")
            # Clear form fields for next entry
            self.site_var.set("")
            self.user_var.set("")
            self.pwd_var.set("")
            self.confirm_var.set("")
        except Exception as e:
            logger.error(f"Add password error: {e}")
            messagebox.showerror("Error", f"Failed to save: {e}")

    def on_show(self, **kwargs):
        """Reset error/success messages when navigating to this page."""
        self.error_label.config(text="")
        self.success_label.config(text="")
