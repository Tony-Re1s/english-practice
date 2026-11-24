"""English Practice — parceira de conversação em inglês com voz, correções e resumo."""

import base64
from datetime import datetime

import streamlit as st

import ui
from config import MAX_HISTORY_TURNS
from prompts import FREE_TALK_ROLE, SCENARIOS, START_MESSAGE, TUTOR_SYSTEM
from services import llm, voice
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
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v if not isinstance(v, list) else list(v))
# contadores que nunca zeram (o microfone contínuo usa para saber o que é novo)
st.session_state.setdefault("reply_seq", 0)
st.session_state.setdefault("listen_token", 0)
ss = st.session_state


def api_messages() -> list[dict]:
    """Monta o histórico no formato da API (começa sempre com a mensagem de abertura)."""
    turns = ss.turns[-MAX_HISTORY_TURNS:]
    if turns and turns[0]["role"] == "user":
        turns = turns[1:]  # após a abertura (user), a próxima precisa ser do assistant
    msgs = [{"role": "user", "content": START_MESSAGE}]
    msgs += [{"role": t["role"], "content": t["text"]} for t in turns]
    return msgs


def set_audio(text: str, slow: bool = False) -> None:
    try:
        data, mime, provider = voice.speak(text, slow=slow)
        ss.audio = (data, mime)
        ss.voice_used = f"voz: {provider}"
        ss.autoplay = True
        ss.reply_seq += 1
    except Exception as e:  # voz é opcional: a conversa segue sem ela
        ss.audio = None
        st.toast(f"Não consegui gerar o áudio: {e}", icon="⚠️")


def assistant_says(data: dict) -> None:
    ss.turns.append({"role": "assistant", "text": data["reply"], "suggestions": data["suggestions"]})
    set_audio(data["reply"])


def reset_session() -> None:
    next_mic = ss.mic_key + 1
    for k, v in DEFAULTS.items():
        ss[k] = v if not isinstance(v, list) else list(v)
    ss.mic_key = next_mic


def start_session(role: str, context_label: str) -> None:
    reset_session()
    ss.role, ss.context_label, ss.started = role, context_label, True
    with st.spinner("Preparando a conversa..."):
        data = llm.tutor_turn(TUTOR_SYSTEM.format(role=role), api_messages())
    assistant_says(data)


def handle_user(text: str) -> None:
    text = text.strip()
    if not text:
        return
    ss.turns.append({"role": "user", "text": text})
    try:
        with st.spinner("Pensando..."):
            data = llm.tutor_turn(TUTOR_SYSTEM.format(role=ss.role), api_messages())
    except Exception:
        ss.turns.pop()  # mantém o histórico alternado para a próxima tentativa
        raise
    corr = data.get("correction")
    if corr and corr.get("better") and corr["better"].strip().lower() != text.lower():
        ss.turns[-1]["correction"] = corr
        ss.corrections.append(corr)
    assistant_says(data)
    ss.mic_key += 1  # limpa o gravador para a próxima fala


def handle_audio(audio: bytes, mime: str) -> None:
    """Transcreve a fala e segue a conversa. Sempre avança o listen_token (sucesso ou falha)."""
    try:
        with st.spinner("Ouvindo..."):
            heard, provider = voice.transcribe(audio, mime)
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
    with st.spinner("Montando seu resumo..."):
        try:
            ss.summary = llm.session_summary(transcript_text(), ss.corrections)
        except Exception as e:
            st.error(f"Erro ao gerar o resumo: {e}")


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
    show_text = st.toggle("Mostrar texto das respostas", value=True,
                          help="Desligue para treinar a escuta: o texto fica escondido até você abrir.")
    if not can_listen:
        st.info("Sem chave de voz (GROQ, GEMINI ou OPENAI): microfone desligado, só texto.", icon="🎙️")
    if ss.voice_used:
        st.caption(ss.voice_used)
    if ss.started:
        user_turns = sum(t["role"] == "user" for t in ss.turns)
        st.caption(f"Falas suas: {user_turns} · Correções: {len(ss.corrections)}")
    if "auth" in st.secrets and st.user.get("is_logged_in", False):
        st.divider()
        st.caption(f"Conectado como {st.user.get('email', '')}")
        st.button("Sair", on_click=st.logout, use_container_width=True)


