"""Smoke tests for ui.gui.PuzzleGameApp, driving the real Tkinter widgets
with synthetic click events. Skipped automatically when no display is
available (CI runs them under a virtual X display via xvfb-run)."""

import tkinter as tk
from types import SimpleNamespace

import cv2
import pytest

from conftest import noise_image, write_image
from engine.fit_strategy import PAD
from ui import gui
from ui.panels import CANVAS_SIZE, SHIFT_MASK, TAG_GRID, TAG_HINT, TAG_SELECT, TAG_TICK
from ui.theme import GRADIENT_PERIOD, GradientBackground, gradient_image


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
    return gui.PuzzleGameApp(root)


@pytest.fixture
def picture(tmp_path):
    # 300x400 is cropped to a 360 px square, so the image is smaller than
    # the canvas and sits centred in it - clicks must allow for the offset.
    return str(write_image(tmp_path / "pic.jpg", noise_image(300, 400)))


def click_event(app, index, shift=False):
    """A fake mouse event at the centre of the tile at `index`."""
    row, col = divmod(index, app.board.grid_size)
    x0, y0, x1, y1 = app.puzzle_panel.cell_box(row, col)
    return SimpleNamespace(
        x=int((x0 + x1) / 2), y=int((y0 + y1) / 2), state=SHIFT_MASK if shift else 0
    )


def left_click(app, index, shift=False):
    app.puzzle_panel.left_click(click_event(app, index, shift))


def right_click(app, index):
    app.puzzle_panel.right_click(click_event(app, index))


def state(button):
    return str(button["state"])


def load(app, path, grid_size=3):
    app.grid_size_var.set(f"{grid_size} x {grid_size}")
    app.load_image_file(path)


def test_buttons_disabled_before_loading(app):
    assert state(app.hint_btn) == "disabled"
    assert state(app.solve_btn) == "disabled"
    assert app.grid_size_var.get() == "3 x 3"


def test_clicks_before_loading_are_ignored(app):
    event = SimpleNamespace(x=100, y=100, state=0)
    app.puzzle_panel.left_click(event)
    app.puzzle_panel.right_click(event)
    app.on_hint()
    app.on_solve()
    assert app.board is None


def test_bad_file_shows_error_and_keeps_round(app, dialogs, picture, tmp_path):
    load(app, picture)
    board = app.board
    bad = tmp_path / "notes.txt"
    bad.write_text("not an image")
    app.load_image_file(str(bad))
    assert dialogs[-1][0] == "error"
    assert "notes.txt" in dialogs[-1][1][1]
    assert app.board is board


@pytest.mark.parametrize("grid_size", [3, 4, 5])
def test_load_draws_both_panels_and_grid(app, picture, grid_size):
    load(app, picture, grid_size)
    assert app.board.grid_size == grid_size
    assert state(app.hint_btn) == "normal"
    assert app.hint_btn["text"] == "Hint (3)"
    for panel in (app.puzzle_panel, app.original_panel):
        assert len(panel.canvas.find_withtag(TAG_GRID)) == 2 * (grid_size - 1)
    assert app.moves_var.get() == "Moves: 0"
    assert app.score_var.get().startswith("Score: ")
    assert app.status_var.get() == gui.STATUS_PLAYING


def test_pad_fit_mode_keeps_the_whole_picture(app, picture):
    app.fit_mode_var.set(PAD)
    load(app, picture)
    assert app.board.reference_image.shape[:2] == (480, 480)


def test_select_deselect_and_swap(app, picture):
    load(app, picture)
    left_click(app, 0)
    assert app.selected_index == 0
    assert app.puzzle_panel.canvas.find_withtag(TAG_SELECT)
    left_click(app, 0)
    assert app.selected_index is None
    assert app.board.moves == 0

    tile_a, tile_b = app.board.tiles[0], app.board.tiles[1]
    left_click(app, 0)
    left_click(app, 1)
    assert app.board.tiles[0] is tile_b and app.board.tiles[1] is tile_a
    assert app.selected_index is None
    assert app.moves_var.get() == "Moves: 1"


def test_right_click_rotates_clockwise(app, picture):
    load(app, picture)
    tile = app.board.tiles[4]
    before = tile.get_display_image().copy()
    right_click(app, 4)
    assert (tile.get_display_image() == cv2.rotate(before, cv2.ROTATE_90_CLOCKWISE)).all()
    assert app.board.moves == 1


def test_shift_click_flips_without_selecting(app, picture):
    load(app, picture)
    tile = app.board.tiles[2]
    mirrored = tile.is_mirrored
    left_click(app, 2, shift=True)
    assert tile.is_mirrored != mirrored
    assert app.selected_index is None
    assert app.board.moves == 1


@pytest.mark.parametrize("x, y", [(-5, 10), (10, -5), (10_000, 10), (10, 10_000), (240, 5)])
def test_clicks_outside_image_ignored(app, picture, x, y):
    # (240, 5) is inside the canvas but in the margin above the image.
    load(app, picture)
    for handler in (app.puzzle_panel.left_click, app.puzzle_panel.right_click):
        handler(SimpleNamespace(x=x, y=y, state=0))
    assert app.selected_index is None
    assert app.board.moves == 0


