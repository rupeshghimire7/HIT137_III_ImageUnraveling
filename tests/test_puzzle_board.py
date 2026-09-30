"""Tests for engine.puzzle_board.PuzzleBoard - scrambling, player moves,
hints, solving and completion."""

import random

import numpy as np
import pytest

from engine.fit_strategy import PAD
from engine.hints import RandomHint
from engine.image_processor import ImageProcessor
from engine.par_solver import ParSolver
from engine.puzzle_board import MAX_HINTS, PuzzleBoard
from models.tile import Tile
from models.transformations import (
    FlipTransformation,
    RotateTransformation,
    SwapTransformation,
)

GRID_SIZES = (3, 4, 5)
SCRAMBLES_PER_SIZE = 200


def targeted_positions(transformation):
    if isinstance(transformation, SwapTransformation):
        return [transformation.index_a, transformation.index_b]
    return [transformation.tile_index]


def solve_like_a_player(board):
    """Restore the picture using only the player's three actions: swap,
    rotate 90 degrees clockwise and flip horizontally."""
    n = board.grid_size
    for position in range(n * n):
        home = divmod(position, n)
        current = next(
            i for i, t in enumerate(board.tiles) if (t.home_row, t.home_col) == home
        )
        if current != position:
            board.swap(position, current)
        tile = board.tiles[position]
        if tile.is_mirrored:
            board.flip_tile(position, "horizontal")
        while tile.rotation != 0:
            board.rotate_tile(position, 90)


@pytest.fixture(scope="module")
def scrambles(tmp_path_factory):
    """200 scrambled boards per grid size (built once for all tests)."""
    from conftest import noise_image, write_image

    path = str(write_image(tmp_path_factory.mktemp("img") / "p.png", noise_image(90, 90)))
    return {
        n: [PuzzleBoard(path, n, seed=seed) for seed in range(SCRAMBLES_PER_SIZE)]
        for n in GRID_SIZES
    }


@pytest.mark.parametrize("n", GRID_SIZES)
def test_scramble_count_scales_with_grid(scrambles, n):
    assert all(len(b.history) == n * (n - 1) for b in scrambles[n])


@pytest.mark.parametrize("n", GRID_SIZES)
def test_no_tile_targeted_twice(scrambles, n):
    for board in scrambles[n]:
        positions = [p for t in board.history for p in targeted_positions(t)]
        assert len(positions) == len(set(positions))


@pytest.mark.parametrize("n", GRID_SIZES)
def test_all_three_types_every_time(scrambles, n):
    required = {SwapTransformation, RotateTransformation, FlipTransformation}
    for board in scrambles[n]:
        assert {type(t) for t in board.history} == required


@pytest.mark.parametrize("n", GRID_SIZES)
def test_never_starts_solved_and_starts_clean(scrambles, n):
    for board in scrambles[n]:
        assert not board.is_solved()
        assert board.moves == 0
        assert board.hints_remaining == MAX_HINTS


@pytest.mark.parametrize("n", GRID_SIZES)
def test_player_can_always_solve(scrambles, n):
    for board in scrambles[n][:50]:
        solve_like_a_player(board)
        assert board.is_solved()
        assert board.incorrect_indices() == []


def test_random_between_loads(image_path):
    first = [t.describe() for t in PuzzleBoard(image_path, 4).history]
    different = any(
        [t.describe() for t in PuzzleBoard(image_path, 4).history] != first for _ in range(5)
    )
    assert different


def test_seed_is_reproducible(image_path):
    a = [t.describe() for t in PuzzleBoard(image_path, 5, seed=42).history]
    b = [t.describe() for t in PuzzleBoard(image_path, 5, seed=42).history]
    assert a == b


def test_each_player_action_counts_one_move(image_path):
    board = PuzzleBoard(image_path, 3, seed=1)
    board.swap(0, 1)
    board.rotate_tile(2, 90)
    board.flip_tile(3, "horizontal")
    assert board.moves == 3


def test_solve_restores_picture_and_clears_moves(image_path):
    board = PuzzleBoard(image_path, 4, seed=3)
    rng = random.Random(0)
    for _ in range(15):
        board.rotate_tile(rng.randrange(16), 90)
        board.swap(*rng.sample(range(16), 2))
    board.solve()
    assert board.is_solved()
    assert board.moves == 0
    assert (board.render() == board.reference_image).all()


