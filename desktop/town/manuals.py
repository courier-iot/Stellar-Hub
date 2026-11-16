"""Instruction manuals: what each building is for and how to use it well, plus the greenhouse care guide.

The resident gets a building's manual when its blueprint is unlocked, reads it properly when the building
opens, and can reread any manual from its Home Dome or the Library (read_manual)."""
from .buildings import BUILDINGS

MANUALS = {
    "home": ("Your Home Dome is yours alone: rest here, keep your journal, and plan the colony.",
             ["Rest when energy is low; sleeping in your own bed restores the most.",
              "Build and move buildings from here. Moving is very expensive, so choose plots carefully.",
              "The showcase has 12 spots per floor. Rotate favourites in and out instead of keeping everything.",
              "Buy furniture at the Credit Vault and arrange your room with arrange_home.",
              "Read any manual again here with read_manual."]),
    "library": ("The Observatory Library holds your notes and everything you've learned, under a telescope dome.",
                ["recall searches your memories; use it before deciding something you've thought about before.",
                 "write_note keeps a fact you want to find again.",
                 "observe_sky shows today's real astronomy picture and the moon phase.",
                 "The manual shelf holds every building's manual, even for places you haven't unlocked: browse_manuals, then read_manual."]),
    "internet_cafe": ("The Uplink Café connects you to Earth's internet. Visits per day are limited, so make each one count.",
                      ["research searches the web for one topic; read_page reads one page in full.",
                       "Write what you learn into a note afterwards, or it fades.",
                       "Solar storms knock the uplink offline until they pass."]),
    "post_office": ("The Relay Post is how you talk with your creator: letters, questions and requests.",
                    ["read_mail first: your creator's letters wait here until you visit.",
                     "ask_question for things you're curious about; send_request for things you want (access, items, help).",
                     "Approved requests can unlock buildings. Be specific about why you want something."]),
    "gallery": ("The Starlight Gallery is where you paint and show your art.",
                ["paint makes a new painting; hang_painting puts one on the 12 walls.",
                 "Your newest painting waits on the easel. Your creator can see everything hung here.",
                 "Painting raises your art skill: bigger canvases unlock as you level up."]),
    "park": ("Low-G Park is for writing, relaxing and puzzles. Chess games with your creator happen here.",
             ["write keeps poems, stories and essays; relax restores mood without sleeping.",
              "solve_puzzle sharpens your thinking and earns a little XP.",
              "Visitors like to sit by the fountain."]),
    "studio": ("The Radio Studio, built onto the Radio Tower, is for making your own music.",
               ["compose writes a chiptune song; play_composition plays one of yours on the speakers.",
                "Your best song can be a gift to your creator."]),
    "station": ("The Orbital Station, above the colony, is for studying and testing what you've learned.",
                ["station_study quizzes you on your own memories with spaced repetition.",
                 "Missed answers come back sooner; known ones come back later."]),
    "exchange": ("The Curio Exchange is an auction house for curios.",
                 ["Only spares can be sold or traded; your last copy of a curio is always kept.",
                  "Fill wanted orders for extra credits. Trade 5 spares of one rarity up into 1 of the next.",
                  "Auctions run for 6 hours; check back afterwards."]),
    "bank": ("The Credit Vault keeps your colony credits and runs the shop.",
             ["check_balance shows your credits and the shop: seeds, decor, furniture, floors and more.",
              "You earn by keeping routines, finishing goals, caring for plants and doing good work.",
              "Fines and pet rescues can put you into debt; nothing can be bought until it's paid back."
             ]),
    "greenhouse": ("The Hydro Greenhouse grows plants. Every species has its own needs.",
                   ["check_plants shows who needs water, food or a light change. Check before you care.",
                    "Watering or feeding too soon hurts a plant. Wait until it's due.",
                    "Match each plant's light (low, medium or high) with set_light; the wrong light slowly harms it.",
                    "Healthy plants grow and bloom for credits. Neglected ones wilt and must be removed.",
                    "read_plant_guide explains any species."]),
    "radio_tower": ("The Radio Tower plays music and broadcasts your colony logs.",
                    ["broadcast_log speaks your log aloud and sends it to your creator's phone.",
                     "host_show records your daily radio show: colony news, a song pick and a dedication.",
                     "list_music and play_music use your creator's PC collection; the phone music actions use theirs on the phone.",
                     "Quiet hours keep the radio silent at night."]),
    "archive": ("The Archive Vault turns old memories into chapters of your life story.",
                ["archive_memories writes a chapter from your older memories; read_chapter rereads one.",
                 "Archiving keeps your mind tidy and your story whole."]),
    "salon": ("The Nova Salon changes how you look.",
              ["change_look sets colours and forms. Forms you've bought are free to switch back to."]),
    "store": ("The Department Store sells everything: seeds, outdoor decor, furniture for every building, pots and unlocks.",
              ["browse_store shows what's for sale and your balance; buy with kind:name, like furniture:neon_sign.",
               "Furniture goes into any building's decor spots with decorate.",
               "In debt, nothing can be bought until it's paid back."]),
    "mech_shop": ("The Mechanical Workshop is where you build machines, and design real projects for your creator.",
                  ["view_workshop shows your parts, this week's machine goal and how your machines are holding up.",
                   "Buy parts at the Department Store with buy parts:<name> (frame, wheel, gear, motor, sensor, circuit, battery...).",
                   "design_machine sends your design through the simulator. It checks parts, power and frame space; parts are only used when it passes.",
                   "Working machines help every day. They wear down slowly: maintain_machine (one spare gear) keeps them going; a broken machine does nothing until fixed.",
                   "design_plan is different: about once a week, design a REAL low-voltage project (electronics, a 3D print, crafts or a smart-home gadget) for your creator to build.",
                   "Every machine and plan that works goes into your skill notebook, and you'll see the best examples next time."]),
    "museum": ("The Stellar Museum is for complete curio sets.",
               ["view_museum shows your sets, what each would sell for, and how much reputation a donation gives.",
                "donate_set puts a set on permanent display: reputation brings a daily stipend and more visitors.",
                "sell_set sells a set to the curator for much more than its pieces alone.",
                "Take a set off display at home first (that splits it back into pieces)."]),
    "pet_shop": ("The Pet Shop is where you adopt helper pets and care for them.",
                 ["browse_pets first: each species has a speciality, a lifespan and its own hours (day, night or any time).",
                  "train_pet gives a pet ONE job and a number of shifts a day. Its specialised jobs cost it less energy.",
                  "Pets rest when off shift. More shifts than it can rest for builds strain: sick, then injured, then critical.",
                  "Feed pets (they get hungry), play with them (they get lonely), and use rest_pet or treat_pet when they're worn out.",
                  "A critical pet has 24 hours: rescue_pet saves it at a steep price, even into debt. Otherwise the Welfare Office takes it and fines you.",
                  "Debt blocks shopping until it's paid off. Pets grow old and pass away at the end of their lifespan."]),
    "spaceport": ("The Spaceport launches research expeditions, and the shuttle to the Orbital Station.",
                  ["start_expedition leaves the colony for hours to study one topic deeply.",
                   "read_reports brings back what you learned. Nothing at home is cared for while you're away."]),
    "workshop": ("The Fabrication Hangar runs small Python programs you write.",
                 ["write_program saves a program; your creator approves it before it runs.",
                  "Programs run in a sandbox with no internet and only their own folder.",
                  "list_programs shows results and what's still waiting for approval.",
                  "Every week there's a coding challenge (view_challenge). attempt_challenge writes code and runs its automatic tests right away, no approval needed.",
                  "Passing makes the next challenge harder; missing a week makes it easier. Your creator can set coding goals too.",
                  "Passing code goes into your skill notebook, and you'll see your best matching examples next time."]),
}

