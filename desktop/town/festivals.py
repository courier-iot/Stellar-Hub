"""v0.14.1: festivals. One in every season of every world, and a big finale in each special season.

- Regular seasons: a 3-day festival in the middle of the month (the 12th to the 14th).
- Special seasons (Starfall, Wild Magic, Storm Season): a 4-day finale (the 20th to the 23rd) with even more events.
- While a festival runs: decorations go up across the town, a festival visitor and a trader arrive,
  and the resident can `celebrate` once a day at the festival's place for credits and a keepsake.
"""
import datetime
import random
import time

from .buildings import BUILDINGS

REGULAR_DAYS = (12, 14)
FINALE_DAYS = (20, 23)

# world -> season -> (title, what happens, where to celebrate, decorations, signature event during it)
FESTIVALS = {
    "moon": {
        "spring": ("🌱 Seedling Day", "Everyone plants something new and the greenhouse is open late.", "greenhouse", "bunting", "stardust"),
        "summer": ("☀️ Sunfire Fair", "Games and music in the park under the long bright days.", "park", "bunting", None),
        "autumn": ("🍂 Harvest Moon", "The year's harvest is shared and the big moon rises copper.", "store", "lanterns", "trader"),
        "winter": ("❄️ Long Night Lights", "Lights in every window and a long night of stories on the radio.", "radio_tower", "lights", None),
        "special": ("☄️ The Great Starfall", "The comet stream peaks: the sky fills with falling stars.", "park", "stars", "meteor_shower"),
    },
    "forest": {
        "spring": ("🌸 Blossom Dance", "Petals fall like snow and everyone dances in the glade.", "park", "petals", "stardust"),
        "summer": ("✨ Firefly Night", "The fireflies gather in their thousands for one bright night.", "park", "stars", "meteor_shower"),
        "autumn": ("🏮 Lantern Festival", "Paper lanterns are hung through the trees to light the long evenings.", "post_office", "lanterns", "trader"),
        "winter": ("❄️ Frostlight Vigil", "Candles in the snow and stories by the fire to welcome the light back.", "home", "lights", None),
        "special": ("🌌 Night of a Thousand Wisps", "The wild magic peaks: wisps pour out of Whisper Woods and fill the sky.", "spaceport", "stars", "solar_storm"),
    },
    "ocean": {
        "spring": ("🐚 Shell Gathering", "The spring tides leave the best shells of the year on the sand.", "park", "bunting", "stardust"),
        "summer": ("⛵ Summer Regatta", "Boats race around the islands and flags fly from every mast.", "spaceport", "bunting", "trader"),
        "autumn": ("🎣 Harvest of the Tides", "The catch is shared at the market with music on the boardwalk.", "store", "lanterns", "trader"),
        "winter": ("🕯️ Beacon Night", "Every light is lit to guide the last ships home before the storms.", "radio_tower", "lights", None),
        "special": ("🌊 The Great Tide", "The storm season's biggest tide: the sea climbs higher than it has all year.", "radio_tower", "lights", "dust_storm"),
    },
}


def current(world, season_id, today=None):
    """The festival running today in this world, or None."""
    t = today or datetime.date.today()
    lo, hi = FINALE_DAYS if season_id == "special" else REGULAR_DAYS
    if not (lo <= t.day <= hi):
        return None
    title, about, place, decor, signature = FESTIVALS[world][season_id]
    return {"id": f"{world}-{season_id}-{t.year}-{t.month}", "title": title, "about": about, "place": place,
            "decor": decor, "signature": signature, "finale": season_id == "special", "day": t.day - lo + 1,
            "days": hi - lo + 1}


class FestivalMixin:
    def festival(self):
        from . import worlds
        f = current(worlds.current(), worlds.season_id())
        if f and not self.is_built(f["place"]):
            f["place"] = "home"
        return f

    def festival_turn(self):
        """Called every turn: opens a festival the first time it's seen (visitor, trader, a memory)."""
        f = self.festival()
        if not f or self.db.get("festival_seen") == f["id"]:
            return f
        self.db.set("festival_seen", f["id"])
        place = BUILDINGS[f["place"]]["name"]
        self.add_event("festival", f"{f['title']} has begun!", f"{f['about']} Celebrate at the {place}.")
        self.mem.add("observation", f"{f['title']} has begun: {f['about']} Everyone's gathering at the {place}.", f["place"], 7)
        try:
            if not self.visitor_now():
                self.maybe_visitor(force=True)
            if f["signature"] and not self.db.get("space_event"):
                self.start_space_event(f["signature"])
        except Exception:
            pass
        return f

    def festival_news(self):
        f = self.festival()
        if not f:
            return []
        place = BUILDINGS[f["place"]]["name"]
        done = self.db.get("celebrated") == self._today()
        return [f"FESTIVAL: {f['title']} (day {f['day']} of {f['days']}). {f['about']} "
                + ("You've celebrated today." if done else f"Join in: celebrate at the {place}.")]

    def festival_actions(self, bid):
        f = self.festival()
        if f and bid == f["place"] and self.db.get("celebrated") != self._today():
            return [("celebrate", "{\"how\": \"what you do to join in\"}  join the " + f["title"].split(" ", 1)[-1] + " festivities (once a day)")]
        return []

    def act_celebrate(self, a, imp):
        f = self.festival()
        if not f:
            return "There's no festival on right now."
        if self.db.get("celebrated") == self._today():
            return "I've already celebrated today. I'll enjoy the decorations."
        self.db.set("celebrated", self._today())
        how = str(a.get("how", "")).strip()[:200] or "joined in"
        reward = 40 if f["finale"] else 20
        self.earn(reward, f"celebrated {f['title'].split(' ', 1)[-1]}")
        keepsake = ""
        if random.random() < (0.6 if f["finale"] else 0.4):
            keepsake = " I came away with a keepsake: " + self.find_curio(f["title"].split(" ", 1)[-1])
        n = (self.db.get("festivals_joined") or 0) + 1
        self.db.set("festivals_joined", n)
        self.mem.add("observation", f"I celebrated {f['title']}: {how}.", f["place"], 8 if f["finale"] else 7)
        self.add_event("festival", f"🎉 {self.name} celebrated {f['title'].split(' ', 1)[-1]}", how)
        self.check_milestone("festival_first", "Celebrated a first festival", 25)
        return f"I celebrated {f['title']} ({how}) and earned {reward} credits.{keepsake}"
