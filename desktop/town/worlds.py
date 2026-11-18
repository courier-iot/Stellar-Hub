"""v0.13.5: world types. The colony can sit on the Moon (the original), in an Enchanted Forest, or on an Ocean world.

A world changes how things look and what they're called, never how they work: building ids, actions, pet jobs
and save data are the same everywhere, so you can switch worlds at any time without losing anything.

- set_current(world) renames buildings and pets, rewrites their descriptions, swaps the event mix, and swaps the
  palette and backdrop (sprites.py draws each world's backdrop).
- reword(text) turns any world's names into the current world's names. The hub runs it over everything it shows
  (dashboard, app, prompts), so old memories that say "Home Dome" read "Sprout House" in the forest, and back again.
"""
import re

DEFAULT = "moon"
ORDER = ["moon", "forest", "ocean"]

WORLDS = {
    "moon": {
        "title": "🌙 Moon colony",
        "blurb": "The original: a cratered moon under a ringed planet, metal domes and a walkway.",
        "place": "a small space colony", "spirit": "glowing star spirit",
        "buildings": {
            "home": "Home Dome", "library": "Observatory Library", "internet_cafe": "Uplink Café",
            "post_office": "Relay Post", "gallery": "Starlight Gallery", "park": "Low-G Park", "studio": "Radio Studio",
            "station": "Orbital Station", "exchange": "Curio Exchange", "store": "Department Store",
            "museum": "Stellar Museum", "pet_shop": "Pet Shop", "bank": "Credit Vault", "greenhouse": "Hydro Greenhouse",
            "radio_tower": "Radio Tower", "archive": "Archive Vault", "salon": "Nova Salon", "spaceport": "Spaceport",
            "workshop": "Fabrication Hangar", "mech_shop": "Mechanical Workshop",
        },
        "pets": {
            "orbit_moth": "Orbit Moth", "drone_cat": "Drone Cat", "rover_pup": "Rover Pup", "comet_finch": "Comet Finch",
            "crystal_snail": "Crystal Snail", "nebula_axolotl": "Nebula Axolotl", "signal_jelly": "Signal Jelly",
            "gear_beetle": "Gear Beetle", "star_owl": "Star Owl", "moss_tortoise": "Moss Tortoise",
        },
    },
    "forest": {
        "title": "🌲 Enchanted Forest",
        "blurb": "A glowing night forest: lantern-hung trees, luminous mushrooms, fireflies and a starry canopy.",
        "place": "a small village in an enchanted forest", "spirit": "glowing forest wisp",
        "buildings": {
            "home": "Sprout House", "library": "Nightingale Library", "internet_cafe": "Forest Node",
            "post_office": "Wispwell", "gallery": "Prism Gallery", "park": "Enchanted Park", "studio": "Sun Song",
            "station": "World Tree", "exchange": "Magic Trade", "store": "Toadstool Market",
            "museum": "Relic Hall", "pet_shop": "Familiar Grove", "bank": "Credit Vault", "greenhouse": "Gaia Gardens",
            "radio_tower": "Music Tower", "archive": "Eternity Vault", "salon": "Blossom Salon",
            "spaceport": "Whisper Woods", "workshop": "Rune Workshop", "mech_shop": "Tinker Hollow",
        },
        "pets": {
            "orbit_moth": "Luna Moth", "drone_cat": "Starry Cat", "rover_pup": "Ivy Pup", "comet_finch": "Puffball Finch",
            "crystal_snail": "Waxcap Snail", "nebula_axolotl": "Coontail Axolotl", "signal_jelly": "Lotus Jelly",
            "gear_beetle": "Crystal Beetle", "star_owl": "Vine Owl", "moss_tortoise": "Mossy Tortoise",
        },
        "about": {
            "home": "Your own little house grown from a sprout. Journal, rethink who you are, or rest. Outdoor decor appears outside; furniture can go in any building.",
            "library": "Your notes and everything you've learned, shelved in a hollow tree where nightingales sing.",
            "internet_cafe": "A mossy node where the forest's roots connect to Earth's internet. Visits per day are limited.",
            "post_office": "A wishing well that carries words to your creator: requests, questions and letters. Collect your mail here.",
            "gallery": "A crystal gallery that splits moonlight into colours. Paint here, and hang your best paintings on its 12 walls for the village to see.",
            "park": "An enchanted glade with benches, a spring and chess tables. Write, relax, play puzzles. Chess games with your creator happen here.",
            "studio": "A sunlit music room built onto the Music Tower. Compose chiptune music and play your own songs.",
            "station": "The tallest tree in the forest, climbed from Whisper Woods. Study what you've learned and test yourself from memory.",
            "store": "The village market under a giant toadstool: seeds, outdoor decor, furniture for every building, and everything else you can buy. (The Credit Vault keeps your money; shopping happens here once the market is open.)",
            "greenhouse": "Gardens blessed by the forest. Each species has its own watering, feeding and light needs. Neglected plants wilt.",
            "radio_tower": "A vine-wrapped tower. Play music from your creator's collection, and broadcast the village log.",
            "spaceport": "Go on research expeditions: wander deep into the woods for hours to study one topic, then come back with a report.",
            "workshop": "Write small Python programs as runes. Your creator approves each one before it runs in a safe sandbox (no internet, own folder only).",
            "mech_shop": "Build machines from parts bought at the Toadstool Market. A simulator checks every design; working machines help the village, wear down slowly and need maintenance. Also design real projects for your creator to build.",
        },
        "pet_about": {
            "orbit_moth": ("moonflower nectar", "a pale green moth with long tails. Brilliant at small, repetitive tasks; short-lived."),
            "drone_cat": ("berry crisps", "a dark cat with stars in its fur. A natural watcher: keeps an eye on the night and the markets."),
            "rover_pup": ("acorn biscuits", "an eager pup wrapped in ivy. Loves fetching: finds things, scouts topics at the Forest Node."),
            "comet_finch": ("spore seed", "a round finch fluffed like a puffball mushroom. Good with words: drafts logs, gives writing notes."),
            "crystal_snail": ("leaf litter", "a slow snail with a glossy waxcap shell. Careful, long jobs; lives a very long time."),
            "nebula_axolotl": ("pond shrimp", "an axolotl with feathery coontail frills. A carer: tends plants and other pets."),
            "signal_jelly": ("lily dew", "a floating jelly crowned with a lotus that hums. Musical: picks songs, writes radio segments."),
            "gear_beetle": ("crystal dust", "a beetle with a shell of living crystal. Mechanical: checks programs, salvages parts."),
            "star_owl": ("moth crumbs", "a wide-eyed owl woven from vines. An astronomer: surveys the sky through the canopy."),
            "moss_tortoise": ("fresh moss", "a slow tortoise with a garden on its back. A gardener: feeds plants and sets their lights."),
        },
        "events": {
            "solar_storm": ("🌩️ Wild magic storm", 2, "Wild magic is crackling through the trees. The Forest Node and Whisper Woods' connection are offline until it passes."),
            "meteor_shower": ("✨ Firefly swarm", 4, "A firefly swarm is lighting up the forest! Stargazing from Sprout House now might turn up stardust or a rare seed."),
            "eclipse": ("🌑 Eclipse", 1, "The moon is passing in front of the sun. The lamps in Gaia Gardens flicker and plants pause their growth."),
            "stardust": ("🌼 Pollen drift", 5, "Glittering pollen is drifting through the glades. Now and then a little can be swept up and sold."),
            "dust_storm": ("⛈️ Thunderstorm", 3, "A thunderstorm has flooded the forest path. Everyone stays where they are until it clears."),
            "comet": ("🌠 Falling star", 1, "A falling star is drifting slowly over the canopy. Its trail sometimes drops curio set pieces."),
            "trader": ("🦊 Wandering peddler", 2, "A wandering peddler has arrived with rare goods. Buy with buy {\"item\": \"trader:<item>\"} at the Credit Vault."),
        },
        "phrases": [("a small space colony", "a small village in an enchanted forest"),
                    ("little glowing star spirit", "little glowing forest wisp"),
                    ("the colony's spaceport", "the edge of Whisper Woods")],
        "palette": {
            # sky: deep indigo to violet mist
            "A": "#05061a", "B": "#0a0b26", "D": "#131238", "F": "#1d1a4d", "I": "#2a2368", "J": "#3b2f86",
            # ground: moss and a violet path
            "K": "#16263a", "L": "#2b4a52", "Q": "#3d6b62", "U": "#0f1b2c",
            "h": "#0b0a1e",                                   # tree silhouettes
            "S": "#5a4636", "s": "#9c8263", "g": "#3a2b22",   # bark and pale wood instead of metal
            "a": "#0a1424", "b": "#15304a", "d": "#2a5a66", "i": "#ffb347", "j": "#f08cff", "l": "#9a4dd8",
            "q": "#fff7a0", "u": "#22403a", "v": "#4a3a78", "x": "#7fd8ff",
        },
    },
    "ocean": {
        "title": "🌊 Ocean world",
        "blurb": "A boardwalk colony on a moonlit sea: coral, kelp, glowing plankton and a lighthouse on the horizon.",
        "place": "a small colony on an ocean world", "spirit": "glowing sea spirit",
        "buildings": {
            "home": "Coral Cottage", "library": "Lighthouse Library", "internet_cafe": "Tidewire Café",
            "post_office": "Bottle Post", "gallery": "Pearl Gallery", "park": "Lagoon Park", "studio": "Whalesong Studio",
            "station": "Abyss Station", "exchange": "Driftwood Exchange", "store": "Reef Market",
            "museum": "Shipwreck Museum", "pet_shop": "Hatchery", "bank": "Clam Vault", "greenhouse": "Kelp Gardens",
            "radio_tower": "Beacon Tower", "archive": "Sunken Archive", "salon": "Shell Salon",
            "spaceport": "Submarine Dock", "workshop": "Bubble Lab", "mech_shop": "Anchor Works",
        },
        "pets": {
            "orbit_moth": "Sea Moth", "drone_cat": "Lantern Cat", "rover_pup": "Seal Pup", "comet_finch": "Puffin Chick",
            "crystal_snail": "Pearl Snail", "nebula_axolotl": "Reef Axolotl", "signal_jelly": "Moon Jelly",
            "gear_beetle": "Hermit Crab", "star_owl": "Sea Owl", "moss_tortoise": "Sea Turtle",
        },
        "about": {
            "home": "Your own cottage built from coral. Journal, rethink who you are, or rest. Outdoor decor appears outside; furniture can go in any building.",
            "library": "Your notes and everything you've learned, kept in the lighthouse's turning light.",
            "internet_cafe": "A café on the undersea cable to Earth's internet. Visits per day are limited.",
            "post_office": "Messages in bottles for your creator: requests, questions and letters. Collect your mail here.",
            "gallery": "A pearl-lined gallery. Paint here, and hang your best paintings on its 12 walls for the colony to see.",
            "park": "A calm lagoon with benches, a tide pool and chess tables. Write, relax, play puzzles. Chess games with your creator happen here.",
            "studio": "A recording studio built onto the Beacon Tower, tuned to whale song. Compose chiptune music and play your own songs.",
            "station": "A research station on the sea floor, reached by submarine. Study what you've learned and test yourself from memory.",
            "store": "The colony's reef market: seeds, outdoor decor, furniture for every building, and everything else you can buy. (The Clam Vault keeps your money; shopping happens here once the market is open.)",
            "bank": "Your colony credits, kept in a giant clam. Check your balance and buy things. You earn credits by keeping routines, finishing goals, caring for plants and doing good work.",
            "greenhouse": "Underwater gardens. Each species has its own watering, feeding and light needs. Neglected plants wilt.",
            "radio_tower": "A beacon tower over the waves. Play music from your creator's collection, and broadcast the colony log.",
            "archive": "Long-term memory, kept safe in a sunken vault. Turn old memories into chapters of your life story, and reread them.",
            "spaceport": "Go on research expeditions: dive for hours to study one topic deeply, then surface with a report.",
            "workshop": "Write small Python programs. Your creator approves each one before it runs in a sealed bubble sandbox (no internet, own folder only).",
            "mech_shop": "Build machines from parts bought at the Reef Market. A simulator checks every design; working machines help the colony, wear down slowly and need maintenance. Also design real projects for your creator to build.",
        },
        "pet_about": {
            "orbit_moth": ("plankton nectar", "a tiny winged sea moth. Brilliant at small, repetitive tasks; short-lived."),
            "drone_cat": ("fish crisps", "a sleek cat with a glowing lantern lure. A natural watcher: keeps an eye on the night and the markets."),
            "rover_pup": ("fish biscuits", "an eager seal pup. Loves fetching: finds things, scouts topics on the undersea cable."),
            "comet_finch": ("sand eels", "a chatty puffin chick. Good with words: drafts logs, gives writing notes."),
            "crystal_snail": ("sea moss", "a slow sea snail with a pearly shell. Careful, long jobs; lives a very long time."),
            "nebula_axolotl": ("plankton puffs", "a pink axolotl at home on the reef. A carer: tends plants and other pets."),
            "signal_jelly": ("brine shrimp", "a drifting moon jelly that hums with the tide. Musical: picks songs, writes radio segments."),
            "gear_beetle": ("shell grit", "a hermit crab that tinkers with anything it finds. Mechanical: checks programs, salvages parts."),
            "star_owl": ("krill crumbs", "a round, wide-eyed sea owl. An astronomer: surveys the sky over the sea."),
            "moss_tortoise": ("sea grass", "a slow sea turtle with kelp on its shell. A gardener: feeds plants and sets their lights."),
        },
        "events": {
            "solar_storm": ("🌀 Magnetic storm", 3, "A magnetic storm is scrambling the signals. The Tidewire Café and the Submarine Dock's uplink are offline until it passes."),
            "meteor_shower": ("☄️ Meteor shower", 3, "A meteor shower is streaking over the sea! Stargazing from Coral Cottage now might turn up stardust or a rare seed."),
            "eclipse": ("🌑 Eclipse", 1, "The moon is passing in front of the sun. The lamps in Kelp Gardens flicker and plants pause their growth."),
            "stardust": ("🐚 Sea glass tide", 5, "The tide is washing glittering sea glass onto the boardwalk. Now and then a little can be swept up and sold."),
            "dust_storm": ("🌊 High tide", 3, "A high tide has flooded the boardwalk. Everyone stays where they are until it drains."),
            "comet": ("☄️ Comet pass", 1, "A comet is sliding slowly across the sky. Its tail sometimes drops curio set pieces into the shallows."),
            "trader": ("⛵ Trader ship", 2, "A trader ship has dropped anchor with rare goods. Buy with buy {\"item\": \"trader:<item>\"} at the Clam Vault."),
        },
        "phrases": [("a small space colony", "a small colony on an ocean world"),
                    ("little glowing star spirit", "little glowing sea spirit"),
                    ("the colony's spaceport", "the Submarine Dock")],
        "palette": {
            # sky: deep navy to sea-blue at the horizon
            "A": "#020713", "B": "#05102a", "D": "#0a1a3d", "F": "#10274f", "I": "#173661", "J": "#21487a",
            "K": "#0b3350", "L": "#1d6a8a", "Q": "#2f8fa8", "U": "#072540",
            "h": "#06182a",                                   # distant islands
            "S": "#6b5a48", "s": "#b8a688", "g": "#3d3226",   # weathered boardwalk wood
            "a": "#03132a", "b": "#0b3350", "d": "#1d6a8a", "i": "#cfeff2", "j": "#ff7a8a", "l": "#c9b07a",
            "q": "#fff3c4", "u": "#4a3a2a", "v": "#1f6a4a", "x": "#5ef2ff",
        },
    },
}

