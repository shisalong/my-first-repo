"""
dashboard.py — Main Navigation Hub
====================================
PURPOSE:
    The central page after login. Displays 5 navigation cards that link
    to all functional pages of the application.

UI LAYOUT:
    ┌──────────────────────────────────────────────────────┐
    │  Dashboard                    Welcome, admin  [Logout]│
    │  ─────────────────────────────────────────────────── │
    │                                                       │
    │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
    │  │ Add Password │ │ View Passwords│ │Delete Passwords│
    │  │ Store a new  │ │ Browse &     │ │ Remove saved │ │
    │  │ credential   │ │ search saved │ │ credentials  │ │
    │  │   [Open]     │ │   [Open]     │ │   [Open]     │ │
    │  └──────────────┘ └──────────────┘ └──────────────┘ │
    │                                                       │
    │  ┌──────────────┐ ┌──────────────┐                   │
    │  │ Audit Log    │ │ Export Data  │                   │
    │  │ View all     │ │ Export to    │                   │
    │  │ activity     │ │ file         │                   │
    │  │   [Open]     │ │   [Open]     │                   │
    │  └──────────────┘ └──────────────┘                   │
    └──────────────────────────────────────────────────────┘

GRID LAYOUT:
    The 5 cards are arranged in a 2-row grid using i // 3 for row and i % 3 for column:
    Row 0: cards 0, 1, 2 (Add, View, Delete)
    Row 1: cards 3, 4     (Audit, Export)

LAMBDA CLOSURE TRICK:
    In the button command, we use: lambda t=target: self.controller.show_frame(t)
    The 't=target' captures the current value of 'target' at loop time.
    Without it, all buttons would navigate to the LAST target in the list
    (a common Python closure bug in loops).
"""

from tkinter import ttk

from app.utils.helpers import setup_logger

logger = setup_logger(__name__)


class Dashboard(ttk.Frame):
    """Dashboard page with navigation cards to all app features."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._build_ui()

    def _build_ui(self):
        """Build the dashboard header and navigation card grid."""
        # Header bar with title, welcome message, and logout button
        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=(15, 5))
        ttk.Label(header, text="Dashboard", font=("Helvetica", 18, "bold")).pack(side="left")
        ttk.Button(header, text="Logout", command=self.controller.logout).pack(side="right")

        # Welcome label — updated in on_show() with the admin's username
        self.welcome_label = ttk.Label(header, text="", font=("Helvetica", 11))
        self.welcome_label.pack(side="right", padx=15)

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=5)

        # Navigation card grid
        nav = ttk.Frame(self)
        nav.pack(expand=True)

        # Each tuple: (card_title, target_page_class_name, description_text)
        buttons = [
            ("Add Password", "AddPasswordPage", "Store a new credential"),
            ("View Passwords", "ViewPasswordsPage", "Browse & search saved passwords"),
            ("Delete Passwords", "DeletePasswordsPage", "Remove saved credentials"),
            ("Audit Log", "AuditPage", "View all activity history"),
            ("Export Data", "ExportPage", "Export passwords to file"),
        ]

        for i, (label, target, desc) in enumerate(buttons):
            # LabelFrame creates a bordered card with a title
            frame = ttk.LabelFrame(nav, text=label, padding=15)
            # i // 3 = row (0 for first 3, 1 for next 2)
            # i % 3 = column (0, 1, 2 cycling)
            frame.grid(row=i // 3, column=i % 3, padx=15, pady=15, sticky="nsew")
            ttk.Label(frame, text=desc, wraplength=180).pack(pady=(0, 10))
            # lambda t=target captures 'target' value at this iteration
            ttk.Button(frame, text="Open", command=lambda t=target: self.controller.show_frame(t)).pack()

    def on_show(self, **kwargs):
        """Update the welcome message with the logged-in admin's username."""
        user = self.controller.current_user
        name = user["username"] if user else ""
        self.welcome_label.config(text=f"Welcome, {name}")
