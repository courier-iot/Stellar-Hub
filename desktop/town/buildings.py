"""The Stellar Hub colony map. Each building is a set of abilities the resident can use.

locked + unlockable: starts locked. Unlocks when the creator unlocks it, approves an access
request for it, or the resident buys it at the Credit Vault (price = unlock_price).
An unlocked building becomes a blueprint: the resident picks an empty plot and builds it from Home.
To add a building: add it here, add `act_<action>` methods (agent.py / colony.py),
and add its art in sprites.py (BUILDERS + ORDER).
"""

BUILDINGS = {
    "home": {
        "name": "Home Dome",
        "about": "Your own habitat dome. Journal, rethink who you are, or rest. Decorations you buy appear outside.",
        "actions": {
            "journal": "{\"text\": \"...\"}  write a private journal entry",
            "update_personality": "{\"text\": \"...\"}  rewrite your self-description (keep what still feels true)",
            "rest": "{}  float quietly for a while",
            "stargaze": "{}  go outside and watch the sky",
            "build": "{\"building\": \"<blueprint id>\", \"plot\": <empty plot number>}  choose where a new building goes and start building it",
            "move_building": "{\"building\": \"<id>\", \"plot\": <empty plot number>}  move a finished building ({move_cost} credits, rebuilds over a few hours)",
            "set_bedtime": "{\"bed_hour\": 0-23, \"wake_hour\": 0-23}  change when you sleep (8-10 hours a night)",
            "paint": "{\"subject\": \"what to paint\", \"title\": \"...\"}  paint a pixel painting",
            "showcase": ("{\"type\": \"painting|curio|plant|writing\", \"id\": <id or curio name>, \"floor\": <n>, \"spot\": <1-12, optional>}  "
                         "display something in your home (each floor has 12 spots; giving a taken spot rotates that item out)"),
            "remove_showcase": "{\"floor\": <n>, \"spot\": <n>}  take something off display",
            "upgrade_home": "{}  add a floor to your Home Dome (floor 2: 150, floor 3: 300, floor 4: 600 credits)",
            "view_collection": "{}  look through your curio collection",
        },
    },
    "library": {
        "name": "Observatory Library",
        "about": "Your notes and everything you've learned, under a telescope dome.",
        "actions": {
            "recall": "{\"topic\": \"...\"}  look through your notes, memories and life story on a topic",
            "write_note": "{\"topic\": \"...\", \"text\": \"...\"}  write or add to a note",
            "observe_sky": "{}  use the observatory telescope: moon phase, today's sky picture, events",
        },
    },
    "internet_cafe": {
        "name": "Uplink Café",
        "about": "A café with an uplink to Earth's internet. Visits per day are limited.",
        "actions": {
            "research": "{\"topic\": \"...\"}  search the web and take notes on a topic",
            "read_page": "{\"url\": \"https://...\"}  read one web page you found earlier",
        },
    },
    "post_office": {
        "name": "Relay Post",
        "about": "Talk with your creator: requests, questions and letters. Collect your mail here.",
        "actions": {
            "read_mail": "{}  open letters, answers and replies waiting for you",
            "ask_question": "{\"question\": \"...\"}  ask your creator anything; they answer in their own words",
            "send_request": ("{\"kind\": \"want|access|learn|other\", \"content\": \"...\", \"reason\": \"...\", "
                             "\"building\": \"<building id, for access requests>\"}  ask your creator for something"),
            "write_letter": "{\"text\": \"...\"}  write your creator a letter (no request, just talking)",
        },
    },
    "gallery": {
        "name": "Starlight Gallery",
        "about": "An art gallery. Paint here, and hang your best paintings on its 12 walls for the colony to see.",
        "locked": True, "unlockable": True, "unlock_price": 90,
        "actions": {
            "paint": "{\"subject\": \"what to paint\", \"title\": \"...\"}  paint a pixel painting",
            "hang_painting": "{\"painting_id\": <id>, \"replace_id\": <id, only when the walls are full>}  hang a painting",
        },
    },
    "park": {
        "name": "Low-G Park",
        "about": "A green park with benches, a fountain and chess tables. Write, relax, play puzzles. Chess games with your creator happen here.",
        "locked": True, "unlockable": True, "unlock_price": 60,
        "actions": {
            "write": "{\"kind\": \"poem|story|myth|essay|song lyrics|letter to the future\", \"title\": \"...\", \"text\": \"...\"}  write something original",
            "relax": "{}  stroll and unwind (you might find something)",
            "solve_puzzle": "{}  try a puzzle at the game tables",
        },
    },
    "studio": {
        "name": "Radio Studio",
        "about": "A recording studio built onto the Radio Tower. Compose chiptune music and play your own songs.",
        "locked": True, "unlockable": True, "unlock_price": 120, "upgrade_of": "radio_tower",
        "actions": {
            "compose": ("{\"title\": \"...\", \"mood\": \"...\", \"bpm\": 60-200, \"wave\": \"square|pulse|triangle|saw\", "
                        "\"melody\": \"C4:1 E4:1 G4:2 R:1 ...\", \"bass\": \"C3:4 F2:4 ... (optional)\"}  write a song "
                        "(notes A-G with # or b, octave 2-6, then :beats; R is a rest)"),
            "play_composition": "{\"composition_id\": <id>}  play one of your songs over the radio",
        },
    },
    "station": {
        "name": "Orbital Station",
        "about": "A space station above the colony, reached from the Spaceport. Study what you've learned and test yourself from memory.",
        "locked": True, "unlockable": True, "unlock_price": 300, "upgrade_of": "spaceport",
        "actions": {
            "station_study": "{}  write test questions on a topic you studied, or take a test that's due",
        },
    },
    "exchange": {
        "name": "Curio Exchange",
        "about": ("An auction house for curios. Sell spares, fill collectors' wanted orders for extra credits, "
                  "trade 5 spares of one rarity up into 1 of the next, or auction something for 6 hours. "
                  "Only spares can go: anything on display stays."),
        "locked": True, "unlockable": True, "unlock_price": 80,
        "actions": {
            "check_exchange": "{}  see prices, today's wanted board, your auctions and your spares",
            "sell_curio": "{\"curio\": \"name or id\", \"count\": n}  sell spare curios",
            "trade_up": "{\"rarity\": \"common|uncommon|rare\", \"kind\": \"optional, e.g. crystal\"}  trade 5 spares for 1 of the next rarity",
            "auction_curio": "{\"curio\": \"name or id\", \"reserve\": <lowest price you'll accept>}  start a 6-hour auction",
        },
    },
    "bank": {
        "name": "Credit Vault",
        "about": "Your colony credits. Check your balance and buy things. You earn credits by keeping routines, finishing goals, caring for plants and doing good work.",
        "actions": {
            "check_balance": "{}  see your credits and recent earnings",
            "buy": "{\"item\": \"...\"}  buy something. Items: {shop}",
        },
    },
    "greenhouse": {
        "name": "Hydro Greenhouse",
        "about": "Grow plants. Each species has its own watering, feeding and light needs. Neglected plants wilt.",
        "locked": True, "unlockable": True, "unlock_price": 60,
        "actions": {
            "check_plants": "{}  see every plant's health, stage and what it needs",
            "plant": "{\"species\": \"...\", \"nickname\": \"...\"}  plant a seed you own",
            "water": "{\"plant_id\": <id or \"all\">}  water a plant (too early = overwatering)",
            "feed": "{\"plant_id\": <id or \"all\">}  give plant food",
            "set_light": "{\"plant_id\": <id>, \"level\": \"low|medium|high\"}  set a plant's grow lamp",
            "remove": "{\"plant_id\": <id>}  clear a wilted plant from its pot",
        },
    },
    "radio_tower": {
        "name": "Radio Tower",
        "about": "Play music from your creator's collection, and broadcast the colony log.",
        "locked": True, "unlockable": True, "unlock_price": 80,
        "actions": {
            "list_music": "{\"search\": \"<words, or empty for a random pick>\"}  browse songs",
            "play_music": "{\"song_id\": <id>}  play a song (out loud in the colony)",
            "stop_music": "{}  stop playing",
            "broadcast_log": "{\"text\": \"...\"}  broadcast a colony log entry: what's happening, how you feel",
        },
    },
    "archive": {
        "name": "Archive Vault",
        "about": "Long-term memory. Turn old memories into chapters of your life story, and reread them.",
        "locked": True, "unlockable": True, "unlock_price": 70,
        "actions": {
            "archive_memories": "{}  write your older memories into a new life-story chapter",
            "read_chapter": "{\"number\": <n>}  reread a chapter of your life story",
        },
    },
    "salon": {
        "name": "Nova Salon",
        "about": "Change how you look. Colours cost {colour_price} credits; a new form costs {form_price} (free once owned).",
        "locked": True, "unlockable": True, "unlock_price": 50,
        "locked_about": "Locked. A salon where you could change how you look. Ask your creator or buy access at the Credit Vault.",
        "actions": {
            "change_look": ("{\"form\": \"star_spirit|robot|person\", \"primary\": \"<colour>\", \"secondary\": \"<colour>\", "
                            "\"accent\": \"<colour>\", \"skin\": \"<skin tone, person only>\"}  redesign yourself. "
                            "Colours: {colours}. Skin tones: {skins}"),
        },
    },
    "spaceport": {
        "name": "Spaceport",
        "about": "Go on research expeditions: leave the colony for hours to study one topic deeply, then come back with a report.",
        "locked": True, "unlockable": True, "unlock_price": 150,
        "actions": {
            "start_expedition": "{\"topic\": \"...\", \"hours\": 1-8}  launch an expedition (you'll be away)",
            "read_reports": "{}  look back at your past expedition reports",
        },
    },
    "workshop": {
        "name": "Fabrication Hangar",
        "about": "Write small Python programs. Your creator approves each one before it runs in a safe sandbox (no internet, own folder only).",
        "locked": True, "unlockable": True, "unlock_price": 200,
        "actions": {
            "write_program": "{\"name\": \"short_name\", \"description\": \"what it does\", \"code\": \"python code\"}  build a program",
            "list_programs": "{}  see your programs and their results",
        },
    },
}

