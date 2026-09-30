"""Tests for the round rules in the engine package: GameState, scoring,
hint strategies, the par solver and the scrambler. None of them needs an
image file or a display."""

import random
from types import SimpleNamespace

import numpy as np
import pytest

from engine.game_state import MAX_HINTS, GameState
from engine.hints import HintAdvisor, RandomHint, SmartHint
from engine.par_solver import ParSolver
from engine.scoring import ScoringRules
from engine.scrambler import Scrambler
from models.tile import Tile
from models.transformations import SwapTransformation

PIXELS = np.zeros((4, 4, 3), dtype=np.uint8)


class FakeClock:
    """A clock the test moves forward by hand."""

    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def solved_tiles(n=3):
    return [Tile(PIXELS, i // n, i % n, tile_id=i) for i in range(n * n)]


def incorrect(tiles, n=3):
    return [i for i, t in enumerate(tiles) if not t.is_correct(*divmod(i, n))]


def swap(tiles, a, b):
    tiles[a], tiles[b] = tiles[b], tiles[a]


# --------------------------------------------------------------------- #
# GameState
# --------------------------------------------------------------------- #
def test_initial_state():
    state = GameState(3, par=5)
    assert (state.moves, state.hints_left, state.is_finished) == (0, MAX_HINTS, False)
    assert state.stars() == 0


@pytest.mark.parametrize("grid_size, par", [(2, 0), (6, 0), (3, -1)])
def test_invalid_state_arguments_rejected(grid_size, par):
    with pytest.raises(ValueError):
        GameState(grid_size, par)


def test_moves_counted_until_finished():
    state = GameState(3, par=5)
    for _ in range(5):
        state.register_move()
    state.finish(was_auto_solved=False)
    state.register_move()
    assert state.moves == 5
    assert state.is_finished and not state.was_auto_solved


def test_hint_budget():
    state = GameState(3, par=5)
    assert [state.consume_hint() for _ in range(MAX_HINTS + 2)] == [True] * 3 + [False] * 2
    assert state.hints_left == 0


def test_no_hints_after_finish():
    state = GameState(3, par=5)
    state.finish(was_auto_solved=False)
    assert not state.consume_hint()
    assert state.hints_left == MAX_HINTS


def test_reset_after_solve_clears_moves_and_score_but_not_hints():
    state = GameState(4, par=5)
    state.register_move()
    state.consume_hint()
    state.reset_after_solve()
    assert state.is_finished and state.was_auto_solved
    assert (state.moves, state.score(), state.stars()) == (0, 0, 0)
    assert state.hints_used == 1


def test_timer_freezes_on_finish():
    clock = FakeClock()
    state = GameState(3, par=5, clock=clock)
    clock.now += 42.9
    assert state.elapsed_seconds() == 42
    state.finish(was_auto_solved=False)
    clock.now += 1000
    assert state.elapsed_seconds() == 42


# --------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------- #
def test_score_never_rises_with_more_moves_time_or_hints_and_never_negative():
    best = ScoringRules.score(3, moves=6, par=6, seconds=0, hints_used=0)
    assert best == 900
    assert ScoringRules.score(3, 5, 6, 0, 0) == best        # beating par earns no bonus
    assert ScoringRules.score(3, 7, 6, 0, 0) < best
    assert ScoringRules.score(3, 6, 6, 10, 0) < best
    assert ScoringRules.score(3, 6, 6, 0, 1) < best
    assert ScoringRules.score(3, 500, 6, 5000, 3) == 0


def test_bigger_grid_has_bigger_base():
    scores = [ScoringRules.score(n, 0, 0, 0, 0) for n in (3, 4, 5)]
    assert scores == sorted(scores) and len(set(scores)) == 3


@pytest.mark.parametrize(
    "moves, par, hints, expected",
    [(10, 10, 0, 3), (10, 10, 1, 2), (14, 10, 0, 2), (30, 10, 0, 1), (0, 0, 0, 3), (1, 0, 0, 1)],
)
def test_stars(moves, par, hints, expected):
    assert ScoringRules.stars(moves, par, hints) == expected


def test_state_score_uses_par_time_and_hints():
    clock = FakeClock()
    state = GameState(3, par=2, clock=clock)
    for _ in range(4):
        state.register_move()
    state.consume_hint()
    clock.now += 10
    state.finish(was_auto_solved=False)
    assert state.score() == 900 - 2 * 15 - 10 * 2 - 150
    assert state.stars() == 1


# --------------------------------------------------------------------- #
# Hints
# --------------------------------------------------------------------- #
def test_random_hint_always_returns_an_incorrect_tile():
    tiles = solved_tiles()
    swap(tiles, 0, 5)
    tiles[7].rotate(90)
    wrong = incorrect(tiles)
    advisor = HintAdvisor(RandomHint(random.Random(1)))
    picks = {advisor.pick(tiles, wrong) for _ in range(50)}
    assert picks == set(wrong)


def test_smart_hint_prefers_tile_at_home_but_wrongly_turned():
    tiles = solved_tiles()
    swap(tiles, 0, 1)
    tiles[6].flip_horizontal()
    assert SmartHint().choose(tiles, incorrect(tiles)) == 6


def test_smart_hint_then_prefers_a_mutual_swap_pair():
    tiles = solved_tiles()
    # 0 -> 1 -> 2 -> 0 is a three-cycle; 5 and 7 are simply exchanged.
    tiles[0], tiles[1], tiles[2] = tiles[2], tiles[0], tiles[1]
    swap(tiles, 5, 7)
    assert SmartHint().choose(tiles, incorrect(tiles)) == 5


def test_smart_hint_falls_back_to_lowest_tile_id():
    tiles = solved_tiles()
    tiles[0], tiles[1], tiles[2] = tiles[2], tiles[0], tiles[1]
    pick = SmartHint().choose(tiles, incorrect(tiles))
    assert tiles[pick].tile_id == 0


def test_advisor_returns_none_when_nothing_is_wrong():
    assert HintAdvisor().pick(solved_tiles(), []) is None


# --------------------------------------------------------------------- #
# Par
# --------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "rotation, mirrored, expected",
    [(0, False, 0), (90, False, 3), (180, False, 2), (270, False, 1),
     (0, True, 1), (90, True, 2), (180, True, 3), (270, True, 2)],
)
def test_turns_needed_matches_what_a_player_can_do(rotation, mirrored, expected):
    tile = Tile(PIXELS, 0, 0)
    if mirrored:
        tile.flip_horizontal()
    tile.rotate(rotation)
    assert (tile.rotation, tile.is_mirrored) == (rotation, mirrored)
    assert ParSolver().turns_needed(tile) == expected


def test_par_of_hand_built_boards():
    solver = ParSolver()
    tiles = solved_tiles()
    assert solver.par_moves(tiles) == 0

    swap(tiles, 0, 8)
    assert solver.par_moves(tiles) == 1

    tiles = solved_tiles()
    tiles[4].rotate(90)
    assert solver.par_moves(tiles) == 3

    tiles = solved_tiles()
    tiles[0], tiles[1], tiles[2] = tiles[2], tiles[0], tiles[1]
    assert solver.par_moves(tiles) == 2


# --------------------------------------------------------------------- #
# Scrambler
# --------------------------------------------------------------------- #
@pytest.mark.parametrize("n, count", [(3, 6), (4, 12), (5, 20)])
def test_scrambler_plans_without_applying(n, count):
    board = SimpleNamespace(tiles=solved_tiles(n))
    scrambler = Scrambler(n, random.Random(0))
    batch = scrambler.generate(board)
    assert len(batch) == scrambler.transformation_count == count
    assert incorrect(board.tiles, n) == []
    kinds = {record["kind"] for record in (t.to_record() for t in batch)}
    assert kinds == {"swap", "rotate", "flip"}


def test_scrambler_rejects_tiny_grid():
    with pytest.raises(ValueError):
        Scrambler(2)


def test_to_record_describes_a_move():
    board = SimpleNamespace(tiles=solved_tiles())
    assert SwapTransformation(board, 1, 2).to_record() == {
        "kind": "swap", "index_a": 1, "index_b": 2,
    }
