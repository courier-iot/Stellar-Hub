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


DESCRIPTIONS = {
    "meteorite": [
        "A heavy little lump of iron, pitted from its fall.", "A dull grey pebble with a burnt black crust.",
        "A drop of natural glass flung out by an ancient impact.", "Orange rust patches show the iron hiding inside.",
        "Two blobs fused together on the way down.", "Tap it and it rings softly, like a small bell.",
        "A tiny round bead from the very birth of the solar system.", "A shard with its own miniature craters.",
        "Gold-green crystals set in shining metal, like stained glass.", "Its glossy crust melted and set during entry.",
        "Quartz scarred with fine lines by an impact's shock wave.", "Still faintly warm, no matter how long it sits.",
        "Polished, it shows a crisscross pattern only found in space metal.", "Said to be the frozen core of a comet.",
        "Hums a single low note when held up to the stars.", "Older than every star in the sky, or so the legends say.",
    ],
    "crystal": [
        "A cloudy white point, cold to the touch.", "A soft pink shard that blushes in the light.",
        "A brown, smoky point that seems to hold a little haze.", "A sunny yellow chip that brightens any shelf.",
        "A small spray of lilac points growing from one base.", "A milky drop with a blue sheen that drifts as you turn it.",
        "Clear as ice, it splits light into tiny rainbows.", "Cracked open, it reveals a teal cave of crystals inside.",
        "Glows green under the colony's night lights.", "Metal stairs in rainbow colours, grown in neat squares.",
        "Flashes of every aurora colour swim inside.", "So dark red it looks black, until light hits it.",
        "A red crystal that crackles faintly with stored energy.", "Deep blue, with a swirl like a tiny galaxy inside.",
        "Light that enters seems to come out a moment late.", "Warm and softly beating, like a heart made of light.",
    ],
    "shell": [
        "A simple spiral, perfectly coiled.", "A sturdy clam shell with neat ridges.", "Small, glossy and smooth as a pebble.",
        "Pale and round, with a soft pearly shine.", "A flat white disc with a five-petal flower pattern.",
        "A little whorl found where water once pooled.", "So thin and pale it's almost see-through.",
        "Its chambers shimmer silver in moonlight.", "A fan-shaped shell with a silver sheen.",
        "A pink, spiky spiral, prettier than it is comfortable.", "A starfish turned to stone long ago.",
        "Hold it to your ear and you hear your own voice, faintly, a second later.", "A long, needle-thin spiral from very deep water.",
        "Its inside shifts through every colour as you turn it.", "Whistles a tune when the air vents blow across it.",
        "A shell from a sea on a moon that no longer has one.",
    ],
    "fossil": [
        "The delicate outline of an ancient fern pressed into stone.", "The tail of a trilobite, one of Earth's first hunters.",
        "A spiral sea creature turned to stone.", "A leaf caught forever mid-fall.", "A tiny pointed tooth from something long gone.",
        "A branching piece of coral from an ancient reef.", "A curved claw from a small, fast dinosaur.",
        "A stack of stone discs from an ancient sea lily.", "A small insect frozen in golden amber.",
        "A whole small fish, every bone kept in stone.", "The outline of feathers in fine grey rock.",
        "A tuft of mammoth hair, still frozen in ancient ice.", "Spores that still glow faintly after a million years.",
        "Layers of microbial life from a wetter, warmer Mars.", "A fern from a world no one has ever named.",
        "A single footprint pressed into rock. No one knows whose.",
    ],
    "earth_relic": [
        "A bent metal bottle cap from some long-ago drink.", "A glass marble with a twist of colour inside.",
        "An old brass key. Whatever it opened is long gone.", "A worn coin from a country that no longer exists.",
        "A cassette tape, its label too faded to read.", "A little tin robot that still walks when wound.",
        "Its needle still finds a north that's very far away.", "A tiny snowy town in a glass dome.",
        "A square of plastic that once held a whole program.", "A small paper bird, folded with great care.",
        "A single record. One song on each side.", "Wind it up and it hops and chirps.",
        "A gold watch that still ticks perfectly.", "A cloth patch from humanity's first steps on the Moon.",
        "A copy of the golden record sent out to the stars.", "A postcard of a blue sky, with a message too faded to read.",
    ],
    "gadget": [
        "A little light that still blinks on its own.", "A tiny gyroscope that spins for hours.",
        "A bent antenna that sometimes picks up static from far away.", "A spare motor from some long-retired robot.",
        "A solar chip that charges in starlight.", "A thumb-sized thruster, out of fuel.",
        "A locket that projects a hologram of a forgotten face.", "Dice that never land the same way twice.",
        "A marble that rolls slightly uphill.", "A lighter that makes a tiny ball of plasma instead of a flame.",
        "A pocket device showing the sky from anywhere.", "A kite that folds and unfolds itself.",
        "A cube that seems to rearrange itself when no one is looking.", "A clock powered by a crystal that ticks through time itself.",
        "A keychain with a tiny swirling portal. Probably harmless.", "The last working piece of a probe sent out long ago.",
    ],
    "seed_pod": [
        "An empty, papery husk that rattles.", "A puffball that bursts into a cloud of spores.",
        "A seed with a single wing for spinning down.", "A spiky burr that sticks to everything.",
        "A bean as clear as glass.", "An acorn that hums very quietly.", "Two seeds sharing one pod.",
        "A seed that glows faintly in the dark.", "A pine cone dusted with frost that never melts.",
        "A tiny seedling that slowly orbits its own pod.", "A pod that glows like a little lantern.",
        "A bulb that might one day become a star-shaped flower.", "A seed that grows toward moonlight.",
        "An acorn made of crystal, somehow still alive.", "Sleep beside it and you dream of forests.",
        "A seed said to grow into a tree that shelters a whole world.",
    ],
    "alien_artifact": [
        "A perfectly smooth tile made of an unknown material.", "A disc that hums when you hold it.",
        "Metal folded in ways that shouldn't be possible.", "A plate etched with symbols no one can read.",
        "A bead that glows from somewhere inside.", "A rod with a spiral groove running its whole length.",
        "A ring that floats a finger's width above any surface.", "A cube that's always warm, like it's alive.",
        "A piece of a map showing stars from somewhere else.", "A shell that speaks in a language no one knows.",
        "A lens that bends light into strange new colours.", "A stone that sings when the stars come out.",
        "A key shaped like a constellation.", "A mirror that shows what you're thinking, not your face.",
        "A shard from some kind of door or gate.", "A message from someone, somewhere. Still waiting to be understood.",
    ],
}
for _kind, _lines in DESCRIPTIONS.items():
    assert len(_lines) == 16, _kind
    for _i, _line in enumerate(_lines):
        CATALOG[f"{_kind}_{_i + 1:02d}"]["about"] = _line
