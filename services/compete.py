"""Corrida Espacial: placar da semana entre todo mundo que usa o app + recordes do Desafio Relâmpago.

Pontos da semana (de segunda a domingo):
  ⭐ cada estrela de exercício/missão = 10 pts · 💬 cada fala na conversa = 2 pts · 🎬 cada vídeo respondido = 15 pts
"""
import json
from datetime import datetime, timedelta, timezone

from services import db, galaxy

BRT = timezone(timedelta(hours=-3))
PTS_STAR, PTS_TURN, PTS_VIDEO = 10, 2, 15
# Corrida justa: cada um tem a sua linha de chegada da semana. Criança chega com ~15 estrelas;
# adulto precisa do dobro (ex.: 15 estrelas + 75 falas). Quem chega mais perto da própria meta lidera.
GOAL_KID, GOAL_ADULT = 150, 300


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


def board(only: set | None = None) -> list[dict]:
    """Placar da semana, do 1º ao último. only = só estas pessoas (eu + amigos)."""
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
    # criança = cadastrada com nível Infantil; sem cadastro, quem só fez missões infantis e não conversou como adulto
    kids = {u["email"] for u in db.list_users() if u.get("level") == "crianca"}
    adult_like = {e["user_email"] for e in act["exercises"] if e["level"] != "crianca"}
    kids |= {e["user_email"] for e in act["exercises"] if e["level"] == "crianca"} - adult_like
    for u in kids:
        pts.setdefault(u, {"stars": 0, "turns": 0, "videos": 0})
    if only is not None:
        for u in only:
            pts.setdefault(u, {"stars": 0, "turns": 0, "videos": 0})
        pts = {u: p for u, p in pts.items() if u in only}
    out = []
    for u, p in pts.items():
        name, avatar = profile(u, astros)
        total = p["stars"] * PTS_STAR + p["turns"] * PTS_TURN + p["videos"] * PTS_VIDEO
        goal = GOAL_KID if u in kids else GOAL_ADULT
        pct = min(100, round(100 * total / goal))
        out.append({"email": u, "name": name, "avatar": avatar, "points": total, "goal": goal, "pct": pct,
                    "kid": u in kids, **p})
    return sorted(out, key=lambda r: (-r["pct"], -r["points"]))


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


def challenge_board(only: set | None = None) -> list[dict]:
    astros = db.pref_all("astronauta")
    out = []
    for u, raw in db.pref_all("desafio").items():
        if only is not None and u not in only:
            continue
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
