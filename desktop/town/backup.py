"""Nightly backups of the resident's mind: one .tar.gz per day, newest `keep` kept.

Restore: stop Stellar Hub, then extract a backup over the desktop/ folder:
    tar -xzf ~/StellarHub-backups/stellarhub-YYYY-MM-DD.tar.gz -C /path/to/StellarHub
"""
import datetime
import glob
import os
import sqlite3
import tarfile
import tempfile


def make_backup(data_dir, dest_dir, keep=14):
    dest_dir = os.path.expanduser(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d")
    out = os.path.join(dest_dir, f"stellarhub-{stamp}.tar.gz")
    with tempfile.TemporaryDirectory() as tmp:
        db_copy = os.path.join(tmp, "town.db")
        src = sqlite3.connect(os.path.join(data_dir, "town.db"))
        dst = sqlite3.connect(db_copy)
        with dst:
            src.backup(dst)            # consistent copy even while the hub is running
        src.close()
        dst.close()
        partial = out + ".part"
        with tarfile.open(partial, "w:gz") as tar:
            tar.add(db_copy, arcname="data/town.db")
            for name in ("home", "workshop/programs", "pair_code.txt"):
                path = os.path.join(data_dir, name)
                if os.path.exists(path):
                    tar.add(path, arcname=f"data/{name}")
        os.replace(partial, out)
        try:
            os.chmod(out, 0o600)   # backups contain the pair code: keep them private to you
        except OSError:
            pass
    backups = sorted(glob.glob(os.path.join(dest_dir, "stellarhub-*.tar.gz")))
    for old in backups[:-keep] if keep > 0 else []:
        os.remove(old)
    return out