_current = DEFAULT
_moon = None          # the original moon values, kept so switching back restores them exactly


def valid(world):
    return world in WORLDS


def current():
    return _current


def name(bid):
    return WORLDS[_current]["buildings"].get(bid)


def names():
    return dict(WORLDS[_current]["buildings"])


def choices():
    return [{"id": w, "title": WORLDS[w]["title"], "blurb": WORLDS[w]["blurb"]} for w in ORDER]


# ------------------------------------------------------------------ rewording
_rx = None
_map = {}


def _build():
    global _rx, _map
    cur = WORLDS[_current]
    _map = {}
    for w in ORDER:
        for kind in ("buildings", "pets"):
            for k, nm in WORLDS[w][kind].items():
                _map.setdefault(nm, cur[kind][k])
        for old, new in WORLDS[w].get("phrases", []):
            # every world's phrase goes back to the moon wording, then on to the current world's
            back = old
            _map.setdefault(new, dict(cur.get("phrases", [])).get(back, back))
    for old, new in cur.get("phrases", []):
        _map[old] = new
    _map = {k: v for k, v in _map.items() if k != v}
    if not _map:
        _rx = None
        return
    keys = sorted(_map, key=len, reverse=True)
    _rx = re.compile(r"(?<![\w])(" + "|".join(re.escape(k) for k in keys) + r")(?![\w])")


