"""The 128 collectible curios: 8 kinds x 16 each, with rarity and a tiny generated pixel icon."""
import hashlib
import random

KINDS = {
    "meteorite": ["Pitted Iron Chunk", "Sooty Pebble", "Glassy Tektite", "Rusty Nodule", "Twin-Lobed Rock",
                  "Ringing Stone", "Chondrite Bead", "Cratered Shard", "Pallasite Slice", "Fusion-Crust Knob",
                  "Shocked Quartz Lump", "Starfall Ember", "Widmanstätten Plate", "Comet Heart",
                  "Singing Siderite", "Fragment of the First Star"],
    "crystal": ["Frosted Quartz", "Rose Shard", "Smoky Point", "Citrine Chip", "Lilac Cluster", "Moonstone Drop",
                "Ice Prism", "Teal Geode", "Glowing Fluorite", "Bismuth Staircase", "Aurora Opal", "Void Garnet",
                "Plasma Ruby", "Nebula Sapphire", "Time-Locked Diamond", "The Heartlight Crystal"],
    "shell": ["Spiral Snail Shell", "Ribbed Clam", "Tiny Cowrie", "Pearl Button Shell", "Sand Dollar",
              "Tidepool Whorl", "Ghost Conch", "Moonlit Nautilus", "Silver Scallop", "Pink Murex",
              "Starfish Fossil", "Echo Shell", "Abyssal Spindle", "Rainbow Abalone", "Singing Nautilus",
              "Shell of the Ocean Moon"],
    "fossil": ["Fern Imprint", "Trilobite Tail", "Ammonite Coil", "Fossil Leaf", "Tiny Tooth", "Coral Fragment",
               "Raptor Claw", "Crinoid Stem", "Amber Bug", "Fish in Stone", "Feathered Imprint",
               "Mammoth Hair in Ice", "Glowing Spore Fossil", "Martian Microbe Mat", "Alien Fern Fossil",
               "The First Footprint"],
    "earth_relic": ["Bottle Cap", "Marble", "Brass Key", "Old Coin", "Cassette Tape", "Tin Robot",
                    "Pocket Compass", "Snow Globe", "Floppy Disk", "Paper Crane", "Vinyl Single", "Wind-Up Bird",
                    "Golden Pocket Watch", "Moon Landing Patch", "Golden Record Replica", "Postcard from Earth"],
    "gadget": ["Blinking Diode", "Pocket Gyro", "Bent Antenna", "Spare Servo", "Solar Cell Chip",
               "Mini Thruster", "Holo Locket", "Quantum Dice", "Gravity Marble", "Plasma Lighter",
               "Pocket Star Map", "Self-Folding Kite", "Thinking Cube", "Time Crystal Clock",
               "Wormhole Keychain", "The Last Working Probe"],
    "seed_pod": ["Dry Husk", "Puffball Pod", "Winged Seed", "Spiky Burr", "Glass Bean", "Humming Acorn",
                 "Twin Pod", "Glowseed", "Frost Pine Cone", "Orbiting Seedling", "Lantern Pod",
                 "Starbloom Bulb", "Moonvine Seed", "Crystal Acorn", "Dream Pod", "Seed of the World Tree"],
    "alien_artifact": ["Smooth Tile", "Humming Disc", "Folded Metal", "Etched Plate", "Glowing Bead",
                       "Spiral Rod", "Floating Ring", "Warm Cube", "Map Fragment", "Speaking Shell",
                       "Light-Bending Lens", "Song Stone", "Star Key", "Mind Mirror", "Gate Shard",
                       "The Message"],
}
RARITY = ["common"] * 8 + ["uncommon"] * 4 + ["rare"] * 3 + ["legendary"]
RARITY_WEIGHT = {"common": 60, "uncommon": 25, "rare": 12, "legendary": 3}
KIND_COLORS = {
    "meteorite": ("S", "K", "Y"), "crystal": ("c", "p", "m"), "shell": ("w", "t", "m"), "fossil": ("o", "O", "t"),
    "earth_relic": ("y", "r", "C"), "gadget": ("s", "c", "r"), "seed_pod": ("e", "E", "y"),
    "alien_artifact": ("p", "c", "e"),
}


