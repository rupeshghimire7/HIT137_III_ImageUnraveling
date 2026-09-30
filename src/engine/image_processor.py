"""
image_processor.py

All OpenCV-based image handling for the tile puzzle: loading a file from
disk, resizing/cropping it to a square that divides evenly into the
requested grid, cutting that square into Tile objects, and re-assembling
a grid of Tile objects back into one image for display.

Keeping every OpenCV call inside this one class means PuzzleBoard and the
GUI never need to import cv2 directly - a clean separation of concerns /
"class interaction" between the image layer, the game-rules layer
(PuzzleBoard) and the presentation layer (gui.py).
"""

import os
from enum import Enum

import cv2
import numpy as np

from engine.fit_strategy import DEFAULT_FIT_MODE, FIT_STRATEGIES
from models.tile import Tile


class LoadFailure(Enum):
    """Why an image file could not be loaded."""

    NOT_FOUND = "not found"
    UNSUPPORTED_FORMAT = "unsupported format"
    UNREADABLE = "unreadable"
    TOO_SMALL = "too small"


class ImageLoadError(ValueError):
    """Raised when a file cannot be used as a puzzle image.

    `reason` says what went wrong; the message (str(error)) is always
    safe to show the player in a message box. It is a ValueError, so
    callers that only care that "the input was bad" can catch that.
    """

    def __init__(self, reason: LoadFailure, message: str) -> None:
        super().__init__(message)
        self.reason = reason


class ImageProcessor:
    """Stateless helper: every method only needs the arguments passed to
    it, so everything is a @staticmethod - there is nothing to construct
    an instance for."""

    #: the square box (in pixels) every loaded image is fitted into.
    #: 480 divides evenly by 3, 4 and 5, which keeps tiles a clean size
    #: for every supported grid.
    DISPLAY_SIZE = 480

    #: file extensions the game accepts (compared case-insensitively).
    ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp")

    #: smallest usable source image, in pixels on its shorter side.
    MIN_SIDE = 16

    @staticmethod
    def load_image(path: str) -> np.ndarray:
        """Read an image file from disk and return it as 8-bit, 3-channel
        RGB.

        The file is read as raw bytes and decoded in memory, which (unlike
        cv2.imread) also works for paths containing non-English characters.
        Grayscale images are expanded to 3 channels, transparent areas of
        PNGs are placed on a white background, and 16-bit images are
        scaled down to 8-bit.

        Raises ImageLoadError (a ValueError) with a message that is safe
        to show the user if the file is missing, is not a JPG/PNG/BMP,
        cannot be decoded as an image, or is smaller than MIN_SIDE pixels.
        """
        name = os.path.basename(path)
        if not os.path.isfile(path):
            raise ImageLoadError(
                LoadFailure.NOT_FOUND,
                f"{name} could not be found.\n"
                "Please check it still exists and try again.",
            )
        if os.path.splitext(path)[1].lower() not in ImageProcessor.ALLOWED_EXTENSIONS:
            raise ImageLoadError(
                LoadFailure.UNSUPPORTED_FORMAT,
                f"{name} is not a supported image.\n"
                "Please choose a JPG, PNG or BMP file.",
            )

        unreadable = ImageLoadError(
            LoadFailure.UNREADABLE,
            f"{name} could not be read as an image - it may be corrupted.\n"
            "Please choose another JPG, PNG or BMP file.",
        )
        try:
            data = np.fromfile(path, dtype=np.uint8)
        except OSError:
            raise unreadable from None

        image = None
        if data.size > 0:
            image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
        if image is None:
            raise unreadable

        image = ImageProcessor._to_rgb(image)
        if min(image.shape[:2]) < ImageProcessor.MIN_SIDE:
            raise ImageLoadError(
                LoadFailure.TOO_SMALL,
                f"{name} is too small to make a puzzle from.\n"
                f"Please choose an image at least {ImageProcessor.MIN_SIDE} pixels "
                "wide and tall.",
            )
        return image

    @staticmethod
    def _to_rgb(image: np.ndarray) -> np.ndarray:
        """Normalise any decoded OpenCV image to 8-bit, 3-channel RGB."""
        if image.dtype == np.uint16:
            image = (image // 257).astype(np.uint8)
        elif image.dtype != np.uint8:
            image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

        if image.shape[2] == 4:
            # Composite onto white so transparent areas don't turn black.
            colour = image[:, :, :3].astype(np.float32)
            alpha = image[:, :, 3:4].astype(np.float32) / 255.0
            white = np.full_like(colour, 255.0)
            image = (colour * alpha + white * (1.0 - alpha)).round().astype(np.uint8)

        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    @staticmethod
    def prepare_square(
        image: np.ndarray,
        grid_size: int,
        target_size: int = DISPLAY_SIZE,
        fit_mode: str = DEFAULT_FIT_MODE,
    ) -> np.ndarray:
        """Resize `image` (preserving aspect ratio) so it fits inside a
        target_size x target_size box, then make it a square whose side is
        an exact multiple of `grid_size`, so it can be cut into equal,
        square tiles (square tiles are what make rotating a tile 90
        degrees fit back into its slot correctly).

        `fit_mode` names the FitStrategy used for that last step: "Crop"
        (cut the picture down to a square) or "Pad" (keep the whole
        picture on a blurred background).

        Raises ValueError for an unknown fit mode.
        """
        if fit_mode not in FIT_STRATEGIES:
            raise ValueError(
                f"Fit mode must be one of {tuple(FIT_STRATEGIES)}, got {fit_mode!r}."
            )

        h, w = image.shape[:2]
        scale = target_size / max(h, w)
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        # Area averaging looks best when shrinking, cubic when enlarging.
        interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
        resized = cv2.resize(image, (new_w, new_h), interpolation=interpolation)

        # Polymorphism: whichever strategy was chosen is applied the same way.
        return FIT_STRATEGIES[fit_mode].apply(resized, grid_size)

    @staticmethod
    def split_into_tiles(square_image: np.ndarray, grid_size: int) -> tuple[list[Tile], int]:
        """Cut a square image into grid_size x grid_size Tile objects,
        returned as a flat, row-major list, along with the pixel length
        of one tile's edge. Each tile gets its own copy of its pixels."""
        side = square_image.shape[0]
        tile_edge = side // grid_size

        tiles = []
        for row in range(grid_size):
            for col in range(grid_size):
                y0, y1 = row * tile_edge, (row + 1) * tile_edge
                x0, x1 = col * tile_edge, (col + 1) * tile_edge
                tile_pixels = square_image[y0:y1, x0:x1].copy()
                tiles.append(Tile(tile_pixels, row, col, tile_id=row * grid_size + col))

        return tiles, tile_edge

    @staticmethod
    def merge_tiles(tiles: list[Tile], grid_size: int, tile_edge: int) -> np.ndarray:
        """Re-assemble the (possibly rotated/flipped/shuffled) tiles - in
        their CURRENT grid order - into a single displayable image."""
        side = tile_edge * grid_size
        canvas = np.zeros((side, side, 3), dtype=np.uint8)

        for index, tile in enumerate(tiles):
            row, col = divmod(index, grid_size)
            y0, y1 = row * tile_edge, (row + 1) * tile_edge
            x0, x1 = col * tile_edge, (col + 1) * tile_edge
            canvas[y0:y1, x0:x1] = tile.get_display_image()

        return canvas
