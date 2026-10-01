# ====================================================================== #
#  Unit tests for: src/models/tile.py  (class Tile)
#
#  Student name : Hemanta Adhikari
#  Student ID   : S403355
#  Layer        : Core OOP models
#
#  Run only this file (from the project root):
#      python -m pytest tests/test_tile.py -v
# ====================================================================== #
"""Tests for models.tile.Tile - constructor checks, encapsulation,
rotation/mirror tracking, the displayed pixels and is_correct()."""

import itertools

import cv2
import numpy as np
import pytest

from models.tile import Tile

# Random 6x6 pixels: every rotation/flip gives a visibly different array.
PIXELS = np.random.default_rng(1).integers(0, 256, (6, 6, 3), dtype=np.uint8)


@pytest.fixture
def tile():
    return Tile(PIXELS, 1, 2)


# --- constructor ------------------------------------------------------- #
def test_constructor_sets_home_and_default_orientation(tile):
    assert (tile.home_row, tile.home_col) == (1, 2)
    assert tile.rotation == 0
    assert tile.is_mirrored is False


@pytest.mark.parametrize("image", [None, np.zeros((0, 0, 3), dtype=np.uint8)])
def test_constructor_rejects_empty_image(image):
    with pytest.raises(ValueError):
        Tile(image, 0, 0)


@pytest.mark.parametrize("row, col", [(-1, 0), (0, -1)])
def test_constructor_rejects_negative_home(row, col):
    with pytest.raises(ValueError):
        Tile(PIXELS, row, col)


# --- encapsulation ----------------------------------------------------- #
@pytest.mark.parametrize("name", ["rotation", "is_mirrored", "home_row", "home_col"])
def test_state_is_read_only(tile, name):
    with pytest.raises(AttributeError):
        setattr(tile, name, 1)


# --- rotate ------------------------------------------------------------ #
def test_rotate_accumulates_and_wraps(tile):
    tile.rotate(90)
    assert tile.rotation == 90
    tile.rotate(180)
    assert tile.rotation == 270
    tile.rotate(90)
    assert tile.rotation == 0


def test_negative_rotation_undoes_rotation(tile):
    tile.rotate(270)
    tile.rotate(-270)
    assert tile.rotation == 0


@pytest.mark.parametrize("degrees", [45, 1, -30])
def test_rotate_rejects_non_right_angles(tile, degrees):
    with pytest.raises(ValueError):
        tile.rotate(degrees)


# --- flips ------------------------------------------------------------- #
def test_flip_horizontal_twice_restores(tile):
    tile.flip_horizontal()
    assert tile.is_mirrored
    tile.flip_horizontal()
    assert not tile.is_mirrored and tile.rotation == 0


def test_flip_vertical_twice_restores(tile):
    tile.flip_vertical()
    assert tile.is_mirrored and tile.rotation == 180
    tile.flip_vertical()
    assert not tile.is_mirrored and tile.rotation == 0


def test_reset_clears_orientation(tile):
    tile.rotate(90)
    tile.flip_horizontal()
    tile.reset()
    assert tile.rotation == 0 and not tile.is_mirrored


# --- displayed pixels match what the player expects -------------------- #
@pytest.mark.parametrize("degrees, code", [
    (90, cv2.ROTATE_90_CLOCKWISE),
    (180, cv2.ROTATE_180),
    (270, cv2.ROTATE_90_COUNTERCLOCKWISE),
])
def test_display_after_rotation(degrees, code):
    t = Tile(PIXELS, 0, 0)
    t.rotate(degrees)
    np.testing.assert_array_equal(t.get_display_image(), cv2.rotate(PIXELS, code))


def test_display_unchanged_by_default(tile):
    np.testing.assert_array_equal(tile.get_display_image(), PIXELS)


def test_flip_horizontal_mirrors_what_is_on_screen():
    """Flipping an already rotated tile mirrors the picture as displayed."""
    t = Tile(PIXELS, 0, 0)
    t.rotate(90)
    shown = t.get_display_image()
    t.flip_horizontal()
    np.testing.assert_array_equal(t.get_display_image(), cv2.flip(shown, 1))


def test_flip_vertical_mirrors_what_is_on_screen():
    t = Tile(PIXELS, 0, 0)
    t.rotate(90)
    shown = t.get_display_image()
    t.flip_vertical()
    np.testing.assert_array_equal(t.get_display_image(), cv2.flip(shown, 0))


def test_original_pixels_never_mutated(tile):
    before = PIXELS.copy()
    tile.rotate(90)
    tile.flip_vertical()
    tile.get_display_image()
    np.testing.assert_array_equal(PIXELS, before)


def test_player_actions_can_fix_any_orientation():
    """Every mix of rotate / flip_h / flip_v can be undone with only the
    player's two actions: flip horizontally once (if mirrored), then
    rotate 90 degrees clockwise until upright."""
    actions = ("rotate", "flip_h", "flip_v")
    for length in range(4):
        for sequence in itertools.product(actions, repeat=length):
            t = Tile(PIXELS, 0, 0)
            for action in sequence:
                if action == "rotate":
                    t.rotate(90)
                elif action == "flip_h":
                    t.flip_horizontal()
                else:
                    t.flip_vertical()
            if t.is_mirrored:
                t.flip_horizontal()
            for _ in range(4):
                if t.rotation == 0:
                    break
                t.rotate(90)
            assert t.is_correct(0, 0), sequence
            np.testing.assert_array_equal(t.get_display_image(), PIXELS)


# --- is_correct -------------------------------------------------------- #
def test_is_correct_only_at_home_and_upright(tile):
    assert tile.is_correct(1, 2)
    assert not tile.is_correct(0, 0)
    tile.rotate(90)
    assert not tile.is_correct(1, 2)
    tile.reset()
    tile.flip_horizontal()
    assert not tile.is_correct(1, 2)


def test_repr_shows_state(tile):
    assert "home=(1,2)" in repr(tile) and "rotation=0" in repr(tile)
