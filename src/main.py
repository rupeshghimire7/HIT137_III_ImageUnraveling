"""
main.py

Entry point for ImageUnraveling, the HIT137 Assignment 3 tile puzzle.

Run with (from the project root):
    python src/main.py

Requires: opencv-python, numpy, Pillow (see requirements.txt)
"""
import tkinter as tk

from audio.sound_game import SoundPuzzleGameApp


def main():
    root = tk.Tk()
    SoundPuzzleGameApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()