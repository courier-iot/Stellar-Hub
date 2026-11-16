"""64 curios that belong to 23 sets (10 pairs, 8 trios, 5 quads). A complete set fills one showcase
spot, pays a bonus the first time, and can be donated to or sold at the Museum. Each set's pieces turn up mostly
from one source, so collecting pulls the resident all over the colony.

source keys: expedition, meteor, visitor, trader, pet, park, observatory, exchange"""

# id: (name, rarity, shape kind, colours (main, shade, accent), source, [(piece name, about), ...])
SETS = {
    # ------------------------------------------------ pairs (2)
    "twin_moons": ("The Twin Moons", "common", "meteorite", ("s", "S", "c"), "observatory",
                   [("Pale Moon Pebble", "A smooth pebble the colour of the smaller moon."),
                    ("Dark Moon Pebble", "Its twin, grey-blue like the larger moon at dusk.")]),
    "comet_tea": ("Comet Tea Service", "common", "earth_relic", ("w", "c", "y"), "trader",
                  [("Comet Teapot", "A tiny teapot painted with a streaking comet."),
                   ("Comet Teacup", "The matching cup. Still smells faintly of bergamot.")]),
    "probe_antenna": ("Lost Probe Antenna", "common", "gadget", ("S", "g", "r"), "expedition",
                      [("Antenna Mast", "A bent mast stamped with a mission number."),
                       ("Antenna Dish", "A palm-sized dish that still points at Earth.")]),
    "seed_and_shell": ("Seed and Shell", "common", "seed_pod", ("e", "t", "m"), "park",
                       [("Shell-Wrapped Seed", "A seed that grew a shell to protect itself."),
                        ("Seed-Shaped Shell", "A shell that grew to look like a seed. They belong together.")]),
    "pilot_wings": ("Pilot's Wings", "uncommon", "earth_relic", ("y", "Y", "w"), "visitor",
                    [("Left Wing Pin", "Half of an old pilot's badge."), ("Right Wing Pin", "The other half. Someone's first flight.")]),
    "ice_and_fire": ("Ice and Fire", "uncommon", "crystal", ("c", "r", "w"), "meteor",
                     [("Frostfall Shard", "A crystal that's always cold to the touch."),
                      ("Emberfall Shard", "Its partner, always warm. Together they hum.")]),
    "lantern_pods": ("Lantern Pods", "common", "seed_pod", ("y", "o", "t"), "pet",
                     [("Dim Lantern Pod", "A pod that glows when you're sad."), ("Bright Lantern Pod", "A pod that glows when you're happy.")]),
    "music_box": ("Broken Music Box", "uncommon", "gadget", ("p", "P", "y"), "exchange",
                  [("Music Box Drum", "A pinned brass drum with half a melody."),
                   ("Music Box Key", "Wind it with the drum and the melody comes back.")]),
    "old_letters": ("Letters from Earth", "common", "earth_relic", ("t", "o", "r"), "visitor",
                    [("Sealed Letter", "A letter addressed to 'whoever lives here next'."),
                     ("Reply Letter", "An answer, written decades later.")]),
    "binary_star": ("Binary Star Charm", "rare", "alien_artifact", ("y", "m", "w"), "observatory",
                    [("Gold Star Charm", "One half of an orbiting pair."), ("Rose Star Charm", "The other half. They circle each other when placed close.")]),
    # ------------------------------------------------ trios (3)
    "first_rover": ("The First Rover", "uncommon", "gadget", ("Y", "S", "c"), "expedition",
                    [("Rover Wheel", "A wheel from the very first colony rover."),
                     ("Rover Camera", "Its camera, lens still cracked from the landing."),
                     ("Rover Nameplate", "A little plate reading 'PATHFINDER-0'.")]),
    "nebula_paints": ("Nebula Paint Set", "uncommon", "crystal", ("p", "m", "c"), "trader",
                      [("Violet Pigment", "Ground from a nebula's edge, they say."), ("Magenta Pigment", "Bright as a pulsar."),
                       ("Cyan Pigment", "The colour of starlight on ice.")]),
    "fossil_family": ("Fossil Family", "uncommon", "fossil", ("o", "O", "t"), "park",
                      [("Parent Fossil", "A large shell creature curled protectively."), ("Young Fossil", "A smaller one, beside it."),
                       ("Egg Fossil", "And one still in its egg.")]),
    "storm_glass": ("Storm Glass Set", "rare", "crystal", ("c", "C", "w"), "meteor",
                    [("Storm Glass Base", "A brass base that tingles during solar storms."),
                     ("Storm Glass Tube", "Crystals inside shift with the space weather."),
                     ("Storm Glass Cap", "Seals it. Now it predicts storms.")]),
    "captain_kit": ("Captain's Kit", "uncommon", "earth_relic", ("R", "y", "w"), "visitor",
                    [("Captain's Compass", "Always points to the nearest friend."), ("Captain's Log", "Half the pages are star maps."),
                     ("Captain's Cap", "Too big for anyone in the colony.")]),
    "garden_bells": ("Garden Bells", "common", "shell", ("w", "e", "y"), "pet",
                     [("Low Bell Shell", "Rings a low note in the wind."), ("Middle Bell Shell", "A middle note."),
                      ("High Bell Shell", "Together they play a little chord.")]),
    "signal_relay": ("Deep Space Relay", "rare", "gadget", ("S", "c", "m"), "expedition",
                     [("Relay Receiver", "Still picks up something faint."), ("Relay Amplifier", "Makes the faint thing louder."),
                      ("Relay Decoder", "Turns it into... a lullaby?")]),
    "auction_trio": ("Collector's Trio", "rare", "alien_artifact", ("y", "Y", "p"), "exchange",
                     [("Collector's Seal", "Proof of a legendary collection."), ("Collector's Ledger", "Lists treasures long scattered."),
                      ("Collector's Lens", "For appraising very small wonders.")]),
    # ------------------------------------------------ quads (4)
    "four_seasons": ("The Four Seasons", "rare", "seed_pod", ("e", "y", "r"), "park",
                     [("Spring Seed", "Sprouts at the first warm hour."), ("Summer Seed", "Hot to hold, smells of grass."),
                      ("Autumn Seed", "Rust-red and crackly."), ("Winter Seed", "Frosted, sleeping, patient.")]),
    "constellation": ("Lost Constellation", "rare", "alien_artifact", ("w", "c", "y"), "observatory",
                      [("Star Stone I", "A stone with a single star carved in it."), ("Star Stone II", "A second star, joined by a line."),
                       ("Star Stone III", "A third, and the shape begins."), ("Star Stone IV", "The last. It's a constellation no chart has.")]),
    "moon_garden": ("Moon Garden", "uncommon", "shell", ("s", "e", "c"), "pet",
                    [("New Moon Shell", "Dark as a moonless night."), ("Crescent Shell", "A sliver of silver."),
                     ("Half Moon Shell", "Half light, half shadow."), ("Full Moon Shell", "Round and glowing softly.")]),
    "ship_in_parts": ("Ship in Parts", "legendary", "gadget", ("s", "S", "y"), "trader",
                      [("Tiny Hull", "The hull of a model starship."), ("Tiny Engine", "Its engine. It glows when nobody's looking."),
                       ("Tiny Sail", "A solar sail no bigger than a stamp."), ("Tiny Pilot", "A pilot figure who seems to wave.")]),
    "first_signal": ("The First Signal", "legendary", "alien_artifact", ("p", "c", "y"), "meteor",
                     [("Signal Fragment: Hello", "A fragment of the first message ever received."),
                      ("Signal Fragment: We", "The second word."), ("Signal Fragment: Are", "The third."),
                      ("Signal Fragment: Here", "The last. Someone was here before us.")]),
}

