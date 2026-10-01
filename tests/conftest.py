# ====================================================================== #
#  Shared test set-up (fixtures and image helpers) - not a test file.
#  Used by every test_*.py in this folder. Owned by the whole group.
# ====================================================================== #

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def write_image(path, image):
    """Encode `image` (BGR/BGRA/gray, OpenCV order) to `path` by its
    extension. Uses imencode + tofile so non-ASCII paths also work."""
    ok, encoded = cv2.imencode(path.suffix, image)
    assert ok, f"could not encode test image as {path.suffix}"
    encoded.tofile(str(path))
    return path


def noise_image(height, width, seed=0):
    """Random-noise BGR image: no two tiles or orientations look alike."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, (height, width, 3), dtype=np.uint8)


@pytest.fixture
def image_path(tmp_path):
    """Path to a small PNG suitable for building a PuzzleBoard."""
    return str(write_image(tmp_path / "picture.png", noise_image(150, 200)))