def test_original_panel_has_no_click_bindings(app, picture):
    load(app, picture)
    assert not app.original_panel.canvas.bind()


def test_hints_mark_both_images_and_clear_after_move(app, picture):
    load(app, picture)
    for used in range(1, 4):
        app.on_hint()
        assert len(app.puzzle_panel.canvas.find_withtag(TAG_HINT)) == 1
        assert len(app.original_panel.canvas.find_withtag(TAG_HINT)) == 1
        assert app.hint_btn["text"] == f"Hint ({3 - used})"
    assert state(app.hint_btn) == "disabled"
    right_click(app, 0)
    assert not app.puzzle_panel.canvas.find_withtag(TAG_HINT)
    assert not app.original_panel.canvas.find_withtag(TAG_HINT)


def test_solve_button_solves_and_locks(app, dialogs, picture):
    load(app, picture)
    right_click(app, 0)
    app.on_solve()
    assert app.board.is_solved()
    assert app.moves_var.get() == "Moves: 0"
    assert app.score_var.get() == "Score: 0"
    assert app.remaining_var.get() == "Tiles left: 0"
    assert state(app.hint_btn) == state(app.solve_btn) == "disabled"
    assert dialogs[-1][0] == "info"
    assert app.status_var.get() == gui.STATUS_AUTO_SOLVED
    right_click(app, 0)
    left_click(app, 0)
    assert app.board.moves == 0 and app.selected_index is None


@pytest.mark.parametrize("grid_size", [3, 4, 5])
def test_player_can_win_with_mouse_actions(app, dialogs, picture, grid_size):
    load(app, picture, grid_size)
    board = app.board
    n = grid_size
    for position in range(n * n):
        current = next(i for i, t in enumerate(board.tiles) if t.tile_id == position)
        if current != position:
            left_click(app, position)
            left_click(app, current)
        tile = board.tiles[position]
        if tile.is_mirrored:
            left_click(app, position, shift=True)
        while tile.rotation != 0:
            right_click(app, position)
    assert board.is_solved()
    assert app.game_over
    assert len(app.puzzle_panel.canvas.find_withtag(TAG_TICK)) == n * n
    kind, (title, message) = dialogs[-1]
    assert kind == "info" and title == "Solved!"
    assert f"{board.moves} moves" in message
    assert "Score:" in message and "Time:" in message and "★" in message


def test_changing_grid_size_mid_round_shows_a_note(app, picture):
    app.on_setting_changed()
    assert app.status_var.get() == gui.STATUS_WELCOME
    load(app, picture)
    app.on_setting_changed()
    assert app.status_var.get() == gui.STATUS_SETTING_CHANGED
    assert app.board.grid_size == 3


def test_loading_new_image_resets_round(app, picture):
    load(app, picture)
    app.on_hint()
    left_click(app, 0)
    app.on_solve()
    load(app, picture, 4)
    assert not app.game_over
    assert app.selected_index is None and app.hint_info is None
    assert app.board.moves == 0 and app.board.hints_remaining == 3
    assert state(app.hint_btn) == state(app.solve_btn) == "normal"
    assert app.hint_btn["text"] == "Hint (3)"
    assert not app.original_panel.canvas.find_withtag(TAG_HINT)


def test_picture_is_centred_in_both_panels(app, picture):
    load(app, picture)   # cropped to a 360 px square inside the 480 px canvas
    side = app.board.reference_image.shape[0]
    margin = (CANVAS_SIZE - side) // 2
    for panel in (app.original_panel, app.puzzle_panel):
        x0, y0, x1, y1 = panel.canvas.bbox(panel.canvas.find_all()[0])
        assert (x0, y0, x1, y1) == (margin, margin, margin + side, margin + side)


def test_gradient_sits_under_every_other_widget(app):
    assert isinstance(app.winfo_children()[0], GradientBackground)


def test_gradient_loops_without_a_seam():
    strip = gradient_image(GRADIENT_PERIOD + 50, 20)
    assert strip.shape == (20, GRADIENT_PERIOD + 50, 3)
    assert (strip[:, :50] == strip[:, GRADIENT_PERIOD:]).all()


def test_random_upload_loads_a_square_sample(app):
    app.on_random_image()
    assert app.board is not None and not app.game_over
    assert app.last_sample in gui.sample_image_paths()
    image = app.board.reference_image
    assert image.shape[0] == image.shape[1] == CANVAS_SIZE


def test_random_upload_never_repeats_the_same_picture_twice_in_a_row(app):
    previous = None
    for _ in range(10):
        app.on_random_image()
        assert app.last_sample != previous
        previous = app.last_sample


def test_random_upload_without_samples_shows_error(app, dialogs, monkeypatch):
    monkeypatch.setattr(gui, "sample_image_paths", lambda: [])
    app.on_random_image()
    assert dialogs[-1][0] == "error" and app.board is None
