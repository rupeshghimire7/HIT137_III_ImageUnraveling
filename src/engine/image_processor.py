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

import cv2
import numpy as np

from models.tile import Tile


class ImageProcessor:
    """Stateless helper: every method only needs the arguments passed to
    it, so everything is a @staticmethod - there is nothing to construct
    an instance for."""

    #: the square box (in pixels) every loaded image is fitted into.
    #: 480 divides evenly by 3, 4 and 5, which keeps tiles a clean size
    #: for every supported grid.
    DISPLAY_SIZE = 480

    @staticmethod
    def load_image(path):
        """Read an image file from disk and convert it to RGB.

        Raises ValueError if the file cannot be decoded as an image (for
        example the user picked a .txt or .docx file by mistake).
        """
        image = cv2.imread(path, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(
                "Could not read that file as an image.\n"
                "Please choose a JPG, PNG or BMP file."
            )
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    @staticmethod
    def prepare_square(image, grid_size, target_size=DISPLAY_SIZE):
        """Resize `image` (preserving aspect ratio) so it fits inside a
        target_size x target_size box, then centre-crop it to a square
        whose side is an exact multiple of `grid_size`, so it can be cut
        into equal, square tiles (square tiles are what make rotating a
        tile 90 degrees fit back into its slot correctly)."""

        h, w = image.shape[:2]
        scale = target_size / max(h, w)
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Centre-crop to a square using the smaller of the two dimensions.
        side = min(new_h, new_w)
        top = (new_h - side) // 2
        left = (new_w - side) // 2
        square = resized[top:top + side, left:left + side]

        # Trim further so the side length is an exact multiple of grid_size.
        even_side = (side // grid_size) * grid_size
        if even_side < grid_size:
            # Degenerate/tiny image - pad up rather than lose all detail.
            pad = grid_size - side
            square = cv2.copyMakeBorder(square, 0, pad, 0, pad, cv2.BORDER_REPLICATE)
        else:
            square = square[:even_side, :even_side]

        return square

    @staticmethod
    def split_into_tiles(square_image, grid_size):
        """Cut a square image into grid_size x grid_size Tile objects,
        returned as a flat, row-major list, along with the pixel length
        of one tile's edge."""
        side = square_image.shape[0]
        tile_edge = side // grid_size

        tiles = []
        for row in range(grid_size):
            for col in range(grid_size):
                y0, y1 = row * tile_edge, (row + 1) * tile_edge
                x0, x1 = col * tile_edge, (col + 1) * tile_edge
                tile_pixels = square_image[y0:y1, x0:x1].copy()
                tiles.append(Tile(tile_pixels, row, col))

        return tiles, tile_edge

    @staticmethod
    def merge_tiles(tiles, grid_size, tile_edge):
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
