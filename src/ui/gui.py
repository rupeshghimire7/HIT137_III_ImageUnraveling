"""
gui.py

The Tkinter front-end for the tile-rotation puzzle. This module is the
only place that talks to Tkinter/PIL - every game rule lives in
PuzzleBoard, Tile and the Transformation classes, so this file's job is
just to draw things and turn mouse clicks into calls on the model.

Controls
--------
Left click a tile      - select it (coloured border). Click a second tile
                         to swap the two. Click the same tile again to
                         deselect it.
Right click a tile     - rotate it 90 degrees clockwise.
Shift + left click     - flip it horizontally.
Hint button            - highlights one wrong tile (max 3 per image).
Solve button            - instantly restores the picture.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageTk

from engine.puzzle_board import PuzzleBoard

CANVAS_SIZE = 480
GRID_LINE_COLOUR = "#B0B0B0"
SELECTION_COLOUR = "#1E90FF"
HINT_COLOUR = "#00A2FF"
TICK_COLOUR = "#00C851"


class PuzzleGameApp(tk.Frame):
    """Main application window / controller."""

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        master.title("Tile Puzzle - HIT137 Assignment 3")
        master.resizable(False, False)

        self.board = None
        self.selected_index = None
        self.hint_info = None    # (tile_index, home_row, home_col) or None
        self.game_over = False

        # Keep references to PhotoImage objects alive (Tkinter otherwise
        # garbage-collects them and the canvas goes blank).
        self._original_photo = None
        self._puzzle_photo = None

        self._build_widgets()
        self.pack()

    # ------------------------------------------------------------------ #
    # Widget construction
    # ------------------------------------------------------------------ #
    def _build_widgets(self):
        controls = tk.Frame(self)
        controls.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=8)

        self.load_btn = tk.Button(
            controls, text="Load Image...", command=self.on_load_image
        )
        self.load_btn.pack(side=tk.LEFT, padx=(0, 12))

        tk.Label(controls, text="Grid size:").pack(side=tk.LEFT)
        self.grid_size_var = tk.StringVar(value="3 x 3")
        self.grid_size_combo = ttk.Combobox(
            controls,
            textvariable=self.grid_size_var,
            state="readonly",
            width=8,
            values=["3 x 3", "4 x 4", "5 x 5"],
        )
        self.grid_size_combo.pack(side=tk.LEFT, padx=(4, 20))

        self.hint_btn = tk.Button(
            controls, text="Hint", command=self.on_hint, state=tk.DISABLED
        )
        self.hint_btn.pack(side=tk.LEFT, padx=4)

        self.solve_btn = tk.Button(
            controls, text="Solve", command=self.on_solve, state=tk.DISABLED
        )
        self.solve_btn.pack(side=tk.LEFT, padx=4)

        # --- image panes -------------------------------------------------
        images_frame = tk.Frame(self)
        images_frame.grid(row=1, column=0, columnspan=2, padx=10)

        left_frame = tk.Frame(images_frame)
        left_frame.pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(left_frame, text="Original (reference only)").pack()
        self.original_canvas = tk.Canvas(
            left_frame,
            width=CANVAS_SIZE,
            height=CANVAS_SIZE,
            bg="#222222",
            highlightthickness=1,
        )
        self.original_canvas.pack()

        right_frame = tk.Frame(images_frame)
        right_frame.pack(side=tk.LEFT)
        tk.Label(right_frame, text="Puzzle (click to solve)").pack()
        self.puzzle_canvas = tk.Canvas(
            right_frame,
            width=CANVAS_SIZE,
            height=CANVAS_SIZE,
            bg="#222222",
            highlightthickness=1,
        )
        self.puzzle_canvas.pack()

        # Only the transformed/right-hand canvas responds to clicks.
        self.puzzle_canvas.bind("<Button-1>", self.on_left_click)
        self.puzzle_canvas.bind("<Shift-Button-1>", self.on_shift_click)
        self.puzzle_canvas.bind("<Button-3>", self.on_right_click)
        self.puzzle_canvas.bind("<Button-2>", self.on_right_click)  # some macOS setups

        # --- status bar ---------------------------------------------------
        status = tk.Frame(self)
        status.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=8)

        self.moves_var = tk.StringVar(value="Moves: 0")
        self.remaining_var = tk.StringVar(value="Tiles left: -")
        self.hints_var = tk.StringVar(value="Hints left: 3")

        tk.Label(status, textvariable=self.moves_var, width=14, anchor="w").pack(side=tk.LEFT)
        tk.Label(status, textvariable=self.remaining_var, width=16, anchor="w").pack(side=tk.LEFT)
        tk.Label(status, textvariable=self.hints_var, width=14, anchor="w").pack(side=tk.LEFT)

    # ------------------------------------------------------------------ #
    # Loading a new image
    # ------------------------------------------------------------------ #
    def on_load_image(self):
        path = filedialog.askopenfilename(
            title="Choose an image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return  # dialog was cancelled - nothing to do

        grid_size = int(self.grid_size_var.get().split(" x ")[0])

        try:
            new_board = PuzzleBoard(path, grid_size)
        except Exception as exc:
            # Covers: non-image files, unreadable/corrupt files, unusual
            # OpenCV errors - always shown to the user in a message box
            # rather than crashing the app.
            messagebox.showerror("Could not load image", str(exc))
            return

        self.board = new_board
        self.selected_index = None
        self.hint_info = None
        self.game_over = False
        self.hint_btn.config(state=tk.NORMAL)
        self.solve_btn.config(state=tk.NORMAL)

        self._redraw()

    # ------------------------------------------------------------------ #
    # Mouse handling
    # ------------------------------------------------------------------ #
    def _index_from_event(self, event):
        """Translate a canvas click into a tile index, or None if the
        click landed outside the puzzle image (handled gracefully)."""
        if self.board is None:
            return None
        edge = self.board.tile_edge
        col = event.x // edge
        row = event.y // edge
        return self.board.index_at(row, col)

    def on_left_click(self, event):
        if self.board is None or self.game_over:
            return
        index = self._index_from_event(event)
        if index is None:
            return

        if self.selected_index is None:
            self.selected_index = index
        elif self.selected_index == index:
            self.selected_index = None  # clicking the same tile deselects it
        else:
            self.board.swap(self.selected_index, index)
            self.selected_index = None
            self.hint_info = None
            self._check_completion()

        self._redraw()

    def on_shift_click(self, event):
        if self.board is None or self.game_over:
            return
        index = self._index_from_event(event)
        if index is None:
            return
        self.board.flip_tile(index, axis="horizontal")
        self.hint_info = None
        self._check_completion()
        self._redraw()

    def on_right_click(self, event):
        if self.board is None or self.game_over:
            return
        index = self._index_from_event(event)
        if index is None:
            return
        self.board.rotate_tile(index, degrees=90)
        self.hint_info = None
        self._check_completion()
        self._redraw()

    # ------------------------------------------------------------------ #
    # Hint / Solve
    # ------------------------------------------------------------------ #
    def on_hint(self):
        if self.board is None or self.game_over:
            return

        hint = self.board.use_hint()
        if hint is None:
            messagebox.showinfo(
                "No hints left", "You have used all 3 hints for this image."
            )
        else:
            self.hint_info = hint

        if self.board.hints_remaining <= 0:
            self.hint_btn.config(state=tk.DISABLED)

        self._redraw()

    def on_solve(self):
        if self.board is None:
            return
        self.board.solve()
        self.selected_index = None
        self.hint_info = None
        self.game_over = False
        self.hint_btn.config(state=tk.NORMAL)
        self._redraw()
        self._check_completion()

    # ------------------------------------------------------------------ #
    # Completion check
    # ------------------------------------------------------------------ #
    def _check_completion(self):
        if self.board.is_solved():
            self.game_over = True
            self.hint_btn.config(state=tk.DISABLED)
            self.solve_btn.config(state=tk.DISABLED)
            messagebox.showinfo(
                "Solved!",
                f"You restored the picture in {self.board.moves} moves!\n"
                "Load another image to keep playing.",
            )

    # ------------------------------------------------------------------ #
    # Drawing
    # ------------------------------------------------------------------ #
    @staticmethod
    def _to_photo(rgb_array):
        return ImageTk.PhotoImage(Image.fromarray(rgb_array))

    def _redraw(self):
        if self.board is None:
            return

        edge = self.board.tile_edge
        n = self.board.grid_size

        # --- original (reference) image ---------------------------------
        self.original_canvas.delete("all")
        self._original_photo = self._to_photo(self.board.reference_image)
        self.original_canvas.create_image(0, 0, anchor="nw", image=self._original_photo)

        if self.hint_info is not None:
            _, home_row, home_col = self.hint_info
            cx = home_col * edge + edge // 2
            cy = home_row * edge + edge // 2
            radius = edge // 4
            self.original_canvas.create_oval(
                cx - radius, cy - radius, cx + radius, cy + radius,
                outline=HINT_COLOUR, width=3,
            )

        # --- puzzle (transformed) image ----------------------------------
        self.puzzle_canvas.delete("all")
        merged = self.board.render()
        self._puzzle_photo = self._to_photo(merged)
        self.puzzle_canvas.create_image(0, 0, anchor="nw", image=self._puzzle_photo)

        # faint grid lines so tile boundaries are visible
        size = edge * n
        for i in range(1, n):
            self.puzzle_canvas.create_line(0, i * edge, size, i * edge, fill=GRID_LINE_COLOUR)
            self.puzzle_canvas.create_line(i * edge, 0, i * edge, size, fill=GRID_LINE_COLOUR)

        # green ticks on correctly placed/oriented tiles
        for index, tile in enumerate(self.board.tiles):
            row, col = divmod(index, n)
            if tile.is_correct(row, col):
                x0, y0 = col * edge, row * edge
                self.puzzle_canvas.create_text(
                    x0 + edge - 12, y0 + 12, text="✔",
                    fill=TICK_COLOUR, font=("Arial", max(10, edge // 6), "bold"),
                )

        # selection highlight
        if self.selected_index is not None:
            row, col = divmod(self.selected_index, n)
            x0, y0 = col * edge, row * edge
            self.puzzle_canvas.create_rectangle(
                x0 + 2, y0 + 2, x0 + edge - 2, y0 + edge - 2,
                outline=SELECTION_COLOUR, width=3,
            )

        # hint circle on the puzzle image itself
        if self.hint_info is not None:
            index, _, _ = self.hint_info
            row, col = divmod(index, n)
            cx = col * edge + edge // 2
            cy = row * edge + edge // 2
            radius = edge // 4
            self.puzzle_canvas.create_oval(
                cx - radius, cy - radius, cx + radius, cy + radius,
                outline=HINT_COLOUR, width=3,
            )

        # status labels
        self.moves_var.set(f"Moves: {self.board.moves}")
        self.remaining_var.set(f"Tiles left: {len(self.board.incorrect_indices())}")
        self.hints_var.set(f"Hints left: {self.board.hints_remaining}")
