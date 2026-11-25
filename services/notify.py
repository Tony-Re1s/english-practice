"""Envio do resumo para a família: Telegram (bot) e/ou e-mail (SMTP, ex.: Gmail com senha de app).

Chaves (nos Secrets do app e nos Secrets do GitHub, para o envio automático):
  TELEGRAM_BOT_TOKEN = token do bot criado no @BotFather
  SMTP_USER          = e-mail que envia (ex.: conta Gmail criada para o app)
  SMTP_PASSWORD      = senha de app desse e-mail (Gmail: Conta Google → Segurança → Senhas de app)
  SMTP_HOST / SMTP_PORT (opcionais; padrão smtp.gmail.com / 465)
"""
import json
import os
import smtplib
import ssl
import urllib.parse
import urllib.request
from email.message import EmailMessage


def secret(name: str) -> str:
    try:
        import streamlit as st
        v = st.secrets.get(name)
        if v:
            return str(v)
    except Exception:
        pass
    return os.environ.get(name, "")


def telegram_ready() -> bool:
    return bool(secret("TELEGRAM_BOT_TOKEN"))


def email_ready() -> bool:
    return bool(secret("SMTP_USER") and secret("SMTP_PASSWORD"))


def _tg(method: str, params: dict) -> dict:
    url = f"https://api.telegram.org/bot{secret('TELEGRAM_BOT_TOKEN')}/{method}"
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(url, data=data, timeout=20) as r:
        out = json.loads(r.read().decode())
    if not out.get("ok"):
        raise RuntimeError(out.get("description", "Telegram recusou"))
    return out["result"]


def telegram_bot_name() -> str:
    try:
        return _tg("getMe", {}).get("username", "")
    except Exception:
        return ""


def telegram_chats() -> list[dict]:
    """Grupos/conversas que falaram com o bot recentemente (para achar o grupo da família)."""
    seen, out = set(), []
    for u in _tg("getUpdates", {"limit": 100}):
        msg = u.get("message") or u.get("my_chat_member") or u.get("channel_post") or {}
        chat = msg.get("chat") or {}
        if chat.get("id") and chat["id"] not in seen:
            seen.add(chat["id"])
            name = chat.get("title") or " ".join(x for x in (chat.get("first_name"), chat.get("last_name")) if x)
            out.append({"id": str(chat["id"]), "name": name or str(chat["id"]),
                        "type": {"private": "conversa", "group": "grupo", "supergroup": "grupo"}.get(chat.get("type"), chat.get("type"))})
    return out


def telegram_find(code: str) -> dict | None:
    """Acha o grupo/conversa onde alguém mandou o código da família (ex.: '/start EP123456')."""
    for u in reversed(_tg("getUpdates", {"limit": 100})):
        msg = u.get("message") or u.get("channel_post") or {}
        if code in (msg.get("text") or ""):
            chat = msg.get("chat") or {}
            name = chat.get("title") or " ".join(x for x in (chat.get("first_name"), chat.get("last_name")) if x)
            return {"id": str(chat.get("id")), "name": name or "conversa"}
    return None


def telegram_send(chat_id: str, text: str) -> None:
    _tg("sendMessage", {"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": "true"})


def email_send(to: list[str], subject: str, text: str) -> None:
    msg = EmailMessage()
    msg["From"] = f"English Practice <{secret('SMTP_USER')}>"
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject
    msg.set_content(text)
    host, port = secret("SMTP_HOST") or "smtp.gmail.com", int(secret("SMTP_PORT") or 465)
    with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=30) as s:
        s.login(secret("SMTP_USER"), secret("SMTP_PASSWORD"))
        s.send_message(msg)


def load_cfg(get_pref, who: str) -> dict:
    try:
        cfg = json.loads(get_pref(who, "resumo") or "{}")
    except Exception:
        cfg = {}
    cfg.setdefault("channels", [])
    cfg.setdefault("emails", "")
    cfg.setdefault("telegram", "")
    return cfg


def send_report(cfg: dict, name: str, text: str) -> list[str]:
    """Manda pelos canais escolhidos. Retorna o que deu certo/errado, para mostrar na tela ou no log."""
    log = []
    if "telegram" in cfg["channels"]:
        try:
            if not telegram_ready():
                raise RuntimeError("falta o TELEGRAM_BOT_TOKEN")
            if not cfg.get("telegram"):
                raise RuntimeError("nenhum grupo escolhido")
            telegram_send(cfg["telegram"], text)
            log.append("✅ Telegram enviado")
        except Exception as e:
            log.append(f"❌ Telegram: {e}")
    if "email" in cfg["channels"]:
        try:
            to = [e.strip() for e in cfg.get("emails", "").replace(";", ",").split(",") if "@" in e]
            if not email_ready():
                raise RuntimeError("falta SMTP_USER/SMTP_PASSWORD")
            if not to:
                raise RuntimeError("nenhum e-mail cadastrado")
            email_send(to, f"🌟 Semana de inglês — {name}", text)
            log.append(f"✅ E-mail enviado para {', '.join(to)}")
        except Exception as e:
            log.append(f"❌ E-mail: {e}")
    return log
