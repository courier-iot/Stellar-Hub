"""A small, complete chess rules engine (no outside libraries).

Board: 64-char string, index 0 = a8 ... 63 = h1. Uppercase = white, lowercase = black, '.' = empty.
Moves are UCI strings like "e2e4" or "e7e8q". Handles castling, en passant, promotion, check,
checkmate, stalemate, 50-move rule and insufficient material.
"""

START = ("rnbqkbnr" "pppppppp" "........" "........" "........" "........" "PPPPPPPP" "RNBQKBNR")
FILES = "abcdefgh"
KNIGHT = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
KING = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
ROOK_DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
BISHOP_DIRS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]


def sq(name):
    return (8 - int(name[1])) * 8 + FILES.index(name[0])


def name(i):
    return FILES[i % 8] + str(8 - i // 8)


def new_game():
    return {"board": START, "turn": "w", "castling": "KQkq", "ep": None, "halfmove": 0,
            "fullmove": 1, "moves": [], "result": None}


def _is_white(p):
    return p.isupper()


def _own(p, color):
    return p != "." and (p.isupper() if color == "w" else p.islower())


def _enemy(p, color):
    return p != "." and (p.islower() if color == "w" else p.isupper())


def attacked(board, i, by):
    """Is square i attacked by side `by`?"""
    r, c = divmod(i, 8)
    pawn = "P" if by == "w" else "p"
    dr = 1 if by == "w" else -1          # white pawns attack upward (towards row 0)
    for dc in (-1, 1):
        rr, cc = r + dr, c + dc
        if 0 <= rr < 8 and 0 <= cc < 8 and board[rr * 8 + cc] == pawn:
            return True
    for dr2, dc2 in KNIGHT:
        rr, cc = r + dr2, c + dc2
        if 0 <= rr < 8 and 0 <= cc < 8 and board[rr * 8 + cc] == ("N" if by == "w" else "n"):
            return True
    for dr2, dc2 in KING:
        rr, cc = r + dr2, c + dc2
        if 0 <= rr < 8 and 0 <= cc < 8 and board[rr * 8 + cc] == ("K" if by == "w" else "k"):
            return True
    for dirs, pieces in ((ROOK_DIRS, "RQ"), (BISHOP_DIRS, "BQ")):
        targets = pieces if by == "w" else pieces.lower()
        for dr2, dc2 in dirs:
            rr, cc = r + dr2, c + dc2
            while 0 <= rr < 8 and 0 <= cc < 8:
                p = board[rr * 8 + cc]
                if p != ".":
                    if p in targets:
                        return True
                    break
                rr += dr2
                cc += dc2
    return False


def _pseudo(g):
    b, color = g["board"], g["turn"]
    out = []
    for i, p in enumerate(b):
        if not _own(p, color):
            continue
        r, c = divmod(i, 8)
        kind = p.upper()
        if kind == "P":
            step = -1 if color == "w" else 1
            start_row = 6 if color == "w" else 1
            rr = r + step
            if 0 <= rr < 8 and b[rr * 8 + c] == ".":
                out.append((i, rr * 8 + c))
                if r == start_row and b[(r + 2 * step) * 8 + c] == ".":
                    out.append((i, (r + 2 * step) * 8 + c))
            for dc in (-1, 1):
                cc = c + dc
                if 0 <= rr < 8 and 0 <= cc < 8:
                    t = rr * 8 + cc
                    if _enemy(b[t], color) or (g["ep"] is not None and t == g["ep"]):
                        out.append((i, t))
        elif kind == "N":
            for dr, dc in KNIGHT:
                rr, cc = r + dr, c + dc
                if 0 <= rr < 8 and 0 <= cc < 8 and not _own(b[rr * 8 + cc], color):
                    out.append((i, rr * 8 + cc))
        elif kind == "K":
            for dr, dc in KING:
                rr, cc = r + dr, c + dc
                if 0 <= rr < 8 and 0 <= cc < 8 and not _own(b[rr * 8 + cc], color):
                    out.append((i, rr * 8 + cc))
            enemy = "b" if color == "w" else "w"
            home = 60 if color == "w" else 4
            if i == home and not attacked(b, home, enemy):
                ks, qs = ("K", "Q") if color == "w" else ("k", "q")
                if ks in g["castling"] and b[home + 1] == "." and b[home + 2] == "." \
                        and not attacked(b, home + 1, enemy) and not attacked(b, home + 2, enemy):
                    out.append((i, home + 2))
                if qs in g["castling"] and b[home - 1] == "." and b[home - 2] == "." and b[home - 3] == "." \
                        and not attacked(b, home - 1, enemy) and not attacked(b, home - 2, enemy):
                    out.append((i, home - 2))
        else:
            dirs = ROOK_DIRS if kind == "R" else BISHOP_DIRS if kind == "B" else ROOK_DIRS + BISHOP_DIRS
            for dr, dc in dirs:
                rr, cc = r + dr, c + dc
                while 0 <= rr < 8 and 0 <= cc < 8:
                    t = rr * 8 + cc
                    if _own(b[t], color):
                        break
                    out.append((i, t))
                    if b[t] != ".":
                        break
                    rr += dr
                    cc += dc
    return out


def _apply(g, f, t, promo="q"):
    b = list(g["board"])
    p = b[f]
    color = g["turn"]
    captured = b[t]
    ep = None
    if p.upper() == "P" and g["ep"] is not None and t == g["ep"] and captured == ".":
        b[t + (8 if color == "w" else -8)] = "."   # en passant capture
        captured = "p" if color == "w" else "P"
    if p.upper() == "P" and abs(t - f) == 16:
        ep = (f + t) // 2
    if p.upper() == "K" and abs(t - f) == 2:        # castling: move the rook too
        if t > f:
            b[t - 1], b[t + 1] = b[t + 1], "."
        else:
            b[t + 1], b[t - 2] = b[t - 2], "."
    b[t], b[f] = p, "."
    if p.upper() == "P" and t // 8 in (0, 7):
        b[t] = promo.upper() if color == "w" else promo.lower()
    castling = g["castling"]
    for corner, right in ((63, "K"), (56, "Q"), (7, "k"), (0, "q")):
        if f == corner or t == corner:
            castling = castling.replace(right, "")
    if p == "K":
        castling = castling.replace("K", "").replace("Q", "")
    if p == "k":
        castling = castling.replace("k", "").replace("q", "")
    return {"board": "".join(b), "turn": "b" if color == "w" else "w", "castling": castling, "ep": ep,
            "halfmove": 0 if (p.upper() == "P" or captured != ".") else g["halfmove"] + 1,
            "fullmove": g["fullmove"] + (1 if color == "b" else 0), "moves": g["moves"], "result": g["result"]}


def in_check(g, color=None):
    color = color or g["turn"]
    king = "K" if color == "w" else "k"
    if king not in g["board"]:
        return False
    return attacked(g["board"], g["board"].index(king), "b" if color == "w" else "w")


def legal_moves(g):
    moves = []
    for f, t in _pseudo(g):
        promo_needed = g["board"][f].upper() == "P" and t // 8 in (0, 7)
        for promo in (("q", "r", "b", "n") if promo_needed else (None,)):
            ng = _apply(g, f, t, promo or "q")
            if not in_check(ng, g["turn"]):
                moves.append(name(f) + name(t) + (promo or ""))
    return moves


def _insufficient(board):
    pieces = [p for p in board if p not in ".Kk"]
    return not pieces or (len(pieces) == 1 and pieces[0].upper() in "BN")


def play(g, uci):
    """Returns the new game state, or raises ValueError for an illegal move."""
    uci = uci.strip().lower()
    legal = legal_moves(g)
    if uci not in legal and uci + "q" in legal:
        uci += "q"
    if uci not in legal:
        raise ValueError(f"{uci} isn't a legal move")
    ng = _apply(g, sq(uci[:2]), sq(uci[2:4]), uci[4] if len(uci) > 4 else "q")
    ng["moves"] = g["moves"] + [uci]
    nxt = legal_moves(ng)
    if not nxt:
        ng["result"] = ("1-0" if ng["turn"] == "b" else "0-1") if in_check(ng) else "1/2-1/2"
    elif ng["halfmove"] >= 100 or _insufficient(ng["board"]):
        ng["result"] = "1/2-1/2"
    return ng


VALUES = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 0}


def describe(g):
    """Plain-text board for the AI, with white at the bottom."""
    rows = []
    for r in range(8):
        rows.append(f"{8 - r} " + " ".join(g["board"][r * 8:(r + 1) * 8]))
    rows.append("  a b c d e f g h")
    return "\n".join(rows)


def material(g, color):
    return sum(VALUES[p.upper()] for p in g["board"] if _own(p, color))
