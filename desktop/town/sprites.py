"""16-bit pixel art for the Stellar Hub space colony.

All art is generated here in Python and served as JSON (rows of palette
characters), so the desktop viewer and Hub Connect S draw the exact same town.
'.' is transparent. Digits 1/2/3 in resident sprites are the resident's own
colours (primary / secondary / accent), 'f' is skin.
"""
import hashlib
import json
import math
import random

PLOTS, HOME_PLOT = 15, 7    # 15 building plots, Home Dome in the middle
W, H = 812, 216            # scene size in pixels
BW, BH = 44, 56            # building sprite size
GROUND_Y = 138             # where the moon surface starts
WALK_Y = 186               # top of the walkway
FEET_Y = 192               # resident stands with feet here
UPPER_WALK_Y = 120         # top of the Upper Street deck (bought later)
UPPER_FEET_Y = 126
UPPER_BASE = 15            # upper plots are numbered 16-30 (index 15-29); the one above the Home Dome stays open sky

PALETTE = {
    "k": "#07080f", "n": "#151a33", "N": "#232a52", "g": "#353e6e", "G": "#56609a",
    "w": "#eef1ff", "t": "#fff3c4", "y": "#ffd86b", "Y": "#ff9f43",
    "c": "#5ef2ff", "C": "#1f8fb3", "m": "#ff4fd8", "M": "#9c2a8f",
    "p": "#a184ff", "P": "#5b3fb5", "r": "#ff5d73", "R": "#9a2a44",
    "e": "#4fe0a5", "E": "#1f8a68", "s": "#a7b0d3", "S": "#6b7399",
    "h": "#1e1838", "o": "#8f6a4c", "O": "#5a4030",
    # sky + ground shades
    "A": "#05060d", "B": "#0a0b1c", "D": "#120f2b", "F": "#1d1440", "I": "#2c1a55",
    "J": "#3d2370", "K": "#2a2f45", "L": "#3a4060", "Q": "#4b5275", "U": "#20243a",
    "V": "#6a3fd0", "X": "#c05ad8",
}

COLOR_CHOICES = {
    "cyan": "#5ef2ff", "magenta": "#ff4fd8", "purple": "#a184ff", "gold": "#ffd86b",
    "orange": "#ff9f43", "red": "#ff5d73", "green": "#4fe0a5", "blue": "#5b8cff",
    "pink": "#ff9ad5", "white": "#eef1ff", "silver": "#a7b0d3", "navy": "#2a3160",
    "teal": "#1fb3a0", "black": "#14162a",
}
SKIN_CHOICES = {"light": "#f6d2b0", "tan": "#d9a376", "brown": "#a86e45", "deep": "#6e4528",
                "starlight": "#c9d8ff", "lilac": "#d2b8ff", "mint": "#b8ffe0"}
FORMS = ["star_spirit", "robot", "person"]
DEFAULT_LOOK = {"form": "star_spirit", "primary": "gold", "secondary": "orange", "accent": "cyan", "skin": "light"}


