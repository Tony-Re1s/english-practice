"""Voz com fallback: tenta o grátis primeiro e só cai no pago se o anterior falhar.

OUVIR (sua fala → texto):   Groq Whisper (grátis) → Gemini → OpenAI
FALAR (texto → áudio):      Edge TTS (grátis) → Gemini → OpenAI → gTTS (grátis, robótica)

Cada etapa só entra se a chave dela estiver nos Secrets (Edge e gTTS não usam chave).
"""

import asyncio
import io
import threading
import time
import wave

import streamlit as st

from config import (
    EDGE_RATES, EDGE_VOICE,
    GEMINI_STT_MODEL, GEMINI_TTS_MODEL, GEMINI_VOICE,
    GROQ_STT_MODEL,
    OPENAI_STT_MODEL, OPENAI_TTS_MODEL, OPENAI_TTS_VOICE,
)

PACE_INSTRUCTION = {
    "slow": "Speak clearly and slowly, like a patient English teacher, with small pauses between phrases.",
    "calm": "Speak clearly and a little slower than normal, in a friendly tone.",
    "normal": "Speak naturally and clearly, in a friendly tone.",
    "brisk": "Speak at a natural native-speaker pace, relaxed and friendly.",
}


def audio_seconds(audio: bytes) -> float | None:
    """Duração de um WAV (None se não for WAV)."""
    try:
        with wave.open(io.BytesIO(audio)) as w:
            return round(w.getnframes() / float(w.getframerate()), 2)
    except Exception:
        return None


# Chaves da pessoa usando o app agora (isoladas por sessão: cada sessão roda na sua própria thread)
_local = threading.local()


def set_keys(keys: dict) -> None:
    """Define quais chaves valem para esta pessoa (a do dono, a própria, ou nenhuma)."""
    _local.keys = {k: v for k, v in (keys or {}).items() if v}


def _key(provider: str) -> str:
    return str(getattr(_local, "keys", {}).get(provider) or "")


def can_listen() -> bool:
    return any(_key(k) for k in ("groq", "gemini", "openai"))


# --- Clientes (um por chave) ------------------------------------------------------
@st.cache_resource(max_entries=20)
def _openai_client(key: str):
    from openai import OpenAI
    return OpenAI(api_key=key)


@st.cache_resource(max_entries=20)
def _groq_client(key: str):
    from openai import OpenAI  # a Groq aceita o mesmo SDK
    return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")


@st.cache_resource(max_entries=20)
def _gemini_client(key: str):
    from google import genai
    return genai.Client(api_key=key)


def _openai():
    return _openai_client(_key("openai"))


def _groq():
    return _groq_client(_key("groq"))


def _gemini():
    return _gemini_client(_key("gemini"))


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
    ("Groq", "groq", GROQ_STT_MODEL, _stt_groq),
    ("Gemini", "gemini", GEMINI_STT_MODEL, _stt_gemini),
    ("OpenAI", "openai", OPENAI_STT_MODEL, _stt_openai),
]


def _noop(**_):
    pass


def transcribe(audio: bytes, mime: str = "audio/wav", log=_noop) -> tuple[str, str]:
    """Retorna (texto, provedor_usado). Chama log(...) para cada tentativa, inclusive as que falharem."""
    errors = []
    secs = audio_seconds(audio)
    for name, key, model, fn in STT_CHAIN:
        if not _key(key):
            continue
        t0 = time.time()
        try:
            text = (fn(audio, mime) or "").strip()
            if text:
                log(step="ouvir", provider=name, model=model, ok=True, audio_seconds=secs,
                    latency_ms=int((time.time() - t0) * 1000))
                return text, name
            errors.append(f"{name}: vazio")
            log(step="ouvir", provider=name, model=model, ok=False, audio_seconds=secs, error="transcrição vazia")
        except Exception as e:
            print(f"[voz] {name} falhou ao ouvir: {e}", flush=True)
            errors.append(f"{name}: {e}")
            log(step="ouvir", provider=name, model=model, ok=False, audio_seconds=secs, error=str(e)[:500])
    raise RuntimeError("Nenhum serviço conseguiu transcrever. " + " | ".join(errors))


# --- Falar ---------------------------------------------------------------------
def _tts_edge(text: str, pace: str) -> tuple[bytes, str]:
    import edge_tts

    async def _run() -> bytes:
        comm = edge_tts.Communicate(text, EDGE_VOICE, rate=EDGE_RATES.get(pace, "+0%"))
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


def _tts_gemini(text: str, pace: str) -> tuple[bytes, str]:
    style = PACE_INSTRUCTION.get(pace, PACE_INSTRUCTION["normal"])
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


def _tts_openai(text: str, pace: str) -> tuple[bytes, str]:
    r = _openai().audio.speech.create(
        model=OPENAI_TTS_MODEL, voice=OPENAI_TTS_VOICE, input=text,
        instructions=PACE_INSTRUCTION.get(pace, PACE_INSTRUCTION["normal"]),
        response_format="mp3",
    )
    return r.content, "audio/mp3"


def _tts_gtts(text: str, pace: str) -> tuple[bytes, str]:
    from gtts import gTTS
    buf = io.BytesIO()
    gTTS(text=text, lang="en", tld="us", slow=(pace == "slow")).write_to_fp(buf)
    return buf.getvalue(), "audio/mp3"


TTS_CHAIN = [
    ("Edge", None, EDGE_VOICE, _tts_edge),
    ("Gemini", "gemini", GEMINI_TTS_MODEL, _tts_gemini),
    ("OpenAI", "openai", OPENAI_TTS_MODEL, _tts_openai),
    ("gTTS", None, "gtts", _tts_gtts),
]


def speak(text: str, pace: str = "normal", log=_noop) -> tuple[bytes, str, str]:
    """Retorna (bytes_do_audio, mime, provedor_usado). pace: slow | calm | normal | brisk."""
    errors = []
    for name, key, model, fn in TTS_CHAIN:
        if key and not _key(key):
            continue
        t0 = time.time()
        try:
            data, mime = fn(text, pace)
            if data:
                log(step="falar", provider=name, model=model, ok=True, chars=len(text),
                    latency_ms=int((time.time() - t0) * 1000))
                return data, mime, name
        except Exception as e:
            print(f"[voz] {name} falhou ao falar: {e}", flush=True)
            errors.append(f"{name}: {e}")
            log(step="falar", provider=name, model=model, ok=False, chars=len(text), error=str(e)[:500])
    raise RuntimeError("Nenhum serviço conseguiu gerar a voz. " + " | ".join(errors))
