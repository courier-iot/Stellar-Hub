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

W, H = 384, 216            # scene size in pixels
BW, BH = 44, 56            # building sprite size
GROUND_Y = 138             # where the moon surface starts
WALK_Y = 186               # top of the walkway
FEET_Y = 192               # resident stands with feet here

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
def window(c, x, y, w, h, lit, glow="y"):
    c.rect(x, y, w, h, "k")
    c.rect(x + 1, y + 1, w - 2, h - 2, glow if lit else "n")
    if lit:
        c.px(x + 1, y + 1, "w")


def porthole(c, cx, cy, r, lit, glow="c"):
    c.disc(cx, cy, r + 1, "k")
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
def b_home(lit):
    c = Canvas(BW, BH)
    c.disc(22, 34, 19, "p", 18)                     # dome habitat
    c.rect(0, 34, BW, 22, ".")
    c.rect(3, 34, 38, 21, "P")
    c.rect(3, 34, 38, 2, "V")
    for x in range(8, 38, 9):
        c.rect(x, 18, 1, 16, "P")                   # dome ribs
    c.disc(16, 24, 3, "X")                          # dome shine
    porthole(c, 11, 42, 3, lit, "y")
    porthole(c, 33, 42, 3, lit, "y")
    d = door(c, 18, 40, 9, 15)
    c.outline()
    antenna(c, 30, 8, 8, "m", lit)
    c.rect(0, 55, BW, 1, "k")
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


BUILDERS = {"home": b_home, "library": b_library, "internet_cafe": b_cafe, "post_office": b_post,
            "salon": b_salon, "bank": b_bank, "workshop": b_workshop}
ORDER = ["home", "library", "internet_cafe", "post_office", "salon", "bank", "workshop"]


def building_sprite(bid, variant):
    lit = variant == "open"
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
    return c.rows()


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
    for _ in range(900):
        a = rnd.random() * math.tau
        r = abs(rnd.gauss(0, 1)) * 26
        x, y = int(120 + math.cos(a) * r * 2.2), int(44 + math.sin(a) * r * 0.8)
        c.px(x, y, rnd.choice("PPMVJ"))
    # stars
    for _ in range(230):
        x, y = rnd.randrange(W), rnd.randrange(GROUND_Y - 30)
        c.px(x, y, rnd.choice("wwtsSG"))
    for _ in range(6):                               # bigger cross stars
        x, y = rnd.randrange(10, W - 10), rnd.randrange(8, 90)
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            c.px(x + dx, y + dy, "w" if dx == dy == 0 else "s")
    # ringed planet
    cx, cy = 312, 42
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
    for _ in range(26):                              # craters
        cx2, cy2, r = rnd.randrange(W), rnd.randrange(GROUND_Y + 6, WALK_Y - 4), rnd.randint(3, 7)
        c.disc(cx2, cy2, r, "U", r * .45)
        c.disc(cx2 + 1, cy2 + 1, r - 1, "K", (r - 1) * .4)
        for xx in range(int(cx2 - r + 1), int(cx2 + r)):
            c.px(xx, int(cy2 - r * .45), "L")
    for _ in range(60):
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
    for i in range(len(ORDER) + 1):
        lx = 6 + i * 53
        c.rect(lx, WALK_Y - 26, 1, 26, "S")
        c.rect(lx - 1, WALK_Y - 28, 3, 2, "c")
    return c.rows()


def stars_for_twinkle():
    rnd = random.Random(11)
    return [[rnd.randrange(W), rnd.randrange(GROUND_Y - 30)] for _ in range(40)]


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


def world(building_states, look):
    """building_states: {id: 'open'|'closed'|'locked'|'construction'}"""
    global _BG
    if _BG is None:
        _BG = background()
    buildings = []
    for i, bid in enumerate(ORDER):
        x = 10 + i * 53
        variant = building_states.get(bid, "open")
        buildings.append({"id": bid, "x": x, "y": WALK_Y - BH + 1, "w": BW, "h": BH, "variant": variant,
                          "door_x": x + BW // 2, "sprite": building_sprite(bid, variant)})
    pal = dict(PALETTE)
    pal.update(resident_palette(look))
    data = {"w": W, "h": H, "palette": pal, "background": _BG, "buildings": buildings,
            "resident": {"frames": resident_frames(look), "form": look.get("form", "star_spirit"),
                         "feet_y": FEET_Y, "floats": look.get("form", "star_spirit") == "star_spirit"},
            "twinkle": stars_for_twinkle()}
    data["version"] = world_version(building_states, look)
    return data


def world_version(building_states, look):
    return hashlib.md5(json.dumps([building_states, look], sort_keys=True).encode()).hexdigest()[:10]
