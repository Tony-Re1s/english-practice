"""English Practice — parceira de conversação em inglês com voz, correções e resumo."""

import base64
from datetime import datetime

import streamlit as st

import ui
from config import DEFAULT_LEVEL, LEVELS, MAX_HISTORY_TURNS
from prompts import FREE_TALK_OPEN, FREE_TALK_ROLE, SCENARIOS, START_MESSAGE, TOPIC_ROLE, TUTOR_SYSTEM
from services import db, llm, voice
from services.voice_chat import voice_chat

st.set_page_config(page_title="English Practice", page_icon="🗣️", layout="centered")
ui.inject_css()


# --- Acesso (login com Google) ------------------------------------------------
def check_login() -> bool:
    """Só deixa entrar quem fizer login com Google e estiver em ALLOWED_EMAILS.

    Sem a seção [auth] nos Secrets (ex.: rodando local), o app abre sem login.
    """
    if "auth" not in st.secrets:
        return True
    if not st.user.get("is_logged_in", False):
        ui.hero("🗣️ English Practice", "Sua parceira de conversação em inglês. Entre com sua conta Google para praticar.")
        st.button("Entrar com Google", on_click=st.login, type="primary")
        return False
    allowed = [e.strip().lower() for e in st.secrets.get("ALLOWED_EMAILS", [])]
    if allowed and str(st.user.get("email", "")).lower() not in allowed:
        ui.hero("🗣️ English Practice", "Acesso restrito.")
        st.error(f"A conta {st.user.get('email')} não tem acesso a este app.")
        st.button("Sair", on_click=st.logout)
        return False
    return True


if not check_login():
    st.stop()


# --- Estado -------------------------------------------------------------------
DEFAULTS = {
    "started": False,
    "role": "",
    "context_label": "",
    "turns": [],          # [{'role': 'user'|'assistant', 'text', 'correction'?, 'suggestions'?}]
    "corrections": [],
    "mic_key": 0,
    "audio": None,        # (bytes, mime) da última fala da IA
    "autoplay": False,
    "summary": None,
    "voice_used": "",
    "last_error": "",
    "session_id": None,
    "system": "",
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v if not isinstance(v, list) else list(v))
# contadores que nunca zeram (o microfone contínuo usa para saber o que é novo)
st.session_state.setdefault("reply_seq", 0)
st.session_state.setdefault("listen_token", 0)
st.session_state.setdefault("level", DEFAULT_LEVEL)
st.session_state.setdefault("view", "conversa")
st.session_state.setdefault("slow_voice", False)   # "voz devagar" fica ligada até você desligar
ss = st.session_state


def user_email() -> str:
    try:
        return str(st.user.get("email") or "local")
    except Exception:
        return "local"


def log(**kw) -> None:
    """Registra uma chamada de IA no banco (se configurado)."""
    db.log_usage(user_email(), ss.session_id, **kw)


def call_tutor() -> dict:
    try:
        data = llm.tutor_turn(ss.system, api_messages())
    except Exception as e:
        log(step="conversa", provider="Anthropic", model=llm.CHAT_MODEL, ok=False, error=str(e)[:500])
        raise
    u = data.pop("_usage", {})
    log(step="conversa", provider="Anthropic", model=u.get("model", llm.CHAT_MODEL), ok=True,
        input_tokens=u.get("input_tokens"), output_tokens=u.get("output_tokens"))
    return data


def api_messages() -> list[dict]:
    """Monta o histórico no formato da API (começa sempre com a mensagem de abertura)."""
    turns = ss.turns[-MAX_HISTORY_TURNS:]
    if turns and turns[0]["role"] == "user":
        turns = turns[1:]  # após a abertura (user), a próxima precisa ser do assistant
    msgs = [{"role": "user", "content": START_MESSAGE}]
    msgs += [{"role": t["role"], "content": t["text"]} for t in turns]
    return msgs


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
        ss[k] = v if not isinstance(v, list) else list(v)
    ss.mic_key = next_mic


def start_session(role: str, context_label: str) -> None:
    reset_session()
    lv = LEVELS[ss.level]
    ss.role, ss.started = role, True
    ss.context_label = f"{context_label} · {lv['label']}"
    ss.system = TUTOR_SYSTEM.format(role=role, cefr=lv["cefr"], level_guide=lv["guide"])
    ss.session_id = db.start_session(user_email(), ss.level, ss.context_label)
    with st.spinner("Preparando a conversa..."):
        data = call_tutor()
    assistant_says(data)