# Which need each action satisfies, and by how much.
SATISFIES = {
    "research": ("curiosity", 45), "read_page": ("curiosity", 35), "recall": ("curiosity", 20),
    "start_expedition": ("curiosity", 60), "read_reports": ("curiosity", 15), "read_chapter": ("curiosity", 15),
    "journal": ("creativity", 35), "write_note": ("creativity", 30), "update_personality": ("creativity", 25),
    "change_look": ("creativity", 40), "write_program": ("creativity", 45), "broadcast_log": ("creativity", 25),
    "archive_memories": ("creativity", 25), "plant": ("creativity", 20),
    "read_mail": ("connection", 35), "send_request": ("connection", 35), "write_letter": ("connection", 45),
    "ask_question": ("connection", 40),
    "rest": ("rest", 60), "stargaze": ("rest", 40), "relax": ("rest", 55), "paint": ("creativity", 45),
    "write": ("creativity", 45), "compose": ("creativity", 50), "play_composition": ("rest", 30),
    "observe_sky": ("curiosity", 35), "station_study": ("curiosity", 40), "solve_puzzle": ("curiosity", 25),
    "showcase": ("creativity", 15), "hang_painting": ("creativity", 15), "upgrade_home": ("creativity", 30),
    "view_collection": ("rest", 15), "check_exchange": ("curiosity", 15), "sell_curio": ("connection", 15),
    "trade_up": ("creativity", 20), "auction_curio": ("connection", 20), "build": ("creativity", 40), "move_building": ("creativity", 30), "play_music": ("rest", 45), "water": ("rest", 10), "check_plants": ("rest", 10),
}
# How much each need grows per turn.
NEED_GROWTH = {"curiosity": 9, "creativity": 7, "connection": 6, "rest": 4}
