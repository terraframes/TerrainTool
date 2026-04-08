"""
orders_tab.py — Orders tab for the TerrainTool Operator app.

Scans the local orders folder (from config.json), reads each order's
params.json, detects its pipeline stage, and renders one row per order.

Each row has three action buttons whose enabled state depends on the order's
current status. Subprocesses always run in background threads so the UI
never freezes.
"""

import json
import os
import subprocess
import threading
import customtkinter as ctk

from config import load_config

# Path to the DEM acquisition script (module 2)
ACQUIRE_SCRIPT = r"E:\TerrainTool\module2\acquire.py"
# Path to the extended acquisition script (module 2b) — handles non-GLO-30 datasets
ACQUIRE_EXTENDED_SCRIPT = r"E:\TerrainTool\module2b\acquire_extended.py"


# --- Status definitions -------------------------------------------------
# Maps processing_status value → (display label, badge colour).

STATUS_META = {
    "received":    ("Received", "#6b7280"),   # grey
    "dem_done":    ("DEM Ready", "#2563eb"),  # blue
    "ready":       ("DEM Ready", "#2563eb"),  # Module 2b sets this instead of dem_done
    "refine_done": ("Refined",   "#d97706"),  # yellow/amber
    "exported":    ("Exported",  "#16a34a"),  # green
    "error":       ("Error",     "#dc2626"),  # red
}
DEFAULT_STATUS_META = ("Unknown", "#6b7280")

_DEM_FILE      = "raw_dem.tif"
_RESAMPLE_FILE = "resampled.tif"
_EXPORT_FILE   = "final.stl"


# --- Status inference ---------------------------------------------------

def _infer_status(order_folder: str) -> str:
    """
    Infer pipeline stage from which output files exist locally.
    Used when params.json has no processing_status field.
    """
    has_dem      = os.path.isfile(os.path.join(order_folder, _DEM_FILE))
    has_resample = os.path.isfile(os.path.join(order_folder, _RESAMPLE_FILE))
    has_export   = os.path.isfile(os.path.join(order_folder, _EXPORT_FILE))

    if has_export:
        return "exported"
    if has_resample:
        return "refine_done"
    if has_dem:
        return "dem_done"
    return "received"


# --- Order scanning -----------------------------------------------------

def _scan_orders(orders_folder: str) -> list[dict]:
    """
    Walk every direct subfolder of orders_folder.
    Returns a list of order dicts for subfolders that contain params.json.
    Subfolders without params.json are silently skipped.
    """
    orders = []
    try:
        entries = sorted(os.scandir(orders_folder), key=lambda e: e.name)
    except OSError:
        return []

    for entry in entries:
        if not entry.is_dir():
            continue
        params_path = os.path.join(entry.path, "params.json")
        if not os.path.isfile(params_path):
            continue
        orders.append(_load_order(entry.name, entry.path, params_path))

    return orders


def _load_order(folder_name: str, folder_path: str, params_path: str) -> dict:
    """
    Parse one order's params.json.
    On any failure, returns an error-state dict so the row still appears.
    """
    try:
        with open(params_path, "r", encoding="utf-8") as f:
            params = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {
            "order_number": folder_name,
            "area_km":      None,
            "dataset":      None,
            "status":       "error",
            "folder_path":  folder_path,
        }

    status = params.get("processing_status") or _infer_status(folder_path)
    if status not in STATUS_META:
        status = "error"

    return {
        "order_number": str(params.get("order_number", folder_name)),
        "area_km":      params.get("area_km"),
        "dataset":      params.get("dataset"),
        "status":       status,
        "folder_path":  folder_path,
    }


# --- Tab class ----------------------------------------------------------

