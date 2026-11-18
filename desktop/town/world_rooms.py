"""v0.15.1: forest and ocean versions of the shared interior pieces: walls, floor, lamps, door and window.
Every room in interiors.py is built from these, so each world reskins all 20 rooms while they keep their furniture.
Forest rooms are cosy treehouse rooms; ocean rooms are a ship's cabin with portholes on to the sea."""
import math
import random

from .world_buildings import arch_door

IW, IH, WALL_TOP, FLOOR_Y = 240, 162, 8, 120


# ------------------------------------------------------------------ Enchanted Forest: a cosy treehouse room
def forest_room(c, wall, seam, trim, floor, floor2, rail=True):
    rnd = random.Random(8)
    c.rect(0, 0, IW, WALL_TOP, "a")
    for x in range(0, IW, 3):                                  # leafy ceiling edge
        c.px(x, WALL_TOP - 1 - (x % 2), "b"); c.px(x + 1, WALL_TOP - 2, "d")
    c.rect(0, WALL_TOP, IW, FLOOR_Y - WALL_TOP, "S")
    for x in range(0, IW, 9):                                  # wooden wall planks with grain
        c.rect(x, WALL_TOP, 1, FLOOR_Y - WALL_TOP, "g")
        for y in range(WALL_TOP + rnd.randint(2, 9), FLOOR_Y - 2, rnd.randint(9, 15)):
            c.rect(x + 2, y, rnd.randint(2, 4), 1, "g")
    for x in range(0, IW, 2):                                  # moss and vines along the top
        c.px(x, WALL_TOP, "u"); c.px(x, WALL_TOP + 1 + (x % 3 == 0), "e" if x % 5 == 0 else "u")
    for x in range(14, IW, 37):
        for y in range(WALL_TOP, WALL_TOP + 10 + (x % 11)):
            c.px(x + (y // 3) % 2, y, "e" if y % 3 else "E")
    if rail:
        c.rect(0, 84, IW, 1, "g"); c.rect(0, 85, IW, 1, "s")
    c.rect(0, FLOOR_Y - 3, IW, 3, "g"); c.rect(0, FLOOR_Y - 1, IW, 1, "k")
    for y in range(FLOOR_Y, IH):                               # floorboards, with a round rug
        band = (y - FLOOR_Y) // 6
        for x in range(IW):
            c.px(x, y, "s" if ((x + band * 7) // (22 + band * 3)) % 2 else "S")
        if (y - FLOOR_Y) % 6 == 5:
            c.rect(0, y, IW, 1, "g")
    c.disc(120, 146, 48, "P", 9); c.disc(120, 146, 40, "M", 6); c.disc(120, 146, 26, "m", 3)
    for x in (60, 120, 180):                                   # hanging lanterns instead of ceiling lamps
        c.rect(x, WALL_TOP, 1, 6, "k"); c.rect(x - 2, WALL_TOP + 6, 5, 6, "i"); c.rect(x - 1, WALL_TOP + 8, 3, 2, "y")
        c.rect(x - 3, WALL_TOP + 5, 7, 1, "g"); c.rect(x - 3, WALL_TOP + 12, 7, 1, "g")


def forest_door(c, lights):
    arch_door(c, 4, 88, 19, 32)
    c.rect(3, 87, 21, 1, "g")
    c.rect(11, 84, 5, 3, "i"); c.px(13, 85, "y")
    lights.append([11, 84, 5, 3, "i", 1700])


def forest_window(c, x, y, w, h, seed=3, planet=False, frame="S"):
    rnd = random.Random(seed)
    c.rect(x - 1, y - 1, w + 2, h + 2, "k")
    c.rect(x, y, w, h, "g")
    for yy in range(y + 2, y + h - 2):                          # the night forest outside
        for xx in range(x + 2, x + w - 2):
            c.px(xx, yy, "A" if (yy - y) < h * 0.4 else "F" if (yy - y) < h * 0.7 else "J")
    for _ in range(max(4, w // 5)):                             # tree silhouettes
        tx = rnd.randrange(x + 2, x + w - 3)
        top = rnd.randrange(y + h // 4, y + h - 4)
        c.rect(tx, top, 2, y + h - 2 - top, "h")
        c.disc(tx + 1, top, 3, "h")
    for _ in range(w * h // 45):
        c.px(rnd.randrange(x + 2, x + w - 2), rnd.randrange(y + 2, y + h - 2), rnd.choice("qqw"))
    if planet:
        c.disc(x + w * 2 // 3, y + h // 3, min(w, h) // 6, "t")
    c.rect(x + w // 2, y, 1, h, "g"); c.rect(x, y + h // 2, w, 1, "g")   # window cross
    for xx in range(x - 1, x + w + 1, 2):
        c.px(xx, y - 2, "e"); c.px(xx + 1, y - 1, "u")          # ivy over the frame


# ------------------------------------------------------------------ Ocean world: a ship's-cabin room
def ocean_room(c, wall, seam, trim, floor, floor2, rail=True):
    c.rect(0, 0, IW, WALL_TOP, "u")
    for x in range(0, IW, 24):
        c.rect(x, 0, 2, WALL_TOP, "g")                           # ceiling beams
    c.rect(0, WALL_TOP, IW, FLOOR_Y - WALL_TOP, "L")
    for y in range(WALL_TOP + 6, FLOOR_Y, 7):                    # painted horizontal planks
        c.rect(0, y, IW, 1, "K")
    for x in range(30, IW, 40):
        c.rect(x, WALL_TOP, 2, FLOOR_Y - WALL_TOP, "u")          # ribs of the hull
        for y in range(WALL_TOP + 4, FLOOR_Y, 12):
            c.px(x, y, "Y")                                      # brass rivets
    if rail:
        for x in range(0, IW, 2):                                # a rope rail
            c.px(x, 84 + (x // 2) % 2, "t"); c.px(x + 1, 85 - (x // 2) % 2, "o")
    c.rect(0, FLOOR_Y - 3, IW, 3, "u"); c.rect(0, FLOOR_Y - 1, IW, 1, "k")
    for y in range(FLOOR_Y, IH):                                 # deck boards
        for x in range(IW):
            c.px(x, y, "s" if ((x // 30 + (y - FLOOR_Y) // 6) % 2) else "S")
        if (y - FLOOR_Y) % 6 == 5:
            c.rect(0, y, IW, 1, "g")
    for x in (60, 120, 180):                                     # ship's lamps
        c.rect(x - 1, WALL_TOP, 3, 3, "Y"); c.rect(x - 3, WALL_TOP + 3, 7, 5, "Y"); c.rect(x - 2, WALL_TOP + 4, 5, 3, "y")


def ocean_door(c, lights):
    c.rect(3, 88, 21, 32, "k"); c.rect(4, 89, 19, 31, "u")
    for y in range(90, 120, 4):
        c.rect(5, y, 17, 1, "g")
    c.disc(13, 98, 5, "Y"); c.disc(13, 98, 4, "d"); c.px(12, 97, "i")      # a little porthole in the door
    c.rect(19, 104, 2, 3, "Y")
    c.rect(11, 85, 5, 2, "x")
    lights.append([11, 85, 5, 2, "x", 1600])


def ocean_window(c, x, y, w, h, seed=3, planet=False, frame="S"):
    rnd = random.Random(seed)
    r = min(w, h) // 2
    cx, cy = x + w // 2, y + h // 2
    c.disc(cx, cy, r + 1, "k"); c.disc(cx, cy, r, "Y"); c.disc(cx, cy, r - 2, "o")
    for yy in range(cy - r + 3, cy + r - 2):                    # under the sea
        for xx in range(cx - r + 3, cx + r - 2):
            if (xx - cx) ** 2 + (yy - cy) ** 2 <= (r - 3) ** 2:
                c.px(xx, yy, "d" if yy < cy - r // 3 else "b" if yy < cy + r // 3 else "a")
    for _ in range(max(2, r // 3)):                              # little fish
        fx, fy = rnd.randrange(cx - r + 5, cx + r - 6), rnd.randrange(cy - r + 5, cy + r - 5)
        col = rnd.choice("jYy")
        c.rect(fx, fy, 3, 2, col); c.px(fx - 1, fy, col); c.px(fx + 1, fy, "k")
    for _ in range(r):
        bx, by = rnd.randrange(cx - r + 4, cx + r - 4), rnd.randrange(cy - r + 4, cy + r - 4)
        if (bx - cx) ** 2 + (by - cy) ** 2 < (r - 4) ** 2:
            c.px(bx, by, "i")
    for xx in range(cx - r + 4, cx + r - 4, 3):                  # kelp at the bottom
        if (xx - cx) ** 2 < (r - 4) ** 2:
            c.px(xx, cy + r - 5, "v"); c.px(xx, cy + r - 6, "v")
    for a in range(0, 360, 45):                                  # bolts around the rim
        c.px(int(cx + (r - 1) * math.cos(math.radians(a))), int(cy + (r - 1) * math.sin(math.radians(a))), "y")


SKINS = {"forest": (forest_room, forest_door, forest_window), "ocean": (ocean_room, ocean_door, ocean_window)}
