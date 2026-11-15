"""The Stellar Hub colony map. Each building is a set of abilities the resident can use.

locked + unlockable: the creator can unlock it from the dashboard or phone.
locked + not unlockable: still under construction (no code yet).
To add a building: add it here, add `act_<action>` methods in agent.py,
and add its art in sprites.py (BUILDERS + ORDER).
"""

BUILDINGS = {
    "home": {
        "name": "Home Dome",
        "about": "Your own habitat dome. Write in your journal, rethink who you are, or rest.",
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
            "recall": "{\"topic\": \"...\"}  look through your notes and memories on a topic",
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
        "about": "Send requests and letters to your creator, and collect your mail.",
        "actions": {
            "read_mail": "{}  open letters and replies waiting for you",
            "send_request": "{\"kind\": \"want|access|learn|other\", \"content\": \"...\", \"reason\": \"...\"}  ask your creator for something",
            "write_letter": "{\"text\": \"...\"}  write your creator a letter (no request, just talking)",
        },
    },
    "salon": {
        "name": "Nova Salon",
        "about": "A salon where you can change how you look: your form and your colours.",
        "locked": True,
        "unlockable": True,
        "locked_about": "Locked. A salon where you could change how you look. Ask your creator for access.",
        "actions": {
            "change_look": ("{\"form\": \"star_spirit|robot|person\", \"primary\": \"<colour>\", \"secondary\": \"<colour>\", "
                            "\"accent\": \"<colour>\", \"skin\": \"<skin tone, person only>\"}  redesign yourself. "
                            "Colours: {colours}. Skin tones: {skins}"),
        },
    },
    "bank": {
        "name": "Credit Vault",
        "about": "Under construction. It will hold your own money someday.",
        "locked": True,
        "actions": {},
    },
    "workshop": {
        "name": "Fabrication Hangar",
        "about": "Under construction. It will let you build and make things someday.",
        "locked": True,
        "actions": {},
    },
}

# Which need each action satisfies, and by how much.
SATISFIES = {
    "research": ("curiosity", 45), "read_page": ("curiosity", 35), "recall": ("curiosity", 20),
    "journal": ("creativity", 35), "write_note": ("creativity", 30), "update_personality": ("creativity", 25),
    "change_look": ("creativity", 40),
    "read_mail": ("connection", 35), "send_request": ("connection", 35), "write_letter": ("connection", 45),
    "rest": ("rest", 60),
}
# How much each need grows per turn.
NEED_GROWTH = {"curiosity": 9, "creativity": 7, "connection": 6, "rest": 4}
