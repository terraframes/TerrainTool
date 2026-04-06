"""
main.py — Entry point for the TerrainTool Operator desktop app.

Run with:  python main.py
Requires:  customtkinter  (pip install customtkinter)
"""

from app import OperatorApp


def main():
    app = OperatorApp()
    # Start the Tkinter event loop — blocks until the window is closed
    app.mainloop()


if __name__ == "__main__":
    main()
