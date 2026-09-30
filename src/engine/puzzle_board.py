"""
puzzle_board.py

PuzzleBoard is the model for one round of the game. It ties the
image-processing layer (ImageProcessor / Tile) together with the
transformation layer (Transformation subclasses). It knows nothing about
Tkinter - gui.py only ever calls its public methods, which keeps the game
rules completely testable on their own (see verify_model.py).
"""

import random

from engine.image_processor import ImageProcessor
from models.transformations import (
    FlipTransformation,
    RotateTransformation,
    SwapTransformation,
    random_transformation,
)

SUPPORTED_GRID_SIZES = (3, 4, 5)
MAX_HINTS = 3


class PuzzleBoard:
    """Model for a single puzzle round: a grid_size x grid_size grid of
    Tile objects, plus a history of every transformation ever applied to
    it (scramble AND player moves), so the round can be perfectly undone
    by the Solve button."""

    def __init__(self, image_path, grid_size, seed=None):
        """Load `image_path`, cut it into a grid_size x grid_size grid and
        scramble it. Pass `seed` to get a reproducible scramble.

        Raises ValueError for an unsupported grid size or a file that
        cannot be read as an image.
        """
        if grid_size not in SUPPORTED_GRID_SIZES:
            raise ValueError(
                f"Grid size must be one of {SUPPORTED_GRID_SIZES}, got {grid_size}."
            )
        self.grid_size = grid_size
        self._rng = random.Random(seed)

        original = ImageProcessor.load_image(image_path)
        self.reference_image = ImageProcessor.prepare_square(
            original, grid_size)
        self.tiles, self.tile_edge = ImageProcessor.split_into_tiles(
            self.reference_image, grid_size
        )

        self.history = []   # every Transformation applied so far, in order
        self.moves = 0       # player-caused moves only (swap/rotate/flip)
        self.hints_used = 0
        self.max_hints = MAX_HINTS

        self._scramble()

    # Scrambling - called once, from __init__
    def _scramble(self):
        """Apply a batch of random transformations, all generated at once,
        so the picture starts in a shuffled state.

        - The count scales with grid size: grid_size * (grid_size - 1),
          i.e. 6 for 3x3, 12 for 4x4 and 20 for 5x5.
        - Every scramble contains at least one swap, rotate and flip.
        - No tile is targeted twice: a swap uses two tiles and a
          rotate/flip one, all drawn from one shuffled pool of positions.
          count + swaps must fit in grid_size**2 tiles, so swaps <= N.
        - At least one swap means the board can never start solved.
        """
        n = self.grid_size
        transformation_count = n * (n - 1)
        swaps = self._rng.randint(1, n)
        rest = transformation_count - swaps
        rotates = self._rng.randint(1, rest - 1)
        flips = rest - rotates

        kinds = ["swap"] * swaps + ["rotate"] * rotates + ["flip"] * flips
        self._rng.shuffle(kinds)
        pool = list(range(n * n))
        self._rng.shuffle(pool)

        # Polymorphism: every transformation is applied the same way,
        # without checking which concrete subclass it is.
        for kind in kinds:
            transformation = random_transformation(self, kind, pool, self._rng)
            transformation.apply()
            self.history.append(transformation)

    # Player actions - every one is a Transformation, pushed onto history
    # Each returns True if the move was made, or False if it was ignored
    # because the puzzle is already complete (no further input accepted).
    def swap(self, index_a, index_b):
        """Swap the tiles at two positions (one move)."""
        return self._play(SwapTransformation(self, index_a, index_b))

    def rotate_tile(self, index, degrees=90):
        """Rotate the tile at `index` clockwise (one move)."""
        return self._play(RotateTransformation(self, index, degrees))

    def flip_tile(self, index, axis="horizontal"):
        """Flip the tile at `index` along `axis` (one move)."""
        return self._play(FlipTransformation(self, index, axis))

    def _play(self, transformation):
        if self.is_solved():
            return False
        transformation.apply()
        self.history.append(transformation)
        self.moves += 1
        return True

    # Solve / hints
    def solve(self):
        """Instantly restore the picture by undoing every transformation
        ever applied to this board (scramble AND player moves) in reverse
        order, then clear the moves/hints counters for this image."""
        while self.history:
            transformation = self.history.pop()
            transformation.undo()
        self.moves = 0
        self.hints_used = 0

    def use_hint(self):
        """Returns (tile_index, home_row, home_col) describing one
        currently-incorrect tile, or None if no hints remain or the
        puzzle is already solved."""
        if self.hints_used >= self.max_hints:
            return None

        incorrect = self.incorrect_indices()
        if not incorrect:
            return None

        self.hints_used += 1
        index = incorrect[0]
        tile = self.tiles[index]
        return index, tile.home_row, tile.home_col

    @property
    def hints_remaining(self):
        return self.max_hints - self.hints_used

    # Queries
    def incorrect_indices(self):
        result = []
        for index, tile in enumerate(self.tiles):
            row, col = divmod(index, self.grid_size)
            if not tile.is_correct(row, col):
                result.append(index)
        return result

    def is_solved(self):
        return len(self.incorrect_indices()) == 0

    def render(self):
        """Return the current (possibly still-scrambled) image as a
        displayable numpy array, tiles reassembled in their current
        grid order with their current rotation/flip applied."""
        return ImageProcessor.merge_tiles(self.tiles, self.grid_size, self.tile_edge)

    def index_at(self, row, col):
        """Convert a (row, col) grid cell into a flat tile-list index, or
        None if it falls outside the grid."""
        if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
            return row * self.grid_size + col
        return None
