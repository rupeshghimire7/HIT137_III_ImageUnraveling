"""
scoring.py

How a finished round is scored. The brief only says that Solve "clears
moves and score", so the team defined the score itself:

- Bigger grids are harder, so they start from a bigger base.
- Points are lost for every move beyond par (the fewest moves that could
  have solved the puzzle), for time taken and for each hint used.
- A round finished with the Solve button always scores 0.

Every number used is a named constant below.
"""

BASE_POINTS_PER_TILE = 100      # 900 / 1600 / 2500 for 3x3 / 4x4 / 5x5
PENALTY_PER_EXTRA_MOVE = 15
PENALTY_PER_SECOND = 2
PENALTY_PER_HINT = 150

MAX_STARS = 3
TWO_STAR_PAR_FACTOR = 1.5       # within 1.5 x par still earns two stars


class ScoringRules:
    """Pure scoring functions - no state, so they are easy to test."""

    @staticmethod
    def score(
        grid_size: int, moves: int, par: int, seconds: int, hints_used: int
    ) -> int:
        """Points for a round played by hand. Never negative."""
        base = BASE_POINTS_PER_TILE * grid_size * grid_size
        extra_moves = max(0, moves - par)
        penalty = (
            PENALTY_PER_EXTRA_MOVE * extra_moves
            + PENALTY_PER_SECOND * seconds
            + PENALTY_PER_HINT * hints_used
        )
        return max(0, base - penalty)

    @staticmethod
    def stars(moves: int, par: int, hints_used: int) -> int:
        """Star rating (1-3) for a round won by hand: 3 for matching par
        without hints, 2 for staying within 1.5 x par, otherwise 1."""
        if moves <= par and hints_used == 0:
            return MAX_STARS
        if moves <= TWO_STAR_PAR_FACTOR * par:
            return 2
        return 1
