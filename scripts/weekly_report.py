"""Envia o resumo da semana para cada família (Telegram e/ou e-mail, conforme os pais escolheram).

Roda toda segunda pelo GitHub Actions (.github/workflows/weekly-report.yml).
Precisa de: DATABASE_URL e, conforme o canal, TELEGRAM_BOT_TOKEN / SMTP_USER + SMTP_PASSWORD.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import db, family, notify, report  # noqa: E402


def main() -> int:
    if not db.enabled():
        print("Sem DATABASE_URL: nada a fazer.")
        return 1
    sent = 0
    for u in db.list_users():
        em = u["email"]
        if not u.get("active"):
            continue
        is_kid_account = family.is_family(em) or u.get("level") == "crianca"
        cfg = notify.load_cfg(db.get_pref, em)
        if not is_kid_account or not cfg["channels"]:
            continue
        name = report.display_name(em)
        log = notify.send_report(cfg, name, report.family_report(em))
        print(f"{name}: " + " · ".join(log))
        sent += sum(1 for x in log if x.startswith("✅"))
    print(f"Pronto: {sent} envio(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
