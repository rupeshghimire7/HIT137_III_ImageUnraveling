"""
scrambler.py

Generates the batch of random transformations that shuffles a freshly
loaded picture. The whole batch is planned at once, so the rules the
brief sets for a scramble can be guaranteed rather than hoped for.
"""

import random

from models.transformations import TileGrid, Transformation, random_transformation


class Scrambler:
    """Builds one scramble for a grid_size x grid_size board.

    Every scramble it generates:
    - has grid_size * (grid_size - 1) transformations (6 / 12 / 20 for
      3x3 / 4x4 / 5x5), so the count scales with the grid;
    - contains at least one swap, one rotate and one flip;
    - never targets a tile twice: a swap uses two tiles and a rotate/flip
      one, all drawn from one shuffled pool of positions. The count plus
      the number of swaps must fit in grid_size**2 tiles, which is why
      there are at most grid_size swaps;
    - can never leave the board solved, because it has at least one swap
      and a swapped tile is not touched again.
    """

    def __init__(self, grid_size: int, rng: random.Random | None = None) -> None:
        """`rng` is the random source; pass a seeded random.Random for a
        reproducible scramble. Raises ValueError if grid_size < 3 (smaller
        grids cannot hold all three transformation types)."""
        if grid_size < 3:
            raise ValueError("A scramble needs a grid of at least 3 x 3.")
        self._grid_size = grid_size
        self._rng = rng or random.Random()

    @property
    def transformation_count(self) -> int:
        """How many transformations each scramble contains."""
        return self._grid_size * (self._grid_size - 1)

    def generate(self, board: TileGrid) -> list[Transformation]:
        """Return a new random scramble for `board`, as a mixed list of
        Swap / Rotate / Flip transformations in the order they should be
        applied. Nothing is applied here - the caller does that."""
        n = self._grid_size
        swaps = self._rng.randint(1, n)
        rest = self.transformation_count - swaps
        rotates = self._rng.randint(1, rest - 1)
        flips = rest - rotates

        kinds = ["swap"] * swaps + ["rotate"] * rotates + ["flip"] * flips
        self._rng.shuffle(kinds)
        pool = list(range(n * n))
        self._rng.shuffle(pool)

        return [random_transformation(board, kind, pool, self._rng) for kind in kinds]
