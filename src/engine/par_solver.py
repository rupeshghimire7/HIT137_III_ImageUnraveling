"""
par_solver.py

Works out "par": the fewest moves that can solve a board. The score
compares the player's move count against it.

Rotating or flipping acts on whatever tile sits in a cell, so putting
tiles in the right cells and turning them the right way up are
independent problems, and the exact minimum is simply the two added
together:

    par = swaps needed + turns needed
"""

from collections import deque

from models.tile import FULL_TURN, RIGHT_ANGLE, Tile

Orientation = tuple[int, bool]   # (clockwise degrees, mirrored)
SOLVED: Orientation = (0, False)


class ParSolver:
    """Calculates the minimum number of player moves (swap, rotate 90
    degrees clockwise, flip horizontally) needed to solve a board."""

    def __init__(self) -> None:
        self._distance = self._build_distance_table()

    @staticmethod
    def _build_distance_table() -> dict[Orientation, int]:
        """Fewest rotate/flip actions from each of the 8 orientations to
        the solved one, found by a breadth-first search backwards from
        the solved orientation. Going backwards means using the inverse
        of each player action: rotating anticlockwise, and flipping
        horizontally (which undoes itself)."""
        distance = {SOLVED: 0}
        queue = deque([SOLVED])
        while queue:
            rotation, mirrored = queue.popleft()
            before_rotate = ((rotation - RIGHT_ANGLE) % FULL_TURN, mirrored)
            before_flip = ((FULL_TURN - rotation) % FULL_TURN, not mirrored)
            for previous in (before_rotate, before_flip):
                if previous not in distance:
                    distance[previous] = distance[(rotation, mirrored)] + 1
                    queue.append(previous)
        return distance

    def turns_needed(self, tile: Tile) -> int:
        """Fewest rotate/flip actions that put `tile` the right way up."""
        return self._distance[(tile.rotation, tile.is_mirrored)]

    def par_moves(self, tiles: list[Tile]) -> int:
        """Fewest moves that solve `tiles`, a complete board given in its
        current row-major order.

        The positions form a permutation; a cycle of k tiles takes k - 1
        swaps to fix, so the swaps needed are (number of tiles) minus
        (number of cycles).
        """
        visited = [False] * len(tiles)
        cycles = 0
        for start in range(len(tiles)):
            if visited[start]:
                continue
            cycles += 1
            position = start
            while not visited[position]:
                visited[position] = True
                position = tiles[position].tile_id   # where this tile belongs

        swaps_needed = len(tiles) - cycles
        return swaps_needed + sum(self.turns_needed(tile) for tile in tiles)
