"""
puzzle_board.py

PuzzleBoard is the model for one round of the game. It ties the
image-processing layer (ImageProcessor / Tile) together with the
transformation layer (Transformation subclasses). It knows nothing about
Tkinter - gui.py only ever calls its public methods, which keeps the game
rules completely testable on their own (see verify_model.py).
"""

from engine.image_processor import ImageProcessor
from models.transformations import (
    RotateTransformation,
    FlipTransformation,
    SwapTransformation,
    random_transformation,
)


class PuzzleBoard:
    """Model for a single puzzle round: a grid_size x grid_size grid of
    Tile objects, plus a history of every transformation ever applied to
    it (scramble AND player moves), so the round can be perfectly undone
    by the Solve button."""

    def __init__(self, image_path, grid_size):
        self.grid_size = grid_size

        original = ImageProcessor.load_image(image_path)
        self.reference_image = ImageProcessor.prepare_square(
            original, grid_size)
        self.tiles, self.tile_edge = ImageProcessor.split_into_tiles(
            self.reference_image, grid_size
        )

        self.history = []   # every Transformation applied so far, in order
        self.moves = 0       # player-caused moves only (swap/rotate/flip)
        self.hints_used = 0
        self.max_hints = 3

        self._scramble()

    # Scrambling - called once, from __init__
    def _scramble(self):
        """Apply a batch of random transformations so the picture starts
        in a shuffled state. The count scales with grid size (6 for 3x3,
        12 for 4x4, 20 for 5x5, i.e. grid_size * (grid_size - 1))."""
        transformation_count = self.grid_size * (self.grid_size - 1)

        applied_kinds = set()
        for _ in range(transformation_count):
            transformation = random_transformation(self)
            transformation.apply()
            self.history.append(transformation)
            applied_kinds.add(type(transformation))

        # Guarantee all three transformation types appear at least once,
        # and that the scramble hasn't landed back on the solved picture.
        required = {RotateTransformation,
                    FlipTransformation, SwapTransformation}
        safety_limit = transformation_count + 50
        while (not required.issubset(applied_kinds) or self.is_solved()) and safety_limit > 0:
            transformation = random_transformation(self)
            transformation.apply()
            self.history.append(transformation)
            applied_kinds.add(type(transformation))
            safety_limit -= 1

    # Player actions - every one is a Transformation, pushed onto history
    def swap(self, index_a, index_b):
        t = SwapTransformation(self, index_a, index_b)
        t.apply()
        self.history.append(t)
        self.moves += 1

    def rotate_tile(self, index, degrees=90):
        t = RotateTransformation(self, index, degrees)
        t.apply()
        self.history.append(t)
        self.moves += 1

    def flip_tile(self, index, axis="horizontal"):
        t = FlipTransformation(self, index, axis)
        t.apply()
        self.history.append(t)
        self.moves += 1

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
