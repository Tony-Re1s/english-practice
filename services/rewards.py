"""Recompensas do modo infantil: estrelas que viram itens na loja do Bip, sequência de dias 🔥 e meta do dia."""

import json
from datetime import date, datetime, timedelta, timezone

from services import db

BRT = timezone(timedelta(hours=-3))
DAILY_GOAL = 1          # meta do dia: 1 planeta
DAILY_LIMIT = 3         # limite gentil: depois de 3 planetas no dia, o Bip pede para voltar amanhã (perfil infantil)

# Loja do Bip: chapéu (em cima do robô) e nave (marca o planeta atual no mapa)
SHOP = [
    {"id": "hat_cap", "kind": "hat", "emoji": "🧢", "name": "Boné", "price": 5},
    {"id": "hat_party", "kind": "hat", "emoji": "🥳", "name": "Festa", "price": 8},
    {"id": "hat_crown", "kind": "hat", "emoji": "👑", "name": "Coroa", "price": 15},
    {"id": "hat_wizard", "kind": "hat", "emoji": "🎩", "name": "Cartola", "price": 12},
    {"id": "hat_grad", "kind": "hat", "emoji": "🎓", "name": "Formatura", "price": 20},
    {"id": "hat_star", "kind": "hat", "emoji": "⭐", "name": "Estrela", "price": 25},
    {"id": "ship_ufo", "kind": "ship", "emoji": "🛸", "name": "Disco voador", "price": 10},
    {"id": "ship_sat", "kind": "ship", "emoji": "🛰️", "name": "Satélite", "price": 10},
    {"id": "ship_comet", "kind": "ship", "emoji": "☄️", "name": "Cometa", "price": 18},
    {"id": "ship_dragon", "kind": "ship", "emoji": "🐉", "name": "Dragão espacial", "price": 30},
]
ITEMS = {i["id"]: i for i in SHOP}


def today() -> date:
    return datetime.now(BRT).date()


def streak(days: list) -> int:
    """Dias seguidos até hoje (ou até ontem, se hoje ainda não jogou)."""
    s = set(days)
    d = today() if today() in s else today() - timedelta(days=1)
    n = 0
    while d in s:
        n += 1
        d -= timedelta(days=1)
    return n


def load_shop(email: str) -> dict:
    raw = db.get_pref(email, "loja") if db.enabled() else None
    try:
        data = json.loads(raw) if raw else {}
    except Exception:
        data = {}
    return {"spent": int(data.get("spent", 0)), "owned": list(data.get("owned", [])),
            "hat": data.get("hat"), "ship": data.get("ship")}


def save_shop(email: str, shop: dict) -> None:
    if db.enabled():
        db.set_pref(email, "loja", json.dumps(shop))


def buy(email: str, shop: dict, item_id: str, earned: int) -> tuple[bool, str]:
    it = ITEMS[item_id]
    if item_id in shop["owned"]:
        shop[it["kind"]] = item_id
        save_shop(email, shop)
        return True, f"{it['emoji']} Agora o Bip está usando: {it['name']}!"
    if earned - shop["spent"] < it["price"]:
        return False, f"Faltam {it['price'] - (earned - shop['spent'])} ⭐ para comprar {it['name']}."
    shop["spent"] += it["price"]
    shop["owned"].append(item_id)
    shop[it["kind"]] = item_id
    save_shop(email, shop)
    return True, f"{it['emoji']} Você comprou {it['name']}!"


def equipped_emoji(shop: dict, kind: str) -> str:
    it = ITEMS.get(shop.get(kind) or "")
    return it["emoji"] if it else ""
