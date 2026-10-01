"""
panels.py

The two picture panels of the game window.

OOP concepts demonstrated here
-------------------------------
Inheritance:
    ImagePanel (shows a picture, a faint grid and overlays)
        -> ReferencePanel     the original picture; reacts to nothing
        -> InteractivePanel   the puzzle; adds the mouse bindings

The panels know nothing about the game's rules: they draw what they are
told to and report which cell was clicked.
"""

import tkinter as tk
from collections.abc import Callable

import numpy as np
from PIL import Image, ImageTk

from ui.hit_test import pixel_to_cell
from ui.theme import CANVAS_BACKGROUND, CARD_OPTIONS, LABEL_OPTIONS

CANVAS_SIZE = 480
GRID_LINE_COLOUR = "#B0B0B0"
SELECTION_COLOUR = "#1E90FF"
HINT_COLOUR = "#00A2FF"
TICK_COLOUR = "#00C851"
OVERLAY_LINE_WIDTH = 3
SELECTION_INSET = 2     # keeps the selection border inside its own cell
TICK_MARGIN = 12        # distance of the tick from the cell's top-right corner
SHIFT_MASK = 0x0001     # bit set in event.state while Shift is held

# Canvas tags, one per kind of overlay, so each can be cleared on its own.
TAG_GRID = "grid"
TAG_TICK = "tick"
TAG_SELECT = "select"
TAG_HINT = "hint"

CellCallback = Callable[[int, int], None]


