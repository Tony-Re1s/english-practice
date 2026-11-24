"""Quem pode entrar, com qual nível, limites e quais chaves de API cada pessoa usa.

- Administradores: e-mails em ADMIN_EMAILS (ou, se não houver, em ALLOWED_EMAILS). Sempre entram e usam as chaves do dono.
- Convidados: cadastrados no painel 👥 Usuários (tabela ep_users). O admin escolhe nível (travado ou livre),
  limite de falas por dia, se pode usar o modo ao vivo e, serviço por serviço, qual chave usar:
    "owner" = chave do dono do app · "own" = chave própria da pessoa · "off" = desligado
- Chaves próprias ficam criptografadas no banco (Fernet), com a senha derivada do cookie_secret do login.
"""

import base64
import hashlib
from dataclasses import dataclass, field

import streamlit as st

from config import DEFAULT_DAILY_TURNS, LIVE_DAILY_MINUTES, PROVIDERS, SECRET_NAME
from services import db

POLICIES = {"owner": "Minha chave", "own": "Chave própria", "off": "Desligado"}


@dataclass
class Profile:
    email: str
    is_admin: bool = False
    allowed: bool = False
    level: str | None = None
    level_locked: bool = False
    daily_turns: int | None = None            # None = sem limite
    live_enabled: bool = False
    live_daily_minutes: int = LIVE_DAILY_MINUTES
    policy: dict = field(default_factory=dict)
    keys: dict = field(default_factory=dict)  # provider -> chave efetiva (None se desligado)


def _secret_list(name: str) -> list[str]:
    try:
        return [str(e).strip().lower() for e in (st.secrets.get(name) or []) if str(e).strip()]
    except Exception:
        return []


def admin_emails() -> list[str]:
    return _secret_list("ADMIN_EMAILS") or _secret_list("ALLOWED_EMAILS")


def owner_key(provider: str) -> str | None:
    try:
        return str(st.secrets.get(SECRET_NAME[provider], "") or "") or None
    except Exception:
        return None


# --- criptografia das chaves próprias ------------------------------------------------
def _fernet():
    from cryptography.fernet import Fernet

    try:
        seed = str(st.secrets.get("ENCRYPTION_KEY") or st.secrets["auth"]["cookie_secret"])
    except Exception:
        seed = str(st.secrets.get("ANTHROPIC_API_KEY", "english-practice"))
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest()))


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str | None:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except Exception:
        return None


def mask(value: str | None) -> str:
    return f"…{value[-4:]}" if value else "—"


# --- perfil efetivo -------------------------------------------------------------------
def load_profile(email: str) -> Profile:
    email = (email or "local").strip().lower()
    if email == "local" or email in admin_emails():
        p = Profile(email=email, is_admin=True, allowed=True, live_enabled=True)
        p.policy = {pr: "owner" for pr in PROVIDERS}
        p.keys = {pr: owner_key(pr) for pr in PROVIDERS}
        row = db.get_user(email) if db.enabled() else None
        if row and row.get("live_daily_minutes"):
            p.live_daily_minutes = int(row["live_daily_minutes"])
        return p

    row = db.get_user(email) if db.enabled() else None
    p = Profile(email=email)
    if not row or not row.get("active"):
        return p  # não autorizado
    p.allowed = True
    p.level = row.get("level") or None
    p.level_locked = bool(row.get("level_locked")) and bool(p.level)
    p.daily_turns = row.get("daily_turns") if row.get("daily_turns") is not None else DEFAULT_DAILY_TURNS
    p.live_enabled = bool(row.get("live_enabled"))
    p.live_daily_minutes = int(row.get("live_daily_minutes") or LIVE_DAILY_MINUTES)
    policy = row.get("key_policy") or {}
    enc = row.get("keys_enc") or {}
    for pr in PROVIDERS:
        mode = policy.get(pr, "owner")
        p.policy[pr] = mode
        if mode == "owner":
            p.keys[pr] = owner_key(pr)
        elif mode == "own":
            p.keys[pr] = decrypt(enc[pr]) if enc.get(pr) else None
        else:
            p.keys[pr] = None
    return p
