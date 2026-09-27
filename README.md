# Tile Rotation Puzzle - HIT137 Assignment 3

A desktop puzzle game built with **Tkinter** (GUI) and **OpenCV** (image
processing), structured into a layered architecture. A loaded image is
cut into a grid of tiles, scrambled with random swaps/rotations/flips,
and the player restores it by clicking tiles.

See **`ARCHITECTURE.md`** for the layer diagram and **`TASK_DIVISION.md`**
for who owns which part of the code.

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
3. **Left click** a tile to select it (blue border). Left click a second
   tile to swap them. Left click the same tile again to deselect it.
4. **Right click** a tile to rotate it 90° clockwise.
5. **Shift + left click** a tile to flip it horizontally.
6. A green tick appears in the corner of any tile that is already in its
   correct place and orientation.
7. **Hint** (max 3 per image) circles one wrong tile on the puzzle image
   in blue, and circles that tile's correct home cell on the original
   image in blue. The circles disappear as soon as you make your next
   move.
8. **Solve** instantly restores the picture and resets the move/hint
   counters for that image.
9. When every tile is correct you get a completion message and the
   puzzle stops responding to clicks until you load a new image.

## Project structure

```
tile_puzzle_game/
├── README.md
├── ARCHITECTURE.md        <- layer diagram + data-flow walkthrough
├── TASK_DIVISION.md       <- who owns which package
├── requirements.txt
├── github_link.txt        <- put your group's repo URL here before submitting
├── outputs/               <- sample original/scrambled images (proof the pipeline works)
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
└── tests/
    └── verify_model.py    <- headless self-check, no display needed
```

## Verifying the game logic without opening the GUI

```bash
python tests/verify_model.py path/to/any_image.jpg
```

This scrambles, plays random moves, and solves the puzzle at all three
grid sizes, asserting the model always ends up back in a fully solved
state, and re-saves the sample images in `outputs/`.

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
`models/transformations.py` (for game moves). See `ARCHITECTURE.md`.

## Design notes

- Every loaded image is resized (aspect ratio preserved) into a 480x480
  box and then centre-cropped to a square whose side divides evenly by
  the grid size - square tiles are what make a 90°/180°/270° rotation
  always fit back into its slot.
- Scramble count is `grid_size * (grid_size - 1)` (6/12/20 for 3x3/4x4/5x5),
  matching the brief's example, guaranteeing all three transformation
  types appear and the result isn't trivially already solved.
- `Solve` pops every transformation ever applied (scramble *and* player
  moves) off a history stack and calls `.undo()` on each, in reverse
  order - a literal "undo everything", exactly as the brief describes.
- All file/image errors (cancelled dialog, non-image file, corrupt file)
  are caught and shown in a message box instead of crashing the app;
  clicks outside the puzzle image are silently ignored.

## Before you submit

1. Read `TASK_DIVISION.md`, split up ownership as described, and make
   sure every team member actually understands their section (and ideally
   the whole app) - you may be asked about any part of it.
2. Create a **public** GitHub repository and add all group members.
3. Push this code and keep committing there as you go (see the GitHub
   workflow section in `TASK_DIVISION.md`).
4. Put the repository URL in `github_link.txt`.
5. Zip the programming files, the `outputs/` folder and `github_link.txt`
   together and upload to Learnline.
