"""English Practice — parceira de conversação em inglês com voz, correções, níveis, modo ao vivo e painel de usuários."""

import base64
import json
import uuid
from datetime import datetime

import streamlit as st

import ui
from config import (DEFAULT_LEVEL, LEVELS, LIVE_MAX_SESSION_MIN, LIVE_MODEL, LIVE_RESET_HOUR_BRT,
                    MAX_HISTORY_TURNS, PROVIDER_LABEL, PROVIDERS)
from prompts import (FREE_TALK_OPEN, FREE_TALK_ROLE, LIVE_SYSTEM, SCENARIOS, START_MESSAGE, TOPIC_ROLE,
                     TUTOR_SYSTEM)
from services import galaxy, db, learn, live, llm, users, voice
from syllabus import topic_for
from services.voice_chat import voice_chat

st.set_page_config(page_title="English Practice", page_icon="static/favicon.png", layout="centered",
                   initial_sidebar_state="collapsed")
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
    ui.brand()
    ui.hero("🗣️ English Practice", "Sua parceira de conversação em inglês. Entre com sua conta Google para praticar.")
    st.button("Entrar com Google", on_click=st.login, type="primary", width="stretch")
    st.stop()

prof = users.load_profile(email)
if not prof.allowed:
    ui.brand()
    ui.hero("🔒 Acesso restrito", "Esta conta ainda não foi liberada.")
    st.info(f"Peça ao administrador para liberar **{email}** no painel de usuários.")
    st.button("Sair", on_click=st.logout)
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
            heard, provider = voice.transcribe(audio, mime, log=log)
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


# --- Navegação (rodapé) ---------------------------------------------------------
NAV = {"inicio": "💬 Falar", "aprender": "📚 Aprender", "historico": "📊 Histórico", "ajustes": "⚙️ Ajustes"}
if prof.is_admin:
    NAV["usuarios"] = "👥 Usuários"


def bottom_nav() -> None:
    def _go():
        ss.view = ss.nav or "inicio"
    ss.nav = ss.view
    with st.bottom:
        st.segmented_control("Navegação", list(NAV), format_func=lambda k: NAV[k], key="nav",
                             label_visibility="collapsed", on_change=_go, width="stretch")


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


# --- Tela: aprender (gramática, vídeos, tradutor) ----------------------------------------
def learn_level() -> str:
    if prof.level_locked:
        st.caption(f"Nível: {LEVELS[ss.level]['label']}")
        return ss.level
    return st.selectbox("Nível da trilha", list(LEVELS), index=list(LEVELS).index(ss.level),
                        format_func=lambda k: LEVELS[k]["label"], key="learn_level")


