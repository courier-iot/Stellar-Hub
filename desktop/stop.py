"""Stops a running Stellar Hub (including one started in the background).  python3 stop.py"""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
try:
    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as f:
        port = json.load(f).get("port", 8080)
except (OSError, ValueError):
    port = 8080
try:
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/shutdown", data=b"{}", method="POST",
                                 headers={"Content-Type": "application/json", "X-Stellar-Hub": "1"})
    urllib.request.urlopen(req, timeout=5)
    print("Stellar Hub stopped. Everything is saved.")
except Exception:
    print("Stellar Hub wasn't running.")
if "--pause" in sys.argv:
    try:
        input("Press Enter to close…")
    except EOFError:
        pass
