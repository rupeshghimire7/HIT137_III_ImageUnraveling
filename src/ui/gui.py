"""
gui.py

The Tkinter front-end for the ImageUnraveling tile puzzle: the main
window and the controller that connects the widgets to the model. Every
game rule lives in the engine and models packages, so this file's job is
just to draw things and turn clicks into calls on PuzzleBoard.

Controls
--------
Left click a tile      - select it (coloured border). Click a second tile
                         to swap the two. Click the same tile again to
                         deselect it.
Right click a tile     - rotate it 90 degrees clockwise.
Shift + left click     - flip it horizontally.
Hint button            - highlights one wrong tile (max 3 per image).
Solve button           - instantly restores the picture.
"""

import logging
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from types import TracebackType

from engine.fit_strategy import DEFAULT_FIT_MODE, FIT_STRATEGIES
from engine.image_processor import ImageLoadError
from engine.puzzle_board import MAX_HINTS, SUPPORTED_GRID_SIZES, PuzzleBoard
from engine.scoring import MAX_STARS
from models.transformations import HORIZONTAL
from ui.panels import TAG_HINT, InteractivePanel, ReferencePanel

logger = logging.getLogger(__name__)

TIMER_INTERVAL_MS = 1000
LEGEND_COLOUR = "#555555"
STAR_FILLED = "★"
STAR_EMPTY = "☆"
CONTROLS_LEGEND = (
    "Left click: select / swap / deselect   ·   Right click: rotate 90° clockwise"
    "   ·   Shift + left click: flip horizontally"
)
STATUS_WELCOME = "Choose a grid size, then load an image to start."
STATUS_PLAYING = "Restore the picture!"
STATUS_WON = "Solved! Load a new image to play again."
STATUS_AUTO_SOLVED = "Auto-solved. Load a new image to play again."
STATUS_SETTING_CHANGED = "The new grid size / fit mode will be used for the next image you load."


def grid_label(grid_size: int) -> str:
    """Text shown in the grid-size dropdown, e.g. "3 x 3"."""
    return f"{grid_size} x {grid_size}"


