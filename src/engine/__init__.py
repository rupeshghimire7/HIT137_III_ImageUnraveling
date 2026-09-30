"""
engine package - the "business logic" layer, sitting between the domain
models and the Tkinter UI:

    image_processor.py  loading, resizing, splitting and merging (OpenCV)
    fit_strategy.py     Crop / Pad ways of making a picture square
    puzzle_board.py     the model for one round
    scrambler.py        the random scramble
    par_solver.py       fewest moves that solve a board
    game_state.py       moves, hints, timer and finished state
    scoring.py          score and star rating
    hints.py            which tile a hint points at
"""
