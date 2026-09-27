"""
tile.py

Defines the Tile class: a single square piece cut out of the source image,
together with the orientation state (rotation / flips) that has been
applied to it since the puzzle was scrambled.

OOP concepts demonstrated here
-------------------------------
Encapsulation:
    The tile's pixel data and orientation flags are stored as "private"
    attributes (leading underscore) and can only be changed through the
    methods below (rotate, flip_horizontal, flip_vertical, reset). Outside
    code never reaches in and edits self._rotation directly.
"""

import cv2


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
        """
        self._original_image = image
        self.home_row = home_row
        self.home_col = home_col

        # Orientation state - changed only through the methods below.
        self._rotation = 0      # clockwise degrees: 0, 90, 180 or 270
        self._flip_h = False    # left-right flip toggled on/off
        self._flip_v = False    # up-down flip toggled on/off

    # ------------------------------------------------------------------ #
    # State-changing methods
    # ------------------------------------------------------------------ #
    def rotate(self, degrees):
        """Rotate clockwise by `degrees` (use a negative value to rotate
        anticlockwise, e.g. when undoing a previous rotation)."""
        self._rotation = (self._rotation + degrees) % 360

    def flip_horizontal(self):
        """Toggle a left-right flip."""
        self._flip_h = not self._flip_h

    def flip_vertical(self):
        """Toggle an up-down flip."""
        self._flip_v = not self._flip_v

    def reset(self):
        """Return this tile to its original, untransformed state."""
        self._rotation = 0
        self._flip_h = False
        self._flip_v = False

    # ------------------------------------------------------------------ #
    # Read-only access
    # ------------------------------------------------------------------ #
    @property
    def rotation(self):
        return self._rotation

    @property
    def is_flipped_h(self):
        return self._flip_h

    @property
    def is_flipped_v(self):
        return self._flip_v

    def get_display_image(self):
        """Return this tile's pixels with its current rotation/flip state
        baked in. The stored original image is never mutated - a fresh
        transformed copy is produced every time this is called."""
        img = self._original_image

        if self._flip_h:
            img = cv2.flip(img, 1)
        if self._flip_v:
            img = cv2.flip(img, 0)

        if self._rotation == 90:
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif self._rotation == 180:
            img = cv2.rotate(img, cv2.ROTATE_180)
        elif self._rotation == 270:
            img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

        return img

    def is_correct(self, current_row, current_col):
        """A tile counts as 'correct' only when it is sitting in its home
        cell AND has no residual rotation/flip applied."""
        return (
            current_row == self.home_row
            and current_col == self.home_col
            and self._rotation == 0
            and not self._flip_h
            and not self._flip_v
        )

    def __repr__(self):
        return (
            f"Tile(home=({self.home_row},{self.home_col}), "
            f"rotation={self._rotation}, flip_h={self._flip_h}, flip_v={self._flip_v})"
        )
