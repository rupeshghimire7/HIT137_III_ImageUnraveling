# ====================================================================== #
#  File         : src/models/tile.py
#  Project      : ImageUnraveling - HIT137 Assignment 3
#
#  Student name : Hemanta Adhikari
#  Student ID   : S403355  
#  Layer        : Core OOP models
#  Unit tests   : tests/test_tile.py
# ====================================================================== #
"""
tile.py - a single square piece of the puzzle image.

A Tile stores its pixels, the grid cell it belongs in (its "home") and
its current orientation (rotation / mirror) since the puzzle was
scrambled.

OOP concepts demonstrated
-------------------------
Encapsulation
    The pixels, home cell and orientation are "private" attributes
    (leading underscore). They can only be changed through the public
    methods rotate(), flip_horizontal(), flip_vertical() and reset(),
    and are read through read-only properties.

How orientation is stored
-------------------------
Every mix of rotations and flips of a square is one of only 8
orientations, so a tile keeps just two values:

    _rotation : 0, 90, 180 or 270   (clockwise degrees)
    _mirrored : True if the original is mirrored left-right
                *before* rotating

The displayed tile is always "mirror first (if mirrored), then rotate".
Each method updates these two values so the change is exactly what the
player sees on screen - e.g. flip_horizontal() mirrors the tile *as
currently displayed*, even if it is already rotated. This is why the
player's two actions (rotate 90° clockwise, flip horizontally) can always
bring any tile back to its correct orientation.
"""

import cv2
import numpy as np

# --- Angle constants (degrees) ----------------------------------------- #
RIGHT_ANGLE = 90
HALF_TURN = 180
FULL_TURN = 360

# OpenCV rotation code for each clockwise rotation (0 needs no rotation).
_ROTATE_CODES = {
    90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}

_MIRROR_LEFT_RIGHT = 1  # cv2.flip() code for a left-right mirror


class Tile:
    """A single piece of the puzzle image."""

    # ------------------------------------------------------------------ #
    # Constructor
    # ------------------------------------------------------------------ #
    def __init__(self, image: np.ndarray, home_row: int, home_col: int):
        """Create a tile in its original, untransformed orientation.

        Parameters
        ----------
        image : numpy.ndarray
            RGB pixels of this tile in its ORIGINAL orientation. The array
            is never modified - every rotation/flip is rendered fresh from
            it, so undoing moves can never drift from the true pixels.
        home_row, home_col : int
            The grid cell this tile belongs in when the picture is solved.

        Raises
        ------
        ValueError
            If the image is empty or the home cell is negative.
        """
        if image is None or image.size == 0:
            raise ValueError("A tile needs a non-empty image.")
        if home_row < 0 or home_col < 0:
            raise ValueError("A tile's home row/column cannot be negative.")

        self._original_image = image
        self._home_row = home_row
        self._home_col = home_col

        # Orientation state - changed only through the methods below.
        self._rotation = 0        # clockwise degrees: 0, 90, 180 or 270
        self._mirrored = False    # mirrored left-right before rotating

    # ------------------------------------------------------------------ #
    # State-changing methods
    # ------------------------------------------------------------------ #
    def rotate(self, degrees: int) -> None:
        """Rotate clockwise by `degrees`, a multiple of 90.

        Use a negative value to rotate anticlockwise (e.g. to undo a
        rotation).

        Raises
        ------
        ValueError
            If `degrees` is not a multiple of 90.
        """
        if degrees % RIGHT_ANGLE != 0:
            raise ValueError("Tiles can only be rotated in steps of 90 degrees.")
        self._rotation = (self._rotation + degrees) % FULL_TURN

    def flip_horizontal(self) -> None:
        """Mirror the tile left-right, as it is currently displayed.

        Mirroring reverses the direction of any rotation already applied,
        so the stored rotation is negated as the mirror flag toggles.
        """
        self._rotation = (FULL_TURN - self._rotation) % FULL_TURN
        self._mirrored = not self._mirrored

    def flip_vertical(self) -> None:
        """Mirror the tile top-bottom, as it is currently displayed.

        A vertical flip equals a horizontal flip followed by a 180° turn,
        which gives the update rule below.
        """
        self._rotation = (FULL_TURN + HALF_TURN - self._rotation) % FULL_TURN
        self._mirrored = not self._mirrored

    def reset(self) -> None:
        """Return this tile to its original, untransformed orientation."""
        self._rotation = 0
        self._mirrored = False

    # ------------------------------------------------------------------ #
    # Read-only properties
    # ------------------------------------------------------------------ #
    @property
    def home_row(self) -> int:
        """Row of the cell this tile belongs in."""
        return self._home_row

    @property
    def home_col(self) -> int:
        """Column of the cell this tile belongs in."""
        return self._home_col

    @property
    def rotation(self) -> int:
        """Current clockwise rotation in degrees (0, 90, 180 or 270)."""
        return self._rotation

    @property
    def is_mirrored(self) -> bool:
        """True if the tile is currently mirrored (before rotation)."""
        return self._mirrored

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #
    def get_display_image(self) -> np.ndarray:
        """Return the tile's pixels with its current orientation applied.

        Mirror first (if mirrored), then rotate clockwise. The stored
        original is never changed - a fresh copy is produced every call.
        """
        image = self._original_image

        if self._mirrored:
            image = cv2.flip(image, _MIRROR_LEFT_RIGHT)

        rotate_code = _ROTATE_CODES.get(self._rotation)
        if rotate_code is not None:
            image = cv2.rotate(image, rotate_code)

        return image

    def is_correct(self, current_row: int, current_col: int) -> bool:
        """True only when the tile sits in its home cell AND is in its
        original orientation (no rotation, not mirrored)."""
        at_home = (current_row, current_col) == (self._home_row, self._home_col)
        upright = self._rotation == 0 and not self._mirrored
        return at_home and upright

    def __repr__(self) -> str:
        return (
            f"Tile(home=({self._home_row},{self._home_col}), "
            f"rotation={self._rotation}, mirrored={self._mirrored})"
        )