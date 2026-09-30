"""
fit_strategy.py

The ways a resized image can be made into a square whose side divides
evenly by the grid size, so it can be cut into equal, square tiles.

OOP concepts demonstrated here
-------------------------------
Inheritance:
    FitStrategy (abstract base)
        -> CropFit   cut the picture down to a square (default)
        -> PadFit    keep the whole picture, fill the rest of the square

Polymorphism:
    ImageProcessor.prepare_square() looks a strategy up by name in
    FIT_STRATEGIES and calls .apply() on it, without knowing which one it
    got.
"""

from abc import ABC, abstractmethod

import cv2
import numpy as np

CROP = "Crop"
PAD = "Pad"

# PadFit's border: a blurred, darkened copy of the picture itself.
PAD_BLUR_SIGMA = 25
PAD_BRIGHTNESS = 0.6


class FitStrategy(ABC):
    """Turns an image of any shape into a square that a grid divides
    evenly."""

    @abstractmethod
    def apply(self, image: np.ndarray, grid_size: int) -> np.ndarray:
        """Return a square 3-channel image whose side is a multiple of
        `grid_size` (and at least `grid_size`). `image` is not modified."""


class CropFit(FitStrategy):
    """Centre-crops the image to a square, then trims the side down to
    the largest multiple of the grid size. Parts of a non-square picture
    are cut off."""

    def apply(self, image: np.ndarray, grid_size: int) -> np.ndarray:
        """See FitStrategy.apply."""
        height, width = image.shape[:2]
        side = min(height, width)
        top = (height - side) // 2
        left = (width - side) // 2
        square = image[top:top + side, left:left + side]

        even_side = side - side % grid_size
        if even_side == 0:
            # Thinner than one pixel per tile (an extreme strip) - stretch
            # the edge out rather than return an empty image.
            pad = grid_size - side
            return cv2.copyMakeBorder(square, 0, pad, 0, pad, cv2.BORDER_REPLICATE)
        return square[:even_side, :even_side].copy()


class PadFit(FitStrategy):
    """Keeps the whole picture: it is placed in the centre of a square
    filled with a blurred, darkened copy of itself."""

    def apply(self, image: np.ndarray, grid_size: int) -> np.ndarray:
        """See FitStrategy.apply."""
        height, width = image.shape[:2]
        side = max(height, width)
        side += (grid_size - side % grid_size) % grid_size

        background = cv2.resize(image, (side, side), interpolation=cv2.INTER_LINEAR)
        background = cv2.GaussianBlur(background, (0, 0), PAD_BLUR_SIGMA)
        background = (background * PAD_BRIGHTNESS).astype(np.uint8)

        top = (side - height) // 2
        left = (side - width) // 2
        background[top:top + height, left:left + width] = image
        return background


#: Fit mode name -> strategy, in the order shown to the player. The first
#: entry is the default.
FIT_STRATEGIES: dict[str, FitStrategy] = {CROP: CropFit(), PAD: PadFit()}
DEFAULT_FIT_MODE = CROP
