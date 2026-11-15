"""The Stellar Hub colony map. Each building is a set of abilities the resident can use.

locked + unlockable: starts locked. Unlocks when the creator unlocks it, approves an access
request for it, or the resident buys it at the Credit Vault (price = unlock_price).
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
        },
    },
    "library": {
        "name": "Observatory Library",
        "about": "Your notes and everything you've learned, under a telescope dome.",
        "actions": {
            "recall": "{\"topic\": \"...\"}  look through your notes, memories and life story on a topic",
            "write_note": "{\"topic\": \"...\", \"text\": \"...\"}  write or add to a note",
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
    "rest": ("rest", 60), "play_music": ("rest", 45), "water": ("rest", 10), "check_plants": ("rest", 10),
}
# How much each need grows per turn.
NEED_GROWTH = {"curiosity": 9, "creativity": 7, "connection": 6, "rest": 4}
