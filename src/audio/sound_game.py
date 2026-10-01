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

from audio.sound_manager import SoundManager
from engine.image_processor import ImageProcessor
from ui.gui import SHIFT_MASK, PuzzleGameApp


class SoundPuzzleGameApp(PuzzleGameApp):
    """PuzzleGameApp with background music and sound effects."""

    def __init__(self, master, sound=None):
        self.sound = sound if sound is not None else SoundManager()
        super().__init__(master)
        master.bind("<KeyPress-m>", self._on_toggle_mute)
        master.bind("<KeyPress-M>", self._on_toggle_mute)
        master.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _correct_count(self):
        board = self.board
        return board.grid_size ** 2 - len(board.incorrect_indices())

    def _play_move_sound(self, correct_before, normal_sound):
        """After a move: winner is handled in _check_completion; here we
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

    def _on_toggle_mute(self, _event=None):
        self.sound.toggle_mute()

    def _on_close(self):
        self.sound.stop_music()
        self.master.destroy()

    # ------------------------------------------------------------------ #
    # Game start
    # ------------------------------------------------------------------ #
    def load_image_file(self, path):
        # Check the file first so the error sound plays together with the
        # error message box that the original method shows.
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
    def on_left_click(self, event):
        if event.state & SHIFT_MASK or self.board is None or self.game_over:
            super().on_left_click(event)  # shift-click goes to on_shift_click
            return

        moves_before = self.board.moves
        selected_before = self.selected_index
        correct_before = self._correct_count()
        super().on_left_click(event)

        if self.board.moves > moves_before:
            self._play_move_sound(correct_before, "swap")
        elif self.selected_index != selected_before:
            self.sound.play("select")

    def on_shift_click(self, event):
        if self.board is None or self.game_over:
            super().on_shift_click(event)
            return
        moves_before = self.board.moves
        correct_before = self._correct_count()
        super().on_shift_click(event)
        if self.board.moves > moves_before:
            self._play_move_sound(correct_before, "flip")

    def on_right_click(self, event):
        if self.board is None or self.game_over:
            super().on_right_click(event)
            return
        moves_before = self.board.moves
        correct_before = self._correct_count()
        super().on_right_click(event)
        if self.board.moves > moves_before:
            self._play_move_sound(correct_before, "rotate")

    # ------------------------------------------------------------------ #
    # Hint / Solve / Win / Errors
    # ------------------------------------------------------------------ #
    def on_hint(self):
        if self.board is not None and not self.game_over:
            if self.board.hints_remaining > 0:
                self.sound.play("hint")
            else:
                self.sound.play("error")
        super().on_hint()

    def on_solve(self):
        if self.board is not None and not self.game_over:
            self.sound.stop_music()
            self.sound.play("auto_solve")
        super().on_solve()

    def _check_completion(self):
        # Play before the original shows its (blocking) "Solved!" box.
        if self.board.is_solved() and not self.game_over:
            self.sound.stop_music()
            self.sound.play("winner")
        super()._check_completion()

    def _report_callback_exception(self, exc_type, exc_value, exc_traceback):
        self.sound.play("error")
        super()._report_callback_exception(exc_type, exc_value, exc_traceback)
