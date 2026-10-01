# ImageUnraveling - HIT137 Assignment 3

A desktop puzzle game built with **Tkinter** (GUI) and **OpenCV** (image
processing), structured into a layered architecture. A loaded image is
cut into a grid of tiles, scrambled with random swaps/rotations/flips,
and the player restores it by clicking tiles.

See **`docs/PRD_Implementation_Plan.md`** for the full requirements.

## Group members

| Student name     | Student ID | Owns (source files)                                   | Unit tests                                          |
| ---------------- | ---------- | ----------------------------------------------------- | --------------------------------------------------- |
| Hemanta Adhikari | S403355    | `src/models/tile.py`, `src/models/transformations.py` | `tests/test_tile.py`, `tests/test_transformations.py` |
| John Karki       | S403518    | `src/engine/image_processor.py`                       | `tests/test_image_processor.py`                     |
| Ashim Koirala    | S000000    | `src/engine/puzzle_board.py`                          | `tests/test_puzzle_board.py`                        |
| Rupesh Ghimire   | S000000    | `src/ui/gui.py`, `src/main.py`                        | `tests/test_gui.py`                                 |

## Setup

```bash
pip install -r requirements.txt
python src/main.py
```

Run from the project root exactly as above. Tested with Python 3.10+.
`tkinter` ships with most Python installers; on some Linux distributions
you may need `sudo apt install python3-tk`.

## How to play

1. Pick a grid size (3x3, 4x4 or 5x5) from the dropdown, then click
   **Load Image...** and choose a JPG/PNG/BMP file.
2. The left canvas shows the original picture (reference only). The right
   canvas shows the scrambled version - only it responds to clicks.
3. **Left click** a tile to select it (coloured border). Left click a second
   tile to swap them. Left click the same tile again to deselect it.
4. **Right click** a tile to rotate it 90° clockwise.
5. **Shift + left click** a tile to flip it horizontally.
6. A green tick appears in the corner of any tile that is already in its
   correct place and orientation.
7. **Hint** (max 3 per image) circles one wrong tile on the puzzle image
   in blue, and circles that tile's correct home cell on the original
   image in blue. The circles disappear as soon as you make your next
   move.
8. **Solve** instantly restores the picture and resets the move counter
   for that image; the round then ends.
9. When every tile is correct you get a completion message and the
   puzzle stops responding to clicks until you load a new image.

## Project structure

```
HIT137_III_ImageUnraveling/
├── README.md
├── requirements.txt       <- game libraries + pytest and ruff
├── github_link.txt
├── docs/                  <- brief, marking rubric, PRD
├── outputs/               <- sample original/scrambled images
├── .github/workflows/ci.yml  <- lint, import check and tests on every push/PR
├── scripts/
│   └── check_imports.py   <- imports every module under src/
├── src/
│   ├── main.py            <- entry point
│   ├── models/            <- Tile + Transformation hierarchy (pure OOP core)
│   │   ├── tile.py
│   │   └── transformations.py
│   ├── engine/            <- game rules + OpenCV image pipeline
│   │   ├── image_processor.py
│   │   └── puzzle_board.py
│   └── ui/                <- Tkinter front-end
│       └── gui.py
└── tests/                 <- pytest suite, no image files needed
    ├── conftest.py              <- shared fixtures (whole group)
    ├── test_tile.py             <- Hemanta Adhikari
    ├── test_transformations.py  <- Hemanta Adhikari
    ├── test_image_processor.py  <- John Karki
    ├── test_puzzle_board.py     <- Ashim Koirala
    └── test_gui.py              <- Rupesh Ghimire
```

## Unit testing

Every source file has its own unit-test file in `tests/`, written by the
group member who owns that part of the code. The header at the top of
each test file gives the student's name and student ID.

| Test file                       | Tests source file               | Student name     | Student ID | Tests |
| ------------------------------- | ------------------------------- | ---------------- | ---------- | ----- |
| `tests/test_tile.py`            | `src/models/tile.py`            | Hemanta Adhikari | S403355    | 27    |
| `tests/test_transformations.py` | `src/models/transformations.py` | Hemanta Adhikari | S403355    | 23    |
| `tests/test_image_processor.py` | `src/engine/image_processor.py` | John Karki       | S403518    | 39    |
| `tests/test_puzzle_board.py`    | `src/engine/puzzle_board.py`    | Ashim Koirala    | S000000    | 58    |
| `tests/test_gui.py`             | `src/ui/gui.py`, `src/main.py`  | Rupesh Ghimire   | S000000    | 19    |
| `tests/conftest.py`             | shared fixtures, not a test file | Whole group     | -          | -     |

The tests use **pytest**. They generate their own small test images in a
temporary folder, so no picture files are needed. `tests/conftest.py`
adds `src/` to the import path, so the commands below work straight from
the project root.

### 1. Install the requirements (once)

From the project root (the folder containing `src/` and `tests/`):

```bash
pip install -r requirements.txt
```

This installs the game's libraries plus `pytest` and `ruff`.

### 2. Run all unit tests

```bash
python -m pytest -v
```

Every test is listed with `PASSED`, ending with `166 passed`.

### 3. Run one student's tests

```bash
python -m pytest tests/test_tile.py -v               # Hemanta Adhikari - 27 tests
python -m pytest tests/test_transformations.py -v    # Hemanta Adhikari - 23 tests
python -m pytest tests/test_image_processor.py -v    # John Karki       - 39 tests
python -m pytest tests/test_puzzle_board.py -v       # Ashim Koirala    - 58 tests
python -m pytest tests/test_gui.py -v                # Rupesh Ghimire   - 19 tests
```

Run a single test by name with `-k`, e.g.
`python -m pytest tests/test_puzzle_board.py -k hint -v`.

