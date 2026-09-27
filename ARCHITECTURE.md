# Architecture

The app is split into four layers, each in its own package under `src/`,
so that a change to one (e.g. swapping Tkinter for another GUI toolkit)
never has to touch the others.

```
┌───────────────────────────────────────────────────────────────┐
│                          src/main.py                            │
│                    application entry point                       │
└───────────────────────────────┬─────────────────────────────────┘
                                 │ creates
                                 ▼
┌───────────────────────────────────────────────────────────────┐
│                          src/ui/gui.py                          │
│                 PuzzleGameApp  (Tkinter front-end)                │
│   - builds widgets: buttons, grid-size combobox, two canvases      │
│   - turns mouse clicks into PuzzleBoard method calls                │
│   - draws grid lines / selection border / green ticks / hint circles│
└───────────────────────────────┬─────────────────────────────────┘
                                 │ calls the public methods of
                                 ▼
┌───────────────────────────────────────────────────────────────┐
│                  src/engine/puzzle_board.py                     │
│                    PuzzleBoard  (game rules)                       │
│   - owns the grid of Tiles + a full transformation history          │
│   - scramble() / swap() / rotate_tile() / flip_tile()                │
│   - use_hint() / solve() / is_solved() / incorrect_indices()          │
└───────────────┬───────────────────────────────┬─────────────────┘
                │ uses                            │ uses
                ▼                                  ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│  src/engine/image_processor.py  │   │           src/models/           │
│         ImageProcessor            │   │  tile.py, transformations.py     │
│  - load_image (OpenCV, JPG/PNG/BMP)│   │  - Tile: encapsulated pixel data  │
│  - prepare_square (resize + crop)   │   │    + rotation/flip state           │
│  - split_into_tiles / merge_tiles    │   │  - Transformation hierarchy:        │
│  - the ONLY file that imports cv2     │   │    Rotate/Flip/Swap, used            │
│                                        │   │    polymorphically as a command      │
│                                        │   │    stack (apply()/undo())             │
└───────────────────────────────┘   └───────────────────────────────┘
```

## Why this shape

- **`models/`** holds classes with no external dependency beyond OpenCV's
  pixel operations (`cv2.rotate`/`cv2.flip` on an already-in-memory array)
  and no knowledge of grids, files or widgets. `Tile` and the
  `Transformation` hierarchy are the pure OOP core of the assignment:
  encapsulation (`Tile`'s private state), inheritance and polymorphism
  (`Transformation` → `TileTransformation` → `Rotate`/`Flip`, and
  `Swap` alongside them).
- **`engine/`** is where domain rules live: `ImageProcessor` deals with
  files and pixel grids; `PuzzleBoard` composes `ImageProcessor` +
  `models` into one playable round (scrambling, scoring, hints, solving).
  Neither file imports Tkinter - both are fully testable headlessly (see
  `tests/verify_model.py`).
- **`ui/`** is the only package that imports `tkinter`/`PIL`. It never
  touches OpenCV or raw pixel arrays directly - it only calls
  `PuzzleBoard`'s public methods and reads back plain Python values
  (booleans, ints, numpy arrays it hands straight to PIL).
- **`main.py`** just wires the three layers together and starts the
  Tk event loop.

## Data flow for a single player action (example: a swap)

1. User clicks a tile, then a second tile, on `puzzle_canvas`.
2. `gui.py` converts the pixel coordinates to a tile index and calls
   `PuzzleBoard.swap(a, b)`.
3. `PuzzleBoard` builds a `SwapTransformation`, calls `.apply()` on it
   (which swaps the two `Tile` objects in its list) and pushes it onto
   `self.history`, and increments `self.moves`.
4. `gui.py` calls `PuzzleBoard.render()`, which asks `ImageProcessor` to
   merge every tile's `get_display_image()` back into one array.
5. `gui.py` converts that array to a `PhotoImage` and redraws the
   canvas, plus the grid lines, any green ticks, and the status labels.

Solving works the same way in reverse: `PuzzleBoard.solve()` pops every
`Transformation` ever applied (scramble transformations AND every player
move) off `history` and calls `.undo()` on each, in reverse order -
guaranteed to land back on the exact original, fully-solved picture.

See `README.md` for setup/run instructions and `TASK_DIVISION.md` for who
owns which package.
