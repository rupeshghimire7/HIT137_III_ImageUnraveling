"""
puzzle_board.py

PuzzleBoard is the model for one round of the game. It ties the
image-processing layer (ImageProcessor / Tile) together with the
transformation layer (Transformation subclasses) and the round's rules
(GameState, HintAdvisor). It knows nothing about Tkinter - gui.py only
ever calls its public methods, which keeps the game rules completely
testable on their own (see tests/).
"""

import random
import time
from collections.abc import Callable

import numpy as np

from engine.fit_strategy import DEFAULT_FIT_MODE
from engine.game_state import MAX_HINTS, SUPPORTED_GRID_SIZES, GameState
from engine.hints import HintAdvisor, HintStrategy
from engine.image_processor import ImageProcessor
from engine.par_solver import ParSolver
from engine.scrambler import Scrambler
from models.tile import Tile
from models.transformations import (
    HORIZONTAL,
    FlipTransformation,
    RotateTransformation,
    SwapTransformation,
    Transformation,
)

__all__ = ["MAX_HINTS", "SUPPORTED_GRID_SIZES", "PuzzleBoard"]


class PuzzleBoard:
    """Model for a single puzzle round: a grid_size x grid_size grid of
    Tile objects, plus a history of every transformation ever applied to
    it (scramble AND player moves), so the round can be perfectly undone
    by the Solve button.

    The tiles, history and counters are private; they are read through
    properties and changed only by the methods below.
    """

    def __init__(
        self,
        image_path: str,
        grid_size: int,
        seed: int | None = None,
        *,
        fit_mode: str = DEFAULT_FIT_MODE,
        hint_strategy: HintStrategy | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Load `image_path`, cut it into a grid_size x grid_size grid and
        scramble it.

        seed          - pass a number to get a reproducible scramble.
        fit_mode      - "Crop" or "Pad": how a non-square picture is made
                        square (see engine.fit_strategy).
        hint_strategy - how hints choose a tile (default: SmartHint).
        clock         - time source for the round timer (for tests).

        Raises ValueError for an unsupported grid size or fit mode, and
        ImageLoadError (also a ValueError) for a file that cannot be used
        as an image.
        """
        if grid_size not in SUPPORTED_GRID_SIZES:
            raise ValueError(
                f"Grid size must be one of {SUPPORTED_GRID_SIZES}, got {grid_size}."
            )
        self._grid_size = grid_size

        original = ImageProcessor.load_image(image_path)
        self._reference_image = ImageProcessor.prepare_square(
            original, grid_size, fit_mode=fit_mode
        )
        self._tiles, self._tile_edge = ImageProcessor.split_into_tiles(
            self._reference_image, grid_size
        )
        self._validate_tiles()

        self._history: list[Transformation] = []   # everything applied so far, in order
        self._hint_advisor = HintAdvisor(hint_strategy)

        self._scramble(Scrambler(grid_size, random.Random(seed)))
        self._state = GameState(grid_size, ParSolver().par_moves(self._tiles), clock)

    def _validate_tiles(self) -> None:
        """Rotating a tile 90 degrees only fits back into its cell if the
        tile is square, so refuse anything else up front."""
        if len(self._tiles) != self._grid_size ** 2:
            raise ValueError(
                f"A {self._grid_size} x {self._grid_size} board needs "
                f"{self._grid_size ** 2} tiles, got {len(self._tiles)}."
            )
        for tile in self._tiles:
            height, width = tile.get_display_image().shape[:2]
            if height != width or height != self._tile_edge:
                raise ValueError(
                    f"Every tile must be a {self._tile_edge} px square, "
                    f"got {width} x {height}."
                )

    # Scrambling - called once, from __init__
    def _scramble(self, scrambler: Scrambler) -> None:
        """Apply a batch of random transformations, all generated at once,
        so the picture starts in a shuffled state (see Scrambler for the
        guarantees).

        Polymorphism: the batch mixes swaps, rotates and flips, and every
        one is applied the same way, without checking which concrete
        subclass it is.
        """
        for transformation in scrambler.generate(self):
            transformation.apply()
            self._history.append(transformation)

    # Player actions - every one is a Transformation, pushed onto history
    # Each returns True if the move was made, or False if it was ignored
    # because the puzzle is already complete (no further input accepted).
    def swap(self, index_a: int, index_b: int) -> bool:
        """Swap the tiles at two positions (one move)."""
        return self._play(SwapTransformation(self, index_a, index_b))

    def rotate_tile(self, index: int, degrees: int = 90) -> bool:
        """Rotate the tile at `index` clockwise (one move)."""
        return self._play(RotateTransformation(self, index, degrees))

    def flip_tile(self, index: int, axis: str = HORIZONTAL) -> bool:
        """Flip the tile at `index` along `axis` (one move)."""
        return self._play(FlipTransformation(self, index, axis))

    def _play(self, transformation: Transformation) -> bool:
        """Apply one player move and count it; a move that completes the
        picture also ends the round as a win."""
        if self._state.is_finished:
            return False
        transformation.apply()
        self._history.append(transformation)
        self._state.register_move()
        if self.is_solved():
            self._state.finish(was_auto_solved=False)
        return True

    # Solve / hints
    def solve(self) -> None:
        """Instantly restore the picture by undoing every transformation
        ever applied to this board (scramble AND player moves) in reverse
        order, then clear the moves and score and end the round as
        auto-solved. Does nothing if the round is already finished."""
        if self._state.is_finished:
            return
        while self._history:
            self._history.pop().undo()
        self._state.reset_after_solve()

    def use_hint(self) -> tuple[int, int, int] | None:
        """Returns (tile_index, home_row, home_col) describing one
        currently-incorrect tile and uses up one hint, or returns None if
        no hints remain or the round is finished."""
        if not self._state.can_hint():
            return None
        index = self._hint_advisor.pick(self._tiles, self.incorrect_indices())
        if index is None:
            return None

        self._state.consume_hint()
        tile = self._tiles[index]
        return index, tile.home_row, tile.home_col

    # Read-only state
    @property
    def grid_size(self) -> int:
        """Number of tiles along each side of the board."""
        return self._grid_size

    @property
    def tile_edge(self) -> int:
        """Length of one tile's side, in pixels."""
        return self._tile_edge

    @property
    def reference_image(self) -> np.ndarray:
        """The prepared original picture (RGB) the player is restoring."""
        return self._reference_image

    @property
    def tiles(self) -> list[Tile]:
        """The tiles in their current row-major grid order. Only
        Transformation objects should reorder this list."""
        return self._tiles

    @property
    def history(self) -> list[Transformation]:
        """Every transformation applied so far and not yet undone."""
        return self._history

    @property
    def state(self) -> GameState:
        """This round's counters, timer and score."""
        return self._state

    @property
    def moves(self) -> int:
        """Player moves made this round (each swap/rotate/flip is one)."""
        return self._state.moves

    @property
    def hints_remaining(self) -> int:
        """Hints still available for this image."""
        return self._state.hints_left

    @property
    def hints_used(self) -> int:
        """Hints used so far for this image (Solve does not give them back)."""
        return self._state.hints_used

    # Queries
    def incorrect_indices(self) -> list[int]:
        """Positions of every tile that is not yet in its home cell the
        right way up."""
        result = []
        for index, tile in enumerate(self._tiles):
            row, col = divmod(index, self._grid_size)
            if not tile.is_correct(row, col):
                result.append(index)
        return result

    def is_solved(self) -> bool:
        """True when every tile is in its home cell the right way up."""
        return not self.incorrect_indices()

    def render(self) -> np.ndarray:
        """Return the current (possibly still-scrambled) image as a
        displayable numpy array, tiles reassembled in their current
        grid order with their current rotation/flip applied."""
        return ImageProcessor.merge_tiles(self._tiles, self._grid_size, self._tile_edge)

    def index_at(self, row: int, col: int) -> int | None:
        """Convert a (row, col) grid cell into a flat tile-list index, or
        None if it falls outside the grid."""
        if 0 <= row < self._grid_size and 0 <= col < self._grid_size:
            return row * self._grid_size + col
        return None
