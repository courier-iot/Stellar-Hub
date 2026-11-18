"""v0.15.1: Enchanted Forest and Ocean world pets: two 12x12 frames each, like the Moon pets in pets.py.
Same species ids, jobs and sizes; only the drawings change with the world."""
from .sprites import Canvas


def frames(draw):
    out = []
    for f in (0, 1):
        c = Canvas(12, 12)
        draw(c, f)
        out.append(c.rows())
    return out


# ------------------------------------------------------------------ Enchanted Forest
def luna_moth(c, f):
    c.rect(5, 3, 2, 6, "t"); c.px(5, 2, "k"); c.px(6, 2, "k"); c.px(4, 1, "o"); c.px(7, 1, "o")
    wy = 2 if f else 4
    c.rect(1, wy, 4, 4, "e"); c.rect(7, wy, 4, 4, "e"); c.px(2, wy + 1, "Y"); c.px(9, wy + 1, "Y")
    c.px(1, wy, "q"); c.px(10, wy, "q")
    c.rect(3, wy + 4, 1, 4 - f, "e"); c.rect(8, wy + 4, 1, 4 - f, "e")      # long tails
    c.px(3, wy + 7 - f, "q"); c.px(8, wy + 7 - f, "q")


def starry_cat(c, f):
    c.rect(3, 6, 7, 4, "n"); c.rect(2, 3, 5, 4, "n"); c.px(2, 2, "n"); c.px(6, 2, "n")
    c.px(3, 4, "y"); c.px(5, 4, "y")
    c.rect(9, 5 - f, 2, 1, "n"); c.px(10, 4 - f, "n"); c.px(11, 3 - f, "w")
    for (x, y) in ((4, 7), (7, 8), (8, 6), (3, 5)):
        c.px(x, y, "w")
    c.rect(4, 10, 1, 2, "n"); c.rect(8, 10, 1, 2, "n")


def ivy_pup(c, f):
    c.rect(3, 5, 7, 4, "o"); c.rect(7, 2, 4, 4, "o"); c.px(9, 3, "k"); c.rect(10, 4, 2, 1, "O")
    c.rect(7, 1, 1, 2, "E"); c.px(2, 4 + f, "o")
    for (x, y) in ((3, 5), (5, 4), (7, 5), (4, 6)):                       # ivy on its back
        c.px(x, y, "e"); c.px(x + 1, y, "E")
    c.disc(4, 10, 1, "O"); c.disc(8, 10, 1, "O"); c.px(4, 11, "k" if f else "O"); c.px(8, 11, "O" if f else "k")


def puffball_finch(c, f):
    c.disc(6, 6, 4, "t"); c.disc(6, 5, 3, "w")
    for (x, y) in ((4, 4), (7, 6), (5, 8), (8, 4)):
        c.px(x, y, "o")                                                    # puffball speckles
    c.px(8, 5, "k"); c.px(10, 6, "Y")
    c.rect(3, 6 - f, 2, 2, "s")
    c.px(5, 10, "O"); c.px(7, 10, "O")


def waxcap_snail(c, f):
    c.rect(1, 9, 10, 2, "s"); c.px(10 + f, 8, "s"); c.px(11, 7, "S"); c.px(9 + f, 7, "S")
    c.disc(5, 6, 4, "r", 3); c.disc(4, 5, 2, "Y", 1.5); c.px(3, 4, "w")    # glossy waxcap shell
    c.rect(2, 8, 7, 1, "R")


def coontail_axolotl(c, f):
    c.rect(2, 6, 8, 3, "e"); c.rect(7, 4, 4, 4, "e"); c.px(9, 5, "k"); c.px(10, 7, "E")
    for i, (x, y) in enumerate(((7, 3), (8, 2), (10, 3), (11, 2), (6, 4))):
        c.px(x, y + (f if i % 2 else 0), "E")                             # feathery coontail frills
        c.px(x, y - 1 + (f if i % 2 else 0), "e")
    c.rect(0, 7 - f, 2, 1, "e"); c.px(3, 9, "E"); c.px(7, 9, "E")


