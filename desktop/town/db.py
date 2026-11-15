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
CREATE TABLE IF NOT EXISTS events(
    id INTEGER PRIMARY KEY, ts REAL, kind TEXT, ref_id INTEGER, title TEXT, body TEXT);
CREATE TABLE IF NOT EXISTS ledger(
    id INTEGER PRIMARY KEY, ts REAL, amount INTEGER, reason TEXT);
CREATE TABLE IF NOT EXISTS plants(
    id INTEGER PRIMARY KEY, species TEXT, nickname TEXT, planted_ts REAL, last_water REAL, last_feed REAL,
    light TEXT, health REAL DEFAULT 100, growth REAL DEFAULT 0, stage TEXT DEFAULT 'seed',
    alive INTEGER DEFAULT 1, updated_ts REAL, bloomed INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS broadcasts(id INTEGER PRIMARY KEY, ts REAL, text TEXT);
CREATE TABLE IF NOT EXISTS chapters(
    id INTEGER PRIMARY KEY, ts REAL, title TEXT, text TEXT, from_ts REAL, to_ts REAL);
CREATE TABLE IF NOT EXISTS expeditions(
    id INTEGER PRIMARY KEY, ts REAL, topic TEXT, hours REAL, return_ts REAL, legs TEXT,
    notes TEXT DEFAULT '', report TEXT, status TEXT DEFAULT 'away');
CREATE TABLE IF NOT EXISTS programs(
    id INTEGER PRIMARY KEY, ts REAL, name TEXT, description TEXT, code TEXT,
    status TEXT DEFAULT 'awaiting_approval', output TEXT, exit_code INTEGER, request_id INTEGER);
"""

# Columns added after v0.3.0. Existing databases get them on startup.
MIGRATIONS = [
    "ALTER TABLE memories ADD COLUMN archived INTEGER DEFAULT 0",
    "ALTER TABLE requests ADD COLUMN building TEXT",
    "ALTER TABLE requests ADD COLUMN extra TEXT",
]


class DB:
    def __init__(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        for sql in MIGRATIONS:
            try:
                self.conn.execute(sql)
            except sqlite3.OperationalError:
                pass  # column already exists
        self.conn.commit()

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
