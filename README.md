# ImageUnraveling - HIT137 Assignment 3

A desktop puzzle game built with **Tkinter** (GUI) and **OpenCV** (image
processing), structured into a layered architecture. A loaded image is
cut into a grid of tiles, scrambled with random swaps/rotations/flips,
and the player restores it by clicking tiles.

See **`docs/PRD_Implementation_Plan.md`** for the full requirements and
**`progress.md`** for what is implemented and what is still to do.

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
   **Load Image...** and choose a JPG/PNG/BMP file. **Fit** decides what
   happens to a picture that is not square: *Crop* cuts it down to a
   square, *Pad* keeps the whole picture on a blurred background.
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
8. **Solve** instantly restores the picture and clears the moves and
   score for that image; the round then ends.
9. When every tile is correct you get a completion message with your
   moves, time, score and star rating, and the puzzle stops responding
   to clicks until you load a new image.

The status bar shows moves, tiles still wrong, time and score. The score
starts at 100 points per tile and loses points for every move beyond par
(the fewest moves that could solve the puzzle), for time and for hints.

## Project structure

```
HIT137_III_ImageUnraveling/
├── README.md
├── progress.md            <- PRD requirements: done / not done yet
├── requirements.txt       <- runtime dependencies
├── requirements-dev.txt   <- + pytest and ruff for development
├── pyproject.toml         <- ruff (lint) and pytest settings
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
│   │   ├── image_processor.py  <- load, resize, split, merge
│   │   ├── fit_strategy.py     <- FitStrategy: Crop / Pad
│   │   ├── puzzle_board.py     <- model for one round
│   │   ├── scrambler.py        <- the random scramble
│   │   ├── par_solver.py       <- fewest moves that solve a board
│   │   ├── game_state.py       <- moves, hints, timer, finished state
│   │   ├── scoring.py          <- score and star rating
│   │   └── hints.py            <- HintStrategy: Random / Smart
│   └── ui/                <- Tkinter front-end
│       ├── gui.py              <- window + controller
│       ├── panels.py           <- ImagePanel: Reference / Interactive
│       └── hit_test.py         <- mouse position -> grid cell
└── tests/                 <- pytest suite, no image files needed
```

## Testing and checks

```bash
pip install -r requirements-dev.txt
python -m pytest              # all tests (GUI tests skip if there is no display)
ruff check src tests scripts  # lint: PEP 8, unused names, import order
python scripts/check_imports.py
```

The same three checks run on GitHub Actions for every push to `main` and
every pull request (`.github/workflows/ci.yml`); there the GUI tests run
under a virtual display (`xvfb-run`).

## How the OOP requirements are met

**Encapsulation** - `Tile` keeps its pixel data and rotation/flip flags as
private attributes; they can only be changed through its methods
(`rotate`, `flip_horizontal`, `flip_vertical`, `reset`), never poked at
directly from the GUI. `GameState` does the same for the move counter,
hint budget and finished flag, so the rules (no moves after completion,
at most 3 hints) cannot be bypassed, and `PuzzleBoard` exposes its tiles
and counters only through read-only properties.

**Constructors** - every class has an `__init__` that fully sets up its
own state and rejects invalid arguments with a `ValueError`.

**Inheritance** - four small hierarchies, each an abstract base with
concrete subclasses:

| Base class | Subclasses | File |
|---|---|---|
| `Transformation` | `SwapTransformation`, `TileTransformation` -> `RotateTransformation`, `FlipTransformation` | `models/transformations.py` |
| `FitStrategy` | `CropFit`, `PadFit` | `engine/fit_strategy.py` |
| `HintStrategy` | `RandomHint`, `SmartHint` | `engine/hints.py` |
| `ImagePanel` | `ReferencePanel`, `InteractivePanel` | `ui/panels.py` |

**Polymorphism** - `PuzzleBoard` keeps one `history` list mixing all
three transformation types. Scrambling, playing moves and solving all
just call `.apply()` / `.undo()` on whatever is in that list - the
correct behaviour happens automatically per subclass, with no
`isinstance` checks anywhere in the model. In the same way
`ImageProcessor.prepare_square` calls `.apply()` on whichever
`FitStrategy` was chosen, and `HintAdvisor` calls `.choose()` on
whichever `HintStrategy` it was given.

**Class interaction / layering** - `ui/gui.py` never touches OpenCV or
pixel arrays directly: it calls `engine/puzzle_board.py` methods, which
in turn use `ImageProcessor` (pixels), `Scrambler` and the
transformations (moves), `GameState` (counters, timer, score) and
`HintAdvisor` (hints).

## Design notes

- Every loaded image is resized (aspect ratio preserved) into a 480x480
  box and then cropped (or, in Pad mode, padded) to a square whose side
  divides evenly by the grid size - square tiles are what make a
  90°/180°/270° rotation always fit back into its slot. A picture smaller
  than its panel is centred, and clicks in the margin are ignored.
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
- All file/image errors (cancelled dialog, missing, non-image, corrupt or
  too-small file) raise an `ImageLoadError` whose message is shown in a
  message box instead of crashing the app, and the round in progress
  carries on; clicks outside the puzzle image are silently ignored.
- A hint picks the most useful wrong tile (`SmartHint`): one that only
  needs turning, then one that a single swap fixes, then the lowest
  numbered misplaced tile.

## Before you submit

1. Make sure every team member understands their section (and ideally
   the whole app) - you may be asked about any part of it.
2. Create a **public** GitHub repository and add all group members.
3. Push this code and keep committing there as you go.
4. Put the repository URL in `github_link.txt`.
5. Zip the programming files, the `outputs/` folder and `github_link.txt`
   together and upload to Learnline.