class OrdersTab:
    """
    Builds and manages the Orders tab.
    Receives a Console instance from app.py so it can log pipeline output.
    """

    def __init__(self, console):
        # console — the Console instance from app.py
        self._console = console
        self._parent = None
        self._list_frame = None
        # Keep a reference to the app root so we can use after() for thread safety
        self._app = None

    # ------------------------------------------------------------------ #
    # Public                                                               #
    # ------------------------------------------------------------------ #

    def build(self, parent: ctk.CTkFrame) -> None:
        """Set up the Orders tab layout and do the first scan."""
        self._parent = parent
        # Walk up the widget tree to find the root Tk window
        self._app = parent.winfo_toplevel()

        # Top bar: heading on the left, Refresh button on the right
        top_bar = ctk.CTkFrame(parent, fg_color="transparent")
        top_bar.pack(fill="x", padx=16, pady=(14, 6))

        ctk.CTkLabel(
            top_bar,
            text="Orders",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left")

        # Keep a reference so we can disable it while a sync is running
        self._refresh_btn = ctk.CTkButton(
            top_bar,
            text="Refresh",
            width=90,
            command=self._refresh,
        )
        self._refresh_btn.pack(side="right")

        # Thin separator below the top bar
        ctk.CTkFrame(parent, height=2, fg_color="gray30").pack(
            fill="x", padx=16, pady=(0, 8)
        )

        # Scrollable list area
        self._list_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self._list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # On first build just scan locally — don't trigger a Drive sync
        self._redraw_list()

    # ------------------------------------------------------------------ #
    # Private — list management                                           #
    # ------------------------------------------------------------------ #

    def _refresh(self) -> None:
        """
        Called when the Refresh button is clicked.
        If acquire.py exists, runs it with --sync-only in a background thread
        to pull any new orders from Google Drive before redrawing the list.
        Falls back to a local-only redraw if the script is missing.
        """
        # Guard: don't let the user trigger a second sync while one is running
        self._refresh_btn.configure(state="disabled")

        if not os.path.isfile(ACQUIRE_SCRIPT):
            # acquire.py missing — just refresh from what's on disk
            self._console.log(
                "acquire.py not found — refreshing local list only", level="warn"
            )
            self._redraw_list()
            self._refresh_btn.configure(state="normal")
            return

        # acquire.py found — run the sync in the background so the UI stays responsive
        self._console.log("Syncing orders from Google Drive...", level="info")

        def run():
            try:
                proc = subprocess.Popen(
                    ["python", ACQUIRE_SCRIPT, "--sync-only"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,   # merge stderr so we see everything
                    text=True,
                    bufsize=1,                  # line-buffered for real-time output
                )

                # Stream each output line to the console on the main thread
                for line in proc.stdout:
                    stripped = line.rstrip()
                    if stripped:
                        self._app.after(0, lambda msg=stripped: self._console.log(msg, level="info"))

                proc.wait()

                if proc.returncode == 0:
                    self._app.after(0, lambda: self._console.log("Sync complete", level="ok"))
                else:
                    self._app.after(0, lambda: self._console.log(
                        "Sync failed — check console for details", level="error"
                    ))

            except Exception as e:
                self._app.after(0, lambda err=e: self._console.log(
                    f"Failed to start acquire.py: {err}", level="error"
                ))
            finally:
                # Always redraw and re-enable the button on the main thread,
                # even if the sync failed — show whatever is available locally
                self._app.after(0, self._redraw_list)
                self._app.after(0, lambda: self._refresh_btn.configure(state="normal"))

        threading.Thread(target=run, daemon=True).start()

    def _redraw_list(self) -> None:
        """Clear and redraw the orders list from the local orders folder."""
        for widget in self._list_frame.winfo_children():
            widget.destroy()

        config = load_config()
        orders_folder = config.get("orders_folder", "").strip()

        if not orders_folder:
            self._show_message("Orders folder not configured — go to Settings")
            return
        if not os.path.isdir(orders_folder):
            self._show_message(f"Orders folder not found:\n{orders_folder}")
            return

        orders = _scan_orders(orders_folder)

        if not orders:
            self._show_message("No orders found")
            return

        for index, order in enumerate(orders):
            shade = "gray17" if index % 2 == 0 else "gray20"
            self._render_row(order, shade)

    def _show_message(self, text: str) -> None:
        """Display a centred message when the list is empty or unconfigured."""
        ctk.CTkLabel(
            self._list_frame,
            text=text,
            text_color="gray60",
            font=ctk.CTkFont(size=14),
        ).pack(expand=True, pady=40)

    # ------------------------------------------------------------------ #
    # Private — row rendering                                             #
    # ------------------------------------------------------------------ #

    def _render_row(self, order: dict, bg_colour: str) -> None:
        """
        Render one order row with:
          col 0 — order number
          col 1 — area
          col 2 — dataset
          col 3 — status badge
          col 4 — spacer
          col 5 — Download DEM button
          col 6 — Open in Blender button
        """
        status = order["status"]

        row = ctk.CTkFrame(self._list_frame, fg_color=bg_colour, corner_radius=6)
        row.pack(fill="x", pady=(0, 4))

        row.grid_columnconfigure(0, minsize=150)   # order number
        row.grid_columnconfigure(1, minsize=80)    # area
        row.grid_columnconfigure(2, minsize=80)    # dataset
        row.grid_columnconfigure(3, minsize=100)   # badge
        row.grid_columnconfigure(4, weight=1)      # spacer
        row.grid_columnconfigure(5, minsize=128)   # Download DEM
        row.grid_columnconfigure(6, minsize=128)   # Open in Blender

        # Order number
        ctk.CTkLabel(
            row,
            text=f"#{order['order_number']}",
            font=ctk.CTkFont(weight="bold"),
            anchor="w",
            width=150,
        ).grid(row=0, column=0, padx=(12, 8), pady=10, sticky="w")

        # Area
        area_text = f"{order['area_km']} km²" if order["area_km"] is not None else "—"
        ctk.CTkLabel(row, text=area_text, anchor="w").grid(
            row=0, column=1, padx=8, pady=10, sticky="w"
        )

        # Dataset
        ctk.CTkLabel(row, text=order["dataset"] or "—", anchor="w").grid(
            row=0, column=2, padx=8, pady=10, sticky="w"
        )

        # Status badge
        label, colour = STATUS_META.get(status, DEFAULT_STATUS_META)
        ctk.CTkLabel(
            row,
            text=label,
            fg_color=colour,
            corner_radius=4,
            width=90,
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=3, padx=8, pady=8, sticky="w")

        # --- Action buttons ---------------------------------------------

        # Button 1: Download DEM — only active when status is "received"
        dl_state = "normal" if status == "received" else "disabled"
        ctk.CTkButton(
            row,
            text="Download DEM",
            width=118,
            state=dl_state,
            command=lambda o=order: self._download_dem(o),
        ).grid(row=0, column=5, padx=(0, 6), pady=8)

        # Button 2: Open in Blender — active at any post-DEM stage
        blender_state = "normal" if status in ("dem_done", "ready", "refine_done", "exported") else "disabled"
        ctk.CTkButton(
            row,
            text="Open in Blender",
            width=118,
            state=blender_state,
            command=lambda o=order: self._open_blender(o),
        ).grid(row=0, column=6, padx=(0, 12), pady=8)

    # ------------------------------------------------------------------ #
    # Private — button actions                                            #
    # ------------------------------------------------------------------ #

    def _download_dem(self, order: dict) -> None:
        """
        Run acquire.py in a background thread, streaming its output to the
        console line by line. Refreshes the order list when the process exits.
        """
        num = order["order_number"]
        self._console.log(f"Downloading DEM for order {num}...", level="info")

        # Route to the correct acquisition script based on the order's dataset.
        # GLO-30 orders use Module 2 (acquire.py).
        # All other datasets (local rasters, future LiDAR) use Module 2b (acquire_extended.py).
        dataset = order.get("dataset", "GLO-30")
        script = ACQUIRE_SCRIPT if dataset == "GLO-30" else ACQUIRE_EXTENDED_SCRIPT

        def run():
            try:
                proc = subprocess.Popen(
                    ["python", script, "--order", num],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,   # merge stderr into stdout
                    text=True,
                    bufsize=1,                  # line-buffered
                )

                # Stream output line by line to the console
                for line in proc.stdout:
                    stripped = line.rstrip()
                    if stripped:
                        self._console.log(stripped, level="info")

                proc.wait()

                if proc.returncode == 0:
                    self._console.log(
                        f"DEM download complete for order {num}", level="ok"
                    )
                else:
                    self._console.log(
                        f"DEM download failed for order {num} "
                        f"(exit code {proc.returncode})",
                        level="error",
                    )

            except Exception as e:
                self._console.log(
                    f"Failed to start acquire.py: {e}", level="error"
                )
            finally:
                # Redraw the order list on the main thread once the process is done
                self._app.after(0, self._redraw_list)

        threading.Thread(target=run, daemon=True).start()

    def _open_blender(self, order: dict) -> None:
        """
        Launch Blender with the terrain addon's load_order operator pre-called.
        Runs in a background daemon thread — never blocks the UI.
        """
        num = order["order_number"]
        config = load_config()
        blender_path = config.get("blender_path", "").strip()

        # Guard: Blender path must be configured in Settings
        if not blender_path:
            self._console.log(
                "Blender path not set — configure it in Settings", level="error"
            )
            return

        # Guard: the executable must actually exist at that path
        if not os.path.isfile(blender_path):
            self._console.log(
                f"Blender executable not found: {blender_path}", level="error"
            )
            return

        # Convert backslashes to forward slashes so the path is safe inside a
        # Python string literal passed via --python-expr on the command line
        folder_fwd = order["folder_path"].replace("\\", "/")

        # The expression tells Blender to call the terrain addon's load_order
        # operator immediately on startup, pointing it at this order's folder
        python_expr = (
            f"import bpy; "
            f"bpy.ops.terrain.load_order('INVOKE_DEFAULT', folder='{folder_fwd}')"
        )

        cmd = [blender_path, "--python-expr", python_expr]

        self._console.log(f"Opening Blender for order {num}...", level="info")

        def run():
            try:
                # Popen returns immediately — we don't wait for Blender to close
                subprocess.Popen(cmd)
                self._console.log(
                    f"Blender launched for order {num}", level="ok"
                )
            except Exception as e:
                self._console.log(f"Failed to launch Blender: {e}", level="error")

        threading.Thread(target=run, daemon=True).start()

