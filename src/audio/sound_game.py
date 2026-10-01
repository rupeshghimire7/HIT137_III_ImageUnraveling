"""
sound_game.py

SoundPuzzleGameApp adds music and sound effects to PuzzleGameApp without
editing gui.py. Each overridden method decides which sound fits, then
calls the original method (super()) so the game logic is unchanged.

Sounds (all in assets/sounds):
    game_start + background_music - a new image is loaded
    select       - a tile is selected / deselected
    swap / rotate / flip - a normal move
    correct_tile - the move put more tiles in the right place
    mistake      - the move made the picture worse (fewer correct tiles)
    hint         - Hint button
    error        - image could not be loaded, no hints left, or any error
    winner       - the player solves the puzzle
    auto_solve   - the Solve button finishes the puzzle

Press M at any time to mute / unmute.
"""

import tkinter as tk
from collections.abc import Callable
from types import TracebackType

from audio.sound_manager import SoundManager
from engine.image_processor import ImageProcessor
from ui.gui import PuzzleGameApp


class SoundPuzzleGameApp(PuzzleGameApp):
    """PuzzleGameApp with background music and sound effects."""

    def __init__(self, master: tk.Tk, sound: SoundManager | None = None) -> None:
        """Build the game window; `sound` can be replaced (e.g. by tests)."""
        self.sound = sound if sound is not None else SoundManager()
        super().__init__(master)
        master.bind("<KeyPress-m>", self._on_toggle_mute)
        master.bind("<KeyPress-M>", self._on_toggle_mute)
        master.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _correct_count(self) -> int:
        """How many tiles are in their home cell the right way up."""
        board = self.board
        return board.grid_size ** 2 - len(board.incorrect_indices())

    def _play_move_sound(self, correct_before: int, normal_sound: str) -> None:
        """After a move: the winner sound is handled in _complete; here we
        pick correct_tile, mistake or the normal move sound."""
        if self.game_over:
            return
        correct_after = self._correct_count()
        if correct_after > correct_before:
            self.sound.play("correct_tile")
        elif correct_after < correct_before:
            self.sound.play("mistake")
        else:
            self.sound.play(normal_sound)

    def _with_move_sound(
        self, action: Callable[[int, int], None], row: int, col: int, normal_sound: str
    ) -> None:
        """Run a rotate/flip handler and play the matching sound if it
        counted as a move."""
        if self.board is None or self.game_over:
            action(row, col)
            return
        moves_before = self.board.moves
        correct_before = self._correct_count()
        action(row, col)
        if self.board.moves > moves_before:
            self._play_move_sound(correct_before, normal_sound)

    def _on_toggle_mute(self, _event: tk.Event | None = None) -> None:
        self.sound.toggle_mute()

    def _on_close(self) -> None:
        self.sound.stop_music()
        self.master.destroy()

    # ------------------------------------------------------------------ #
    # Game start
    # ------------------------------------------------------------------ #
    def load_image_file(self, path: str) -> None:
        """Check the file first so the error sound plays together with the
        error message box that the original method shows."""
        try:
            ImageProcessor.load_image(path)
        except Exception:
            self.sound.play("error")
            super().load_image_file(path)
            return

        old_board = self.board
        super().load_image_file(path)
        if self.board is not old_board:
            self.sound.play("game_start")
            self.sound.start_music()

    # ------------------------------------------------------------------ #
    # Player actions
    # ------------------------------------------------------------------ #
    def on_tile_left(self, row: int, col: int) -> None:
        """Select / deselect sounds, or the sound of the swap it made."""
        if self.board is None or self.game_over:
            super().on_tile_left(row, col)
            return
        moves_before = self.board.moves
        selected_before = self.selected_index
        correct_before = self._correct_count()
        super().on_tile_left(row, col)

        if self.board.moves > moves_before:
            self._play_move_sound(correct_before, "swap")
        elif self.selected_index != selected_before:
            self.sound.play("select")

    def on_tile_right(self, row: int, col: int) -> None:
        """Rotate, with its sound."""
        self._with_move_sound(super().on_tile_right, row, col, "rotate")

    def on_tile_shift_left(self, row: int, col: int) -> None:
        """Flip, with its sound."""
        self._with_move_sound(super().on_tile_shift_left, row, col, "flip")

    # ------------------------------------------------------------------ #
    # Hint / Solve / Win / Errors
    # ------------------------------------------------------------------ #
    def on_hint(self) -> None:
        """Hint sound, or the error sound when no hints are left."""
        if self.board is not None and not self.game_over:
            if self.board.hints_remaining > 0:
                self.sound.play("hint")
            else:
                self.sound.play("error")
        super().on_hint()

    def on_solve(self) -> None:
        """Stop the music and play the auto-solve sound."""
        if self.board is not None and not self.game_over:
            self.sound.stop_music()
            self.sound.play("auto_solve")
        super().on_solve()

    def _complete(self, auto_solved: bool) -> None:
        """Play the winner sound before the original shows its (blocking)
        "Solved!" box. A Solve-button finish already played its sound."""
        if not auto_solved:
            self.sound.stop_music()
            self.sound.play("winner")
        super()._complete(auto_solved)

    def _report_callback_exception(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None:
        self.sound.play("error")
        super()._report_callback_exception(exc_type, exc_value, exc_traceback)