def handle_user(text: str) -> None:
    text = text.strip()
    if not text:
        return
    ss.turns.append({"role": "user", "text": text})
    try:
        with st.spinner("Pensando..."):
            data = call_tutor()
    except Exception:
        ss.turns.pop()  # mantém o histórico alternado para a próxima tentativa
        raise
    corr = data.get("correction")
    if corr and corr.get("better") and corr["better"].strip().lower() != text.lower():
        ss.turns[-1]["correction"] = corr
        ss.corrections.append(corr)
    else:
        corr = None
    db.add_turn(ss.session_id, "user", text, corr)
    assistant_says(data)
    ss.mic_key += 1  # limpa o gravador para a próxima fala
    if data.get("end_session"):  # você pediu para encerrar falando ("let's stop here")
        finish_session()


def handle_audio(audio: bytes, mime: str) -> None:
    """Transcreve a fala e segue a conversa. Sempre avança o listen_token (sucesso ou falha)."""
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
            ss.summary, u = llm.session_summary(transcript_text(), ss.corrections, LEVELS[ss.level]["cefr"])
            log(step="resumo", provider="Anthropic", model=u["model"], ok=True,
                input_tokens=u["input_tokens"], output_tokens=u["output_tokens"])
        except Exception as e:
            log(step="resumo", provider="Anthropic", model=llm.SUMMARY_MODEL, ok=False, error=str(e)[:500])
            ss.summary = "_Não consegui gerar o resumo desta vez._"
            st.error(f"Erro ao gerar o resumo: {e}")
    db.end_session(ss.session_id, ss.summary)


# --- Barra lateral: ajustes -----------------------------------------------------
with st.sidebar:
    st.subheader("⚙️ Ajustes")
    can_listen = voice.can_listen()
    mode = st.radio(
        "Modo de conversa",
        ["🎧 Contínua (mãos livres)", "👆 Apertar para falar"],
        disabled=not can_listen,
        help="Contínua: o microfone ouve sozinho e para quando você termina de falar.",
    )
    continuous = can_listen and mode.startswith("🎧")
    ss.slow_voice = st.toggle("🐢 Voz devagar", value=ss.slow_voice,
                              help="A parceira fala mais devagar em toda a conversa.")
    show_text = st.toggle("Mostrar texto das respostas", value=True,
                          help="Desligue para treinar a escuta: o texto fica escondido até você abrir.")
    if not can_listen:
        st.info("Sem chave de voz (GROQ, GEMINI ou OPENAI): microfone desligado, só texto.", icon="🎙️")
    if ss.voice_used:
        st.caption(ss.voice_used)
    if ss.started:
        user_turns = sum(t["role"] == "user" for t in ss.turns)
        st.caption(f"Falas suas: {user_turns} · Correções: {len(ss.corrections)}")
    st.divider()
    if ss.view == "uso":
        if st.button("💬 Voltar para a conversa", width="stretch"):
            ss.view = "conversa"
            st.rerun()
    elif st.button("📊 Uso e histórico", width="stretch"):
        ss.view = "uso"
        st.rerun()
    if "auth" in st.secrets and st.user.get("is_logged_in", False):
        st.caption(f"Conectado como {st.user.get('email', '')}")
        st.button("Sair", on_click=st.logout, width="stretch")


# --- Tela: uso e histórico -------------------------------------------------------
def usage_view() -> None:
    ui.hero("📊 Uso e histórico", "Quais IAs foram usadas, quanto custou (estimado) e suas conversas anteriores.")
    if not db.enabled():
        st.info("O registro ainda não está ligado. Falta colocar o **DATABASE_URL** (Neon) nos Secrets do app.",
                icon="🗄️")
        return
    import pandas as pd

    days = st.segmented_control("Período", [7, 30, 90], default=30, format_func=lambda d: f"{d} dias") or 30
    rows = db.usage_by_provider(user_email(), days)
    df = pd.DataFrame(rows)
    if df.empty:
        st.caption("Nenhum uso registrado ainda neste período.")
    else:
        df["custo_usd"] = df["custo_usd"].astype(float)
        total = df["custo_usd"].sum()
        openai_calls = int(df.loc[df["servico"] == "OpenAI", "chamadas"].sum())
        openai_cost = df.loc[df["servico"] == "OpenAI", "custo_usd"].sum()
        sessions = db.sessions_recent(user_email(), 500)
        m1, m2, m3 = st.columns(3)
        m1.metric("Custo estimado", f"US$ {total:.3f}")
        m2.metric("Chamadas à OpenAI", openai_calls, help="A OpenAI só entra quando os serviços grátis falham.")
        m3.metric("Custo OpenAI", f"US$ {openai_cost:.3f}")
        if openai_calls:
            st.warning(f"A OpenAI (crédito pago) foi usada {openai_calls} vez(es) nos últimos {days} dias. "
                       "Veja abaixo as falhas que levaram a isso.", icon="💳")
        else:
            st.success("Nenhum uso da OpenAI no período: só serviços grátis e o Claude.", icon="✅")
        st.markdown("**Por etapa e serviço**")
        st.dataframe(df, hide_index=True, width="stretch")
    with st.expander("🕒 Últimas chamadas (inclui falhas e trocas de serviço)"):
        st.dataframe(pd.DataFrame(db.usage_recent(user_email())), hide_index=True, width="stretch")
    st.caption("Custos são estimativas pela tabela de preços do app. Valores oficiais: "
               "platform.claude.com (Anthropic) e platform.openai.com/usage (OpenAI).")

    st.markdown("### 🗂️ Conversas anteriores")
    sess = db.sessions_recent(user_email())
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
                import json
                c = json.loads(c)
            if c:
                ui.correction(c.get("better", ""), c.get("tip_pt", ""))
    if chosen.get("summary"):
        with st.expander("📋 Resumo dessa conversa", expanded=True):
            st.markdown(chosen["summary"])


