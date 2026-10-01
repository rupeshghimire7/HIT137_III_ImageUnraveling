"""Smoke tests for audio.sound_game.SoundPuzzleGameApp: every overridden
handler still matches PuzzleGameApp and plays the right sound. A fake
sound manager records the sounds, so no audio device is needed. Skipped
automatically when no display is available."""

import tkinter as tk

import pytest

from audio.sound_game import SoundPuzzleGameApp
from conftest import noise_image, write_image
from ui import gui


class FakeSound:
    """Stands in for SoundManager and remembers what was played."""

    def __init__(self):
        self.played = []
        self.music = False

    def play(self, name):
        self.played.append(name)

    def start_music(self):
        self.music = True

    def stop_music(self):
        self.music = False

    def toggle_mute(self):
        return True


@pytest.fixture
def app(monkeypatch, tmp_path):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display available for Tkinter")
    root.withdraw()
    monkeypatch.setattr(gui.messagebox, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(gui.messagebox, "showerror", lambda *a, **k: None)
    game = SoundPuzzleGameApp(root, sound=FakeSound())
    yield game
    root.destroy()


@pytest.fixture
def picture(tmp_path):
    return str(write_image(tmp_path / "pic.png", noise_image(300, 300)))


def test_loading_starts_music(app, picture):
    app.load_image_file(picture)
    assert app.sound.played == ["game_start"] and app.sound.music


def test_bad_file_plays_error(app, tmp_path):
    bad = tmp_path / "notes.txt"
    bad.write_text("not an image")
    app.load_image_file(str(bad))
    assert app.sound.played == ["error"] and app.board is None


def test_tile_actions_play_sounds(app, picture):
    app.load_image_file(picture)
    app.on_tile_left(0, 0)
    assert app.sound.played[-1] == "select"
    app.on_tile_left(0, 1)
    app.on_tile_right(1, 1)
    app.on_tile_shift_left(2, 2)
    move_sounds = {"swap", "rotate", "flip", "correct_tile", "mistake", "winner"}
    assert len(app.sound.played) == 5
    assert set(app.sound.played[2:]) <= move_sounds
    assert app.board.moves == 3


def test_hint_and_solve_sounds(app, picture):
    app.load_image_file(picture)
    app.on_hint()
    app.on_solve()
    assert app.sound.played[-2:] == ["hint", "auto_solve"]
    assert app.game_over and not app.sound.music