SET_BONUS = {2: 40, 3: 90, 4: 180}
RARITY_MULT = {"common": 1.0, "uncommon": 1.5, "rare": 2.5, "legendary": 5.0}
SOURCE_WORDS = {"expedition": ("expedition",), "meteor": ("meteor", "star", "sky"), "visitor": ("visitor", "pack", "talk"),
                "trader": ("trader",), "pet": ("pet", "wander", "Dusty", "Bolt"), "park": ("park", "walk"),
                "observatory": ("observatory", "telescope", "deck"), "exchange": ("exchange", "auction", "collector")}

assert sum(len(s[5]) for s in SETS.values()) == 64, "there should be 64 set curios"


def piece_ids(set_id):
    return [f"set_{set_id}_{i + 1}" for i in range(len(SETS[set_id][5]))]


def set_of(cid):
    if not str(cid).startswith("set_"):
        return None
    sid = str(cid)[4:].rsplit("_", 1)[0]
    return sid if sid in SETS else None


def add_to_catalog(catalog):
    for sid, (name, rarity, kind, colors, source, pieces) in SETS.items():
        for i, (pname, about) in enumerate(pieces):
            cid = f"set_{sid}_{i + 1}"
            catalog[cid] = {"id": cid, "kind": kind, "name": pname, "rarity": rarity, "about": about,
                            "set": sid, "set_name": name, "colors": colors, "source": source}


def source_for(text):
    t = str(text).lower()
    for key, words in SOURCE_WORDS.items():
        if any(w.lower() in t for w in words):
            return key
    return None
