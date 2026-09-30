"""Tests for the Transformation hierarchy in models.transformations."""

import random
from types import SimpleNamespace

import numpy as np
import pytest

from models.tile import Tile
from models.transformations import (
    FlipTransformation,
    RotateTransformation,
    SwapTransformation,
    Transformation,
    random_transformation,
)


def make_board(count=9):
    rng = np.random.default_rng(0)
    tiles = [
        Tile(rng.integers(0, 256, (4, 4, 3), dtype=np.uint8), i // 3, i % 3)
        for i in range(count)
    ]
    return SimpleNamespace(tiles=tiles)


def board_state(board):
    return [(id(t), t.rotation, t.is_mirrored) for t in board.tiles]


@pytest.mark.parametrize(
    "factory",
    [
        lambda b: SwapTransformation(b, 0, 4),
        lambda b: RotateTransformation(b, 2, 90),
        lambda b: RotateTransformation(b, 2, 180),
        lambda b: RotateTransformation(b, 2, 270),
        lambda b: FlipTransformation(b, 5, "horizontal"),
        lambda b: FlipTransformation(b, 5, "vertical"),
    ],
)
def test_apply_then_undo_restores_board(factory):
    board = make_board()
    before = board_state(board)
    transformation = factory(board)
    transformation.apply()
    assert board_state(board) != before
    transformation.undo()
    assert board_state(board) == before


def test_polymorphic_undo_of_mixed_list():
    board = make_board()
    before = board_state(board)
    history = [
        SwapTransformation(board, 0, 1),
        RotateTransformation(board, 0, 90),
        FlipTransformation(board, 1, "vertical"),
        SwapTransformation(board, 1, 8),
    ]
    for t in history:
        t.apply()
    for t in reversed(history):
        assert isinstance(t, Transformation)
        t.undo()
    assert board_state(board) == before


def test_invalid_arguments_rejected():
    board = make_board()
    with pytest.raises(ValueError):
        SwapTransformation(board, 3, 3)
    for degrees in (0, 45, 360):
        with pytest.raises(ValueError):
            RotateTransformation(board, 0, degrees)
    with pytest.raises(ValueError):
        FlipTransformation(board, 0, "diagonal")


@pytest.mark.parametrize(
    "kind, cls, used", [("swap", SwapTransformation, 2), ("rotate", RotateTransformation, 1),
                        ("flip", FlipTransformation, 1)]
)
def test_factory_draws_tiles_from_pool(kind, cls, used):
    board = make_board()
    pool = list(range(9))
    transformation = random_transformation(board, kind, pool, random.Random(0))
    assert isinstance(transformation, cls)
    assert len(pool) == 9 - used


def test_factory_rejects_unknown_kind():
    with pytest.raises(ValueError):
        random_transformation(make_board(), "shear", [0, 1])


def test_describe_is_readable():
    board = make_board()
    assert "rotate" in RotateTransformation(board, 1, 180).describe()
    assert "180" in RotateTransformation(board, 1, 180).describe()
