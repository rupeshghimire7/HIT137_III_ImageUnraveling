"""
make_sample_images.py

Draws the five square sample pictures that the game's "Random Upload"
button picks from, and saves them in assets/images as 480 x 480 PNGs.

Every picture is drawn with OpenCV from a fixed random seed, so running
the script again gives exactly the same files. Each one has detail in
every corner and light that changes across AND down the picture, so
every tile looks different from its neighbours and from its own
rotated / flipped versions - the puzzle is always solvable by eye.

Run once from the project root, then commit the five PNG files:
    python scripts/make_sample_images.py
"""

from pathlib import Path

import cv2
import numpy as np

OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "images"
SIZE = 480          # divides evenly by 3, 4 and 5
AA = cv2.LINE_AA


def rgb(colour: str) -> tuple[int, int, int]:
    """'#RRGGBB' as the (b, g, r) tuple OpenCV draws with."""
    return int(colour[5:7], 16), int(colour[3:5], 16), int(colour[1:3], 16)


def diagonal_gradient(top_left: str, bottom_right: str, tilt: float = 0.35) -> np.ndarray:
    """A SIZE x SIZE background that blends from one corner to the other."""
    ys, xs = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    t = ys + tilt * xs
    t = (t - t.min()) / (t.max() - t.min())
    a = np.array(rgb(top_left), np.float32)
    b = np.array(rgb(bottom_right), np.float32)
    return (a + (b - a) * t[..., None]).astype(np.uint8)


def glow(image: np.ndarray, centre: tuple[int, int], radius: int, colour: str) -> None:
    """Brighten `image` in a soft circle around `centre` (in place)."""
    ys, xs = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    dist = np.hypot(xs - centre[0], ys - centre[1]) / radius
    weight = np.clip(1.0 - dist, 0, 1)[..., None] ** 2
    tint = np.array(rgb(colour), np.float32)
    image[:] = (image * (1 - weight) + tint * weight).astype(np.uint8)


def ridge(rng: np.random.Generator, base: int, roughness: int) -> np.ndarray:
    """A random mountain-ridge outline as polygon points, closed along
    the bottom edge."""
    xs = np.linspace(0, SIZE, 13)
    ys = base + rng.integers(-roughness, roughness, len(xs))
    points = [(int(x), int(y)) for x, y in zip(xs, ys, strict=True)]
    return np.array([(0, SIZE), *points, (SIZE, SIZE)], np.int32)


def sunset_mountains() -> np.ndarray:
    """An orange sky, a low sun on the right, three mountain ranges and
    a lake with the sun's reflection."""
    rng = np.random.default_rng(1)
    image = diagonal_gradient("#FF9A5A", "#6A2C70")
    glow(image, (340, 190), 210, "#FFE3A3")
    cv2.circle(image, (340, 190), 46, rgb("#FFF4D6"), -1, AA)
    for base, rough, colour in ((250, 60, "#8E3B6E"), (300, 45, "#5B2756"), (345, 30, "#35183D")):
        cv2.fillPoly(image, [ridge(rng, base, rough)], rgb(colour), AA)
    lake = diagonal_gradient("#4A1F52", "#1C0B26", tilt=-0.8)
    image[380:] = lake[380:]
    for x, y in rng.integers((0, 392), (SIZE, SIZE), (40, 2)):
        cv2.line(image, (int(x), int(y)), (int(x) + 18, int(y)), rgb("#7A3E78"), 1, AA)
    for i, y in enumerate(range(390, SIZE, 12)):
        half = 70 - i * 6
        cv2.line(image, (340 - half, y), (340 + half, y), rgb("#FFC98B"), 3, AA)
    for x, y in ((90, 110), (130, 90), (165, 120)):
        cv2.polylines(image, [np.array([(x - 12, y - 6), (x, y), (x + 12, y - 6)])],
                      False, rgb("#2A1236"), 2, AA)
    return image


