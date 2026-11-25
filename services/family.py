"""Conta da família: o pai entra com o Google dele, cria a conta, e dentro dela há dois perfis.

👧 Perfil Criança: abre por padrão, só o que é da criança.
👨‍👩‍👧 Perfil Pais: protegido por PIN de 4 números (o pai cadastra; o admin pode zerar).
Tudo fica em ep_prefs da conta: familia (JSON), pin (salt$hash), consent_parents, resumo (JSON), limites.
"""
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone

from services import db

BRT = timezone(timedelta(hours=-3))

PRIVACY_TEXT = """
**O que o app faz:** é um app de prática de inglês. A criança faz missões, ganha estrelas e conversa por voz com o
robozinho Bip. Não tem anúncios, compras nem conversa com outras pessoas.

**Para onde vão os dados:**
- 🎤 **Voz**: a gravação da fala é enviada ao **Groq** só para virar texto. O app não guarda o áudio.
- 💬 **Conversa e missões**: o texto vai para o **Claude (Anthropic)** para criar as respostas e as missões. No modo
  "ao vivo", vai para o **Gemini (Google)**.
- 🔊 **Voz do Bip**: o texto é enviado a um serviço de voz (Microsoft Edge, Google ou OpenAI) para virar áudio.
- 🗄️ **Guardado no banco do app (Neon)**: e-mail da conta, nome do astronauta, conversas em texto, respostas das
  missões, estrelas e tempo de uso. O e-mail é usado só para entrar.
- 🎬 **Vídeos**: vêm do YouTube no modo de privacidade reforçada (sem cookies de anúncio).

**Combinados de segurança:** o Bip nunca pede dados pessoais (endereço, escola, telefone). Se a criança contar algo
assim, ele muda de assunto e diz para falar com os pais. O responsável pode **ler todas as conversas** no Histórico,
pedir para **apagar tudo** no Perfil Pais, e escolher limite de **tempo** e de **planetas por dia**.
"""


def info(email: str) -> dict:
    try:
        return json.loads(db.get_pref(email, "familia") or "{}")
    except Exception:
        return {}


def is_family(email: str) -> bool:
    return bool(info(email))


def _hash(pin: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 120_000).hex()


def set_pin(email: str, pin: str) -> None:
    salt = secrets.token_hex(8)
    db.set_pref(email, "pin", f"{salt}${_hash(pin, salt)}")


def has_pin(email: str) -> bool:
    return bool(db.get_pref(email, "pin"))


def check_pin(email: str, pin: str) -> bool:
    raw = db.get_pref(email, "pin") or ""
    if "$" not in raw:
        return False
    salt, h = raw.split("$", 1)
    return secrets.compare_digest(_hash(pin, salt), h)


def reset_pin(email: str) -> None:
    db.set_pref(email, "pin", "")


def valid_pin(pin: str) -> bool:
    return pin.isdigit() and len(pin) == 4 and pin not in ("0000", "1234", "1111")


def signup_mode() -> str:
    """'approval' (padrão: o admin aprova cada família nova) ou 'open' (entra direto)."""
    return db.get_pref("__app__", "signup") or "approval"


def create(email: str, parent: str, child: str, pin: str, channels: list[str], emails: str) -> bool:
    """Cria a conta da família. Retorna True se já entra liberada."""
    now = datetime.now(BRT).strftime("%d/%m/%Y %H:%M")
    open_now = signup_mode() == "open"
    db.upsert_user(email, name=parent, active=open_now, level=None, level_locked=False, daily_turns=60,
                   live_enabled=False, live_daily_minutes=10)
    db.set_pref(email, "familia", json.dumps({"parent": parent, "child": child, "created": now}, ensure_ascii=False))
    set_pin(email, pin)
    db.set_pref(email, "consent_parents", now)
    db.set_pref(email, "resumo", json.dumps({"channels": channels, "emails": emails, "telegram": ""}))
    if not (db.get_pref(email, "astronauta") or ""):
        db.set_pref(email, "astronauta", f"{child}|🚀|🧑‍🚀")
    return open_now


def connect_code(email: str) -> str:
    """Código curto e fixo da família, usado para achar o grupo dela no Telegram."""
    code = db.get_pref(email, "tg_code")
    if not code:
        code = f"EP{secrets.randbelow(900000) + 100000}"
        db.set_pref(email, "tg_code", code)
    return code


def pending() -> list[dict]:
    """Famílias aguardando aprovação do admin."""
    out = []
    for u in db.list_users():
        if not u.get("active") and not u.get("is_admin"):
            f = info(u["email"])
            if f:
                out.append({"email": u["email"], **f})
    return out