def catalog():
    out = {}
    for kind, names in KINDS.items():
        for i, n in enumerate(names):
            cid = f"{kind}_{i + 1:02d}"
            out[cid] = {"id": cid, "kind": kind, "name": n, "rarity": RARITY[i]}
    return out


CATALOG = catalog()


def _shape(kind, rnd):
    """10x10 mask for the kind, with a little random variation per item."""
    g = [["." for _ in range(10)] for _ in range(10)]

    def put(x, y, c="1"):
        if 0 <= x < 10 and 0 <= y < 10:
            g[y][x] = c
    if kind in ("meteorite", "fossil", "seed_pod"):
        cx, cy, rx, ry = 4.5 + rnd.uniform(-.5, .5), 5 + rnd.uniform(-.5, .5), rnd.uniform(3, 4.4), rnd.uniform(2.6, 4)
        for y in range(10):
            for x in range(10):
                d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if d <= 1 - rnd.uniform(0, .15):
                    put(x, y, "1" if d < .45 else "2")
    elif kind == "crystal":
        for k in range(rnd.randint(2, 3)):
            x0, h = rnd.randint(2, 6), rnd.randint(5, 8)
            for y in range(9 - h, 9):
                w = 1 if y < 9 - h + 2 else 2
                for x in range(x0 - w + 1, x0 + w):
                    put(x, y, "1" if x <= x0 else "2")
    elif kind == "shell":
        for y in range(10):
            for x in range(10):
                d = ((x - 4.5) ** 2 + (y - 5) ** 2) ** .5
                if d < 4.3 and (int(d * 1.6) + (x > 4)) % 2 == 0:
                    put(x, y, "1")
                elif d < 4.3:
                    put(x, y, "2")
    elif kind == "earth_relic":
        if rnd.random() < .5:
            for y in range(2, 9):
                for x in range(1, 9):
                    put(x, y, "1" if 2 < y < 7 else "2")
        else:
            for y in range(10):
                for x in range(10):
                    if (x - 4.5) ** 2 + (y - 4.5) ** 2 < 14:
                        put(x, y, "1" if (x + y) % 3 else "2")
    elif kind == "gadget":
        for y in range(3, 9):
            for x in range(2, 8):
                put(x, y, "2")
        for y in range(4, 8):
            for x in range(3, 7):
                put(x, y, "1")
        put(rnd.randint(3, 6), 1); put(rnd.randint(3, 6), 2)
    else:  # alien artifact: symmetric glyph
        for y in range(1, 9):
            for x in range(1, 5):
                if rnd.random() < .55:
                    put(x, y, "1" if rnd.random() < .7 else "2")
                    put(9 - x, y, g[y][x])
    # sparkle / detail in the accent colour
    for _ in range(2):
        x, y = rnd.randint(2, 7), rnd.randint(2, 7)
        if g[y][x] != ".":
            g[y][x] = "3"
    # outline
    out = [row[:] for row in g]
    for y in range(10):
        for x in range(10):
            if g[y][x] == "." and any(0 <= x + dx < 10 and 0 <= y + dy < 10 and g[y + dy][x + dx] != "."
                                      for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[y][x] = "k"
    return out


def sprite(cid):
    item = CATALOG[cid]
    rnd = random.Random(int(hashlib.md5(cid.encode()).hexdigest()[:8], 16))
    a, b, accent = KIND_COLORS[item["kind"]]
    if item["rarity"] in ("rare", "legendary"):
        accent = "y" if item["rarity"] == "legendary" else "m"
    grid = _shape(item["kind"], rnd)
    m = {"1": a, "2": b, "3": accent}
    return ["".join(m.get(ch, ch) for ch in row) for row in grid]


def random_find(rnd=random, boost=0):
    """Picks a curio by rarity. boost (0-3) shifts the odds toward rarer finds."""
    weights = dict(RARITY_WEIGHT)
    weights["rare"] += boost * 6
    weights["legendary"] += boost * 2
    rarity = rnd.choices(list(weights), list(weights.values()))[0]
    pool = [c for c in CATALOG.values() if c["rarity"] == rarity]
    return rnd.choice(pool)["id"]
