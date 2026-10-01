# ====================================================================== #
#  Unit tests for: src/engine/puzzle_board.py  (class PuzzleBoard)
#
#  Student name : Ashim Koirala
#  Student ID   : S407089
#  Layer        : Game engine / rules
#
#  Run only this file (from the project root):
#      python -m pytest tests/test_puzzle_board.py -v
# ====================================================================== #
"""Tests for PuzzleBoard: grid-size validation, the scramble rules,
player moves and the move counter, the 3-hint limit, the "undo
everything" solve(), win detection / locking, render() and index_at()."""

import random

import numpy as np
import pytest

from engine.puzzle_board import MAX_HINTS, PuzzleBoard
from models.transformations import (
    FlipTransformation,
    RotateTransformation,
    SwapTransformation,
)

GRIDS = [3, 4, 5]


def targeted_tiles(transformation):
    if isinstance(transformation, SwapTransformation):
        return [transformation.index_a, transformation.index_b]
    return [transformation.tile_index]


# --- construction / validation ----------------------------------------- #
@pytest.mark.parametrize("grid", [0, 2, 6, 10])
def test_unsupported_grid_size_rejected(image_path, grid):
    with pytest.raises(ValueError):
        PuzzleBoard(image_path, grid)


def test_bad_file_rejected(tmp_path):
    bad = tmp_path / "bad.png"
    bad.write_text("not an image")
    with pytest.raises(ValueError):
        PuzzleBoard(str(bad), 3)


def test_counters_start_at_zero(image_path):
    board = PuzzleBoard(image_path, 3, seed=1)
    assert board.moves == 0 and board.hints_used == 0
    assert board.hints_remaining == MAX_HINTS == 3


def test_same_seed_gives_same_scramble(image_path):
    a = PuzzleBoard(image_path, 4, seed=7)
    b = PuzzleBoard(image_path, 4, seed=7)
    assert [t.describe() for t in a.history] == [t.describe()
                                                 for t in b.history]
    np.testing.assert_array_equal(a.render(), b.render())


# --- scramble rules ---------------------------------------------------- #
@pytest.mark.parametrize("grid", GRIDS)
@pytest.mark.parametrize("seed", range(10))
def test_scramble_rules(image_path, grid, seed):
    board = PuzzleBoard(image_path, grid, seed=seed)
    assert len(board.tiles) == grid * grid
    assert len(board.history) == grid * (grid - 1)          # 6 / 12 / 20
    kinds = {type(t) for t in board.history}
    assert kinds == {SwapTransformation,
                     RotateTransformation, FlipTransformation}
    targets = [i for t in board.history for i in targeted_tiles(t)]
    # no tile hit twice
    assert len(targets) == len(set(targets))
    assert not board.is_solved()


# --- player moves ------------------------------------------------------ #
@pytest.fixture
def board(image_path):
    return PuzzleBoard(image_path, 3, seed=3)


def test_swap_move(board):
    a, b = board.tiles[0], board.tiles[8]
    assert board.swap(0, 8) is True
    assert board.tiles[0] is b and board.tiles[8] is a
    assert board.moves == 1


def test_rotate_move(board):
    tile = board.tiles[4]
    before = tile.rotation
    assert board.rotate_tile(4) is True
    assert tile.rotation == (before + 90) % 360 or tile.is_mirrored
    assert board.moves == 1


def test_flip_move(board):
    tile = board.tiles[2]
    before = tile.is_mirrored
    assert board.flip_tile(2, "horizontal") is True
    assert tile.is_mirrored != before
    assert board.moves == 1


def test_moves_are_added_to_history(board):
    start = len(board.history)
    board.swap(0, 1)
    board.rotate_tile(0)
    board.flip_tile(1, "vertical")
    assert board.moves == 3
    assert len(board.history) == start + 3


def test_no_moves_accepted_once_solved(board):
    board.solve()
    assert board.swap(0, 1) is False
    assert board.rotate_tile(0) is False
    assert board.flip_tile(0) is False
    assert board.moves == 0 and board.is_solved()


# --- hints ------------------------------------------------------------- #
def test_hint_names_a_wrong_tile_and_its_home(board):
    index, row, col = board.use_hint()
    assert index in board.incorrect_indices()
    tile = board.tiles[index]
    assert (row, col) == (tile.home_row, tile.home_col)


def test_max_three_hints(board):
    for left in (2, 1, 0):
        assert board.use_hint() is not None
        assert board.hints_remaining == left
    assert board.use_hint() is None
    assert board.hints_used == 3


def test_no_hint_when_solved(board):
    board.solve()
    assert board.use_hint() is None
    assert board.hints_used == 0


# --- solve / completion ------------------------------------------------ #
@pytest.mark.parametrize("grid", GRIDS)
def test_solve_restores_picture(image_path, grid):
    board = PuzzleBoard(image_path, grid, seed=grid)
    board.solve()
    assert board.is_solved()
    assert board.incorrect_indices() == []
    np.testing.assert_array_equal(board.render(), board.reference_image)


def test_solve_after_random_moves_and_hint(image_path):
    rng = random.Random(42)
    board = PuzzleBoard(image_path, 4, seed=42)
    n = len(board.tiles)
    for _ in range(25):
        action = rng.choice(("swap", "rotate", "flip"))
        if action == "swap":
            board.swap(*rng.sample(range(n), 2))
        elif action == "rotate":
            board.rotate_tile(rng.randrange(n), rng.choice((90, 180, 270)))
        else:
            board.flip_tile(rng.randrange(n), rng.choice(
                ("horizontal", "vertical")))
    board.use_hint()
    board.solve()
    assert board.is_solved()
    assert board.history == [] and board.moves == 0 and board.hints_used == 0


def test_manual_undo_counts_as_solved(board):
    for t in reversed(board.history):
        t.undo()
    assert board.is_solved()


# --- queries ----------------------------------------------------------- #
def test_render_shape_and_scrambled(board):
    image = board.render()
    assert image.shape == board.reference_image.shape
    assert image.shape[0] == board.tile_edge * board.grid_size
    assert not np.array_equal(image, board.reference_image)


@pytest.mark.parametrize("row, col, expected", [
    (0, 0, 0), (1, 2, 5), (2, 2, 8),
    (-1, 0, None), (0, -1, None), (3, 0, None), (0, 3, None),
])
def test_index_at(board, row, col, expected):
    assert board.index_at(row, col) == expected