class ImagePanel(tk.Frame):
    """A titled canvas showing one square picture, centred, with a faint
    grid over it, plus overlays (ticks, selection border, hint circle)
    drawn per cell."""

    def __init__(self, parent: tk.Misc, title: str) -> None:
        """Create the panel inside `parent` as a solid card (so its title
        stays readable over the window's gradient) with `title` above the
        canvas."""
        super().__init__(parent, padx=8, pady=4, **CARD_OPTIONS)
        tk.Label(self, text=title, **LABEL_OPTIONS).pack(pady=(0, 3))
        self._canvas = tk.Canvas(
            self,
            width=CANVAS_SIZE,
            height=CANVAS_SIZE,
            bg=CANVAS_BACKGROUND,
            highlightthickness=0,
        )
        self._canvas.pack()

        # Tkinter garbage-collects a PhotoImage nobody references, which
        # blanks the canvas - so the panel holds on to it.
        self._photo: ImageTk.PhotoImage | None = None
        self._grid_size = 0
        self._image_side = 0
        self._image_left = 0
        self._image_top = 0

    @property
    def canvas(self) -> tk.Canvas:
        """The canvas the picture and overlays are drawn on."""
        return self._canvas

    def show(self, image: np.ndarray, grid_size: int) -> None:
        """Replace everything on the panel with `image` (a square RGB
        array), centred in the canvas, and draw the faint grid over it.

        Canvas coordinates start at the outer edge of the widget, under
        any border, so the border width is added to the offsets: that
        keeps the picture exactly centred in the visible area even if a
        border is added to the canvas later."""
        self._grid_size = grid_size
        self._image_side = image.shape[0]
        inset = int(self._canvas["borderwidth"]) + int(self._canvas["highlightthickness"])
        self._image_left = inset + (CANVAS_SIZE - image.shape[1]) // 2
        self._image_top = inset + (CANVAS_SIZE - image.shape[0]) // 2

        self._canvas.delete("all")
        self._photo = ImageTk.PhotoImage(Image.fromarray(image))
        self._canvas.create_image(
            self._image_left, self._image_top, anchor="nw", image=self._photo
        )
        self.draw_grid()

    def cell_at(self, x: float, y: float) -> tuple[int, int] | None:
        """The (row, col) under canvas position (x, y), or None if that
        point is outside the picture (or no picture is shown yet)."""
        return pixel_to_cell(
            x, y, self._image_left, self._image_top, self._image_side, self._grid_size
        )

    def cell_box(self, row: int, col: int) -> tuple[float, float, float, float]:
        """Canvas coordinates (x0, y0, x1, y1) of the cell at (row, col)."""
        cell = self._image_side / self._grid_size
        x0 = self._image_left + col * cell
        y0 = self._image_top + row * cell
        return x0, y0, x0 + cell, y0 + cell

    def draw_grid(self) -> None:
        """Draw faint lines along the tile boundaries."""
        left, top, side = self._image_left, self._image_top, self._image_side
        for i in range(1, self._grid_size):
            offset = i * side / self._grid_size
            self._canvas.create_line(
                left, top + offset, left + side, top + offset,
                fill=GRID_LINE_COLOUR, tags=TAG_GRID,
            )
            self._canvas.create_line(
                left + offset, top, left + offset, top + side,
                fill=GRID_LINE_COLOUR, tags=TAG_GRID,
            )

    def draw_tick(self, row: int, col: int) -> None:
        """Draw a small green tick in the top-right corner of a cell."""
        x0, y0, x1, _ = self.cell_box(row, col)
        self._canvas.create_text(
            x1 - TICK_MARGIN, y0 + TICK_MARGIN, text="✔", fill=TICK_COLOUR,
            font=("Arial", max(10, int(x1 - x0) // 6), "bold"), tags=TAG_TICK,
        )

    def draw_selection(self, row: int, col: int) -> None:
        """Draw the coloured "selected" border just inside a cell."""
        x0, y0, x1, y1 = self.cell_box(row, col)
        self._canvas.create_rectangle(
            x0 + SELECTION_INSET, y0 + SELECTION_INSET,
            x1 - SELECTION_INSET, y1 - SELECTION_INSET,
            outline=SELECTION_COLOUR, width=OVERLAY_LINE_WIDTH, tags=TAG_SELECT,
        )

    def draw_hint(self, row: int, col: int) -> None:
        """Draw the blue hint circle in the middle of a cell."""
        x0, y0, x1, y1 = self.cell_box(row, col)
        radius = (x1 - x0) / 4
        centre_x, centre_y = (x0 + x1) / 2, (y0 + y1) / 2
        self._canvas.create_oval(
            centre_x - radius, centre_y - radius, centre_x + radius, centre_y + radius,
            outline=HINT_COLOUR, width=OVERLAY_LINE_WIDTH, tags=TAG_HINT,
        )

    def clear(self, tag: str) -> None:
        """Remove every overlay drawn with `tag` (one of the TAG_ names)."""
        self._canvas.delete(tag)


class ReferencePanel(ImagePanel):
    """The original picture. It has no mouse bindings at all: it is there
    to be looked at, not clicked."""


class InteractivePanel(ImagePanel):
    """The puzzle picture. Turns mouse clicks into "this cell was
    left-clicked / right-clicked / shift-clicked" callbacks; clicks that
    miss the picture are ignored."""

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        on_left: CellCallback,
        on_right: CellCallback,
        on_shift_left: CellCallback,
    ) -> None:
        """Each callback receives the (row, col) of the clicked cell."""
        super().__init__(parent, title)
        self._on_left = on_left
        self._on_right = on_right
        self._on_shift_left = on_shift_left

        self._canvas.bind("<Button-1>", self.left_click)
        self._canvas.bind("<Shift-Button-1>", self.shift_click)
        self._canvas.bind("<Button-3>", self.right_click)
        if self.tk.call("tk", "windowingsystem") == "aqua":
            # macOS delivers right clicks as Button-2 or Control + click.
            self._canvas.bind("<Button-2>", self.right_click)
            self._canvas.bind("<Control-Button-1>", self.right_click)

    def left_click(self, event: tk.Event) -> None:
        """Handle a plain left click. A Shift + left click can reach this
        handler too; it is passed on as a shift click, never as a plain
        one."""
        if event.state & SHIFT_MASK:
            self.shift_click(event)
        else:
            self._dispatch(event, self._on_left)

    def shift_click(self, event: tk.Event) -> None:
        """Handle a Shift + left click."""
        self._dispatch(event, self._on_shift_left)

    def right_click(self, event: tk.Event) -> None:
        """Handle a right click."""
        self._dispatch(event, self._on_right)

    def _dispatch(self, event: tk.Event, callback: CellCallback) -> None:
        """Call `callback` with the clicked cell, if the click hit one."""
        cell = self.cell_at(event.x, event.y)
        if cell is not None:
            callback(*cell)
