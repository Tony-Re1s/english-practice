"""Corrida Espacial: placar da semana entre todo mundo que usa o app + recordes do Desafio Relâmpago.

Pontos da semana (de segunda a domingo):
  ⭐ cada estrela de exercício/missão = 10 pts · 💬 cada fala na conversa = 2 pts · 🎬 cada vídeo respondido = 15 pts
"""
import json
from datetime import datetime, timedelta, timezone

from services import db, galaxy

BRT = timezone(timedelta(hours=-3))
PTS_STAR, PTS_TURN, PTS_VIDEO = 10, 2, 15


def week_tag() -> str:
    y, w, _ = datetime.now(BRT).isocalendar()
    return f"{y}-W{w:02d}"


def profile(email: str, astros: dict) -> tuple[str, str]:
    """(nome, avatar) de cada pessoa: o astronauta dela, se tiver; senão o começo do e-mail."""
    raw = astros.get(email) or ""
    parts = raw.split("|")
    name = parts[0].strip() if parts and parts[0].strip() else email.split("@")[0].split(".")[0].capitalize()
    avatar = parts[2] if len(parts) > 2 and parts[2] else "🧑‍🚀"
    return name, avatar


def board() -> list[dict]:
    """Placar da semana, do 1º ao último."""
    act = db.week_activity()
    pts: dict[str, dict] = {}
    for e in act["exercises"]:
        p = pts.setdefault(e["user_email"], {"stars": 0, "turns": 0, "videos": 0})
        p["stars"] += galaxy.stars_for(e["score"] or 0, e["total"] or 0)
    for u, n in act["turns"].items():
        pts.setdefault(u, {"stars": 0, "turns": 0, "videos": 0})["turns"] = int(n)
    for u, n in act["videos"].items():
        pts.setdefault(u, {"stars": 0, "turns": 0, "videos": 0})["videos"] = int(n)
    astros = db.pref_all("astronauta")
    out = []
    for u, p in pts.items():
        name, avatar = profile(u, astros)
        total = p["stars"] * PTS_STAR + p["turns"] * PTS_TURN + p["videos"] * PTS_VIDEO
        out.append({"email": u, "name": name, "avatar": avatar, "points": total, **p})
    return sorted(out, key=lambda r: -r["points"])


def load_best(email: str) -> dict:
    try:
        d = json.loads(db.get_pref(email, "desafio") or "{}")
    except Exception:
        d = {}
    if d.get("week") != week_tag():
        d["week"], d["week_best"] = week_tag(), 0
    d.setdefault("best", 0)
    return d


def save_score(email: str, score: int) -> dict:
    """Salva a pontuação do desafio; retorna {'best','week_best','new_record': bool}."""
    d = load_best(email)
    rec = score > d["best"]
    d["best"] = max(d["best"], score)
    d["week_best"] = max(d.get("week_best", 0), score)
    db.set_pref(email, "desafio", json.dumps(d))
    return {**d, "new_record": rec}


def challenge_board() -> list[dict]:
    astros = db.pref_all("astronauta")
    out = []
    for u, raw in db.pref_all("desafio").items():
        try:
            d = json.loads(raw)
        except Exception:
            continue
        if d.get("week") == week_tag() and d.get("week_best"):
            name, avatar = profile(u, astros)
            out.append({"email": u, "name": name, "avatar": avatar, "score": d["week_best"]})
    return sorted(out, key=lambda r: -r["score"])


def score_for(correct: int, wrong: int, seconds: float) -> int:
    """Cada acerto vale 10; acerto rápido (sobrou tempo) ganha bônus; erro tira 3."""
    left = max(0, 60 - seconds)
    return max(0, correct * 10 - wrong * 3 + int(left // 2))
