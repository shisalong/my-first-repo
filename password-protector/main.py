"""
main.py — Application Entry Point & Frame Controller
======================================================
PURPOSE:
    This is the MAIN file that starts the entire application.
    Run it with: uv run python main.py

WHAT IT DOES:
    1. Creates the main Tkinter window (900x650 pixels)
    2. Builds ALL 8 GUI pages (frames) and stacks them on top of each other
    3. Shows the Login page first
    4. Provides navigation between pages via show_frame()

TKINTER FRAME STACKING PATTERN:
    All 8 pages are created at startup and placed in the SAME grid cell (row=0, col=0).
    They are literally stacked on top of each other like a deck of cards.
    show_frame() calls tkraise() to bring a specific page to the front.

    This is more efficient than destroying and recreating pages on every navigation.

    ┌─────────────────────────────────────────┐
    │  Container (ttk.Frame)                  │
    │  ┌───────────────────────────────────┐  │
    │  │  ExportPage        (bottom)       │  │
    │  │  AuditPage                        │  │
    │  │  DeletePasswordsPage              │  │
    │  │  ViewPasswordsPage                │  │
    │  │  AddPasswordPage                  │  │
    │  │  Dashboard                        │  │
    │  │  MfaPage                          │  │
    │  │  LoginPage          (top/visible) │  │
    │  └───────────────────────────────────┘  │
    └─────────────────────────────────────────┘

CONTROLLER PATTERN:
    The App class acts as a "controller" — it's passed to every page as 'controller'.
    Pages use controller.show_frame("PageName") to navigate, and
    controller.current_user to access the logged-in admin's info.
    This avoids tight coupling between pages — they only know about the controller.

TTK THEME:
    We use ttk (themed Tkinter) with the "clam" theme for a modern look.
    Available themes: 'clam', 'alt', 'default', 'classic' (varies by OS).
"""

import tkinter as tk
from tkinter import ttk

from app.gui.add_password import AddPasswordPage
from app.gui.audit_page import AuditPage
from app.gui.dashboard import Dashboard
from app.gui.delete_passwords import DeletePasswordsPage
from app.gui.export_page import ExportPage
from app.gui.login_page import LoginPage
from app.gui.mfa_page import MfaPage
from app.gui.view_passwords import ViewPasswordsPage
from app.utils.constants import APP_NAME
from app.utils.helpers import setup_logger

logger = setup_logger(__name__)


class App(tk.Tk):
    """Main application window and page controller.

    Inherits from tk.Tk, which is the root Tkinter window.
    All GUI pages are children of this window.

    Attributes:
        current_user: dict or None — the logged-in admin's DB record.
                      Set after successful authentication, cleared on logout.
        frames:       dict mapping page names to their Frame instances.
        container:    The parent frame that holds all stacked pages.
    """

    def __init__(self):
        super().__init__()

        # Window configuration
        self.title(APP_NAME)  # Window title bar text
        self.geometry("900x650")  # Initial window size (width x height)
        self.minsize(800, 600)  # Minimum resize dimensions

        # Track the currently logged-in admin user (None = not logged in)
        self.current_user = None

        # Apply the "clam" ttk theme for modern-looking widgets
        # ttk.Style controls the visual appearance of all ttk widgets
        style = ttk.Style(self)
        style.theme_use("clam")

        # Create the container frame that holds all pages
        # fill="both" + expand=True makes it fill the entire window
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)
        # Configure grid so the stacked frames expand to fill the container
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Dictionary to store all page frames: {"LoginPage": <LoginPage instance>, ...}
        self.frames: dict[str, ttk.Frame] = {}
        self._build_frames()

        # Show the login page on startup
        self.show_frame("LoginPage")

    def _build_frames(self):
        """Create all 8 GUI pages and stack them in the container.

        Each page class receives:
        - parent: The container frame (so the page is a child widget of it)
        - controller: This App instance (so the page can navigate and access state)

        All pages are placed in the same grid cell (0, 0) with sticky="nsew"
        so they stretch to fill the entire container.
        """
        for page_class in (
            LoginPage,
            MfaPage,
            Dashboard,
            AddPasswordPage,
            ViewPasswordsPage,
            DeletePasswordsPage,
            AuditPage,
            ExportPage,
        ):
            name = page_class.__name__  # e.g., "LoginPage", "Dashboard"
            frame = page_class(parent=self.container, controller=self)
            self.frames[name] = frame
            # sticky="nsew" = stretch North, South, East, West (fill entire cell)
            frame.grid(row=0, column=0, sticky="nsew")

    def show_frame(self, name: str, **kwargs):
        """Navigate to a specific page by bringing it to the front.

        If the page has an on_show() method, it's called first. This lets
        pages refresh their data or reset their form fields when navigated to.

        Args:
            name:   The class name of the page (e.g., "Dashboard", "AddPasswordPage").
            kwargs: Optional keyword arguments passed to the page's on_show() method.
                    Example: show_frame("MfaPage", user=user_dict)
        """
        frame = self.frames[name]
        # Call on_show() if the page defines it (for data refresh/reset)
        if hasattr(frame, "on_show"):
            frame.on_show(**kwargs)
        # tkraise() brings this frame to the top of the stack (makes it visible)
        frame.tkraise()
        logger.info(f"Navigated to {name}")

    def set_user(self, user: dict):
        """Store the authenticated admin user's info after successful login.

        Args:
            user: The admin_users row dict from the database.
        """
        self.current_user = user

    def logout(self):
        """Log out the current admin and return to the login page.

        Clears the current_user and navigates back to LoginPage.
        The login page's on_show() will clear the form fields.
        """
        self.current_user = None
        self.show_frame("LoginPage")


def main():
    """Application entry point. Creates and runs the Tkinter main loop.

    The mainloop() call is BLOCKING — it runs forever, processing GUI events
    (clicks, key presses, window resizes) until the user closes the window.
    """
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
