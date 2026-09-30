"""
main.py

Entry point for ImageUnraveling, the HIT137 Assignment 3 tile puzzle.

Run with (from the project root):
    python src/main.py

Requires: opencv-python, numpy, Pillow (see requirements.txt)
"""

import tkinter as tk

from ui.gui import PuzzleGameApp


def main() -> None:
    """Open the game window and run until it is closed."""
    root = tk.Tk()
    PuzzleGameApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