class Canvas:
    def __init__(self, w, h, fill="."):
        self.w, self.h = w, h
        self.g = [[fill] * w for _ in range(h)]

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h and c and c != ".":
            self.g[y][x] = c

    def get(self, x, y):
        return self.g[y][x] if 0 <= x < self.w and 0 <= y < self.h else "."

    def rect(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.px(xx, yy, c)

    def box(self, x, y, w, h, fill, line="k"):
        self.rect(x, y, w, h, line)
        self.rect(x + 1, y + 1, w - 2, h - 2, fill)

    def disc(self, cx, cy, r, c, ry=None):
        ry = ry or r
        for yy in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for xx in range(int(cx - r) - 1, int(cx + r) + 2):
                if ((xx + .5 - cx) / r) ** 2 + ((yy + .5 - cy) / ry) ** 2 <= 1:
                    self.px(xx, yy, c)

    def outline(self, c="k"):
        marks = []
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] == "." and any(self.get(x + dx, y + dy) not in (".", c)
                                                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    marks.append((x, y))
        for x, y in marks:
            self.g[y][x] = c

    def paste(self, rows, x, y):
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                self.px(x + i, y + j, ch)

    def rows(self):
        return ["".join(r) for r in self.g]


# ---------------------------------------------------------------- pieces
_DAY = False   # daytime: windows reflect light instead of glowing


def window(c, x, y, w, h, lit, glow="y"):
    c.rect(x, y, w, h, "k")
    if lit and _DAY:
        c.rect(x + 1, y + 1, w - 2, h - 2, "g")
        c.px(x + 1, y + 1, "s"); c.px(x + w - 2, y + h - 2, "G")
        return
    c.rect(x + 1, y + 1, w - 2, h - 2, glow if lit else "n")
    if lit:
        c.px(x + 1, y + 1, "w")


def porthole(c, cx, cy, r, lit, glow="c"):
    c.disc(cx, cy, r + 1, "k")
    if lit and _DAY:
        c.disc(cx, cy, r, "g")
        c.px(int(cx - r / 2), int(cy - r / 2), "s")
        return
    c.disc(cx, cy, r, glow if lit else "n")
    if lit:
        c.px(int(cx - r / 2), int(cy - r / 2), "w")


def door(c, x, y, w, h, frame="S"):
    c.rect(x, y, w, h, "k")
    c.rect(x + 1, y + 1, w - 2, h - 1, frame)
    c.rect(x + 2, y + 2, w - 4, h - 2, "g")
    c.rect(x + w // 2, y + 2, 1, h - 2, "k")   # sliding airlock seam
    return (x, y, w, h)


def neon_icon(c, x, y, icon, col):
    shapes = {
        "heart": [".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."],
        "book": ["###.###", "#.#.#.#", "#.#.#.#", "#.#.#.#", "###.###", "...#..."],
        "at": [".#####.", "#.....#", "#.###.#", "#.#.#.#", "#.####.", ".#....."],
        "mail": ["#######", "##...##", "#.#.#.#", "#..#..#", "#.....#", "#######"],
        "star": ["...#...", "..###..", "#######", ".#####.", ".##.##.", "#.....#"],
        "coin": [".#####.", "#..#..#", "#.###.#", "#..#..#", "#.###.#", ".#####."],
        "gear": ["#.#.#.#", ".#####.", "##...##", "##...##", ".#####.", "#.#.#.#"],
        "box": ["#######", "#.....#", "#######", "#.###.#", "#.....#", "#######"],
        "leaf": ["....###", "..#####", ".####.#", ".###.##", ".#.####", "#......"],
        "note": ["..####.", "..#..#.", "..#..#.", "..#..#.", "###.###", "###.###"],
        "rocket": ["...#...", "..###..", "..#.#..", "..###..", ".#####.", "#.#.#.#"],
        "gavel": [".###...", ".####..", "..###..", "...#.#.", "....#.#", "######."],
        "bag": ["..###..", ".#...#.", "#######", "#.....#", "#.....#", "#######"],
        "column": ["#######", ".#.#.#.", ".#.#.#.", ".#.#.#.", ".#.#.#.", "#######"],
        "paw": ["#.#.#..", "#.#.#..", ".......", ".###...", "#####..", ".###..."],
    }
    for j, row in enumerate(shapes[icon]):
        for i, ch in enumerate(row):
            if ch == "#":
                c.px(x + i, y + j, col)


def sign(c, cx, y, icon, col, lit):
    c.box(cx - 6, y, 13, 10, "h")
    neon_icon(c, cx - 3, y + 2, icon, col if lit else "g")


def antenna(c, x, y, h, tip="r", lit=True):
    c.rect(x, y, 1, h, "S")
    c.px(x, y - 1, tip if lit else "R")


# ---------------------------------------------------------------- buildings
def b_home(lit, floors=1):
    """The Home Dome. Each extra floor adds a 14px habitat ring under the dome."""
    extra = 14 * (max(1, min(4, floors)) - 1)
    c = Canvas(BW, BH + extra)
    c.disc(22, 34, 19, "p", 18)                     # dome
    c.rect(0, 34, BW, 22 + extra, ".")
    for x in range(8, 38, 9):
        c.rect(x, 18, 1, 16, "P")
    c.disc(16, 24, 3, "X")
    for f in range(floors - 1):                     # upper floors
        y = 34 + f * 14
        c.rect(4, y, 36, 14, "P"); c.rect(4, y, 36, 1, "V"); c.rect(4, y + 13, 36, 1, "M")
        for wx in (9, 17, 25, 33):
            porthole(c, wx, y + 7, 2, lit, "y")
    base = 34 + extra
    c.rect(3, base, 38, 21, "P")
    c.rect(3, base, 38, 2, "V")
    porthole(c, 11, base + 8, 3, lit, "y")
    porthole(c, 33, base + 8, 3, lit, "y")
    d = door(c, 18, base + 6, 9, 15)
    c.outline()
    antenna(c, 30, 8, 8, "m", lit)
    c.rect(0, BH + extra - 1, BW, 1, "k")
    return c, d


def b_library(lit):
    c = Canvas(BW, BH)
    c.box(4, 18, 36, 38, "N")
    c.rect(2, 14, 40, 5, "g"); c.rect(2, 14, 40, 1, "G")    # roof slab
    c.rect(8, 6, 28, 9, "Q"); c.rect(8, 6, 28, 1, "s")      # observatory deck
    c.disc(22, 6, 7, "S", 5); c.rect(15, 6, 15, 6, "Q")
    c.rect(21, 1, 2, 4, "s")                                # telescope
    for x in (7, 15, 27, 35):
        c.rect(x, 20, 2, 35, "S")                           # columns
    window(c, 10, 24, 4, 10, lit, "y"); window(c, 30, 24, 4, 10, lit, "y")
    d = door(c, 18, 40, 9, 15)
    sign(c, 22, 26, "book", "c", lit)
    c.outline()
    c.rect(0, 55, BW, 1, "k")
    return c, d


def b_cafe(lit):
    c = Canvas(BW, BH)
    c.box(3, 20, 38, 36, "U")
    c.rect(3, 18, 38, 3, "g"); c.rect(3, 18, 38, 1, "G")
    c.disc(10, 18, 5, "S", 3); c.disc(34, 18, 5, "S", 3)    # satellite pods
    c.rect(1, 22, 42, 2, "m" if lit else "M")               # neon band
    window(c, 6, 27, 12, 12, lit, "c")
    window(c, 26, 27, 12, 12, lit, "c")
    if lit:
        for wx in (8, 28):                                  # screens glow
            c.rect(wx, 30, 7, 4, "C"); c.rect(wx + 1, 31, 5, 1, "w")
    d = door(c, 18, 40, 9, 15)
    sign(c, 22, 6, "at", "m", lit)
    c.outline()
    antenna(c, 6, 4, 12, "c", lit); antenna(c, 38, 6, 10, "c", lit)
    c.disc(38, 5, 3, "s", 2)                                # dish
    c.rect(0, 55, BW, 1, "k")
    return c, d


def b_post(lit):
    c = Canvas(BW, BH)
    c.box(5, 16, 34, 40, "R")
    c.rect(5, 16, 34, 3, "r")
    for y in range(22, 54, 6):
        c.rect(6, y, 32, 1, "M")                            # hull plates
    c.rect(3, 12, 38, 5, "S"); c.rect(3, 12, 38, 1, "s")
    porthole(c, 12, 28, 4, lit, "y"); porthole(c, 32, 28, 4, lit, "y")
    d = door(c, 18, 40, 9, 15)
    sign(c, 22, 1, "mail", "y", lit)
    c.box(1, 44, 6, 11, "C")                                # mail pod
    c.rect(2, 46, 4, 1, "k")
    c.outline()
    c.rect(0, 55, BW, 1, "k")
    return c, d


def b_salon(lit):
    c = Canvas(BW, BH)
    c.disc(22, 30, 18, "M", 16)
    c.rect(0, 30, BW, 26, ".")
    c.box(4, 30, 36, 26, "M")
    c.rect(4, 30, 36, 2, "m" if lit else "M")
    c.disc(15, 21, 3, "X")
    window(c, 7, 36, 9, 9, lit, "m"); window(c, 28, 36, 9, 9, lit, "m")
    d = door(c, 18, 40, 9, 15)
    sign(c, 22, 2, "star", "c", lit)
    for y in range(36, 54, 2):                              # striped pole
        c.px(41, y, "w" if y % 4 else ("m" if lit else "M"))
    c.outline()
    c.rect(0, 55, BW, 1, "k")
    return c, d


def b_bank(lit):
    c = Canvas(BW, BH)
    c.box(3, 20, 38, 36, "Q")
    c.rect(1, 14, 42, 7, "S"); c.rect(1, 14, 42, 1, "s")
    for x in range(4, 40, 3):
        c.px(x, 17, "k")
    for x in (6, 13, 30, 37):
        c.rect(x, 22, 2, 33, "s")
    window(c, 9, 26, 4, 9, lit, "y"); window(c, 31, 26, 4, 9, lit, "y")
    d = door(c, 17, 38, 11, 17)
    sign(c, 22, 3, "coin", "y", lit)
    c.outline()
    c.rect(0, 55, BW, 1, "k")
    return c, d


def b_workshop(lit):
    c = Canvas(BW, BH)
    c.box(2, 20, 40, 36, "K")
    for x in range(2, 42, 4):
        c.rect(x, 20, 2, 2, "Y" if x % 8 else "k")          # hazard stripe
    c.rect(2, 16, 40, 4, "S")
    d = (6, 30, 24, 25)
    c.rect(6, 30, 24, 25, "k")
    for y in range(31, 55, 3):
        c.rect(7, y, 22, 2, "L")                            # hangar shutter
    window(c, 33, 30, 6, 8, lit, "Y")
    sign(c, 22, 4, "gear", "Y", lit)
    c.outline()
    antenna(c, 38, 8, 8, "Y", lit)
    c.rect(0, 55, BW, 1, "k")
    return c, (12, 40, 9, 15)


def b_greenhouse(lit, plants=()):
    c = Canvas(BW, BH)
    c.disc(22, 30, 20, "C", 20)
    c.rect(0, 30, BW, 26, ".")
    c.box(2, 30, 40, 26, "C")
    c.disc(22, 30, 19, "N" if not lit else "n", 19)
    c.rect(3, 30, 38, 25, "N" if not lit else "n")
    for x in range(6, 40, 8):                               # glass panes
        c.rect(x, 12, 1, 43, "C")
    c.rect(2, 30, 40, 1, "C")
    c.disc(13, 20, 3, "c" if lit else "C")
    # planter boxes with the resident's real plants (up to 8)
    c.rect(4, 49, 36, 3, "O"); c.rect(4, 49, 36, 1, "o")
    slots = [6, 10, 14, 30, 34, 38, 8, 36]
    for i, (leaf, flower, stage) in enumerate(list(plants)[:8]):
        px = slots[i]
        h = {"seed": 1, "sprout": 3, "young": 5, "mature": 8, "blooming": 9}.get(stage, 2)
        c.rect(px, 49 - h, 1, h, leaf)
        if h >= 5:
            c.px(px - 1, 49 - h + 2, leaf); c.px(px + 1, 49 - h + 3, leaf)
        if stage == "blooming":
            c.px(px, 48 - h, flower); c.px(px - 1, 49 - h, flower); c.px(px + 1, 49 - h, flower)
        elif stage == "wilted":
            c.rect(px, 47, 2, 2, "O")
    d = door(c, 18, 40, 9, 15)
    sign(c, 22, 1, "leaf", "e", lit)
    c.outline()
    c.rect(0, 55, BW, 1, "k")
    return c, d


def b_radio(lit, playing=False):
    c = Canvas(BW, BH)
    for y in range(4, 42):                                  # lattice tower
        half = 2 + (y - 4) // 5
        c.px(22 - half, y, "S"); c.px(22 + half, y, "S")
        if y % 4 == 0:
            c.rect(22 - half, y, half * 2 + 1, 1, "S")
        if y % 8 == 2:
            for i in range(-half, half + 1):
                c.px(22 + i, y + (i % 2), "g")
    c.disc(32, 16, 4, "s", 3)                               # dish
    c.px(30, 16, "k")
    c.box(8, 38, 28, 18, "N")
    c.rect(8, 38, 28, 2, "p" if lit else "P")
    window(c, 11, 43, 5, 5, lit, "p")
    d = door(c, 18, 42, 9, 13)
    window(c, 29, 43, 5, 5, lit, "p")
    sign(c, 22, 26, "note", "p", lit)
    c.outline()
    c.px(22, 2, "r" if lit else "R"); c.px(22, 3, "r" if lit else "R")
    if playing and lit:
        for (x, y) in ((6, 8), (36, 6), (10, 20)):          # floating music notes
            c.rect(x, y, 1, 4, "c"); c.rect(x - 2, y + 3, 2, 2, "c"); c.px(x + 1, y, "c")
    c.rect(0, 55, BW, 1, "k")
    return c, d


def b_archive(lit):
    c = Canvas(BW, BH)
    c.box(2, 14, 40, 42, "Q")
    c.rect(2, 14, 40, 3, "s")
    for y in range(20, 55, 5):
        c.rect(3, y, 38, 1, "L")
    c.disc(22, 36, 12, "k")
    c.disc(22, 36, 11, "y" if lit else "o")                 # round vault door
    c.disc(22, 36, 9, "S")
    c.disc(22, 36, 3, "s")
    for dx, dy in ((0, -6), (0, 6), (-6, 0), (6, 0)):
        c.rect(22 + dx, 36 + dy, 1, 1, "y" if lit else "o")
    sign(c, 22, 2, "box", "y", lit)
    window(c, 5, 22, 4, 6, lit, "y"); window(c, 35, 22, 4, 6, lit, "y")
    c.outline()
    c.rect(0, 55, BW, 1, "k")
    return c, (18, 42, 9, 13)


def b_spaceport(lit, away=False):
    c = Canvas(BW, BH)
    c.rect(0, 50, BW, 5, "S"); c.rect(0, 50, BW, 1, "s")    # launch pad
    for x in range(1, 44, 6):
        c.px(x, 52, "Y" if lit else "o")
    c.rect(34, 6, 2, 44, "o")                               # gantry
    for y in range(8, 50, 5):
        c.rect(30, y, 6, 1, "O")
    if not away:
        c.rect(16, 14, 8, 30, "w")                          # rocket body
        c.rect(16, 14, 2, 30, "s")
        c.disc(20, 14, 4, "r", 6); c.rect(16, 14, 8, 2, "w")
        c.rect(15, 10, 10, 1, ".")
        porthole(c, 20, 24, 2, lit, "c")
        c.rect(12, 38, 4, 8, "r"); c.rect(24, 38, 4, 8, "r")  # fins
        c.rect(18, 44, 4, 6, "S")
    else:
        for x in range(14, 27):
            c.px(x, 49, "k" if x % 2 else "U")              # scorch marks
    c.box(1, 34, 12, 16, "N")                               # control hut
    window(c, 3, 37, 8, 5, lit, "c")
    sign(c, 7, 22, "rocket", "c", lit)
    c.outline()
    c.rect(0, 55, BW, 1, "k")
    return c, (3, 44, 8, 6)


def b_gallery(lit, painting=None):
    c = Canvas(BW, BH)
    c.box(2, 14, 40, 42, "N")
    c.rect(0, 10, 44, 5, "s"); c.rect(0, 10, 44, 1, "w")             # roof cornice
    for x in (3, 39):
        c.rect(x, 16, 2, 39, "s")                                    # pillars
    c.box(10, 17, 24, 22, "o")                                       # big frame
    c.rect(12, 19, 20, 18, "n")
    if painting:                                                     # featured painting, scaled to fit 18x18
        n = len(painting)
        for y in range(18):
            for x in range(18):
                ch = painting[y * n // 18][x * n // 18]
                if ch != ".":
                    c.px(13 + x, 19 + y, ch)
    c.rect(6, 42, 32, 2, "m" if lit else "M")                        # neon strip
    d = door(c, 18, 44, 9, 11)
    window(c, 6, 46, 6, 6, lit, "y"); window(c, 32, 46, 6, 6, lit, "y")
    sign(c, 22, 0, "star", "m", lit)
    c.outline()
    c.rect(0, 55, BW, 1, "k")
    return c, d


def b_park(lit):
    c = Canvas(BW, BH)
    c.rect(0, 46, BW, 9, "E"); c.rect(0, 46, BW, 1, "e")             # lawn
    for x in range(0, 44, 3):
        c.px(x, 47 + (x % 2), "e")
    for (tx, h, r) in ((8, 24, 7), (35, 20, 6)):                       # trees
        c.rect(tx, 46 - h + r, 2, h - r, "o")
        c.disc(tx + 1, 46 - h + r, r, "E")
        c.disc(tx, 46 - h + r - 1, r - 2, "e")
    c.disc(22, 44, 5, "S", 2); c.disc(22, 43, 4, "c" if lit else "C", 1)    # fountain
    c.rect(22, 36, 1, 7, "c" if lit else "C"); c.px(21, 36, "w")
    c.rect(14, 49, 7, 1, "o"); c.px(14, 50, "O"); c.px(20, 50, "O")        # bench
    c.rect(26, 48, 5, 2, "k")                                               # chess table
    for x in range(26, 31):
        c.px(x, 48, "w" if x % 2 else "k")
    c.px(28, 50, "O")
    c.rect(0, 54, BW, 1, "U")
    sign(c, 22, 18, "leaf", "e", lit)
    c.outline()
    c.rect(0, 55, BW, 1, "k")
    return c, (18, 45, 9, 10)


def cutting_icon(leaf, flower):
    rows = ["..F..F....", "...LFL....", "...LLL....", ".....L....", "....LL....",
            "...kkkkk..", "...kooook.", "...kooook.", "....kook..", ".........."]
    return [r.replace("L", leaf).replace("F", flower) for r in rows]


WRITING_ICON = ["..........", ".kkkkkkk..", ".kttttttk.", ".ktkkkktk.", ".kttttttk.", ".ktkkkttk.",
                ".kttttttk.", ".ktkkkktk.", ".kttttttk.", ".kkkkkkkk."]


def b_exchange(lit):
    c = Canvas(BW, BH)
    c.box(3, 18, 38, 38, "R")
    c.rect(3, 18, 38, 2, "y" if lit else "o")
    c.disc(22, 18, 14, "y" if lit else "o", 6); c.rect(8, 18, 29, 6, ".")       # golden dome
    c.disc(22, 18, 12, "Y" if lit else "O", 5); c.rect(10, 18, 25, 6, ".")
    for x in (6, 14, 30, 38):
        c.rect(x, 22, 2, 33, "M")
    window(c, 9, 26, 4, 8, lit, "y"); window(c, 31, 26, 4, 8, lit, "y")
    c.rect(16, 36, 13, 2, "y" if lit else "o")                                  # "SOLD" rail
    d = door(c, 18, 40, 9, 15)
    sign(c, 22, 2, "gavel", "y", lit)
    c.outline()
    c.rect(0, 55, BW, 1, "k")
    return c, d


def b_pet_shop(lit):
    c = Canvas(BW, BH)
    c.box(4, 24, 36, 31, "E")                                                 # rounded habitat
    c.disc(22, 24, 18, "e" if lit else "E", 8); c.rect(4, 24, 37, 8, ".")
    c.disc(22, 24, 16, "E", 6); c.rect(6, 24, 33, 7, ".")
    c.rect(4, 24, 36, 2, "e" if lit else "E")
    for i, x in enumerate((8, 32)):                                           # round pet windows
        c.disc(x + 2, 34, 4, "k"); c.disc(x + 2, 34, 3, "c" if lit else "D")
        if lit:
            c.px(x + 1 + i, 35, "y"); c.px(x + 3 - i, 33, "w")
    c.rect(4, 46, 36, 1, "o")
    d = door(c, 18, 40, 9, 15)
    sign(c, 22, 6, "paw", "m", lit)
    c.rect(6, 52, 4, 3, "O"); c.rect(35, 52, 4, 3, "O")                        # food bowls
    c.outline()
    c.rect(0, 55, BW, 1, "k")
    return c, d


def b_store(lit):
    c = Canvas(BW, BH)
    c.box(2, 14, 40, 41, "M")                                                 # tall store front
    c.rect(2, 14, 40, 2, "m" if lit else "M")
    for i, x in enumerate(range(4, 40, 6)):                                   # striped awning
        c.rect(x, 26, 6, 4, ("m" if i % 2 else "w") if lit else ("M" if i % 2 else "g"))
    for x in (6, 30):                                                         # display windows
        c.rect(x, 32, 9, 9, "k"); c.rect(x + 1, 33, 7, 7, "t" if lit else "D")
        c.rect(x + 2, 36, 2, 4, "c" if lit else "C"); c.rect(x + 5, 35, 2, 5, "y" if lit else "o")
    for x in range(6, 40, 8):
        window(c, x, 18, 4, 5, lit, "y")
    d = door(c, 18, 40, 9, 15)
    sign(c, 22, 3, "bag", "m", lit)
    c.outline()
    c.rect(0, 55, BW, 1, "k")
    return c, d


def b_museum(lit):
    c = Canvas(BW, BH)
    c.box(3, 26, 38, 29, "s")
    for i in range(10):                                                       # pediment
        c.rect(22 - i * 2, 16 + i, i * 4 + 1, 1, "s")
    c.rect(2, 25, 40, 2, "w" if lit else "S")
    for x in (5, 12, 30, 37):                                                 # columns
        c.rect(x, 27, 3, 26, "w" if lit else "S"); c.rect(x - 1, 27, 5, 1, "S"); c.rect(x - 1, 52, 5, 1, "S")
    c.rect(2, 53, 40, 2, "S")
    c.disc(22, 21, 2, "y" if lit else "o")
    d = door(c, 18, 40, 9, 13)
    sign(c, 22, 2, "column", "y", lit)
    c.outline()
    c.rect(0, 55, BW, 1, "k")
    return c, d


STATION = [
    "............kk............",
    "...........kcck...........",
    "kkkkkkkk...kssk...kkkkkkkk",
    "kCCcCCck..kssssk..kcCCcCCk",
    "kCCcCCcSSSssccssSSScCCcCCk",
    "kCCcCCck..kssssk..kcCCcCCk",
    "kkkkkkkk...kssk...kkkkkkkk",
    "...........kSSk...........",
    "............kk............",
]

BUILDERS = {"home": b_home, "gallery": b_gallery, "park": b_park, "exchange": b_exchange, "pet_shop": b_pet_shop, "store": b_store, "museum": b_museum, "library": b_library, "internet_cafe": b_cafe, "post_office": b_post,
            "salon": b_salon, "bank": b_bank, "workshop": b_workshop, "greenhouse": b_greenhouse,
            "radio_tower": b_radio, "archive": b_archive, "spaceport": b_spaceport}
ORDER = ["home", "library", "internet_cafe", "post_office", "greenhouse", "radio_tower",
         "archive", "salon", "spaceport", "bank", "workshop"]
X0, STEP = 13, 53


def building_sprite(bid, variant, extra=None, with_door=False):
    global _DAY
    lit = variant == "open"
    extra = extra or {}
    _DAY = not extra.get("night", True)
    if bid == "home":
        c, (dx, dy, dw, dh) = b_home(lit, extra.get("floors", 1))
    elif bid == "gallery":
        c, (dx, dy, dw, dh) = b_gallery(lit, extra.get("featured"))
    elif bid == "greenhouse":
        c, (dx, dy, dw, dh) = b_greenhouse(lit, extra.get("plants", ()))
    elif bid == "radio_tower":
        c, (dx, dy, dw, dh) = b_radio(lit, extra.get("playing", False))
        if extra.get("studio"):                                     # studio annex
            c.box(32, 40, 12, 15, "M")
            c.rect(32, 40, 12, 1, "m" if lit else "M")
            window(c, 35, 44, 6, 4, lit, "m")
            c.rect(34, 50, 8, 1, "k")
            for x in range(34, 42, 2):
                c.px(x, 51, "w")
    elif bid == "spaceport":
        c, (dx, dy, dw, dh) = b_spaceport(lit, extra.get("away", False))
    else:
        c, (dx, dy, dw, dh) = BUILDERS[bid](lit)
    if variant == "locked":                         # chained airlock + padlock
        for x in range(dx - 1, dx + dw + 1):
            c.px(x, dy + 6 + (x % 2), "S")
        cx = dx + dw // 2
        c.rect(cx - 2, dy + 7, 5, 4, "y"); c.rect(cx - 1, dy + 5, 3, 2, "k"); c.px(cx, dy + 8, "k")
    elif variant == "closed":
        c.rect(dx - 1, dy + 5, dw + 2, 3, "r"); c.rect(dx, dy + 6, dw, 1, "w")
    elif variant == "construction":
        for x in (1, 21, 41):
            c.rect(x, 10, 1, 45, "o")
        for y in (14, 28, 42):
            c.rect(1, y, 41, 2, "O"); c.rect(1, y, 41, 1, "o")
        for i in range(0, 44, 7):
            c.px(i, 54, "Y")
        c.rect(30, 48, 5, 7, "Y"); c.rect(31, 51, 3, 1, "w"); c.rect(29, 54, 7, 1, "k")   # cone
    return (c.rows(), [dx, dy, dw, dh]) if with_door else c.rows()


# ---------------------------------------------------------------- background
def background():
    rnd = random.Random(7)
    c = Canvas(W, H)
    bands = ["A", "B", "D", "F", "I", "J"]
    band_h = GROUND_Y // len(bands) + 1
    for y in range(GROUND_Y):
        i = min(len(bands) - 1, y // band_h)
        nxt = bands[min(len(bands) - 1, i + 1)]
        frac = (y % band_h) / band_h
        for x in range(W):
            # ordered dither between bands, very 16-bit
            thresh = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]][y % 4][x % 4] / 16
            c.px(x, y, nxt if frac > 0.55 and thresh < (frac - 0.55) * 2.2 else bands[i])
    # nebula
    for _ in range(1700):
        a = rnd.random() * math.tau
        r = abs(rnd.gauss(0, 1)) * 26
        x, y = int(300 + math.cos(a) * r * 3.2), int(44 + math.sin(a) * r * 0.8)
        c.px(x, y, rnd.choice("PPMVJ"))
    # stars
    for _ in range(480):
        x, y = rnd.randrange(W), rnd.randrange(GROUND_Y - 30)
        c.px(x, y, rnd.choice("wwtsSG"))
    for _ in range(9):                               # bigger cross stars
        x, y = rnd.randrange(10, W - 10), rnd.randrange(8, 90)
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            c.px(x + dx, y + dy, "w" if dx == dy == 0 else "s")
    # ringed planet
    cx, cy = 690, 42
    c.disc(cx, cy, 22, "C")
    c.disc(cx - 4, cy - 4, 18, "c")
    c.disc(cx + 6, cy + 6, 16, "C")
    for yy in range(cy - 22, cy + 23):
        for xx in range(cx - 22, cx + 23):
            if c.get(xx, yy) in "cC" and (yy - cy + 3 * math.sin(xx / 5)) % 9 < 2:
                c.px(xx, yy, "C" if c.get(xx, yy) == "c" else "g")
    for t in range(0, 360):
        a = math.radians(t)
        for rr in (34, 35, 37):
            x = cx + math.cos(a) * rr
            y = cy + math.sin(a) * rr * 0.28 - math.cos(a) * 5
            front = math.sin(a) > 0
            if front or ((x - cx) ** 2 + (y - cy) ** 2) > 22 ** 2:
                c.px(int(x), int(y), "s" if rr != 37 else "S")
    # small moon
    c.disc(40, 26, 6, "S"); c.disc(38, 24, 5, "s"); c.px(41, 27, "Q"); c.px(37, 23, "Q")
    # distant colony silhouette on the horizon
    x = 0
    while x < W:
        w, h = rnd.randint(6, 16), rnd.randint(6, 26)
        for xx in range(x, x + w):
            for yy in range(GROUND_Y - h, GROUND_Y):
                c.px(xx, yy, "h")
        if rnd.random() < .4:
            c.disc(x + w / 2, GROUND_Y - h, w / 2, "h")
        for _ in range(rnd.randint(0, 3)):
            c.px(rnd.randrange(x + 1, x + w - 1), rnd.randrange(GROUND_Y - h + 2, GROUND_Y - 1), rnd.choice("ycmp"))
        x += w + rnd.randint(0, 6)
    # moon surface
    for y in range(GROUND_Y, WALK_Y):
        for x in range(W):
            c.px(x, y, "K" if (x * 7 + y * 13) % 23 else "U")
    c.rect(0, GROUND_Y, W, 1, "L")
    for _ in range(54):                              # craters
        cx2, cy2, r = rnd.randrange(W), rnd.randrange(GROUND_Y + 6, WALK_Y - 4), rnd.randint(3, 7)
        c.disc(cx2, cy2, r, "U", r * .45)
        c.disc(cx2 + 1, cy2 + 1, r - 1, "K", (r - 1) * .4)
        for xx in range(int(cx2 - r + 1), int(cx2 + r)):
            c.px(xx, int(cy2 - r * .45), "L")
    for _ in range(95):
        c.px(rnd.randrange(W), rnd.randrange(GROUND_Y + 2, WALK_Y), rnd.choice("LQ"))
    # metal walkway
    c.rect(0, WALK_Y, W, 1, "s")
    c.rect(0, WALK_Y + 1, W, 9, "S")
    for x in range(0, W, 12):
        c.rect(x, WALK_Y + 1, 1, 9, "g")
    c.rect(0, WALK_Y + 10, W, 1, "k")
    for x in range(4, W, 24):
        c.rect(x, WALK_Y + 4, 3, 1, "c")             # guide lights
    # lower surface
    for y in range(WALK_Y + 11, H):
        for x in range(W):
            c.px(x, y, "U" if (x + y * 3) % 17 else "h")
    # lamp posts between buildings
    for i in range(PLOTS + 1):
        lx = X0 - 4 + i * STEP
        c.rect(lx, WALK_Y - 26, 1, 26, "S")
        c.rect(lx - 1, WALK_Y - 28, 3, 2, "c")
    return c.rows()


def stars_for_twinkle():
    rnd = random.Random(11)
    return [[rnd.randrange(W), rnd.randrange(GROUND_Y - 30)] for _ in range(80)]


# ---------------------------------------------------------------- the resident
def _star(primary="1", shade="2"):
    c = Canvas(16, 16)
    cx, cy = 7.5, 8.6
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = 7.6 if i % 2 == 0 else 3.3
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))

    def inside(x, y):
        n, j, res = len(pts), len(pts) - 1, False
        for i in range(n):
            xi, yi = pts[i]; xj, yj = pts[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                res = not res
            j = i
        return res

    for y in range(16):
        for x in range(16):
            if inside(x + .5, y + .5):
                c.px(x, y, shade if (x - cx) + (y - cy) > 3 else primary)
    c.px(6, 5, "w"); c.px(5, 6, "w")
    c.px(6, 9, "k"); c.px(9, 9, "k")                # eyes
    c.px(7, 11, "k"); c.px(8, 11, "k")              # smile
    c.outline()
    return c


def resident_frames(look):
    form = look.get("form", "star_spirit")
    if form == "robot":
        top = ["........3.......", "........k.......", "....kkkkkkkk....", "...k11111111k...",
               "...k1kkkkkk1k...", "...k1k3kk3k1k...", "...k1kkkkkk1k...", "...k11111111k...",
               "....kkkkkkkk....", "...kk222222kk...", "..k1k222222k1k..", "..k1k223322k1k..",
               "..kkk222222kkk..", "....kkkkkkkk...."]
        return [top + ["....k2k..k2k....", "....kkk..kkk...."],
                top + [".....k2kk2k.....", ".....kkkkkk....."]]
    if form == "person":
        top = ["......kkkk......", "....kk2222kk....", "...k22222222k...", "...k2ffffff2k...",
               "...kfkffffkfk...", "...kffffffffk...", "....kffkkffk....", ".....kffffk.....",
               "....kk1111kk....", "...k11133111k...", "..kf11133111fk..", "..kk11111111kk..",
               "....k111111k....", "....knnkknnk...."]
        return [top + ["....knk..knk....", "....kkk..kkk...."],
                top + [".....knkknk.....", ".....kkkkkk....."]]
    a = _star()
    b = _star()
    for x, y in ((1, 1), (14, 2), (0, 12), (15, 13), (8, 0)):   # sparkle aura on frame 2
        b.px(x, y, "3")
    return [a.rows(), b.rows()]


def resident_palette(look):
    pal = {"1": COLOR_CHOICES.get(look.get("primary"), "#ffd86b"),
           "2": COLOR_CHOICES.get(look.get("secondary"), "#ff9f43"),
           "3": COLOR_CHOICES.get(look.get("accent"), "#5ef2ff"),
           "f": SKIN_CHOICES.get(look.get("skin"), "#f6d2b0")}
    return pal


# ---------------------------------------------------------------- world JSON
_BG = None


DECOR = {
    "bench": ["..........", "..........", "..........", "kkkkkkkkkk", "kooooooook", "kkkkkkkkkk",
              ".kk....kk.", ".kS....Sk.", ".kS....Sk.", ".kk....kk."],
    "lantern": ["...kk.....", "..kSSk....", "..kyyk....", "..kyyk....", "..kSSk....", "...kk.....",
                "...kS.....", "...kS.....", "..kSSk....", "..kkkk...."],
    "flag": ["kmmmmk....", "kmccmk....", "kmmmmk....", "kS........", "kS........", "kS........",
             "kS........", "kS........", "kSk.......", "kkk......."],
    "telescope": [".......kk.", ".....kkwwk", "...kkssk..", ".kkssk....", ".ksk......", "..k.k.....",
                  ".k...k....", ".k...k....", "k.....k...", "k.....k..."],
    "fountain": ["....cc....", "...c..c...", "..c.cc.c..", "....cc....", "...kSSk...", ".kkkkkkkk.",
                 "kcccccccck", "kCCCCCCCCk", ".kkkkkkkk.", ".........."],
    "robot_pet": ["..........", "...k..k...", "...kkkk...", "..kssssk..", "..kcsscsk.",
                  "..kssssk..", "...kkkk...", "..kSSSSk..", "..kk..kk..", ".........."],
    "neon_sign": ["kkkkkkkkkk", "kmmmmmmmmk", "kmkmmkmmmk", "kmmmmmmmmk", "kkkkkkkkkk", "....kk....",
                  "....kS....", "....kS....", "...kSSk...", "...kkkk..."],
    "satellite_dish": ["...kkkk...", "..kssssk..", ".kss..ssk.", ".ks....sk.", "..kk..kk..", "....kk....",
                       "....kS....", "....kS....", "...kSSk...", "..kkkkkk.."],
}
DECOR_PRICES = {"bench": 15, "lantern": 20, "flag": 10, "telescope": 40, "fountain": 60,
                "robot_pet": 80, "neon_sign": 35, "satellite_dish": 45}


DIGITS = {"0": ["###", "#.#", "#.#", "#.#", "###"], "1": [".#.", "##.", ".#.", ".#.", "###"],
          "2": ["###", "..#", "###", "#..", "###"], "3": ["###", "..#", ".##", "..#", "###"],
          "4": ["#.#", "#.#", "###", "..#", "..#"], "5": ["###", "#..", "###", "..#", "###"],
          "6": ["###", "#..", "###", "#.#", "###"], "7": ["###", "..#", ".#.", ".#.", ".#."],
          "8": ["###", "#.#", "###", "#.#", "###"], "9": ["###", "#.#", "###", "..#", "###"]}


def empty_lot(number):
    """A bare plot: foundation pad, corner markers, a beacon and the plot number."""
    c = Canvas(BW, BH)
    c.rect(2, 50, 40, 5, "U"); c.rect(2, 50, 40, 1, "L")
    for x in range(3, 41, 4):
        c.px(x, 52, "Q")
    for x in (2, 41):
        c.rect(x, 46, 1, 4, "Y"); c.px(x, 45, "Y")
    c.rect(36, 30, 1, 20, "S")                       # beacon pole
    c.rect(35, 28, 3, 2, "c")
    c.box(4, 36, 15, 9, "h")                         # plot number sign
    text = str(number)
    x = 6 if len(text) == 2 else 10
    for ch in text:
        for j, row in enumerate(DIGITS[ch]):
            for i, v in enumerate(row):
                if v == "#":
                    c.px(x + i, 38 + j, "s")
        x += 5
    c.rect(11, 45, 1, 5, "S")
    return c.rows()


EMOTES = {
    "!": ["kkkkkkkkk", "kwwwrwwwk", "kwwwrwwwk", "kwwwrwwwk", "kwwwwwwwk", "kwwwrwwwk", "kkkkkkkkk", "...kk....", "...k....."],
    "?": ["kkkkkkkkk", "kwwPPPwwk", "kwwwwPwwk", "kwwwPPwwk", "kwwwwwwwk", "kwwwPwwwk", "kkkkkkkkk", "...kk....", "...k....."],
    "note": ["kkkkkkkkk", "kwwwCCCwk", "kwwwCwCwk", "kwwwCwwwk", "kwwCCwwwk", "kwwCCwwwk", "kkkkkkkkk", "...kk....", "...k....."],
    "z": ["kkkkkkkkk", "kwwCCCCwk", "kwwwwCwwk", "kwwwCwwwk", "kwwCwwwwk", "kwwCCCCwk", "kkkkkkkkk", "...kk....", "...k....."],
    "heart": ["kkkkkkkkk", "kwmmwmmwk", "kwmmmmmwk", "kwmmmmmwk", "kwwmmmwwk", "kwwwmwwwk", "kkkkkkkkk", "...kk....", "...k....."],
    "chat": ["kkkkkkkkk", "kwwwwwwwk", "kwwwwwwwk", "kwSwSwSwk", "kwwwwwwwk", "kwwwwwwwk", "kkkkkkkkk", "...kk....", "...k....."],
    "idea": ["kkkkkkkkk", "kwwyyywwk", "kwyyyyywk", "kwwyyywwk", "kwwwSwwwk", "kwwwSwwwk", "kkkkkkkkk", "...kk....", "...k....."],
}

TRADER_SHIP = [
    "........kkkkkk..........",
    "......kkssssssk.........",
    "....kkssccccsssk........",
    "..kkssscwwccsssskkk.....",
    ".kssssssccsssssssssk....",
    "kssssssssssssssssssskkk.",
    "kSSSSSSSSSSSSSSSSSSSSSSk",
    ".kSSmmSSmmSSmmSSmmSSSSk.",
    "..kkkkkkkkkkkkkkkkkkkk..",
    "...kY.........kY........",
    "...kYY........kYY.......",
]


def plot_x(i):
    return X0 + (i % PLOTS) * STEP


LIFT_X = X0 + HOME_PLOT * STEP + BW + 4       # the lift between the walkway and the Upper Street, right of the Home Dome


def upper_plots():
    return [UPPER_BASE + i for i in range(PLOTS) if i != HOME_PLOT]


def upper_deck(state):
    """The Upper Street: an elevated deck on pylons, with a glass lift beside the Home Dome."""
    top = UPPER_WALK_Y - 2
    c = Canvas(W, WALK_Y - top)
    gap0, gap1 = plot_x(HOME_PLOT) - 4, LIFT_X + 5           # the deck opens around the Home Dome and its lift
    building = state == "construction"
    for x in range(W):
        if gap0 <= x < gap1:
            continue
        c.px(x, 2, "s")
        for y in range(3, 9):
            c.px(x, y, ("Y" if (x // 4) % 2 else "k") if building and y in (4, 5) else "S")
        c.px(x, 9, "k")
        if x % 24 == 0:
            c.rect(x, 3, 1, 6, "g")
        if x % 48 == 10 and not building:
            c.rect(x, 5, 3, 1, "c")
        if x % 6 == 0:                                          # railing posts
            c.rect(x, 0, 1, 2, "S")
    for x in range(W):
        if not (gap0 <= x < gap1):
            c.px(x, 0, "g")
    for i in range(PLOTS - 1):                                  # pylons in the gaps between the buildings below
        px = plot_x(i) + BW + 2
        if px >= gap0 - 6 and px < gap1:
            continue
        c.rect(px, 10, 5, WALK_Y - top - 10, "L"); c.rect(px + 1, 10, 1, WALK_Y - top - 10, "U")
        c.rect(px + 2, 24, 1, 2, "c" if not building else "Y")
    lx = LIFT_X - 3                                             # glass lift tube
    c.rect(lx, 0, 7, WALK_Y - top, "S"); c.rect(lx + 1, 0, 5, WALK_Y - top, "C")
    for y in range(4, WALK_Y - top, 8):
        c.rect(lx + 1, y, 5, 1, "c")
    c.rect(lx - 1, 8, 9, 2, "S")
    if building:
        for x in range(0, W, 30):                               # scaffolding while it's being built
            if not (gap0 <= x < gap1):
                c.rect(x, 10, 1, 40, "o"); c.rect(x, 30, 12, 1, "O")
    return c.rows()


def world(layout, building_states, look, extras=None):
    """layout: {plot index: building id}. building_states: {id: open|closed|construction}
    extras: {"plants": [...], "playing": bool, "away": bool, "decor": [...], "night": bool}"""
    global _BG
    extras = extras or {}
    if _BG is None:
        _BG = background()
    buildings = []
    upper = extras.get("upper")
    for i in list(range(PLOTS)) + (upper_plots() if upper == "open" else []):
        x = plot_x(i)
        level = 1 if i >= UPPER_BASE else 0
        base, feet = (UPPER_WALK_Y, UPPER_FEET_Y) if level else (WALK_Y, FEET_Y)
        bid = layout.get(i) if isinstance(layout, dict) else None
        if bid:
            variant = building_states.get(bid, "open")
            spr, dr = building_sprite(bid, variant, extras, with_door=True)
            h = len(spr)
            buildings.append({"id": bid, "plot": i, "x": x, "y": base - h + 1, "w": BW, "h": h, "variant": variant,
                              "door_x": x + BW // 2, "door": dr, "sprite": spr, "level": level, "feet_y": feet})
        else:
            buildings.append({"id": None, "plot": i, "x": x, "y": base - BH + 1, "w": BW, "h": BH, "variant": "empty",
                              "door_x": x + BW // 2, "sprite": empty_lot(i + 1), "level": level, "feet_y": feet})
    decor = []
    start = plot_x(HOME_PLOT) - 70
    for i, name in enumerate([d for d in extras.get("decor", []) if d in DECOR][:20]):
        decor.append({"name": name, "x": start + i * 14, "y": WALK_Y + 12, "sprite": DECOR[name]})
    pal = dict(PALETTE)
    pal.update(resident_palette(look))
    data = {"w": W, "h": H, "palette": pal, "background": _BG, "buildings": buildings, "decor": decor,
            "away": bool(extras.get("away")), "night": bool(extras.get("night", True)),
            "emotes": EMOTES, "trader_ship": TRADER_SHIP, "home_plot": HOME_PLOT,
            "aliases": {"studio": "radio_tower", "station": "spaceport"},
            "station": {"sprite": STATION, "x": 520, "y": 14} if extras.get("station") else None,
            "resident": {"frames": resident_frames(look), "form": look.get("form", "star_spirit"),
                         "feet_y": FEET_Y, "floats": look.get("form", "star_spirit") == "star_spirit"},
            "twinkle": stars_for_twinkle(),
            "upper": {"state": upper, "x": 0, "y": UPPER_WALK_Y - 2, "sprite": upper_deck(upper), "lift_x": LIFT_X,
                      "feet_y": UPPER_FEET_Y} if upper else None}
    data["version"] = world_version(layout, building_states, look, extras)
    return data


def world_version(layout, building_states, look, extras=None):
    key = [sorted((int(k), v) for k, v in (layout or {}).items()), building_states, look, extras or {}]
    return hashlib.md5(json.dumps(key, sort_keys=True).encode()).hexdigest()[:10]
