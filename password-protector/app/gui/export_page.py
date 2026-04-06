"""
export_page.py — Data Export Page
===================================
PURPOSE:
    Allows the admin to export all stored passwords to external files.
    Three export formats are supported:
    1. CSV  — Plain text, opens in Excel/Sheets (⚠️ contains plain passwords)
    2. JSON — Plain text, structured format (⚠️ contains plain passwords)
    3. Encrypted — Binary file protected with a password (✅ secure)

UI LAYOUT:
    ┌──────────────────────────────────────────────────────────────┐
    │  Export Data                                [← Dashboard]    │
    │  ──────────────────────────────────────────────────────────  │
    │                                                              │
    │  ┌─ Export as CSV ─────────────────────────────────────────┐ │
    │  │ Exports all passwords in plain CSV format.              │ │
    │  │                                        [Export CSV]     │ │
    │  └─────────────────────────────────────────────────────────┘ │
    │                                                              │
    │  ┌─ Export as JSON ────────────────────────────────────────┐ │
    │  │ Exports all passwords in plain JSON format.             │ │
    │  │                                        [Export JSON]    │ │
    │  └─────────────────────────────────────────────────────────┘ │
    │                                                              │
    │  ┌─ Export Encrypted ──────────────────────────────────────┐ │
    │  │ Exports all passwords encrypted with a password.        │ │
    │  │ Export Password: [**************]                        │ │
    │  │                                   [Export Encrypted]    │ │
    │  └─────────────────────────────────────────────────────────┘ │
    │                                                              │
    │  CSV exported to /path/to/passwords.csv                     │
    └──────────────────────────────────────────────────────────────┘

FILE DIALOG:
    Each export button opens a native OS "Save As" dialog (filedialog.asksaveasfilename).
    The admin chooses where to save the file. If they cancel, nothing happens.

ENCRYPTED EXPORT:
    The export password is validated against the same password standards as
    regular passwords. This ensures the export file is protected with a strong key.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.services.audit_service import log_action
from app.services.export_service import export_csv, export_encrypted, export_json
from app.utils.helpers import setup_logger, validate_password

logger = setup_logger(__name__)


class ExportPage(ttk.Frame):
    """Export page with CSV, JSON, and encrypted export options."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._build_ui()

    def _build_ui(self):
        """Build the three export option panels."""
        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=(15, 5))
        ttk.Label(header, text="Export Data", font=("Helvetica", 16, "bold")).pack(side="left")
        ttk.Button(header, text="← Dashboard", command=lambda: self.controller.show_frame("Dashboard")).pack(
            side="right"
        )

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=5)

        wrapper = ttk.Frame(self)
        wrapper.pack(expand=True)

        # --- CSV Export Panel ---
        csv_frame = ttk.LabelFrame(wrapper, text="Export as CSV", padding=15)
        csv_frame.pack(fill="x", pady=10, padx=20)
        ttk.Label(csv_frame, text="Exports all passwords in plain CSV format.").pack(anchor="w")
        ttk.Button(csv_frame, text="Export CSV", command=self._export_csv).pack(anchor="e", pady=5)

        # --- JSON Export Panel ---
        json_frame = ttk.LabelFrame(wrapper, text="Export as JSON", padding=15)
        json_frame.pack(fill="x", pady=10, padx=20)
        ttk.Label(json_frame, text="Exports all passwords in plain JSON format.").pack(anchor="w")
        ttk.Button(json_frame, text="Export JSON", command=self._export_json).pack(anchor="e", pady=5)

        # --- Encrypted Export Panel ---
        enc_frame = ttk.LabelFrame(wrapper, text="Export Encrypted", padding=15)
        enc_frame.pack(fill="x", pady=10, padx=20)
        ttk.Label(enc_frame, text="Exports all passwords encrypted with a password you provide.").pack(anchor="w")
        # Password input for encrypted export
        pwd_row = ttk.Frame(enc_frame)
        pwd_row.pack(fill="x", pady=5)
        ttk.Label(pwd_row, text="Export Password:").pack(side="left")
        self.enc_pwd_var = tk.StringVar()
        ttk.Entry(pwd_row, textvariable=self.enc_pwd_var, width=30, show="*").pack(side="left", padx=5)
        ttk.Button(enc_frame, text="Export Encrypted", command=self._export_encrypted).pack(anchor="e", pady=5)

        # Status message (shows success after export)
        self.status_label = ttk.Label(wrapper, text="", foreground="green", font=("Helvetica", 10))
        self.status_label.pack(pady=10)

    def _export_csv(self):
        """Open a Save As dialog and export passwords to CSV."""
        # filedialog returns the chosen path, or empty string if cancelled
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return  # User cancelled
        try:
            export_csv(path)
            self._log_export("CSV", path)
            self.status_label.config(text=f"CSV exported to {path}")
        except Exception as e:
            logger.error(f"CSV export error: {e}")
            messagebox.showerror("Error", f"Export failed: {e}")

    def _export_json(self):
        """Open a Save As dialog and export passwords to JSON."""
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            export_json(path)
            self._log_export("JSON", path)
            self.status_label.config(text=f"JSON exported to {path}")
        except Exception as e:
            logger.error(f"JSON export error: {e}")
            messagebox.showerror("Error", f"Export failed: {e}")

    def _export_encrypted(self):
        """Validate the export password, then export to an encrypted file.

        The export password must meet the same standards as regular passwords.
        This prevents weak encryption on the exported file.
        """
        pwd = self.enc_pwd_var.get()
        ok, errors = validate_password(pwd)
        if not ok:
            messagebox.showwarning("Weak Password", "\n".join(errors))
            return
        path = filedialog.asksaveasfilename(defaultextension=".enc", filetypes=[("Encrypted", "*.enc")])
        if not path:
            return
        try:
            export_encrypted(path, pwd)
            self._log_export("ENCRYPTED", path)
            self.status_label.config(text=f"Encrypted file exported to {path}")
            self.enc_pwd_var.set("")  # Clear the password field after export
        except Exception as e:
            logger.error(f"Encrypted export error: {e}")
            messagebox.showerror("Error", f"Export failed: {e}")

    def _log_export(self, fmt: str, path: str):
        """Log the export action to the audit trail."""
        admin = self.controller.current_user["username"]
        log_action("EXPORT", f"Exported data as {fmt} to {path}.", admin)

    def on_show(self, **kwargs):
        """Reset status message and password field when navigating here."""
        self.status_label.config(text="")
        self.enc_pwd_var.set("")