def test_no_moves_accepted_after_completion(image_path):
    board = PuzzleBoard(image_path, 3, seed=5)
    board.solve()
    assert board.swap(0, 1) is False
    assert board.rotate_tile(0) is False
    assert board.flip_tile(0) is False
    assert board.moves == 0
    assert board.is_solved()


def test_hints_limited_to_three_and_point_at_wrong_tiles(image_path):
    board = PuzzleBoard(image_path, 3, seed=7)
    for used in range(1, MAX_HINTS + 1):
        index, home_row, home_col = board.use_hint()
        assert index in board.incorrect_indices()
        tile = board.tiles[index]
        assert (tile.home_row, tile.home_col) == (home_row, home_col)
        assert board.hints_remaining == MAX_HINTS - used
    assert board.use_hint() is None
    assert board.moves == 0  # hints are not moves


def test_render_matches_reference_size(image_path):
    board = PuzzleBoard(image_path, 5, seed=0)
    assert board.render().shape == board.reference_image.shape


def test_index_at_bounds(image_path):
    board = PuzzleBoard(image_path, 3, seed=0)
    assert board.index_at(2, 2) == 8
    assert board.index_at(3, 0) is None
    assert board.index_at(-1, 0) is None


@pytest.mark.parametrize("grid_size", [0, 2, 6, 7])
def test_invalid_grid_size_rejected(image_path, grid_size):
    with pytest.raises(ValueError):
        PuzzleBoard(image_path, grid_size)


def test_non_image_rejected(tmp_path):
    path = tmp_path / "x.txt"
    path.write_text("hello")
    with pytest.raises(ValueError):
        PuzzleBoard(str(path), 3)


def test_winning_by_hand_finishes_the_round_with_a_score(image_path):
    board = PuzzleBoard(image_path, 3, seed=11, clock=lambda: 0.0)
    par = board.state.par
    assert par == ParSolver().par_moves(board.tiles) > 0
    solve_like_a_player(board)
    state = board.state
    assert state.is_finished and not state.was_auto_solved
    assert state.moves >= par
    assert state.score() > 0 and 1 <= state.stars() <= 3


def test_solve_ends_round_as_auto_solved_and_keeps_hint_budget(image_path):
    board = PuzzleBoard(image_path, 3, seed=2)
    board.use_hint()
    board.rotate_tile(0)
    board.solve()
    assert board.state.was_auto_solved
    assert (board.moves, board.state.score()) == (0, 0)
    assert board.hints_remaining == MAX_HINTS - 1  # only a new image refills hints
    assert board.use_hint() is None
    board.solve()  # solving again changes nothing
    assert board.is_solved()


def test_hint_strategy_can_be_swapped(image_path):
    board = PuzzleBoard(image_path, 4, seed=4, hint_strategy=RandomHint(random.Random(0)))
    picks = set()
    for seed in range(30):
        other = PuzzleBoard(image_path, 4, seed=4, hint_strategy=RandomHint(random.Random(seed)))
        picks.add(other.use_hint()[0])
    assert picks <= set(board.incorrect_indices())
    assert len(picks) > 1


def test_pad_fit_mode_is_passed_through(image_path):
    # The fixture image is 150x200: cropping gives 360 px, padding the full 480.
    assert PuzzleBoard(image_path, 3).reference_image.shape[0] == 360
    assert PuzzleBoard(image_path, 3, fit_mode=PAD).reference_image.shape[0] == 480


def test_non_square_tiles_rejected(image_path, monkeypatch):
    def lopsided_square(image, grid_size, **kwargs):
        return np.zeros((90, 120, 3), dtype=np.uint8)

    def lopsided_split(image, grid_size):
        tiles = [
            Tile(image[:30, :40].copy(), i // grid_size, i % grid_size, tile_id=i)
            for i in range(grid_size ** 2)
        ]
        return tiles, 30

    monkeypatch.setattr(ImageProcessor, "prepare_square", staticmethod(lopsided_square))
    monkeypatch.setattr(ImageProcessor, "split_into_tiles", staticmethod(lopsided_split))
    with pytest.raises(ValueError, match="square"):
        PuzzleBoard(image_path, 3)


def test_board_state_is_read_only(image_path):
    board = PuzzleBoard(image_path, 3, seed=0)
    for name in ("tiles", "history", "moves", "grid_size", "state", "hints_remaining"):
        with pytest.raises(AttributeError):
            setattr(board, name, None)