# --- Tela inicial: escolher o cenário ------------------------------------------
if not ss.started:
    ui.hero("🗣️ English Practice",
            "Escolha um cenário, toque em começar e converse. Você fala, ela responde e te ajuda a soar mais natural.")
    scen_key = st.pills("Cenário", list(SCENARIOS), format_func=lambda k: SCENARIOS[k]["label"],
                        default="dia_a_dia", selection_mode="single") or "dia_a_dia"
    scen = SCENARIOS[scen_key]
    if scen["situations"]:
        situation = st.pills("Situação", list(scen["situations"]), selection_mode="single",
                             default=list(scen["situations"])[0]) or list(scen["situations"])[0]
        role = scen["situations"][situation]
        context_label = f"{scen['label']} · {situation}"
    else:
        topic = st.text_input("Sobre o que você quer conversar hoje?",
                              placeholder="ex.: minha viagem de intercâmbio, futebol, séries...")
        role = FREE_TALK_ROLE.format(topic=topic or "anything the learner wants; ask what they'd like to talk about")
        context_label = f"{scen['label']} · {topic or 'assunto livre'}"

    if st.button("▶️ Começar conversa", type="primary", use_container_width=True):
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
            "- 🆘 Travou? Abra **Ideias de resposta**.\n"
            "- 🐢 Não entendeu? **Ouvir devagar**.\n"
            "- 🏁 No fim, **Encerrar** mostra seus erros recorrentes e o que treinar."
        )
    st.stop()


# --- Conversa -----------------------------------------------------------------
c1, c2, c3 = st.columns([3, 1.2, 1.2], vertical_alignment="center")
with c1:
    ui.pill(ss.context_label)
user_turns = sum(t["role"] == "user" for t in ss.turns)
if c2.button("🏁 Encerrar", use_container_width=True, disabled=user_turns == 0 or bool(ss.summary)):
    finish_session()
    st.rerun()
if c3.button("🔄 Nova", use_container_width=True):
    reset_session()
    st.rerun()

last_ai = max((i for i, t in enumerate(ss.turns) if t["role"] == "assistant"), default=-1)

for i, t in enumerate(ss.turns):
    if t["role"] == "assistant":
        hide = not show_text and i == last_ai
        ui.ai_bubble(t["text"], hidden=hide)
        if i == last_ai:
            if hide:
                with st.expander("👀 Ver texto"):
                    st.markdown(t["text"])
            if ss.audio and not continuous:
                st.audio(ss.audio[0], format=ss.audio[1], autoplay=ss.autoplay)
            b1, b2 = st.columns(2)
            if b1.button("🐢 Ouvir devagar", key=f"slow_{i}", use_container_width=True):
                set_audio(t["text"], slow=True)
                st.rerun()
            if b2.button("🔁 Ouvir de novo", key=f"normal_{i}", use_container_width=True):
                set_audio(t["text"])
                st.rerun()
            if t.get("suggestions") and not ss.summary:
                with st.expander("🆘 Travou? Ideias de resposta"):
                    for s in t["suggestions"]:
                        st.markdown(f"- {s}")
    else:
        ui.user_bubble(t["text"])
        c = t.get("correction")
        if c:
            ui.correction(c["better"], c["tip_pt"])

ss.autoplay = False  # toca só uma vez; reruns seguintes não repetem o áudio

# --- Resumo -------------------------------------------------------------------
if ss.summary:
    st.divider()
    st.subheader("📋 Resumo da sessão")
    with st.container(border=True):
        st.markdown(ss.summary)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    doc = f"# Sessão de inglês — {ss.context_label}\n\n{ss.summary}\n\n---\n\n## Transcrição\n\n{transcript_text()}\n"
    st.download_button("⬇️ Baixar resumo + transcrição (.md)", doc,
                       file_name=f"sessao_ingles_{stamp}.md", mime="text/markdown")
    st.caption("Para continuar praticando, toque em 🔄 Nova.")
    st.stop()

# --- Entrada ------------------------------------------------------------------
if ss.last_error:
    st.warning(ss.last_error, icon="⚠️")
if continuous:
    audio_b64 = base64.b64encode(ss.audio[0]).decode() if ss.audio else None
    utter = voice_chat(ss.reply_seq, audio_b64, ss.audio[1] if ss.audio else None, ss.listen_token)
    if utter and utter.get("b64"):
        handle_audio(base64.b64decode(utter["b64"]), utter.get("mime") or "audio/webm")
        st.rerun()
elif can_listen:
    rec = st.audio_input("🎙️ Grave sua resposta", key=f"mic_{ss.mic_key}")
    if rec is not None:
        handle_audio(rec.getvalue(), "audio/wav")
        st.rerun()

typed = st.chat_input("Ou digite sua resposta em inglês...")
if typed:
    try:
        handle_user(typed)
        st.rerun()
    except Exception as e:
        st.error(f"Erro: {e}")
