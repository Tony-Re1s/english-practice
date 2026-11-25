"""Resumo da semana para a família (usado na tela do Histórico e no envio automático por Telegram/e-mail)."""
import json

from config import LEVELS
from services import compete, db, galaxy, learn, rewards, space
from syllabus import topic_for


def kid_minutes_today(who: str) -> int:
    import datetime as _dt
    day = _dt.datetime.now(compete.BRT).strftime("%Y-%m-%d")
    try:
        return int(float((db.get_pref(who, f"tempo:{day}") if db.enabled() else None) or 0) // 60)
    except ValueError:
        return 0


def display_name(who: str) -> str:
    astro = (db.get_pref(who, "astronauta") or "").split("|")[0].strip()
    if astro:
        return astro
    u = db.get_user(who) or {}
    return u.get("name") or who.split("@")[0]


def learned_words(who: str, lvl: str = "crianca", days: int | None = None) -> tuple[list[str], list[str]]:
    """(palavras que já acerta, palavras para treinar), a partir das respostas das missões."""
    import datetime as _dt
    status: dict[str, bool] = {}
    since = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=days)) if days else None
    for a in (db.attempts(who, lvl) if db.enabled() else []):
        if since and a["ts"] and a["ts"] < since:
            continue
        ex = a.get("content") or {}
        ans = a.get("answers") or {}
        if isinstance(ex, str):
            ex = json.loads(ex)
        if isinstance(ans, str):
            ans = json.loads(ans)
        for i, q in enumerate(ex.get("questions") or [], 1):
            word = str(q.get("answer", "")).strip()
            if not word or str(i) not in ans or len(word.split()) > 3:
                continue
            status[word.lower()] = learn.check_answer(q, ans[str(i)], lenient=True)   # vale a tentativa mais recente
    know = sorted(w for w, ok in status.items() if ok)
    review = sorted(w for w, ok in status.items() if not ok)
    return know, review


def family_report(who: str) -> str:
    """Texto curto e animado sobre os últimos 7 dias, pronto para mandar para a família."""
    r = db.week_report(who)
    name = display_name(who)
    kid_ex = [e for e in r["exercises"] if LEVELS.get(e["level"], {}).get("kids")]
    lines = [f"🌟 Semana de inglês — {name}", ""]
    if kid_ex:
        ok = [e for e in kid_ex if galaxy.passed(e["score"], e["total"])]
        stars = sum(galaxy.stars_for(e["score"], e["total"]) for e in kid_ex)
        lines.append(f"🚀 Planetas explorados: {len(ok)} ({stars} ⭐)")
        for e in ok[-6:]:
            info = space.stop(e["num"])
            lines.append(f"   • {info['en']} — {topic_for(e['level'], e['num'])[0]}")
        days = db.kid_days(who, kid_ex[0]["level"])
        lines.append(f"🔥 Sequência: {rewards.streak(days)} dia(s) seguidos")
        know, review = learned_words(who, kid_ex[0]["level"], days=7)
        if know:
            lines.append(f"✅ Palavras que acertou: {', '.join(know[:15])}")
        if review:
            lines.append(f"🔁 Para treinar: {', '.join(review[:10])}")
        mins = kid_minutes_today(who)
        if mins:
            lines.append(f"⏳ Tempo no app hoje: {mins} min")
    other = [e for e in r["exercises"] if not LEVELS.get(e["level"], {}).get("kids")]
    if other:
        lines.append(f"📝 Exercícios feitos: {len(other)}")
    lines.append(f"💬 Conversas: {r['talks']} ({r['talk_turns']} falas em inglês)")
    lines.append(f"🎬 Vídeos com perguntas: {r['videos']}")
    if not r["exercises"] and not r["talks"] and not r["videos"]:
        lines.append("Ainda não teve atividade nesta semana — que tal uma missão hoje? 🚀")
    else:
        lines += ["", "Parabéns pelo esforço! 👏 Continue assim!"]
    return "\n".join(lines)
