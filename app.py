"""English Practice — parceira de conversação em inglês com voz, correções e resumo."""

from datetime import datetime

import streamlit as st

from config import MAX_HISTORY_TURNS
from prompts import FREE_TALK_ROLE, SCENARIOS, START_MESSAGE, TUTOR_SYSTEM
from services import llm, voice

st.set_page_config(page_title="English Practice", page_icon="🗣️", layout="centered")


# --- Acesso (login com Google) ------------------------------------------------
def check_login() -> bool:
    """Só deixa entrar quem fizer login com Google e estiver em ALLOWED_EMAILS.

    Sem a seção [auth] nos Secrets (ex.: rodando local), o app abre sem login.
    """
    if "auth" not in st.secrets:
        return True
    if not st.user.get("is_logged_in", False):
        st.title("🗣️ English Practice")
        st.write("Entre com sua conta Google para praticar.")
        st.button("Entrar com Google", on_click=st.login, type="primary")
        return False
    allowed = [e.strip().lower() for e in st.secrets.get("ALLOWED_EMAILS", [])]
    if allowed and str(st.user.get("email", "")).lower() not in allowed:
        st.title("🗣️ English Practice")
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
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v if not isinstance(v, list) else list(v))
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
    except Exception as e:  # voz é opcional: a conversa segue sem ela
        ss.audio = None
        st.toast(f"Não consegui gerar o áudio: {e}", icon="⚠️")


def assistant_says(data: dict) -> None:
    ss.turns.append({"role": "assistant", "text": data["reply"], "suggestions": data["suggestions"]})
    set_audio(data["reply"])


def start_session(role: str, context_label: str) -> None:
    next_mic = ss.mic_key + 1
    for k, v in DEFAULTS.items():
        ss[k] = v if not isinstance(v, list) else list(v)
    ss.mic_key = next_mic
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


def transcript_text() -> str:
    who = {"user": "Aluno", "assistant": "Parceira"}
    return "\n".join(f"{who[t['role']]}: {t['text']}" for t in ss.turns)


# --- Barra lateral ------------------------------------------------------------
with st.sidebar:
    st.header("Configurar conversa")
    scen_key = st.selectbox(
        "Cenário", list(SCENARIOS), format_func=lambda k: SCENARIOS[k]["label"]
    )
    scen = SCENARIOS[scen_key]
    if scen["situations"]:
        situation = st.selectbox("Situação", list(scen["situations"]))
        role = scen["situations"][situation]
        context_label = f"{scen['label']} · {situation}"
    else:
        topic = st.text_input("Sobre o que você quer conversar?", placeholder="ex.: séries, futebol, viagens...")
        role = FREE_TALK_ROLE.format(topic=topic or "anything the learner wants; ask what they'd like to talk about")
        context_label = f"{scen['label']} · {topic or 'assunto livre'}"

    if st.button("▶️ Começar nova conversa", type="primary", use_container_width=True):
        try:
            start_session(role, context_label)
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao iniciar: {e}")

    st.divider()
    show_text = st.toggle("Mostrar texto das respostas", value=True,
                          help="Desligue para treinar a escuta: o texto fica escondido até você abrir.")
    user_turns = sum(t["role"] == "user" for t in ss.turns)
    if ss.started and st.button("🏁 Encerrar e ver resumo", use_container_width=True,
                                disabled=user_turns == 0):
        with st.spinner("Montando seu resumo..."):
            try:
                ss.summary = llm.session_summary(transcript_text(), ss.corrections)
            except Exception as e:
                st.error(f"Erro ao gerar o resumo: {e}")
        st.rerun()
    if ss.started:
        st.caption(f"Falas suas: {user_turns} · Correções: {len(ss.corrections)}")
    if not voice.can_listen():
        st.info("Sem chave de voz (GROQ, GEMINI ou OPENAI): microfone desligado, só texto.", icon="🎙️")
    if ss.voice_used:
        st.caption(ss.voice_used)
    if "auth" in st.secrets and st.user.get("is_logged_in", False):
        st.divider()
        st.caption(f"Conectado como {st.user.get('email', '')}")
        st.button("Sair", on_click=st.logout, use_container_width=True)


