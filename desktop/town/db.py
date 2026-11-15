"""SQLite storage for the town. One file holds the resident's whole mind."""
import json
import os
import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories(
    id INTEGER PRIMARY KEY, ts REAL, kind TEXT, building TEXT,
    content TEXT, importance INTEGER DEFAULT 3);
CREATE TABLE IF NOT EXISTS requests(
    id INTEGER PRIMARY KEY, ts REAL, kind TEXT, content TEXT, reason TEXT,
    status TEXT DEFAULT 'pending', reply TEXT, replied_ts REAL);
CREATE TABLE IF NOT EXISTS letters(
    id INTEGER PRIMARY KEY, ts REAL, sender TEXT, content TEXT, read INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS library(
    id INTEGER PRIMARY KEY, ts REAL, topic TEXT, summary TEXT, source TEXT);
CREATE TABLE IF NOT EXISTS turns(
    id INTEGER PRIMARY KEY, ts REAL, building TEXT, action TEXT, thought TEXT, result TEXT);
CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY, value TEXT);
"""


class DB:
    def __init__(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def q(self, sql, args=()):
        with self.lock:
            rows = [dict(r) for r in self.conn.execute(sql, args).fetchall()]
            return rows

    def x(self, sql, args=()):
        with self.lock:
            cur = self.conn.execute(sql, args)
            self.conn.commit()
            return cur.lastrowid

    def get(self, key, default=None):
        rows = self.q("SELECT value FROM state WHERE key=?", (key,))
        return json.loads(rows[0]["value"]) if rows else default

    def set(self, key, value):
        self.x("INSERT OR REPLACE INTO state(key, value) VALUES(?, ?)", (key, json.dumps(value)))
