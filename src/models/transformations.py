"""
transformations.py

Implements the puzzle's three transformation types (swap / rotate / flip)
as a small class hierarchy, following the "command" pattern: every
transformation knows how to apply() itself to a PuzzleBoard and how to
undo() itself again, exactly reversing that effect.

OOP concepts demonstrated here
-------------------------------
Inheritance:
    Transformation (abstract base)
        -> TileTransformation (abstract - acts on one tile)
            -> RotateTransformation
            -> FlipTransformation
        -> SwapTransformation (acts on two tiles directly)

Polymorphism:
    PuzzleBoard.solve() and the scrambler both keep a plain list of
    Transformation objects and call .apply() / .undo() on each one without
    ever checking *which* concrete subclass it is. The right behaviour
    happens automatically because each subclass overrides apply()/undo().
"""

import random
from abc import ABC, abstractmethod


class Transformation(ABC):
    """Base class for anything that can be applied to, and later undone
    from, a PuzzleBoard."""

    def __init__(self, board):
        self.board = board

    @abstractmethod
    def apply(self):
        """Perform the transformation on self.board."""

    @abstractmethod
    def undo(self):
        """Exactly reverse the effect of apply()."""

    @abstractmethod
    def describe(self):
        """Short, human-readable description (handy for debugging)."""

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.describe()}>"


class TileTransformation(Transformation):
    """A transformation that acts on a single tile, identified by that
    tile's current index/position in the board's tile list."""

    def __init__(self, board, tile_index):
        super().__init__(board)
        self.tile_index = tile_index

    @property
    def tile(self):
        return self.board.tiles[self.tile_index]


class RotateTransformation(TileTransformation):
    """Rotates one tile clockwise by a multiple of 90 degrees."""

    VALID_DEGREES = (90, 180, 270)

    def __init__(self, board, tile_index, degrees=90):
        super().__init__(board, tile_index)
        if degrees not in self.VALID_DEGREES:
            raise ValueError("degrees must be 90, 180 or 270")
        self.degrees = degrees

    def apply(self):
        self.tile.rotate(self.degrees)

    def undo(self):
        self.tile.rotate(-self.degrees)

    def describe(self):
        return f"rotate tile {self.tile_index} by {self.degrees} degrees"


class FlipTransformation(TileTransformation):
    """Flips one tile horizontally or vertically. A flip is its own
    inverse, so undo() simply performs the same flip a second time."""

    def __init__(self, board, tile_index, axis="horizontal"):
        super().__init__(board, tile_index)
        if axis not in ("horizontal", "vertical"):
            raise ValueError("axis must be 'horizontal' or 'vertical'")
        self.axis = axis

    def apply(self):
        if self.axis == "horizontal":
            self.tile.flip_horizontal()
        else:
            self.tile.flip_vertical()

    def undo(self):
        self.apply()  # flipping twice restores the original state

    def describe(self):
        return f"flip tile {self.tile_index} {self.axis}ly"


class SwapTransformation(Transformation):
    """Exchanges the grid position of two tiles. Also its own inverse."""

    def __init__(self, board, index_a, index_b):
        super().__init__(board)
        if index_a == index_b:
            raise ValueError("a tile cannot be swapped with itself")
        self.index_a = index_a
        self.index_b = index_b

    def apply(self):
        tiles = self.board.tiles
        tiles[self.index_a], tiles[self.index_b] = (
            tiles[self.index_b],
            tiles[self.index_a],
        )

    def undo(self):
        self.apply()  # swapping twice restores the original arrangement

    def describe(self):
        return f"swap tiles {self.index_a} and {self.index_b}"


def random_transformation(board, kind, pool, rng=random):
    """Factory function: builds one transformation of the given `kind`
    ("swap", "rotate" or "flip") with random parameters, used while
    scrambling a freshly loaded image.

    The tile positions it acts on are popped from `pool` (a shuffled list
    of still-untouched positions), so across a whole scramble no tile is
    ever targeted by more than one transformation.

    This is the "class interaction" piece that ties the transformation
    hierarchy to PuzzleBoard without PuzzleBoard needing to know anything
    about how each transformation type works internally.
    """
    if kind == "swap":
        return SwapTransformation(board, pool.pop(), pool.pop())

    if kind == "rotate":
        degrees = rng.choice(RotateTransformation.VALID_DEGREES)
        return RotateTransformation(board, pool.pop(), degrees)

    if kind == "flip":
        axis = rng.choice(("horizontal", "vertical"))
        return FlipTransformation(board, pool.pop(), axis)

    raise ValueError(f"unknown transformation kind: {kind!r}")
