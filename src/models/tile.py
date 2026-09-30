"""
tile.py

Defines the Tile class: a single square piece cut out of the source image,
together with the orientation state (rotation / mirror) that has been
applied to it since the puzzle was scrambled.

OOP concepts demonstrated here
-------------------------------
Encapsulation:
    The tile's pixel data, home cell and orientation are stored as
    "private" attributes (leading underscore) and can only be changed
    through the methods below (rotate, flip_horizontal, flip_vertical,
    reset). Outside code never reaches in and edits self._rotation directly.

How orientation is stored
-------------------------
Every combination of rotations and flips of a square is one of only 8
orientations, so the tile keeps just two values:

    _rotation : 0, 90, 180 or 270 (clockwise degrees)
    _mirrored : True if the original is mirrored left-right *before*
                rotating

The displayed tile is always "mirror first (if _mirrored), then rotate".
Every method updates these two values so that the change is exactly what
the player sees on screen - e.g. flip_horizontal() always flips the tile
left-right *as currently displayed*, even if it is already rotated. This
also means the player's two actions (rotate 90 degrees clockwise and flip
horizontally) can always return any tile to its correct orientation.
"""

import cv2

RIGHT_ANGLE = 90
FULL_TURN = 360


class Tile:
    """A single piece of the puzzle image."""

    def __init__(self, image, home_row, home_col):
        """
        Parameters
        ----------
        image : numpy.ndarray
            RGB pixel data for this tile in its ORIGINAL orientation.
            This array is never modified in place - every rotation/flip is
            produced fresh from it, so undoing a sequence of moves can
            never "drift" away from the true original pixels.
        home_row, home_col : int
            The row/column this tile belongs to when the picture is fully
            solved (its "home").

        Raises ValueError if the image is empty or the home cell is
        negative.
        """
        if image is None or image.size == 0:
            raise ValueError("A tile needs a non-empty image.")
        if home_row < 0 or home_col < 0:
            raise ValueError("A tile's home row/column cannot be negative.")

        self._original_image = image
        self._home_row = home_row
        self._home_col = home_col

        # Orientation state - changed only through the methods below.
        self._rotation = 0       # clockwise degrees: 0, 90, 180 or 270
        self._mirrored = False   # mirrored left-right before rotating

    # ------------------------------------------------------------------ #
    # State-changing methods
    # ------------------------------------------------------------------ #
    def rotate(self, degrees):
        """Rotate clockwise by `degrees`, a multiple of 90 (use a negative
        value to rotate anticlockwise, e.g. when undoing a rotation).

        Raises ValueError if `degrees` is not a multiple of 90.
        """
        if degrees % RIGHT_ANGLE != 0:
            raise ValueError("Tiles can only be rotated in steps of 90 degrees.")
        self._rotation = (self._rotation + degrees) % FULL_TURN

    def flip_horizontal(self):
        """Mirror the tile left-right, as it is currently displayed.

        Mirroring reverses the direction of any rotation already applied,
        so the stored rotation is negated as the mirror flag toggles.
        """
        self._rotation = (FULL_TURN - self._rotation) % FULL_TURN
        self._mirrored = not self._mirrored

    def flip_vertical(self):
        """Mirror the tile top-bottom, as it is currently displayed.

        A vertical flip equals a horizontal flip followed by a 180 degree
        rotation, which gives the update rule below.
        """
        self._rotation = (FULL_TURN + 180 - self._rotation) % FULL_TURN
        self._mirrored = not self._mirrored

    def reset(self):
        """Return this tile to its original, untransformed state."""
        self._rotation = 0
        self._mirrored = False

    # ------------------------------------------------------------------ #
    # Read-only access
    # ------------------------------------------------------------------ #
    @property
    def home_row(self):
        """Row of the cell this tile belongs in."""
        return self._home_row

    @property
    def home_col(self):
        """Column of the cell this tile belongs in."""
        return self._home_col

    @property
    def rotation(self):
        """Current clockwise rotation in degrees (0, 90, 180 or 270)."""
        return self._rotation

    @property
    def is_mirrored(self):
        """True if the tile is currently mirrored (before rotation)."""
        return self._mirrored

    def get_display_image(self):
        """Return this tile's pixels with its current orientation baked
        in: mirror first (if mirrored), then rotate clockwise. The stored
        original image is never mutated - a fresh transformed copy is
        produced every time this is called."""
        img = self._original_image

        if self._mirrored:
            img = cv2.flip(img, 1)

        if self._rotation == 90:
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif self._rotation == 180:
            img = cv2.rotate(img, cv2.ROTATE_180)
        elif self._rotation == 270:
            img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

        return img

    def is_correct(self, current_row, current_col):
        """A tile counts as 'correct' only when it is sitting in its home
        cell AND is in its original orientation."""
        return (
            current_row == self._home_row
            and current_col == self._home_col
            and self._rotation == 0
            and not self._mirrored
        )

    def __repr__(self):
        return (
            f"Tile(home=({self._home_row},{self._home_col}), "
            f"rotation={self._rotation}, mirrored={self._mirrored})"
        )
