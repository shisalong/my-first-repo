"""
delete_passwords.py — Delete Passwords Page (Paginated)
========================================================
PURPOSE:
    Paginated table for selecting and deleting stored passwords.
    Similar to view_passwords.py but without the password column (no need to
    show passwords when deleting) and with a delete button instead of reveal.

UI LAYOUT:
    ┌──────────────────────────────────────────────────────────────┐
    │  Delete Passwords                          [← Dashboard]    │
    │  ──────────────────────────────────────────────────────────  │
    │  [search_______________] [Search] [Clear]                   │
    │                                                              │
    │  ┌────┬──────────┬──────────┬──────────────────┐            │
    │  │ ID │ Site     │ Username │ Created          │            │
    │  ├────┼──────────┼──────────┼──────────────────┤            │
    │  │ 1  │ Gmail    │ john     │ 2025-01-15 10:30 │  ← click  │
    │  │ 2  │ GitHub   │ jane     │ 2025-01-14 09:15 │  to select│
    │  └────┴──────────┴──────────┴──────────────────┘            │
    │                                                              │
    │              [Delete Selected]                               │
    │        [◀ Prev]  Page 1 / 3  [Next ▶]                      │
    └──────────────────────────────────────────────────────────────┘

DELETE FLOW:
    1. Admin selects a row in the table
    2. Clicks "Delete Selected"
    3. Confirmation dialog: "Delete password for 'Gmail' (ID: 1)?"
    4. If confirmed → delete from DB → log to audit → refresh table
    5. If cancelled → nothing happens

WHY SEPARATE FROM VIEW PAGE?
    Separation of concerns: each page has a single responsibility.
    The view page is for browsing/revealing, the delete page is for removal.
    This prevents accidental deletions while browsing.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from app.services.audit_service import log_action
from app.services.password_service import delete_password, get_passwords, search_passwords
from app.utils.helpers import setup_logger

logger = setup_logger(__name__)


class DeletePasswordsPage(ttk.Frame):
    """Paginated password list with search and delete functionality."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.current_page = 1
        self.total_pages = 1
        self.search_query = ""
        self._build_ui()

    def _build_ui(self):
        """Build the search bar, data table, delete button, and pagination."""
        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=(15, 5))
        ttk.Label(header, text="Delete Passwords", font=("Helvetica", 16, "bold")).pack(side="left")
        ttk.Button(header, text="← Dashboard", command=lambda: self.controller.show_frame("Dashboard")).pack(
            side="right"
        )

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=5)

        # Search bar
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", padx=20, pady=5)
        self.search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.search_var, width=40).pack(side="left")
        ttk.Button(search_frame, text="Search", command=self._search).pack(side="left", padx=5)
        ttk.Button(search_frame, text="Clear", command=self._clear_search).pack(side="left")

        # Data table — no Password column (not needed for deletion)
        cols = ("ID", "Site", "Username", "Created")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for col in cols:
            self.tree.heading(col, text=col)
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Site", width=220)
        self.tree.column("Username", width=200)
        self.tree.column("Created", width=180)
        self.tree.pack(fill="both", expand=True, padx=20, pady=5)

        # Delete button
        ttk.Button(self, text="Delete Selected", command=self._delete, style="Accent.TButton").pack(pady=5)

        # Pagination
        pag_frame = ttk.Frame(self)
        pag_frame.pack(pady=5)
        ttk.Button(pag_frame, text="◀ Prev", command=self._prev).pack(side="left", padx=5)
        self.page_label = ttk.Label(pag_frame, text="Page 1 / 1")
        self.page_label.pack(side="left", padx=10)
        ttk.Button(pag_frame, text="Next ▶", command=self._next).pack(side="left", padx=5)

    def _load(self):
        """Fetch and display passwords for the current page."""
        for row in self.tree.get_children():
            self.tree.delete(row)
        try:
            if self.search_query:
                rows, self.total_pages = search_passwords(self.search_query, self.current_page)
            else:
                rows, self.total_pages = get_passwords(self.current_page)
            for r in rows:
                self.tree.insert(
                    "", "end", iid=r["id"], values=(r["id"], r["site_name"], r["username"], str(r["created_at"]))
                )
            self.page_label.config(text=f"Page {self.current_page} / {self.total_pages}")
        except Exception as e:
            logger.error(f"Load error: {e}")
            messagebox.showerror("Error", f"Failed to load: {e}")

    def _delete(self):
        """Delete the selected password after confirmation.

        Steps:
            1. Check that a row is selected
            2. Extract the row ID and site name for the confirmation message
            3. Show a Yes/No confirmation dialog
            4. If confirmed: call delete_password() → log audit → refresh table
        """
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Select a row to delete.")
            return

        item_id = int(sel[0])  # The iid is the DB row ID (as string), convert to int
        values = self.tree.item(sel[0], "values")
        site = values[1] if values else "unknown"

        # Confirmation dialog — prevents accidental deletions
        if not messagebox.askyesno("Confirm Delete", f"Delete password for '{site}' (ID: {item_id})?"):
            return

        try:
            if delete_password(item_id):
                admin = self.controller.current_user["username"]
                log_action("DELETE_PASSWORD", f"Deleted password id={item_id}, site='{site}'.", admin)
                messagebox.showinfo("Deleted", "Password deleted successfully.")
                self._load()  # Refresh the table to reflect the deletion
            else:
                messagebox.showerror("Error", "Record not found.")
        except Exception as e:
            logger.error(f"Delete error: {e}")
            messagebox.showerror("Error", f"Failed to delete: {e}")

    def _search(self):
        """Apply search filter and reload from page 1."""
        self.search_query = self.search_var.get().strip()
        self.current_page = 1
        self._load()

    def _clear_search(self):
        """Clear search and show all passwords."""
        self.search_var.set("")
        self.search_query = ""
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
        """Reset to page 1 with no search when navigating to this page."""
        self.current_page = 1
        self.search_query = ""
        self.search_var.set("")
        self._load()
