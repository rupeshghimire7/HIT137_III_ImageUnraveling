"""Smoke tests for ui.gui.PuzzleGameApp, driving the real Tkinter widgets
with synthetic click events. Skipped automatically when no display is
available (CI runs them under a virtual X display via xvfb-run)."""

import tkinter as tk
from types import SimpleNamespace

import pytest

from conftest import noise_image, write_image
from ui import gui
from ui.gui import SHIFT_MASK, PuzzleGameApp


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("no display available for Tkinter")
    window.withdraw()
    yield window
    window.destroy()


@pytest.fixture
def dialogs(monkeypatch):
    """Record message boxes instead of blocking on them."""
    shown = []
    monkeypatch.setattr(gui.messagebox, "showinfo", lambda *a, **k: shown.append(("info", a)))
    monkeypatch.setattr(gui.messagebox, "showerror", lambda *a, **k: shown.append(("error", a)))
    return shown


@pytest.fixture
def app(root, dialogs):
    return PuzzleGameApp(root)


@pytest.fixture
def picture(tmp_path):
    return str(write_image(tmp_path / "pic.jpg", noise_image(300, 400)))


def click_event(app, index, shift=False):
    """A fake mouse event at the centre of the tile at `index`."""
    edge = app.board.tile_edge
    row, col = divmod(index, app.board.grid_size)
    return SimpleNamespace(
        x=col * edge + edge // 2,
        y=row * edge + edge // 2,
        state=SHIFT_MASK if shift else 0,
    )


def state(button):
    return str(button["state"])


def load(app, path, grid_size=3):
    app.grid_size_var.set(f"{grid_size} x {grid_size}")
    app.load_image_file(path)


def test_buttons_disabled_before_loading(app):
    assert state(app.hint_btn) == "disabled"
    assert state(app.solve_btn) == "disabled"


def test_bad_file_shows_error_and_keeps_round(app, dialogs, picture, tmp_path):
    load(app, picture)
    board = app.board
    bad = tmp_path / "notes.txt"
    bad.write_text("not an image")
    app.load_image_file(str(bad))
    assert dialogs[-1][0] == "error"
    assert app.board is board


@pytest.mark.parametrize("grid_size", [3, 4, 5])
def test_load_draws_both_panels_and_grid(app, picture, grid_size):
    load(app, picture, grid_size)
    assert app.board.grid_size == grid_size
    assert state(app.hint_btn) == "normal"
    assert len(app.puzzle_canvas.find_withtag("grid")) == 2 * (grid_size - 1)
    assert app.original_canvas.find_all()
    assert app.moves_var.get() == "Moves: 0"


def test_select_deselect_and_swap(app, picture):
    load(app, picture)
    app.on_left_click(click_event(app, 0))
    assert app.selected_index == 0
    assert app.puzzle_canvas.find_withtag("select")
    app.on_left_click(click_event(app, 0))
    assert app.selected_index is None
    assert app.board.moves == 0

    tile_a, tile_b = app.board.tiles[0], app.board.tiles[1]
    app.on_left_click(click_event(app, 0))
    app.on_left_click(click_event(app, 1))
    assert app.board.tiles[0] is tile_b and app.board.tiles[1] is tile_a
    assert app.selected_index is None
    assert app.moves_var.get() == "Moves: 1"


def test_right_click_rotates_clockwise(app, picture):
    load(app, picture)
    tile = app.board.tiles[4]
    before = tile.rotation
    app.on_right_click(click_event(app, 4))
    assert tile.rotation == (before + 90) % 360 or tile.is_mirrored
    assert app.board.moves == 1


def test_shift_click_flips_without_selecting(app, picture):
    load(app, picture)
    tile = app.board.tiles[2]
    mirrored = tile.is_mirrored
    app.on_left_click(click_event(app, 2, shift=True))
    assert tile.is_mirrored != mirrored
    assert app.selected_index is None
    assert app.board.moves == 1


@pytest.mark.parametrize("x, y", [(-5, 10), (10, -5), (10_000, 10), (10, 10_000)])
def test_clicks_outside_image_ignored(app, picture, x, y):
    load(app, picture)
    for handler in (app.on_left_click, app.on_right_click):
        handler(SimpleNamespace(x=x, y=y, state=0))
    assert app.selected_index is None
    assert app.board.moves == 0


def test_hints_mark_both_images_and_clear_after_move(app, picture):
    load(app, picture)
    for _ in range(3):
        app.on_hint()
        assert len(app.puzzle_canvas.find_withtag("hint")) == 1
        assert len(app.original_canvas.find_withtag("hint")) == 1
    assert state(app.hint_btn) == "disabled"
    app.on_right_click(click_event(app, 0))
    assert not app.puzzle_canvas.find_withtag("hint")
    assert not app.original_canvas.find_withtag("hint")


def test_solve_button_solves_and_locks(app, dialogs, picture):
    load(app, picture)
    app.on_right_click(click_event(app, 0))
    app.on_solve()
    assert app.board.is_solved()
    assert app.moves_var.get() == "Moves: 0"
    assert app.remaining_var.get() == "Tiles left: 0"
    assert state(app.hint_btn) == state(app.solve_btn) == "disabled"
    assert dialogs[-1][0] == "info"
    app.on_right_click(click_event(app, 0))
    assert app.board.moves == 0


@pytest.mark.parametrize("grid_size", [3, 4, 5])
def test_player_can_win_with_mouse_actions(app, dialogs, picture, grid_size):
    load(app, picture, grid_size)
    board = app.board
    n = grid_size
    for position in range(n * n):
        home = divmod(position, n)
        current = next(
            i for i, t in enumerate(board.tiles) if (t.home_row, t.home_col) == home
        )
        if current != position:
            app.on_left_click(click_event(app, position))
            app.on_left_click(click_event(app, current))
        tile = board.tiles[position]
        if tile.is_mirrored:
            app.on_left_click(click_event(app, position, shift=True))
        while tile.rotation != 0:
            app.on_right_click(click_event(app, position))
    assert board.is_solved()
    assert app.game_over
    assert len(app.puzzle_canvas.find_withtag("tick")) == n * n
    assert dialogs[-1][0] == "info" and dialogs[-1][1][0] == "Solved!"


def test_loading_new_image_resets_round(app, picture):
    load(app, picture)
    app.on_hint()
    app.on_left_click(click_event(app, 0))
    app.on_solve()
    load(app, picture, 4)
    assert not app.game_over
    assert app.selected_index is None and app.hint_info is None
    assert app.board.moves == 0 and app.board.hints_remaining == 3
    assert state(app.hint_btn) == state(app.solve_btn) == "normal"
