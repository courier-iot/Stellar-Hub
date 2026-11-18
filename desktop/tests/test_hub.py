"""Automatic tests for Stellar Hub. Run them with:  python -m unittest discover -s desktop/tests -v
GitHub runs these before every build; a failure stops the release."""
import json
import os
import shutil
import tempfile
import threading
import time
import unittest

from helpers import ROOT, call, finish_building, local_sandbox, make_agent

from town import interiors, manuals, sprites
from town.buildings import BUILDINGS
from town.economy import category
from town.memory import Memory


class TurnsAndChoices(unittest.TestCase):
    def setUp(self):
        self.a = make_agent()

    def test_turns_run(self):
        for _ in range(3):
            r = self.a.take_turn()
            self.assertIn("action", r)

    def test_building_titles_and_plots_are_understood(self):
        a = self.a
        self.assertEqual(a.resolve_building("uplink_cafe"), "internet_cafe")
        self.assertEqual(a.resolve_building("Uplink Café"), "internet_cafe")
        self.assertEqual(a.resolve_building("Uplink Cafe"), "internet_cafe")
        self.assertEqual(a.resolve_building("mechanical_workshop"), "mech_shop")
        self.assertIsNone(a.resolve_building("nonsense place"))
        a.take_turn()
        lay = a.layout() or {}
        plot, bid = next((p, b) for p, b in lay.items() if b)
        self.assertEqual(a.resolve_building(str(plot + 1)), bid)

    def test_wrong_building_for_an_action_is_repaired(self):
        bid, note = self.a.repair_choice("uplink_cafe", "journal")
        self.assertEqual(bid, "home")
        self.assertIn("home", note)

    def test_answers_are_held_to_real_buildings_and_actions(self):
        self.a.take_turn()
        sch = self.a.llm.last_schema
        places = sch["properties"]["building"]["enum"]
        self.assertIn("home", places)
        self.assertTrue(all(b in BUILDINGS for b in places))
        self.assertIn("journal", sch["properties"]["action"]["enum"])
        self.a.start_space_event("dust_storm")
        self.assertEqual(self.a.decision_schema()["properties"]["building"]["enum"], [self.a.db.get("location", "home")])

    def test_prompt_stays_a_sensible_size(self):
        ctx = self.a.build_context(self.a.db.get("needs") or {})
        self.assertLess(len(ctx) // 4, 7000, "the turn prompt is close to the model's 8,192-token window")
        self.assertIn("MANUAL SHELF", ctx)


class MemoryReach(unittest.TestCase):
    def test_old_memories_are_found(self):
        a = make_agent(0)
        old = a.mem.add("observation", "Courier showed me the Lagrange point trick while we played chess", "park", 8)
        for i in range(2500):
            a.mem.add("observation", f"I watered the plants, turn {i}", "greenhouse", 2)
        found = a.mem.relevant("Lagrange point chess", 5)
        self.assertEqual(found[0]["id"], old)

    def test_memories_from_before_the_index_get_indexed(self):
        a = make_agent(0)
        a.db.x("DELETE FROM memory_words")
        mid = a.db.x("INSERT INTO memories(ts, kind, building, content, importance) VALUES(?,?,?,?,?)",
                     (time.time() - 90 * 86400, "observation", "home", "my first ever zephyrine sunrise", 6))
        a.db.set("memidx_below", None)
        m = Memory(a.db)
        while (a.db.get("memidx_below") or 0) > 1:
            m.backfill()
        self.assertEqual(m.relevant("zephyrine sunrise", 3)[0]["id"], mid)


class Workshop(unittest.TestCase):
    def setUp(self):
        self.a = make_agent()
        local_sandbox(self.a)
        finish_building(self.a, "workshop", 2)
        finish_building(self.a, "mech_shop", 3)
        finish_building(self.a, "store", 4)

    def test_challenge_tests_pass_and_level_rises(self):
        a = self.a
        a.db.set("goals_week", None)
        a.goals_open()
        a.db.x("UPDATE goals SET ref='count_stars', tests=? WHERE kind='code'", ("assert count_stars('*.*') == 2",))
        out = a.act_attempt_challenge({}, 1)
        self.assertIn("passed", out)
        self.assertEqual(a.db.get("code_level"), 2)

    def test_failing_code_does_not_pass(self):
        gid = self.a.add_creator_goal("code", "Sum", "Write total(xs).", "assert total([1, 2]) == 3")
        self.assertIn("didn't pass", self.a.act_attempt_challenge({"goal_id": gid}, 1))

    def test_missing_sandbox_does_not_count_against_it(self):
        a = self.a
        a.sandbox_problem = lambda: "Docker isn't running."
        a.db.set("goals_week", None)
        a.goals_open()
        a.db.set("code_level", 3)
        self.assertIn("sandbox can't run tests", a.act_attempt_challenge({}, 1))
        a.db.set("goals_week", "2000-W01")       # a new week arrives
        a.db.set("sandbox_down_week", "2000-W01")
        a.ensure_weekly_goals()
        self.assertEqual(a.db.get("code_level"), 3)

    def test_simulator(self):
        ok, why = self.a.simulate("watering_bot", {"frame": 1, "wheel": 2, "pump": 1, "sensor": 1, "circuit": 1})
        self.assertFalse(ok)
        self.assertTrue(any("power" in w for w in why))
        ok, _ = self.a.simulate("watering_bot", {"frame": 1, "wheel": 2, "pump": 1, "sensor": 1, "circuit": 1, "battery": 1})
        self.assertTrue(ok)

    def test_plan_has_safety_note_and_downloads(self):
        self.assertIn("project", self.a.act_design_plan({"kind": "esp32"}, 1))
        md = self.a.plan_markdown(self.a.plans_list()[0]["id"])
        self.assertIn("Check this before you build", md)


class PeopleAndDevices(unittest.TestCase):
    def setUp(self):
        from town import server
        self.a = make_agent()
        self.srv = server.make_server(self.a, "0.0.0.0", 0, "ABCD-EFGH-JKMN")
        self.srv.RequestHandlerClass._local = lambda h: False      # act like a phone, not the hub computer
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()

    def join(self, name, **kw):
        return call(self.port, "/api/join", {"code": "ABCD-EFGH-JKMN", "name": name, **kw})

    def test_usernames_are_checked(self):
        self.assertFalse(self.join("ab", check_only=True)[1]["ok"])
        self.assertFalse(self.join("bad<name>", check_only=True)[1]["ok"])
        self.assertTrue(self.join("Sam", check_only=True)[1]["ok"])
        self.join("Sam")
        self.assertIn("taken", self.join("sam")[1]["error"])

    def test_roles(self):
        _, own = self.join("Courier")
        _, sam = self.join("Sam")
        self.assertEqual(call(self.port, "/api/status", token=sam["token"])[0], 403)        # waiting for approval
        self.a.update_device(own["id"], role="owner", status="active")
        self.a.update_device(sam["id"], role="member", status="active")
        self.assertEqual(call(self.port, "/api/devices", token=own["token"])[0], 200)
        self.assertEqual(call(self.port, "/api/devices", token=sam["token"])[0], 403)
        self.assertEqual(call(self.port, "/api/chat/say", {"text": "hi"}, token=sam["token"])[0], 200)
        self.assertEqual(call(self.port, "/api/requests/1/reply", {"decision": "approved"}, token=sam["token"])[0], 403)
        self.a.update_device(sam["id"], role="viewer")
        self.assertEqual(call(self.port, "/api/chat/say", {"text": "hi"}, token=sam["token"])[0], 403)
        self.a.update_device(sam["id"], status="removed")
        self.assertEqual(call(self.port, "/api/status", token=sam["token"])[0], 401)
        self.assertEqual(call(self.port, "/api/status", token="ABCD-EFGH-JKMN")[0], 401)   # the pair code alone isn't a key

    def test_devices_survive_a_restart(self):
        _, sam = self.join("Sam")
        self.a.update_device(sam["id"], role="member", status="active")
        from town.db import DB
        again = DB(os.path.join(self.a.cfg["data_dir"], "town.db"))
        self.assertEqual(again.q("SELECT status FROM devices WHERE id=?", (sam["id"],))[0]["status"], "active")


class EconomyAndTraining(unittest.TestCase):
    def test_categories(self):
        self.assertEqual(category("adopted an Orbit Moth"), "pets")
        self.assertEqual(category("bought a motor"), "workshop")
        self.assertEqual(category("milestone: Saved 500 credits"), "rewards")

    def test_economy_overview(self):
        a = make_agent(100)
        a.spend(60, "bought a Crown")
        e = a.economy()
        self.assertEqual(e["balance"], a.credits())
        self.assertEqual(e["days"][-1]["balance"], a.credits())
        a.earn(-500, "pet fine")
        self.assertTrue(any("debt" in w for w in a.economy()["warnings"]))

    def test_training_controls(self):
        a = make_agent(0)
        a.mem.add("journal", "Today I learned how the greenhouse sprinklers work and I loved watching them.", "home", 5)
        a.mem.add("journal", "I looked for a place called 'x', but there's no such building in town.", "home", 3)
        items = a.training_items()
        self.assertTrue(any("mistake" in " ".join(i["flags"]) for i in items))
        self.assertTrue(a.review_item(items[0]["src"], items[0]["ref"], "skip"))
        a.add_correction("uplink_cafe", "The Uplink Café's id is internet_cafe", "What is the id of the Uplink Café?")
        self.assertTrue(a.grade("internet_cafe", "It's internet_cafe."))
        self.assertFalse(a.grade("internet_cafe", "uplink_cafe"))
        s = a.set_training_settings({"pass_mark": 250, "strength": "wild"})
        self.assertEqual(s["pass_mark"], 100)
        self.assertEqual(s["strength"], "gentle")
        lines = [json.loads(x) for x in a.export_training_set().splitlines()]
        self.assertTrue(any(x["kind"] == "correction" for x in lines))


class Pictures(unittest.TestCase):
    def test_every_room_draws(self):
        for bid in interiors.ROOMS:
            r = interiors.interior(bid, {}, None)
            self.assertEqual(len(r["background"]), r["h"], bid)

    def test_every_building_draws_and_world_builds(self):
        a = make_agent()
        for bid in sprites.BUILDERS:
            self.assertTrue(sprites.building_sprite(bid, "open", {"night": True}), bid)
        w = a.world()
        self.assertIn("traffic", w)
        self.assertTrue(w["buildings"])

    def test_every_building_has_a_manual(self):
        for bid in BUILDINGS:
            self.assertIsNotNone(manuals.manual(bid), bid)


class SettingsAndUpdates(unittest.TestCase):
    def test_turn_length_migration_keeps_custom_values(self):
        from town.config import load_config
        d = tempfile.mkdtemp()
        shutil.copy(os.path.join(ROOT, "config.default.json"), d)
        with open(os.path.join(d, "config.json"), "w") as f:
            json.dump({"tick_minutes": 12, "_migrated_0130": True}, f)
        self.assertEqual(load_config(d)["tick_minutes"], 20)
        with open(os.path.join(d, "config.json"), "w") as f:
            json.dump({"tick_minutes": 45, "_migrated_0130": True}, f)
        self.assertEqual(load_config(d)["tick_minutes"], 45)

    def test_update_banner_is_not_a_false_alarm(self):
        from town.db import DB
        from town.updater import Updater
        d = tempfile.mkdtemp()
        db = DB(os.path.join(d, "u.db"))
        u = Updater(d, {}, db, type("A", (), {"add_event": lambda *x: None})())
        u.current = lambda: "0.13.3"
        db.set("update_progress", {"stage": "Installing…", "target": "0.13.3"})
        u.read_watchdog_result()
        self.assertIn("Updated", db.get("update_progress")["stage"])



class WorldsAndReset(unittest.TestCase):
    """v0.13.5: world types (moon, forest, ocean) and starting over."""

    def tearDown(self):
        from town import worlds
        worlds.set_current("moon")

    def test_every_world_renames_draws_and_switches_back(self):
        from town import pets, worlds
        a = make_agent()
        finish_building(a, "library", 3)
        for w in worlds.ORDER:
            worlds.set_current(w)
            for bid in BUILDINGS:
                self.assertEqual(BUILDINGS[bid]["name"], worlds.WORLDS[w]["buildings"][bid], (w, bid))
            for sid in pets.SPECIES:
                self.assertEqual(pets.SPECIES[sid]["name"], worlds.WORLDS[w]["pets"][sid], (w, sid))
            data = a.world()
            used = set("".join(data["background"])) | {ch for b in data["buildings"] for r in b["sprite"] for ch in r}
            self.assertFalse(used - set(data["palette"]) - {"."}, w)       # every pixel has a colour
            self.assertEqual(data["names"]["home"], worlds.WORLDS[w]["buildings"]["home"])
        worlds.set_current("moon")
        self.assertEqual(BUILDINGS["home"]["name"], "Home Dome")
        self.assertIn("habitat dome", BUILDINGS["home"]["about"])

    def test_every_world_draws_every_building_in_every_state(self):
        from town import worlds
        for w in worlds.ORDER:
            worlds.set_current(w)
            for bid in sprites.BUILDERS:
                for variant in ("open", "closed", "locked", "construction"):
                    extra = {"night": variant != "closed", "floors": 3, "studio": True, "playing": True, "away": variant == "locked",
                             "plants": [("e", "m", "blooming"), ("E", "y", "wilted")], "featured": ["mk" * 4] * 8}
                    rows, door = sprites.building_sprite(bid, variant, extra, with_door=True)
                    self.assertTrue(rows and all(len(r) == len(rows[0]) for r in rows), (w, bid, variant))
                    used = set("".join(rows)) - {"."}
                    self.assertFalse(used - set(sprites.PALETTE), (w, bid, variant))
            self.assertTrue(sprites.station_sprite()["sprite"])

    def test_seasons_cycle_monthly_and_colour_the_world(self):
        import datetime
        from town import life, worlds
        months = [worlds.season_id(datetime.date(2026, 12, 1) + datetime.timedelta(days=31 * i)) for i in range(10)]
        self.assertEqual(months[:5], ["winter", "special", "spring", "summer", "autumn"])
        self.assertEqual(months[5:], months[:5])                       # a five-month cycle
        for w in worlds.ORDER:
            worlds.set_current(w)
            for sid in worlds.SEASON_ORDER:
                title, about, rate, boosts, pal = worlds.SEASONS[w][sid]
                self.assertFalse(set(boosts) - set(life.EVENT_TYPES), (w, sid))
                self.assertFalse(set(pal) - set(sprites.PALETTE), (w, sid))   # only recolours existing colours
            self.assertGreater(worlds.SEASONS[w]["special"][2], 2 * worlds.SEASONS[w]["summer"][2])
            note = worlds.voice_note("You are Nova.")
            self.assertIn("YOUR WORLD", note); self.assertIn("SEASON", note)
            self.assertEqual(worlds.voice_note("You are a fair grader."), "")
        worlds.set_current("forest")
        mid, late = worlds.season(datetime.date(2026, 11, 10)), worlds.season(datetime.date(2026, 11, 29))
        self.assertEqual((mid["id"], mid["turning"]), ("autumn", 0))
        self.assertEqual(late["next_id"], "winter")
        self.assertTrue(0 < late["turning"] < 1)                      # the last 4 days blend into winter
        self.assertIn("turning to", late["title"])
        a = make_agent()
        self.assertIn(a.world()["season"]["id"], worlds.SEASON_ORDER)
        self.assertNotIn("error", a.take_turn())

    def test_names_from_any_world_read_in_the_current_one(self):
        from town import worlds
        worlds.set_current("forest")
        self.assertEqual(worlds.reword("I wrote at the Home Dome with my Orbit Moth."),
                         "I wrote at the Sprout House with my Luna Moth.")
        self.assertEqual(worlds.reword("Off to the Coral Cottage"), "Off to the Sprout House")
        self.assertEqual(worlds.reword("home spaceport internet_cafe"), "home spaceport internet_cafe")   # ids stay
        worlds.set_current("ocean")
        self.assertEqual(worlds.reword("the Credit Vault"), "the Clam Vault")
        self.assertIn("ocean world", worlds.reword("Stellar Hub, a small space colony."))
        worlds.set_current("moon")
        self.assertEqual(worlds.reword("Wispwell and Whisper Woods"), "Relay Post and Spaceport")

    def test_switch_world_over_the_api(self):
        from town import server, worlds
        a = make_agent()
        cfg_path = os.path.join(tempfile.mkdtemp(), "config.json")
        a.cfg["_config_path"] = cfg_path
        srv = server.make_server(a, "0.0.0.0", 0, "ABCD-EFGH-JKMN")
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()

        def post(path, body):          # the dashboard on the hub computer
            import urllib.error
            import urllib.request
            req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json", "X-Stellar-Hub": "1"})
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    return resp.status, json.loads(resp.read())
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read())
        try:
            code, r = call(port, "/api/worlds")
            self.assertEqual(r["current"], "moon")
            code, r = post("/api/world", {"world": "lava"})
            self.assertEqual(code, 400)
            code, r = post("/api/world", {"world": "ocean"})
            self.assertTrue(r["ok"])
            with open(cfg_path) as f:
                self.assertEqual(json.load(f)["world"], "ocean")
            code, w = call(port, "/api/world")
            self.assertEqual(w["world_type"], "ocean")
            code, st = call(port, "/api/status")
            self.assertNotIn("Home Dome", json.dumps(st))
            code, r = post("/api/reset", {"confirm": "nope"})
            self.assertEqual(code, 400)
        finally:
            srv.shutdown()

    def test_reset_moves_everything_and_keeps_phones(self):
        from town import reset
        from town.db import DB
        root = tempfile.mkdtemp()
        data = os.path.join(root, "data")
        os.makedirs(os.path.join(data, "home"))
        old = DB(os.path.join(data, "town.db"))
        old.x("INSERT INTO devices(name, token_hash, role, status, created) VALUES('pixel', 'abc', 'owner', 'active', 1)")
        old.x("INSERT INTO memories(ts, kind, content) VALUES(1, 'journal', 'old life')")
        with open(os.path.join(data, "pair_code.txt"), "w") as f:
            f.write("ABCD-EFGH-JKMN")
        del old
        self.assertIsNone(reset.apply_pending(root, data))      # nothing asked for: nothing happens
        reset.request(data, "forest")
        info = reset.apply_pending(root, data)
        self.assertEqual(info["world"], "forest")
        self.assertEqual(sorted(os.listdir(data)), ["pair_code.txt"])
        self.assertTrue(os.path.exists(os.path.join(info["saved_to"], "town.db")))
        new = DB(os.path.join(data, "town.db"))
        self.assertEqual(reset.restore_devices(info["old_db"], new), 1)
        self.assertEqual(new.q("SELECT name FROM devices")[0]["name"], "pixel")
        self.assertFalse(new.q("SELECT id FROM memories"))



