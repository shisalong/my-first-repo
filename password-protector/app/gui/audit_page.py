"""
audit_page.py — Audit Log Viewer Page (Paginated + Filterable)
===============================================================
PURPOSE:
    Displays the complete audit trail of all actions performed in the app.
    Supports pagination and filtering by action type (e.g., show only LOGIN events).

UI LAYOUT:
    ┌──────────────────────────────────────────────────────────────┐
    │  Audit Log                                 [← Dashboard]    │
    │  ──────────────────────────────────────────────────────────  │
    │  Filter by action: [ALL          ▼] [Apply]                 │
    │                                                              │
    │  ┌────┬───────────────┬────────────────┬───────┬──────────┐ │
    │  │ ID │ Action        │ Details        │ User  │ Timestamp│ │
    │  ├────┼───────────────┼────────────────┼───────┼──────────┤ │
    │  │ 5  │ ADD_PASSWORD  │ Added for Gmail│ admin │ 10:30:00 │ │
    │  │ 4  │ LOGIN         │ User logged in │ admin │ 10:29:00 │ │
    │  │ 3  │ LOGIN_FAILED  │ Wrong password │ admin │ 10:28:00 │ │
    │  └────┴───────────────┴────────────────┴───────┴──────────┘ │
    │                                                              │
    │        [◀ Prev]  Page 1 / 3  [Next ▶]                      │
    └──────────────────────────────────────────────────────────────┘

FILTER DROPDOWN:
    Uses ttk.Combobox with state="readonly" (user can only select, not type).
    Options: ALL, LOGIN, LOGIN_FAILED, MFA_VERIFIED, MFA_FAILED,
             ADD_PASSWORD, VIEW_PASSWORD, DELETE_PASSWORD, EXPORT
    "ALL" means no filter (show everything).
"""

import tkinter as tk
from tkinter import messagebox, ttk

from app.services.audit_service import ACTIONS, get_audit_logs
from app.utils.helpers import setup_logger

logger = setup_logger(__name__)


class AuditPage(ttk.Frame):
    """Paginated audit log viewer with action type filtering."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.current_page = 1
        self.total_pages = 1
        self.action_filter = None  # None = show all, "LOGIN" = show only logins
        self._build_ui()

    def _build_ui(self):
        """Build the filter bar, audit log table, and pagination controls."""
        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=(15, 5))
        ttk.Label(header, text="Audit Log", font=("Helvetica", 16, "bold")).pack(side="left")
        ttk.Button(header, text="← Dashboard", command=lambda: self.controller.show_frame("Dashboard")).pack(
            side="right"
        )

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=5)

        # Filter dropdown (Combobox)
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill="x", padx=20, pady=5)
        ttk.Label(filter_frame, text="Filter by action:").pack(side="left")
        self.filter_var = tk.StringVar(value="ALL")
        # state="readonly" prevents typing — user must select from the list
        combo = ttk.Combobox(
            filter_frame, textvariable=self.filter_var, values=["ALL"] + ACTIONS, state="readonly", width=20
        )
        combo.pack(side="left", padx=5)
        ttk.Button(filter_frame, text="Apply", command=self._apply_filter).pack(side="left", padx=5)

        # Audit log table
        cols = ("ID", "Action", "Details", "User", "Timestamp")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        for col in cols:
            self.tree.heading(col, text=col)
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Action", width=130)
        self.tree.column("Details", width=320)
        self.tree.column("User", width=100)
        self.tree.column("Timestamp", width=160)
        self.tree.pack(fill="both", expand=True, padx=20, pady=5)

        # Pagination
        pag_frame = ttk.Frame(self)
        pag_frame.pack(pady=5)
        ttk.Button(pag_frame, text="◀ Prev", command=self._prev).pack(side="left", padx=5)
        self.page_label = ttk.Label(pag_frame, text="Page 1 / 1")
        self.page_label.pack(side="left", padx=10)
        ttk.Button(pag_frame, text="Next ▶", command=self._next).pack(side="left", padx=5)

    def _load(self):
        """Fetch and display audit logs for the current page and filter."""
        for row in self.tree.get_children():
            self.tree.delete(row)
        try:
            rows, self.total_pages = get_audit_logs(self.current_page, self.action_filter)
            for r in rows:
                self.tree.insert(
                    "", "end", values=(r["id"], r["action"], r["details"], r["performed_by"], str(r["performed_at"]))
                )
            self.page_label.config(text=f"Page {self.current_page} / {self.total_pages}")
        except Exception as e:
            logger.error(f"Audit load error: {e}")
            messagebox.showerror("Error", f"Failed to load audit log: {e}")

    def _apply_filter(self):
        """Apply the selected action filter and reload from page 1."""
        val = self.filter_var.get()
        # "ALL" means no filter (None), anything else is the action string
        self.action_filter = None if val == "ALL" else val
        self.current_page = 1
        self._load()

    def _prev(self):
        """Navigate to previous page."""
        if self.current_page > 1:
            self.current_page -= 1
            self._load()

    def _next(self):
        """Navigate to next page."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._load()

    def on_show(self, **kwargs):
        """Reset filter and pagination when navigating to this page."""
        self.current_page = 1
        self.action_filter = None
        self.filter_var.set("ALL")
        self._load()
