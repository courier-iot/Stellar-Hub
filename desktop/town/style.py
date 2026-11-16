"""v0.13: accessories, building paint jobs and roof lights, space weather effects, traffic and building life."""
import random
import time

from . import sprites
from .workshop import PARTS

ACCESSORIES = {   # id: (name, price, what the resident might think of it)
    "antenna_cap": ("Antenna Cap", 30, "a cap with a little blinking antenna"),
    "beanie": ("Beanie", 25, "a warm red beanie"),
    "crown": ("Crown", 80, "a small golden crown"),
    "bubble_helmet": ("Bubble Helmet", 60, "a glassy bubble helmet"),
    "scarf": ("Scarf", 25, "a long green scarf that flaps as it walks"),
    "comet_trail": ("Comet Trail", 120, "a sparkling trail of comet dust"),
}
PAINTS = {   # id: (name, dark shade, light shade) in the shared palette
    "dusk": ("Dusk Blue", "N", "c"), "forest": ("Forest", "E", "e"), "ember": ("Ember", "R", "y"),
    "lilac": ("Lilac", "P", "p"), "rust": ("Rust", "O", "o"), "steel": ("Steel", "g", "c"),
    "rose": ("Rose", "M", "m"), "silver": ("Silver", "S", "s"),
}
ROOF_LIGHTS = {"red": "#ff5d73", "gold": "#ffd86b", "cyan": "#5ef2ff", "green": "#4fe0a5", "magenta": "#ff4fd8", "white": "#eef1ff"}
PAINT_PRICE = 40
_SKIP = set(".kwtyYnc") | {"g"}      # outlines, glass and window glows stay as they are


def _lum(ch):
    h = sprites.PALETTE.get(ch, "#000000").lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.3 * r + 0.59 * g + 0.11 * b


def apply_paint(rows, paint):
    """Recolours a building sprite: its two most common wall shades become the paint job's dark and light shades."""
    if paint not in PAINTS:
        return rows
    count = {}
    for r in rows:
        for ch in r:
            if ch not in _SKIP:
                count[ch] = count.get(ch, 0) + 1
    top = sorted(count, key=lambda c: -count[c])[:2]
    if not top:
        return rows
    top.sort(key=_lum)
    _, dark, light = PAINTS[paint]
    swap = {top[0]: dark} if len(top) == 1 else {top[0]: dark, top[1]: light}
    return ["".join(swap.get(ch, ch) for ch in r) for r in rows]


