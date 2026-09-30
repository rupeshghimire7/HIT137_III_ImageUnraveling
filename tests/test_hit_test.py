"""Tests for ui.hit_test.pixel_to_cell - pure arithmetic, no display."""

import pytest

from ui.hit_test import pixel_to_cell

SIDE = 360
LEFT, TOP = 60, 40   # the image does not start at the canvas corner


@pytest.mark.parametrize("n", [3, 4, 5])
def test_centre_first_and_last_pixel_of_every_cell(n):
    cell = SIDE // n
    for row in range(n):
        for col in range(n):
            x0, y0 = LEFT + col * cell, TOP + row * cell
            for dx, dy in [(cell // 2, cell // 2), (0, 0), (cell - 1, cell - 1)]:
                assert pixel_to_cell(x0 + dx, y0 + dy, LEFT, TOP, SIDE, n) == (row, col)


@pytest.mark.parametrize("n", [3, 4, 5])
def test_grid_line_belongs_to_the_cell_it_starts(n):
    line = LEFT + SIDE // n
    assert pixel_to_cell(line, TOP, LEFT, TOP, SIDE, n) == (0, 1)
    assert pixel_to_cell(line - 1, TOP, LEFT, TOP, SIDE, n) == (0, 0)


@pytest.mark.parametrize(
    "x, y",
    [(LEFT - 1, TOP), (LEFT, TOP - 1), (LEFT + SIDE, TOP), (LEFT, TOP + SIDE), (-5, -5), (0, 0)],
)
def test_outside_the_image_is_none(x, y):
    assert pixel_to_cell(x, y, LEFT, TOP, SIDE, 3) is None


def test_no_image_is_none():
    assert pixel_to_cell(10, 10, 0, 0, 0, 0) is None