def format_time(seconds: int) -> str:
    """Seconds as mm:ss."""
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class PuzzleGameApp(tk.Frame):
    """Main application window / controller."""

    def __init__(self, master: tk.Tk) -> None:
        """Build the window inside `master` and wait for an image."""
        super().__init__(master)
        self.master = master
        master.title("ImageUnraveling - HIT137 Assignment 3")
        master.resizable(False, False)
        # Any unexpected error inside a button/click handler is shown in a
        # message box instead of silently breaking the app.
        master.report_callback_exception = self._report_callback_exception

        self.board: PuzzleBoard | None = None
        self.selected_index: int | None = None
        self.hint_info: tuple[int, int, int] | None = None   # (tile_index, home_row, home_col)
        self.game_over = False

        self._build_widgets()
        self.pack()
        self._tick()

    # ------------------------------------------------------------------ #
    # Widget construction
    # ------------------------------------------------------------------ #
    def _build_widgets(self) -> None:
        self._build_toolbar()

        images_frame = tk.Frame(self)
        images_frame.grid(row=1, column=0, padx=10)
        self.original_panel = ReferencePanel(images_frame, "Original (reference only)")
        self.original_panel.pack(side=tk.LEFT, padx=(0, 10))
        # Only the transformed/right-hand panel responds to clicks.
        self.puzzle_panel = InteractivePanel(
            images_frame,
            "Puzzle (click to solve)",
            on_left=self.on_tile_left,
            on_right=self.on_tile_right,
            on_shift_left=self.on_tile_shift_left,
        )
        self.puzzle_panel.pack(side=tk.LEFT)

        self._build_status_bar()

    def _build_toolbar(self) -> None:
        controls = tk.Frame(self)
        controls.grid(row=0, column=0, sticky="ew", padx=10, pady=8)

        self.load_btn = tk.Button(
            controls, text="Load Image...", command=self.on_load_image
        )
        self.load_btn.pack(side=tk.LEFT, padx=(0, 12))

        tk.Label(controls, text="Grid size:").pack(side=tk.LEFT)
        self.grid_size_var = tk.StringVar(value=grid_label(SUPPORTED_GRID_SIZES[0]))
        self.grid_size_combo = ttk.Combobox(
            controls,
            textvariable=self.grid_size_var,
            state="readonly",
            width=8,
            values=[grid_label(size) for size in SUPPORTED_GRID_SIZES],
        )
        self.grid_size_combo.pack(side=tk.LEFT, padx=(4, 12))

        tk.Label(controls, text="Fit:").pack(side=tk.LEFT)
        self.fit_mode_var = tk.StringVar(value=DEFAULT_FIT_MODE)
        self.fit_mode_combo = ttk.Combobox(
            controls,
            textvariable=self.fit_mode_var,
            state="readonly",
            width=6,
            values=list(FIT_STRATEGIES),
        )
        self.fit_mode_combo.pack(side=tk.LEFT, padx=(4, 20))

        for combo in (self.grid_size_combo, self.fit_mode_combo):
            combo.bind("<<ComboboxSelected>>", self.on_setting_changed)

        self.hint_btn = tk.Button(
            controls, text=f"Hint ({MAX_HINTS})", command=self.on_hint, state=tk.DISABLED
        )
        self.hint_btn.pack(side=tk.LEFT, padx=4)

        self.solve_btn = tk.Button(
            controls, text="Solve", command=self.on_solve, state=tk.DISABLED
        )
        self.solve_btn.pack(side=tk.LEFT, padx=4)

    def _build_status_bar(self) -> None:
        counters = tk.Frame(self)
        counters.grid(row=2, column=0, sticky="ew", padx=10, pady=(8, 0))

        self.moves_var = tk.StringVar(value="Moves: 0")
        self.remaining_var = tk.StringVar(value="Tiles left: -")
        self.time_var = tk.StringVar(value="Time: 00:00")
        self.score_var = tk.StringVar(value="Score: -")
        for variable in (self.moves_var, self.remaining_var, self.time_var, self.score_var):
            tk.Label(counters, textvariable=variable, width=16, anchor="w").pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value=STATUS_WELCOME)
        tk.Label(self, textvariable=self.status_var, anchor="w").grid(
            row=3, column=0, sticky="ew", padx=10, pady=(4, 0)
        )
        tk.Label(self, text=CONTROLS_LEGEND, fg=LEGEND_COLOUR).grid(
            row=4, column=0, sticky="w", padx=10, pady=(4, 8)
        )

    # ------------------------------------------------------------------ #
    # Loading a new image
    # ------------------------------------------------------------------ #
    def on_load_image(self) -> None:
        """Load Image button: ask for a file and start a new round."""
        path = filedialog.askopenfilename(
            title="Choose an image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return  # dialog was cancelled - nothing to do
        self.load_image_file(path)

    def load_image_file(self, path: str) -> None:
        """Start a new round from `path` using the chosen grid size and
        fit mode. If the file cannot be loaded, an error box is shown and
        the current round (if any) keeps running untouched."""
        grid_size = int(self.grid_size_var.get().split(" x ")[0])

        # The new round is built completely before it replaces the old
        # one, so a failed load never destroys the game in progress.
        try:
            new_board = PuzzleBoard(path, grid_size, fit_mode=self.fit_mode_var.get())
        except ImageLoadError as exc:
            # Missing, non-image, corrupt or too-small files: the message
            # is written for the player.
            messagebox.showerror("Could not load image", str(exc))
            return
        except Exception:
            logger.exception("Unexpected error while loading %s", path)
            messagebox.showerror(
                "Could not load image",
                "Something went wrong while loading that image.\n"
                "Please try a different file.",
            )
            return

        self.board = new_board
        self.selected_index = None
        self.hint_info = None
        self.game_over = False
        self.hint_btn.config(state=tk.NORMAL)
        self.solve_btn.config(state=tk.NORMAL)
        self.status_var.set(STATUS_PLAYING)

        self.original_panel.show(new_board.reference_image, grid_size)
        self._redraw()

    def on_setting_changed(self, _event: tk.Event | None = None) -> None:
        """Grid size or fit mode changed: it only applies to the next
        load, so say so if a round is in progress."""
        if self.board is not None and not self.game_over:
            self.status_var.set(STATUS_SETTING_CHANGED)

    # ------------------------------------------------------------------ #
    # Tile clicks (reported by the puzzle panel as a row and column)
    # ------------------------------------------------------------------ #
    def _playable_index(self, row: int, col: int) -> int | None:
        """The tile index at (row, col), or None if no round is running."""
        if self.board is None or self.game_over:
            return None
        return self.board.index_at(row, col)

    def on_tile_left(self, row: int, col: int) -> None:
        """Left click: select a tile, deselect it, or swap it with the
        tile already selected."""
        index = self._playable_index(row, col)
        if index is None:
            return

        if self.selected_index is None:
            self.selected_index = index
            self._redraw()
        elif self.selected_index == index:
            self.selected_index = None  # clicking the same tile deselects it
            self._redraw()
        else:
            self.board.swap(self.selected_index, index)
            self._after_move()

    def on_tile_right(self, row: int, col: int) -> None:
        """Right click: rotate the tile 90 degrees clockwise."""
        index = self._playable_index(row, col)
        if index is None:
            return
        self.board.rotate_tile(index, degrees=90)
        self._after_move()

    def on_tile_shift_left(self, row: int, col: int) -> None:
        """Shift + left click: flip the tile horizontally."""
        index = self._playable_index(row, col)
        if index is None:
            return
        self.board.flip_tile(index, axis=HORIZONTAL)
        self._after_move()

    def _after_move(self) -> None:
        """Runs after every swap, rotate or flip: the selection and any
        hint circles go, the picture is redrawn, and a finished puzzle is
        announced."""
        self.selected_index = None
        self.hint_info = None
        if self.status_var.get() == STATUS_SETTING_CHANGED:
            self.status_var.set(STATUS_PLAYING)
        self._redraw()
        if self.board.is_solved():
            self._complete(auto_solved=False)

    # ------------------------------------------------------------------ #
    # Hint / Solve / completion
    # ------------------------------------------------------------------ #
    def on_hint(self) -> None:
        """Hint button: circle one incorrect tile on the puzzle and its
        home cell on the original."""
        if self.board is None or self.game_over:
            return
        hint = self.board.use_hint()
        if hint is None:
            return
        self.hint_info = hint
        self._redraw()

    def on_solve(self) -> None:
        """Solve button: restore the picture and end the round."""
        if self.board is None or self.game_over:
            return
        self.board.solve()
        self.selected_index = None
        self.hint_info = None
        self._redraw()
        self._complete(auto_solved=True)

    def _complete(self, auto_solved: bool) -> None:
        """End the round: lock all puzzle input until a new image is
        loaded, then tell the player how it ended."""
        self.game_over = True
        self.hint_btn.config(state=tk.DISABLED)
        self.solve_btn.config(state=tk.DISABLED)

        if auto_solved:
            self.status_var.set(STATUS_AUTO_SOLVED)
            messagebox.showinfo(
                "Solved",
                "The puzzle was solved automatically, so the moves and score "
                "were cleared.\nLoad another image to keep playing.",
            )
            return

        state = self.board.state
        stars = state.stars()
        self.status_var.set(STATUS_WON)
        messagebox.showinfo(
            "Solved!",
            f"You restored the picture in {state.moves} moves!\n\n"
            f"Time: {format_time(state.elapsed_seconds())}\n"
            f"Score: {state.score()}\n"
            f"Rating: {STAR_FILLED * stars}{STAR_EMPTY * (MAX_STARS - stars)}\n\n"
            "Load another image to keep playing.",
        )

    def _report_callback_exception(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None:
        """Tkinter calls this for any error raised inside a handler."""
        logger.error("Unexpected error", exc_info=(exc_type, exc_value, exc_traceback))
        messagebox.showerror(
            "Something went wrong",
            f"{exc_value}\n\nYou can keep playing or load a new image.",
        )

    # ------------------------------------------------------------------ #
    # Drawing
    # ------------------------------------------------------------------ #
    def _redraw(self) -> None:
        """Redraw the puzzle and every overlay, in the order image, grid,
        ticks, selection, hint, then refresh the counters."""
        if self.board is None:
            return
        n = self.board.grid_size

        self.puzzle_panel.show(self.board.render(), n)
        for index, tile in enumerate(self.board.tiles):
            row, col = divmod(index, n)
            if tile.is_correct(row, col):
                self.puzzle_panel.draw_tick(row, col)
        if self.selected_index is not None:
            self.puzzle_panel.draw_selection(*divmod(self.selected_index, n))

        # A hint marks the tile where it is now (puzzle) and where it
        # belongs (original).
        self.original_panel.clear(TAG_HINT)
        if self.hint_info is not None:
            index, home_row, home_col = self.hint_info
            self.puzzle_panel.draw_hint(*divmod(index, n))
            self.original_panel.draw_hint(home_row, home_col)

        self._update_status()

    def _update_status(self) -> None:
        """Refresh the counters and the Hint button from the model."""
        state = self.board.state
        self.moves_var.set(f"Moves: {state.moves}")
        self.remaining_var.set(f"Tiles left: {len(self.board.incorrect_indices())}")
        self.time_var.set(f"Time: {format_time(state.elapsed_seconds())}")
        self.score_var.set(f"Score: {state.score()}")
        self.hint_btn.config(text=f"Hint ({state.hints_left})")
        if state.hints_left <= 0:
            self.hint_btn.config(state=tk.DISABLED)

    def _tick(self) -> None:
        """Keep the time and score on screen current while a round runs."""
        if self.board is not None and not self.game_over:
            self._update_status()
        self.after(TIMER_INTERVAL_MS, self._tick)
