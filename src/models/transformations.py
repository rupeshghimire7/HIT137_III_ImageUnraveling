# ====================================================================== #
#  File         : src/models/transformations.py
#  Project      : ImageUnraveling - HIT137 Assignment 3
#
#  Student name : Hemanta Adhikari
#  Student ID   : S403355
#  Layer        : Core OOP models
#  Unit tests   : tests/test_transformations.py
# ====================================================================== #
"""
transformations.py - the puzzle's three move types: swap, rotate, flip.

Each move is a small object following the "command" pattern: it knows
how to apply() itself to a PuzzleBoard and how to undo() itself again,
exactly reversing that effect.

OOP concepts demonstrated
-------------------------
Inheritance
    Transformation                 (abstract base)
     ├── TileTransformation        (abstract - acts on one tile)
     │    ├── RotateTransformation
     │    └── FlipTransformation
     └── SwapTransformation        (acts on two tiles)

Polymorphism
    PuzzleBoard.solve() and the scrambler keep one plain list of
    Transformation objects and call .apply() / .undo() on each, never
    checking *which* subclass it is. The right behaviour happens
    automatically because every subclass overrides apply() / undo().
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # only for type hints - avoids a circular import
    from engine.puzzle_board import PuzzleBoard
    from models.tile import Tile

# --- Transformation kinds used by the scrambler ------------------------ #
SWAP = "swap"
ROTATE = "rotate"
FLIP = "flip"


# ====================================================================== #
# Abstract base classes
# ====================================================================== #
class Transformation(ABC):
    """Base class for anything that can be applied to, and later undone
    from, a PuzzleBoard."""

    def __init__(self, board: PuzzleBoard):
        self.board = board

    @abstractmethod
    def apply(self) -> None:
        """Perform the transformation on self.board."""

    @abstractmethod
    def undo(self) -> None:
        """Exactly reverse the effect of apply()."""

    @abstractmethod
    def describe(self) -> str:
        """Short, human-readable description (handy for debugging)."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.describe()}>"


class TileTransformation(Transformation):
    """A transformation acting on a single tile, identified by the tile's
    current position (index) in the board's tile list."""

    def __init__(self, board: PuzzleBoard, tile_index: int):
        super().__init__(board)
        self.tile_index = tile_index

    @property
    def tile(self) -> Tile:
        """The tile currently at `tile_index` on the board."""
        return self.board.tiles[self.tile_index]


# ====================================================================== #
# Concrete transformations
# ====================================================================== #
class RotateTransformation(TileTransformation):
    """Rotates one tile clockwise by 90, 180 or 270 degrees."""

    VALID_DEGREES = (90, 180, 270)

    def __init__(self, board: PuzzleBoard, tile_index: int, degrees: int = 90):
        """Raises ValueError unless `degrees` is 90, 180 or 270."""
        super().__init__(board, tile_index)
        if degrees not in self.VALID_DEGREES:
            raise ValueError("degrees must be 90, 180 or 270")
        self.degrees = degrees

    def apply(self) -> None:
        self.tile.rotate(self.degrees)

    def undo(self) -> None:
        self.tile.rotate(-self.degrees)   # turn back the same amount

    def describe(self) -> str:
        return f"rotate tile {self.tile_index} by {self.degrees} degrees"


class FlipTransformation(TileTransformation):
    """Flips one tile horizontally or vertically.

    A flip is its own inverse, so undo() simply flips again.
    """

    VALID_AXES = ("horizontal", "vertical")

    def __init__(self, board: PuzzleBoard, tile_index: int, axis: str = "horizontal"):
        """Raises ValueError unless `axis` is 'horizontal' or 'vertical'."""
        super().__init__(board, tile_index)
        if axis not in self.VALID_AXES:
            raise ValueError("axis must be 'horizontal' or 'vertical'")
        self.axis = axis

    def apply(self) -> None:
        if self.axis == "horizontal":
            self.tile.flip_horizontal()
        else:
            self.tile.flip_vertical()

    def undo(self) -> None:
        self.apply()   # flipping twice restores the original state

    def describe(self) -> str:
        return f"flip tile {self.tile_index} {self.axis}ly"


class SwapTransformation(Transformation):
    """Exchanges the grid positions of two tiles.

    A swap is its own inverse, so undo() simply swaps again.
    """

    def __init__(self, board: PuzzleBoard, index_a: int, index_b: int):
        """Raises ValueError if both indices are the same tile."""
        super().__init__(board)
        if index_a == index_b:
            raise ValueError("a tile cannot be swapped with itself")
        self.index_a = index_a
        self.index_b = index_b

    def apply(self) -> None:
        tiles = self.board.tiles
        a, b = self.index_a, self.index_b
        tiles[a], tiles[b] = tiles[b], tiles[a]

    def undo(self) -> None:
        self.apply()   # swapping twice restores the original arrangement

    def describe(self) -> str:
        return f"swap tiles {self.index_a} and {self.index_b}"


# ====================================================================== #
# Factory
# ====================================================================== #
def random_transformation(board: PuzzleBoard, kind: str, pool: list[int],
                          rng=random) -> Transformation:
    """Build one transformation of the given `kind` ("swap", "rotate" or
    "flip") with random parameters - used when scrambling a new image.

    The tile positions it acts on are popped from `pool` (a shuffled list
    of still-untouched positions), so across a whole scramble no tile is
    ever targeted more than once.

    This is the "class interaction" piece: PuzzleBoard asks for a move by
    name and never needs to know how each transformation works inside.

    Raises
    ------
    ValueError
        If `kind` is not one of "swap", "rotate" or "flip".
    """
    if kind == SWAP:
        return SwapTransformation(board, pool.pop(), pool.pop())

    if kind == ROTATE:
        degrees = rng.choice(RotateTransformation.VALID_DEGREES)
        return RotateTransformation(board, pool.pop(), degrees)

    if kind == FLIP:
        axis = rng.choice(FlipTransformation.VALID_AXES)
        return FlipTransformation(board, pool.pop(), axis)

    raise ValueError(f"unknown transformation kind: {kind!r}")