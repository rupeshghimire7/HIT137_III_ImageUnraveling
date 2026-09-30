"""Tests for engine.image_processor.ImageProcessor."""

import numpy as np
import pytest

from conftest import noise_image, write_image
from engine.fit_strategy import CROP, FIT_STRATEGIES, PAD, FitStrategy
from engine.image_processor import ImageLoadError, ImageProcessor, LoadFailure

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


def load_failure(path):
    with pytest.raises(ImageLoadError) as caught:
        ImageProcessor.load_image(str(path))
    assert str(caught.value)  # always has a message to show the player
    return caught.value.reason


def test_load_errors_say_why(tmp_path):
    text = tmp_path / "notes.txt"
    text.write_text("not an image")
    corrupt = tmp_path / "broken.png"
    corrupt.write_bytes(b"this is really text")
    tiny = write_image(tmp_path / "tiny.png", solid(10, 10, BLUE_BGR))

    assert load_failure(tmp_path / "nope.png") is LoadFailure.NOT_FOUND
    assert load_failure(tmp_path) is LoadFailure.NOT_FOUND  # a folder, not a file
    assert load_failure(text) is LoadFailure.UNSUPPORTED_FORMAT
    assert load_failure(corrupt) is LoadFailure.UNREADABLE
    assert load_failure(tiny) is LoadFailure.TOO_SMALL


def test_renamed_image_still_loads(tmp_path):
    # JPEG data in a file called .bmp: the content matters, not the name.
    jpeg = write_image(tmp_path / "real.jpg", solid(40, 40, BLUE_BGR))
    renamed = tmp_path / "renamed.bmp"
    renamed.write_bytes(jpeg.read_bytes())
    assert ImageProcessor.load_image(str(renamed)).shape == (40, 40, 3)


@pytest.mark.parametrize("fit_mode", [CROP, PAD])
@pytest.mark.parametrize("grid_size", [3, 4, 5])
@pytest.mark.parametrize("height, width", [(613, 997), (997, 613), (100, 2000), (16, 5000)])
def test_every_fit_mode_gives_an_evenly_divisible_square(fit_mode, grid_size, height, width):
    image = noise_image(height, width)
    square = ImageProcessor.prepare_square(image, grid_size, fit_mode=fit_mode)
    side = square.shape[0]
    assert square.shape == (side, side, 3) and square.dtype == np.uint8
    assert side % grid_size == 0
    assert grid_size <= side <= ImageProcessor.DISPLAY_SIZE


def test_pad_keeps_the_whole_picture_in_the_centre():
    image = noise_image(240, 480)   # already fits the box, so it is not resized
    square = ImageProcessor.prepare_square(image, 4, fit_mode=PAD)
    assert square.shape == (480, 480, 3)
    assert np.array_equal(square[120:360], image)


def test_fit_strategies_are_polymorphic_and_leave_the_input_alone():
    image = noise_image(90, 150)
    before = image.copy()
    for strategy in FIT_STRATEGIES.values():
        assert isinstance(strategy, FitStrategy)
        assert strategy.apply(image, 3).shape[0] % 3 == 0
    assert np.array_equal(image, before)


def test_unknown_fit_mode_rejected():
    with pytest.raises(ValueError):
        ImageProcessor.prepare_square(noise_image(50, 50), 3, fit_mode="Stretch")


def test_tiles_are_numbered_in_row_major_order():
    tiles, _ = ImageProcessor.split_into_tiles(noise_image(60, 60), 3)
    assert [t.tile_id for t in tiles] == list(range(9))
