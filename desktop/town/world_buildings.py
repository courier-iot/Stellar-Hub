"""v0.13.5: building exteriors for the Enchanted Forest and the Ocean world.

Each world has its own drawing for every building (the Moon keeps the original domes in sprites.py). The drawings
use the same 44x56 size, door positions and features as the Moon versions: the Home's extra floors, the greenhouse's
real plants, the gallery's featured painting, music notes while the radio plays, and an empty pad while the resident
is away on an expedition. Colours come from each world's palette (see worlds.py).
"""
import math

from .sprites import BH, BW, Canvas, porthole, sign, window


def clear(c, x, y):
    if 0 <= x < c.w and 0 <= y < c.h:
        c.g[y][x] = "."


def arch_door(c, x, y, w, h, fill="S", line="g", knob="y"):
    """A rounded wooden door. Returns its rectangle like sprites.door."""
    r = w / 2
    c.disc(x + r, y + r, r, "k")
    c.rect(x, int(y + r), w, h - int(r), "k")
    c.disc(x + r, y + r, r - 1, fill)
    c.rect(x + 1, int(y + r), w - 2, h - int(r), fill)
    for xx in range(x + 2, x + w - 1, 2):
        c.rect(xx, y + 2, 1, h - 2, line)
    c.px(x + w - 3, y + h // 2 + 2, knob)
    return (x, y, w, h)


def base(c):
    c.outline()
    c.rect(0, BH - 1, BW, 1, "k")


def lantern(c, x, y, lit):
    c.px(x, y, "k"); c.rect(x - 1, y + 1, 3, 3, "i" if lit else "O"); c.px(x, y + 2, "y" if lit else "O")


def mushroom(c, cx, cy, rx, ry, cap="r", spot="w", stem="t"):
    c.disc(cx, cy, rx, cap, ry)
    for yy in range(int(cy) + 1, int(cy + ry) + 2):
        for xx in range(int(cx - rx) - 1, int(cx + rx) + 2):
            clear(c, xx, yy)
    for i, (dx, dy) in enumerate(((-rx * .5, -ry * .4), (rx * .3, -ry * .6), (rx * .65, -ry * .15), (-rx * .1, -ry * .1))):
        c.px(int(cx + dx), int(cy + dy), spot)
    return stem


def leaves(c, cx, cy, r, dark="b", light="d"):
    c.disc(cx, cy, r, dark, r * .7)
    c.disc(cx - 1, cy - 1, r - 2, light, (r - 2) * .55)
    for i in range(-r + 2, r - 1, 3):
        c.px(cx + i, int(cy + r * .35), dark)


# ================================================================== the Enchanted Forest


def f_cafe(lit):
    """Forest Node: a mossy stone hut with a glowing rune crystal on top; root cables glow to the network."""
    c = Canvas(BW, BH)
    c.box(4, 22, 36, 34, "Q")
    for y in range(24, 54, 5):                                   # stones
        for x in range(5 + (y % 2) * 3, 39, 7):
            c.rect(x, y, 5, 1, "L")
    c.disc(22, 22, 19, "u", 6); c.rect(3, 22, 38, 6, ".")       # moss roof
    c.rect(4, 21, 36, 3, "u"); c.rect(4, 21, 36, 1, "e")
    c.rect(20, 6, 5, 13, "x" if lit else "C"); c.rect(21, 3, 3, 4, "c" if lit else "C"); c.px(22, 2, "w")
    c.rect(21, 8, 1, 9, "w" if lit else "c")
    window(c, 7, 29, 10, 9, lit, "x")
    window(c, 27, 29, 10, 9, lit, "x")
    for x in range(1, 43, 2):                                    # glowing root cables along the ground
        c.px(x, 54 - (x % 3 == 0), "x" if lit else "C")
    d = arch_door(c, 18, 40, 9, 15)
    sign(c, 9, 8, "at", "x", lit)
    base(c)
    return c, d


def f_post(lit):
    """Wispwell: a wishing well under a little roof, with a stone post hut behind it. Wisps carry the letters."""
    c = Canvas(BW, BH)
    c.box(14, 18, 28, 38, "Q")                                   # stone hut
    for y in range(20, 54, 5):
        c.rect(15, y, 26, 1, "L")
    for i in range(10):                                          # pointed roof
        c.rect(28 - i * 2 + 2, 9 + i, i * 4 - 1 if i else 1, 1, "S")
    c.rect(12, 18, 32, 2, "g")
    porthole(c, 34, 27, 3, lit, "i")
    d = arch_door(c, 25, 40, 9, 15)
    c.disc(8, 46, 8, "Q", 3); c.rect(0, 46, 17, 9, "Q")          # the well
    c.rect(1, 46, 15, 1, "s")
    for x in range(1, 16, 4):
        c.rect(x, 48, 3, 1, "L"); c.rect(x + 2, 51, 3, 1, "L")
    c.disc(8, 46, 6, "k", 2)
    c.rect(1, 30, 1, 16, "S"); c.rect(15, 30, 1, 16, "S")         # well roof
    for i in range(6):
        c.rect(8 - i - 2, 25 + i, (i + 2) * 2 + 1, 1, "g")
    c.rect(8, 31, 1, 9, "s"); c.rect(6, 40, 4, 3, "O")          # rope + bucket
    if lit:
        for (x, y) in ((4, 20), (12, 15), (6, 10)):              # wisps
            c.px(x, y, "x"); c.px(x + 1, y, "w"); c.px(x, y + 1, "c")
    sign(c, 28, 1, "mail", "y", lit)
    base(c)
    return c, d


def f_store(lit):
    """Toadstool Market: market stalls under a giant red toadstool."""
    c = Canvas(BW, BH)
    c.rect(18, 18, 8, 37, "t"); c.rect(19, 18, 1, 37, "w")       # stalk
    c.disc(22, 16, 21, "r", 13)                                   # cap
    for yy in range(17, 31):
        for xx in range(44):
            clear(c, xx, yy)
    c.rect(1, 16, 42, 2, "R")
    for (x, y, r) in ((10, 10, 2), (22, 6, 3), (33, 9, 2), (16, 13, 1), (29, 14, 1), (5, 14, 1), (38, 13, 1)):
        c.disc(x, y, r, "w")
    for i, x in enumerate(range(2, 42, 5)):                       # striped awning under the cap
        c.rect(x, 19, 5, 3, ("i" if i % 2 else "w") if lit else ("O" if i % 2 else "g"))
    for x0 in (2, 28):                                            # stalls
        c.box(x0, 30, 14, 25, "S")
        c.rect(x0 + 1, 33, 12, 2, "s")
        c.rect(x0 + 2, 31, 3, 2, "e"); c.rect(x0 + 6, 31, 2, 2, "r"); c.rect(x0 + 9, 31, 3, 2, "y")
        window(c, x0 + 3, 38, 8, 6, lit, "i")
    d = arch_door(c, 18, 40, 9, 15, "O", "g")
    sign(c, 22, 23, "bag", "j", lit)
    base(c)
    return c, d


def f_museum(lit):
    """Relic Hall: an old overgrown temple with mossy columns and vines."""
    c = Canvas(BW, BH)
    c.box(3, 26, 38, 29, "L")
    for i in range(10):
        c.rect(22 - i * 2, 16 + i, i * 4 + 1, 1, "Q")
    c.rect(2, 25, 40, 2, "s")
    for x in (5, 12, 30, 37):
        c.rect(x, 27, 3, 26, "s"); c.rect(x - 1, 27, 5, 1, "Q"); c.rect(x - 1, 52, 5, 1, "Q")
        for y in range(28, 52, 3):
            c.px(x + (y % 2) * 2, y, "u")                         # vines
    for x in range(3, 41, 2):
        c.px(x, 27 + (x % 3), "e")
    c.rect(2, 53, 40, 2, "Q")
    c.disc(22, 21, 2, "x" if lit else "C")                        # relic gem
    d = arch_door(c, 18, 40, 9, 13, "g", "a")
    sign(c, 22, 2, "column", "x", lit)
    base(c)
    return c, d


def f_bank(lit):
    """Credit Vault (forest): a stone vault wrapped in tree roots, coins glinting in the cracks."""
    c = Canvas(BW, BH)
    c.box(3, 20, 38, 36, "Q")
    for y in range(22, 54, 5):
        for x in range(4 + (y % 2) * 4, 40, 8):
            c.rect(x, y, 6, 1, "L")
    c.rect(1, 15, 42, 6, "L"); c.rect(1, 15, 42, 1, "s")
    for (x0, d) in ((4, 1), (39, 1)):                             # roots
        for y in range(15, 55):
            c.px(x0 + int(2 * math.sin(y / 4)), y, "S")
    c.rect(8, 14, 28, 2, "S")
    for x in (10, 18, 26, 33):
        c.px(x, 20 + (x % 3), "y" if lit else "o")
    window(c, 9, 26, 4, 9, lit, "i"); window(c, 31, 26, 4, 9, lit, "i")
    d = arch_door(c, 17, 38, 11, 17, "g", "a")
    sign(c, 22, 3, "coin", "y", lit)
    base(c)
    return c, d


def f_greenhouse(lit, plants=()):
    """Gaia Gardens: a vine-framed glass dome full of the resident's plants."""
    c = Canvas(BW, BH)
    c.disc(22, 30, 20, "S", 20)
    c.rect(0, 30, BW, 26, ".")
    c.box(2, 30, 40, 26, "S")
    c.disc(22, 30, 19, "b" if lit else "a", 19)
    c.rect(3, 30, 38, 25, "b" if lit else "a")
    for x in range(6, 40, 8):
        c.rect(x, 12, 1, 43, "S")
    c.rect(2, 30, 40, 1, "S")
    for y in range(12, 54, 2):                                    # vines on the frame
        c.px(6 + (y % 3), y, "e"); c.px(38 - (y % 3), y, "e")
    c.disc(13, 20, 3, "d" if lit else "b")
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
    d = arch_door(c, 18, 40, 9, 15)
    sign(c, 22, 1, "leaf", "e", lit)
    base(c)
    return c, d


def f_radio(lit, playing=False):
    """Music Tower: a vine-wrapped wooden tower crowned with a giant bell flower."""
    c = Canvas(BW, BH)
    c.rect(18, 10, 9, 30, "S")
    for y in range(10, 40, 3):
        c.rect(18, y, 9, 1, "g")
    for y in range(10, 40):                                       # vines
        c.px(18 + int(4 + 4 * math.sin(y / 3)), y, "e")
    for i in range(7):                                            # bell flower horn
        c.rect(22 - i, 3 + i, i * 2 + 1, 1, "l" if lit else "P")
    c.rect(15, 9, 15, 2, "j" if lit else "M")
    c.rect(21, 0, 3, 3, "E"); c.px(20, 1, "e"); c.px(24, 1, "e")
    c.box(8, 38, 28, 18, "S")
    c.rect(8, 38, 28, 2, "u")
    window(c, 11, 43, 5, 5, lit, "i")
    d = arch_door(c, 18, 42, 9, 13)
    window(c, 29, 43, 5, 5, lit, "i")
    sign(c, 22, 24, "note", "j", lit)
    c.outline()
    if playing and lit:
        for (x, y) in ((6, 8), (36, 6), (10, 20)):
            c.rect(x, y, 1, 4, "q"); c.rect(x - 2, y + 3, 2, 2, "q"); c.px(x + 1, y, "q")
    c.rect(0, 55, BW, 1, "k")
    return c, d


def f_archive(lit):
    """Eternity Vault: a grassy mound with a round carved door, like an ancient barrow."""
    c = Canvas(BW, BH)
    c.disc(22, 40, 21, "u", 24)
    c.rect(0, 40, BW, 16, ".")
    c.rect(1, 40, 42, 15, "u")
    c.disc(22, 40, 21, "u", 24); c.rect(1, 40, 42, 15, "u")
    for x in range(2, 42, 3):
        c.px(x, 17 + abs(22 - x) // 2, "e")
    for y in range(24, 54, 4):
        for x in range(4 + y % 3, 41, 9):
            c.px(x, y, "E")
    c.disc(22, 40, 12, "k")
    c.disc(22, 40, 11, "y" if lit else "o")
    c.disc(22, 40, 9, "Q")
    c.disc(22, 40, 3, "s")
    for dx, dy in ((0, -6), (0, 6), (-6, 0), (6, 0)):
        c.px(22 + dx, 40 + dy, "x" if lit else "C")
    window(c, 6, 36, 4, 5, lit, "i"); window(c, 34, 36, 4, 5, lit, "i")
    sign(c, 22, 6, "box", "y", lit)
    base(c)
    return c, (18, 42, 9, 13)


def f_spaceport(lit, away=False):
    """Whisper Woods: the trailhead into the deep woods. Two old trees arch over a path, with a signpost."""
    c = Canvas(BW, BH)
    for (x0, lean) in ((4, 1), (34, -1)):                         # arching trees
        for y in range(12, 55):
            c.rect(x0 + (lean * (55 - y)) // 14 if y < 30 else x0, y, 6, 1, "S")
    leaves(c, 10, 10, 11); leaves(c, 34, 10, 11); leaves(c, 22, 6, 10)
    c.rect(10, 20, 24, 35, "a")                                   # dark path into the woods
    for y in range(26, 55):
        half = 2 + (y - 26) // 3
        c.rect(22 - half, y, half * 2, 1, "v")
    for (x, y) in ((16, 30), (27, 34), (20, 26)):                 # eyes / wisps in the dark
        c.px(x, y, "x" if lit else "C")
    if not away:
        c.rect(13, 42, 18, 3, "S"); c.rect(14, 45, 3, 8, "g"); c.rect(27, 45, 3, 8, "g")    # waiting cart
        c.disc(15, 52, 2, "k"); c.disc(28, 52, 2, "k")
        lantern(c, 22, 38, lit)
    else:
        for y in range(46, 55, 3):                                # footprints heading in
            c.px(20 + (y % 2) * 3, y, "k")
    c.rect(37, 34, 2, 20, "g")                                    # signpost
    c.box(32, 33, 12, 6, "s")
    c.rect(34, 35, 7, 1, "g")
    sign(c, 7, 22, "rocket", "x", lit)
    base(c)
    return c, (16, 44, 12, 11)


def f_workshop(lit):
    """Rune Workshop: a stone workshop with a glowing rune circle on its wall and a sparking chimney."""
    c = Canvas(BW, BH)
    c.box(2, 22, 40, 34, "Q")
    for y in range(24, 54, 5):
        for x in range(3 + (y % 2) * 3, 41, 7):
            c.rect(x, y, 5, 1, "L")
    for i in range(8):                                            # slate roof
        c.rect(2 + i, 22 - i, 40 - i * 2, 1, "g")
    c.rect(32, 6, 5, 12, "Q"); c.rect(31, 5, 7, 2, "L")          # chimney
    if lit:
        for (x, y) in ((34, 2), (36, 0), (33, 1)):
            c.px(x, y, "i")
    c.disc(13, 38, 8, "k"); c.disc(13, 38, 7, "a")                 # rune circle
    for a in range(0, 360, 30):
        c.px(int(13 + 6 * math.cos(math.radians(a))), int(38 + 6 * math.sin(math.radians(a))), "x" if lit else "C")
    c.rect(12, 34, 3, 9, "x" if lit else "C"); c.rect(9, 37, 9, 2, "x" if lit else "C")
    window(c, 33, 30, 6, 8, lit, "x")
    d = arch_door(c, 23, 40, 9, 15)
    sign(c, 18, 9, "gear", "x", lit)
    base(c)
    return c, (23, 40, 9, 15)


def f_mech_shop(lit):
    """Tinker Hollow: a timber barn with a turning water wheel and cogs on the gable."""
    c = Canvas(BW, BH)
    c.box(8, 24, 34, 31, "S")
    for x in range(10, 41, 3):
        c.rect(x, 25, 1, 29, "g")
    for i in range(10):
        c.rect(25 - i * 2, 14 + i, i * 4 + 1, 1, "O")
    c.disc(25, 18, 3, "y" if lit else "o"); c.disc(25, 18, 1, "k")  # cog on the gable
    c.disc(7, 42, 9, "S"); c.disc(7, 42, 7, "a")                   # water wheel
    for a in range(0, 360, 45):
        x, y = 7 + 8 * math.cos(math.radians(a)), 42 + 8 * math.sin(math.radians(a))
        c.px(int(x), int(y), "s")
        for t in range(1, 7):
            c.px(int(7 + t * math.cos(math.radians(a))), int(42 + t * math.sin(math.radians(a))), "g")
    c.disc(7, 42, 2, "s")
    c.rect(0, 52, 16, 3, "C"); c.rect(0, 52, 16, 1, "x")           # stream
    c.rect(16, 34, 20, 21, "k")                                     # barn door
    for y in range(35, 55, 2):
        c.rect(17, y, 18, 1, "S" if y % 4 else "s")
    c.rect(17, 35, 18, 1, "g"); c.rect(25, 35, 1, 20, "g")
    window(c, 37, 30, 4, 6, lit, "i")
    d = (21, 40, 9, 15)
    sign(c, 25, 25, "wrench", "y", lit)
    base(c)
    return c, d


def f_studio(c, lit):
    """Sun Song annex beside the Music Tower: a little round hut with a sun on its roof."""
    c.box(32, 40, 12, 15, "s")
    c.disc(38, 40, 4, "y" if lit else "o", 3); c.rect(33, 40, 10, 2, "Y" if lit else "O")
    window(c, 35, 45, 6, 4, lit, "i")
    c.rect(34, 51, 8, 1, "k")


FOREST_STATION = [   # the World Tree's crown: a lantern-lit platform high in the canopy
    "..........kkkkkk..........",
    ".......kkbbddddbbkk.......",
    "....kkbbddbbddddbbbbkk....",
    "..kbbddddbbbbddbbddddbbk..",
    ".kbbbbiddbbddbbbbddibbbbk.",
    "..kkbbbbbbkkSSkkbbbbbbkk..",
    "....kkkkkkkSSSSkkkkkkk....",
    "..........kSyySk..........",
    "...........kSSk...........",
]


# ------------------------------------------------------------------ v0.13.5 picks: the chosen forest styles
# Picked from mockups: Burrow gallery, Willow Pond park, Wizard Tower trade, Fallen Log grove, Treehouse home,
# Moon Tower library, Cherry Tree salon.
def petals(c, cx, cy, r, col, hi):
    c.disc(cx, cy, r, col, r * .8)
    c.disc(cx - 1, cy - 1, max(1, r - 2), hi, max(1, r - 2) * .7)


def gallery_burrow(lit, painting=None):
    """Prism Gallery as a hillside burrow: crystal-lit round windows and a big framed painting at the front."""
    c = Canvas(BW, BH)
    c.disc(22, 44, 21, "u", 26); c.rect(0, 44, BW, 12, ".")
    c.rect(1, 44, 42, 11, "u")
    c.disc(22, 44, 21, "u", 26); c.rect(1, 44, 42, 11, "u")
    for x in range(2, 42, 3):
        c.px(x, 19 + abs(22 - x) * 3 // 4, "e")
    for (x, y, r, col) in ((7, 38, 3, "x"), (37, 38, 3, "j"), (10, 28, 2, "y"), (34, 28, 2, "c")):
        c.disc(x, y, r + 1, "S"); c.disc(x, y, r, col if lit else "a")     # coloured glass windows
    for (x, h) in ((16, 6), (19, 9), (25, 8), (28, 5)):                     # crystals on the roof
        c.rect(x, 22 - h, 2, h, "x" if lit else "C"); c.px(x, 21 - h, "w")
    c.box(13, 25, 18, 14, "S"); c.rect(14, 26, 16, 12, "n")                 # featured painting
    for y in range(12):
        for x in range(16):
            ch = painting[y * len(painting) // 12][x * len(painting) // 16] if painting else "mjxcyp"[(x + y) // 4 % 6]
            if ch != ".":
                c.px(14 + x, 26 + y, ch)
    arch_door(c, 18, 42, 9, 13)
    sign(c, 22, 6, "star", "j", lit)
    base(c)
    return c


def park_willow(lit):
    """A weeping willow over a lily pond, with a bench in its shade."""
    c = Canvas(BW, BH)
    c.rect(0, 46, BW, 9, "u"); c.rect(0, 46, BW, 1, "e")
    c.disc(30, 49, 11, "C", 3); c.disc(30, 49, 10, "x" if lit else "b", 2)
    for (x, y) in ((25, 49), (33, 48), (37, 50)):
        c.rect(x, y, 3, 1, "E"); c.px(x + 1, y - 1, "m")
    c.rect(11, 22, 4, 25, "S"); c.rect(12, 22, 1, 25, "g")
    c.disc(13, 16, 13, "E", 9); c.disc(12, 14, 10, "e", 6)
    for x in range(1, 27, 2):                                    # hanging willow strands
        ln = 14 + (x * 7) % 12
        for y in range(18, 18 + ln):
            c.px(x + (y // 6) % 2, y, "e" if (x + y) % 3 else "E")
    c.rect(2, 48, 9, 1, "S"); c.px(2, 49, "g"); c.px(10, 49, "g")
    if lit:
        lantern(c, 26, 20, lit); lantern(c, 6, 22, lit)
        for (x, y) in ((34, 34), (40, 28), (30, 40)):
            c.px(x, y, "q")
    sign(c, 35, 14, "leaf", "e", lit)
    c.outline()
    c.rect(0, 54, BW, 1, "U"); c.rect(0, 55, BW, 1, "k")
    return c


def trade_tower(lit):
    """A narrow wizard's tower with a starry pointed hat."""
    c = Canvas(BW, BH)
    c.box(12, 24, 20, 31, "Q")
    for y in range(26, 54, 4):
        for x in range(13 + (y % 2) * 3, 31, 6):
            c.rect(x, y, 4, 1, "L")
    for i in range(20):                                          # hat
        w = 2 + i
        c.rect(22 - w // 2 + (3 if i < 5 else 0), 4 + i, w, 1, "P")
    c.rect(8, 23, 28, 2, "P")
    for (x, y) in ((20, 14), (24, 19), (17, 21), (27, 22)):
        c.px(x, y, "y" if lit else "o")
    c.px(26, 3, "y" if lit else "o")
    window(c, 19, 28, 6, 6, lit, "j")
    c.box(2, 40, 12, 15, "P"); c.rect(2, 40, 12, 2, "y" if lit else "o")   # side stall
    c.rect(4, 44, 3, 2, "x"); c.rect(9, 44, 3, 2, "j")
    d = arch_door(c, 18, 40, 9, 15, "M", "P")
    lantern(c, 38, 34, lit)
    sign(c, 37, 22, "gavel", "y", lit)
    base(c)
    return c


def grove_log(lit):
    """A fallen hollow log turned into a pet shop, with a fern roof and a fence."""
    c = Canvas(BW, BH)
    c.rect(2, 30, 40, 25, "S")
    for y in range(31, 54, 3):
        c.rect(3, y, 34, 1, "g")
    c.disc(40, 42, 4, "S", 12); c.disc(40, 42, 3, "s", 10)         # cut end with rings
    c.disc(40, 42, 1, "o", 5)
    for (x, r) in ((8, 6), (18, 7), (28, 6), (36, 5)):
        c.disc(x, 30, r, "E", r * .5); c.disc(x - 1, 29, r - 2, "e", (r - 2) * .4)
    mushroom(c, 12, 24, 3, 2, "i", "y")
    window(c, 6, 37, 7, 6, lit, "i"); window(c, 27, 37, 7, 6, lit, "i")
    if lit:
        c.px(8, 40, "k"); c.px(10, 40, "k"); c.rect(8, 41, 3, 1, "O")
    d = arch_door(c, 17, 40, 8, 15)
    for x in range(0, 44, 4):
        c.rect(x, 50, 1, 5, "s")
    c.rect(0, 51, BW, 1, "s")
    sign(c, 22, 14, "paw", "j", lit)
    base(c)
    return c


def home_treehouse(lit, floors=1):
    """Sprout House as a treehouse: each extra floor is another room further up the trunk, sprout on top."""
    floors = max(1, min(4, floors))
    T = 8                                                        # room above the canopy for the sprout
    extra = 14 * (floors - 1)
    H = BH + extra + T
    c = Canvas(BW, H)
    c.rect(18, T + 14, 8, H - 14 - T, "S"); c.rect(19, T + 14, 1, H - 14 - T, "g")
    for d in (-1, 1):
        for i in range(6):
            c.rect(22 + d * (4 + i), H - 3 + i // 3, 1, 3, "S")
    leaves(c, 11, T + 10, 10, "E", "e"); leaves(c, 33, T + 10, 10, "E", "e"); leaves(c, 22, T + 7, 10, "E", "e")
    c.rect(21, 0, 2, T + 2, "E"); c.px(22, 0, "e")              # the sprout, poking out of the canopy
    c.disc(17, 3, 4, "q", 2); c.disc(27, 2, 4, "q", 2)
    c.disc(17, 3, 2, "Y", 1); c.disc(27, 2, 2, "Y", 1)

    def room(y, w):
        x0 = 22 - w // 2
        c.box(x0, y, w, 14, "s"); c.rect(x0, y, w, 1, "t")
        for x in range(x0 + 2, x0 + w - 1, 3):
            c.rect(x, y + 1, 1, 12, "o")
        for i in range(5):
            c.rect(x0 - 2 + i, y - i, w + 4 - i * 2, 1, "O")
        porthole(c, x0 + 7, y + 7, 3, lit, "i"); porthole(c, x0 + w - 8, y + 7, 3, lit, "i")
        c.rect(x0 - 2, y + 14, w + 4, 2, "S")
    for f in range(floors):                                      # top room first, ground-level room last
        room(T + 20 + f * 14, 26 if f < floors - 1 else 32)
    by = T + 20 + floors * 14 + 2
    for y in range(by, H - 1, 3):                                # rope ladder down to the door
        c.rect(9, y, 5, 1, "o")
    c.rect(9, by, 1, H - 1 - by, "O"); c.rect(13, by, 1, H - 1 - by, "O")
    arch_door(c, 18, H - 16, 8, 15)
    c.box(29, H - 9, 9, 8, "O"); c.rect(30, H - 8, 7, 2, "e")
    lantern(c, 40, by - 2, lit)
    base(c)
    return c


def library_moon_tower(lit):
    """A slim stone tower wound with vines, with a big round moon window and a lookout perch."""
    c = Canvas(BW, BH)
    c.box(11, 14, 22, 41, "Q")
    for y in range(16, 54, 4):
        for x in range(12 + (y % 2) * 3, 32, 6):
            c.rect(x, y, 4, 1, "L")
    for i in range(10):
        c.rect(22 - i - 2, 4 + i, (i + 2) * 2 + 1, 1, "g")
    c.disc(22, 26, 7, "k"); c.disc(22, 26, 6, "t" if lit else "D")
    if lit:
        c.disc(24, 24, 4, "n"); c.rect(18, 28, 8, 1, "S"); c.rect(19, 29, 6, 1, "S")
    for y in range(14, 55):
        if y % 2:
            c.px(11 + int(11 + 10 * math.sin(y / 5)), y, "e")
    c.rect(33, 18, 9, 2, "S"); c.rect(39, 15, 3, 3, "O"); c.px(42, 16, "y")
    c.box(1, 38, 11, 17, "S"); window(c, 3, 42, 6, 6, lit, "i")      # reading room
    c.box(33, 38, 10, 17, "S"); window(c, 35, 42, 6, 6, lit, "i")
    d = arch_door(c, 18, 41, 9, 14, "g", "a")
    sign(c, 22, 35, "book", "x", lit)
    base(c)
    return c


def salon_cherry(lit):
    """A cherry blossom tree with the salon tucked into its curved trunk."""
    c = Canvas(BW, BH)
    for y in range(18, 55):
        x = 16 + int(3 * math.sin(y / 6))
        c.rect(x, y, 13, 1, "S")
        c.px(x + 2, y, "g")
    for (x, y, r) in ((8, 14, 9), (22, 9, 11), (36, 14, 9), (14, 22, 6), (31, 22, 6)):
        petals(c, x, y, r, "M", "m")
    for (x, y) in ((5, 12), (12, 6), (20, 3), (30, 8), (38, 10), (27, 18), (16, 16), (41, 20)):
        c.px(x, y, "w")
    for (x, y) in ((4, 40), (40, 44), (8, 50), (34, 36), (38, 52)):
        c.px(x, y, "m")
    window(c, 18, 26, 9, 7, lit, "j")
    d = arch_door(c, 18, 40, 9, 15, "M", "R")
    c.box(30, 42, 12, 13, "s"); window(c, 32, 45, 8, 5, lit, "j")      # little side room
    c.box(2, 46, 10, 9, "s"); c.rect(3, 47, 8, 2, "m")
    sign(c, 7, 34, "star", "x", lit)
    base(c)
    return c


def _home(lit, floors=1):
    c = home_treehouse(lit, floors)
    return c, (18, c.h - 16, 8, 15)


f_home = _home
f_gallery = lambda lit, painting=None: (gallery_burrow(lit, painting), (18, 42, 9, 13))
f_park = lambda lit: (park_willow(lit), (18, 45, 9, 10))
f_exchange = lambda lit: (trade_tower(lit), (18, 40, 9, 15))
f_pet_shop = lambda lit: (grove_log(lit), (17, 40, 8, 15))
f_library = lambda lit: (library_moon_tower(lit), (18, 41, 9, 14))
f_salon = lambda lit: (salon_cherry(lit), (18, 40, 9, 15))


# ================================================================== the Ocean world
def wave_line(c, y, col="x"):
    for x in range(0, BW, 4):
        c.px(x, y, col); c.px(x + 1, y - 1, col)


def o_home(lit, floors=1):
    """Coral Cottage: a round cottage built of pink coral with a scallop-shell roof. Extra floors stack up."""
    extra = 14 * (max(1, min(4, floors)) - 1)
    c = Canvas(BW, BH + extra)
    top = 20
    for f in range(floors - 1):
        y = top + 12 + f * 14
        c.box(6, y, 32, 14, "j")
        for wx in (12, 22, 32):
            porthole(c, wx, y + 7, 2, lit, "y")
        for x in range(7, 37, 5):
            c.px(x, y + 2, "m")
    by = top + 12 + extra
    c.box(3, by, 38, BH + extra - by, "j")
    for (x, y) in ((6, by + 3), (14, by + 6), (30, by + 4), (36, by + 9), (9, by + 14), (34, by + 16)):
        c.disc(x, y, 1, "m")
    c.disc(22, top + 10, 20, "w", 12)                            # scallop shell roof
    c.rect(0, top + 11, BW, 14, ".")
    for i in range(-18, 19, 4):
        for t in range(12):
            c.px(22 + i * t // 12, top + 10 - t, "t")
    c.rect(2, top + 10, 40, 2, "i")
    porthole(c, 10, by + 9, 3, lit, "y")
    porthole(c, 34, by + 9, 3, lit, "y")
    d = arch_door(c, 18, BH + extra - 16, 9, 15, "u", "g")
    c.outline()
    c.disc(40, by - 2, 2, "y")                                    # pearl lamp
    c.rect(0, BH + extra - 1, BW, 1, "k")
    return c, d


def o_library(lit):
    """Lighthouse Library: a red-and-white lighthouse full of books, its lamp turning at the top."""
    c = Canvas(BW, BH)
    for y in range(14, 55):
        half = 8 + (y - 14) // 6
        col = "r" if ((y - 14) // 8) % 2 else "w"
        c.rect(22 - half, y, half * 2, 1, col)
    c.rect(12, 11, 20, 3, "k"); c.rect(13, 12, 18, 1, "S")       # gallery rail
    c.rect(16, 4, 12, 7, "k"); c.rect(17, 5, 10, 5, "y" if lit else "n")
    c.rect(15, 2, 14, 2, "R"); c.rect(21, 0, 2, 2, "R")
    if lit:
        for i in range(1, 8):                                     # beams
            c.px(16 - i, 6 + i // 3, "t"); c.px(27 + i, 6 + i // 3, "t")
    window(c, 19, 22, 6, 6, lit, "y")
    d = arch_door(c, 18, 40, 9, 15, "u", "g")
    sign(c, 22, 30, "book", "C", lit)
    base(c)
    return c, d


def o_cafe(lit):
    """Tidewire Café: a beach shack with a surfboard, glowing screens, and its cable running into the sea."""
    c = Canvas(BW, BH)
    c.box(3, 22, 38, 34, "S")
    for x in range(5, 40, 3):
        c.rect(x, 23, 1, 31, "g")
    for i in range(6):                                            # tin roof
        c.rect(1 + i, 22 - i, 42 - i * 2, 1, "s" if i % 2 else "S")
    c.rect(1, 22, 42, 2, "x" if lit else "C")                     # neon band
    window(c, 6, 28, 12, 11, lit, "x"); window(c, 26, 28, 12, 11, lit, "x")
    if lit:
        for wx in (8, 28):
            c.rect(wx, 31, 7, 4, "C"); c.rect(wx + 1, 32, 5, 1, "w")
    c.rect(40, 18, 3, 37, "y"); c.rect(41, 18, 1, 37, "r")         # surfboard
    for x in range(0, 20):                                         # the cable into the sea
        c.px(x, 54 - (x % 2), "x" if lit else "C")
    d = arch_door(c, 18, 40, 9, 15, "u", "g")
    sign(c, 22, 5, "at", "x", lit)
    base(c)
    return c, d


def o_post(lit):
    """Bottle Post: a boathouse with a giant message-in-a-bottle on its roof and a mailbox buoy."""
    c = Canvas(BW, BH)
    c.box(5, 24, 34, 32, "C")
    for y in range(26, 54, 4):
        c.rect(6, y, 32, 1, "b")
    for i in range(6):
        c.rect(3 + i, 24 - i, 38 - i * 2, 1, "S")
    c.rect(10, 8, 24, 10, "e"); c.rect(10, 8, 24, 1, "c")         # the bottle (on its side)
    c.rect(34, 11, 4, 4, "e"); c.rect(38, 11, 2, 4, "O")
    c.rect(14, 10, 12, 6, "t"); c.rect(16, 12, 8, 1, "o")         # the letter inside
    porthole(c, 12, 32, 4, lit, "y"); porthole(c, 32, 32, 4, lit, "y")
    d = arch_door(c, 18, 40, 9, 15, "u", "g")
    c.disc(3, 48, 3, "r"); c.rect(2, 50, 3, 5, "w"); c.rect(1, 47, 5, 1, "w")   # buoy
    sign(c, 22, 1, "mail", "y", lit)
    base(c)
    return c, d


def o_gallery(lit, painting=None):
    """Pearl Gallery: a gallery with a pearly scallop-shell front."""
    c = Canvas(BW, BH)
    c.box(2, 18, 40, 38, "N")
    c.disc(22, 18, 21, "w", 13)
    c.rect(0, 19, BW, 14, ".")
    for i in range(-20, 21, 4):
        for t in range(13):
            c.px(22 + i * t // 13, 18 - t, "i")
    c.rect(0, 18, 44, 2, "t")
    for x in (3, 39):
        c.rect(x, 20, 2, 35, "i")
    c.box(10, 21, 24, 21, "o")
    c.rect(12, 23, 20, 17, "n")
    if painting:
        n = len(painting)
        for y in range(17):
            for x in range(18):
                ch = painting[y * n // 17][x * n // 18]
                if ch != ".":
                    c.px(13 + x, 23 + y, ch)
    c.disc(22, 10, 2, "w")                                       # the pearl
    d = arch_door(c, 18, 44, 9, 11, "u", "g")
    window(c, 6, 45, 6, 6, lit, "y"); window(c, 32, 45, 6, 6, lit, "y")
    sign(c, 22, 0, "star", "j", lit)
    base(c)
    return c, d


def o_park(lit):
    """Lagoon Park: a sandy lagoon with palm trees, a tide pool, a bench and a chess table."""
    c = Canvas(BW, BH)
    c.rect(0, 46, BW, 9, "l"); c.rect(0, 46, BW, 1, "t")
    for x in range(0, 44, 4):
        c.px(x, 48 + (x % 3), "o")
    for (tx, h, lean) in ((6, 28, 1), (37, 24, -1)):             # palms
        for y in range(h):
            c.rect(tx + lean * (y // 6), 46 - y, 2, 1, "o")
        top_x, top_y = tx + lean * (h // 6), 46 - h
        for dx, dy in ((-6, 3), (6, 3), (-4, 1), (4, 1), (-7, 5), (7, 5), (0, -1)):
            for t in range(4):
                c.px(top_x + dx * t // 4, top_y + dy * t // 4 + t // 2, "E")
        c.px(top_x, top_y + 2, "O"); c.px(top_x + 1, top_y + 2, "O")
    c.disc(22, 47, 7, "C", 2); c.disc(22, 47, 6, "x" if lit else "C", 1.5)   # tide pool
    c.px(20, 47, "j"); c.px(25, 46, "y")
    c.rect(12, 49, 6, 1, "S"); c.px(12, 50, "g"); c.px(17, 50, "g")
    c.rect(28, 49, 5, 2, "k")
    for x in range(28, 33):
        c.px(x, 49, "w" if x % 2 else "k")
    c.px(30, 51, "g")
    sign(c, 22, 20, "leaf", "e", lit)
    c.outline()
    c.rect(0, 54, BW, 1, "l")
    c.rect(0, 55, BW, 1, "k")
    return c, (18, 45, 9, 10)


def o_store(lit):
    """Reef Market: a striped market stall stacked with crates, nets and a fish sign."""
    c = Canvas(BW, BH)
    c.box(2, 22, 40, 33, "S")
    for x in range(4, 41, 3):
        c.rect(x, 23, 1, 31, "g")
    for i, x in enumerate(range(0, 44, 6)):
        c.rect(x, 16, 6, 6, ("C" if i % 2 else "w") if lit else ("b" if i % 2 else "g"))
        c.px(x + 2, 22, "C" if i % 2 else "w")
    c.rect(0, 15, 44, 1, "k")
    for x in (5, 29):
        c.rect(x, 30, 10, 9, "k"); c.rect(x + 1, 31, 8, 7, "t" if lit else "D")
        c.rect(x + 2, 34, 3, 3, "j" if lit else "R"); c.rect(x + 6, 33, 2, 4, "x" if lit else "C")
    c.box(1, 46, 8, 9, "O"); c.box(36, 46, 7, 9, "O")
    d = arch_door(c, 18, 40, 9, 15, "u", "g")
    sign(c, 22, 3, "bag", "C", lit)
    base(c)
    return c, d


def o_museum(lit):
    """Shipwreck Museum: an old ship's hull hauled up on the boardwalk, mast and all."""
    c = Canvas(BW, BH)
    for y in range(28, 55):
        inset = max(0, (y - 44)) // 2
        c.rect(1 + inset, y, 42 - inset * 2, 1, "S" if y % 3 else "g")
    c.rect(0, 28, 44, 2, "O")
    c.rect(21, 4, 2, 24, "o")                                    # mast
    c.rect(12, 8, 20, 1, "o")
    for y in range(9, 22):                                        # torn sail
        c.rect(14 + (y - 9) // 4, y, 16 - (y - 9) // 2, 1, "t" if y % 4 else "s")
    for x in (8, 15, 29, 36):
        porthole(c, x, 36, 2, lit, "y")
    c.disc(22, 22, 2, "y" if lit else "o")
    for (x, y) in ((4, 50), (40, 44), (10, 46)):                  # barnacles
        c.px(x, y, "i")
    d = arch_door(c, 18, 40, 9, 13, "u", "g")
    sign(c, 34, 14, "column", "y", lit)
    base(c)
    return c, d


def o_pet_shop(lit):
    """Hatchery: a round aquarium building with little creatures swimming inside."""
    c = Canvas(BW, BH)
    c.disc(22, 32, 20, "S", 20); c.rect(0, 46, BW, 10, ".")
    c.box(4, 40, 36, 15, "S")
    c.disc(22, 30, 17, "b" if lit else "a", 16)
    for (x, y, col) in ((14, 26, "Y"), (28, 22, "j"), (22, 34, "y"), (31, 32, "x")):
        if lit:
            c.rect(x, y, 3, 2, col); c.px(x - 1, y, col); c.px(x + 3, y + 1, "k")
    for y in range(18, 44, 6):
        c.px(10 + y % 5, y, "i"); c.px(33 - y % 4, y - 2, "i")
    c.rect(4, 44, 36, 1, "o")
    d = arch_door(c, 18, 40, 9, 15, "u", "g")
    sign(c, 22, 4, "paw", "j", lit)
    c.rect(6, 52, 4, 3, "O"); c.rect(35, 52, 4, 3, "O")
    base(c)
    return c, d


def o_exchange(lit):
    """Driftwood Exchange: an auction hall of weathered driftwood, hung with nets and floats."""
    c = Canvas(BW, BH)
    c.box(3, 22, 38, 34, "s")
    for y in range(24, 54, 3):
        c.rect(4, y, 36, 1, "S" if y % 2 else "o")
    for i in range(10):
        c.rect(22 - i * 2, 12 + i, i * 4 + 1, 1, "S")
    for x in range(4, 40, 2):                                     # net
        c.px(x, 24 + (x % 4), "g")
    for x in (8, 18, 28, 36):
        c.disc(x, 27, 1, "Y" if lit else "O")                     # floats
    window(c, 7, 31, 5, 7, lit, "y"); window(c, 32, 31, 5, 7, lit, "y")
    c.rect(16, 36, 13, 2, "y" if lit else "o")
    d = arch_door(c, 18, 40, 9, 15, "u", "g")
    sign(c, 22, 1, "gavel", "y", lit)
    base(c)
    return c, d


def o_bank(lit):
    """Clam Vault: a giant clam, open just enough to show the pearl, on a stone base."""
    c = Canvas(BW, BH)
    c.box(4, 44, 36, 11, "L")
    c.disc(22, 44, 20, "j", 14); c.rect(0, 44, BW, 12, ".")         # top shell
    for i in range(-18, 19, 4):
        for t in range(14):
            c.px(22 + i * t // 14, 44 - t, "m")
    c.rect(4, 42, 36, 3, "k")
    c.disc(22, 40, 4, "w" if lit else "s"); c.px(21, 39, "t")       # pearl
    c.rect(4, 44, 36, 2, "j")
    window(c, 7, 47, 4, 5, lit, "y"); window(c, 33, 47, 4, 5, lit, "y")
    d = arch_door(c, 17, 45, 11, 10, "u", "g")
    sign(c, 22, 14, "coin", "y", lit)
    base(c)
    return c, d


def o_greenhouse(lit, plants=()):
    """Kelp Gardens: a water-filled glass dome where the resident's plants grow among bubbles."""
    c = Canvas(BW, BH)
    c.disc(22, 30, 20, "S", 20)
    c.rect(0, 30, BW, 26, ".")
    c.box(2, 30, 40, 26, "S")
    c.disc(22, 30, 19, "d" if lit else "b", 19)
    c.rect(3, 30, 38, 25, "d" if lit else "b")
    for x in range(6, 40, 8):
        c.rect(x, 12, 1, 43, "s")
    c.rect(2, 30, 40, 1, "s")
    for (x, y) in ((12, 22), (30, 18), (24, 28), (16, 36), (34, 40)):
        c.px(x, y, "i"); c.px(x + 1, y - 2, "i")
    for x in (5, 39):                                             # kelp fronds
        for y in range(30, 48):
            c.px(x + (y // 3) % 2, y, "v")
    c.rect(4, 49, 36, 3, "l"); c.rect(4, 49, 36, 1, "t")
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
    d = arch_door(c, 18, 40, 9, 15, "u", "g")
    sign(c, 22, 1, "leaf", "e", lit)
    base(c)
    return c, d


def o_radio(lit, playing=False):
    """Beacon Tower: a striped lattice beacon with a lamp and a foghorn."""
    c = Canvas(BW, BH)
    for y in range(6, 40):
        half = 2 + (y - 6) // 5
        col = "r" if (y // 5) % 2 else "w"
        c.px(22 - half, y, col); c.px(22 + half, y, col)
        if y % 5 == 0:
            c.rect(22 - half, y, half * 2 + 1, 1, "S")
    c.rect(19, 1, 7, 5, "k"); c.rect(20, 2, 5, 3, "y" if lit else "n")
    c.rect(26, 14, 6, 3, "s"); c.rect(32, 13, 2, 5, "s")          # foghorn
    c.box(8, 38, 28, 18, "C")
    c.rect(8, 38, 28, 2, "x" if lit else "b")
    window(c, 11, 43, 5, 5, lit, "y")
    d = arch_door(c, 18, 42, 9, 13, "u", "g")
    window(c, 29, 43, 5, 5, lit, "y")
    sign(c, 22, 26, "note", "x", lit)
    c.outline()
    if playing and lit:
        for (x, y) in ((6, 8), (36, 6), (10, 20)):
            c.rect(x, y, 1, 4, "x"); c.rect(x - 2, y + 3, 2, 2, "x"); c.px(x + 1, y, "x")
    c.rect(0, 55, BW, 1, "k")
    return c, d


def o_archive(lit):
    """Sunken Archive: a barnacled stone vault with a round brass hatch."""
    c = Canvas(BW, BH)
    c.box(2, 14, 40, 42, "L")
    c.rect(2, 14, 40, 3, "Q")
    for y in range(20, 55, 5):
        c.rect(3, y, 38, 1, "K")
    for (x, y) in ((5, 18), (38, 22), (7, 48), (36, 50), (30, 17), (12, 24)):
        c.px(x, y, "i"); c.px(x + 1, y, "s")
    for x in range(3, 41, 3):                                     # seaweed at the base
        c.rect(x, 50 - (x % 4), 1, 5 + (x % 4), "v")
    c.disc(22, 36, 12, "k")
    c.disc(22, 36, 11, "Y" if lit else "O")
    c.disc(22, 36, 8, "C")
    for dx, dy in ((0, -10), (0, 10), (-10, 0), (10, 0), (7, 7), (-7, 7), (7, -7), (-7, -7)):
        c.px(22 + dx, 36 + dy, "y" if lit else "o")
    c.disc(22, 36, 3, "s")
    sign(c, 22, 2, "box", "y", lit)
    window(c, 5, 22, 4, 6, lit, "y"); window(c, 35, 22, 4, 6, lit, "y")
    base(c)
    return c, (18, 42, 9, 13)


def o_salon(lit):
    """Shell Salon: a salon inside a giant spiral conch."""
    c = Canvas(BW, BH)
    for y in range(8, 55):                                        # conch body
        half = min(20, 3 + (y - 8) * 2 // 3)
        c.rect(22 - half, y, half * 2, 1, "t" if (y // 4) % 2 else "j")
    for t in range(0, 40):                                        # spiral ridges
        a = t / 4
        c.px(int(22 + math.cos(a) * t / 3), int(26 + math.sin(a) * t / 4), "m")
    c.rect(20, 3, 4, 5, "j"); c.px(22, 2, "m")
    window(c, 7, 38, 8, 8, lit, "m"); window(c, 29, 38, 8, 8, lit, "m")
    d = arch_door(c, 18, 40, 9, 15, "M", "R")
    sign(c, 34, 10, "star", "x", lit)
    base(c)
    return c, d


def o_spaceport(lit, away=False):
    """Submarine Dock: a little dock with a yellow submarine waiting in the water (gone while it dives)."""
    c = Canvas(BW, BH)
    c.rect(0, 44, BW, 11, "b"); c.rect(0, 44, BW, 1, "d")         # dock pool
    wave_line(c, 46, "d")
    c.rect(0, 50, BW, 5, "S"); c.rect(0, 50, BW, 1, "s")           # pier
    for x in range(2, 44, 8):
        c.rect(x, 51, 2, 4, "u")
    c.rect(34, 8, 2, 42, "S")                                      # crane
    c.rect(22, 8, 14, 2, "Y" if lit else "O"); c.rect(23, 10, 1, 8, "s")
    if not away:
        c.disc(22, 40, 11, "y", 5)                                 # submarine
        c.rect(19, 30, 6, 6, "y"); c.rect(21, 26, 1, 4, "s"); c.rect(21, 26, 3, 1, "s")
        porthole(c, 16, 40, 2, lit, "x"); porthole(c, 22, 40, 2, lit, "x"); porthole(c, 28, 40, 2, lit, "x")
        c.rect(31, 39, 3, 3, "Y")
    else:
        for (x, y) in ((18, 42), (22, 40), (25, 43), (21, 37)):     # bubbles where it dived
            c.px(x, y, "i")
    c.box(1, 30, 12, 15, "C")
    window(c, 3, 33, 8, 5, lit, "x")
    sign(c, 7, 18, "rocket", "x", lit)
    base(c)
    return c, (3, 39, 8, 6)


def o_workshop(lit):
    """Bubble Lab: a glass bubble lab on stilts, bubbling away, with a hatch below."""
    c = Canvas(BW, BH)
    for x in (8, 34):
        c.rect(x, 40, 2, 15, "S")
    c.disc(22, 26, 17, "C", 15)
    c.disc(22, 26, 15, "b" if lit else "a", 13)
    c.disc(16, 20, 3, "i")
    c.rect(14, 30, 4, 7, "x" if lit else "C"); c.rect(24, 28, 5, 9, "j" if lit else "R")   # flasks
    c.rect(13, 36, 18, 2, "s")
    if lit:
        for (x, y) in ((15, 26), (26, 24), (27, 20), (16, 22)):
            c.px(x, y, "w")
    c.box(4, 40, 36, 15, "S")
    window(c, 31, 43, 6, 6, lit, "x")
    d = arch_door(c, 18, 40, 9, 15, "u", "g")
    sign(c, 22, 2, "gear", "x", lit)
    base(c)
    return c, d


def o_mech_shop(lit):
    """Anchor Works: a boathouse workshop with a big anchor on the front and a hoist."""
    c = Canvas(BW, BH)
    c.box(2, 22, 40, 33, "S")
    for y in range(24, 54, 3):
        c.rect(3, y, 38, 1, "g")
    for i in range(7):
        c.rect(2 + i, 22 - i, 40 - i * 2, 1, "C" if i % 2 else "b")
    c.rect(28, 6, 1, 10, "S"); c.rect(28, 6, 12, 1, "Y" if lit else "O")
    c.rect(38, 7, 1, 6, "s"); c.rect(37, 13, 3, 2, "s")
    c.rect(10, 34, 24, 21, "k")
    for y in range(35, 55, 2):
        c.rect(11, y, 22, 1, "C" if y % 4 else "b")
    c.rect(21, 24, 2, 8, "s"); c.rect(18, 25, 8, 1, "s")           # anchor
    c.rect(17, 31, 10, 1, "s"); c.px(16, 30, "s"); c.px(27, 30, "s")
    c.disc(22, 23, 1, "s")
    window(c, 4, 36, 5, 6, lit, "y"); window(c, 35, 36, 5, 6, lit, "y")
    d = (18, 40, 9, 15)
    sign(c, 8, 9, "wrench", "y", lit)
    base(c)
    return c, d


def o_studio(c, lit):
    """Whalesong Studio annex beside the Beacon Tower: a round hut with a whale on its roof."""
    c.box(32, 40, 12, 15, "C")
    c.rect(33, 37, 9, 3, "b"); c.px(42, 36, "b"); c.px(43, 35, "b"); c.px(35, 38, "w")
    window(c, 35, 45, 6, 4, lit, "x")
    c.rect(34, 51, 8, 1, "k")


OCEAN_STATION = [   # the Abyss Station's surface buoy, out on the water
    "...........kk...........",
    "..........krrk..........",
    "..........kyyk..........",
    "...........kk...........",
    "..........kssk..........",
    "........kkrrrrkk........",
    "......kkrrwwwwrrkk......",
    "....kkddddddddddddkk....",
    "..kddiddddiddddddiddk...",
]


FOREST = {"home": f_home, "library": f_library, "internet_cafe": f_cafe, "post_office": f_post,
          "gallery": f_gallery, "park": f_park, "store": f_store, "museum": f_museum, "pet_shop": f_pet_shop,
          "exchange": f_exchange, "bank": f_bank, "greenhouse": f_greenhouse, "radio_tower": f_radio,
          "archive": f_archive, "salon": f_salon, "spaceport": f_spaceport, "workshop": f_workshop,
          "mech_shop": f_mech_shop}
OCEAN = {"home": o_home, "library": o_library, "internet_cafe": o_cafe, "post_office": o_post,
         "gallery": o_gallery, "park": o_park, "store": o_store, "museum": o_museum, "pet_shop": o_pet_shop,
         "exchange": o_exchange, "bank": o_bank, "greenhouse": o_greenhouse, "radio_tower": o_radio,
         "archive": o_archive, "salon": o_salon, "spaceport": o_spaceport, "workshop": o_workshop,
         "mech_shop": o_mech_shop}
SETS = {"forest": (FOREST, f_studio, FOREST_STATION, 40), "ocean": (OCEAN, o_studio, OCEAN_STATION, 86)}


def builders(world):
    """(builders, studio annex, station sprite, station y) for a world, or None for the Moon."""
    return SETS.get(world)