def balloons() -> np.ndarray:
    """Hot-air balloons of different sizes and stripes in a blue sky with
    clouds."""
    image = diagonal_gradient("#7FD3FF", "#1E5AA8", tilt=0.6)
    glow(image, (60, 50), 220, "#FFFFFF")
    for cx, cy, w, h in ((380, 90, 70, 26), (120, 330, 90, 30), (300, 420, 110, 34)):
        for dx in (-w // 2, 0, w // 2):
            cv2.ellipse(image, (cx + dx, cy), (w // 2, h // 2), 0, 0, 360,
                        rgb("#F4F9FF"), -1, AA)
    specs = ((150, 150, 80, ("#E63946", "#FFD166")), (350, 250, 60, ("#06D6A0", "#118AB2")),
             (230, 380, 40, ("#F77F00", "#7B2CBF")))
    for cx, cy, r, colours in specs:
        mask = np.zeros((SIZE, SIZE), np.uint8)
        cv2.ellipse(mask, (cx, cy), (r, int(r * 1.15)), 0, 0, 360, 255, -1, AA)
        stripes = np.full_like(image, rgb(colours[0]))
        for i, x in enumerate(range(cx - r, cx + r, max(4, r // 4))):
            cv2.rectangle(stripes, (x, 0), (x + r // 4, SIZE), rgb(colours[i % 2]), -1)
        image[mask > 0] = stripes[mask > 0]
        top, bottom = cy + int(r * 1.15), cy + int(r * 1.15) + r // 2
        for side in (-1, 1):
            cv2.line(image, (cx + side * r // 3, top - 4), (cx + side * r // 5, bottom),
                     rgb("#5C4033"), 2, AA)
        cv2.rectangle(image, (cx - r // 5, bottom), (cx + r // 5, bottom + r // 4),
                      rgb("#8B5A2B"), -1)
    return image


def bauhaus() -> np.ndarray:
    """Overlapping circles, triangles and bars in bold, flat colours."""
    rng = np.random.default_rng(3)
    image = diagonal_gradient("#F7EDD5", "#E2B98A", tilt=0.8)
    palette = [rgb(c) for c in ("#E63946", "#1D3557", "#F4A261", "#2A9D8F", "#264653",
                                "#E9C46A")]
    for _ in range(22):
        colour = palette[int(rng.integers(len(palette)))]
        kind = rng.integers(3)
        x, y = (int(v) for v in rng.integers(0, SIZE, 2))
        size = int(rng.integers(40, 150))
        if kind == 0:
            cv2.circle(image, (x, y), size // 2, colour, -1, AA)
        elif kind == 1:
            pts = np.array([(x, y - size // 2), (x + size // 2, y + size // 2),
                            (x - size // 2, y + size // 3)], np.int32)
            cv2.fillPoly(image, [pts], colour, AA)
        else:
            cv2.rectangle(image, (x - size, y - 10), (x + size, y + 10), colour, -1)
    for y in range(0, 2 * SIZE, 32):
        cv2.line(image, (0, y), (y, 0), rgb("#1D3557"), 1, AA)
    cv2.circle(image, (110, 120), 70, rgb("#1D3557"), 6, AA)
    return image


def night_city() -> np.ndarray:
    """A city skyline at night with lit windows, a crescent moon, stars
    and the lights reflected in a river."""
    rng = np.random.default_rng(4)
    image = diagonal_gradient("#0B1D51", "#3E1F47", tilt=-0.4)
    glow(image, (110, 90), 160, "#4A5FA8")
    for x, y in rng.integers(0, (SIZE, 260), (90, 2)):
        cv2.circle(image, (int(x), int(y)), int(rng.integers(1, 3)), rgb("#FFF8DC"), -1, AA)
    cv2.circle(image, (110, 90), 38, rgb("#FDF6C9"), -1, AA)
    cv2.circle(image, (128, 80), 34, image[60, 20].tolist(), -1, AA)
    x = 0
    while x < SIZE:
        width = int(rng.integers(35, 75))
        top = int(rng.integers(150, 330))
        shade = rgb(("#1B1B3A", "#24244A", "#151530")[int(rng.integers(3))])
        cv2.rectangle(image, (x, top), (x + width, 390), shade, -1)
        for wy in range(top + 10, 380, 18):
            for wx in range(x + 6, x + width - 8, 14):
                if rng.random() < 0.45:
                    cv2.rectangle(image, (wx, wy), (wx + 6, wy + 9), rgb("#FFD27F"), -1)
        x += width + int(rng.integers(0, 8))
    cv2.rectangle(image, (0, 390), (SIZE, SIZE), rgb("#0E1433"), -1)
    river = cv2.flip(image[300:390], 0)
    image[390:480] = (image[390:480] * 0.5 + river * 0.35).astype(np.uint8)
    return image


def coral_reef() -> np.ndarray:
    """Fish, seaweed and bubbles under water, with sunlight from the top
    right."""
    rng = np.random.default_rng(5)
    image = diagonal_gradient("#3FC1C9", "#0B3954", tilt=-0.2)
    glow(image, (420, 0), 260, "#B8F3FF")
    cv2.ellipse(image, (240, 520), (320, 120), 0, 180, 360, rgb("#E9D8A6"), -1, AA)
    for base_x in (40, 95, 400, 450):
        pts = [(base_x + int(18 * np.sin(y / 22 + base_x)), y) for y in range(470, 250, -10)]
        cv2.polylines(image, [np.array(pts, np.int32)], False, rgb("#2D6A4F"), 9, AA)
    fish = (((150, 140), 34, "#FF7F11"), ((330, 230), 26, "#FFD60A"),
            ((210, 330), 40, "#E5383B"), ((380, 120), 20, "#9D4EDD"))
    for (cx, cy), r, colour in fish:
        cv2.ellipse(image, (cx, cy), (r, int(r * 0.6)), 0, 0, 360, rgb(colour), -1, AA)
        tail = np.array([(cx + r - 4, cy), (cx + r + r // 2, cy - r // 2),
                         (cx + r + r // 2, cy + r // 2)], np.int32)
        cv2.fillPoly(image, [tail], rgb(colour), AA)
        cv2.circle(image, (cx - r // 2, cy - r // 6), max(2, r // 8), rgb("#FFFFFF"), -1, AA)
        cv2.circle(image, (cx - r // 2, cy - r // 6), max(1, r // 14), rgb("#000000"), -1, AA)
    for x, y in rng.integers((0, 0), (SIZE, 420), (25, 2)):
        cv2.circle(image, (int(x), int(y)), int(rng.integers(3, 9)), rgb("#E0FBFC"), 1, AA)
    return image


PICTURES = {
    "sample_1_sunset.png": sunset_mountains,
    "sample_2_balloons.png": balloons,
    "sample_3_bauhaus.png": bauhaus,
    "sample_4_night_city.png": night_city,
    "sample_5_coral_reef.png": coral_reef,
}


def main() -> None:
    """Draw every picture and save it in assets/images."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, draw in PICTURES.items():
        image = draw()
        assert image.shape == (SIZE, SIZE, 3), name
        ok, encoded = cv2.imencode(".png", image)
        if not ok:
            raise RuntimeError(f"Could not encode {name}")
        encoded.tofile(str(OUT_DIR / name))
        print(f"wrote {OUT_DIR / name}")


if __name__ == "__main__":
    main()
