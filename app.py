"""English Practice — parceira de conversação em inglês com voz, correções, níveis, modo ao vivo e painel de usuários."""

import base64
import json
import re
from html import escape as html_escape
import uuid
from datetime import datetime

import streamlit as st

import ui
from config import (DEFAULT_LEVEL, LEVELS, LIVE_MAX_SESSION_MIN, LIVE_MODEL, LIVE_RESET_HOUR_BRT,
                    MAX_HISTORY_TURNS, PROVIDER_LABEL, PROVIDERS)
from prompts import (FREE_TALK_OPEN, FREE_TALK_ROLE, LIVE_SYSTEM, SCENARIOS, START_MESSAGE, TOPIC_ROLE,
                     TUTOR_SYSTEM)
from services import album, compete, family, galaxy, i18n, nav, notify, report, rewards, space, db, learn, live, llm, users, voice
from syllabus import topic_for
from services.voice_chat import voice_chat

st.set_page_config(page_title="English Practice", page_icon="static/favicon.png", layout="centered",
                   initial_sidebar_state="collapsed")
i18n.install()   # menus em inglês no perfil adulto (o infantil e a área dos pais seguem em português)
ui.inject_css()
ui.install_app_icons()


# --- Acesso (login com Google + autorização) ---------------------------------------
def current_email() -> str | None:
    """E-mail logado. Sem a seção [auth] nos Secrets (rodando local), entra como 'local' (admin)."""
    if "auth" not in st.secrets:
        return "local"
    if not st.user.get("is_logged_in", False):
        return None
    return str(st.user.get("email") or "").lower()


email = current_email()
if email is None:
    ui.login_screen("English Practice", "Sua parceira de conversação em inglês, do seu jeito e no seu nível.")
    st.button("Entrar com o Google", on_click=st.login, width="stretch", key="login_btn")
    st.markdown('<div class="lg-foot">Acesso só para contas liberadas pelo administrador.</div>', unsafe_allow_html=True)
    st.stop()

def family_signup() -> None:
    """Primeiro acesso: o pai (ou mãe) cria a conta da família em 3 passos, com explicação em cada um."""
    ui.login_screen("Bem-vindo! 👋", "Vamos criar a conta da família. Leva 1 minuto.")
    st.markdown(f"Você entrou como **{email}**. Esta conta vai ser **dos pais**; dentro dela a criança tem o "
                "perfil dela, e vocês têm uma área protegida por PIN.")
    with st.form("signup"):
        st.markdown("#### 1️⃣ Quem vai usar")
        parent = st.text_input("Seu nome", placeholder="ex.: Ana")
        child = st.text_input("Nome da criança", placeholder="ex.: Matheus",
                              help="É o nome que o robozinho Bip vai usar. Pode ser só o primeiro nome ou um apelido.")
        st.markdown("#### 2️⃣ Seu PIN de pais")
        st.caption("4 números para entrar na área dos pais (limites, relatórios, conversas). "
                   "A criança não precisa saber. Evite 1234 ou 0000.")
        c1, c2 = st.columns(2)
        pin1 = c1.text_input("Crie o PIN", type="password", max_chars=4)
        pin2 = c2.text_input("Repita o PIN", type="password", max_chars=4)
        st.markdown("#### 3️⃣ Resumo da semana e autorização")
        ch = st.multiselect("Como quer receber o resumo toda segunda?", ["E-mail", "Telegram"], default=["E-mail"],
                            help="Telegram você conecta depois, na área dos pais (tem um passo a passo).")
        mails = st.text_input("E-mails que recebem o resumo", value=email,
                              help="Pode colocar mais de um, separado por vírgula (ex.: o seu e o da mãe).")
        with st.expander("📄 Como o app usa os dados (leia antes de autorizar)"):
            st.markdown(family.PRIVACY_TEXT)
        ok = st.checkbox("Sou pai, mãe ou responsável, li como o app usa os dados e autorizo a criança a usar.")
        go = st.form_submit_button("🚀 Criar conta da família", type="primary", width="stretch")
    if go:
        errs = []
        if not parent.strip() or not child.strip():
            errs.append("preencha os dois nomes")
        if pin1 != pin2:
            errs.append("os dois PINs estão diferentes")
        elif not family.valid_pin(pin1):
            errs.append("o PIN precisa ter 4 números (e não pode ser 1234, 0000 ou 1111)")
        if not ok:
            errs.append("marque a autorização")
        if errs:
            st.error("Quase lá: " + "; ".join(errs) + ".")
        else:
            chans = [{"E-mail": "email", "Telegram": "telegram"}[c] for c in ch]
            if family.create(email, parent.strip(), child.strip(), pin1, chans, mails):
                st.rerun()
            st.success("Conta criada! ✅ Agora é só aguardar a liberação do administrador.")
    st.button("Entrar com outra conta", on_click=st.logout, key="login_btn")
    st.stop()


prof = users.load_profile(email)
if not prof.allowed:
    row = db.get_user(email) if db.enabled() else None
    if db.enabled() and not row:
        family_signup()
    elif row and family.is_family(email):
        ui.login_screen("Quase pronto! ⏳", "A conta da família foi criada e está aguardando a liberação do "
                        "administrador. Assim que for liberada, é só abrir o app de novo.", restricted=True)
    else:
        ui.login_screen("Acesso restrito", f"A conta {email} ainda não foi liberada. Peça ao administrador para "
                        "liberar seu e-mail.", restricted=True)
    st.button("Entrar com outra conta", on_click=st.logout, width="stretch", key="login_btn")
    st.stop()

voice.set_keys(prof.keys)  # chaves desta pessoa: a do dono, a própria ou desligada, serviço por serviço


# --- Estado -------------------------------------------------------------------
DEFAULTS = {
    "started": False, "role": "", "context_label": "", "turns": [], "corrections": [],
    "mic_key": 0, "audio": None, "autoplay": False, "summary": None, "voice_used": "",
    "last_error": "", "session_id": None, "system": "", "mode": "maos",
    "live_token": None, "live_session_key": "", "live_msg": "",
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v if not isinstance(v, list) else list(v))
st.session_state.setdefault("reply_seq", 0)       # contadores que nunca zeram
st.session_state.setdefault("listen_token", 0)
st.session_state.setdefault("level", prof.level or DEFAULT_LEVEL)
st.session_state.setdefault("view", "inicio")
st.session_state.setdefault("slow_voice", False)
st.session_state.setdefault("show_text", True)
st.session_state.setdefault("live_blocked", False)
ss = st.session_state
if "theme_pref" not in ss:
    try:
        ss.theme_pref = (db.get_pref(email, "tema") if db.enabled() else None) or "london"
    except Exception:
        ss.theme_pref = "london"


def current_theme() -> str:
    """Nível Criança → Espaço; os outros níveis → o tema escolhido em Ajustes (Londres ou Clássico).
    Existe um nível só (ss.level), que vale para o app inteiro — Falar, Aprender e todas as telas."""
    if ss.view == "aprender" and ss.get("kid_inside") and LEVELS.get(ss.get("kid_lvl", ""), {}).get("kids"):
        return "space"
    if LEVELS.get(ss.level, {}).get("kids"):
        return "space"
    return ss.theme_pref


def _set_level(widget_key: str) -> None:
    """Callback dos seletores de nível: muda o nível do app inteiro (roda antes da tela ser desenhada)."""
    v = ss.get(widget_key)
    if v:
        ss.level = v
        ss.kid_inside = None


def sound_cfg() -> dict:
    """Preferências de som da conta: música de fundo, toques, festa, volume e o mudo rápido (🔇)."""
    if "sound" not in ss:
        try:
            ss.sound = json.loads((db.get_pref(email, "sons") if db.enabled() else None) or "{}")
        except Exception:
            ss.sound = {}
        for k, v in {"music": True, "taps": True, "fx": True, "vol": 55, "muted": False}.items():
            ss.sound.setdefault(k, v)
    return ss.sound


def save_sound() -> None:
    if db.enabled():
        db.set_pref(email, "sons", json.dumps(ss.sound))


_th = current_theme()
_snd = dict(sound_cfg())
if _th == "london":          # adulto: só a trilha de Londres; os "plins" e festas são do infantil
    _snd.update(taps=False, fx=False)
_snd.update(talking=bool(ss.get("started")) and not ss.get("summary"), en=bool(ss.get("_ui_en")))
_ev = ui.apply_theme(_th, _snd) or {}
if _ev.get("mute") in ("on", "off") and (_ev["mute"] == "on") != ss.sound["muted"]:
    ss.sound["muted"] = _ev["mute"] == "on"
    save_sound()
if isinstance(_ev.get("vol"), (int, float)) and int(_ev["vol"]) != ss.sound["vol"]:
    ss.sound["vol"] = int(_ev["vol"])
    save_sound()
voice.set_kid_voice(bool(LEVELS.get(ss.level, {}).get("kids")))   # modo Criança: voz infantil de robozinho
if prof.level_locked:
    ss.level = prof.level


def log(**kw) -> None:
    """Registra uma chamada de IA no banco (se configurado)."""
    db.log_usage(email, ss.session_id, **kw)


def api_messages() -> list[dict]:
    """Monta o histórico no formato da API (começa sempre com a mensagem de abertura)."""
    turns = ss.turns[-MAX_HISTORY_TURNS:]
    if turns and turns[0]["role"] == "user":
        turns = turns[1:]
    msgs = [{"role": "user", "content": START_MESSAGE}]
    msgs += [{"role": t["role"], "content": t["text"]} for t in turns]
    return msgs


def call_tutor() -> dict:
    try:
        data = llm.tutor_turn(ss.system, api_messages(), prof.keys.get("anthropic"))
    except Exception as e:
        log(step="conversa", provider="Anthropic", model=llm.CHAT_MODEL, ok=False, error=str(e)[:500])
        raise
    u = data.pop("_usage", {})
    log(step="conversa", provider="Anthropic", model=u.get("model", llm.CHAT_MODEL), ok=True,
        input_tokens=u.get("input_tokens"), output_tokens=u.get("output_tokens"))
    return data


def set_audio(text: str, pace: str | None = None) -> None:
    try:
        pace = pace or ("slow" if ss.slow_voice else LEVELS[ss.level]["pace"])
        data, mime, provider = voice.speak(text, pace=pace, log=log)
        ss.audio = (data, mime)
        ss.voice_used = f"voz: {provider}"
        ss.autoplay = True
        ss.reply_seq += 1
    except Exception as e:  # voz é opcional: a conversa segue sem ela
        ss.audio = None
        st.toast(f"Não consegui gerar o áudio: {e}", icon="⚠️")


def assistant_says(data: dict) -> None:
    ss.turns.append({"role": "assistant", "text": data["reply"], "suggestions": data["suggestions"]})
    db.add_turn(ss.session_id, "assistant", data["reply"])
    set_audio(data["reply"])


def undo_last_exchange() -> None:
    """O app entendeu errado: tira a última fala do aluno e a resposta, e a parceira repete a pergunta anterior."""
    if len(ss.turns) >= 2 and ss.turns[-1]["role"] == "assistant" and ss.turns[-2]["role"] == "user":
        ss.turns.pop()
        wrong = ss.turns.pop()
        if wrong.get("correction") and ss.corrections and ss.corrections[-1] == wrong["correction"]:
            ss.corrections.pop()
        prev = next((t for t in reversed(ss.turns) if t["role"] == "assistant"), None)
        if prev:
            set_audio(prev["text"])


def reset_session() -> None:
    next_mic = ss.mic_key + 1
    for k, v in DEFAULTS.items():
        if k == "mode":
            continue
        ss[k] = v if not isinstance(v, list) else list(v)
    ss.mic_key = next_mic


def turns_left() -> int | None:
    if prof.daily_turns is None or not db.enabled():
        return None
    return max(0, int(prof.daily_turns) - db.turns_today(email))


def live_status() -> tuple[bool, str, float]:
    """(pode usar?, motivo se não puder, segundos já usados hoje)."""
    used = db.live_seconds_today(email) if db.enabled() else 0.0
    if not prof.live_enabled:
        return False, "desativado para esta conta", used
    if not prof.keys.get("gemini"):
        return False, "sem chave do Gemini", used
    if ss.live_blocked or (db.enabled() and db.live_blocked_since_reset(LIVE_RESET_HOUR_BRT)):
        return False, "a cota grátis do Gemini acabou hoje (renova por volta das 5h)", used
    if used >= prof.live_daily_minutes * 60:
        return False, f"seus {prof.live_daily_minutes} minutos de hoje acabaram", used
    return True, "", used


def start_session(role: str, context_label: str) -> None:
    reset_session()
    lv = LEVELS[ss.level]
    ss.role, ss.started = role, True
    ss.context_label = f"{context_label} · {lv['label']}"
    ss.session_id = db.start_session(email, ss.level, ss.context_label + (" · ⚡ ao vivo" if ss.mode == "aovivo" else ""))
    if ss.mode == "aovivo":
        ss.system = LIVE_SYSTEM.format(role=role, cefr=lv["cefr"], level_guide=lv["guide"])
        with st.spinner("Preparando a chamada..."):
            ss.live_token = live.create_token(prof.keys["gemini"])
        ss.live_session_key = uuid.uuid4().hex
        return
    ss.system = TUTOR_SYSTEM.format(role=role, cefr=lv["cefr"], level_guide=lv["guide"])
    with st.spinner("Preparando a conversa..."):
        data = call_tutor()
    assistant_says(data)


def handle_user(text: str) -> None:
    text = text.strip()
    if not text:
        return
    left = turns_left()
    if left is not None and left <= 0:
        ss.last_error = "Você chegou ao limite de falas de hoje. Volte amanhã! 🙂"
        return
    ss.turns.append({"role": "user", "text": text})
    try:
        with st.spinner("Pensando..."):
            data = call_tutor()
    except Exception:
        ss.turns.pop()
        raise
    corr = data.get("correction")
    if corr and corr.get("better") and corr["better"].strip().lower() != text.lower():
        ss.turns[-1]["correction"] = corr
        ss.corrections.append(corr)
    else:
        corr = None
    db.add_turn(ss.session_id, "user", text, corr)
    assistant_says(data)
    ss.mic_key += 1
    if data.get("end_session"):  # você pediu para encerrar falando ("let's stop here")
        finish_session()


def handle_audio(audio: bytes, mime: str) -> None:
    try:
        with st.spinner("Ouvindo..."):
            # contexto: a última fala da parceira + as sugestões → o reconhecimento erra bem menos
            last = next((t for t in reversed(ss.turns) if t["role"] == "assistant"), None)
            ctx = ""
            if last:
                ctx = last["text"] + " " + " ".join(last.get("suggestions") or [])
            m = re.search(r"use mostly these words and structures: (.*?)\. Ask", ss.get("role") or "")
            if m:   # modo infantil: as palavras da fase ajudam a entender a voz de criança
                ctx = m.group(1) + ". " + ctx
            heard, provider = voice.transcribe(audio, mime, log=log, context=ctx)
        ss.voice_used = f"ouvido por: {provider}"
        ss.last_error = ""
        handle_user(heard)
    except Exception as e:
        print(f"[voz] falha ao ouvir ({mime}, {len(audio)} bytes): {e}", flush=True)
        ss.last_error = f"Não consegui entender o áudio. Detalhe técnico: {e}"
    finally:
        ss.listen_token += 1


def transcript_text() -> str:
    who = {"user": "Aluno", "assistant": "Parceira"}
    return "\n".join(f"{who[t['role']]}: {t['text']}" for t in ss.turns)


