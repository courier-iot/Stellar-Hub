"""Building interiors for Hub Connect S: when the resident walks into a building, the app follows it inside.

Every building has its own room, drawn here in the same 16-bit palette as the colony and served as JSON.
Each room lists 'spots' where the resident can stand (the easel, a painting on the wall, the bed...),
which action happens at which spot, and a few blinking lights. Live things are drawn from the colony's
real state: the paintings hung in the gallery, the plants in the greenhouse, the Home Dome showcase, etc.
"""
import hashlib
import json
import math
import random

from .sprites import Canvas, PALETTE

IW, IH = 240, 162      # room size in pixels (same shape as the phone's colony window)
WALL_TOP = 8           # ceiling ends here
FLOOR_Y = 120          # back wall meets the floor
BASE_Y = 128           # furniture stands on the floor here
FEET = 142             # the resident walks along this line
DOOR_X = 13            # the airlock everyone comes in through


# ---------------------------------------------------------------- room kit
def room(c, wall, seam, trim, floor, floor2, rail=True):
    c.rect(0, 0, IW, WALL_TOP, "k")
    c.rect(0, WALL_TOP - 1, IW, 1, trim)
    c.rect(0, WALL_TOP, IW, FLOOR_Y - WALL_TOP, wall)
    for x in range(30, IW, 40):                              # wall panel seams
        c.rect(x, WALL_TOP, 1, FLOOR_Y - WALL_TOP, seam)
    if rail:
        c.rect(0, 84, IW, 1, seam); c.rect(0, 85, IW, 1, trim)
    c.rect(0, FLOOR_Y - 3, IW, 3, trim); c.rect(0, FLOOR_Y - 1, IW, 1, "k")
    for y in range(FLOOR_Y, IH):                             # floor tiles, wider toward the front
        band = (y - FLOOR_Y) // 7
        for x in range(IW):
            w = 12 + band * 3
            c.px(x, y, floor if ((x + band * 5) // w + band) % 2 else floor2)
    for y in range(FLOOR_Y + 6, IH, 7):
        c.rect(0, y, IW, 1, floor2)
    for x in (60, 120, 180):                                 # ceiling lamps
        c.rect(x - 4, WALL_TOP, 9, 2, "S"); c.rect(x - 3, WALL_TOP + 2, 7, 1, "t")


def airlock(c, lights):
    c.rect(3, 88, 21, 32, "k")
    c.rect(4, 89, 19, 31, "S")
    c.rect(6, 91, 15, 29, "g")
    c.rect(13, 91, 1, 29, "k")                               # sliding seam
    c.rect(7, 104, 3, 1, "G"); c.rect(17, 104, 3, 1, "G")
    c.rect(11, 85, 5, 2, "e")
    lights.append([11, 85, 5, 2, "e", 1600])


def space_window(c, x, y, w, h, seed=3, planet=False, frame="S"):
    rnd = random.Random(seed)
    c.rect(x - 1, y - 1, w + 2, h + 2, "k")
    c.rect(x, y, w, h, frame)
    for yy in range(y + 2, y + h - 2):
        for xx in range(x + 2, x + w - 2):
            c.px(xx, yy, "A" if (yy - y) < h * 0.45 else "B" if (yy - y) < h * 0.75 else "D")
    for _ in range(w * h // 30):
        c.px(rnd.randrange(x + 2, x + w - 2), rnd.randrange(y + 2, y + h - 2), rnd.choice("wwsS"))
    if planet:
        cx, cy, r = x + w * 2 // 3, y + h // 2, min(w, h) // 4
        c.disc(cx, cy, r, "C"); c.disc(cx - 2, cy - 2, r - 2, "c")
        for xx in range(cx - r - 4, cx + r + 5):
            c.px(xx, cy + 1, "s")
    if w > 30:
        c.rect(x + w // 2, y, 1, h, frame)                   # window mullion


def put_art(c, rows, x, y, size):
    """Draws a painting scaled into a size x size box."""
    if not rows:
        return
    n = len(rows)
    for yy in range(size):
        for xx in range(size):
            ch = rows[yy * n // size][min(len(rows[0]) - 1, xx * n // size)]
            if ch != ".":
                c.px(x + xx, y + yy, ch)


def frame(c, x, y, size, rows=None, wood="o"):
    c.rect(x - 2, y - 2, size + 4, size + 4, "k")
    c.rect(x - 1, y - 1, size + 2, size + 2, wood)
    c.rect(x, y, size, size, "n")
    put_art(c, rows, x, y, size)


def table(c, x, w, top_y, col="o", shade="O"):
    c.rect(x, top_y, w, 3, col); c.rect(x, top_y + 3, w, 1, shade)
    c.rect(x + 1, top_y + 4, 2, BASE_Y - top_y - 4, shade)
    c.rect(x + w - 3, top_y + 4, 2, BASE_Y - top_y - 4, shade)


def screen(c, x, y, w, h, on=True, glow="c"):
    c.rect(x, y, w, h, "k")
    c.rect(x + 1, y + 1, w - 2, h - 2, glow if on else "n")
    if on:
        for yy in range(y + 2, y + h - 2, 2):
            c.rect(x + 2, yy, (w - 4) * ((yy * 7) % 5 + 2) // 7, 1, "C" if glow == "c" else "k")


def chair(c, x, col="g"):
    c.rect(x, BASE_Y - 9, 7, 2, col); c.rect(x + 5, BASE_Y - 16, 2, 7, col)
    c.rect(x + 1, BASE_Y - 7, 1, 7, "k"); c.rect(x + 5, BASE_Y - 7, 1, 7, "k")


def plant_pot(c, x, leaf, flower, stage, pot="O"):
    c.rect(x - 3, BASE_Y - 6, 7, 6, pot); c.rect(x - 3, BASE_Y - 6, 7, 1, "o")
    h = {"seed": 1, "sprout": 6, "young": 11, "mature": 17, "blooming": 19}.get(stage, 2)
    top = BASE_Y - 6 - h
    if stage == "wilted":
        c.rect(x, BASE_Y - 10, 1, 4, "O"); c.rect(x + 1, BASE_Y - 9, 3, 1, "O")
        return
    c.rect(x, top, 1, h, leaf)
    for j in range(2, h, 3):
        c.px(x - 1 - (j % 2), top + j, leaf); c.px(x + 1 + ((j + 1) % 2), top + j + 1, leaf)
    if stage == "blooming":
        c.px(x, top - 1, flower); c.px(x - 1, top, flower); c.px(x + 1, top, flower); c.px(x, top + 1, "y")


def icon(c, rows, x, y):
    for j, row in enumerate(rows or []):
        for i, ch in enumerate(row):
            if ch != ".":
                c.px(x + i, y + j, ch)


def sign_text(c, x, y, color, glyphs):
    """Tiny 3x5 block letters for signs like ON AIR."""
    font = {"O": ["###", "#.#", "#.#", "#.#", "###"], "N": ["#.#", "###", "###", "###", "#.#"],
            "A": [".#.", "#.#", "###", "#.#", "#.#"], "I": ["###", ".#.", ".#.", ".#.", "###"],
            "R": ["##.", "#.#", "##.", "#.#", "#.#"], "B": ["##.", "#.#", "##.", "#.#", "##."],
            "S": ["###", "#..", "###", "..#", "###"], "L": ["#..", "#..", "#..", "#..", "###"],
            "D": ["##.", "#.#", "#.#", "#.#", "##."], "E": ["###", "#..", "##.", "#..", "###"],
            "W": ["#.#", "#.#", "###", "###", "#.#"], "T": ["###", ".#.", ".#.", ".#.", ".#."],
            "C": ["###", "#..", "#..", "#..", "###"], "P": ["##.", "#.#", "##.", "#..", "#.."], "F": ["###", "#..", "##.", "#..", "#.."],
            "Y": ["#.#", "#.#", ".#.", ".#.", ".#."],
            " ": ["...", "...", "...", "...", "..."]}
    for ch in glyphs:
        for j, row in enumerate(font.get(ch, font[" "])):
            for i, v in enumerate(row):
                if v == "#":
                    c.px(x + i, y + j, color)
        x += 4


# ---------------------------------------------------------------- the rooms
# Each returns (spots, actions, idle). spots: {name: [x, top_y, fx]}; fx is the little effect shown there.

def r_home(c, d, L):
    room(c, "J", "I", "V", "O", "o")
    airlock(c, L)
    if d.get("floors", 1) > 1:                                  # ladder to the upper floors
        for y in range(WALL_TOP + 2, BASE_Y, 5):
            c.rect(27, y, 7, 1, "S")
        c.rect(27, WALL_TOP, 1, BASE_Y - WALL_TOP, "S"); c.rect(33, WALL_TOP, 1, BASE_Y - WALL_TOP, "S")
    # desk with journal and lamp
    table(c, 38, 30, 110)
    c.rect(44, 106, 9, 4, "t"); c.rect(48, 106, 1, 4, "S")
    c.rect(60, 98, 1, 12, "S"); c.rect(57, 96, 7, 3, "y")
    chair(c, 54, "M")
    # easel with the newest painting
    c.rect(78, 92, 1, 36, "O"); c.rect(90, 92, 1, 36, "O"); c.rect(84, 88, 1, 40, "o")
    frame(c, 76, 90, 16, d.get("latest"), "o")
    c.rect(75, 110, 18, 2, "o")
    # porthole with a telescope
    c.disc(120, 50, 22, "k"); c.disc(120, 50, 21, "V")
    space_window(c, 103, 33, 34, 34, seed=12, frame="V")
    c.rect(116, 96, 2, 32, "S"); c.rect(112, 126, 10, 2, "S")
    c.rect(110, 88, 14, 4, "s"); c.rect(108, 89, 2, 2, "c")
    # showcase cabinet: the first floor's 12 spots
    c.rect(142, 34, 50, 86, "k"); c.rect(143, 35, 48, 84, "M")
    spots_items = d.get("showcase", [])
    for i in range(12):
        col, row = i % 3, i // 3
        sx, sy = 145 + col * 15, 37 + row * 20
        c.rect(sx, sy, 14, 18, "h"); c.rect(sx, sy + 15, 14, 3, "m" if i < len(spots_items) and spots_items[i] else "P")
        it = spots_items[i] if i < len(spots_items) else None
        if it:
            if it.get("rows"):
                frame(c, sx + 2, sy + 2, 10, it["rows"], "y")
            else:
                icon(c, it.get("icon"), sx + 2, sy + 4)
    # bed
    c.rect(198, 110, 40, 12, "N"); c.rect(198, 108, 40, 4, "w"); c.rect(200, 105, 10, 5, "t")
    c.rect(198, 122, 2, 6, "O"); c.rect(236, 122, 2, 6, "O"); c.rect(198, 98, 3, 24, "O")
    c.rect(212, 109, 26, 3, "p")
    return ({"desk": [52, 96, "write"], "easel": [84, 88, "paint"], "window": [118, 86, "sparkle"],
             "showcase": [166, 34, "sparkle"], "bed": [218, 102, "zzz"]},
            {"journal": "desk", "update_personality": "desk", "build": "desk", "move_building": "desk",
             "upgrade_home": "desk", "set_bedtime": "bed", "rest": "bed", "sleep": "bed", "stargaze": "window",
             "paint": "easel", "showcase": "showcase", "remove_showcase": "showcase", "view_collection": "showcase"},
            ["desk", "window", "showcase", "easel"])


def r_library(c, d, L):
    room(c, "N", "n", "S", "g", "G")
    airlock(c, L)
    rnd = random.Random(4)
    for sx in (32, 150):                                      # tall bookshelves
        c.rect(sx, 20, 58, 108, "O"); c.rect(sx + 2, 22, 54, 104, "h")
        for shelf in range(5):
            y = 24 + shelf * 21
            x = sx + 3
            while x < sx + 54:
                w = rnd.randint(2, 4)
                h = rnd.randint(12, 17)
                c.rect(x, y + 18 - h, w, h, rnd.choice("rRcCeEyYpmMs"))
                x += w + (1 if rnd.random() < .3 else 0)
            c.rect(sx + 2, y + 18, 54, 2, "O")
    table(c, 98, 44, 108, "o", "O")                             # reading desk
    c.rect(104, 104, 14, 4, "t"); c.rect(110, 104, 1, 4, "S")
    c.rect(126, 96, 1, 12, "S"); c.rect(123, 94, 7, 3, "y")
    space_window(c, 214, 26, 22, 40, seed=21)
    c.rect(222, 84, 2, 44, "S"); c.rect(218, 126, 10, 2, "S"); c.rect(214, 78, 18, 5, "s"); c.rect(212, 79, 2, 3, "c")
    return ({"shelf_a": [60, 20, "sparkle"], "desk": [118, 94, "write"], "shelf_b": [178, 20, "sparkle"],
             "telescope": [224, 76, "sparkle"]},
            {"recall": "shelf_a", "write_note": "desk", "observe_sky": "telescope"},
            ["shelf_a", "shelf_b", "desk", "telescope"])


def r_cafe(c, d, L):
    room(c, "h", "F", "c", "k", "n")
    airlock(c, L)
    on = not d.get("storm")
    c.rect(32, 96, 40, 32, "N"); c.rect(32, 94, 40, 3, "c" if on else "C")        # counter
    c.rect(38, 72, 12, 22, "s"); c.rect(40, 76, 8, 6, "k"); c.rect(42, 84, 4, 4, "Y")   # drink machine
    c.rect(56, 88, 5, 6, "w"); c.rect(64, 89, 4, 5, "m")
    sign_text(c, 40, 30, "m" if on else "M", "CAFE")
    for i, tx in enumerate((84, 136, 188)):                     # terminal booths
        table(c, tx, 40, 108, "g", "G")
        screen(c, tx + 8, 82, 24, 18, on)
        c.rect(tx + 18, 100, 4, 8, "S")
        c.rect(tx + 10, 105, 20, 2, "S")
        chair(c, tx + 28, "N")
        if on:
            L.append([tx + 10, 84, 2, 2, "w", 700 + i * 230])
    return ({"counter": [52, 70, "sparkle"], "terminal_1": [104, 80, "type"], "terminal_2": [156, 80, "type"],
             "terminal_3": [208, 80, "type"]},
            {"research": "terminal_1", "read_page": "terminal_2"},
            ["counter", "terminal_3", "terminal_2"])


def r_post(c, d, L):
    room(c, "N", "g", "y", "U", "K")
    airlock(c, L)
    waiting = d.get("letters", 0)
    c.rect(32, 30, 60, 60, "k")                                 # mail slot wall
    for i in range(16):
        x, y = 34 + (i % 4) * 14, 32 + (i // 4) * 14
        c.rect(x, y, 13, 13, "S"); c.rect(x + 2, y + 5, 9, 2, "y" if i < waiting else "k")
    table(c, 100, 44, 108, "o", "O")
    c.rect(106, 103, 12, 5, "w"); c.rect(108, 104, 8, 1, "S"); c.rect(124, 100, 1, 8, "k"); c.rect(123, 99, 3, 1, "Y")
    c.rect(152, 34, 40, 34, "O"); c.rect(154, 36, 36, 30, "o")   # question board
    rnd = random.Random(8)
    for _ in range(6):
        x, y = rnd.randrange(156, 182), rnd.randrange(38, 58)
        c.rect(x, y, 7, 6, rnd.choice("twy")); c.px(x + 3, y, "r")
    c.rect(206, 20, 10, 108, "s"); c.rect(208, 20, 6, 108, "c")  # pneumatic tube
    c.rect(200, 92, 22, 14, "S"); c.rect(203, 95, 16, 8, "k")
    L.append([210, 24, 2, 100, "C", 2200])
    return ({"slots": [62, 28, "sparkle"], "desk": [122, 98, "write"], "board": [172, 32, "sparkle"],
             "tube": [211, 90, "sparkle"]},
            {"read_mail": "slots", "write_letter": "desk", "ask_question": "board", "send_request": "tube"},
            ["slots", "board", "desk"])


def r_salon(c, d, L):
    room(c, "M", "m", "p", "w", "k")
    airlock(c, L)
    c.rect(40, 30, 26, 90, "S"); c.rect(42, 32, 22, 86, "k")    # wardrobe with outfits
    for i, col in enumerate("cmypreY"):
        c.rect(44 + i * 3, 36, 2, 30 + (i % 3) * 6, col)
    c.rect(42, 34, 22, 1, "s")
    c.disc(116, 58, 20, "y", 26); c.disc(116, 58, 18, "s", 24)  # big mirror
    c.disc(110, 50, 4, "w", 8)
    c.rect(106, 104, 20, 4, "R"); c.rect(110, 90, 12, 14, "R"); c.rect(115, 108, 2, 16, "S"); c.rect(109, 124, 14, 4, "S")
    for i in range(5):                                          # vanity lights
        c.rect(92 + i * 12, 26, 3, 3, "t")
        L.append([92 + i * 12, 26, 3, 3, "w", 900 + i * 170])
    c.rect(160, 100, 40, 28, "h"); c.rect(160, 98, 40, 3, "m")  # colour samples counter
    for i, col in enumerate("cmypreYsG"):
        c.rect(163 + i * 4, 92, 3, 6, col)
    for x in (210, 224):                                        # mannequins
        c.disc(x, 70, 4, "s"); c.rect(x - 4, 76, 9, 22, "p" if x == 210 else "e"); c.rect(x, 98, 1, 26, "S")
        c.rect(x - 4, 124, 9, 2, "S")
    return ({"wardrobe": [52, 28, "sparkle"], "mirror": [116, 30, "sparkle"], "samples": [180, 90, "sparkle"],
             "mannequins": [217, 64, "sparkle"]},
            {"change_look": "mirror"},
            ["wardrobe", "samples", "mannequins", "mirror"])


def r_bank(c, d, L):
    room(c, "R", "M", "y", "k", "h")
    airlock(c, L)
    c.rect(32, 92, 66, 36, "M"); c.rect(32, 90, 66, 3, "y")     # teller counter
    c.rect(36, 60, 58, 30, "k")
    for x in range(36, 95, 6):
        c.rect(x, 60, 1, 30, "y")                               # teller bars
    screen(c, 54, 66, 20, 14, True, "y")
    c.disc(150, 68, 30, "S"); c.disc(150, 68, 27, "s"); c.disc(150, 68, 22, "S")   # vault door
    for a in range(8):
        x = 150 + int(math.cos(a * math.pi / 4) * 14); y = 68 + int(math.sin(a * math.pi / 4) * 14)
        c.rect(x - 1, y - 1, 3, 3, "k")
    c.disc(150, 68, 6, "y"); c.rect(149, 62, 2, 12, "Y")
    credits = d.get("credits", 0)
    piles = min(6, 1 + credits // 150) if credits else 0
    for i in range(piles):                                     # coin piles grow with the savings
        h = 4 + (credits // (60 * (i + 1))) % 12
        c.rect(122 + i * 10, BASE_Y - h, 7, h, "y")
        for y in range(BASE_Y - h, BASE_Y, 2):
            c.rect(122 + i * 10, y, 7, 1, "Y")
    c.rect(198, 64, 30, 64, "S"); c.rect(200, 66, 26, 60, "k")  # shop catalog kiosk
    screen(c, 202, 70, 22, 28, True, "e")
    c.rect(206, 104, 14, 4, "y")
    L.append([206, 104, 14, 4, "Y", 1300])
    return ({"teller": [64, 58, "sparkle"], "vault": [150, 38, "sparkle"], "kiosk": [212, 62, "type"]},
            {"check_balance": "teller", "buy": "kiosk"},
            ["teller", "vault", "kiosk"])


def r_workshop(c, d, L):
    room(c, "U", "L", "Y", "K", "U")
    airlock(c, L)
    for x in range(0, IW, 8):                                   # hazard stripes
        c.rect(x, WALL_TOP, 4, 3, "Y"); c.rect(x + 4, WALL_TOP, 4, 3, "k")
    table(c, 32, 56, 106, "S", "g")                             # workbench
    screen(c, 38, 82, 22, 18, True, "e")
    c.rect(64, 98, 8, 8, "Q"); c.rect(76, 100, 10, 6, "Y")
    c.rect(98, 40, 56, 88, "k"); c.rect(99, 41, 54, 86, "D")   # sandbox chamber
    c.rect(99, 41, 54, 1, "c"); c.rect(125, 41, 2, 30, "S"); c.rect(118, 70, 16, 4, "S"); c.rect(118, 74, 3, 6, "S")
    c.rect(131, 74, 3, 6, "S")
    c.rect(110, 112, 32, 14, "Q"); c.rect(110, 112, 32, 1, "s")
    L.append([102, 44, 3, 3, "c", 1100])
    n = max(1, min(18, d.get("programs", 0)))
    c.rect(170, 26, 58, 102, "h")                               # program server rack
    for i in range(18):
        x, y = 174 + (i % 3) * 18, 30 + (i // 3) * 16
        c.rect(x, y, 15, 12, "N"); c.rect(x + 2, y + 9, 11, 1, "g")
        if i < n:
            L.append([x + 2, y + 2, 2, 2, "e" if i % 2 else "c", 500 + i * 97])
    return ({"bench": [60, 80, "type"], "chamber": [126, 38, "sparkle"], "rack": [199, 24, "type"]},
            {"write_program": "bench", "list_programs": "rack"},
            ["bench", "chamber", "rack"])


def r_greenhouse(c, d, L):
    room(c, "n", "C", "C", "E", "O", rail=False)
    for x in range(0, IW, 20):                                  # glass panes on to the stars
        c.rect(x, WALL_TOP, 1, FLOOR_Y - WALL_TOP, "C")
    rnd = random.Random(5)
    for _ in range(90):
        c.px(rnd.randrange(IW), rnd.randrange(WALL_TOP, 80), rnd.choice("wsS"))
    c.rect(0, 40, IW, 1, "C")
    airlock(c, L)
    light = d.get("light", "normal")
    lamp = {"bright": "t", "dim": "Y", "off": "g"}.get(light, "y")
    for x in range(50, 230, 30):                               # grow lamps
        c.rect(x, WALL_TOP + 6, 20, 2, "S"); c.rect(x + 2, WALL_TOP + 8, 16, 1, lamp)
    c.rect(30, 70, 14, 58, "O"); c.rect(31, 72, 12, 54, "o")    # seed shelf
    for i in range(6):
        c.rect(33 + (i % 2) * 5, 76 + (i // 2) * 16, 4, 6, rnd.choice("tYyw"))
    c.rect(50, 116, 160, 12, "O"); c.rect(50, 114, 160, 3, "o") # planter bench
    plants = d.get("plants", [])[:12]
    for i, (leaf, flower, stage) in enumerate(plants):
        x = 58 + i * 13
        c.rect(x - 4, 110, 9, 4, "O")
        plant_pot(c, x, leaf, flower, stage, "O")
    c.rect(216, 84, 10, 16, "S"); c.rect(218, 86, 6, 6, lamp if light != "off" else "k")   # lamp switch
    c.rect(214, 108, 22, 20, "O"); c.rect(214, 106, 22, 3, "o"); c.rect(218, 102, 14, 4, "E")  # feed + compost
    return ({"seeds": [37, 68, "sparkle"], "planters": [130, 92, "drops"], "planters_left": [80, 92, "sparkle"],
             "planters_right": [180, 92, "sparkle"], "switch": [221, 82, "sparkle"], "compost": [225, 100, "sparkle"]},
            {"plant": "seeds", "water": "planters", "check_plants": "planters_left", "set_light": "switch",
             "feed": "compost", "remove": "compost"},
            ["planters_left", "planters", "planters_right"])


def r_radio(c, d, L):
    room(c, "N", "M", "r", "h", "n")
    for y in range(14, 80, 8):                                  # acoustic foam
        for x in range(32, IW, 8):
            c.rect(x + (y // 8 % 2) * 4, y, 3, 3, "F")
    airlock(c, L)
    rnd = random.Random(6)
    c.rect(32, 70, 50, 58, "O")                                 # record shelf
    for shelf in range(3):
        y = 72 + shelf * 18
        for x in range(34, 80, 3):
            c.rect(x, y + 2, 2, 14, rnd.choice("kkhRMPC"))
        c.rect(32, y + 16, 50, 2, "o")
    playing = d.get("playing")
    table(c, 92, 50, 106, "g", "G")                             # turntable desk
    c.disc(108, 103, 9, "k", 3); c.disc(108, 103, 3, "r" if playing else "R", 1)
    c.rect(122, 98, 1, 6, "s"); c.rect(122, 98, 8, 1, "s")
    c.rect(130, 100, 8, 4, "S")
    if playing:
        L.append([100, 102, 2, 1, "w", 300])
    sign_text(c, 166, 30, "r" if playing else "R", "ON AIR")
    if playing:
        L.append([164, 28, 26, 1, "r", 800])
    table(c, 156, 42, 106, "o", "O")                            # broadcast desk with mic
    c.rect(176, 90, 2, 16, "S"); c.disc(177, 88, 3, "S", 4); c.rect(170, 104, 14, 2, "S")
    for x in (206, 226):                                        # speakers
        c.rect(x, 80, 12, 48, "k"); c.disc(x + 6, 92, 4, "g"); c.disc(x + 6, 112, 5, "g"); c.disc(x + 6, 112, 2, "k")
    return ({"records": [56, 68, "sparkle"], "turntable": [112, 96, "notes"], "mic": [177, 84, "notes"],
             "speakers": [220, 78, "notes"]},
            {"list_music": "records", "play_music": "turntable", "stop_music": "turntable", "broadcast_log": "mic",
             "list_phone_music": "records", "play_phone_music": "turntable"},
            ["records", "speakers", "turntable"])


def r_studio(c, d, L):
    room(c, "P", "M", "m", "h", "N")
    for y in range(14, 80, 10):
        for x in range(34, IW, 10):
            c.rect(x, y, 6, 6, "V")
    airlock(c, L)
    n = min(8, d.get("compositions", 0))
    for i in range(8):                                          # one gold disc per song it wrote
        x, y = 40 + i * 24, 22
        c.disc(x + 8, y + 8, 8, "y" if i < n else "M"); c.disc(x + 8, y + 8, 2, "k")
    c.rect(36, 96, 84, 10, "k"); c.rect(38, 98, 80, 6, "w")    # synth keyboard
    for x in range(40, 118, 4):
        c.rect(x, 98, 1, 6, "S")
        if x % 8 == 0:
            c.rect(x + 1, 98, 2, 3, "k")
    c.rect(40, 90, 76, 6, "N")
    for i in range(6):
        c.rect(44 + i * 12, 91, 3, 3, "cmyerp"[i])
        L.append([44 + i * 12, 91, 3, 3, "w", 600 + i * 140])
    c.rect(44, 106, 2, 22, "S"); c.rect(110, 106, 2, 22, "S")
    table(c, 140, 60, 104, "g", "G")                            # mixing desk
    for x in range(144, 196, 5):
        c.rect(x, 96, 2, 8, "S"); c.rect(x, 98 + (x * 3) % 5, 2, 2, "c")
    for x in (204, 222):
        c.rect(x, 74, 14, 30, "k"); c.disc(x + 7, 84, 4, "g"); c.disc(x + 7, 96, 5, "g")
        c.rect(x + 5, 104, 4, 24, "S")
    return ({"keyboard": [78, 88, "notes"], "mixer": [170, 94, "notes"], "discs": [130, 20, "sparkle"]},
            {"compose": "keyboard", "play_composition": "mixer"},
            ["discs", "keyboard", "mixer"])


def r_archive(c, d, L):
    room(c, "n", "N", "c", "k", "h")
    airlock(c, L)
    n = max(3, min(60, d.get("chapters", 0) * 4 + d.get("memories", 0) // 20))
    for col in range(3):                                        # data cube stacks
        sx = 34 + col * 46
        c.rect(sx, 22, 40, 106, "U"); c.rect(sx + 2, 24, 36, 102, "k")
        for i in range(20):
            x, y = sx + 4 + (i % 4) * 9, 26 + (i // 4) * 20
            idx = col * 20 + i
            c.rect(x, y, 7, 7, "C" if idx < n else "N")
            if idx < n and idx % 5 == 0:
                L.append([x + 2, y + 2, 3, 3, "c", 900 + idx * 53])
    c.rect(180, 96, 36, 6, "S"); c.rect(186, 80, 6, 16, "S"); c.rect(182, 102, 4, 26, "S"); c.rect(210, 102, 4, 26, "S")
    c.disc(198, 56, 16, "c", 3)                                 # reading holo
    for y in range(58, 90, 3):
        c.rect(190, y, 16, 1, "C")
    L.append([190, 56, 16, 2, "w", 1400])
    return ({"cubes": [80, 20, "sparkle"], "reader": [198, 52, "sparkle"], "cubes_far": [146, 20, "sparkle"]},
            {"archive_memories": "cubes", "read_chapter": "reader"},
            ["cubes", "cubes_far", "reader"])


def r_spaceport(c, d, L):
    room(c, "L", "Q", "Y", "K", "U")
    airlock(c, L)
    for x in range(30, IW, 10):
        c.rect(x, FLOOR_Y + 2, 5, 2, "Y")
    table(c, 32, 50, 104, "S", "g")                             # mission console
    screen(c, 36, 76, 20, 16, True, "e"); screen(c, 58, 76, 20, 16, True, "c")
    L.append([40, 80, 2, 2, "w", 650])
    c.rect(96, 16, 80, 112, "U"); c.rect(98, 18, 76, 108, "h")  # launch bay
    if not d.get("away"):
        c.disc(136, 40, 10, "w", 18); c.rect(126, 40, 21, 60, "w")   # the rocket
        c.rect(126, 40, 21, 60, "s"); c.rect(128, 40, 4, 60, "w")
        c.disc(136, 56, 4, "c"); c.px(134, 54, "w")
        c.rect(118, 88, 8, 14, "r"); c.rect(147, 88, 8, 14, "r")
        c.rect(130, 100, 13, 6, "S"); c.rect(132, 106, 9, 4, "Y")
    else:
        sign_text(c, 116, 64, "y", "AWAY")
    for y in range(20, 126, 12):
        c.rect(98, y, 4, 2, "Y"); c.rect(170, y, 4, 2, "Y")
    space_window(c, 190, 24, 44, 44, seed=31, planet=True)
    return ({"console": [56, 74, "type"], "rocket": [136, 30, "sparkle"], "window": [212, 70, "sparkle"]},
            {"start_expedition": "rocket", "read_reports": "console"},
            ["console", "window", "rocket"])


def r_station(c, d, L):
    room(c, "s", "S", "c", "S", "g")
    airlock(c, L)
    c.rect(40, 16, 160, 66, "k")                                # the big window down to the colony moon
    space_window(c, 41, 17, 158, 64, seed=41, frame="S")
    for x in range(43, 197):                                    # the colony moon's curve, far below
        top = int(60 + ((x - 120) / 80) ** 2 * 20)
        for y in range(top, 79):
            c.px(x, y, "L" if y == top else "K" if (x + y) % 7 else "U")
    for x in range(84, 160, 6):                                 # the colony's lights
        c.px(x, int(60 + ((x - 120) / 80) ** 2 * 20) + 3, "y")
        L.append([x, int(60 + ((x - 120) / 80) ** 2 * 20) + 3, 1, 1, "t", 1200 + x * 13])
    table(c, 72, 40, 106, "S", "g")                             # study console
    screen(c, 78, 86, 28, 18, True, "c")
    c.disc(170, 98, 12, "c", 3)                                 # quiz holo
    for y in range(94, 120, 3):
        c.rect(162, y, 16, 1, "C")
    L.append([162, 96, 16, 2, "w", 1000])
    c.rect(212, 60, 20, 68, "S"); c.rect(214, 62, 16, 64, "g")  # sleep pod
    c.disc(222, 70, 5, "c")
    return ({"console": [92, 84, "type"], "holo": [170, 90, "sparkle"], "pod": [222, 58, "sparkle"]},
            {"station_study": "console"},
            ["console", "holo", "pod"])


def r_gallery(c, d, L):
    room(c, "s", "S", "w", "o", "O")
    airlock(c, L)
    hung = d.get("hung", [])[:12]
    art = []
    for i in range(12):                                         # two rows of frames, filled with real paintings
        col, row = i % 6, i // 6
        x, y = 36 + col * 28, 22 + row * 38
        rows = hung[i]["rows"] if i < len(hung) else None
        if rows is None:
            c.rect(x - 1, y - 1, 18, 18, "S"); c.rect(x, y, 16, 16, "s")
        else:
            frame(c, x, y, 16, rows, "y" if i == 0 else "o")
            c.rect(x + 6, y + 19, 4, 1, "S")                    # little title plaque
            art.append((i, x + 8))
        c.rect(x + 4, WALL_TOP + 1, 8, 1, "t")                  # picture light
    spots = {}
    for i, x in art:
        spots[f"art_{i + 1}"] = [x, 20, "sparkle"]
    if not spots:
        spots["wall"] = [104, 20, "sparkle"]
    c.rect(78, 110, 40, 4, "O"); c.rect(80, 114, 2, 14, "O"); c.rect(114, 114, 2, 14, "O")   # bench
    c.rect(200, 72, 1, 56, "O"); c.rect(222, 72, 1, 56, "O"); c.rect(211, 66, 1, 62, "o")      # easel
    frame(c, 203, 70, 16, d.get("latest"), "o")
    c.rect(199, 92, 25, 2, "o")
    c.rect(226, 112, 10, 16, "S"); c.rect(227, 108, 2, 4, "r"); c.rect(230, 106, 2, 6, "c"); c.rect(233, 108, 2, 4, "y")
    spots["easel"] = [211, 66, "paint"]
    newest = f"art_{len(hung)}" if hung else "easel"
    return (spots,
            {"paint": "easel", "hang_painting": newest if newest in spots else "easel"},
            [k for k in spots if k.startswith("art_")] or ["wall", "easel"])


def r_park(c, d, L):
    rnd = random.Random(9)
    for y in range(0, FLOOR_Y):                                 # open sky under the dome
        for x in range(IW):
            c.px(x, y, "A" if y < 40 else "B" if y < 80 else "D")
    for _ in range(140):
        c.px(rnd.randrange(IW), rnd.randrange(0, 100), rnd.choice("wwsS"))
    for x in range(IW):                                         # dome glass arc
        y = int(6 + ((x - 120) / 120) ** 2 * 30)
        c.px(x, y, "C")
    c.disc(196, 30, 10, "s"); c.disc(193, 27, 8, "w")
    for y in range(FLOOR_Y, IH):
        for x in range(IW):
            c.px(x, y, "E" if (x * 3 + y * 7) % 11 else "e")
    c.rect(0, FLOOR_Y, IW, 1, "e")
    for y in range(FLOOR_Y + 4, IH, 6):
        for x in range(rnd.randrange(3), IW, 7):
            c.px(x, y, "e")
    c.rect(2, 88, 22, 32, "S"); c.rect(4, 90, 18, 30, "g"); c.rect(12, 90, 1, 30, "k"); c.rect(11, 85, 5, 2, "e")
    L.append([11, 85, 5, 2, "e", 1600])
    for tx, h, r in ((40, 64, 18), (226, 56, 15)):              # trees
        c.rect(tx - 2, BASE_Y - h + r, 5, h - r, "o")
        c.disc(tx, BASE_Y - h + r, r, "E"); c.disc(tx - 3, BASE_Y - h + r - 3, r - 5, "e")
    c.rect(70, 112, 36, 4, "o"); c.rect(70, 104, 36, 3, "O")    # bench
    c.rect(72, 116, 2, 12, "O"); c.rect(102, 116, 2, 12, "O")
    table(c, 124, 28, 110, "s", "S")                            # chess / puzzle table
    for x in range(126, 150, 3):
        c.rect(x, 108, 3, 2, "w" if (x // 3) % 2 else "k")
    c.disc(186, 118, 16, "S", 6); c.disc(186, 117, 14, "c", 4)  # fountain
    c.rect(185, 92, 2, 24, "c"); c.rect(181, 90, 10, 2, "w")
    L.append([185, 92, 2, 24, "w", 450])
    for i in range(10):
        x = 150 + rnd.randrange(0, 20) if i < 5 else 60 + rnd.randrange(0, 50)
        c.px(x, 124 + rnd.randrange(3), rnd.choice("mypr"))
    return ({"bench": [88, 100, "write"], "table": [138, 104, "sparkle"], "fountain": [186, 88, "drops"],
             "tree": [44, 70, "sparkle"]},
            {"write": "bench", "relax": "bench", "solve_puzzle": "table"},
            ["bench", "fountain", "tree", "table"])


def r_exchange(c, d, L):
    room(c, "R", "h", "y", "k", "R")
    airlock(c, L)
    c.rect(32, 92, 50, 36, "M"); c.rect(32, 90, 50, 3, "y")    # sell counter
    c.rect(48, 80, 16, 10, "S"); c.rect(50, 82, 12, 6, "y")
    c.rect(94, 74, 30, 54, "O"); c.rect(96, 76, 26, 50, "o")    # auction podium
    c.rect(90, 72, 38, 4, "y")
    c.rect(118, 66, 8, 4, "O"); c.rect(121, 70, 2, 4, "O")      # gavel
    c.rect(136, 22, 50, 30, "O"); c.rect(138, 24, 46, 26, "t")  # wanted board
    rnd = random.Random(10)
    for _ in range(5):
        c.rect(rnd.randrange(140, 176), rnd.randrange(26, 44), 6, 4, rnd.choice("rcey"))
    for i in range(4):                                         # display cases with its real curios
        x = 136 + (i % 2) * 26
        y = 70 if i < 2 else 98
        c.rect(x, y, 22, 22, "k"); c.rect(x + 1, y + 1, 20, 20, "D"); c.rect(x + 1, y + 1, 20, 1, "c")
        items = d.get("curios", [])
        if i < len(items):
            icon(c, items[i], x + 6, y + 6)
    c.rect(198, 56, 36, 72, "S"); c.rect(200, 58, 32, 40, "k")  # trade-up machine
    c.disc(216, 76, 10, "M"); c.disc(216, 76, 6, "m"); c.rect(204, 104, 24, 10, "Y")
    L.append([212, 72, 8, 8, "p", 750])
    return ({"counter": [57, 78, "sparkle"], "podium": [109, 64, "sparkle"], "board": [161, 20, "sparkle"],
             "cases": [158, 64, "sparkle"], "machine": [216, 54, "sparkle"]},
            {"sell_curio": "counter", "auction_curio": "podium", "check_exchange": "board", "trade_up": "machine"},
            ["cases", "board", "counter"])


ROOMS = {"home": (r_home, "Home Dome"), "library": (r_library, "Library"), "internet_cafe": (r_cafe, "Uplink Café"),
         "post_office": (r_post, "Relay Post"), "salon": (r_salon, "Salon"), "bank": (r_bank, "Credit Vault"),
         "workshop": (r_workshop, "Fab Hangar"), "greenhouse": (r_greenhouse, "Greenhouse"),
         "radio_tower": (r_radio, "Radio Tower"), "studio": (r_studio, "Radio Studio"),
         "archive": (r_archive, "Archive Vault"), "spaceport": (r_spaceport, "Spaceport"),
         "station": (r_station, "Orbital Station"), "gallery": (r_gallery, "Gallery"), "park": (r_park, "Park"),
         "exchange": (r_exchange, "Exchange")}


def interior_version(bid, data):
    return hashlib.md5(json.dumps([bid, data, 3], sort_keys=True, default=str).encode()).hexdigest()[:10]


def interior(bid, data, resident_palette=None):
    """The room for one building. data: the live details that room shows (see Agent.interior_data)."""
    if bid not in ROOMS:
        return None
    fn, name = ROOMS[bid]
    c = Canvas(IW, IH, "k")
    lights = []
    spots, actions, idle = fn(c, data or {}, lights)
    pal = dict(PALETTE)
    pal.update(resident_palette or {})
    return {"id": bid, "name": name, "w": IW, "h": IH, "feet_y": FEET, "door_x": DOOR_X,
            "palette": pal, "background": c.rows(),
            "spots": {k: {"x": v[0], "top": v[1], "fx": v[2]} for k, v in spots.items()},
            "actions": actions, "idle": [s for s in idle if s in spots], "lights": lights,
            "version": interior_version(bid, data)}
