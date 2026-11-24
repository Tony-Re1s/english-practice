"""Conversa com o Claude (Anthropic API)."""

import anthropic
import streamlit as st

from config import CHAT_MAX_TOKENS, CHAT_MODEL, SUMMARY_MAX_TOKENS, SUMMARY_MODEL
from prompts import RESPOND_TOOL, SUMMARY_SYSTEM


@st.cache_resource
def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])


def tutor_turn(system: str, messages: list[dict]) -> dict:
    """Retorna {'reply': str, 'correction': dict|None, 'suggestions': list[str]}."""
    resp = _client().messages.create(
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
            return data
    raise RuntimeError("O modelo não devolveu uma resposta válida.")


def session_summary(transcript: str, corrections: list[dict]) -> str:
    corr_txt = "\n".join(
        f"- Aluno: {c['original']} → Melhor: {c['better']} ({c['tip_pt']})" for c in corrections
    ) or "(nenhuma correção durante a sessão)"
    user_msg = f"TRANSCRIÇÃO:\n{transcript}\n\nCORREÇÕES FEITAS NA HORA:\n{corr_txt}"
    resp = _client().messages.create(
        model=SUMMARY_MODEL,
        max_tokens=SUMMARY_MAX_TOKENS,
        system=SUMMARY_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()
