"""
app.py — Main application window.

Layout (top to bottom):
  - CTkTabview  — Orders, Archive, Settings tabs (expands to fill space)
  - Console pane — fixed-height, always visible, shows pipeline log output

The Console instance is created here and passed into any tab that needs it
so all modules write to the same pane.
"""

import customtkinter as ctk
from console import Console
from orders_tab import OrdersTab
from settings_tab import SettingsTab


class OperatorApp(ctk.CTk):
    """
    The top-level application window.
    Inherits from CTk (CustomTkinter's main window class).
    """

    def __init__(self):
        super().__init__()

        # --- Window basics ------------------------------------------------
        self.title("TerrainTool Operator")
        self.geometry("900x650")
        self.minsize(700, 520)

        # Dark theme that suits a pipeline operator tool
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # --- Console (built before tabs so we can pass it in) ------------
        # The console pane sits at the bottom of the window. We build it
        # last visually (pack order) but create the object first so tabs
        # can receive a reference to it during construction.
        self._console = Console()

        # --- Tab view ----------------------------------------------------
        # pack with expand=True so the tab area grows and the console stays
        # anchored at the bottom at its fixed height.
        self.tabs = ctk.CTkTabview(self, anchor="nw")
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(12, 0))

        self.tabs.add("Orders")
        self.tabs.add("Archive")
        self.tabs.add("Settings")

        # Build each tab's content
        self._build_orders_tab()
        self._build_archive_tab()
        self._build_settings_tab()

        # --- Console pane — anchored to the bottom -----------------------
        # Build into a container frame so padding is consistent
        console_container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        console_container.pack(fill="x", padx=0, pady=0)
        self._console.build(console_container)

        # Print the startup message once the window is ready
        self._console.log("TerrainTool Operator ready.", level="info")

    # ------------------------------------------------------------------ #
    # Tab builders                                                         #
    # ------------------------------------------------------------------ #

    def _build_orders_tab(self) -> None:
        """Orders tab — implemented in OrdersTab (orders_tab.py)."""
        frame = self.tabs.tab("Orders")
        orders = OrdersTab(console=self._console)
        orders.build(frame)

    def _build_archive_tab(self) -> None:
        """Archive tab — placeholder for a future phase."""
        frame = self.tabs.tab("Archive")
        ctk.CTkLabel(
            frame,
            text="Coming soon",
            font=ctk.CTkFont(size=18),
            text_color="gray60",
        ).place(relx=0.5, rely=0.5, anchor="center")

    def _build_settings_tab(self) -> None:
        """Settings tab — fully implemented in SettingsTab (settings_tab.py)."""
        frame = self.tabs.tab("Settings")
        settings = SettingsTab()
        settings.build(frame)