Example output (`python -m pytest tests/test_tile.py -v`):

```
collected 27 items

tests/test_tile.py::test_constructor_sets_home_and_default_orientation PASSED [  3%]
tests/test_tile.py::test_constructor_rejects_empty_image[None] PASSED    [  7%]
...
tests/test_tile.py::test_repr_shows_state PASSED                         [100%]

============================== 27 passed in 0.10s ==============================
```

### 4. GUI tests need a display

`test_gui.py` opens a hidden Tkinter window, records message boxes
instead of showing them, and simulates mouse clicks. It works on any
normal Windows/macOS/Linux desktop. On a machine with no screen those
tests are **skipped**, not failed (e.g. `148 passed, 18 skipped`). On a
headless Linux machine run them with `xvfb-run -a python -m pytest -v`.

### Troubleshooting

- `ModuleNotFoundError: No module named 'models'` - your
  `tests/conftest.py` is an old copy without the `sys.path` lines. Update
  it, or run `PYTHONPATH=src python -m pytest -v`.
- `file or directory not found` - check the file name (e.g. one `.py`,
  not `.py.py`) and that you are in the project root.

### What each test file checks

- **test_tile.py** (Hemanta Adhikari) - constructor checks, read-only
  (encapsulated) state, rotation wrap-around and 90° validation, flips
  mirror the tile as displayed, reset, original pixels never change,
  every orientation can be fixed with the player's two actions,
  `is_correct`.
- **test_transformations.py** (Hemanta Adhikari) - abstract classes
  can't be created, inheritance tree, `apply()`/`undo()` for
  rotate/flip/swap, invalid input rejected, polymorphic undo of a mixed
  history, `random_transformation` factory.
- **test_image_processor.py** (John Karki) - loading PNG/JPG/BMP,
  grayscale, transparent and 16-bit images, non-English file names, clear
  `ValueError` for bad/empty/missing files, square output divisible by
  3/4/5, split into row-major tiles, merge rebuilds the exact picture.
- **test_puzzle_board.py** (Ashim Koirala) - supported grid sizes,
  reproducible seeded scramble, scramble rules (6/12/20 steps, all three
  types, no tile hit twice, never starts solved), moves and move counter,
  moves refused once solved, max 3 hints, `solve()`, `render()`,
  `index_at()`.
- **test_gui.py** (Rupesh Ghimire) - button states, loading every grid
  size, bad-file error box, select/deselect/swap, right-click rotate,
  shift-click flip, off-image clicks ignored, hints on both images, solve
  and lock, winning with mouse actions only, `main()` start-up.

### Other checks

```bash
ruff check src tests scripts      # lint: PEP 8, unused names, import order
python scripts/check_imports.py   # every module under src/ imports cleanly
```

These checks and the tests also run on GitHub Actions for every push to
`main` and every pull request (`.github/workflows/ci.yml`); there the GUI
tests run under a virtual display (`xvfb-run`).

## How the OOP requirements are met

**Encapsulation** - `Tile` keeps its pixel data and rotation/flip flags as
private attributes; they can only be changed through its methods
(`rotate`, `flip_horizontal`, `flip_vertical`, `reset`), never poked at
directly from the GUI.

**Constructors** - every class (`Tile`, the `Transformation` subclasses,
`ImageProcessor`, `PuzzleBoard`, `PuzzleGameApp`) has an `__init__` that
sets up its own state.

**Inheritance** - `src/models/transformations.py` defines an abstract
base class `Transformation`, an abstract `TileTransformation` subclass
(single-tile actions), and concrete leaves `RotateTransformation` and
`FlipTransformation`; `SwapTransformation` inherits directly from
`Transformation`.

**Polymorphism** - `PuzzleBoard` keeps one `history` list mixing all
three transformation types. Scrambling, playing moves and solving all
just call `.apply()` / `.undo()` on whatever is in that list - the
correct behaviour happens automatically per subclass, with no
`isinstance` checks anywhere in the model.

**Class interaction / layering** - `ui/gui.py` never touches OpenCV or
pixel arrays directly: it calls `engine/puzzle_board.py` methods, which
in turn call `engine/image_processor.py` (for pixels) and
`models/transformations.py` (for game moves).

## Design notes

- Every loaded image is resized (aspect ratio preserved) into a 480x480
  box and then centre-cropped to a square whose side divides evenly by
  the grid size - square tiles are what make a 90°/180°/270° rotation
  always fit back into its slot.
- Scramble count is `grid_size * (grid_size - 1)` (6/12/20 for 3x3/4x4/5x5),
  matching the brief's example; at least one swap means the board never
  starts solved.
- Each tile's orientation is stored as a rotation plus a mirror flag, and
  every rotate/flip updates it exactly as the player sees it on screen. So
  the player's two tile actions (rotate 90° clockwise, flip horizontally)
  can always undo any scramble, including vertical flips.
- The scramble draws its tiles from one shuffled pool, so no tile is
  targeted by more than one transformation, and it always contains at
  least one swap, rotate and flip.
- `Solve` pops every transformation ever applied (scramble *and* player
  moves) off a history stack and calls `.undo()` on each, in reverse
  order - a literal "undo everything", exactly as the brief describes.
- All file/image errors (cancelled dialog, non-image file, corrupt file)
  are caught and shown in a message box instead of crashing the app;
  clicks outside the puzzle image are silently ignored.

## Before you submit

1. Make sure every team member understands their section (and ideally
   the whole app) - you may be asked about any part of it.
2. Check the repository is **public** and all group members are added.
3. Replace every `S000000` in this README and in the test file headers
   with the real student IDs.
4. Check the repository URL in `github_link.txt`.
5. Zip the programming files, the `outputs/` folder and `github_link.txt`
   together and upload to Learnline.