if ss.view == "uso":
    usage_view()
    st.stop()


# --- Tela inicial: escolher o cenário ------------------------------------------
if not ss.started:
    ui.hero("🗣️ English Practice",
            "Escolha o nível e o cenário, toque em começar e converse. Ela responde e te ajuda a soar mais natural.")
    ss.level = st.pills("Nível", list(LEVELS), format_func=lambda k: f"{LEVELS[k]['label']} ({LEVELS[k]['cefr']})",
                        default=ss.level, selection_mode="single", key="level_pick") or ss.level
    scen_key = st.pills("Cenário", list(SCENARIOS), format_func=lambda k: SCENARIOS[k]["label"],
                        default="dia_a_dia", selection_mode="single") or "dia_a_dia"
    scen = SCENARIOS[scen_key]
    if scen["situations"]:
        situation = st.pills("Assunto" if scen_key == "assuntos" else "Situação", list(scen["situations"]),
                             selection_mode="single", default=list(scen["situations"])[0]) or list(scen["situations"])[0]
        role = scen["situations"][situation]
        if scen_key == "assuntos":
            role = TOPIC_ROLE.format(topic=role)
        context_label = f"{scen['label']} · {situation}"
    else:
        topic = st.text_input("Sobre o que você quer conversar hoje?",
                              placeholder="ex.: taxa de juros, minha viagem de intercâmbio, futebol... (ou deixe vazio)")
        role = FREE_TALK_ROLE.format(topic=topic) if topic.strip() else FREE_TALK_OPEN
        context_label = f"{scen['label']} · {topic or 'você escolhe na conversa'}"

    if st.button("▶️ Começar conversa", type="primary", width="stretch"):
        try:
            start_session(role, context_label)
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao iniciar: {e}")

    with st.expander("Como funciona"):
        st.markdown(
            "- 🎧 **Modo contínuo**: toque no microfone uma vez e converse. Ele para sozinho quando você termina de "
            "falar e volta a ouvir depois da resposta. Toque de novo para **pausar** e pensar.\n"
            "- ✏️ Quando algo puder soar mais natural, aparece uma **dica amarela** embaixo da sua fala.\n"
            "- 🆘 Travou? Abra **Ideias de resposta**. 🐢 **Falar devagar** fica ligado até você desligar.\n"
            "- 🏁 Para terminar, toque em **Encerrar** ou simplesmente diga *\"let's stop here\"*. "
            "Você recebe o resumo com seus erros recorrentes.\n"
            "- 📊 Em **Uso e histórico** (barra lateral) você vê quais IAs foram usadas, o custo e as conversas antigas."
        )
    st.stop()


# --- Conversa -----------------------------------------------------------------
ui.pill(ss.context_label)

last_ai = max((i for i, t in enumerate(ss.turns) if t["role"] == "assistant"), default=-1)

for i, t in enumerate(ss.turns):
    if t["role"] == "assistant":
        hide = not show_text and i == last_ai and not ss.summary
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

ss.autoplay = False  # toca só uma vez; reruns seguintes não repetem o áudio

# --- Resumo (conversa encerrada: microfone desligado) -----------------------------
if ss.summary:
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
    st.stop()

# --- Entrada (rodapé fixo: microfone + encerrar + texto, sempre visíveis) -----------
if ss.last_error:
    st.warning(ss.last_error, icon="⚠️")

utter = rec = None
with st._bottom:
    m1, m2 = st.columns([4, 1.3], vertical_alignment="center")
    with m1:
        if continuous:
            audio_b64 = base64.b64encode(ss.audio[0]).decode() if ss.audio else None
            utter = voice_chat(ss.reply_seq, audio_b64, ss.audio[1] if ss.audio else None, ss.listen_token)
        elif can_listen:
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
