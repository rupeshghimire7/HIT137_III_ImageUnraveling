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
from typing import Protocol

from models.tile import Tile

HORIZONTAL = "horizontal"
VERTICAL = "vertical"


class TileGrid(Protocol):
    """Anything that holds the puzzle's tiles as a flat, row-major list
    (in practice a PuzzleBoard). It is all a transformation needs."""

    @property
    def tiles(self) -> list[Tile]:
        """The tiles in their current grid order."""


class Transformation(ABC):
    """Base class for anything that can be applied to, and later undone
    from, a PuzzleBoard."""

    def __init__(self, board: TileGrid) -> None:
        """`board` is the grid whose tiles this transformation acts on."""
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

    @abstractmethod
    def to_record(self) -> dict[str, object]:
        """Plain-data description of this transformation: its "kind"
        ("swap", "rotate" or "flip") plus the positions and parameters it
        uses. Lets other code log or compare moves without holding on to
        the transformation object itself."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.describe()}>"


class TileTransformation(Transformation):
    """A transformation that acts on a single tile, identified by that
    tile's current index/position in the board's tile list."""

    def __init__(self, board: TileGrid, tile_index: int) -> None:
        """`tile_index` is the grid position of the tile to act on."""
        super().__init__(board)
        self.tile_index = tile_index

    @property
    def tile(self) -> Tile:
        """The tile currently sitting at this transformation's position."""
        return self.board.tiles[self.tile_index]


class RotateTransformation(TileTransformation):
    """Rotates one tile clockwise by a multiple of 90 degrees."""

    VALID_DEGREES = (90, 180, 270)

    def __init__(self, board: TileGrid, tile_index: int, degrees: int = 90) -> None:
        """Raises ValueError unless `degrees` is 90, 180 or 270."""
        super().__init__(board, tile_index)
        if degrees not in self.VALID_DEGREES:
            raise ValueError("degrees must be 90, 180 or 270")
        self.degrees = degrees

    def apply(self) -> None:
        """Rotate the tile clockwise by this transformation's degrees."""
        self.tile.rotate(self.degrees)

    def undo(self) -> None:
        """Rotate the tile back anticlockwise by the same amount."""
        self.tile.rotate(-self.degrees)

    def describe(self) -> str:
        """E.g. "rotate tile 7 by 180 degrees"."""
        return f"rotate tile {self.tile_index} by {self.degrees} degrees"

    def to_record(self) -> dict[str, object]:
        """{"kind": "rotate", "index": ..., "degrees": ...}"""
        return {"kind": "rotate", "index": self.tile_index, "degrees": self.degrees}


class FlipTransformation(TileTransformation):
    """Flips one tile horizontally or vertically. A flip is its own
    inverse, so undo() simply performs the same flip a second time."""

    VALID_AXES = (HORIZONTAL, VERTICAL)

    def __init__(self, board: TileGrid, tile_index: int, axis: str = HORIZONTAL) -> None:
        """Raises ValueError unless `axis` is "horizontal" or "vertical"."""
        super().__init__(board, tile_index)
        if axis not in self.VALID_AXES:
            raise ValueError("axis must be 'horizontal' or 'vertical'")
        self.axis = axis

    def apply(self) -> None:
        """Flip the tile along this transformation's axis."""
        if self.axis == HORIZONTAL:
            self.tile.flip_horizontal()
        else:
            self.tile.flip_vertical()

    def undo(self) -> None:
        """Flip again - flipping twice restores the original state."""
        self.apply()

    def describe(self) -> str:
        """E.g. "flip tile 3 horizontally"."""
        return f"flip tile {self.tile_index} {self.axis}ly"

    def to_record(self) -> dict[str, object]:
        """{"kind": "flip", "index": ..., "axis": ...}"""
        return {"kind": "flip", "index": self.tile_index, "axis": self.axis}


class SwapTransformation(Transformation):
    """Exchanges the grid position of two tiles. Also its own inverse."""

    def __init__(self, board: TileGrid, index_a: int, index_b: int) -> None:
        """Raises ValueError if both positions are the same."""
        super().__init__(board)
        if index_a == index_b:
            raise ValueError("a tile cannot be swapped with itself")
        self.index_a = index_a
        self.index_b = index_b

    def apply(self) -> None:
        """Exchange the two tiles' positions in the board's tile list."""
        tiles = self.board.tiles
        tiles[self.index_a], tiles[self.index_b] = (
            tiles[self.index_b],
            tiles[self.index_a],
        )

    def undo(self) -> None:
        """Swap again - swapping twice restores the original arrangement."""
        self.apply()

    def describe(self) -> str:
        """E.g. "swap tiles 0 and 5"."""
        return f"swap tiles {self.index_a} and {self.index_b}"

    def to_record(self) -> dict[str, object]:
        """{"kind": "swap", "index_a": ..., "index_b": ...}"""
        return {"kind": "swap", "index_a": self.index_a, "index_b": self.index_b}


def random_transformation(
    board: TileGrid, kind: str, pool: list[int], rng: random.Random | None = None
) -> Transformation:
    """Factory function: builds one transformation of the given `kind`
    ("swap", "rotate" or "flip") with random parameters, used while
    scrambling a freshly loaded image.

    The tile positions it acts on are popped from `pool` (a shuffled list
    of still-untouched positions), so across a whole scramble no tile is
    ever targeted by more than one transformation. `rng` supplies the
    random degrees/axis (a fresh random.Random if omitted).

    This is the "class interaction" piece that ties the transformation
    hierarchy to PuzzleBoard without PuzzleBoard needing to know anything
    about how each transformation type works internally.

    Raises ValueError for an unknown `kind`.
    """
    rng = rng or random.Random()

    if kind == "swap":
        return SwapTransformation(board, pool.pop(), pool.pop())

    if kind == "rotate":
        degrees = rng.choice(RotateTransformation.VALID_DEGREES)
        return RotateTransformation(board, pool.pop(), degrees)

    if kind == "flip":
        axis = rng.choice(FlipTransformation.VALID_AXES)
        return FlipTransformation(board, pool.pop(), axis)

    raise ValueError(f"unknown transformation kind: {kind!r}")
