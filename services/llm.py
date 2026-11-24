"""Conversa com o Claude (Anthropic API)."""

import anthropic
import streamlit as st

from config import CHAT_MAX_TOKENS, CHAT_MODEL, SUMMARY_MAX_TOKENS, SUMMARY_MODEL
from prompts import RESPOND_TOOL, SUMMARY_SYSTEM


@st.cache_resource(max_entries=20)
def _client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key)


def _need(api_key: str | None) -> str:
    if not api_key:
        raise RuntimeError("Sem chave da Anthropic liberada para esta conta. Fale com o administrador do app.")
    return api_key


def _usage(resp, model: str) -> dict:
    u = getattr(resp, "usage", None)
    return {"model": model, "input_tokens": getattr(u, "input_tokens", 0) or 0,
            "output_tokens": getattr(u, "output_tokens", 0) or 0}


def tutor_turn(system: str, messages: list[dict], api_key: str | None) -> dict:
    """Retorna {'reply', 'correction'|None, 'suggestions', 'end_session', '_usage'}."""
    resp = _client(_need(api_key)).messages.create(
        model=CHAT_MODEL,
        max_tokens=CHAT_MAX_TOKENS,
        system=system,
        messages=messages,
        tools=[RESPOND_TOOL],
        tool_choice={"type": "tool", "name": "respond"},
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "respond":
            data = dict(block.input)
            data.setdefault("correction", None)
            data["suggestions"] = list(data.get("suggestions") or [])[:3]
            data["end_session"] = bool(data.get("end_session"))
            data["_usage"] = _usage(resp, CHAT_MODEL)
            return data
    raise RuntimeError("O modelo não devolveu uma resposta válida.")


def session_summary(transcript: str, corrections: list[dict], cefr: str, api_key: str | None) -> tuple[str, dict]:
    corr_txt = "\n".join(
        f"- Aluno: {c['original']} → Melhor: {c['better']} ({c['tip_pt']})" for c in corrections
    ) or "(nenhuma correção durante a sessão)"
    user_msg = f"TRANSCRIÇÃO:\n{transcript}\n\nCORREÇÕES FEITAS NA HORA:\n{corr_txt}"
    resp = _client(_need(api_key)).messages.create(
        model=SUMMARY_MODEL,
        max_tokens=SUMMARY_MAX_TOKENS,
        system=SUMMARY_SYSTEM.format(cefr=cefr),
        messages=[{"role": "user", "content": user_msg}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    return text, _usage(resp, SUMMARY_MODEL)
