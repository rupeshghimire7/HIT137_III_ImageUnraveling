# ====================================================================== #
#  Unit tests for: src/models/transformations.py
#                  (Transformation hierarchy + random_transformation)
#
#  Student name : Hemanta Adhikari
#  Student ID   : S403355       
#  Layer        : Core OOP models
#
#  Run only this file (from the project root):
#      python -m pytest tests/test_transformations.py -v
# ====================================================================== #
"""Tests for the Transformation classes: inheritance, apply()/undo()
for swap/rotate/flip, input validation, polymorphic undo of a mixed
history, and the random_transformation() factory. A tiny FakeBoard
stands in for PuzzleBoard so only the models package is exercised."""

import random

import numpy as np
import pytest

from models.tile import Tile
from models.transformations import (
    FlipTransformation,
    RotateTransformation,
    SwapTransformation,
    TileTransformation,
    Transformation,
    random_transformation,
)


class FakeBoard:
    """Minimal stand-in for PuzzleBoard: transformations only need .tiles"""

    def __init__(self, n_tiles=9):
        self.tiles = [
            Tile(np.full((2, 2, 3), i, dtype=np.uint8), i // 3, i % 3)
            for i in range(n_tiles)
        ]

    def snapshot(self):
        return [(id(t), t.rotation, t.is_mirrored) for t in self.tiles]


@pytest.fixture
def board():
    return FakeBoard()


# --- inheritance ------------------------------------------------------- #
def test_abstract_classes_cannot_be_created(board):
    with pytest.raises(TypeError):
        Transformation(board)
    with pytest.raises(TypeError):
        TileTransformation(board, 0)


def test_class_hierarchy():
    assert issubclass(RotateTransformation, TileTransformation)
    assert issubclass(FlipTransformation, TileTransformation)
    assert issubclass(TileTransformation, Transformation)
    assert issubclass(SwapTransformation, Transformation)
    assert not issubclass(SwapTransformation, TileTransformation)


# --- rotate ------------------------------------------------------------ #
@pytest.mark.parametrize("degrees", [90, 180, 270])
def test_rotate_apply_and_undo(board, degrees):
    t = RotateTransformation(board, 4, degrees)
    t.apply()
    assert board.tiles[4].rotation == degrees
    assert board.tiles[3].rotation == 0
    t.undo()
    assert board.tiles[4].rotation == 0


@pytest.mark.parametrize("degrees", [0, 45, 360, -90])
def test_rotate_rejects_invalid_degrees(board, degrees):
    with pytest.raises(ValueError):
        RotateTransformation(board, 0, degrees)


def test_tile_property_points_at_board_tile(board):
    assert RotateTransformation(board, 5).tile is board.tiles[5]


# --- flip -------------------------------------------------------------- #
@pytest.mark.parametrize("axis", ["horizontal", "vertical"])
def test_flip_apply_and_undo(board, axis):
    t = FlipTransformation(board, 0, axis)
    t.apply()
    assert board.tiles[0].is_mirrored
    t.undo()
    assert not board.tiles[0].is_mirrored
    assert board.tiles[0].rotation == 0


def test_flip_rejects_invalid_axis(board):
    with pytest.raises(ValueError):
        FlipTransformation(board, 0, "diagonal")


# --- swap -------------------------------------------------------------- #
def test_swap_apply_and_undo(board):
    before = board.snapshot()
    a, b = board.tiles[0], board.tiles[8]
    t = SwapTransformation(board, 0, 8)
    t.apply()
    assert board.tiles[0] is b and board.tiles[8] is a
    t.undo()
    assert board.snapshot() == before


def test_swap_with_itself_rejected(board):
    with pytest.raises(ValueError):
        SwapTransformation(board, 3, 3)


def test_describe_and_repr(board):
    assert SwapTransformation(board, 2, 6).describe() == "swap tiles 2 and 6"
    assert "rotate tile 1" in RotateTransformation(board, 1, 180).describe()
    assert "vertical" in FlipTransformation(board, 3, "vertical").describe()
    assert "SwapTransformation" in repr(SwapTransformation(board, 0, 1))


# --- polymorphism ------------------------------------------------------ #
def test_mixed_history_undone_without_type_checks():
    """Apply many mixed transformations, then undo them in reverse order
    without checking their types - the board must be exactly restored."""
    rng = random.Random(0)
    board = FakeBoard(25)
    before = board.snapshot()
    history = []
    for _ in range(40):
        kind = rng.choice(("swap", "rotate", "flip"))
        pool = list(range(25))
        rng.shuffle(pool)
        t = random_transformation(board, kind, pool, rng)
        t.apply()
        history.append(t)
    while history:
        history.pop().undo()
    assert board.snapshot() == before


# --- random_transformation factory ------------------------------------- #
@pytest.mark.parametrize("kind, cls", [
    ("swap", SwapTransformation),
    ("rotate", RotateTransformation),
    ("flip", FlipTransformation),
])
def test_factory_builds_requested_kind(board, kind, cls):
    t = random_transformation(board, kind, list(range(9)), random.Random(1))
    assert isinstance(t, cls)


def test_factory_pops_tiles_from_pool(board):
    pool = [0, 1, 2, 3]
    swap = random_transformation(board, "swap", pool, random.Random(1))
    assert {swap.index_a, swap.index_b} == {3, 2}
    rotate = random_transformation(board, "rotate", pool, random.Random(1))
    assert rotate.tile_index == 1
    assert pool == [0]


def test_factory_parameters_are_valid(board):
    rng = random.Random(2)
    for _ in range(50):
        r = random_transformation(board, "rotate", list(range(9)), rng)
        f = random_transformation(board, "flip", list(range(9)), rng)
        assert r.degrees in (90, 180, 270)
        assert f.axis in ("horizontal", "vertical")


def test_factory_rejects_unknown_kind(board):
    with pytest.raises(ValueError):
        random_transformation(board, "shuffle", list(range(9)))
