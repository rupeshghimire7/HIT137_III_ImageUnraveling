# Task Division - Hemanta, John, Ashim, Rupesh

The codebase is already a complete, working reference solution (see `ARCHITECTURE.md` for the layer diagram). Splitting a finished program up "per person" only makes sense if each person actually owns, understands, tests and can explain their slice - so the split below is by **architectural layer**, matching the four packages under `src/`. Read your section fully before touching anything else.

| Person  | Owns (files)                                          | Layer                     |
| ------- | ----------------------------------------------------- | ------------------------- |
| John    | `src/engine/image_processor.py`                       | Image processing (OpenCV) |
| Hemanta | `src/models/tile.py`, `src/models/transformations.py` | Core OOP models           |
| Ashim   | `src/engine/puzzle_board.py`                          | Game engine / rules       |
| Rupesh  | `src/ui/gui.py`, `src/main.py`                        | Tkinter GUI               |

## John - Image Processing (`src/engine/image_processor.py`)

* `load_image` - reading JPG/PNG/BMP with OpenCV, BGR->RGB conversion, raising a clear `ValueError` for anything that isn't a real image.
* `prepare_square` - resizing to fit an on-screen box while keeping aspect ratio, then centre-cropping to a square whose side divides evenly by the chosen grid size (this is **why** rotating a tile 90° always fits back into its slot).
* `split_into_tiles` / `merge_tiles` - cutting the square into a flat, row-major list of `Tile`s, and reassembling the grid back into one image for display.
* Marking criteria this covers: **Image Processing** (all three rows - loading/scaling, all three grid sizes, correct reassembly).

## Hemanta - Core OOP Models (`src/models/tile.py`, `src/models/transformations.py`)

* `Tile` - encapsulates a tile's pixel data and its rotation/flip state; the only way to change a tile is through its methods.
* `Transformation` (abstract) -> `TileTransformation` (abstract) -> `RotateTransformation`, `FlipTransformation`; `SwapTransformation` alongside them. Each implements `apply()` / `undo()` / `describe()`.
* `random_transformation()` - the factory used by the scrambler.
* Marking criteria this covers: **OOP Design** (encapsulation, inheritance, polymorphism, constructors) and the "three or more transformation types" part of **Image Processing**.

## Ashim - Game Engine (`src/engine/puzzle_board.py`)

* `PuzzleBoard.__init__` / `_scramble` - builds a round from `ImageProcessor` + `models`, applies `grid_size * (grid_size - 1)` random transformations, guarantees all three types appear and the result isn't trivially solved.
* `swap` / `rotate_tile` / `flip_tile` - player moves, each recorded on the history stack and counted in `self.moves`.
* `use_hint` / `solve` / `is_solved` / `incorrect_indices` - hint limit (max 3), the "undo everything" solve, and win detection.
* Marking criteria this covers: **Moves and Score**, **Hints**, **Completion and Solve** (the second half of Tkinter GUI and Gameplay).

## Rupesh - GUI (`src/ui/gui.py`, `src/main.py`)

* Widget layout: load button, grid-size combobox, hint/solve buttons, two canvases, status labels.
* Mouse handling: left click (select/swap), right click (rotate), shift+left click (flip), off-image clicks ignored.
* Drawing: grid lines, selection border, green ticks, hint circles on both canvases, redraw after every action.
* File dialog + error handling (`messagebox` for cancelled dialogs and bad files).
* Marking criteria this covers: **Tkinter GUI and Gameplay** (image display/layout, interaction mapping) and the error-handling row under **OOP Design**.

## Shared work (all four)

* **Agree the interfaces below on day one**, before writing code, so everyone can work in parallel without waiting on each other:

  * `Tile`: `rotate(degrees)`, `flip_horizontal()`, `flip_vertical()`, `get_display_image()`, `is_correct(row, col)`
  * `Transformation` subclasses: `apply()`, `undo()`, `describe()`
  * `ImageProcessor`: `load_image(path)`, `prepare_square(image, grid_size)`, `split_into_tiles(square_image, grid_size)`, `merge_tiles(tiles, grid_size, tile_edge)`
  * `PuzzleBoard`: `swap(a, b)`, `rotate_tile(i, degrees)`, `flip_tile(i, axis)`, `use_hint()`, `solve()`, `is_solved()`, `incorrect_indices()`, `render()`, `index_at(row, col)`

* **Dependency order**: John's image engine and Hemanta's models don't depend on each other and can start immediately. Ashim's `PuzzleBoard` needs both (or just the agreed interfaces above, as stubs, to start earlier). Rupesh's GUI needs `PuzzleBoard`'s public API but can be scaffolded against a stub board first and wired to the real one once Ashim's is ready.

* **Testing**: extend `tests/verify_model.py` with a case or two for your own layer as you build it.

* **Everyone** must be able to explain the whole app end to end, not just their own file - read `ARCHITECTURE.md` and skim every module before the demo/submission.

## GitHub workflow (this is what gets checked against "all contributions recorded in GitHub")

1. One person creates the **public** repo and adds the other three as collaborators.

2. Each person works on their own branch (e.g. `john-image-processing`, `hemanta-models`, `ashim-engine`, `rupesh-gui`), committing from their own GitHub account in small, meaningful steps - not one giant commit at the end.

3. Open a pull request per branch; at least one teammate reviews/approves before merging to `main`.

4. Once everything is merged and working, update `github_link.txt` with the repo URL before zipping up the submission.
