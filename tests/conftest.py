"""Shared pytest fixtures. Every test image is generated on the fly, so the
suite needs no image files and no display (except the GUI tests, which
skip themselves when no display is available)."""

import cv2
import numpy as np
import pytest


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