def lotus_jelly(c, f):
    c.disc(6, 6, 4, "p", 3); c.disc(6, 6, 2, "w", 1.5); c.rect(2, 6, 9, 1, "P")
    c.px(4, 2, "m"); c.px(8, 2, "m"); c.rect(5, 1, 3, 2, "m"); c.px(6, 0, "w")    # the lotus on top
    for i, x in enumerate((3, 5, 7, 9)):
        c.rect(x, 8, 1, 2 + (i + f) % 2 * 2, "m" if i % 2 else "p")


def crystal_beetle(c, f):
    c.disc(6, 7, 4, "x"); c.rect(6, 3, 1, 8, "C"); c.px(4, 5, "w"); c.px(8, 8, "w"); c.px(5, 9, "c")
    c.rect(9, 5, 2, 2, "k"); c.px(10, 4 - f, "S"); c.px(11, 3, "S")
    for x in (3, 6, 9):
        c.px(x, 11, "k"); c.px(x + f - 1 if x != 6 else x, 11, "k")


def vine_owl(c, f):
    c.disc(6, 6, 4, "E"); c.disc(4, 5, 2, "t"); c.disc(8, 5, 2, "t"); c.px(4, 5, "k"); c.px(8, 5, "k")
    c.px(6, 7, "Y"); c.px(3, 2, "E"); c.px(9, 2, "E")
    c.px(2, 8 - f, "e"); c.px(10, 8 - f, "e"); c.px(5, 9, "e"); c.px(7, 9, "e")     # vine curls
    c.px(2, 4, "e"); c.px(10, 4, "e")
    c.rect(5, 11, 1, 1, "Y"); c.rect(7, 11, 1, 1, "Y")


def mossy_tortoise(c, f):
    c.disc(5, 7, 4, "o"); c.disc(5, 6, 3, "u"); c.px(4, 4, "e"); c.px(6, 3, "e"); c.px(3, 6, "E")
    c.px(6, 2, "r"); c.px(5, 2, "r"); c.px(6, 1, "w")                       # a tiny mushroom on its back
    c.rect(9, 7, 3, 2, "e"); c.px(10, 7, "k")
    c.rect(2, 10, 2, 2, "e"); c.rect(7, 10, 2, 2 - f, "e")


FOREST_LIST = [("Luna Moth", luna_moth), ("Starry Cat", starry_cat), ("Ivy Pup", ivy_pup), ("Puffball Finch", puffball_finch),
          ("Waxcap Snail", waxcap_snail), ("Coontail Axolotl", coontail_axolotl), ("Lotus Jelly", lotus_jelly),
          ("Crystal Beetle", crystal_beetle), ("Vine Owl", vine_owl), ("Mossy Tortoise", mossy_tortoise)]


# ------------------------------------------------------------------ Ocean world
def sea_moth(c, f):
    c.disc(6, 6, 3, "Y", 2); c.px(9, 6, "Y"); c.px(10, 6, "o"); c.px(8, 5, "k")
    wy = 3 if f else 5                                                      # wing-like fins
    c.rect(3, wy, 3, 2, "y"); c.rect(3, 12 - wy - 2, 3, 2, "y")
    c.rect(1, 5, 2, 3, "O"); c.px(0, 4 + f, "O")


def lantern_cat(c, f):
    c.rect(3, 6, 7, 4, "k"); c.rect(2, 3, 5, 4, "k"); c.px(2, 2, "k"); c.px(6, 2, "k")
    c.px(3, 4, "x"); c.px(5, 4, "x")
    c.rect(4, 1, 1, 2, "S"); c.px(5, 0, "y"); c.px(5 + f, 0, "q")          # the glowing lure
    c.rect(9, 5 - f, 2, 1, "k"); c.px(10, 4 - f, "k")
    c.rect(4, 10, 1, 2, "D"); c.rect(8, 10, 1, 2, "D")


def seal_pup(c, f):
    c.disc(6, 7, 4, "s", 3); c.disc(6, 6, 3, "w", 2); c.px(8, 5, "k"); c.px(5, 5, "k"); c.px(7, 7, "k")
    c.rect(1, 9, 3, 1, "S"); c.rect(9, 9 - f, 3, 1, "S")                    # flippers
    c.px(6, 10, "S")