def finish_session() -> None:
    """Encerra a conversa: gera o resumo, desliga o microfone e grava no histórico."""
    if not any(t["role"] == "user" for t in ss.turns):
        db.end_session(ss.session_id, None)
        reset_session()
        return
    with st.spinner("Montando seu resumo..."):
        try:
            ss.summary, u = llm.session_summary(transcript_text(), ss.corrections, LEVELS[ss.level]["cefr"],
                                                prof.keys.get("anthropic"))
            log(step="resumo", provider="Anthropic", model=u["model"], ok=True,
                input_tokens=u["input_tokens"], output_tokens=u["output_tokens"])
        except Exception as e:
            log(step="resumo", provider="Anthropic", model=llm.SUMMARY_MODEL, ok=False, error=str(e)[:500])
            ss.summary = "_Não consegui gerar o resumo desta vez._"
    db.end_session(ss.session_id, ss.summary)


def handle_live_end(res: dict) -> None:
    """A chamada ao vivo terminou: guarda a transcrição, registra o tempo e gera o resumo."""
    secs = float(res.get("seconds") or 0)
    err = res.get("error") or ""
    if err == "cota":
        ss.live_blocked = True
        log(step="ao vivo", provider="Gemini", model=LIVE_MODEL, ok=False, audio_seconds=secs, error="cota esgotada")
    elif err:
        log(step="ao vivo", provider="Gemini", model=LIVE_MODEL, ok=False, audio_seconds=secs, error=str(err)[:500])
    if secs > 0:
        log(step="ao vivo", provider="Gemini", model=LIVE_MODEL, ok=True, audio_seconds=secs)
    for t in res.get("transcript") or []:
        role = "user" if t.get("role") == "user" else "assistant"
        text = str(t.get("text") or "").strip()
        if text:
            ss.turns.append({"role": role, "text": text})
            db.add_turn(ss.session_id, role, text)
    ss.live_token = None
    if any(t["role"] == "user" for t in ss.turns):
        finish_session()
    else:
        db.end_session(ss.session_id, None)
        msg = ("A cota grátis do Gemini acabou por hoje — use o modo normal." if err == "cota"
               else f"A chamada não começou. {('Detalhe: ' + err) if err else ''}")
        reset_session()
        ss.live_msg = msg


# --- Navegação (barra de baixo + menu lateral ☰) -----------------------------------------
# Conta da família: abre no Perfil Criança; o Perfil Pais pede o PIN.
FAMILY = (not prof.is_admin) and db.enabled() and family.is_family(email)
if FAMILY:
    ss.setdefault("fam_mode", "kid")
    if ss.fam_mode == "kid":
        prof.level, prof.level_locked = "crianca", True
        ss.level = "crianca"
    elif LEVELS.get(ss.level, {}).get("kids"):
        ss.level = DEFAULT_LEVEL     # na área dos pais, o app volta ao inglês de adulto
KIDS_PROFILE = (not prof.is_admin) and bool(LEVELS.get(prof.level or "", {}).get("kids"))
if "ui_lang" not in ss:
    ss.ui_lang = (db.get_pref(email, "ui_lang") if db.enabled() else None) or "en"
# inglês só no perfil adulto: nunca no infantil nem na conta da família (os pais podem não falar inglês)
ss._ui_en = (ss.ui_lang == "en") and not FAMILY and not KIDS_PROFILE and not LEVELS.get(ss.level, {}).get("kids")
NAV_ITEMS = [("inicio", "💬", "Falar"), ("aprender", "📚", "Aprender"), ("historico", "📊", "Histórico"),
             ("pais", "👨‍👩‍👧", "Pais"), ("ajustes", "⚙️", "Ajustes"), ("usuarios", "👥", "Usuários")]
if KIDS_PROFILE:
    NAV_ITEMS = [n for n in NAV_ITEMS if n[0] in ("inicio", "aprender", "ajustes") or (FAMILY and n[0] == "pais")]
    if FAMILY:
        NAV_ITEMS = [(k, "🔒" if k == "pais" else i, t) for k, i, t in NAV_ITEMS]
elif FAMILY:
    NAV_ITEMS = [n for n in NAV_ITEMS if n[0] != "usuarios"]
else:
    NAV_ITEMS = [n for n in NAV_ITEMS if n[0] not in ("usuarios", "pais") or prof.is_admin]
    if prof.is_admin:
        NAV_ITEMS = [n for n in NAV_ITEMS if n[0] != "pais"]
NAV = {k: f"{i} {t}" for k, i, t in NAV_ITEMS}


def bottom_nav(bar: bool = True) -> None:
    """bar=True: barra completa no rodapé. bar=False: só o botão ☰ (usado durante a conversa)."""
    items = [{"key": k, "icon": i, "label": t} for k, i, t in NAV_ITEMS]
    if not bar:   # abre espaço para o botão ☰ que fica no canto de cima
        st.markdown("<style>.block-container{padding-top:4.4rem !important}</style>", unsafe_allow_html=True)
    with st.bottom:
        go = nav.nav(items, ss.view, current_theme(), bar=bar, key="nav_bar" if bar else "nav_fab")
    if go and go != ss.view:
        ss.view = go
        if go != "aprender":
            ss.kid_inside = None
        st.rerun()


# --- Tela: histórico -------------------------------------------------------------
def history_view() -> None:
    ui.hero("📊 Histórico e uso", "Quais IAs foram usadas, quanto custou (estimado) e suas conversas anteriores.")
    if not db.enabled():
        st.info("O registro não está ligado: falta o **DATABASE_URL** (Neon) nos Secrets do app.", icon="🗄️")
        return
    import pandas as pd

    who = email
    if prof.is_admin:
        people = sorted(set(db.known_users()) | {email})
        who = st.selectbox("Pessoa", people, index=people.index(email))
    with st.expander("🏁 Corrida Espacial da semana" + (" (todo mundo)" if prof.is_admin else " (você e amigos)"),
                     expanded=False):
        st.caption(f"Cada um corre até a própria meta (criança {compete.GOAL_KID} pts, adulto {compete.GOAL_ADULT} pts). "
                   "⭐ estrela = 10 · 💬 fala = 2 · 🎬 vídeo = 15 · recomeça toda segunda")
        only = None if prof.is_admin else ({email} | db.friends(email)["ok"])
        st.markdown(race_track_html(compete.board(only=only)), unsafe_allow_html=True)
        st.markdown("**⚡ Recordes do Desafio Relâmpago**")
        st.markdown(race_board_html(compete.challenge_board(only=only), "score", "pts"), unsafe_allow_html=True)
    know, review = report.learned_words(who)
    if know or review:
        with st.expander(f"📚 O que aprendeu no Infantil ({len(know)} palavras)", expanded=False):
            st.markdown("**✅ Já acerta:** " + (", ".join(know) if know else "—"))
            st.markdown("**🔁 Ainda erra (vale treinar junto):** " + (", ".join(review) if review else "nada! 🎉"))
            st.caption("Conta a tentativa mais recente de cada palavra nas missões. As conversas dele ficam em "
                       "🗂️ Conversas anteriores, mais abaixo.")
    with st.expander("📨 Resumo da semana para a família", expanded=False):
        txt = report.family_report(who)
        st.text_area("Resumo", txt, height=220, label_visibility="collapsed")
        cfg = notify.load_cfg(db.get_pref, who)
        st.caption("Canais escolhidos: " + (", ".join(cfg["channels"]) or "nenhum") +
                   ". Vai sozinho toda segunda de manhã.")
        if cfg["channels"] and st.button("📨 Enviar agora", key="hist_send"):
            for line in notify.send_report(cfg, report.display_name(who), txt):
                st.write(line)
    days = st.segmented_control("Período", [7, 30, 90], default=30, format_func=lambda d: f"{d} dias") or 30
    df = pd.DataFrame(db.usage_by_provider(who, days))
    if df.empty:
        st.caption("Nenhum uso registrado ainda neste período.")
    else:
        df["custo_usd"] = df["custo_usd"].astype(float)
        openai_calls = int(df.loc[df["servico"] == "OpenAI", "chamadas"].sum())
        live_min = db.live_seconds_today(who) / 60
        m1, m2, m3 = st.columns(3)
        m1.metric("Custo estimado", f"US$ {df['custo_usd'].sum():.3f}")
        m2.metric("Chamadas à OpenAI", openai_calls, help="A OpenAI só entra quando os serviços grátis falham.")
        m3.metric("Ao vivo hoje", f"{live_min:.1f} min")
        if openai_calls:
            st.warning(f"A OpenAI (crédito pago) foi usada {openai_calls} vez(es) nos últimos {days} dias.", icon="💳")
        else:
            st.success("Nenhum uso da OpenAI no período: só serviços grátis e o Claude.", icon="✅")
        st.dataframe(df, hide_index=True, width="stretch")
    with st.expander("🕒 Últimas chamadas (inclui falhas e trocas de serviço)"):
        st.dataframe(pd.DataFrame(db.usage_recent(who)), hide_index=True, width="stretch")
    st.caption("Custos estimados pela tabela de preços do app. Valores oficiais: platform.claude.com e "
               "platform.openai.com/usage. O Gemini ao vivo roda no plano grátis.")

    learning_history(who)

    st.markdown("### 🗂️ Conversas anteriores")
    sess = db.sessions_recent(who)
    if not sess:
        st.caption("Nenhuma conversa registrada ainda.")
        return
    label = {s_["id"]: f"{s_['inicio']} · {s_['conversa']} · {s_['falas']} falas" for s_ in sess}
    sid = st.selectbox("Abrir conversa", list(label), format_func=lambda i: label[i])
    chosen = next(s_ for s_ in sess if s_["id"] == sid)
    for t in db.session_turns(sid):
        if t["role"] == "assistant":
            ui.ai_bubble(t["text"])
        else:
            ui.user_bubble(t["text"])
            c = t.get("correction")
            if isinstance(c, str):
                c = json.loads(c)
            if c:
                ui.correction(c.get("better", ""), c.get("tip_pt", ""))
    if chosen.get("summary"):
        with st.expander("📋 Resumo dessa conversa", expanded=True):
            st.markdown(chosen["summary"])


def learning_history(who: str) -> None:
    import pandas as pd

    st.markdown("### 📚 Trilhas concluídas")
    ex = db.exercise_history(who)
    vd = db.video_history(who)
    c1, c2 = st.columns(2)
    c1.metric("Exercícios de gramática", len(ex))
    c2.metric("Vídeos", len(vd))
    if ex:
        st.markdown("**📝 Gramática**")
        st.dataframe(pd.DataFrame(ex), hide_index=True, width="stretch")
    if vd:
        st.markdown("**🎬 Vídeos**")
        st.dataframe(pd.DataFrame(vd), hide_index=True, width="stretch")
    if not ex and not vd:
        st.caption("Nenhum exercício ou vídeo concluído ainda.")


# --- Tela: ajustes ---------------------------------------------------------------
def settings_view() -> None:
    ui.hero("⚙️ Ajustes", "Do seu jeito: voz, texto e sua conta.")
    ss.slow_voice = st.toggle("🐢 Voz devagar", value=ss.slow_voice, help="A parceira fala mais devagar sempre.")
    ss.show_text = st.toggle("👀 Mostrar texto das respostas", value=ss.show_text,
                             help="Desligue para treinar a escuta: o texto fica escondido até você abrir.")
    if not prof.level_locked:
        ss.set_level = ss.level
        st.selectbox("Nível", list(LEVELS), format_func=lambda k: LEVELS[k]["label"], key="set_level",
                     on_change=_set_level, args=("set_level",))
    themes = {"london": "🇬🇧 Londres (imersivo)", "classic": "🤍 Clássico (claro)"}
    pick = st.segmented_control("Visual do app", list(themes), format_func=lambda k: themes[k],
                                default=ss.theme_pref if ss.theme_pref in themes else "london", key="theme_pick")
    if pick and pick != ss.theme_pref:
        ss.theme_pref = pick
        if db.enabled():
            db.set_pref(email, "tema", pick)
        st.rerun()
    st.caption("No nível Infantil o app vira sempre o tema Espaço.")
    if not FAMILY and not KIDS_PROFILE:
        langs = {"en": "🇬🇧 English", "pt": "🇧🇷 Português"}
        lp = st.segmented_control("🌐 Idioma dos menus", list(langs), format_func=lambda k: langs[k],
                                  default=ss.ui_lang, key="ui_lang_pick")
        if lp and lp != ss.ui_lang:
            ss.ui_lang = lp
            # seletores com chave guardam o texto exibido: zera para não ficarem presos no idioma antigo
            for k in ("learn_level", "set_level", "theme_pick", "kid_limit_pick", "kid_minutes_pick", "signup_mode",
                      "fam_pick", "ui_lang_pick"):
                ss.pop(k, None)
            if db.enabled():
                db.set_pref(email, "ui_lang", lp)
            st.rerun()
    if KIDS_PROFILE or LEVELS.get(ss.level, {}).get("kids") or ss.get("astro"):
        with st.expander("👩‍🚀 Meu astronauta (nome, rosto e nave)"):
            astro_form("astro_settings", "Mude o nome, quem você é no jogo ou a nave quando quiser:")
    if prof.is_admin and db.enabled():
        opts = {3: "3 por dia", 5: "5 por dia", 10: "10 por dia", 0: "Sem limite"}
        cur_lim = daily_limit()
        new_lim = st.segmented_control("🪐 Planetas novos por dia (perfil infantil)", list(opts),
                                       format_func=lambda k: opts[k], default=cur_lim if cur_lim in opts else 3,
                                       key="kid_limit_pick")
        if new_lim is not None and new_lim != cur_lim:
            db.set_pref("__app__", "kid_limit", str(new_lim))
            st.toast("Limite atualizado ✅")
        st.caption("Refazer planetas que ele já visitou e o ⚡ Desafio nunca contam no limite.")
        mopts = {0: "Sem limite", 15: "15 min", 30: "30 min", 45: "45 min", 60: "1 hora"}
        cur_m = kid_minutes_limit()
        new_m = st.segmented_control("⏳ Tempo de uso por dia (perfil infantil)", list(mopts),
                                     format_func=lambda k: mopts[k], default=cur_m if cur_m in mopts else 0,
                                     key="kid_minutes_pick")
        if new_m is not None and new_m != cur_m:
            db.set_pref("__app__", "kid_minutes", str(new_m))
            st.toast("Tempo atualizado ✅")
        st.caption("Conta só o tempo usando de verdade. Quando acaba, o Bip se despede e o app só volta no dia seguinte.")
    if current_theme() in ("space", "london"):
        with st.expander("🔊 Sons e música", expanded=KIDS_PROFILE):
            snd = sound_cfg()
            changed = False
            opts = (("music", "🎵 Música de fundo"), ("taps", "👆 Som quando toca nos botões"),
                    ("fx", "🎉 Sons de acerto, erro e festa"))
            if current_theme() == "london":
                opts = opts[:1]
            for k, lab in opts:
                v = st.toggle(lab, value=bool(snd[k]) and not snd["muted"], key=f"snd_{k}")
                if v != (bool(snd[k]) and not snd["muted"]):
                    snd[k], snd["muted"], changed = v, False, True
            vol = st.slider("Volume da música", 0, 100, int(snd["vol"]), step=10, key="snd_vol",
                            disabled=not snd["music"])
            if vol != snd["vol"]:
                snd["vol"], changed = vol, True
            st.caption("Também dá para mudar o volume ou silenciar tudo no botão 🔊 no canto de cima da tela. "
                       "A música abaixa sozinha quando o app fala ou um vídeo toca, e fica desligada durante a conversa por voz.")
            if changed:
                save_sound()
                st.rerun()
    if KIDS_PROFILE:
        return
    with st.expander("🔒 Privacidade e dados"):
        st.markdown(PRIVACY_TEXT)
        if db.enabled():
            sure = st.checkbox("Quero apagar todas as conversas desta conta (não dá para desfazer).", key="del_conv_ok")
            if st.button("🗑️ Apagar minhas conversas", disabled=not sure, key="del_conv"):
                n = db.delete_conversations(email)
                st.success(f"Pronto: {n} conversa(s) apagada(s).")
    st.divider()
    st.markdown(f"**Conta:** {email}" + (" · administrador" if prof.is_admin else ""))
    lv = LEVELS.get(prof.level or "", None)
    left = turns_left()
    ok, why, used = live_status()
    st.markdown(
        f"- Nível: **{lv['label'] if lv else 'livre'}**{' (definido pelo administrador)' if prof.level_locked else ''}\n"
        f"- Falas hoje: **{'sem limite' if left is None else f'{left} restantes'}**\n"
        f"- Ao vivo: **{f'{max(0, prof.live_daily_minutes - used / 60):.0f} de {prof.live_daily_minutes} min hoje' if ok else why}**"
    )
    with st.expander("📲 Instalar no celular e no Mac"):
        st.markdown(
            "- **iPhone (Safari):** Compartilhar → *Adicionar à Tela de Início*.\n"
            "- **Mac (Safari):** Arquivo → *Adicionar ao Dock*. **Chrome:** menu ⋮ → *Transmitir, salvar e "
            "compartilhar* → *Instalar página como app*.\n"
            "- Abrindo pelo ícone, o app aparece sem barras do navegador."
        )
    if "auth" in st.secrets:
        st.button("Sair da conta", on_click=st.logout, width="stretch")


