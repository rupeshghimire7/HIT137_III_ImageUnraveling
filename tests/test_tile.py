"""Tests for models.tile.Tile - orientation tracking and correctness."""

import itertools

import cv2
import numpy as np
import pytest

from models.tile import Tile

PIXELS = np.random.default_rng(1).integers(0, 256, (6, 6, 3), dtype=np.uint8)
ACTIONS = ("rotate", "flip_h", "flip_v")


def apply_action(tile, action):
    if action == "rotate":
        tile.rotate(90)
    elif action == "flip_h":
        tile.flip_horizontal()
    else:
        tile.flip_vertical()


def all_orientations():
    """Tiles in every reachable orientation (all 8, with duplicates)."""
    for length in range(4):
        for sequence in itertools.product(ACTIONS, repeat=length):
            tile = Tile(PIXELS, 0, 0)
            for action in sequence:
                apply_action(tile, action)
            yield tile


def test_new_tile_is_correct_only_at_home():
    tile = Tile(PIXELS, 1, 2)
    assert tile.is_correct(1, 2)
    assert not tile.is_correct(2, 1)


def test_four_rotations_return_to_original():
    tile = Tile(PIXELS, 0, 0)
    for _ in range(4):
        tile.rotate(90)
    assert tile.is_correct(0, 0)
    assert np.array_equal(tile.get_display_image(), PIXELS)


def test_all_eight_orientations_are_reachable():
    states = {(t.rotation, t.is_mirrored) for t in all_orientations()}
    assert len(states) == 8


@pytest.mark.parametrize(
    "action, expected",
    [
        ("rotate", lambda img: cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)),
        ("flip_h", lambda img: cv2.flip(img, 1)),
        ("flip_v", lambda img: cv2.flip(img, 0)),
    ],
)
def test_each_action_changes_the_tile_as_displayed(action, expected):
    """Whatever the current orientation, the action does exactly what the
    player sees: e.g. a horizontal flip of a rotated tile is still a
    left-right flip on screen."""
    for tile in all_orientations():
        before = tile.get_display_image()
        apply_action(tile, action)
        assert np.array_equal(tile.get_display_image(), expected(before))


def test_correct_exactly_when_pixels_match_original():
    for tile in all_orientations():
        looks_right = np.array_equal(tile.get_display_image(), PIXELS)
        assert tile.is_correct(0, 0) == looks_right


def test_player_can_fix_every_orientation():
    """Using only the player's actions (rotate 90 clockwise, flip
    horizontally), every orientation - including a vertical flip from the
    scramble - can be returned to correct (at most 1 flip + 3 rotations)."""
    for tile in all_orientations():
        moves = 0
        if tile.is_mirrored:
            tile.flip_horizontal()
            moves += 1
        while tile.rotation != 0:
            tile.rotate(90)
            moves += 1
        assert tile.is_correct(0, 0)
        assert moves <= 4


def test_flip_h_then_flip_v_is_a_half_turn_not_correct():
    tile = Tile(PIXELS, 0, 0)
    tile.flip_horizontal()
    tile.flip_vertical()
    assert (tile.rotation, tile.is_mirrored) == (180, False)
    assert not tile.is_correct(0, 0)


def test_reset_restores_original():
    tile = Tile(PIXELS, 0, 0)
    tile.rotate(270)
    tile.flip_vertical()
    tile.reset()
    assert tile.is_correct(0, 0)


def test_original_pixels_never_modified():
    pixels = PIXELS.copy()
    tile = Tile(pixels, 0, 0)
    for action in ACTIONS:
        apply_action(tile, action)
        tile.get_display_image()
    assert np.array_equal(pixels, PIXELS)


def test_invalid_input_rejected():
    with pytest.raises(ValueError):
        Tile(np.empty((0, 0, 3), dtype=np.uint8), 0, 0)
    with pytest.raises(ValueError):
        Tile(PIXELS, -1, 0)
    with pytest.raises(ValueError):
        Tile(PIXELS, 0, 0).rotate(45)


def test_home_is_read_only():
    tile = Tile(PIXELS, 1, 1)
    with pytest.raises(AttributeError):
        tile.home_row = 2
