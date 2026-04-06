"""
view_passwords.py — View Passwords Page (Paginated)
=====================================================
PURPOSE:
    Displays all stored passwords in a paginated table with search and
    password reveal functionality. Passwords are shown as "••••••••" by
    default and only decrypted when the admin clicks "Reveal".

UI LAYOUT:
    ┌──────────────────────────────────────────────────────────────┐
    │  View Passwords                            [← Dashboard]    │
    │  ──────────────────────────────────────────────────────────  │
    │  [search_______________] [Search] [Clear]                   │
    │                                                              │
    │  ┌────┬──────────┬──────────┬──────────┬──────────────────┐ │
    │  │ ID │ Site     │ Username │ Password │ Created          │ │
    │  ├────┼──────────┼──────────┼──────────┼──────────────────┤ │
    │  │ 1  │ Gmail    │ john     │ •••••••• │ 2025-01-15 10:30 │ │
    │  │ 2  │ GitHub   │ jane     │ •••••••• │ 2025-01-14 09:15 │ │
    │  └────┴──────────┴──────────┴──────────┴──────────────────┘ │
    │                                                              │
    │           [Reveal Selected Password]                        │
    │        [◀ Prev]  Page 1 / 3  [Next ▶]                      │
    └──────────────────────────────────────────────────────────────┘

KEY CONCEPTS:

    TREEVIEW WIDGET:
        ttk.Treeview is Tkinter's table/grid widget. Despite the name, it can
        display flat tabular data (not just trees). Each row has an 'iid'
        (internal item ID) which we set to the database row ID for easy lookup.

    PASSWORD MASKING WITH TAGS:
        Passwords are displayed as "••••••••" in the table. The actual encrypted
        password is stored in the row's "tags" attribute (a hidden metadata field).
        When "Reveal" is clicked, we read the tag, decrypt it, and update the cell.

    PAGINATION STATE:
        - current_page: Which page we're viewing (1-based)
        - total_pages: Calculated from total records / PAGE_SIZE
        - search_query: Active search term (empty = show all)
"""

import tkinter as tk
from tkinter import messagebox, ttk

from app.services.audit_service import log_action
from app.services.password_service import decrypt_password, get_passwords, search_passwords
from app.utils.helpers import setup_logger

logger = setup_logger(__name__)


class ViewPasswordsPage(ttk.Frame):
    """Paginated password viewer with search and reveal functionality."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.current_page = 1
        self.total_pages = 1
        self.search_query = ""
        self._build_ui()

    def _build_ui(self):
        """Build the search bar, data table, reveal button, and pagination controls."""
        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=(15, 5))
        ttk.Label(header, text="View Passwords", font=("Helvetica", 16, "bold")).pack(side="left")
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

        # Data table (Treeview)
        cols = ("ID", "Site", "Username", "Password", "Created")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for col in cols:
            self.tree.heading(col, text=col)
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Site", width=180)
        self.tree.column("Username", width=150)
        self.tree.column("Password", width=220)
        self.tree.column("Created", width=160)

        # Vertical scrollbar linked to the treeview
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(fill="both", expand=True, padx=20, pady=5)
        scrollbar.pack()

        # Reveal button
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Reveal Selected Password", command=self._reveal).pack(side="left", padx=5)

        # Pagination controls
        pag_frame = ttk.Frame(self)
        pag_frame.pack(pady=5)
        ttk.Button(pag_frame, text="◀ Prev", command=self._prev).pack(side="left", padx=5)
        self.page_label = ttk.Label(pag_frame, text="Page 1 / 1")
        self.page_label.pack(side="left", padx=10)
        ttk.Button(pag_frame, text="Next ▶", command=self._next).pack(side="left", padx=5)

    def _load(self):
        """Fetch and display passwords for the current page.

        Clears the table, fetches the appropriate page of data (with or without
        search filter), and populates the Treeview rows.

        Each row's encrypted_password is stored in the 'tags' attribute so it
        can be retrieved later for decryption without another DB query.
        """
        # Clear all existing rows
        for row in self.tree.get_children():
            self.tree.delete(row)
        try:
            # Fetch data based on whether a search is active
            if self.search_query:
                rows, self.total_pages = search_passwords(self.search_query, self.current_page)
            else:
                rows, self.total_pages = get_passwords(self.current_page)

            for r in rows:
                # Display "••••••••" instead of the actual password
                self.tree.insert(
                    "",
                    "end",
                    iid=r["id"],
                    values=(r["id"], r["site_name"], r["username"], "••••••••", str(r["created_at"])),
                )
                # Store the encrypted password in the row's tags for later reveal
                self.tree.item(r["id"], tags=(r["encrypted_password"],))

            self.page_label.config(text=f"Page {self.current_page} / {self.total_pages}")
        except Exception as e:
            logger.error(f"Load passwords error: {e}")
            messagebox.showerror("Error", f"Failed to load: {e}")

    def _reveal(self):
        """Decrypt and display the selected row's password.

        Steps:
            1. Get the selected row from the Treeview
            2. Read the encrypted password from the row's tags
            3. Decrypt it using crypto_service
            4. Update the Password column with the plain text
            5. Log the reveal action to the audit trail
        """
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Select a row first.")
            return
        item = sel[0]  # The iid (which is the DB row ID)
        tags = self.tree.item(item, "tags")
        if not tags:
            return
        try:
            decrypted = decrypt_password(tags[0])  # tags[0] = encrypted_password
            values = list(self.tree.item(item, "values"))
            values[3] = decrypted  # Replace "••••••••" with actual password
            self.tree.item(item, values=values)
            admin = self.controller.current_user["username"]
            log_action("VIEW_PASSWORD", f"Revealed password id={item}.", admin)
        except Exception as e:
            messagebox.showerror("Error", f"Decryption failed: {e}")

    def _search(self):
        """Apply search filter and reload from page 1."""
        self.search_query = self.search_var.get().strip()
        self.current_page = 1
        self._load()

    def _clear_search(self):
        """Clear search filter and show all passwords."""
        self.search_var.set("")
        self.search_query = ""
        self.current_page = 1
        self._load()

    def _prev(self):
        """Navigate to the previous page (if not on page 1)."""
        if self.current_page > 1:
            self.current_page -= 1
            self._load()

    def _next(self):
        """Navigate to the next page (if not on the last page)."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._load()

    def on_show(self, **kwargs):
        """Reset to page 1 with no search filter when navigating to this page."""
        self.current_page = 1
        self.search_query = ""
        self.search_var.set("")
        self._load()
