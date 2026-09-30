"""
hit_test.py

Maps a mouse position to the grid cell under it. Kept free of Tkinter so
it can be unit-tested without a window.
"""


def pixel_to_cell(
    x: float, y: float, image_left: int, image_top: int, image_side: int, grid_size: int
) -> tuple[int, int] | None:
    """Return the (row, col) of the cell at canvas position (x, y), or
    None if the position is outside the image.

    The image is a square of `image_side` pixels whose top-left corner is
    at (image_left, image_top) on the canvas, divided into
    grid_size x grid_size equal cells.
    """
    if image_side <= 0 or grid_size <= 0:
        return None
    local_x = x - image_left
    local_y = y - image_top
    if not (0 <= local_x < image_side and 0 <= local_y < image_side):
        return None

    cell_size = image_side / grid_size
    # min() guards the very last pixel against floating-point rounding.
    row = min(int(local_y // cell_size), grid_size - 1)
    col = min(int(local_x // cell_size), grid_size - 1)
    return row, col