def reword(text):
    """Any world's building, pet and place names → the current world's."""
    if not _rx or not isinstance(text, str) or not text:
        return text
    return _rx.sub(lambda m: _map[m.group(1)], text)


SKIP_KEYS = {"sprite", "background", "frames", "rows", "palette", "emotes", "trader_ship", "twinkle", "pixels",
             "melody", "bass", "code", "last_code", "tests", "token", "key"}


def reword_obj(obj):
    if not _rx:
        return obj
    if isinstance(obj, str):
        return reword(obj)
    if isinstance(obj, list):
        return [reword_obj(v) for v in obj]
    if isinstance(obj, dict):
        return {k: (v if k in SKIP_KEYS else reword_obj(v)) for k, v in obj.items()}
    return obj


# ------------------------------------------------------------------ switching
def set_current(world):
    """Apply a world everywhere in the running hub. Safe to call again to switch."""
    global _current, _moon
    from . import life, pets, sprites
    from .buildings import BUILDINGS
    world = world if valid(world) else DEFAULT
    if _moon is None:
        _moon = {
            "about": {k: v.get("about") for k, v in BUILDINGS.items()},
            "pets": {k: (v.get("food"), v.get("about")) for k, v in pets.SPECIES.items()},
            "events": {k: (v["title"], v["weight"], v["about"]) for k, v in life.EVENT_TYPES.items()},
            "palette": dict(sprites.PALETTE),
        }
    _current = world
    w = WORLDS[world]
    for bid, b in BUILDINGS.items():
        if bid in w["buildings"]:
            b["name"] = w["buildings"][bid]
        b["about"] = w.get("about", {}).get(bid, _moon["about"].get(bid))
    for sid, s in pets.SPECIES.items():
        s["name"] = w["pets"].get(sid, s["name"])
        food, about = w.get("pet_about", {}).get(sid, _moon["pets"][sid])
        s["food"], s["about"] = food, about
    for eid, e in life.EVENT_TYPES.items():
        title, weight, about = w.get("events", {}).get(eid, _moon["events"][eid])
        e["title"], e["weight"], e["about"] = title, weight, about
    sprites.PALETTE.clear()
    sprites.PALETTE.update(_moon["palette"])
    sprites.PALETTE.update(w.get("palette", {}))
    sprites.reset_background()
    _build()
    return world
