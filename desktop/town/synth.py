"""Turns the resident's compositions into 16-bit-style chiptune WAV files (standard library only).

A composition is text like:  "C4:1 E4:1 G4:2 R:1 A4:1/2"   (note:beats, R = rest, # for sharps, b for flats)
with an optional bass line in the same format.
"""
import math
import re
import struct
import wave

RATE = 22050
NOTE_INDEX = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
WAVES = ("square", "pulse", "triangle", "saw")


def parse(text, max_beats=256):
    """Returns [(frequency or None, beats)]. Ignores anything it can't read."""
    out, total = [], 0.0
    for tok in re.split(r"[\s,]+", str(text or "").strip()):
        m = re.fullmatch(r"([A-Ga-gRr])([#b]?)(\d?)(?::(\d+(?:\.\d+)?(?:/\d+)?))?", tok)
        if not m:
            continue
        letter, acc, octave, dur = m.groups()
        try:
            if not dur:
                beats = 1.0
            elif "/" in dur:
                num, den = dur.split("/")
                beats = float(num) / float(den)
            else:
                beats = float(dur)
        except (ValueError, ZeroDivisionError):
            beats = 1.0
        beats = max(0.125, min(8.0, beats))
        if letter.upper() == "R":
            out.append((None, beats))
        else:
            semis = NOTE_INDEX[letter.upper()] + (1 if acc == "#" else -1 if acc == "b" else 0)
            octv = int(octave) if octave else 4
            midi = 12 * (octv + 1) + semis
            out.append((440.0 * 2 ** ((midi - 69) / 12), beats))
        total += beats
        if total >= max_beats:
            break
    return out


def _osc(kind, phase):
    p = phase % 1.0
    if kind == "square":
        return 1.0 if p < 0.5 else -1.0
    if kind == "pulse":
        return 1.0 if p < 0.25 else -1.0
    if kind == "triangle":
        return 4 * abs(p - 0.5) - 1
    return 2 * p - 1  # saw


def _render(notes, bpm, kind, volume):
    beat = 60.0 / bpm
    samples = []
    for freq, beats in notes:
        n = int(beats * beat * RATE)
        attack, release = min(200, n // 4), min(900, n // 3)
        for i in range(n):
            if freq is None:
                samples.append(0.0)
                continue
            env = min(1.0, i / attack if attack else 1.0) * min(1.0, (n - i) / release if release else 1.0)
            samples.append(_osc(kind, freq * i / RATE) * env * volume)
    return samples


def render_wav(path, melody, bass="", bpm=110, wave_kind="square", max_seconds=60):
    bpm = max(50, min(220, int(bpm or 110)))
    wave_kind = wave_kind if wave_kind in WAVES else "square"
    lead = _render(parse(melody), bpm, wave_kind, 0.32)
    low = _render(parse(bass), bpm, "triangle", 0.38) if bass else []
    n = min(max(len(lead), len(low)), max_seconds * RATE)
    if n == 0:
        raise ValueError("no playable notes")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        frames = bytearray()
        for i in range(n):
            s = (lead[i] if i < len(lead) else 0.0) + (low[i] if i < len(low) else 0.0)
            frames += struct.pack("<h", int(max(-1.0, min(1.0, s)) * 30000))
        w.writeframes(bytes(frames))
    return n / RATE
