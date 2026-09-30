"""
hints.py

Decides which incorrect tile the Hint button points at.

OOP concepts demonstrated here
-------------------------------
Inheritance:
    HintStrategy (abstract base)
        -> RandomHint   any incorrect tile
        -> SmartHint    the incorrect tile that is quickest to fix (default)

Polymorphism:
    HintAdvisor holds a HintStrategy and calls .choose() on it without
    knowing which one it was given.

Tiles are passed around as the board's flat, row-major list, so a tile's
position in the list is the cell it is sitting in and its tile_id is the
position it belongs in.
"""

import random
from abc import ABC, abstractmethod

from models.tile import Tile


class HintStrategy(ABC):
    """A rule for choosing which incorrect tile to point out."""

    @abstractmethod
    def choose(self, tiles: list[Tile], incorrect: list[int]) -> int:
        """Return one position from `incorrect`, the non-empty list of
        positions in `tiles` whose tile is not yet correct."""


class RandomHint(HintStrategy):
    """Points at any incorrect tile, chosen at random."""

    def __init__(self, rng: random.Random | None = None) -> None:
        """`rng` is the random source (a fresh random.Random if omitted)."""
        self._rng = rng or random.Random()

    def choose(self, tiles: list[Tile], incorrect: list[int]) -> int:
        """See HintStrategy.choose."""
        return self._rng.choice(incorrect)


class SmartHint(HintStrategy):
    """Points at the most useful tile, in this order of preference:

    1. a tile already in its home cell but turned the wrong way
       (rotating/flipping it fixes it without moving anything);
    2. a tile whose home cell holds the tile that belongs in *its* cell
       (one swap puts both in place);
    3. the misplaced tile with the lowest id, so the choice is predictable.
    """

    def choose(self, tiles: list[Tile], incorrect: list[int]) -> int:
        """See HintStrategy.choose."""
        for position in incorrect:
            if tiles[position].tile_id == position:
                return position

        for position in incorrect:
            home = tiles[position].tile_id
            if tiles[home].tile_id == position:
                return position

        return min(incorrect, key=lambda position: tiles[position].tile_id)


class HintAdvisor:
    """Picks the tile to hint at, using whichever strategy it was given."""

    def __init__(self, strategy: HintStrategy | None = None) -> None:
        """`strategy` defaults to SmartHint."""
        self._strategy = strategy or SmartHint()

    def pick(self, tiles: list[Tile], incorrect: list[int]) -> int | None:
        """Return the position of the tile to hint at, or None if no tile
        is incorrect."""
        if not incorrect:
            return None
        return self._strategy.choose(tiles, incorrect)
