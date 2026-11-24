"""Voz: transcrição (você → texto) e fala (texto → áudio).

Com OPENAI_API_KEY: Whisper para ouvir e TTS da OpenAI para falar.
Sem a chave: o microfone fica desligado e a fala usa o gTTS (grátis, voz mais robótica).
"""

import io

import streamlit as st

from config import STT_MODEL, TTS_MODEL, TTS_SPEED_NORMAL, TTS_SPEED_SLOW, TTS_VOICE


def has_openai() -> bool:
    return bool(st.secrets.get("OPENAI_API_KEY", ""))


@st.cache_resource
def _openai():
    from openai import OpenAI

    return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def transcribe(audio_bytes: bytes) -> str:
    result = _openai().audio.transcriptions.create(
        model=STT_MODEL,
        file=("speech.wav", audio_bytes),
        language="en",
    )
    return (result.text or "").strip()


def speak(text: str, slow: bool = False) -> tuple[bytes, str]:
    """Retorna (bytes_do_audio, mime)."""
    if has_openai():
        resp = _openai().audio.speech.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=text,
            speed=TTS_SPEED_SLOW if slow else TTS_SPEED_NORMAL,
        )
        return resp.content, "audio/mp3"

    from gtts import gTTS

    buf = io.BytesIO()
    gTTS(text=text, lang="en", tld="us", slow=slow).write_to_fp(buf)
    return buf.getvalue(), "audio/mp3"