# --- Tela: usuários (administrador) ------------------------------------------------
def users_view() -> None:
    ui.hero("👥 Usuários", "Libere pessoas, escolha o nível delas, o limite por dia e quais chaves de API usam.")
    if not db.enabled():
        st.info("Precisa do banco (DATABASE_URL) ligado para cadastrar usuários.", icon="🗄️")
        return
    import pandas as pd

    rows = db.list_users()
    if rows:
        view = [{
            "e-mail": r["email"], "ativo": r["active"], "nível": LEVELS.get(r["level"] or "", {}).get("label", "livre"),
            "travado": r["level_locked"], "falas/dia": r["daily_turns"] if r["daily_turns"] is not None else "padrão",
            "ao vivo": f"{r['live_daily_minutes'] or 10} min" if r["live_enabled"] else "não",
            "chaves": ", ".join(f"{PROVIDER_LABEL[p].split(' ')[0]}: {users.POLICIES.get((r['key_policy'] or {}).get(p, 'owner'))}"
                                for p in PROVIDERS),
        } for r in rows if not r.get("is_admin")]
        if view:
            st.dataframe(pd.DataFrame(view), hide_index=True, width="stretch")
    st.caption("Lembrete: se o login do Google estiver em modo de teste, adicione o e-mail também como "
               "usuário de teste no Google Cloud (Google Auth Platform → Público-alvo).")

    # --- famílias (contas criadas pelos pais) ---
    st.markdown("### 👨‍👩‍👧 Famílias")
    smode = family.signup_mode()
    nm = st.segmented_control("Quando um pai cria a conta da família:", ["approval", "open"], default=smode,
                              format_func=lambda k: {"approval": "✋ Eu aprovo antes", "open": "✅ Entra direto"}[k],
                              key="signup_mode")
    if nm and nm != smode:
        db.set_pref("__app__", "signup", nm)
        st.toast("Salvo ✅")
    for pnd in family.pending():
        c1, c2 = st.columns([3, 1], vertical_alignment="center")
        c1.markdown(f"⏳ **{pnd.get('parent', '')}** ({pnd['email']}) · criança: **{pnd.get('child', '')}** · "
                    f"criada em {pnd.get('created', '')}")
        if c2.button("✅ Aprovar", key=f"appr_{pnd['email']}", width="stretch"):
            db.upsert_user(pnd["email"], active=True)
            st.rerun()
    fams = [r["email"] for r in rows if family.is_family(r["email"])]
    if fams:
        fpick = st.selectbox("Família", fams, format_func=lambda e: f"{family.info(e).get('parent', '')} · "
                             f"{family.info(e).get('child', '')} ({e})", key="fam_pick")
        c1, c2 = st.columns(2)
        if c1.button("🔑 Zerar PIN", key="fam_reset_pin", width="stretch"):
            family.reset_pin(fpick)
            st.success("PIN zerado: no próximo acesso à área dos pais, eles criam outro.")
        c2.caption(f"Autorização: {db.get_pref(fpick, 'consent_parents') or 'não registrada'}")
    else:
        st.caption("Nenhuma família ainda. Quando um pai entrar com o Google pela primeira vez, ele cria a conta.")
    st.divider()

    existing = [r["email"] for r in rows if not r.get("is_admin")]
    pick = st.selectbox("Editar", ["➕ Novo usuário"] + existing)
    cur = next((r for r in rows if r["email"] == pick), {}) if pick != "➕ Novo usuário" else {}
    with st.form("user_form", clear_on_submit=False):
        em = st.text_input("E-mail Google", value=cur.get("email", ""), disabled=bool(cur))
        name = st.text_input("Nome (opcional)", value=cur.get("name") or "")
        active = st.toggle("Acesso liberado", value=cur.get("active", True))
        level_opts = ["(livre)"] + list(LEVELS)
        lv_cur = cur.get("level") or "(livre)"
        lvl = st.selectbox("Nível", level_opts, index=level_opts.index(lv_cur) if lv_cur in level_opts else 0,
                           format_func=lambda k: k if k == "(livre)" else LEVELS[k]["label"])
        locked = st.checkbox("Travar o nível (a pessoa não pode trocar)", value=bool(cur.get("level_locked")))
        turns = st.number_input("Limite de falas por dia (0 = sem limite)", min_value=0, max_value=1000,
                                value=int(cur["daily_turns"]) if cur.get("daily_turns") is not None else 60)
        live_on = st.toggle("Pode usar o modo ao vivo (Gemini grátis)", value=bool(cur.get("live_enabled")))
        live_min = st.number_input("Minutos ao vivo por dia", min_value=1, max_value=60,
                                   value=int(cur.get("live_daily_minutes") or 10))
        consent = st.checkbox("👨‍👩‍👧 Os pais autorizaram (obrigatório para contas do nível Infantil)",
                              value=bool(cur and db.get_pref(cur["email"], "consent_parents")))
        st.markdown("**Chaves de API, serviço por serviço**")
        policy = dict(cur.get("key_policy") or {})
        enc = dict(cur.get("keys_enc") or {})
        new_keys = {}
        for p in PROVIDERS:
            c1, c2 = st.columns([1.2, 2])
            pol_opts = list(users.POLICIES)
            policy[p] = c1.selectbox(PROVIDER_LABEL[p], pol_opts, index=pol_opts.index(policy.get(p, "owner")),
                                     format_func=lambda k: users.POLICIES[k], key=f"pol_{p}_{pick}")
            hint = users.mask(users.decrypt(enc[p])) if enc.get(p) else "nenhuma"
            new_keys[p] = c2.text_input(f"Chave própria ({PROVIDER_LABEL[p]}) — atual: {hint}", type="password",
                                        key=f"key_{p}_{pick}", help="Só é usada se escolher 'Chave própria'. "
                                                             "Deixe em branco para manter a atual.")
        saved = st.form_submit_button("💾 Salvar usuário", type="primary", width="stretch")
    if saved:
        target = (cur.get("email") or em or "").strip().lower()
        if "@" not in target:
            st.error("Informe um e-mail válido.")
        else:
            for p, k in new_keys.items():
                if k.strip():
                    enc[p] = users.encrypt(k.strip())
            db.upsert_user(target, name=name or None, active=active, level=None if lvl == "(livre)" else lvl,
                           level_locked=locked and lvl != "(livre)", daily_turns=None if turns == 0 else int(turns),
                           live_enabled=live_on, live_daily_minutes=int(live_min), key_policy=policy, keys_enc=enc)
            if consent and not db.get_pref(target, "consent_parents"):
                db.set_pref(target, "consent_parents", f"pelo admin · {_now_tag()}")
            elif not consent:
                db.set_pref(target, "consent_parents", "")
            st.success(f"Salvo: {target}")
            st.rerun()
    if cur and st.button(f"🗑️ Remover {cur['email']}", width="stretch"):
        db.delete_user(cur["email"])
        st.rerun()

    st.divider()
    my = db.get_user(email) or {}
    mine = st.number_input("Meus minutos ao vivo por dia", min_value=1, max_value=60,
                           value=int(my.get("live_daily_minutes") or prof.live_daily_minutes), key="my_live_min")
    if st.button("Salvar meus minutos"):
        db.upsert_user(email, is_admin=True, active=True, live_daily_minutes=int(mine))
        st.success("Salvo.")


# --- Tela: Pais (perfil protegido por PIN) -----------------------------------------------
def parents_view() -> None:
    import time as _t
    f = family.info(email)
    child = f.get("child", "a criança")
    if ss.get("fam_mode") != "parent" and not family.has_pin(email):
        ui.hero("🔑 Criar um novo PIN", "O PIN foi zerado pelo administrador. Crie um novo para a área dos pais.")
        with st.form("new_pin"):
            p1 = st.text_input("Novo PIN (4 números)", type="password", max_chars=4)
            p2 = st.text_input("Repita", type="password", max_chars=4)
            if st.form_submit_button("Salvar e entrar", type="primary", width="stretch"):
                if p1 != p2 or not family.valid_pin(p1):
                    st.error("Os PINs precisam ser iguais e ter 4 números (nada de 1234 ou 0000).")
                else:
                    family.set_pin(email, p1)
                    ss.fam_mode = "parent"
                    st.rerun()
        return
    if ss.get("fam_mode") != "parent":
        ui.hero("🔒 Área dos pais", f"Digite o PIN de 4 números para entrar. Aqui ficam os limites, os relatórios e "
                f"as conversas de {child}.")
        wait = ss.get("pin_lock", 0) - _t.time()
        if wait > 0:
            st.warning(f"Muitas tentativas. Tente de novo em {int(wait // 60) + 1} min.", icon="⏳")
            return
        with st.form("pin_form"):
            pin = st.text_input("PIN", type="password", max_chars=4, placeholder="••••")
            go = st.form_submit_button("🔓 Entrar", type="primary", width="stretch")
        if go:
            if family.check_pin(email, pin.strip()):
                ss.fam_mode, ss.pin_tries = "parent", 0
                ss.view = "pais"
                st.rerun()
            ss.pin_tries = ss.get("pin_tries", 0) + 1
            if ss.pin_tries >= 5:
                ss.pin_lock, ss.pin_tries = _t.time() + 300, 0
            st.error("PIN errado.")
        st.caption("Esqueceu o PIN? Peça ao administrador do app para zerar; no próximo acesso você cria outro.")
        return

    ui.hero("👨‍👩‍👧 Área dos pais", f"Tudo sobre {child}: limites, resumo da semana, conversas e privacidade.")
    if st.button(f"👧 Voltar para o perfil de {child}", type="primary", width="stretch", key="to_kid"):
        ss.fam_mode, ss.view, ss.kid_inside = "kid", "aprender", None
        st.rerun()
    if not family.has_pin(email):
        st.warning("O PIN foi zerado pelo administrador. Crie um novo em 🔑 PIN, abaixo.", icon="🔑")

    t1, t2, t3, t4, t5 = st.tabs(["📊 Progresso", "⏳ Limites", "📨 Resumo", "💬 Conversas", "🔒 Conta"])
    with t1:
        txt = report.family_report(email)
        st.text(txt)
        know, review = report.learned_words(email)
        st.markdown("**✅ Palavras que já acerta:** " + (", ".join(know) if know else "—"))
        st.markdown("**🔁 Vale treinar junto:** " + (", ".join(review) if review else "nada! 🎉"))
    with t2:
        opts = {3: "3 por dia", 5: "5 por dia", 10: "10 por dia", 0: "Sem limite"}
        cur = daily_limit()
        new = st.segmented_control("🪐 Planetas novos por dia", list(opts), format_func=lambda k: opts[k],
                                   default=cur if cur in opts else 3, key="fam_limit")
        if new is not None and new != cur:
            db.set_pref(email, "kid_limit", str(new))
            st.toast("Salvo ✅")
        st.caption("Refazer planetas que já visitou e o ⚡ Desafio não contam.")
        mopts = {0: "Sem limite", 15: "15 min", 30: "30 min", 45: "45 min", 60: "1 hora"}
        cur_m = kid_minutes_limit()
        new_m = st.segmented_control("⏳ Tempo de uso por dia", list(mopts), format_func=lambda k: mopts[k],
                                     default=cur_m if cur_m in mopts else 0, key="fam_minutes")
        if new_m is not None and new_m != cur_m:
            db.set_pref(email, "kid_minutes", str(new_m))
            st.toast("Salvo ✅")
        st.caption(f"Hoje: {report.kid_minutes_today(email)} min de uso. Quando o tempo acaba, o Bip se despede "
                   "e o perfil da criança só volta no dia seguinte (a área dos pais continua aberta).")
    with t3:
        cfg = notify.load_cfg(db.get_pref, email)
        labels = {"email": "📧 E-mail", "telegram": "✈️ Telegram"}
        chans = st.pills("Receber o resumo toda segunda por:", list(labels), format_func=lambda k: labels[k],
                         selection_mode="multi", default=cfg["channels"], key="fam_chans")
        mails = st.text_input("E-mails (separe por vírgula)", value=cfg["emails"] or email, key="fam_mails")
        if "telegram" in (chans or []):
            st.markdown("**Conectar o Telegram (uma vez só):**")
            code = family.connect_code(email)
            bot = notify.telegram_bot_name() if notify.telegram_ready() else ""
            if not bot:
                st.info("O Telegram ainda não foi ligado pelo administrador do app. Por enquanto, use o e-mail.", icon="ℹ️")
            else:
                st.markdown(f"1. Toque aqui para adicionar o robô ao **grupo da família**: "
                            f"[➕ Adicionar @{bot} a um grupo](https://t.me/{bot}?startgroup={code})  \n"
                            f"   (ou, para receber só você: [abrir conversa com @{bot}](https://t.me/{bot}?start={code}))\n"
                            f"2. Se o Telegram não mandar sozinho, escreva no grupo: `/start {code}`\n"
                            f"3. Volte aqui e toque em **Procurar**.")
                if st.button("🔎 Procurar meu grupo", key="tg_find"):
                    try:
                        found = notify.telegram_find(code)
                    except Exception as e:
                        found, st.session_state["tg_err"] = None, str(e)
                    if found:
                        cfg["telegram"] = found["id"]
                        cfg["telegram_name"] = found["name"]
                        db.set_pref(email, "resumo", json.dumps(cfg, ensure_ascii=False))
                        st.success(f"Conectado: {found['name']} ✅")
                    else:
                        st.warning("Ainda não achei. Confira se o robô está no grupo e se a mensagem com o código foi enviada.")
            if cfg.get("telegram"):
                st.caption(f"✅ Telegram conectado: {cfg.get('telegram_name') or cfg['telegram']}")
        c1, c2 = st.columns(2)
        if c1.button("💾 Salvar", type="primary", width="stretch", key="fam_save_rep"):
            cfg.update(channels=list(chans or []), emails=mails)
            db.set_pref(email, "resumo", json.dumps(cfg, ensure_ascii=False))
            st.toast("Salvo ✅")
        if c2.button("📨 Enviar agora (teste)", width="stretch", key="fam_send"):
            cfg.update(channels=list(chans or []), emails=mails)
            for line in notify.send_report(cfg, child, report.family_report(email)):
                st.write(line)
    with t4:
        sess = db.sessions_recent(email)
        if not sess:
            st.caption("Nenhuma conversa ainda.")
        else:
            label = {x["id"]: f"{x['inicio']} · {x['conversa']} · {x['falas']} falas" for x in sess}
            sid = st.selectbox("Abrir conversa", list(label), format_func=lambda i: label[i], key="fam_sess")
            for t in db.session_turns(sid):
                (ui.ai_bubble if t["role"] == "assistant" else ui.user_bubble)(t["text"])
    with t5:
        st.markdown(f"**Conta:** {email} · criada em {f.get('created', '—')}")
        st.markdown(f"**Autorização dos pais:** registrada em {db.get_pref(email, 'consent_parents') or '—'}")
        with st.expander("📄 Como o app usa os dados"):
            st.markdown(family.PRIVACY_TEXT)
        with st.form("fam_pin"):
            st.markdown("**🔑 Trocar o PIN**")
            p1 = st.text_input("Novo PIN", type="password", max_chars=4)
            p2 = st.text_input("Repita", type="password", max_chars=4)
            if st.form_submit_button("Salvar PIN"):
                if p1 != p2 or not family.valid_pin(p1):
                    st.error("Os PINs precisam ser iguais e ter 4 números (nada de 1234 ou 0000).")
                else:
                    family.set_pin(email, p1)
                    st.success("PIN trocado ✅")
        nm = st.text_input("Nome da criança", value=f.get("child", ""), key="fam_child")
        if st.button("Salvar nome", key="fam_child_save") and nm.strip():
            f["child"] = nm.strip()
            db.set_pref(email, "familia", json.dumps(f, ensure_ascii=False))
            st.toast("Salvo ✅")
        st.divider()
        sure = st.checkbox("Quero apagar todas as conversas desta conta (não dá para desfazer).", key="fam_del_ok")
        if st.button("🗑️ Apagar conversas", disabled=not sure, key="fam_del"):
            st.success(f"Pronto: {db.delete_conversations(email)} conversa(s) apagada(s).")
        st.button("🚪 Sair da conta", on_click=st.logout, key="fam_logout")


