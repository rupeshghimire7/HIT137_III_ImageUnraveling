# ImageUnraveling - HIT137 Assignment Project III


- **Course:** HIT137 — Group Assignment 3

- **Product:** Desktop image-restoration puzzle (Python, Tkinter, OpenCV)

- **Team:** 4 members

- Member 1: John Karki
- Member 2: Hemanta Adhikari
- Member 3: Ashim Koirala
- Member 4: Rupesh Ghimire (s403354)

## Overview
A desktop game where the player loads a picture, the app cuts it into a grid of tiles and scrambles them (moving, rotating and flipping pieces), and the player clicks tiles to restore the original picture. The app counts moves, shows how many tiles are still wrong, offers limited hints, can auto-solve, and announces when the picture is restored.


## Core User Flow

1. Player chooses a grid size (3×3 default, 4×4 or 5×5).
2. Player clicks **Load Image** and picks a JPG, PNG or BMP file.
3. App resizes the image to fit the screen, crops or pads it so the grid divides evenly, and cuts it into tiles.
4. App generates a random batch of transformations (swap, rotate, flip) all at once and applies them.
5. Window shows the **original** image on the left (reference only) and the **scrambled** image on the right (interactive), with a faint grid over the scrambled image.
6. Player restores tiles:
   - Left click selects a tile (coloured border). Left click another tile swaps them. Left click the same tile deselects it.
   - Right click rotates a tile 90° clockwise.
   - Shift + left click flips a tile horizontally.
7. After every action the image is re-rendered, a green tick appears on every correct tile, and the move counter and "tiles incorrect" counter update.
8. Player may press **Hint** (max 3 per image) or **Solve**.
9. When all tiles are correct, the player is notified and the puzzle stops accepting input. The player can load another image.


## Constraints

- GUI: **Tkinter**. Image processing: **OpenCV**. Language: Python.
- Formats: **JPG, PNG, BMP** must work.
- Grid sizes: exactly **3×3, 4×4, 5×5**, default **3×3**, selectable **before loading**.
- Transformations: minimum **Swap, Rotate (90/180/270), Flip (H or V)**; random each load; generated at once; count scales with grid size; **no tile targeted twice**.



## Project Timeline and Progress:

- Github Repo Initialized
- Project Documents downloaded 
- Initial PRD and Implementation plan with task division created and shared to GroupMembers after multiple iterations (Rupesh) 
- Readme file created


*Note: A team discussion is to be held to discuss implementation and hereon after, all members shall use their own feature branches and create pull requests*

- 


## Members:

Member 1: John Karki
Member 2: Hemanta Adhikari
Member 3: Ashim Koirala
Member 4: Rupesh Ghimire