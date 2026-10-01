"""
theme.py

The look of the game window: a slowly flowing "aurora" gradient behind
everything, and light "cards" that every piece of text sits on.

Readability rule: no text is ever drawn straight onto the gradient. The
toolbar, the panel titles and the status bar are solid cards whose text
colours are dark shades taken from the gradient itself, so they match
the background but always keep a high contrast (about 15:1 for body
text), whatever colour is flowing behind them.

OOP concepts demonstrated here
-------------------------------
Inheritance:
    tk.Canvas -> GradientBackground   a canvas that paints and animates
                                      the gradient underneath its siblings
"""

import tkinter as tk
from tkinter import ttk

import numpy as np
from PIL import Image, ImageTk

# --- Gradient --------------------------------------------------------- #
#: Colour stops of the aurora: midnight blue -> violet -> plum -> rose ->
#: apricot. The gradient runs through them and back again, so it loops
#: without a visible seam.
GRADIENT_STOPS = ("#1B1F6B", "#4B2A99", "#9C2F8F", "#E2557A", "#F59E6B")
GRADIENT_PERIOD = 1400      # pixels for one full loop of the colours
GRADIENT_SLANT = 0.55       # how diagonal the colour bands are
GRADIENT_SHADE = 0.18       # the bottom edge is this much darker than the top
GRADIENT_STEP = 2           # pixels the gradient flows per frame
GRADIENT_FRAME_MS = 45      # time between frames (about 22 frames a second)

# --- Cards and text (dark text on light cards, from the same palette) -- #
CARD_BG = "#FBF8FF"
CARD_BORDER = "#D8CCF5"
TEXT_COLOUR = "#1F1846"
TEXT_MUTED = "#5A5280"
BUTTON_BG = "#EDE6FF"
BUTTON_ACTIVE_BG = "#DCCFFF"
BUTTON_TEXT = "#2B1F66"
BUTTON_DISABLED_TEXT = "#9A93B8"
FIELD_BG = "#FFFFFF"
FIELD_SELECT_BG = "#DCCFFF"
CANVAS_BACKGROUND = GRADIENT_STOPS[0]

#: Options for the solid card frames that hold text.
CARD_OPTIONS = {
    "bg": CARD_BG,
    "highlightbackground": CARD_BORDER,
    "highlightthickness": 1,
}
#: Options for labels placed on a card.
LABEL_OPTIONS = {"bg": CARD_BG, "fg": TEXT_COLOUR}
#: Options for buttons placed on a card. Only light background colours
#: are used, so the dark text stays readable even on macOS, which ignores
#: a button's background colour.
BUTTON_OPTIONS = {
    "bg": BUTTON_BG,
    "fg": BUTTON_TEXT,
    "activebackground": BUTTON_ACTIVE_BG,
    "activeforeground": BUTTON_TEXT,
    "disabledforeground": BUTTON_DISABLED_TEXT,
    "highlightbackground": CARD_BG,
    "relief": tk.FLAT,
    "padx": 10,
    "pady": 3,
    "cursor": "hand2",
}


def _hex_to_rgb(colour: str) -> tuple[int, int, int]:
    """'#RRGGBB' as an (r, g, b) tuple."""
    return int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16)


def gradient_colours(period: int = GRADIENT_PERIOD) -> np.ndarray:
    """A (period, 3) uint8 table: the colour at each step of one loop,
    going through GRADIENT_STOPS and back so the last colour flows
    smoothly into the first."""
    stops = [_hex_to_rgb(colour) for colour in GRADIENT_STOPS]
    loop = np.array(stops + stops[-2:0:-1] + stops[:1], dtype=np.float32)
    positions = np.linspace(0, len(loop) - 1, period, endpoint=False)
    channels = [
        np.interp(positions, np.arange(len(loop)), loop[:, channel]) for channel in range(3)
    ]
    return np.stack(channels, axis=1).round().astype(np.uint8)


def gradient_image(width: int, height: int, period: int = GRADIENT_PERIOD) -> np.ndarray:
    """A (height, width, 3) RGB image of diagonal colour bands that
    repeats exactly every `period` pixels across, so a strip of it can
    be slid sideways and wrapped around with no seam."""
    table = gradient_colours(period)
    xs = np.arange(width)[np.newaxis, :]
    ys = np.arange(height)[:, np.newaxis]
    band = (xs + (ys * GRADIENT_SLANT).astype(int)) % period
    image = table[band].astype(np.float32)
    shade = 1.0 - GRADIENT_SHADE * np.arange(height) / max(1, height - 1)
    return (image * shade[:, np.newaxis, np.newaxis]).round().astype(np.uint8)


def style_widgets(root: tk.Misc) -> None:
    """Give the ttk dropdowns (and their pop-up lists) the card colours."""
    style = ttk.Style(root)
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", FIELD_BG)],
        foreground=[("readonly", TEXT_COLOUR)],
        selectbackground=[("readonly", FIELD_BG)],
        selectforeground=[("readonly", TEXT_COLOUR)],
    )
    root.option_add("*TCombobox*Listbox.background", FIELD_BG)
    root.option_add("*TCombobox*Listbox.foreground", TEXT_COLOUR)
    root.option_add("*TCombobox*Listbox.selectBackground", FIELD_SELECT_BG)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT_COLOUR)


class GradientBackground(tk.Canvas):
    """Fills its parent with the flowing gradient.

    It is placed over the whole parent and must be the parent's FIRST
    child: Tk stacks sibling widgets in the order they are created, so
    every widget created after it is drawn on top and the gradient only
    shows in the gaps between them.

    The gradient is drawn once, one loop wider than the window; each
    frame just slides that picture a little to the left and wraps it
    round, so the animation costs almost nothing.
    """

    def __init__(self, parent: tk.Misc) -> None:
        """Cover `parent` and start flowing."""
        super().__init__(parent, highlightthickness=0, borderwidth=0, bg=GRADIENT_STOPS[0])
        self._photo: ImageTk.PhotoImage | None = None
        self._item: int | None = None
        self._size = (0, 0)
        self._offset = 0
        self.place(x=0, y=0, relwidth=1, relheight=1)
        self.bind("<Configure>", self._on_resize)
        self._after_id: str | None = self.after(GRADIENT_FRAME_MS, self._flow)

    def _on_resize(self, event: tk.Event) -> None:
        """Redraw the gradient strip whenever the window's size changes."""
        size = (event.width, event.height)
        if size == self._size or min(size) <= 1:
            return
        self._size = size
        strip = gradient_image(event.width + GRADIENT_PERIOD, event.height)
        self._photo = ImageTk.PhotoImage(Image.fromarray(strip))
        if self._item is None:
            self._item = self.create_image(-self._offset, 0, anchor="nw", image=self._photo)
        else:
            self.itemconfigure(self._item, image=self._photo)

    def _flow(self) -> None:
        """Slide the gradient one step and schedule the next frame."""
        self._offset = (self._offset + GRADIENT_STEP) % GRADIENT_PERIOD
        if self._item is not None:
            self.coords(self._item, -self._offset, 0)
        self._after_id = self.after(GRADIENT_FRAME_MS, self._flow)

    def destroy(self) -> None:
        """Stop the animation before the canvas goes away."""
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None
        super().destroy()
