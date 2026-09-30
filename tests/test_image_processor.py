"""Tests for engine.image_processor.ImageProcessor."""

import numpy as np
import pytest

from conftest import noise_image, write_image
from engine.image_processor import ImageProcessor

BLUE_BGR = (255, 0, 0)


def solid(height, width, bgr):
    return np.full((height, width, 3), bgr, dtype=np.uint8)


@pytest.mark.parametrize("name", ["a.jpg", "a.jpeg", "a.png", "a.bmp", "UPPER.JPG"])
def test_loads_supported_formats_as_rgb(tmp_path, name):
    path = write_image(tmp_path / name, solid(40, 60, BLUE_BGR))
    image = ImageProcessor.load_image(str(path))
    assert image.shape == (40, 60, 3)
    assert image.dtype == np.uint8
    # OpenCV's BGR blue must come back as RGB blue.
    assert image[20, 30, 2] > 200 and image[20, 30, 0] < 50


def test_non_ascii_path(tmp_path):
    path = write_image(tmp_path / "photo_ñandú_写真.png", solid(20, 20, BLUE_BGR))
    assert ImageProcessor.load_image(str(path)).shape == (20, 20, 3)


def test_text_file_rejected(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("not an image")
    with pytest.raises(ValueError):
        ImageProcessor.load_image(str(path))


@pytest.mark.parametrize("content", [b"", b"this is really text"])
def test_corrupt_or_empty_png_rejected(tmp_path, content):
    path = tmp_path / "broken.png"
    path.write_bytes(content)
    with pytest.raises(ValueError):
        ImageProcessor.load_image(str(path))


def test_missing_file_rejected(tmp_path):
    with pytest.raises(ValueError):
        ImageProcessor.load_image(str(tmp_path / "nope.png"))


def test_transparent_png_becomes_white(tmp_path):
    bgra = np.zeros((20, 20, 4), dtype=np.uint8)  # fully transparent black
    path = write_image(tmp_path / "clear.png", bgra)
    image = ImageProcessor.load_image(str(path))
    assert image.shape == (20, 20, 3)
    assert (image == 255).all()


def test_grayscale_becomes_three_channels(tmp_path):
    path = write_image(tmp_path / "gray.png", np.full((20, 20), 90, dtype=np.uint8))
    image = ImageProcessor.load_image(str(path))
    assert image.shape == (20, 20, 3)
    assert (image == 90).all()


def test_sixteen_bit_becomes_eight_bit(tmp_path):
    path = write_image(tmp_path / "deep.png", np.full((20, 20, 3), 65535, dtype=np.uint16))
    image = ImageProcessor.load_image(str(path))
    assert image.dtype == np.uint8
    assert (image == 255).all()


@pytest.mark.parametrize("grid_size", [3, 4, 5])
@pytest.mark.parametrize("height, width", [(613, 997), (997, 613), (100, 2000), (50, 50),
                                           (480, 480), (7, 7)])
def test_prepare_square_divides_evenly(grid_size, height, width):
    square = ImageProcessor.prepare_square(noise_image(height, width), grid_size)
    side = square.shape[0]
    assert square.shape[1] == side
    assert side % grid_size == 0
    assert grid_size <= side <= ImageProcessor.DISPLAY_SIZE


def test_prepare_square_preserves_aspect_ratio():
    # 200x400 scales by 1.2 to 240x480 (not stretched), then is cropped to
    # 240x240 - so the square side equals the scaled shorter edge.
    square = ImageProcessor.prepare_square(noise_image(200, 400), 3)
    assert square.shape[:2] == (240, 240)


@pytest.mark.parametrize("grid_size", [3, 4, 5])
def test_split_and_merge_round_trip(grid_size):
    square = ImageProcessor.prepare_square(noise_image(300, 300), grid_size)
    tiles, edge = ImageProcessor.split_into_tiles(square, grid_size)
    assert len(tiles) == grid_size * grid_size
    assert edge * grid_size == square.shape[0]
    for index, tile in enumerate(tiles):
        pixels = tile.get_display_image()
        assert pixels.shape == (edge, edge, 3)
        assert not np.shares_memory(pixels, square)
        assert tile.is_correct(*divmod(index, grid_size))
    merged = ImageProcessor.merge_tiles(tiles, grid_size, edge)
    assert np.array_equal(merged, square)
