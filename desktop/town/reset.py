"""v0.13.5: start the whole project over with a brand-new resident.

Resetting is done in two steps so nothing is deleted while the hub has its files open:
1. request(): the dashboard asks for a reset. A marker file is written and the hub restarts.
2. apply_pending(): on the next start, before anything is opened, everything in data/ is MOVED (not deleted)
   into resets/<date-time>/, so the old resident can be brought back by moving the folder back.

Kept: config.json (your settings, AI model and world), the pair code, and approved phones and their roles,
so nobody has to pair again. Everything else (memories, buildings, credits, pets, plants, curios, the
skill notebook, training data) starts fresh.
"""
import json
import os
import shutil
import sqlite3
import time

MARKER = "RESET_PENDING.json"
KEEP_COPY = ("pair_code.txt",)


def request(data_dir, world):
    with open(os.path.join(data_dir, MARKER), "w", encoding="utf-8") as f:
        json.dump({"world": world, "ts": time.time()}, f)


def _move(src, dst, tries=30):
    for i in range(tries):          # on Windows the old copy of the hub may still be letting go of its files
        try:
            shutil.move(src, dst)
            return True
        except (PermissionError, OSError):
            if i == tries - 1:
                raise
            time.sleep(1)
    return False


def apply_pending(root, data_dir):
    """Returns {"world": ..., "saved_to": ...} if a reset was done, else None."""
    marker = os.path.join(data_dir, MARKER)
    if not os.path.exists(marker):
        return None
    try:
        with open(marker, encoding="utf-8") as f:
            info = json.load(f)
    except (OSError, ValueError):
        info = {}
    dest = os.path.join(root, "resets", time.strftime("%Y-%m-%d_%H%M%S"))
    os.makedirs(dest, exist_ok=True)
    for name in os.listdir(data_dir):
        if name == MARKER:
            continue
        src = os.path.join(data_dir, name)
        if name in KEEP_COPY:
            shutil.copy2(src, os.path.join(dest, name))
            continue
        _move(src, os.path.join(dest, name))
    os.remove(marker)
    return {"world": info.get("world"), "saved_to": dest, "old_db": os.path.join(dest, "town.db")}


def restore_devices(old_db, db):
    """Bring approved phones (and their roles) across to the new database."""
    if not old_db or not os.path.exists(old_db):
        return 0
    try:
        con = sqlite3.connect(old_db)
        con.row_factory = sqlite3.Row
        rows = [dict(r) for r in con.execute("SELECT * FROM devices")]
        con.close()
    except sqlite3.Error:
        return 0
    n = 0
    for r in rows:
        cols = [c for c in r if c != "id"]
        try:
            db.x(f"INSERT INTO devices({','.join(cols)}) VALUES({','.join('?' * len(cols))})", [r[c] for c in cols])
            n += 1
        except Exception:
            pass
    return n
