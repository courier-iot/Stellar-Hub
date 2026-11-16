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


if __name__ == "__main__":
    unittest.main()
