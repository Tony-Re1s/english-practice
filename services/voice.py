"""Voz com fallback: tenta o grátis primeiro e só cai no pago se o anterior falhar.

OUVIR (sua fala → texto):   Groq Whisper (grátis) → Gemini → OpenAI
FALAR (texto → áudio):      Edge TTS (grátis) → Gemini → OpenAI → gTTS (grátis, robótica)

Cada etapa só entra se a chave dela estiver nos Secrets (Edge e gTTS não usam chave).
"""

import asyncio
import io
import wave

import streamlit as st

from config import (
    EDGE_RATE_NORMAL, EDGE_RATE_SLOW, EDGE_VOICE,
    GEMINI_STT_MODEL, GEMINI_TTS_MODEL, GEMINI_VOICE,
    GROQ_STT_MODEL,
    OPENAI_STT_MODEL, OPENAI_TTS_MODEL, OPENAI_TTS_VOICE,
)

SLOW_INSTRUCTION = "Speak clearly and a bit slowly, like a patient English teacher."
NORMAL_INSTRUCTION = "Speak naturally and clearly, in a friendly tone."


def _key(name: str) -> str:
    return str(st.secrets.get(name, "") or "")


def can_listen() -> bool:
    return any(_key(k) for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY"))


# --- Clientes -----------------------------------------------------------------
@st.cache_resource
def _openai():
    from openai import OpenAI
    return OpenAI(api_key=_key("OPENAI_API_KEY"))


@st.cache_resource
def _groq():
    from openai import OpenAI  # a Groq aceita o mesmo SDK
    return OpenAI(api_key=_key("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")


@st.cache_resource
def _gemini():
    from google import genai
    return genai.Client(api_key=_key("GEMINI_API_KEY"))


# --- Ouvir ---------------------------------------------------------------------
EXT = {"audio/wav": "wav", "audio/x-wav": "wav", "audio/webm": "webm", "audio/mp4": "mp4",
       "audio/mpeg": "mp3", "audio/ogg": "ogg", "audio/aac": "aac"}


def _fname(mime: str) -> str:
    return "speech." + EXT.get(mime, "webm")


def _stt_groq(audio: bytes, mime: str) -> str:
    r = _groq().audio.transcriptions.create(
        model=GROQ_STT_MODEL, file=(_fname(mime), audio), language="en")
    return r.text


def _stt_gemini(audio: bytes, mime: str) -> str:
    from google.genai import types
    r = _gemini().models.generate_content(
        model=GEMINI_STT_MODEL,
        contents=[
            "Transcribe this English speech exactly as spoken. "
            "Return only the transcript, without comments. Keep the speaker's mistakes.",
            types.Part.from_bytes(data=audio, mime_type=mime),
        ],
    )
    return r.text or ""


def _stt_openai(audio: bytes, mime: str) -> str:
    r = _openai().audio.transcriptions.create(
        model=OPENAI_STT_MODEL, file=(_fname(mime), audio), language="en")
    return r.text


STT_CHAIN = [
    ("Groq", "GROQ_API_KEY", _stt_groq),
    ("Gemini", "GEMINI_API_KEY", _stt_gemini),
    ("OpenAI", "OPENAI_API_KEY", _stt_openai),
]


def transcribe(audio: bytes, mime: str = "audio/wav") -> tuple[str, str]:
    """Retorna (texto, provedor_usado)."""
    errors = []
    for name, key, fn in STT_CHAIN:
        if not _key(key):
            continue
        try:
            text = (fn(audio, mime) or "").strip()
            if text:
                return text, name
            errors.append(f"{name}: vazio")
        except Exception as e:
            errors.append(f"{name}: {e}")
    raise RuntimeError("Nenhum serviço conseguiu transcrever. " + " | ".join(errors))


# --- Falar ---------------------------------------------------------------------
def _tts_edge(text: str, slow: bool) -> tuple[bytes, str]:
    import edge_tts

    async def _run() -> bytes:
        comm = edge_tts.Communicate(text, EDGE_VOICE, rate=EDGE_RATE_SLOW if slow else EDGE_RATE_NORMAL)
        buf = bytearray()
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                buf.extend(chunk["data"])
        return bytes(buf)

    data = asyncio.run(_run())
    if not data:
        raise RuntimeError("Edge TTS não devolveu áudio")
    return data, "audio/mp3"


def _pcm_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def _tts_gemini(text: str, slow: bool) -> tuple[bytes, str]:
    style = "slow, clear and patient" if slow else "natural, friendly and clear"
    r = _gemini().models.generate_content(
        model=GEMINI_TTS_MODEL,
        contents=[{"role": "user", "parts": [{"text": text, "speech_metadata": {"style": style}}]}],
        config={
            "response_modalities": ["AUDIO"],
            "speech_config": {"voice_config": {"voice": GEMINI_VOICE}},
        },
    )
    data = r.candidates[0].content.parts[0].inline_data.data
    if not data.startswith(b"RIFF"):  # garante WAV tocável mesmo se vier PCM cru
        data = _pcm_to_wav(data)
    return data, "audio/wav"


def _tts_openai(text: str, slow: bool) -> tuple[bytes, str]:
    r = _openai().audio.speech.create(
        model=OPENAI_TTS_MODEL, voice=OPENAI_TTS_VOICE, input=text,
        instructions=SLOW_INSTRUCTION if slow else NORMAL_INSTRUCTION,
        response_format="mp3",
    )
    return r.content, "audio/mp3"


def _tts_gtts(text: str, slow: bool) -> tuple[bytes, str]:
    from gtts import gTTS
    buf = io.BytesIO()
    gTTS(text=text, lang="en", tld="us", slow=slow).write_to_fp(buf)
    return buf.getvalue(), "audio/mp3"


TTS_CHAIN = [
    ("Edge", None, _tts_edge),
    ("Gemini", "GEMINI_API_KEY", _tts_gemini),
    ("OpenAI", "OPENAI_API_KEY", _tts_openai),
    ("gTTS", None, _tts_gtts),
]


def speak(text: str, slow: bool = False) -> tuple[bytes, str, str]:
    """Retorna (bytes_do_audio, mime, provedor_usado)."""
    errors = []
    for name, key, fn in TTS_CHAIN:
        if key and not _key(key):
            continue
        try:
            data, mime = fn(text, slow)
            if data:
                return data, mime, name
        except Exception as e:
            errors.append(f"{name}: {e}")
    raise RuntimeError("Nenhum serviço conseguiu gerar a voz. " + " | ".join(errors))