def puffin_chick(c, f):
    c.disc(6, 6, 4, "k"); c.disc(6, 7, 3, "w", 2.5); c.disc(6, 4, 2, "w", 1.5); c.px(5, 4, "k")
    c.rect(8, 4, 3, 2, "Y"); c.px(10, 4, "r")                               # bright beak
    c.rect(2, 6 - f, 2, 3, "k")
    c.px(5, 11, "Y"); c.px(7, 11, "Y")


def pearl_snail(c, f):
    c.rect(1, 9, 10, 2, "j"); c.px(10 + f, 8, "j"); c.px(11, 7, "m")
    c.disc(5, 6, 4, "t", 3.5); c.disc(5, 6, 2, "m", 2); c.px(5, 6, "w"); c.px(3, 4, "w")


def reef_axolotl(c, f):
    c.rect(2, 6, 8, 3, "m"); c.rect(7, 4, 4, 4, "m"); c.px(9, 5, "k"); c.px(10, 7, "j")
    c.px(7, 3, "j"); c.px(8, 2 + f, "Y"); c.px(10, 3, "j"); c.px(11, 2 + f, "Y")    # coral-coloured gills
    c.rect(0, 7 - f, 2, 1, "m"); c.px(3, 9, "j"); c.px(7, 9, "j")


def moon_jelly(c, f):
    c.disc(6, 4, 5, "C", 3.5); c.disc(6, 4, 4, "c", 2.5)
    for (x, y) in ((4, 3), (8, 3), (4, 5), (8, 5)):
        c.px(x, y, "m")                                                     # the four rings
    c.rect(1, 6, 11, 1, "C")
    for i, x in enumerate((3, 5, 7, 9)):
        c.rect(x, 7, 1, 3 + (i + f) % 2 * 2, "w" if i % 2 else "c")


def hermit_crab(c, f):
    c.disc(4, 6, 4, "t", 3.5); c.disc(4, 6, 2, "o", 2); c.px(4, 6, "t")   # borrowed shell
    c.rect(7, 7, 4, 3, "r"); c.px(9, 5, "k"); c.px(10, 5, "k"); c.rect(9, 6, 1, 1, "r"); c.rect(10, 6, 1, 1, "r")
    c.rect(11, 6 - f, 1, 2, "r")                                            # a waving claw
    for x in (6, 8, 10):
        c.px(x, 11, "R"); c.px(x + (f if x == 8 else 0), 10, "r")


def sea_owl(c, f):
    c.disc(6, 6, 5, "d", 4.5); c.disc(6, 7, 4, "b", 3)
    c.disc(4, 5, 2, "w"); c.disc(8, 5, 2, "w"); c.px(4, 5, "k"); c.px(8, 5, "k")   # big round eyes
    c.px(6, 8, "Y")
    c.rect(0, 5 + f, 2, 2, "d"); c.rect(10, 5 + f, 2, 2, "d")


def sea_turtle(c, f):
    c.disc(5, 6, 4, "o", 3); c.disc(5, 6, 3, "E", 2); c.px(4, 5, "v"); c.px(6, 6, "v"); c.px(5, 4, "e")
    c.rect(9, 5, 3, 2, "e"); c.px(10, 5, "k")
    c.rect(1, 2 + f, 3, 2, "e"); c.rect(6, 9 - f, 3, 2, "e")               # swimming flippers
    c.rect(1, 9 - f, 2, 1, "e")


OCEAN_LIST = [("Sea Moth", sea_moth), ("Lantern Cat", lantern_cat), ("Seal Pup", seal_pup), ("Puffin Chick", puffin_chick),
         ("Pearl Snail", pearl_snail), ("Reef Axolotl", reef_axolotl), ("Moon Jelly", moon_jelly),
         ("Hermit Crab", hermit_crab), ("Sea Owl", sea_owl), ("Sea Turtle", sea_turtle)]


ORDER = ["orbit_moth", "drone_cat", "rover_pup", "comet_finch", "crystal_snail", "nebula_axolotl", "signal_jelly",
         "gear_beetle", "star_owl", "moss_tortoise"]
DRAW = {"forest": dict(zip(ORDER, (fn for _, fn in FOREST_LIST))), "ocean": dict(zip(ORDER, (fn for _, fn in OCEAN_LIST)))}


def world_frames(world, species):
    fn = DRAW.get(world, {}).get(species)
    return frames(fn) if fn else None