# --- Tela: aprender (gramática, vídeos, tradutor) ----------------------------------------
def learn_level() -> str:
    if prof.level_locked:
        st.caption(f"Nível: {LEVELS[ss.level]['label']}")
        return ss.level
    ss.learn_level = ss.level   # sempre igual ao nível do app
    st.selectbox("Nível", list(LEVELS), format_func=lambda k: LEVELS[k]["label"], key="learn_level",
                 on_change=_set_level, args=("learn_level",))
    return ss.level


AVATARS = ["🧑🏻‍🚀", "🧑🏽‍🚀", "🧑🏿‍🚀", "👦🏻", "👦🏽", "👦🏿", "👧🏻", "👧🏽", "👧🏿", "🐶", "🐱", "🦁", "🐼", "🦖", "🤖"]


PRIVACY_TEXT = family.PRIVACY_TEXT


def kids_astro() -> tuple[str, str]:
    if "astro" not in ss:
        ss.astro = (db.get_pref(email, "astronauta") if db.enabled() else None) or ""
    parts = ss.astro.split("|")
    return parts[0], (parts[1] if len(parts) > 1 and parts[1] else "🚀")


def kids_avatar() -> str:
    kids_astro()
    parts = ss.astro.split("|")
    return parts[2] if len(parts) > 2 and parts[2] else "🧑‍🚀"


def _acct_pref(key: str, default: int) -> int:
    """Limite da própria família (Perfil Pais); se não tiver, vale o padrão do admin."""
    if not db.enabled():
        return default
    for who in (email, "__app__"):
        v = db.get_pref(who, key)
        if v not in (None, ""):
            try:
                return int(v)
            except ValueError:
                pass
    return default


def kid_minutes_limit() -> int:
    return _acct_pref("kid_minutes", 0)


def kid_time_tick() -> None:
    """Soma o tempo de uso de hoje (conta só intervalos curtos entre toques = tempo ativo de verdade)."""
    import datetime as _dt
    import time as _t
    now = _t.time()
    last = ss.get("kid_tick")
    ss.kid_tick = now
    if last is None or not db.enabled():
        return
    delta = now - last
    if 0 < delta <= 120:
        day = _dt.datetime.now(compete.BRT).strftime("%Y-%m-%d")
        try:
            cur = float(db.get_pref(email, f"tempo:{day}") or 0)
        except ValueError:
            cur = 0
        db.set_pref(email, f"tempo:{day}", str(round(cur + delta, 1)))


def daily_limit() -> int:
    """Planetas novos por dia no perfil infantil (0 = sem limite). Os pais mudam no Perfil Pais."""
    return _acct_pref("kid_limit", rewards.DAILY_LIMIT)


def astro_form(key: str = "astro_form", title: str = "### 👩‍🚀 Vamos montar o seu astronauta!") -> None:
    name, ship = kids_astro()
    with st.form(key):
        st.markdown(title)
        nm = st.text_input("Como se chama o astronauta?", value=name, max_chars=20)
        av_now = kids_avatar()
        av = st.radio("Quem é você no jogo?", AVATARS, index=AVATARS.index(av_now) if av_now in AVATARS else 0,
                      horizontal=True)
        ships = ["🚀", "🛸", "🛰️"]
        sh = st.radio("Escolha a nave", ships, index=ships.index(ship) if ship in ships else 0, horizontal=True)
        if st.form_submit_button("Decolar! 🚀", type="primary", width="stretch") and nm.strip():
            ss.astro = f"{nm.strip()}|{sh}|{av}"
            if db.enabled():
                db.set_pref(email, "astronauta", ss.astro)
            st.rerun()


def kids_next(done: dict) -> int:
    ok = {n for n, (sc, tt) in done.items() if galaxy.passed(sc, tt)}
    nxt = 1
    while nxt in ok:
        nxt += 1
    return nxt


@st.cache_resource
def _pregen_state() -> dict:
    return {"running": set()}


def pregen_missions(lvl: str, nums: list[int]) -> None:
    """Prepara as próximas missões em segundo plano: quando ele tocar no planeta, já está pronto (sem espera)."""
    if not db.enabled():
        return
    import threading
    state = _pregen_state()
    lv, key = LEVELS[lvl], prof.keys.get("anthropic")
    for n in nums:
        tag = f"{lvl}:{n}"
        if tag in state["running"] or db.get_exercise(lvl, n):
            continue
        state["running"].add(tag)

        def work(n=n, tag=tag):
            try:
                topic, rnd = topic_for(lvl, n)
                ex, _u = learn.make_kids_exercise(lv["guide"], topic, rnd, key, num=n)
                if not db.get_exercise(lvl, n):
                    db.save_exercise(lvl, n, topic, ex)
            except Exception as e:
                print(f"[pré-missão] {tag}: {e}", flush=True)
            finally:
                state["running"].discard(tag)
        threading.Thread(target=work, daemon=True).start()


def race_track_html(rows: list[dict]) -> str:
    """Corrida: cada um num trilho até a própria linha de chegada (meta da semana)."""
    if not rows:
        return '<div class="kp-card" style="text-align:center">Ninguém correu ainda esta semana. Seja o primeiro! 🚀</div>'
    medals = ["🥇", "🥈", "🥉"]
    out = []
    for i, r in enumerate(rows[:8]):
        me = r["email"] == email
        pos = min(92, max(0, r["pct"] * 0.92))
        done = r["pct"] >= 100
        out.append(f'<div style="margin:10px 0;padding:8px 10px 10px;border-radius:16px;'
                   f'background:{"rgba(255,224,102,.16)" if me else "rgba(255,255,255,.06)"};'
                   f'border:2px solid {"#FFE066" if me else "rgba(126,232,255,.25)"}">'
                   f'<div style="display:flex;justify-content:space-between;font-weight:900">'
                   f'<span>{medals[i] if i < 3 else i + 1} {html_escape(r["name"])}{" (você)" if me else ""}'
                   f' <small style="font-weight:700;color:#AFC0E8">{"criança" if r["kid"] else "adulto"}</small></span>'
                   f'<span>{r["pct"]}%</span></div>'
                   f'<div style="position:relative;height:40px;margin-top:4px;border-radius:99px;'
                   f'background:repeating-linear-gradient(90deg,rgba(255,255,255,.08) 0 12px,rgba(255,255,255,.02) 12px 24px)">'
                   f'<div style="position:absolute;right:6px;top:6px;font-size:24px">🏁</div>'
                   f'<div style="position:absolute;left:{pos}%;top:2px;font-size:30px;transition:left 1s">'
                   f'{"🏆" if done else r["avatar"]}</div></div>'
                   f'<div style="font-size:12px;color:#AFC0E8;margin-top:2px">{r["points"]} de {r["goal"]} pts</div></div>')
    return "".join(out)


def race_board_html(rows: list[dict], key: str, unit: str) -> str:
    medals = ["🥇", "🥈", "🥉"]
    if not rows:
        return '<div class="kp-card" style="text-align:center">Ninguém pontuou ainda esta semana. Seja o primeiro! 🚀</div>'
    top = rows[0][key] or 1
    out = []
    for i, r in enumerate(rows[:8]):
        me = r["email"] == email
        bar = max(6, int(100 * (r[key] or 0) / top))
        out.append(f'<div style="display:flex;align-items:center;gap:10px;margin:8px 0;padding:8px 10px;border-radius:16px;'
                   f'background:{"rgba(255,224,102,.18)" if me else "rgba(255,255,255,.07)"};'
                   f'border:2px solid {"#FFE066" if me else "rgba(126,232,255,.25)"}">'
                   f'<div style="font-size:26px;width:34px;text-align:center">{medals[i] if i < 3 else i + 1}</div>'
                   f'<div style="font-size:34px">{r["avatar"]}</div>'
                   f'<div style="flex:1;min-width:0"><div style="font-weight:900;font-size:1.05rem">{html_escape(r["name"])}'
                   f'{" (você)" if me else ""}</div>'
                   f'<div style="height:10px;border-radius:99px;background:rgba(255,255,255,.12);margin-top:4px">'
                   f'<div style="height:100%;width:{bar}%;border-radius:99px;background:linear-gradient(90deg,#FFE066,#FFB020)">'
                   f'</div></div></div><div style="font-weight:900;font-size:1.1rem;white-space:nowrap">{r[key]} {unit}</div></div>')
    return "".join(out)


def challenge_pool(lvl: str) -> list[dict]:
    """Perguntas de escolher das missões/exercícios que já existem até onde a pessoa chegou."""
    done = db.exercises_done_map(email, lvl) if db.enabled() else {}
    upto = max(3, kids_next(done) - 1) if LEVELS.get(lvl, {}).get("kids") else max(3, max(done or {0: 0}) + 1)
    pool = []
    for n in range(1, upto + 1):
        row = db.get_exercise(lvl, n) if db.enabled() else None
        ex = (row or {}).get("content") or {}
        if isinstance(ex, str):
            ex = json.loads(ex)
        for q in (ex.get("questions") or []):
            if q.get("type") == "mc" and q.get("options") and q.get("answer") in q["options"]:
                pool.append(q)
    return pool


def race_view(lvl: str) -> None:
    """Corrida Espacial: placar da semana + Desafio Relâmpago de 60 segundos."""
    import random
    import time as _t
    ch = ss.get("challenge")
    if ch and not ch.get("over"):
        challenge_play(ch)
        return
    kid = bool(LEVELS.get(lvl, {}).get("kids"))
    if not kid:
        st.markdown("<style>.kp-card{background:rgba(20,28,52,.75);border:2px solid #C9A85C;border-radius:16px;"
                    "padding:12px 14px;margin:8px 0}.kp-ins{color:#E6CD8E;font-weight:700}.kp-q{font-size:1.25rem;"
                    "font-weight:700;margin-top:4px}</style>", unsafe_allow_html=True)
    if ch and ch.get("over") and not kid:
        r = ch["result"]
        (st.success if r["new_record"] else st.info)(
            f"🏆 Novo recorde: {r['score']} pontos!" if r["new_record"] else
            f"{r['score']} pontos. Seu recorde é {r['best']}.", icon="⚡")
    elif ch and ch.get("over"):
        r = ch["result"]
        if r["new_record"]:
            galaxy.mascot("NEW RECORD! 🏆", f"NOVO RECORDE! {r['score']} pontos!", party=True, big=True, confetti=True,
                          medal="🏆", medal_text=f"{r['score']} pontos", key=f"ch_rec_{ch['id']}")
        else:
            galaxy.mascot(f"{r['score']} points! 🚀", f"Você fez {r['score']} pontos! Seu recorde é {r['best']}. "
                          "Tente de novo para bater!", party=True, confetti=r["score"] > 0, key=f"ch_end_{ch['id']}")
    st.markdown('<div style="font-size:1.6rem;font-weight:900;margin:4px 0">⚡ Desafio Relâmpago</div>'
                '<div style="opacity:.8;margin-bottom:8px">60 segundos para acertar o máximo de questões '
                + ('das suas missões' if kid else 'dos seus exercícios de gramática')
                + '. Acerto rápido vale mais!</div>', unsafe_allow_html=True)
    pool = challenge_pool(lvl)
    best = compete.load_best(email) if db.enabled() else {"best": 0}
    if len(pool) < 4:
        st.info("Complete pelo menos 1 planeta para liberar o desafio! 🪐" if kid else
                "Faça pelo menos um exercício de gramática para liberar o desafio.", icon="🔒")
    elif st.button(f"⚡ Começar desafio (seu recorde: {best['best']})", type="primary", width="stretch", key="ch_go"):
        random.shuffle(pool)
        ss.challenge = {"id": int(_t.time()), "qs": pool[:20], "i": 0, "ok": 0, "bad": 0, "start": _t.time(),
                        "over": False}
        st.rerun()
    if not db.enabled():
        return
    mine = friends_box()
    st.markdown('<div style="font-size:1.3rem;font-weight:900;margin:18px 0 4px">🏆 Recordes do desafio (semana)</div>',
                unsafe_allow_html=True)
    st.markdown(race_board_html(compete.challenge_board(only=mine), "score", "pts"), unsafe_allow_html=True)
    st.markdown('<div style="font-size:1.3rem;font-weight:900;margin:18px 0 4px">🏁 Corrida Espacial da semana</div>'
                '<div style="color:#AFC0E8;font-size:.9rem">Cada um corre até a sua linha de chegada: criança '
                f'{compete.GOAL_KID} pts, adulto {compete.GOAL_ADULT} pts. ⭐ estrela = 10 · 💬 fala = 2 · 🎬 vídeo = 15 · '
                'recomeça toda segunda.</div>', unsafe_allow_html=True)
    st.markdown(race_track_html(compete.board(only=mine)), unsafe_allow_html=True)


