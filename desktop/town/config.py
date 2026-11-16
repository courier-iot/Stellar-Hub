"""Settings: config.default.json ships with every update; config.json holds your own changes.

config.json is created from the defaults the first time, and updates never overwrite it.
New settings added in an update show up automatically, because defaults fill in anything missing.
"""
import json
import os
import shutil


def _merge(base, mine):
    out = dict(base)
    for k, v in mine.items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def load_config(root):
    default_path = os.path.join(root, "config.default.json")
    path = os.path.join(root, "config.json")
    defaults = {}
    if os.path.exists(default_path):
        with open(default_path, encoding="utf-8") as f:
            defaults = json.load(f)
    if not os.path.exists(path) and os.path.exists(default_path):
        shutil.copyfile(default_path, path)
    mine = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            mine = json.load(f)
    cfg = _merge(defaults, mine)
    cfg["_config_path"] = path
    return cfg


def save_setting(cfg, section, key, value):
    """Changes one setting in config.json (and in the running config)."""
    cfg.setdefault(section, {})[key] = value
    path = cfg.get("_config_path")
    if not path:
        return
    mine = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            mine = json.load(f)
    mine.setdefault(section, {})[key] = value
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(mine, f, indent=2)
    os.replace(path + ".tmp", path)