def kids_galaxy(done: dict) -> int | None:
    """Nível Criança: a trilha vira uma viagem pela galáxia. Retorna o nº do exercício escolhido."""
    if "astro" not in ss:
        ss.astro = (db.get_pref(email, "astronauta") if db.enabled() else None) or ""
    name, _, ship = ss.astro.partition("|")
    ship = ship or "🚀"
    if not name:
        with st.form("astro_form"):
            st.markdown("### 👩‍🚀 Vamos montar o seu astronauta!")
            nm = st.text_input("Como se chama o astronauta?", max_chars=20)
            sh = st.radio("Escolha a nave", ["🚀", "🛸", "🛰️"], horizontal=True)
            if st.form_submit_button("Decolar! 🚀", type="primary", width="stretch") and nm.strip():
                ss.astro = f"{nm.strip()}|{sh}"
                if db.enabled():
                    db.set_pref(email, "astronauta", ss.astro)
                st.rerun()
        return None  # (sem st.stop, para a barra de baixo continuar aparecendo)

    ok = {n for n, (sc, tt) in done.items() if galaxy.passed(sc, tt)}
    nxt = 1
    while nxt in ok:
        nxt += 1
    n_blocks = max(3, (nxt - 1) // 10 + 2)
    jump = ss.pop("kid_jump", None)
    if jump:
        n_blocks = max(n_blocks, (jump - 1) // 10 + 1)
    names = [f"Galáxia {i + 1}" for i in range(n_blocks)]
    if jump:
        ss.kid_blk, ss.kid_sel = names[(jump - 1) // 10], jump
    blk = st.segmented_control("Galáxia", names, default=names[(nxt - 1) // 10], key="kid_blk",
                               label_visibility="collapsed") or names[(nxt - 1) // 10]
    b = names.index(blk)
    nums = list(range(b * 10 + 1, b * 10 + 11))
    sel = ss.get("kid_sel")
    if sel not in nums:
        sel = nxt if nxt in nums else nums[0]
    planets = [{"num": n, "done": n in done, "stars": galaxy.stars_for(*done[n]) if n in done else 0,
                "locked": n > nxt and not prof.is_admin, "current": n == nxt, "selected": n == sel,
                "boss": ("sun" if b % 2 == 0 else "moon") if n % 10 == 0 else None} for n in nums]
    stars = sum(galaxy.stars_for(*v) for v in done.values())
    if nxt in nums:
        say, sub = f"Hi, {name}! Let's fly to planet {nxt}!", f"Oi, {name}! Vamos voar até o planeta {nxt}!"
    elif nxt > nums[-1]:
        say, sub = "Wow! You finished this galaxy! 🌟", "Uau! Você completou esta galáxia!"
    else:
        say, sub = "This galaxy is still far away… 🔭", f"Primeiro termine o planeta {nxt}."
    pick = galaxy.galaxy_map(planets, say, sub, name=name, ship=ship, total_stars=stars,
                             foot="Acerte pelo menos metade para liberar o próximo planeta ✨", key=f"gx_{b}")
    if pick and pick != sel:
        ss.kid_sel = pick
        st.rerun()
    ss.kid_sel = sel
    with st.expander("👩‍🚀 Trocar nome ou nave"):
        if st.button("Montar outro astronauta"):
            ss.astro = ""
            if db.enabled():
                db.set_pref(email, "astronauta", "")
            st.rerun()
    return sel


def grammar_tab(lvl: str) -> None:
    done = db.exercises_done_map(email, lvl) if db.enabled() else {}
    kids = LEVELS[lvl].get("kids", False)
    if kids:
        num = kids_galaxy(done)
        if num is None:
            return
    else:
        st.session_state.setdefault("ex_blocks", 5)  # 5 blocos de 10 = 50 exercícios visíveis; dá para ir aumentando
        n_total = ss.ex_blocks * 10
        st.caption(f"Concluídos neste nível: **{len(done)}** de {n_total}. O exercício nº é sempre o mesmo para todo mundo "
                   "do mesmo nível — dá para combinar \"hoje do 1 ao 3\".")
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
    vids = db.list_videos(lvl)
    if not vids:
        st.caption("Ainda não há vídeos neste nível." + (" Adicione pelo botão acima." if prof.is_admin else
                                                          " Peça ao administrador para adicionar."))
        return
    done = db.videos_done_map(email)
    series = sorted({v.get("series") or "Avulsos" for v in vids})
    if len(series) > 1:
        pick = st.segmented_control("Série", series, default=series[0], key=f"vser_{lvl}") or series[0]
        vids = [v for v in vids if (v.get("series") or "Avulsos") == pick]
    label = {v["id"]: f"{'✅ ' if v['id'] in done else ''}{i + 1}. {v['title']}" for i, v in enumerate(vids)}
    vid_id = st.selectbox("Vídeo", list(label), format_func=lambda k: label[k], key=f"vsel_{lvl}")
    v = next(x for x in vids if x["id"] == vid_id)
    st.video(v["url"])
    st.link_button("▶️ Não tocou aqui? Abrir no YouTube", v["url"], width="stretch")
    notes = v.get("notes")
    notes_json = json.dumps(notes, ensure_ascii=False) if isinstance(notes, (dict, list)) else (notes or "")
    if not notes_json:
        gem = prof.keys.get("gemini") or users.owner_key("gemini")
        if st.button("📖 Preparar perguntas (o Gemini assiste o vídeo uma única vez)", type="primary", width="stretch"):
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
                qs, u = learn.video_questions(notes_json, LEVELS[lvl]["cefr"], prof.keys.get("anthropic"), prev)
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
                res, u = learn.grade_answers(notes_json, qs, ans, LEVELS[lvl]["cefr"], prof.keys.get("anthropic"))
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


def translator_tab() -> None:
    st.caption("Digite ou fale uma palavra ou frase, em inglês ou português.")
    text = st.text_input("O que você quer traduzir?", key="tr_text", placeholder="ex.: 'cash flow' ou 'fazer hora extra'")
    rec = st.audio_input("…ou fale", key=f"tr_mic_{st.session_state.get('tr_mic', 0)}") if voice.can_listen() else None
    go = st.button("🔤 Traduzir", type="primary", width="stretch")
    if rec is not None:
        try:
            with st.spinner("Ouvindo..."):
                text, _ = voice.transcribe(rec.getvalue(), "audio/wav", log=log, language=None)
            st.session_state["tr_mic"] = st.session_state.get("tr_mic", 0) + 1
            go = True
        except Exception as e:
            st.error(f"Não entendi o áudio: {e}")
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
    ui.hero("📚 Aprender", "Trilhas separadas da conversa: gramática por nível, vídeos para treinar a escuta e um tradutor.")
    lvl = learn_level()
    t1, t2, t3 = st.tabs(["📝 Gramática", "🎬 Vídeos", "🔤 Tradutor"])
    with t1:
        grammar_tab(lvl)
    with t2:
        videos_tab(lvl)
    with t3:
        translator_tab()


# --- Roteamento das telas sem conversa ativa -----------------------------------------------
if not ss.started and ss.view != "inicio":
    {"historico": history_view, "ajustes": settings_view, "usuarios": users_view,
     "aprender": learn_view}.get(ss.view, history_view)()
    bottom_nav()
    st.stop()


# --- Tela inicial: escolher nível, modo e cenário ------------------------------------
if not ss.started:
    ui.brand()
    ui.hero("Pronto para conversar?", "Escolha o nível, o modo e o assunto. Ela responde e te ajuda a soar mais natural.")
    if ss.live_msg:
        st.info(ss.live_msg, icon="⚡")
        ss.live_msg = ""

    if prof.level_locked:
        st.markdown(f"**Nível:** {LEVELS[ss.level]['label']}")
    else:
        ss.level = st.pills("Nível", list(LEVELS), format_func=lambda k: LEVELS[k]["label"],
                            default=ss.level, selection_mode="single", key="level_pick") or ss.level

    live_ok, live_why, live_used = live_status()
    modes = {"maos": "🎧 Mãos livres", "apertar": "👆 Apertar para falar"}
    if live_ok:
        modes["aovivo"] = "⚡ Ao vivo"
    if not voice.can_listen():
        modes = {"texto": "⌨️ Só texto"}
    if ss.mode not in modes:
        ss.mode = list(modes)[0]
    ss.mode = st.pills("Modo", list(modes), format_func=lambda k: modes[k], default=ss.mode,
                       selection_mode="single", key="mode_pick") or ss.mode
    if live_ok:
        st.caption(f"⚡ Ao vivo: {max(0, prof.live_daily_minutes - live_used / 60):.0f} de "
                   f"{prof.live_daily_minutes} min hoje · Gemini grátis")
    elif prof.live_enabled:
        st.caption(f"⚡ Ao vivo indisponível: {live_why}.")

    kids = LEVELS[ss.level].get("kids")
    scen_keys = ["criancas"] if kids else [k for k in SCENARIOS if k != "criancas"]
    scen_key = st.pills("Cenário", scen_keys, format_func=lambda k: SCENARIOS[k]["label"],
                        default=scen_keys[0], selection_mode="single", key=f"scen_{int(bool(kids))}") or scen_keys[0]
    scen = SCENARIOS[scen_key]
    if scen["situations"]:
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
    if st.button("▶️ Começar conversa", type="primary", width="stretch", disabled=blocked):
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
if ss.mode == "aovivo" and not ss.summary:
    ui.pill(ss.context_label + " · ⚡ ao vivo")
    ok, why, used = live_status()
    res = live.live_call(ss.live_token or "", ss.system, used_seconds=used,
                         max_seconds=prof.live_daily_minutes * 60,
                         session_max_seconds=LIVE_MAX_SESSION_MIN * 60, session_key=ss.live_session_key)
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
        ui.ai_bubble(t["text"], hidden=hide)
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

ss.autoplay = False


def summary_block() -> None:
    st.divider()
    st.subheader("📋 Resumo da sessão")
    with st.container(border=True):
        st.markdown(ss.summary)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    doc = f"# Sessão de inglês — {ss.context_label}\n\n{ss.summary}\n\n---\n\n## Transcrição\n\n{transcript_text()}\n"
    d1, d2 = st.columns(2)
    d1.download_button("⬇️ Baixar resumo (.md)", doc, file_name=f"sessao_ingles_{stamp}.md",
                       mime="text/markdown", width="stretch")
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
with st.bottom:
    m1, m2 = st.columns([4, 1.3], vertical_alignment="center")
    with m1:
        if continuous:
            audio_b64 = base64.b64encode(ss.audio[0]).decode() if ss.audio else None
            utter = voice_chat(ss.reply_seq, audio_b64, ss.audio[1] if ss.audio else None, ss.listen_token)
        elif ss.mode == "apertar" and voice.can_listen():
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
