# ====================================================================== #
#  Unit tests for: src/engine/image_processor.py  (class ImageProcessor)
#
#  Student name : John Karki
#  Student ID   : S403518
#  Layer        : Image processing (OpenCV)
#
#  Run only this file (from the project root):
#      python -m pytest tests/test_image_processor.py -v
# ====================================================================== #
"""Tests for ImageProcessor: loading JPG/PNG/BMP (incl. grayscale,
transparent and 16-bit images), clear errors for bad files, resizing and
cropping to a square that divides by 3/4/5, splitting into tiles and
merging them back into the exact same picture."""

import cv2
import numpy as np
import pytest

from conftest import noise_image, write_image
from engine.image_processor import ImageProcessor
from models.tile import Tile


# --- load_image -------------------------------------------------------- #
def test_png_loaded_as_rgb(tmp_path):
    bgr = noise_image(30, 40)
    path = write_image(tmp_path / "img.png", bgr)
    loaded = ImageProcessor.load_image(str(path))
    assert loaded.shape == (30, 40, 3) and loaded.dtype == np.uint8
    np.testing.assert_array_equal(loaded, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


@pytest.mark.parametrize("ext", [".jpg", ".bmp"])
def test_other_formats_load(tmp_path, ext):
    path = write_image(tmp_path / f"img{ext}", noise_image(20, 20))
    assert ImageProcessor.load_image(str(path)).shape == (20, 20, 3)


def test_grayscale_becomes_three_channels(tmp_path):
    # At least ImageProcessor.MIN_SIDE (16 px) - smaller files are rejected.
    gray = np.full((16, 18), 77, dtype=np.uint8)
    path = write_image(tmp_path / "gray.png", gray)
    loaded = ImageProcessor.load_image(str(path))
    assert loaded.shape == (16, 18, 3)
    assert (loaded == 77).all()


def test_transparent_png_goes_on_white(tmp_path):
    bgra = np.zeros((16, 16, 4), dtype=np.uint8)   # fully transparent black
    path = write_image(tmp_path / "clear.png", bgra)
    loaded = ImageProcessor.load_image(str(path))
    assert loaded.shape == (16, 16, 3)
    assert (loaded == 255).all()


def test_16_bit_png_scaled_to_8_bit(tmp_path):
    img16 = np.full((16, 16, 3), 65535, dtype=np.uint16)
    path = write_image(tmp_path / "deep.png", img16)
    loaded = ImageProcessor.load_image(str(path))
    assert loaded.dtype == np.uint8 and (loaded == 255).all()


def test_non_ascii_path_loads(tmp_path):
    path = write_image(tmp_path / "छवि_图片.png", noise_image(16, 16))
    assert ImageProcessor.load_image(str(path)).shape == (16, 16, 3)


def test_non_image_file_raises_value_error(tmp_path):
    bad = tmp_path / "notes.txt"
    bad.write_text("definitely not an image")
    with pytest.raises(ValueError):
        ImageProcessor.load_image(str(bad))


def test_empty_file_raises_value_error(tmp_path):
    empty = tmp_path / "empty.png"
    empty.write_bytes(b"")
    with pytest.raises(ValueError):
        ImageProcessor.load_image(str(empty))


def test_missing_file_raises_value_error(tmp_path):
    with pytest.raises(ValueError):
        ImageProcessor.load_image(str(tmp_path / "missing.png"))


# --- prepare_square ---------------------------------------------------- #
@pytest.mark.parametrize("size", [(640, 480), (480, 640), (1000, 1000), (123, 457), (50, 30)])
@pytest.mark.parametrize("grid", [3, 4, 5])
def test_square_and_divisible(size, grid):
    w, h = size
    square = ImageProcessor.prepare_square(noise_image(h, w), grid)
    assert square.shape[0] == square.shape[1]
    assert square.shape[0] % grid == 0
    assert square.shape[0] <= ImageProcessor.DISPLAY_SIZE


@pytest.mark.parametrize("grid", [3, 4, 5])
def test_large_and_small_images_fill_display_box(grid):
    for side in (960, 120):   # shrunk and enlarged
        square = ImageProcessor.prepare_square(noise_image(side, side), grid)
        assert square.shape[:2] == (480, 480)


def test_custom_target_size():
    square = ImageProcessor.prepare_square(noise_image(200, 300), 4, target_size=100)
    assert square.shape[0] <= 100 and square.shape[0] % 4 == 0


def test_tiny_image_padded_not_crashed():
    square = ImageProcessor.prepare_square(noise_image(2, 2), 5, target_size=2)
    assert square.shape[0] == square.shape[1] >= 5


# --- split_into_tiles / merge_tiles ------------------------------------ #
@pytest.mark.parametrize("grid", [3, 4, 5])
def test_split_gives_row_major_tiles(grid):
    square = ImageProcessor.prepare_square(noise_image(480, 480), grid)
    tiles, edge = ImageProcessor.split_into_tiles(square, grid)
    assert len(tiles) == grid * grid
    assert edge == square.shape[0] // grid
    for i, tile in enumerate(tiles):
        assert isinstance(tile, Tile)
        assert (tile.home_row, tile.home_col) == divmod(i, grid)
        assert tile.get_display_image().shape == (edge, edge, 3)


def test_split_tile_pixels_match_source():
    square = ImageProcessor.prepare_square(noise_image(480, 480), 3)
    tiles, edge = ImageProcessor.split_into_tiles(square, 3)
    np.testing.assert_array_equal(               # row 1, col 2 -> index 5
        tiles[5].get_display_image(), square[edge:2 * edge, 2 * edge:3 * edge]
    )


def test_split_tiles_are_independent_copies():
    square = ImageProcessor.prepare_square(noise_image(480, 480), 3)
    tiles, _ = ImageProcessor.split_into_tiles(square, 3)
    square[:] = 0
    assert tiles[0].get_display_image().any()


@pytest.mark.parametrize("grid", [3, 4, 5])
def test_merge_rebuilds_original(grid):
    square = ImageProcessor.prepare_square(noise_image(400, 500), grid)
    tiles, edge = ImageProcessor.split_into_tiles(square, grid)
    merged = ImageProcessor.merge_tiles(tiles, grid, edge)
    assert merged.dtype == np.uint8
    np.testing.assert_array_equal(merged, square)


def test_merge_uses_current_order_and_orientation():
    square = ImageProcessor.prepare_square(noise_image(480, 480), 3)
    tiles, e = ImageProcessor.split_into_tiles(square, 3)
    tiles[0], tiles[1] = tiles[1], tiles[0]
    tiles[4].rotate(90)
    merged = ImageProcessor.merge_tiles(tiles, 3, e)
    np.testing.assert_array_equal(merged[0:e, 0:e], square[0:e, e:2 * e])
    np.testing.assert_array_equal(
        merged[e:2 * e, e:2 * e],
        cv2.rotate(square[e:2 * e, e:2 * e], cv2.ROTATE_90_CLOCKWISE),
    )