class StyleMixin:
    # ------------------------------------------------------------ accessories
    def accessories(self):
        return self.db.get("accessories", [])

    def wearing(self):
        w = self.db.get("wearing")
        return w if w in self.accessories() else None

    def act_buy_accessory(self, a, imp):
        item = str(a.get("item", "")).strip().lower().replace(" ", "_")
        if item not in ACCESSORIES:
            return f"The store doesn't sell '{item}'. Accessories: " + ", ".join(f"{k} ({v[1]})" for k, v in ACCESSORIES.items())
        if item in self.accessories():
            return f"I already own the {ACCESSORIES[item][0]}."
        name, price, desc = ACCESSORIES[item]
        if not self.spend(price, f"bought a {name}"):
            return f"I can't afford the {name} ({self.credits()}/{price} credits)."
        self.db.set("accessories", self.accessories() + [item])
        self.db.set("wearing", item)
        self.mem.add("observation", f"I bought {desc} and put it on.", "store", 6)
        self.add_event("style", f"🎩 {self.name} bought a {name}", desc)
        return f"I bought the {name} for {price} credits and I'm wearing it now!"

    def act_wear(self, a, imp):
        item = str(a.get("item", "")).strip().lower().replace(" ", "_")
        if item in ("none", "nothing", ""):
            self.db.set("wearing", None)
            return "I took my accessory off."
        if item not in self.accessories():
            return f"I don't own that. I own: {', '.join(self.accessories()) or 'nothing yet'}."
        self.db.set("wearing", item)
        return f"I'm wearing my {ACCESSORIES[item][0]} now."

    # ------------------------------------------------------------ paint jobs
    def paints(self):
        return self.db.get("paints", {})

    def act_paint_building(self, a, imp):
        bid = self.resolve_building(str(a.get("building", "")).strip().lower()) if hasattr(self, "resolve_building") else \
            str(a.get("building", "")).strip().lower()
        if not bid or not self.is_built(bid):
            return "I can only paint a building that's been built."
        paint = str(a.get("paint", "")).strip().lower()
        light = str(a.get("roof_light", "")).strip().lower() or None
        if paint not in PAINTS and paint not in ("original", "none"):
            return "Paint jobs: " + ", ".join(PAINTS) + " (or original). Roof lights: " + ", ".join(ROOF_LIGHTS)
        if light and light not in ROOF_LIGHTS:
            light = None
        if not self.spend(PAINT_PRICE, f"painted the {bid.replace('_', ' ')}"):
            return f"A paint job costs {PAINT_PRICE} credits and I have {self.credits()}."
        ps = self.paints()
        ps[bid] = {"paint": None if paint in ("original", "none") else paint, "light": light or (ps.get(bid) or {}).get("light")}
        self.db.set("paints", ps)
        label = PAINTS.get(paint, ("its original colours",))[0]
        self.mem.add("observation", f"I painted the {bid.replace('_', ' ')} {label}" + (f" with a {light} roof light." if light else "."), bid, 5)
        self.add_event("style", f"🎨 {self.name} repainted the {bid.replace('_', ' ')}", label)
        return f"The {bid.replace('_', ' ')} is {label} now" + (f", with a {light} roof light." if light else ".")

    def style_shop_text(self):
        return ("accessories (buy_accessory): " + ", ".join(f"{k} {v[1]}" for k, v in ACCESSORIES.items())
                + f"; paint jobs (paint_building, {PAINT_PRICE} each): " + ", ".join(PAINTS)
                + "; roof lights: " + ", ".join(ROOF_LIGHTS)
                + "; workshop parts: " + ", ".join(f"parts:{k} ({v[0]})" for k, v in PARTS.items()))

    # ------------------------------------------------------------ weather
    def weather(self):
        ev = self.db.get("space_event")
        return ev["type"] if ev and ev.get("end", 0) > time.time() else None

    def walkway_closed(self):
        return self.weather() == "dust_storm"

    def weather_turn(self):
        w = self.weather()
        if w == "stardust" and random.random() < 0.25:
            self.earn(random.randint(1, 3), "swept up drifting stardust")
        elif w == "comet" and random.random() < (0.35 if self.machine_working("comet_catcher") else 0.08):
            from .curio_sets import SETS, piece_ids
            sid = random.choice(list(SETS))
            cid = random.choice(piece_ids(sid))
            col = self.collection()
            first = cid not in col
            col[cid] = col.get(cid, 0) + 1
            self.db.set("curios", col)
            if first:
                self.note_curio(cid, "the comet's tail")
            self.add_event("curio", f"☄️ {self.name} caught a set piece from the comet", cid)

    # ------------------------------------------------------------ the living colony
    def traffic(self):
        built = len([b for b in self.draw_layout().values() if b]) if isinstance(self.draw_layout(), dict) else 0
        recent = self.db.q("SELECT COUNT(*) AS n FROM ledger WHERE amount < 0 AND ts > ?", (time.time() - 86400,))[0]["n"]
        d = self.db.get("delivery") or {}
        return {"bots": 1 + built // 6, "drones": min(4, recent // 3 + (1 if built >= 8 else 0)),
                "shuttle": self.is_built("spaceport"), "lift": self.upper_state() == "open",
                "delivery": d.get("to") if time.time() - d.get("ts", 0) < 3600 else None,
                "machines": len([m for m in self.machines() if m["condition"] > 0])}
