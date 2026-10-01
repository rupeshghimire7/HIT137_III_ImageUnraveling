"""The sample pictures used by the Random Upload button: there are five,
every one is square, and every one loads and fills the display box."""

import pytest

from engine.image_processor import ImageProcessor
from ui.gui import SAMPLE_IMAGES_DIR, sample_image_paths

SAMPLE_COUNT = 5


def test_there_are_five_sample_pictures():
    assert len(sample_image_paths()) == SAMPLE_COUNT, (
        f"expected {SAMPLE_COUNT} pictures in {SAMPLE_IMAGES_DIR} - "
        "run python scripts/make_sample_images.py and commit them"
    )


@pytest.mark.parametrize("path", sample_image_paths(), ids=lambda path: path.name)
def test_sample_is_square_and_loads(path):
    image = ImageProcessor.load_image(str(path))
    height, width = image.shape[:2]
    assert height == width >= ImageProcessor.DISPLAY_SIZE


@pytest.mark.parametrize("path", sample_image_paths(), ids=lambda path: path.name)
@pytest.mark.parametrize("grid", [3, 4, 5])
def test_sample_fills_the_display_box(path, grid):
    image = ImageProcessor.load_image(str(path))
    square = ImageProcessor.prepare_square(image, grid)
    assert square.shape[:2] == (ImageProcessor.DISPLAY_SIZE, ImageProcessor.DISPLAY_SIZE)
