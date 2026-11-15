"""The 32 greenhouse species and how they're cared for.

water_h: hours between waterings (watering much earlier than half of this is overwatering)
feed_h:  hours between feedings
light:   low | medium | high (the grow lamp setting the plant wants)
days:    days to reach full bloom when healthy
colors:  (leaf, flower) palette keys used by the pixel art
"""

TIER_PRICE = {"common": 3, "uncommon": 10, "rare": 25, "legendary": 60}

SPECIES = {
    # ---- common (easy, forgiving)
    "moon_moss":       dict(tier="common", water_h=24, feed_h=96, light="low", days=2, colors=("E", "s"), about="soft silver moss that glows faintly"),
    "dust_fern":       dict(tier="common", water_h=18, feed_h=72, light="low", days=3, colors=("e", "e"), about="a hardy fern that grows in regolith"),
    "comet_clover":    dict(tier="common", water_h=12, feed_h=72, light="medium", days=2, colors=("e", "w"), about="clover with tiny white comet-tail flowers"),
    "crater_cactus":   dict(tier="common", water_h=72, feed_h=168, light="high", days=4, colors=("E", "m"), about="a squat cactus that loves bright light and little water"),
    "solar_sprout":    dict(tier="common", water_h=12, feed_h=48, light="high", days=2, colors=("e", "y"), about="a cheerful sprout that turns toward the lamp"),
    "pebble_succulent": dict(tier="common", water_h=96, feed_h=168, light="medium", days=4, colors=("s", "p"), about="looks like a pile of pebbles, barely needs water"),
    "orbit_ivy":       dict(tier="common", water_h=24, feed_h=96, light="low", days=3, colors=("E", "c"), about="ivy that grows in slow spirals"),
    "starlight_grass": dict(tier="common", water_h=18, feed_h=96, light="medium", days=2, colors=("e", "t"), about="thin grass with glowing tips"),
    # ---- uncommon (need a routine)
    "nebula_rose":     dict(tier="uncommon", water_h=12, feed_h=48, light="medium", days=5, colors=("E", "m"), about="a rose with swirling pink-purple petals"),
    "ion_tulip":       dict(tier="uncommon", water_h=16, feed_h=48, light="high", days=4, colors=("e", "c"), about="a tulip that crackles softly with static"),
    "gravity_lily":    dict(tier="uncommon", water_h=8, feed_h=48, light="low", days=5, colors=("E", "w"), about="a water lily whose petals float upward"),
    "plasma_pepper":   dict(tier="uncommon", water_h=12, feed_h=36, light="high", days=5, colors=("e", "r"), about="a pepper plant with glowing red fruit"),
    "echo_orchid":     dict(tier="uncommon", water_h=24, feed_h=72, light="low", days=6, colors=("E", "p"), about="an orchid that hums when touched"),
    "aurora_sage":     dict(tier="uncommon", water_h=20, feed_h=72, light="medium", days=4, colors=("e", "c"), about="a herb whose leaves shimmer green and teal"),
    "quartz_aloe":     dict(tier="uncommon", water_h=48, feed_h=120, light="high", days=6, colors=("s", "c"), about="aloe with crystal-clear leaf tips"),
    "meteor_marigold": dict(tier="uncommon", water_h=12, feed_h=48, light="high", days=4, colors=("e", "Y"), about="a fiery orange flower that loves light"),
    # ---- rare (demanding)
    "void_bloom":      dict(tier="rare", water_h=10, feed_h=30, light="low", days=7, colors=("P", "p"), about="a dark flower that only opens in dim light"),
    "pulsar_poppy":    dict(tier="rare", water_h=8, feed_h=24, light="high", days=6, colors=("e", "r"), about="a poppy that pulses with light every few seconds"),
    "cryo_camellia":   dict(tier="rare", water_h=14, feed_h=36, light="low", days=8, colors=("C", "w"), about="a camellia with frosty, ice-cold petals"),
    "singing_willow":  dict(tier="rare", water_h=12, feed_h=48, light="medium", days=9, colors=("E", "e"), about="a tiny willow that whistles in the vents"),
    "magnetar_mint":   dict(tier="rare", water_h=6, feed_h=24, light="medium", days=6, colors=("e", "c"), about="mint that aligns its leaves to magnetic fields"),
    "eclipse_iris":    dict(tier="rare", water_h=16, feed_h=36, light="low", days=7, colors=("P", "y"), about="an iris with a dark ring around a golden center"),
    "photon_fig":      dict(tier="rare", water_h=12, feed_h=30, light="high", days=9, colors=("E", "P"), about="a fig tree whose fruit stores sunlight"),
    "tidal_lotus":     dict(tier="rare", water_h=6, feed_h=36, light="medium", days=8, colors=("C", "m"), about="a lotus that rises and falls like a tide"),
    # ---- legendary (very hard, very rewarding)
    "supernova_sunflower": dict(tier="legendary", water_h=8, feed_h=20, light="high", days=10, colors=("e", "y"), about="a sunflower that blooms with a burst of light"),
    "quasar_queen":    dict(tier="legendary", water_h=6, feed_h=18, light="high", days=12, colors=("E", "c"), about="a regal blossom said to outshine galaxies"),
    "dark_matter_dahlia": dict(tier="legendary", water_h=10, feed_h=24, light="low", days=11, colors=("P", "M"), about="a dahlia almost invisible, except to those who care for it"),
    "starseed_bonsai": dict(tier="legendary", water_h=24, feed_h=48, light="medium", days=14, colors=("E", "s"), about="a bonsai grown from a fallen star"),
    "chrono_cherry":   dict(tier="legendary", water_h=12, feed_h=24, light="medium", days=12, colors=("e", "m"), about="cherry blossoms that seem to bloom in slow motion"),
    "galaxy_glowcap":  dict(tier="legendary", water_h=8, feed_h=30, light="low", days=10, colors=("P", "c"), about="a glowing mushroom with a spiral galaxy on its cap"),
    "celestial_vine":  dict(tier="legendary", water_h=6, feed_h=20, light="medium", days=13, colors=("E", "t"), about="a vine that maps the constellations as it grows"),
    "phoenix_fern":    dict(tier="legendary", water_h=12, feed_h=24, light="high", days=11, colors=("e", "Y"), about="a fern that can regrow from its own ashes"),
}

STAGES = [(0.0, "seed"), (0.15, "sprout"), (0.4, "young"), (0.75, "mature"), (1.0, "blooming")]
LIGHTS = ("low", "medium", "high")


def stage_for(growth):
    name = "seed"
    for threshold, s in STAGES:
        if growth >= threshold:
            name = s
    return name


def by_tier_text():
    tiers = {}
    for name, s in SPECIES.items():
        tiers.setdefault(s["tier"], []).append(name)
    return "; ".join(f"{t} ({TIER_PRICE[t]}cr): {', '.join(n)}" for t, n in tiers.items())