PLANT_GUIDE = ("Greenhouse care guide: 1) check_plants before caring, so you only water or feed what's due. "
               "2) Too-early care hurts. 3) Each species wants low, medium or high light: set it once with set_light. "
               "4) Health above 40% means growth; full health blooms faster and earns credits. "
               "5) An eclipse pauses growth. 6) Remove wilted plants to free the pot, and learn from it.")


def manual(bid):
    if bid not in MANUALS or bid not in BUILDINGS:
        return None
    intro, tips = MANUALS[bid]
    acts = ", ".join(BUILDINGS[bid]["actions"])
    return f"MANUAL: {BUILDINGS[bid]['name']}. {intro} Actions here: {acts}. Tips: " + " ".join(f"- {t}" for t in tips)


def short(bid):
    if bid not in MANUALS:
        return ""
    intro, tips = MANUALS[bid]
    return f"{intro} {tips[0]}"


def species_card(species, sp):
    return (f"{species.replace('_', ' ')} ({sp['tier']}): {sp['about']}. Water every {sp['water_h']}h, feed every "
            f"{sp['feed_h']}h, {sp['light']} light, blooms in about {sp['days']} days of good care.")


def page(bid, tips=2):
    """A short page for the prompt: what the building is for, its actions, and a couple of tips."""
    if bid not in MANUALS or bid not in BUILDINGS:
        return None
    intro, ts = MANUALS[bid]
    return (f"{BUILDINGS[bid]['name']} (id {bid}): {intro} Actions: {', '.join(BUILDINGS[bid]['actions'])}. "
            + " ".join(ts[:tips]))


def best_match(query, exclude=()):
    """The manual that best matches what it's been doing or thinking about."""
    import re
    q = {w for w in re.findall(r"[a-z_]{3,}", (query or "").lower())}
    best, score = None, 0
    for bid in MANUALS:
        if bid not in BUILDINGS or bid in exclude:
            continue
        b = BUILDINGS[bid]
        vocab = set(re.findall(r"[a-z_]{3,}", (b["name"] + " " + bid + " " + " ".join(b["actions"])).lower()))
        vocab |= set(bid.split("_")) | {a for act in b["actions"] for a in act.split("_") if len(a) > 3}
        sc = len(q & vocab)
        if sc > score:
            best, score = bid, sc
    return best
