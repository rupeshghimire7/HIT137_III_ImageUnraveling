"""
main.py

Entry point for the HIT137 Assignment 3 tile-rotation puzzle.

Run with (from the project root):
    python src/main.py

Requires: opencv-python, numpy, Pillow (see requirements.txt)
"""

import tkinter as tk

from ui.gui import PuzzleGameApp


def main():
    root = tk.Tk()
    PuzzleGameApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