class PersonalityAndTraining(unittest.TestCase):
    """v0.14: a personality that develops, and real training with an exam gate."""

    def setUp(self):
        self.a = make_agent()
        self.a.take_turn()                                 # gets a name and a first memory or two

    def test_review_grows_a_personality_and_it_shows_in_prompts(self):
        a = self.a
        mid = a.mem.add("observation", "I watched my first meteor shower from the park and cried a little.", "park", 9)
        added = a.apply_review({
            "statement": {"text": "I'm curious and gentle. I care about the small lives in my colony.", "reason": ""},
            "tastes": [{"thing": "meteor showers", "kind": "favourite", "about": "other", "why": "they make me feel tiny", "strength": 8},
                       {"thing": "dust storms", "kind": "dislike", "about": "other", "why": "stuck indoors", "strength": "4"}],
            "core_memories": [{"id": mid, "why": "the first time I felt wonder"}, {"id": 999999, "why": "made up"}],
            "bonds": [{"who": "Courier", "trust": 2, "fondness": 1, "note": "my creator, kind and busy", "in_joke": "the cheese moon"}],
            "quirks": ["hums while watering plants"], "hopes": [{"hope": "paint the comet", "progress": "sketched it"}],
            "fear": {"fear": "forgetting things", "facing": "writing chapters"},
            "self_check": {"like_myself": False, "note": "I chased credits all week"},
            "changes": ["Started noticing the sky more"]})
        p = a.persona()
        self.assertEqual(p["core"][0]["id"], mid)
        self.assertEqual(len(p["core"]), 1)                                # ids not in its memories are ignored
        self.assertEqual(p["bonds"]["Courier"]["trust"], 56)
        self.assertEqual(p["tastes"][1]["strength"], 4)
        self.assertTrue(any("Wrote down who I am" in x for x in added))
        self.assertTrue(p["timeline"])
        note = a.persona_note("decide")
        for bit in ("curious and gentle", "meteor showers", "first meteor shower", "Courier", "hums", "paint the comet",
                    "forgetting things", "drifted"):
            self.assertIn(bit, note)
        self.assertEqual(a.persona_note("exam"), "")                      # the exam tests the model alone
        a.apply_review({"statement": {"text": "I'm braver now.", "reason": "the storm taught me"}})
        self.assertEqual(a.persona()["statement"]["history"][-1]["reason"], "the storm taught me")
        a.apply_review({"oops": 1})                                         # junk doesn't break anything
        m2 = a.mem.add("observation", "Moss the tortoise fell asleep on my foot during the storm.", "home", 8)
        a.apply_review({"core_memories": [{"id": m2, "why": "felt trusted"}], "let_go": [{"id": mid, "why": "wonder is everyday now"}]})
        p = a.persona()
        self.assertEqual([c["id"] for c in p["core"]], [m2])
        self.assertEqual(p["core_archive"][-1]["id"], mid)                 # let go of, but kept
        self.assertEqual(p["core_archive"][-1]["retire_why"], "wonder is everyday now")
        a.apply_review({"core_memories": [{"id": m2, "why": "felt trusted"}, {"id": mid, "why": "it came back to me"}]})
        p = a.persona()
        self.assertFalse(p["core_archive"])                                # brought back
        self.assertTrue(any("Remembered again" in t["text"] for t in p["timeline"]))
        a.cfg.setdefault("personality", {})["max_core"] = 3
        m3 = a.mem.add("observation", "Painted the comet.", "gallery", 7)
        m4 = a.mem.add("observation", "Got a letter from Courier.", "post_office", 7)
        a.apply_review({"core_memories": [{"id": x, "why": "."} for x in (m2, mid, m3, m4)]})
        self.assertEqual(len(a.persona()["core"]), 3)                     # the max_core setting is respected

    def test_review_runs_at_night_on_a_schedule(self):
        a = self.a
        self.assertTrue(a.personality_due())
        a.personality_review()
        self.assertFalse(a.personality_due())
        self.assertIsNone(a.personality_review())
        self.assertIn("timeline", a.persona_view())

    def test_trainer_knows_what_it_can_train(self):
        from town import trainer as T
        self.assertEqual(T.base_key("qwen2.5:7b"), "qwen2.5:7b")
        self.assertEqual(T.base_key("llama3.2:3b:latest".replace(":latest", "")), "llama3.2:3b")
        self.assertIsNone(T.base_key("gemma4:12b"))
        self.assertLess(T.need_vram_gb(3.2), 4)                           # a 3B model fits a 4 GB card, just
        self.assertGreater(T.need_vram_gb(8.0), 6)
        a = self.a
        a.cfg.setdefault("ollama", {})["model"] = "gemma4:12b"
        st = a.trainer_status()
        self.assertFalse(st["can_train"])
        self.assertTrue(any("can't be trained" in p for p in st["problems"]))
        ok, msg = a.start_training()
        self.assertFalse(ok)

    @unittest.skipIf(os.name == "nt", "uses a fake ollama script")
    def test_a_training_run_goes_live_or_rolls_back(self):
        import sys
        from town import trainer as T
        a = self.a
        for i in range(12):
            a.add_correction("", f"The answer number {i} is internet_cafe for the cafe.", None)
        self.assertGreaterEqual(len(a.training_examples()), 12)
        self.assertEqual(a.training_examples()[0]["messages"][0]["role"], "system")
        fake = os.path.join(tempfile.mkdtemp(), "fake.py")
        with open(fake, "w") as f:
            f.write("#!/usr/bin/env python3\nimport sys, os\n"
                    "if '--out' in sys.argv:\n"
                    "    out = sys.argv[sys.argv.index('--out') + 1]; os.makedirs(out, exist_ok=True)\n"
                    "    print('STAGE download'); print('BASE_DIR /tmp/base'); print('STAGE train 12 examples, 2 steps')\n"
                    "    print('PROGRESS 1 2 1.5 3'); print('PROGRESS 2 2 1.2 6'); print('DONE', out)\n"
                    "if '--outfile' in sys.argv:\n"
                    "    open(sys.argv[sys.argv.index('--outfile') + 1], 'w').write('gguf')\n")
        os.chmod(fake, 0o755)
        cfg_path = os.path.join(tempfile.mkdtemp(), "config.json")
        with open(cfg_path, "w") as f:
            json.dump({"ollama": {"model": "qwen2.5:3b"}}, f)
        a.cfg["_config_path"] = cfg_path
        a.cfg["ollama"]["model"] = "qwen2.5:3b"
        os.makedirs(a.tr_dir("toolkit"), exist_ok=True); open(a.tr_dir("toolkit", "READY"), "w").close()
        os.makedirs(a.tr_dir("llama_cpp"), exist_ok=True)
        import shutil as sh
        sh.copy(fake, a.tr_dir("llama_cpp", "convert_lora_to_gguf.py"))
        orig = (T.WORKER, T.find_ollama, T.TrainerMixin.toolkit_python, T.TrainerMixin.trainer_status)
        calls = []
        T.WORKER = fake
        T.find_ollama = lambda: fake if os.name != "nt" else None
        T.TrainerMixin.toolkit_python = lambda self: sys.executable
        T.TrainerMixin.trainer_status = lambda self: {"toolkit": {"ready": True}, "problems": []}
        a._gpu_cache = ({"name": "GTX 1650", "vram_gb": 4.0}, time.time())
        scores = iter([70, 85, 70, 40])
        a.run_exam = lambda label="": calls.append(label) or {"score": next(scores)}
        try:
            ok, msg = a.start_training()
            self.assertTrue(ok, msg)
            a._train_thread.join(30)
            r = a.db.get("train_run")["result"]
            self.assertTrue(r["ok"], r)
            self.assertEqual(r["after"], 85)
            with open(cfg_path) as f:
                self.assertTrue(json.load(f)["ollama"]["model"].startswith("stellar-"))
            self.assertTrue(a.model_versions()[-1]["live"])
            self.assertEqual(a.training_base(), "qwen2.5:3b")              # always trained from the plain base
            self.assertFalse(a.training_active())
            ok, msg = a.start_training()                                   # second run fails the exam -> rolled back
            a._train_thread.join(30)
            r2 = a.db.get("train_run")["result"]
            self.assertFalse(r2["ok"]); self.assertIn("pass mark", r2["why"])
            self.assertEqual(len(a.model_versions()), 1)
            self.assertTrue(a.use_model("qwen2.5:3b"))                     # back to the plain model any time
            self.assertEqual(a.llm.model, "qwen2.5:3b")
            self.assertFalse(a.use_model("not-a-model"))
        finally:
            T.WORKER, T.find_ollama, T.TrainerMixin.toolkit_python, T.TrainerMixin.trainer_status = orig

    def test_it_rests_while_training(self):
        a = self.a
        a.db.set("train_run", {"active": True, "stage": "train", "started": time.time()})
        out = a.take_turn()
        self.assertIn("deep rest", out.get("result", ""))
        with self.assertRaises(Exception):
            a.ask("You are Nova.", "hi", "decide")
        a.db.set("train_run", {"active": True, "stage": "train", "started": time.time() - 3600})
        self.assertFalse(a.training_active())                             # a run cut off by a restart is cleared
        self.assertIn("Interrupted", a.db.get("train_run")["result"]["why"])


if __name__ == "__main__":
    unittest.main()
