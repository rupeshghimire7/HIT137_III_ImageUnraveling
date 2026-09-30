"""
game_state.py

GameState holds the rules of one round that have nothing to do with
where the tiles are: how many moves were made, how many hints are left,
how long the round has run, whether it is over and how it ended.

OOP concepts demonstrated here
-------------------------------
Encapsulation:
    Every counter and flag is private. They change only through methods
    that enforce the rules (no moves or hints once the round is finished,
    never more than MAX_HINTS hints), so the rest of the program cannot
    put a round into an impossible state.
"""

import time
from collections.abc import Callable

from engine.scoring import ScoringRules

SUPPORTED_GRID_SIZES = (3, 4, 5)
MAX_HINTS = 3


class GameState:
    """Counters, timer and finished/auto-solved flags for a single round."""

    def __init__(
        self, grid_size: int, par: int, clock: Callable[[], float] = time.monotonic
    ) -> None:
        """Start a round on a grid_size x grid_size board that can be
        solved in `par` moves at best.

        `clock` returns the current time in seconds. The default is a
        monotonic clock, so changing the system time cannot break the
        timer; tests pass a fake one.

        Raises ValueError for an unsupported grid size or a negative par.
        """
        if grid_size not in SUPPORTED_GRID_SIZES:
            raise ValueError(
                f"Grid size must be one of {SUPPORTED_GRID_SIZES}, got {grid_size}."
            )
        if par < 0:
            raise ValueError("Par cannot be negative.")

        self._grid_size = grid_size
        self._par = par
        self._clock = clock
        self._moves = 0
        self._hints_used = 0
        self._finished = False
        self._auto_solved = False
        self._start_time = clock()
        self._finish_time: float | None = None

    # ------------------------------------------------------------------ #
    # Moves
    # ------------------------------------------------------------------ #
    def register_move(self) -> None:
        """Count one player move (a swap, rotate or flip). Ignored once
        the round is finished."""
        if not self._finished:
            self._moves += 1

    @property
    def moves(self) -> int:
        """Moves made by the player so far."""
        return self._moves

    @property
    def par(self) -> int:
        """Fewest moves that could have solved the starting board."""
        return self._par

    # ------------------------------------------------------------------ #
    # Hints - the budget is per image and is never refilled
    # ------------------------------------------------------------------ #
    def can_hint(self) -> bool:
        """True while the round is running and hints remain."""
        return not self._finished and self._hints_used < MAX_HINTS

    def consume_hint(self) -> bool:
        """Use up one hint. Returns False (and changes nothing) if none
        are left or the round is finished."""
        if not self.can_hint():
            return False
        self._hints_used += 1
        return True

    @property
    def hints_used(self) -> int:
        """Hints used this round."""
        return self._hints_used

    @property
    def hints_left(self) -> int:
        """Hints still available this round."""
        return MAX_HINTS - self._hints_used

    # ------------------------------------------------------------------ #
    # Finishing
    # ------------------------------------------------------------------ #
    def finish(self, was_auto_solved: bool) -> None:
        """End the round and freeze the timer. Does nothing if the round
        has already finished."""
        if self._finished:
            return
        self._finished = True
        self._auto_solved = was_auto_solved
        self._finish_time = self._clock()

    def reset_after_solve(self) -> None:
        """The Solve button was pressed: clear the moves (and with them
        the score) and end the round as auto-solved."""
        self._moves = 0
        self.finish(was_auto_solved=True)

    @property
    def is_finished(self) -> bool:
        """True once the round has ended, by a win or by Solve."""
        return self._finished

    @property
    def was_auto_solved(self) -> bool:
        """True if the round ended with the Solve button."""
        return self._auto_solved

    # ------------------------------------------------------------------ #
    # Timer and score
    # ------------------------------------------------------------------ #
    def elapsed_seconds(self) -> int:
        """Whole seconds since the round started; stops growing once the
        round is finished."""
        end = self._finish_time if self._finish_time is not None else self._clock()
        return int(end - self._start_time)

    def score(self) -> int:
        """Current score; 0 for an auto-solved round."""
        if self._auto_solved:
            return 0
        return ScoringRules.score(
            self._grid_size, self._moves, self._par, self.elapsed_seconds(), self._hints_used
        )

    def stars(self) -> int:
        """Star rating, 1-3, for a round won by hand; 0 while the round is
        still running or if it was auto-solved."""
        if self._auto_solved or not self._finished:
            return 0
        return ScoringRules.stars(self._moves, self._par, self._hints_used)