def friends_box() -> set:
    """Amigos da Corrida: convites pelo nome (sem mostrar e-mail), aceitar/recusar. Retorna eu + amigos."""
    fr = db.friends(email)
    astros = db.pref_all("astronauta")
    people = {u["email"]: u for u in db.list_users() if u.get("active") and u["email"] != email}

    def who(e: str) -> str:
        name, avatar = compete.profile(e, astros)
        f = family.info(e)
        return f"{avatar} {f.get('child') or name}"

    for e in sorted(fr["in"]):
        st.markdown(f'<div class="kp-card" style="border-color:#7EF0B5">🤝 <b>{html_escape(who(e))}</b> quer ser seu '
                    f'amigo na Corrida Espacial!</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("✅ Aceitar", key=f"fr_ok_{e}", type="primary", width="stretch"):
            db.friend_answer(e, email, True)
            st.rerun()
        if c2.button("Agora não", key=f"fr_no_{e}", width="stretch"):
            db.friend_answer(e, email, False)
            st.rerun()
    with st.popover(f"🤝 Amigos ({len(fr['ok'])})", width="stretch"):
        st.markdown("**Convide alguém para correr com você!** A pessoa precisa aceitar.")
        options = [e for e in people if e not in fr["ok"] and e not in fr["out"]]
        if options:
            pick = st.selectbox("Quem?", options, format_func=who, key="fr_pick")
            if st.button("📨 Mandar convite", type="primary", width="stretch", key="fr_send"):
                db.friend_request(email, pick)
                st.toast("Convite enviado! 🚀")
                st.rerun()
        else:
            st.caption("Ninguém novo para convidar agora.")
        for e in sorted(fr["out"]):
            st.caption(f"⏳ Esperando {who(e)} aceitar")
        for e in sorted(fr["ok"]):
            c1, c2 = st.columns([3, 1], vertical_alignment="center")
            c1.markdown(who(e))
            if c2.button("Sair", key=f"fr_rm_{e}"):
                db.friend_remove(email, e)
                st.rerun()
    return {email} | fr["ok"]


def challenge_play(ch: dict) -> None:
    import time as _t
    left = 60 - (_t.time() - ch["start"])
    if left <= 0 or ch["i"] >= len(ch["qs"]):
        score = compete.score_for(ch["ok"], ch["bad"], 60 - max(0, left))
        res = compete.save_score(email, score) if db.enabled() else {"best": score, "new_record": True}
        ch.update(over=True, result={"score": score, **res})
        st.rerun()
    q = ch["qs"][ch["i"]]
    st.markdown(f'<div style="display:flex;justify-content:space-between;font-weight:900;font-size:1.2rem">'
                f'<span>⚡ {ch["ok"]} acertos</span><span>⏱️ {int(left)}s</span></div>'
                f'<div style="height:14px;border-radius:99px;background:rgba(255,255,255,.12);overflow:hidden;margin:6px 0 12px">'
                f'<div style="height:100%;width:{left / 60 * 100:.1f}%;background:linear-gradient(90deg,#FF6FB5,#FFB020);'
                f'animation: chbar {left:.1f}s linear forwards"></div></div>'
                f'<style>@keyframes chbar {{ to {{ width:0% }} }}</style>', unsafe_allow_html=True)
    if ss.get("ch_fb"):
        fb = ss.pop("ch_fb")
        st.markdown(f'<div style="text-align:center;font-size:2rem;line-height:1">{"✅" if fb == "ok" else "❌"}</div>',
                    unsafe_allow_html=True)
    prompt = q.get("prompt") or ""
    say = q.get("say") or prompt or q["answer"]
    ins = q.get("instruction_pt") or "Escolha a resposta certa"
    st.markdown(f'<div class="kp-card"><div class="kp-ins">{html_escape(ins)}</div>'
                + (f'<div class="kp-q">{html_escape(prompt)}</div>' if prompt else "") + '</div>', unsafe_allow_html=True)
    tag = f"{ch['id']}:{ch['i']}"
    if q.get("say"):   # voz do aparelho: instantânea, não gasta o tempo do desafio
        ui.say_now(say, tag, key="say_now_ch")
        if st.button("🔊 Ouvir de novo", key=f"ch_re_{tag}"):
            ui.say_now(say, tag + f":{_t.time()}", key="say_now_ch2")
    emo = q.get("emojis") or []
    cols = st.columns(2)
    for j, opt in enumerate(q["options"]):
        label = f"{emo[j]}  {opt}" if j < len(emo) and emo[j] else opt
        if cols[j % 2].button(label, key=f"ch_{tag}_{j}", width="stretch"):
            ok = learn.check_answer(q, opt, lenient=True)
            ch["ok" if ok else "bad"] += 1
            ss.ch_fb = "ok" if ok else "bad"
            ch["i"] += 1
            st.rerun()
    if st.button("🏳️ Parar", key=f"ch_stop_{ch['id']}"):
        ch["start"] -= 999
        st.rerun()


def album_view(lvl: str) -> None:
    """Álbum de figurinhas: planetas concluídos + especiais por conquistas."""
    done = db.exercises_done_map(email, lvl) if db.enabled() else {}
    passed = {n for n, v in done.items() if galaxy.passed(*v)}
    stars = sum(galaxy.stars_for(*v) for v in done.values())
    st.caption("Toque numa figurinha para virar e ouvir a curiosidade em inglês 🔊")
    ui.album_grid(album.stickers(passed, stars), key="album_grid")


def kids_galaxy(lvl: str, done: dict) -> None:
    """Nível Criança: o mapa da galáxia. Tocar num planeta = mergulhar nele (abre o exercício direto)."""
    name, ship = kids_astro()
    if not name:
        astro_form()
        return
    nxt = kids_next(done)
    pregen_missions(lvl, [nxt, nxt + 1])
    shop = rewards.load_shop(email)
    hat, ship_eq = rewards.equipped_emoji(shop, "hat"), rewards.equipped_emoji(shop, "ship") or ship
    stars = sum(galaxy.stars_for(*v) for v in done.values())
    wallet = stars - shop["spent"]
    days = db.kid_days(email, lvl) if db.enabled() else []
    today_nums = db.kid_today_nums(email, lvl) if db.enabled() else set()
    streak = rewards.streak(days)
    lim = daily_limit()
    limit_hit = KIDS_PROFILE and lim > 0 and len(today_nums) >= lim

    n_blocks = max(3, (nxt - 1) // 10 + 2)
    names = [space.galaxy_name(i) for i in range(n_blocks)]
    GX_IMG = ["sun.webp", "planet_sgr_a.webp", "p_ringpink.webp"]
    b = ss.get("kid_blk_i", (nxt - 1) // 10)
    b = min(b, n_blocks - 1)
    gx_items = [{"key": str(i), "label": names[i], "img": "app/static/theme/" + GX_IMG[i % len(GX_IMG)],
                 "lock": i * 10 + 1 > nxt and not prof.is_admin} for i in range(n_blocks)]
    gpick = ui.kid_tiles(gx_items, str(b), key="kid_gx_tiles", small=True)
    if gpick is not None and int(gpick) != b:
        ss.kid_blk_i = int(gpick)
        st.rerun()
    g = space.GALAXIES[b % len(space.GALAXIES)]
    planets = []
    for n in range(b * 10 + 1, b * 10 + 11):
        info = space.stop(n)
        planets.append({"num": n, "name": info["en"], "img": info["img"], "done": n in done,
                        "stars": galaxy.stars_for(*done[n]) if n in done else 0,
                        "locked": (n > nxt or (limit_hit and n not in done)) and not prof.is_admin,
                        "current": n == nxt, "selected": False,
                        "boss": ("sun" if info["key"] == "sun" else "big") if info["boss"] else None})
    first, last = b * 10 + 1, b * 10 + 10
    if limit_hit:
        say, sub = "Great job today! See you tomorrow! 🌙", (f"Muito bem hoje! Até amanhã! · Planetas novos só amanhã, "
                                                             f"mas você pode treinar nos que já visitou e jogar o ⚡ Desafio!")
    elif first <= nxt <= last:
        say, sub = (f"Hi, {name}! Let's fly to {space.stop(nxt)['en']}!",
                    f"Oi, {name}! Vamos voar para {space.stop(nxt)['pt']}! 👆 Toque no planeta")
    elif nxt > last:
        say, sub = "Wow! You explored this whole galaxy! 🌟", "Uau! Você explorou esta galáxia inteira!"
    else:
        say, sub = "This galaxy is still far away! 🔭", f"Esta galáxia ainda está longe! Primeiro explore {space.stop(nxt)['pt']}."
    goal_ok = len(today_nums) >= rewards.DAILY_GOAL
    hud = [{"t": f"🔥 {streak}"}, {"t": "🎯 ✓" if goal_ok else "🎯 0/1", "ok": goal_ok}, {"t": f"💰 {wallet}"}]
    if KIDS_PROFILE and kid_minutes_limit():
        hud.append({"t": f"⏳ {max(0, kid_minutes_limit() - report.kid_minutes_today(email))} min"})
    in_gal = sum(1 for n in range(first, last + 1) if n in done)
    left = 10 - in_gal
    boss = space.stop(last)["pt"]
    prog_text = f"🏁 {left} até o {boss}" if left else "🏆 Galáxia completa!"
    foot = "Em Andrômeda ainda não conhecemos planetas de verdade: estes são imaginários! ✨" if g["imaginary"] else ""
    if ss.get("shop_party"):   # acabou de comprar: o Bip aparece grande, com o chapéu novo e confete
        it = ss.pop("shop_party")
        galaxy.mascot(f"Wow! I love it! {it['emoji']}", f"Uau! Eu amei! Obrigado pelo {it['name']}, {name}!",
                      party=True, big=True, confetti=True, hat=hat, key=f"shop_party_{it['id']}")
    pick = galaxy.galaxy_map(planets, say, sub, name=f"{kids_avatar()} {name}", ship=ship_eq, total_stars=stars,
                             foot=foot, galaxy="", where="", key=f"gx_{b}", hat=hat, hud=hud,
                             progress=in_gal / 10, progress_text=prog_text)
    if pick:
        ss.kid_inside, ss.kid_lvl = int(pick), lvl
        st.rerun()

    with st.popover("🛍️ Loja do Bip", width="stretch"):
        st.markdown(f"**Você tem {wallet} ⭐** · troque suas estrelas por coisas para o Bip!")
        for kind, title in (("hat", "Chapéus do Bip"), ("ship", "Naves")):
            st.caption(title)
            cols = st.columns(3)
            for j, it in enumerate([i for i in rewards.SHOP if i["kind"] == kind]):
                owned = it["id"] in shop["owned"]
                using = shop.get(kind) == it["id"]
                label = f"{it['emoji']} {it['name']}\n" + ("✓ usando" if using else "usar" if owned else f"{it['price']} ⭐")
                if cols[j % 3].button(label, key=f"shop_{it['id']}", width="stretch", disabled=using):
                    ok, msg = rewards.buy(email, shop, it["id"], stars)
                    if ok:
                        ss.shop_party = it
                    else:
                        ss.shop_msg = msg
                    st.rerun()
        if ss.get("shop_msg"):
            st.success(ss.pop("shop_msg"))


def _say(text: str) -> None:
    """O robô lê em inglês (voz devagar, grátis). Guarda o áudio para não gerar de novo."""
    text = (text or "").replace("___", "…").strip()
    if not text:
        return
    try:
        cache = ss.setdefault("tts_cache", {})
        if text not in cache:
            cache[text] = voice.speak(text, pace="slow", log=log)[:2]
        audio, mime = cache[text]
        st.audio(audio, format=mime, autoplay=True)
    except Exception as e:
        st.caption(f"Não consegui falar agora: {e}")


def kids_planet(lvl: str, num: int, done: dict) -> None:
    """Dentro do planeta: o mapa some e a missão vira uma trilha de paradas."""
    info = space.stop(num)
    st.markdown(galaxy.TRAIL_CSS, unsafe_allow_html=True)
    ui.dive_bg(info["surf"] or info["img"], surface=bool(info["surf"]))
    if st.button("🛰️ Voltar para a galáxia", key="kp_back"):
        ss.kid_inside = None
        st.rerun()
    pron = space.PRON.get(info["key"], "")
    st.markdown(f'<div class="kp-head"><img src="{info["img"]}" alt=""><div><h2>{info["en"]}</h2>'
                f'<small>{"🗣️ fala-se <b>" + pron + "</b> · " if pron else ""}{info["pt"]} · {info["galaxy"]}</small>'
                f'</div></div><div class="kp-fact">💡 {info["fact"]}</div>', unsafe_allow_html=True)
    if st.button(f"🔊 Como se fala {info['en']}?", key=f"kp_name_{num}"):
        _say(info["en"])
    hat = rewards.equipped_emoji(rewards.load_shop(email), "hat")

    topic, rnd = topic_for(lvl, num)
    cache = st.session_state.setdefault("ex_cache", {})
    key = f"{lvl}:{num}"
    ex = cache.get(key) or ((db.get_exercise(lvl, num) or {}).get("content") if db.enabled() else None)
    if isinstance(ex, str):
        ex = json.loads(ex)
    if not ex:
        with st.spinner(f"🚀 Pousando em {info['en']}..."):
            try:
                lv = LEVELS[lvl]
                ex, u = learn.make_kids_exercise(lv["guide"], topic, rnd, prof.keys.get("anthropic"), num=num)
                log(step="exercício", provider="Anthropic", model=u["model"], ok=True,
                    input_tokens=u["input_tokens"], output_tokens=u["output_tokens"])
                db.save_exercise(lvl, num, topic, ex)
            except Exception as e:
                st.error(f"Não consegui preparar a missão: {e}")
                return
    cache[key] = ex
    qs = list(ex.get("questions", []))
    examples = [e for e in ex.get("examples", []) if 2 < len(str(e).split()) <= 9]
    if examples:   # uma parada de "montar a frase" tocando nas palavras
        sent = examples[0].strip()
        qs.append({"type": "order", "prompt": "Monte a frase em inglês:", "answer": sent,
                   "explain_pt": "Essa é uma das frases de exemplo da missão."})
    n_stops = len(qs) + 1
    stt = ss.setdefault(f"kp_{key}", {"i": 0, "res": {}, "ans": {}, "done": False})
    icons = {0: "📜"} | {j + 1: "🧩" if q["type"] == "order" else "✍️" if q["type"] == "fill" else str(j + 1)
                        for j, q in enumerate(qs)}
    st.markdown(galaxy.trail_html(n_stops, -1 if stt["done"] else stt["i"], stt["res"], icons),
                unsafe_allow_html=True)

    if stt["done"]:
        stt.pop("flash", None)
        score = sum(1 for v in stt["res"].values() if v)
        total = len(qs)
        if galaxy.passed(score, total) and info["boss"]:
            # fim de galáxia: medalha grande, confete e o Bip gigante comemorando
            MEDALS = ["🏅", "🏆", "👑"]
            gi = (num - 1) // 10
            galaxy.mascot("YOU DID IT! Galaxy complete! 🎉", f"VOCÊ CONSEGUIU! Completou a galáxia {info['galaxy']}! "
                          f"Ganhou a medalha e uma figurinha nova no álbum!", party=True, big=True, confetti=True,
                          hat=hat, medal=MEDALS[gi % 3], medal_text=f"Medalha {info['galaxy']}", key=f"kp_party_{num}")
            if st.button("🚀 Voar para a próxima galáxia!", type="primary", width="stretch", key=f"kp_next_{num}"):
                ss.kid_inside, ss.kid_blk_i = None, gi + 1
                st.rerun()
        elif galaxy.passed(score, total):
            galaxy.mascot(f"Mission complete! {'⭐' * galaxy.stars_for(score, total)}",
                          f"Missão cumprida em {info['pt']}! Você acertou {score} de {total}.", party=True,
                          confetti=True, hat=hat, key=f"kp_party_{num}")
            if st.button("🚀 Voar para o próximo planeta", type="primary", width="stretch", key=f"kp_next_{num}"):
                ss.kid_inside = num + 1
                st.rerun()
        else:
            galaxy.mascot("Almost there! Try again! 💪", f"Quase! Você acertou {score} de {total}. "
                          "Tente de novo para ganhar estrelas e liberar o próximo planeta.", key=f"kp_party_{num}")
        c1, c2 = st.columns(2)
        if c1.button("🔁 Fazer de novo", width="stretch", key=f"kp_redo_{num}"):
            ss[f"kp_{key}"] = {"i": 0, "res": {}, "ans": {}, "done": False}
            st.rerun()
        if c2.button("🛰️ Voltar à galáxia", width="stretch", key=f"kp_home_{num}"):
            ss.kid_inside = None
            st.rerun()
        return

    i = stt["i"]
    if i == 0:   # briefing: o Bip conta a missão em poucas palavras e fala os exemplos
        galaxy.mascot(f"📜 {ex.get('title', topic)}", ex.get("explanation_pt", ""), hat=hat, sound=False,
                      key=f"kp_brief_{num}")
        chips = "".join(f'<span style="display:inline-block;margin:4px;padding:8px 14px;border-radius:999px;'
                        f'background:rgba(255,255,255,.12);border:1px solid rgba(126,232,255,.4);font-weight:800;'
                        f'font-size:1.1rem">{html_escape(e)}</span>' for e in ex.get("examples", [])[:3])
        st.markdown(f'<div style="text-align:center;margin:6px 0 10px">{chips}</div>', unsafe_allow_html=True)
        said = ss.setdefault("kp_said", set())
        if f"{key}:0" not in said:
            said.add(f"{key}:0")
            _say(". ".join(ex.get("examples", [])[:3]))
        c1, c2 = st.columns([1, 2])
        if c1.button("🔊 Ouvir", width="stretch", key=f"kp_say0_{num}"):
            _say(". ".join(ex.get("examples", [])[:3]))
        if c2.button("🚀 Vamos!", type="primary", width="stretch", key=f"kp_go_{num}"):
            stt["i"] = 1
            st.rerun()
        return

    if stt.get("flash") is not None:   # comemoração rápida do acerto anterior
        galaxy.mascot("Great job! ⭐", f"Isso mesmo! {stt.pop('flash')}", party=True, hat=hat,
                      key=f"kp_flash_{num}_{i}")
    q = qs[i - 1]
    prompt = q.get("prompt", "")
    g = ((num - 1) // 10) % 3          # galáxia 1: instrução em português; 2: inglês + português; 3: inglês
    ins_pt, ins_en = q.get("instruction_pt", ""), q.get("instruction_en", "")
    if q["type"] == "order":
        ins_pt, ins_en = "Toque nas palavras na ordem certa para montar a frase.", "Make the sentence!"
    if g == 0 or not ins_en:
        ins_html = html_escape(ins_pt)
    elif g == 1:
        ins_html = f'{html_escape(ins_en)}<div style="font-size:.95rem;color:#AFC0E8;font-weight:600">{html_escape(ins_pt)}</div>'
    else:
        ins_html = html_escape(ins_en)
    shown = "" if q["type"] == "order" else prompt
    st.markdown(f'<div class="kp-card"><div style="color:#AFC0E8;font-weight:800">PARADA {i} DE {len(qs)}</div>'
                f'<div class="kp-ins">{ins_html}</div>'
                + (f'<div class="kp-q">{html_escape(shown)}</div>' if shown else "") + '</div>', unsafe_allow_html=True)
    say = q.get("say") or (q["answer"] if q["type"] == "order" else prompt)
    said = ss.setdefault("kp_said", set())
    c1, c2 = st.columns(2)
    replay = c1.button("🔊 Ouvir de novo", key=f"kp_say_{num}_{i}", width="stretch")
    if (f"{key}:{i}" not in said or replay) and i not in stt["res"]:
        said.add(f"{key}:{i}")
        _say(say)       # ouvir vem antes de ler: o robô fala sozinho quando a parada abre
    if q.get("hint_pt") and c2.button("🇧🇷 O que quer dizer?", key=f"kp_hint_{num}_{i}", width="stretch"):
        st.info(q["hint_pt"], icon="💡")

    def finish_mission() -> None:
        stt["done"] = True
        score = sum(1 for v in stt["res"].values() if v)
        if db.enabled():
            db.exercise_done(email, lvl, num, score, len(qs), {str(k): v for k, v in stt["ans"].items()})

    def answer(given: str) -> None:
        ok = learn.check_answer(q, given, lenient=True)
        stt["res"][i] = ok
        stt["ans"][i] = given
        if ok:   # sem botão: a nave já avança e o Bip comemora na próxima tela
            stt["flash"] = q.get("explain_pt", "")
            if i == len(qs):
                finish_mission()
            else:
                stt["i"] = i + 1
        st.rerun()

    if i in stt["res"]:
        ok = stt["res"][i]
        if ok:
            galaxy.mascot("Great job! ⭐", f"Isso mesmo! {q.get('explain_pt', '')}", party=True, key=f"kp_fb_{num}_{i}",
                          hat=hat)
        else:
            galaxy.mascot("Oops! Let's learn it 💡", f"A resposta é: {q['answer']}. {q.get('explain_pt', '')}",
                          key=f"kp_fb_{num}_{i}", oops=True, hat=hat)
        last = i == len(qs)
        if st.button("🏁 Ver resultado" if last else "🚀 Próxima parada", type="primary", width="stretch",
                     key=f"kp_nx_{num}_{i}"):
            if last:
                finish_mission()
            else:
                stt["i"] = i + 1
            st.rerun()
        return

    if q["type"] == "mc" and q.get("options"):
        emo = q.get("emojis") or []
        cols = st.columns(2)
        for j, opt in enumerate(q["options"]):
            label = f"{emo[j]}  {opt}" if j < len(emo) and emo[j] else opt
            if cols[j % 2].button(label, key=f"kp_opt_{num}_{i}_{j}", width="stretch"):
                answer(opt)
    elif q["type"] == "order":
        import random
        words = q["answer"].split()
        rng = random.Random(num * 31 + i)
        shuffled = words[:]
        while len(words) > 1 and shuffled == words:
            rng.shuffle(shuffled)
        got = galaxy.word_builder(shuffled, key=f"kp_wb_{num}_{i}")
        if got:
            answer(got)
    else:
        ans_words = str(q.get("answer", ""))
        if st.button("💡 Me dá uma dica", key=f"kp_tip_{num}_{i}"):
            st.info("Começa assim: **" + " ".join(w[0] + " _" * (len(w) - 1) for w in ans_words.split()) + "**", icon="💡")
        with st.form(f"kp_fill_{num}_{i}"):
            typed = st.text_input("Escreva a resposta em inglês ✍️", key=f"kp_in_{num}_{i}")
            if st.form_submit_button("🚀 Confirmar", type="primary", width="stretch") and typed.strip():
                answer(typed)


def grammar_tab(lvl: str) -> None:
    done = db.exercises_done_map(email, lvl) if db.enabled() else {}
    kids = LEVELS[lvl].get("kids", False)
    if kids:
        if ss.get("kid_inside"):
            kids_planet(lvl, ss.kid_inside, done)
        else:
            kids_galaxy(lvl, done)
        return
    else:
        st.session_state.setdefault("ex_blocks", 5)  # 5 blocos de 10 = 50 exercícios visíveis; dá para ir aumentando
        n_total = ss.ex_blocks * 10
        st.caption(f"Concluídos: **{len(done)}** de {n_total}")
        blocks = [f"{i * 10 + 1}–{i * 10 + 10}" for i in range(ss.ex_blocks)]
        blk = st.segmented_control("Bloco", blocks, default=blocks[0], key=f"blk_{lvl}") or blocks[0]
        start = int(blk.split("–")[0])
        nums = list(range(start, start + 10))
        num = st.pills("Exercício", nums, default=nums[0], key=f"exn_{lvl}_{start}",
                       format_func=lambda n: f"✅ {n}" if n in done else str(n)) or nums[0]
        if st.button("➕ Mostrar mais 10 exercícios", key="more_ex"):
            ss.ex_blocks += 1
            st.rerun()

    topic, rnd = topic_for(lvl, num)
    head = f"🪐 Planeta {num}" if kids else f"{num}."
    st.markdown(f"#### {head} {topic}" + (f" · revisão {rnd}" if rnd > 1 else ""))
    cache = st.session_state.setdefault("ex_cache", {})
    key = f"{lvl}:{num}"
    ex = cache.get(key) or ((db.get_exercise(lvl, num) or {}).get("content") if db.enabled() else None)
    if isinstance(ex, str):
        ex = json.loads(ex)
    redo = bool(ex) and prof.is_admin and st.button("🔁 Refazer exercício (admin)", key=f"redo_{key}",
                                                     help="Gera uma nova versão deste número, para todos do nível.")
    if not ex or redo:
        if redo or st.button("✨ Abrir exercício", type="primary", key=f"open_{key}", width="stretch"):
            with st.spinner("Preparando o exercício (só na primeira vez)..."):
                try:
                    lv = LEVELS[lvl]
                    ex, u = learn.make_exercise(lv["guide"], lv["cefr"], topic, rnd, prof.keys.get("anthropic"))
                    log(step="exercício", provider="Anthropic", model=u["model"], ok=True,
                        input_tokens=u["input_tokens"], output_tokens=u["output_tokens"])
                    db.save_exercise(lvl, num, topic, ex, replace=redo)
                    cache[key] = ex
                    st.rerun()
                except Exception as e:
                    st.error(f"Não consegui criar o exercício: {e}")
        return
    cache[key] = ex
    if num in done and not kids:
        sc, tt = done[num]
        st.success(f"Você já concluiu este exercício (melhor nota: {sc}/{tt}). Pode refazer quando quiser.", icon="✅")
    with st.container(border=True):
        st.markdown(f"**{ex.get('title', '')}**")
        st.markdown(ex.get("explanation_pt", ""))
        for e in ex.get("examples", []):
            st.markdown(f"- *{e}*")
    qs = ex.get("questions", [])
    with st.form(f"form_{key}"):
        answers = {}
        for i, q in enumerate(qs):
            if q.get("type") == "mc" and q.get("options"):
                answers[i] = st.radio(f"{i + 1}. {q['prompt']}", q["options"], index=None, key=f"q_{key}_{i}")
            else:
                answers[i] = st.text_input(f"{i + 1}. {q['prompt']}", key=f"q_{key}_{i}")
        sent = st.form_submit_button("✅ Corrigir", type="primary", width="stretch")
    if sent:
        score = 0
        for i, q in enumerate(qs):
            ok = learn.check_answer(q, answers.get(i))
            score += ok
            if ok:
                st.markdown(f"✅ **{i + 1}.** Certo! {q.get('explain_pt', '')}")
            else:
                st.markdown(f"❌ **{i + 1}.** Resposta: **{q['answer']}** — {q.get('explain_pt', '')}")
        db.exercise_done(email, lvl, num, score, len(qs), {str(k): v for k, v in answers.items()})
        if kids:
            n_st = galaxy.stars_for(score, len(qs))
            if galaxy.passed(score, len(qs)):
                galaxy.mascot(f"Great job! {'⭐' * n_st}", f"Muito bem! Você acertou {score} de {len(qs)} "
                              "e liberou o próximo planeta!", party=True, key=f"party_{num}")
                st.button("🚀 Voar para o próximo planeta", type="primary", width="stretch", key=f"next_{num}",
                          on_click=lambda n=num + 1: ss.update(kid_jump=n))
            else:
                galaxy.mascot("Almost there! Try again! 💪", f"Quase! Você acertou {score} de {len(qs)}. "
                              "Tente de novo para ganhar estrelas.", key=f"party_{num}")
        else:
            st.markdown(f"### Nota: {score}/{len(qs)}")
            if score == len(qs):
                st.balloons()


def videos_tab(lvl: str) -> None:
    if not db.enabled():
        st.info("A trilha de vídeos precisa do banco ligado.", icon="🗄️")
        return
    if prof.is_admin:
        with st.expander("➕ Adicionar vídeo do YouTube"):
            with st.form("add_video", clear_on_submit=True):
                url = st.text_input("Link do YouTube (público)")
                title = st.text_input("Título (opcional — o Gemini preenche ao ler o vídeo)")
                vlev = st.selectbox("Nível", list(LEVELS), index=list(LEVELS).index(lvl),
                                    format_func=lambda k: LEVELS[k]["label"])
                if st.form_submit_button("Adicionar", width="stretch"):
                    vid = learn.youtube_id(url)
                    if not vid:
                        st.error("Não reconheci esse link do YouTube.")
                    else:
                        db.add_video(vlev, title or f"Vídeo {vid}", f"https://www.youtube.com/watch?v={vid}", vid, email)
                        st.success("Vídeo adicionado.")
        with st.expander("📥 Importar uma playlist inteira"):
            with st.form("import_pl"):
                purl = st.text_input("Link da playlist do YouTube (tem 'list=' no endereço)")
                pser = st.text_input("Nome da série", placeholder="ex.: American English File — Rob & Jenny")
                pauto = st.toggle("Separar por nível pela numeração AEF (AEF 1 → Iniciante, 2 → Básico, "
                                  "3 → Intermediário, 4-5 → Avançado)", value=True)
                plev = st.selectbox("Nível dos vídeos sem numeração", list(LEVELS), index=list(LEVELS).index(lvl),
                                    format_func=lambda k: LEVELS[k]["label"])
                if st.form_submit_button("Importar", width="stretch"):
                    try:
                        with st.spinner("Lendo a playlist..."):
                            items, complete = learn.playlist_videos(purl)
                        count: dict = {}
                        for i, it in enumerate(items, 1):
                            lv = (pauto and learn.level_from_title(it["title"])) or plev
                            db.add_video(lv, it["title"], f"https://www.youtube.com/watch?v={it['youtube_id']}",
                                         it["youtube_id"], email, position=i, series=pser.strip() or None)
                            count[lv] = count.get(lv, 0) + 1
                        st.success(f"{len(items)} vídeos importados: " +
                                   ", ".join(f"{LEVELS[k]['label']} {n}" for k, n in count.items()))
                        if not complete:
                            st.warning("O YouTube só deixou ler os 15 primeiros. Se a playlist tiver mais, "
                                       "adicione o resto pelo \"Adicionar vídeo\" (os que já existem não duplicam).")
                    except Exception as e:
                        st.error(f"Não consegui ler a playlist: {e}")
        with st.expander("📦 Séries e níveis"):
            for row in db.series_summary():
                c1, c2, c3 = st.columns([3, 2, 1], vertical_alignment="center")
                c1.markdown(f"**{row['series']}** · {row['n']} vídeos")
                new = c2.selectbox("Nível", list(LEVELS), index=list(LEVELS).index(row["level"]) if row["level"] in LEVELS else 0,
                                   format_func=lambda k: LEVELS[k]["label"], key=f"sl_{row['series']}",
                                   label_visibility="collapsed")
                if new != row["level"]:
                    db.set_series_level(row["series"], new)
                    st.rerun()
                if c3.button("🗑️", key=f"sd_{row['series']}", help="Apagar a série"):
                    db.delete_series(row["series"])
                    st.rerun()
    vids = db.list_videos(lvl)
    if not vids:
        st.caption("Ainda não há vídeos neste nível.")
        return
    done = db.videos_done_map(email)
    series = sorted({v.get("series") or "Avulsos" for v in vids})
    if len(series) > 1:
        pick = st.segmented_control("Série", series, default=series[0], key=f"vser_{lvl}") or series[0]
        vids = [v for v in vids if (v.get("series") or "Avulsos") == pick]
    ikey = f"vidx_{lvl}_{vids[0].get('series') or ''}"
    idx = min(max(ss.get(ikey, 0), 0), len(vids) - 1)
    b1, mid, b2 = st.columns([1, 5, 1], vertical_alignment="center")
    if b1.button("◀", key=f"vprev_{ikey}", disabled=idx == 0, width="stretch"):
        ss[ikey] = idx - 1
        st.rerun()
    if b2.button("▶", key=f"vnext_{ikey}", disabled=idx >= len(vids) - 1, width="stretch"):
        ss[ikey] = idx + 1
        st.rerun()
    v = vids[idx]
    mid.markdown(f'<div class="vid-title">{"✅ " if v["id"] in done else ""}{html_escape(v["title"])}'
                 f'<small>{idx + 1} de {len(vids)}</small></div>', unsafe_allow_html=True)
    t1, t2 = st.columns(2)
    cc = t1.toggle("Legendas em inglês", value=ss.get("vid_cc", True), key="vid_cc")
    seq = t2.toggle("Assistir em sequência", value=ss.get("vid_seq", bool(LEVELS[lvl].get("kids"))), key="vid_seq")
    ended = ui.youtube(v["youtube_id"], captions=cc, autoplay=ss.pop("vid_autoplay", False))
    if ended == v["youtube_id"] and seq and idx < len(vids) - 1:
        ss[ikey] = idx + 1
        ss.vid_autoplay = True
        st.rerun()
    st.link_button("▶️ Não tocou aqui? Abrir no YouTube", v["url"], width="stretch")
    notes = v.get("notes")
    notes_json = json.dumps(notes, ensure_ascii=False) if isinstance(notes, (dict, list)) else (notes or "")
    if not notes_json:
        gem = prof.keys.get("gemini") or users.owner_key("gemini")
        if st.button("📖 Preparar perguntas", type="primary", width="stretch"):
            with st.spinner("O Gemini está assistindo o vídeo..."):
                try:
                    notes_json, _ = learn.video_summary(v["url"], gem)
                    log(step="vídeo", provider="Gemini", model=learn.GEMINI_STT_MODEL, ok=True)
                    db.set_video_notes(v["id"], notes_json, json.loads(notes_json).get("title"))
                    st.rerun()
                except Exception as e:
                    log(step="vídeo", provider="Gemini", model=learn.GEMINI_STT_MODEL, ok=False, error=str(e)[:500])
                    st.error(f"Não consegui ler o vídeo: {e}")
        return
    info = json.loads(notes_json)
    if info.get("vocab"):
        with st.expander("📒 Vocabulário do vídeo"):
            for w in info["vocab"]:
                st.markdown(f"- **{w.get('en', '')}** — {w.get('pt', '')}")
    qkey = f"vq_{v['id']}"
    if qkey not in ss or st.button("🔄 Novas perguntas", key=f"newq_{v['id']}"):
        with st.spinner("Preparando perguntas..."):
            try:
                prev = ss.get(qkey) or []
                qs, u = learn.video_questions(notes_json, LEVELS[lvl]["cefr"], prof.keys.get("anthropic"), prev,
                                              kids=bool(LEVELS[lvl].get("kids")))
                log(step="vídeo perguntas", provider="Anthropic", model=u["model"], ok=True,
                    input_tokens=u["input_tokens"], output_tokens=u["output_tokens"])
                ss[qkey] = qs
            except Exception as e:
                st.error(f"Não consegui criar as perguntas: {e}")
                return
    qs = ss[qkey]
    with st.form(f"vform_{v['id']}_{abs(hash(tuple(qs)))}"):
        ans = [st.text_area(f"{i + 1}. {q}", height=68, key=f"va_{v['id']}_{i}_{abs(hash(q))}") for i, q in enumerate(qs)]
        sent = st.form_submit_button("✅ Enviar respostas", type="primary", width="stretch")
    if sent:
        with st.spinner("Corrigindo..."):
            try:
                res, u = learn.grade_answers(notes_json, qs, ans, LEVELS[lvl]["cefr"], prof.keys.get("anthropic"),
                                             kids=bool(LEVELS[lvl].get("kids")))
                log(step="vídeo correção", provider="Anthropic", model=u["model"], ok=True,
                    input_tokens=u["input_tokens"], output_tokens=u["output_tokens"])
            except Exception as e:
                st.error(f"Não consegui corrigir: {e}")
                return
        results = res.get("results", [])
        score = sum(1 for r in results if r.get("correct"))
        for i, r in enumerate(results):
            st.markdown(f"{'✅' if r.get('correct') else '❌'} **{i + 1}.** {r.get('comment_pt', '')}  \n"
                        f"<span style='color:#5D7A82'>Exemplo: <i>{r.get('better', '')}</i></span>",
                        unsafe_allow_html=True)
        st.markdown(f"### Nota: {score}/{len(qs)}")
        st.info(res.get("overall_pt", ""), icon="💬")
        db.video_done(email, v["id"], score, len(qs), {"q": qs, "a": ans})
    if st.button("💬 Conversar sobre este vídeo", width="stretch"):
        role = ("You and the learner just watched this video together. Talk about it: ask what they understood, "
                "their opinion, and use the video's key expressions. VIDEO NOTES: " + notes_json[:3000])
        ss.view = "inicio"
        try:
            start_session(role, f"🎬 {v['title']}")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao iniciar: {e}")


SIT_EMOJI = {
    "Restaurante": "🍽️", "Supermercado": "🛒", "Pedir informação na rua": "🗺️", "Farmácia": "💊",
    "Small talk com vizinho": "🏡", "Reunião de status": "📋", "Explicar um dashboard": "📊",
    "Entrevista de emprego": "🤝", "Colega estrangeiro": "🌍", "Explicar um processo": "⚙️",
    "Imigração no aeroporto": "🛂", "Primeiro dia na escola": "🏫", "Check-in no Airbnb": "🔑",
    "Fazer amigos na escola": "🧑‍🤝‍🧑", "Chip de celular": "📱", "Mercado financeiro": "📈",
    "Câmbio e moedas": "💱", "Tesouraria e dados": "🏦", "Tecnologia e IA": "🤖", "Viagens e culturas": "🧳",
    "Notícias e atualidades": "📰", "Filmes e séries": "🎬", "Esportes e saúde": "🏃",
}
SIT_SLUG = {k: "sit_" + "".join(ch for ch in __import__("unicodedata").normalize("NFKD", k.lower())
                                if ch.isalnum() or ch == " ").strip().replace(" ", "_") + ".webp" for k in SIT_EMOJI}


def theme_img(name: str) -> str:
    """Caminho da ilustração se ela já existe em static/theme; senão vazio (o cartão usa o emoji)."""
    from pathlib import Path as _P
    return "app/static/theme/" + name if (_P(__file__).resolve().parent / "static" / "theme" / name).exists() else ""


def _now_tag() -> str:
    import time as _t
    return str(_t.time())


def translator_tab() -> None:
    kids = bool(LEVELS.get(ss.level, {}).get("kids"))
    if kids:
        text = st.text_input("Qual palavra você quer saber em inglês? ✍️", key="tr_text",
                             placeholder="ex.: cachorro, arco-íris, eu gosto de pizza")
        st.markdown('<div style="font-weight:800;font-size:1.1rem;margin:6px 0 4px">🎤 Ou toque no microfone e fale</div>',
                    unsafe_allow_html=True)
        rec = st.audio_input("Fale", key=f"tr_mic_{st.session_state.get('tr_mic', 0)}",
                             label_visibility="collapsed") if voice.can_listen() else None
    else:
        text = st.text_input("O que você quer traduzir?", key="tr_text", placeholder="ex.: 'cash flow' ou 'fazer hora extra'")
        rec = st.audio_input("…ou fale", key=f"tr_mic_{st.session_state.get('tr_mic', 0)}") if voice.can_listen() else None
    go = st.button("🔤 Como se diz?" if kids else "🔤 Traduzir", type="primary", width="stretch")
    if rec is not None:
        try:
            with st.spinner("Ouvindo..."):
                text, _ = voice.transcribe(rec.getvalue(), "audio/wav", log=log, language=None)
            st.session_state["tr_mic"] = st.session_state.get("tr_mic", 0) + 1
            go = True
        except Exception as e:
            st.error(f"Não entendi o áudio: {e}")
    if go and text.strip() and kids:
        with st.spinner("O Bip está procurando... 🤖"):
            try:
                ss.tr_kid, u = learn.translate_kids(text, prof.keys.get("anthropic"))
                ss.tr_kid["_tag"] = f"{text}:{len(text)}:{id(u)}"
                log(step="tradutor", provider="Anthropic", model=u["model"], ok=True,
                    input_tokens=u["input_tokens"], output_tokens=u["output_tokens"])
            except Exception as e:
                st.error(f"Não consegui achar: {e}")
    if kids:
        k = ss.get("tr_kid")
        if k:
            st.markdown(f'<div class="kp-card" style="text-align:center">'
                        f'<div style="font-size:64px;line-height:1.1">{html_escape(k.get("emoji", ""))}</div>'
                        f'<div style="font-size:2.4rem;font-weight:900;color:#FFE066">{html_escape(k.get("english", ""))}</div>'
                        f'<div style="font-size:1.1rem;color:#AFC0E8">🗣️ fala-se <b>{html_escape(k.get("say_like", ""))}</b></div>'
                        f'<div style="font-size:1.2rem;margin-top:6px">🇧🇷 {html_escape(k.get("portuguese", ""))}</div>'
                        f'<div style="margin-top:10px;padding:8px 12px;border-radius:14px;background:rgba(255,255,255,.08)">'
                        f'<b>{html_escape(k.get("example_en", ""))}</b><br><small>{html_escape(k.get("example_pt", ""))}</small>'
                        f'</div></div>', unsafe_allow_html=True)
            ui.say_now(k.get("english", ""), k.get("_tag", ""), key="say_now_tr")
            c1, c2 = st.columns(2)
            if c1.button("🔊 Ouvir a palavra", width="stretch", key="tr_k1"):
                ui.say_now(k.get("english", ""), f"w{_now_tag()}", key="say_now_tr2")
            if c2.button("🔊 Ouvir a frase", width="stretch", key="tr_k2"):
                ui.say_now(k.get("example_en", ""), f"e{_now_tag()}", key="say_now_tr3")
        return
    if go and text.strip():
        with st.spinner("Traduzindo..."):
            try:
                ss.tr_result, u = learn.translate(text, prof.keys.get("anthropic"))
                ss.tr_result["_input"] = text
                log(step="tradutor", provider="Anthropic", model=u["model"], ok=True,
                    input_tokens=u["input_tokens"], output_tokens=u["output_tokens"])
                ss.tr_audio = None
            except Exception as e:
                st.error(f"Não consegui traduzir: {e}")
    r = ss.get("tr_result")
    if not r:
        return
    with st.container(border=True):
        arrow = "🇺🇸 → 🇧🇷" if r.get("source_lang") == "en" else "🇧🇷 → 🇺🇸"
        st.caption(f"{arrow} “{r.get('_input', '')}”")
        st.markdown(f"### {r.get('translation', '')}")
        st.markdown(r.get("meaning_pt", ""))
        if r.get("alternatives"):
            st.markdown("**Outras formas:** " + " · ".join(r["alternatives"]))
        for e in r.get("examples", []):
            st.markdown(f"- *{e.get('en', '')}* — {e.get('pt', '')}")
        if r.get("tip_pt"):
            st.info(r["tip_pt"], icon="💡")
    if st.button("🔊 Ouvir em inglês", width="stretch"):
        try:
            data, mime, _ = voice.speak(r.get("english") or r.get("translation", ""), pace="calm", log=log)
            ss.tr_audio = (data, mime)
        except Exception as e:
            st.error(f"Não consegui gerar o áudio: {e}")
    if ss.get("tr_audio"):
        st.audio(ss.tr_audio[0], format=ss.tr_audio[1], autoplay=True)


def learn_view() -> None:
    if ss.get("kid_inside") and LEVELS.get(ss.get("kid_lvl", ""), {}).get("kids"):
        # dentro do planeta: só a missão, sem título, abas nem seletor (imersão total)
        kids_planet(ss.kid_lvl, ss.kid_inside, db.exercises_done_map(email, ss.kid_lvl) if db.enabled() else {})
        return
    kids = bool(LEVELS.get(ss.level, {}).get("kids"))
    if kids:
        # infantil: sem título nem seletor de nível — 3 cartões ilustrados e o conteúdo logo abaixo
        from pathlib import Path as _P
        _theme = _P(__file__).resolve().parent / "static" / "theme"

        def timg(name: str, fallback: str) -> str:   # usa a ilustração nova se já existir
            return "app/static/theme/" + (name if (_theme / name).exists() else fallback)
        items = [{"key": "planetas", "label": "Planetas", "img": timg("tile_planets.webp", "planet_saturn.webp")},
                 {"key": "corrida", "label": "Corrida", "img": timg("tile_race.webp", "rocket.webp")},
                 {"key": "album", "label": "Álbum", "img": timg("tile_album.webp", "p_ringgold.webp")},
                 {"key": "desenhos", "label": "Desenhos", "img": timg("tile_cartoons.webp", "robot_party.webp")},
                 {"key": "diz", "label": "Como se diz?", "img": timg("tile_say.webp", "robot_wave.webp")}]
        cur = ss.get("kid_tab", "planetas")
        pick = ui.kid_tiles(items, cur, key="kid_tabs")
        if pick and pick != cur:
            ss.kid_tab = pick
            st.rerun()
        if cur == "planetas":
            grammar_tab(ss.level)
        elif cur == "desenhos":
            videos_tab(ss.level)
        elif cur == "album":
            album_view(ss.level)
        elif cur == "corrida":
            race_view(ss.level)
        else:
            translator_tab()
        return
    lvl = learn_level()
    th = current_theme()
    if th == "london":
        # mesmo padrão do infantil, no estilo Londres: cartões ilustrados e o conteúdo logo abaixo
        items = [{"key": "gram", "label": "Gramática", "img": theme_img("tile_lon_grammar.webp"), "emoji": "📝"},
                 {"key": "vid", "label": "Vídeos", "img": theme_img("tile_lon_videos.webp"), "emoji": "🎬"},
                 {"key": "tr", "label": "Tradutor", "img": theme_img("tile_lon_translate.webp"), "emoji": "🔤"},
                 {"key": "race", "label": "Corrida", "img": theme_img("tile_lon_race.webp"), "emoji": "🏁"}]
        cur = ss.get("adult_tab", "gram")
        pk = ui.kid_tiles(items, cur, key="adult_tabs", theme="london")
        if pk and pk != cur:
            ss.adult_tab = pk
            st.rerun()
        {"gram": grammar_tab, "vid": videos_tab, "race": race_view}.get(cur, lambda _l: translator_tab())(lvl)
        return
    ui.hero("📚 Aprender", "Trilhas separadas da conversa: gramática por nível, vídeos para treinar a escuta e um tradutor.")
    t1, t2, t3 = st.tabs(["📝 Gramática", "🎬 Vídeos", "🔤 Tradutor"])
    with t1:
        grammar_tab(lvl)
    with t2:
        videos_tab(lvl)
    with t3:
        translator_tab()


# --- Roteamento das telas sem conversa ativa -----------------------------------------------
if KIDS_PROFILE and ss.view != "pais":
    kid_time_tick()
    if db.enabled() and not db.get_pref(email, "consent_parents"):
        galaxy.mascot("Almost ready! 🔒", "Quase pronto! Peça para um adulto liberar o app para você. "
                      "Ele precisa ler e autorizar antes da primeira viagem.", key="kid_wait", sound=False)
        bottom_nav()
        st.stop()
    lim_min = kid_minutes_limit()
    if lim_min and report.kid_minutes_today(email) >= lim_min:
        galaxy.mascot("Time to rest! See you tomorrow! 🌙", f"Hora de descansar! Você já brincou {lim_min} minutos hoje. "
                      "Seus planetas e estrelas estão guardadinhos. Até amanhã!", key="kid_rest", sound=False)
        bottom_nav()
        st.stop()

if ss.view != "inicio":
    {"historico": history_view, "ajustes": settings_view, "usuarios": users_view,
     "aprender": learn_view, "pais": parents_view}.get(ss.view, history_view)()
    bottom_nav()
    st.stop()


# --- Tela inicial: escolher nível, modo e cenário ------------------------------------
SCENE_IMG = {"dia_a_dia": "app/static/theme/lon_daily.webp", "trabalho": "app/static/theme/lon_work.webp",
             "intercambio": "app/static/theme/lon_travel.webp", "assuntos": "app/static/theme/lon_topics.webp",
             "livre": "app/static/theme/lon_free.webp"}
if not ss.started:
    ui.brand()
    kids_home = bool(LEVELS[ss.level].get("kids"))
    if kids_home:
        galaxy.mascot("Hi! I'm Bip! 🤖", "Vamos conversar em inglês? Escolha um assunto e toque no botão!",
                      hat=rewards.equipped_emoji(rewards.load_shop(email), "hat"), sound=False, key="bip_home")
    else:
        ui.hero("Pronto para conversar?", "Escolha o nível, o modo e o assunto. Ela responde e te ajuda a soar mais natural.")
    if ss.live_msg:
        st.info(ss.live_msg, icon="⚡")
        ss.live_msg = ""

    if prof.level_locked:
        if not kids_home:
            st.markdown(f"**Nível:** {LEVELS[ss.level]['label']}")
    elif kids_home:
        ss.level_pick_k = ss.level  # infantil: seletor pequeno, discreto (só para quem pode trocar)
        st.selectbox("Nível", list(LEVELS), format_func=lambda k: LEVELS[k]["label"], key="level_pick_k",
                     on_change=_set_level, args=("level_pick_k",))
    elif current_theme() == "london":
        st.markdown("**Nível**")
        lv_items = [{"key": k, "emoji": LEVELS[k]["label"].split(" ", 1)[0],
                     "label": LEVELS[k]["label"].split(" ", 1)[-1].replace(" (", "\n(")} for k in LEVELS]
        lp = ui.kid_tiles(lv_items, ss.level, key="lvl_tiles", theme="london", small=True, cols=3)
        if lp and lp != ss.level:
            ss.level = lp
            st.rerun()
    else:
        ss.level_pick = ss.level    # sempre igual ao nível do app
        st.pills("Nível", list(LEVELS), format_func=lambda k: LEVELS[k]["label"], selection_mode="single",
                 key="level_pick", on_change=_set_level, args=("level_pick",))

    live_ok, live_why, live_used = live_status()
    modes = {"maos": "🎧 Mãos livres", "apertar": "👆 Apertar para falar"}
    if live_ok:
        modes["aovivo"] = "⚡ Ao vivo"
    if not voice.can_listen():
        modes = {"texto": "⌨️ Só texto"}
    if ss.mode not in modes:
        ss.mode = list(modes)[0]
    if kids_home:
        # criança: sem escolher "modo" — é sempre apertar para falar (a vez dele fica bem clara)
        ss.mode = "apertar" if "apertar" in modes else list(modes)[0]
    elif current_theme() == "london":
        st.markdown("**Modo**")
        mp = ui.kid_tiles([{"key": k, "emoji": v.split(" ", 1)[0], "label": v.split(" ", 1)[-1]} for k, v in modes.items()],
                          ss.mode, key="mode_tiles", theme="london", small=True)
        if mp and mp != ss.mode:
            ss.mode = mp
            st.rerun()
    else:
        ss.mode = st.pills("Modo", list(modes), format_func=lambda k: modes[k], default=ss.mode,
                           selection_mode="single", key="mode_pick") or ss.mode
    if kids_home:
        pass
    elif live_ok:
        st.caption(f"⚡ Ao vivo: {max(0, prof.live_daily_minutes - live_used / 60):.0f} de "
                   f"{prof.live_daily_minutes} min hoje")
    elif prof.live_enabled:
        st.caption(f"⚡ Ao vivo indisponível: {live_why}.")

    kids = LEVELS[ss.level].get("kids")
    scen_keys = ["criancas"] if kids else [k for k in SCENARIOS if k != "criancas"]
    if current_theme() == "london" and not kids:
        st.markdown("**Cenário**")
        cur = ss.get("scen_card") if ss.get("scen_card") in scen_keys else scen_keys[0]
        picked = ui.scene_cards([{"key": k, "label": SCENARIOS[k]["label"], "img": SCENE_IMG.get(k, "")}
                                 for k in scen_keys], cur, key="scen_cards")
        if picked and picked != cur:
            ss.scen_card = picked
            st.rerun()
        scen_key = cur
    elif kids:
        scen_key = "criancas"
    else:
        scen_key = st.pills("Cenário", scen_keys, format_func=lambda k: SCENARIOS[k]["label"],
                            default=scen_keys[0], selection_mode="single", key=f"scen_{int(bool(kids))}") or scen_keys[0]
    scen = SCENARIOS[scen_key]
    if scen_key == "criancas":
        # a fase da conversa acompanha a galáxia em que ele está na trilha (dá para escolher outra)
        phases = list(scen["phases"])
        done_k = db.exercises_done_map(email, ss.level) if db.enabled() else {}
        cur_ph = phases[min(((kids_next(done_k) - 1) // 10), len(phases) - 1)]
        phase = cur_ph
        if prof.is_admin:   # a criança segue a fase da galáxia; o admin pode escolher outra
            GX = ["sun.webp", "planet_sgr_a.webp", "p_ringpink.webp"]
            phase = ss.get("kid_phase_k") if ss.get("kid_phase_k") in phases else cur_ph
            pk = ui.kid_tiles([{"key": ph, "label": ph.split("·")[-1].strip(), "img": "app/static/theme/" + GX[i % 3]}
                               for i, ph in enumerate(phases)], phase, key="kid_phase_tiles", small=True)
            if pk and pk != phase:
                ss.kid_phase_k = pk
                st.rerun()
        sits = scen["phases"][phase]
        names = list(sits)
        skey = f"sit_kid_k_{phases.index(phase)}"
        situation = ss.get(skey) if ss.get(skey) in names else names[0]
        st.markdown('<div style="font-weight:900;font-size:1.15rem;margin:10px 0 6px">Sobre o que vamos conversar?</div>',
                    unsafe_allow_html=True)
        sp = ui.kid_tiles([{"key": n, "emoji": n.split(" ", 1)[0], "label": n.split(" ", 1)[-1]} for n in names],
                          situation, key=f"kid_sit_tiles_{phases.index(phase)}", cols=3)
        if sp and sp != situation:
            ss[skey] = sp
            st.rerun()
        role = sits[situation]
        context_label = f"{scen['label']} · {situation}"
    elif scen["situations"] and current_theme() == "london":
        names = list(scen["situations"])
        skey = f"sit_lon_{scen_key}"
        situation = ss.get(skey) if ss.get(skey) in names else names[0]
        st.markdown("**" + ("Assunto" if scen_key == "assuntos" else "Situação") + "**")
        sp = ui.kid_tiles([{"key": n, "label": n, "emoji": SIT_EMOJI.get(n, "💬"), "img": theme_img(SIT_SLUG.get(n, ""))}
                           for n in names], situation, key=f"sit_tiles_{scen_key}", theme="london",
                          cols=4 if len(names) > 6 else 3)
        if sp and sp != situation:
            ss[skey] = sp
            st.rerun()
        role = scen["situations"][situation]
        if scen_key == "assuntos":
            role = TOPIC_ROLE.format(topic=role)
        context_label = f"{scen['label']} · {situation}"
    elif scen["situations"]:
        situation = st.pills("Assunto" if scen_key == "assuntos" else "Situação", list(scen["situations"]),
                             selection_mode="single", default=list(scen["situations"])[0],
                             key=f"sit_{scen_key}") or list(scen["situations"])[0]
        role = scen["situations"][situation]
        if scen_key == "assuntos":
            role = TOPIC_ROLE.format(topic=role)
        context_label = f"{scen['label']} · {situation}"
    else:
        topic = st.text_input("Sobre o que você quer conversar hoje?",
                              placeholder="ex.: taxa de juros, minha viagem de intercâmbio, futebol... (ou deixe vazio)")
        role = FREE_TALK_ROLE.format(topic=topic) if topic.strip() else FREE_TALK_OPEN
        context_label = f"{scen['label']} · {topic or 'você escolhe na conversa'}"

    left = turns_left()
    if left is not None:
        st.caption(f"Falas restantes hoje: {left}")
    blocked = left is not None and left <= 0
    if blocked:
        st.warning("Você chegou ao limite de falas de hoje. Volte amanhã! 🙂")
    if st.button("🤖 Conversar com o Bip" if kids_home else "▶️ Começar conversa", type="primary", width="stretch",
                 disabled=blocked):
        try:
            start_session(role, context_label)
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao iniciar: {e}")
            if ss.mode == "aovivo":
                ss.mode = "maos"
                reset_session()
    bottom_nav()
    st.stop()


# --- Conversa ao vivo ------------------------------------------------------------------
bottom_nav(bar=False)
if ss.mode == "aovivo" and not ss.summary:
    ui.pill(ss.context_label + " · ⚡ ao vivo")
    ok, why, used = live_status()
    res = live.live_call(ss.live_token or "", ss.system, used_seconds=used,
                         max_seconds=prof.live_daily_minutes * 60,
                         session_max_seconds=LIVE_MAX_SESSION_MIN * 60, session_key=ss.live_session_key,
                         silence_ms=2400 if LEVELS[ss.level].get("kids") else 1800)
    st.caption("Dica: use fone de ouvido. A transcrição e o resumo aparecem quando a chamada terminar.")
    if st.button("↩️ Voltar sem ligar", width="stretch",
                 help="Use só se a chamada ainda não começou. Para encerrar uma chamada em andamento, toque no botão dela."):
        db.end_session(ss.session_id, None)
        reset_session()
        st.rerun()
    if res:
        handle_live_end(res)
        st.rerun()
    st.stop()


# --- Conversa (mãos livres / apertar para falar / texto) ---------------------------------
h1, h2 = st.columns([5, 1], vertical_alignment="center")
with h1:
    ui.pill(ss.context_label)
with h2.popover("⚙️", width="stretch"):
    ss.slow_voice = st.toggle("🐢 Voz devagar", value=ss.slow_voice, key="pop_slow")
    ss.show_text = st.toggle("👀 Mostrar texto", value=ss.show_text, key="pop_text")
    if ss.voice_used:
        st.caption(ss.voice_used)

continuous = ss.mode == "maos" and voice.can_listen()
last_ai = max((i for i, t in enumerate(ss.turns) if t["role"] == "assistant"), default=-1)

for i, t in enumerate(ss.turns):
    if t["role"] == "assistant":
        hide = not ss.show_text and i == last_ai and not ss.summary
        ui.ai_bubble(t["text"], hidden=hide, avatar="🤖" if LEVELS[ss.level].get("kids") else "🧑‍🏫")
        if i == last_ai:
            if hide:
                with st.expander("👀 Ver texto"):
                    st.markdown(t["text"])
            if ss.audio and (not continuous or ss.summary):
                st.audio(ss.audio[0], format=ss.audio[1], autoplay=ss.autoplay)
            if not ss.summary:
                b1, b2 = st.columns(2)
                slow_label = "🐢 Devagar: ligado" if ss.slow_voice else "🐢 Falar devagar"
                if b1.button(slow_label, key=f"slow_{i}", width="stretch",
                             type="primary" if ss.slow_voice else "secondary",
                             help="Liga/desliga a voz devagar para o resto da conversa (e repete esta fala)."):
                    ss.slow_voice = not ss.slow_voice
                    set_audio(t["text"])
                    st.rerun()
                if b2.button("🔁 Ouvir de novo", key=f"normal_{i}", width="stretch"):
                    set_audio(t["text"])
                    st.rerun()
                if t.get("suggestions"):
                    with st.expander("🆘 Travou? Ideias de resposta"):
                        for s in t["suggestions"]:
                            st.markdown(f"- {s}")
    else:
        ui.user_bubble(t["text"])
        c = t.get("correction")
        if c:
            ui.correction(c["better"], c["tip_pt"])
        if i == last_ai - 1 and not ss.summary and st.button(
                "🔁 Não falei isso, quero falar de novo" if LEVELS[ss.level].get("kids") else "↩️ Não foi isso que eu disse",
                key=f"undo_{i}",
                                                              help="Apaga esta fala e a resposta; é só falar de novo."):
            undo_last_exchange()
            st.rerun()

ss.autoplay = False


def summary_block() -> None:
    st.divider()
    st.subheader("📋 Resumo da sessão")
    with st.container(border=True):
        st.markdown(ss.summary)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    doc = f"# Sessão de inglês — {ss.context_label}\n\n{ss.summary}\n\n---\n\n## Transcrição\n\n{transcript_text()}\n"
    d1, d2 = st.columns(2)
    try:
        d1.download_button("⬇️ Baixar resumo (PDF)", ui.summary_pdf(ss.context_label, ss.summary, transcript_text()),
                           file_name=f"sessao_ingles_{stamp}.pdf", mime="application/pdf", width="stretch")
    except Exception:
        d1.download_button("⬇️ Baixar resumo", doc, file_name=f"sessao_ingles_{stamp}.txt", mime="text/plain",
                           width="stretch")
    if d2.button("✅ Concluir e voltar ao início", type="primary", width="stretch"):
        reset_session()
        st.rerun()


if ss.summary:
    summary_block()
    st.stop()


# --- Entrada (rodapé fixo: microfone + encerrar + texto) ------------------------------
if ss.last_error:
    st.warning(ss.last_error, icon="⚠️")

utter = rec = None
kid_talk = bool(LEVELS[ss.level].get("kids"))
if kid_talk and ss.turns and ss.turns[-1]["role"] == "assistant":
    sug = ss.turns[-1].get("suggestions") or []
    st.markdown('<div class="kp-card" style="text-align:center;border-color:#7EF0B5">'
                '<div style="font-size:1.4rem;font-weight:900;color:#7EF0B5">🎤 Sua vez! Aperte o microfone e fale</div>'
                + (f'<div style="margin-top:6px;color:#EAF2FF">Você pode dizer: <b>{html_escape(sug[0])}</b></div>' if sug else "")
                + '</div>', unsafe_allow_html=True)
with st.bottom:
    m1, m2 = st.columns([4, 1.3], vertical_alignment="center")
    with m1:
        if continuous:
            audio_b64 = base64.b64encode(ss.audio[0]).decode() if ss.audio else None
            utter = voice_chat(ss.reply_seq, audio_b64, ss.audio[1] if ss.audio else None, ss.listen_token)
        elif ss.mode == "apertar" and voice.can_listen():
            st.markdown('<div style="font-weight:800;margin:0 0 4px 4px">🎤 Toque no microfone e fale</div>',
                        unsafe_allow_html=True)
            rec = st.audio_input("🎙️ Grave sua resposta", key=f"mic_{ss.mic_key}", label_visibility="collapsed")
    end_clicked = m2.button("🏁 Encerrar", key="end_bottom", width="stretch",
                            help="Encerra a conversa, desliga o microfone e mostra o resumo.")
    typed = st.chat_input("Ou digite sua resposta em inglês...")

if end_clicked:
    finish_session()
    st.rerun()
if utter and utter.get("b64"):
    handle_audio(base64.b64decode(utter["b64"]), utter.get("mime") or "audio/webm")
    st.rerun()
if rec is not None:
    handle_audio(rec.getvalue(), "audio/wav")
    st.rerun()
if typed:
    try:
        handle_user(typed)
        st.rerun()
    except Exception as e:
        st.error(f"Erro: {e}")