# --- Conversa -----------------------------------------------------------------
st.title("🗣️ English Practice")

if not ss.started:
    st.markdown(
        """
Escolha um **cenário** e uma **situação** na barra lateral e clique em **Começar nova conversa**.

Como funciona:
- 🎙️ **Fale** (ou digite) sua resposta — a parceira responde em voz.
- ✏️ Quando algo puder soar mais natural, aparece uma **dica curta** embaixo da sua fala.
- 🆘 Travou? Abra **Ideias de resposta** para ver duas frases que você pode usar.
- 🐢 Não entendeu? **Ouvir devagar**.
- 🏁 No fim, **Encerrar e ver resumo** mostra seus erros recorrentes e o que treinar.
"""
    )
    st.stop()

st.caption(ss.context_label)

last_ai = max((i for i, t in enumerate(ss.turns) if t["role"] == "assistant"), default=-1)

for i, t in enumerate(ss.turns):
    if t["role"] == "assistant":
        with st.chat_message("assistant", avatar="🧑‍🏫"):
            if show_text or i != last_ai:
                st.markdown(t["text"])
            else:
                with st.expander("👀 Ver texto"):
                    st.markdown(t["text"])
            if i == last_ai:
                if ss.audio:
                    st.audio(ss.audio[0], format=ss.audio[1], autoplay=ss.autoplay)
                c1, c2 = st.columns(2)
                if c1.button("🐢 Ouvir devagar", key=f"slow_{i}", use_container_width=True):
                    set_audio(t["text"], slow=True)
                    st.rerun()
                if c2.button("🔁 Ouvir normal", key=f"normal_{i}", use_container_width=True):
                    set_audio(t["text"])
                    st.rerun()
                if t.get("suggestions") and not ss.summary:
                    with st.expander("🆘 Travou? Ideias de resposta"):
                        for s in t["suggestions"]:
                            st.markdown(f"- {s}")
    else:
        with st.chat_message("user", avatar="🙋"):
            st.markdown(t["text"])
            c = t.get("correction")
            if c:
                st.info(f"✏️ **Mais natural:** {c['better']}\n\n💡 {c['tip_pt']}")

ss.autoplay = False  # toca só uma vez; reruns seguintes não repetem o áudio

# --- Resumo -------------------------------------------------------------------
if ss.summary:
    st.divider()
    st.subheader("📋 Resumo da sessão")
    st.markdown(ss.summary)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    doc = f"# Sessão de inglês — {ss.context_label}\n\n{ss.summary}\n\n---\n\n## Transcrição\n\n{transcript_text()}\n"
    st.download_button("⬇️ Baixar resumo + transcrição (.md)", doc,
                       file_name=f"sessao_ingles_{stamp}.md", mime="text/markdown")
    st.caption("Para continuar praticando, comece uma nova conversa na barra lateral.")
    st.stop()

# --- Entrada ------------------------------------------------------------------
if voice.can_listen():
    rec = st.audio_input("🎙️ Grave sua resposta", key=f"mic_{ss.mic_key}")
    if rec is not None:
        try:
            with st.spinner("Ouvindo..."):
                heard, provider = voice.transcribe(rec.getvalue())
            ss.voice_used = f"ouvido por: {provider}"
            if heard:
                handle_user(heard)
                st.rerun()
            else:
                st.warning("Não consegui entender o áudio. Tente de novo, mais perto do microfone.")
        except Exception as e:
            st.error(f"Erro: {e}")

typed = st.chat_input("Ou digite sua resposta em inglês...")
if typed:
    try:
        handle_user(typed)
        st.rerun()
    except Exception as e:
        st.error(f"Erro: {e}")
