"""Tradutor, exercícios de gramática e perguntas sobre vídeos.

- Claude Haiku (barato) cria exercícios, traduz, faz perguntas e corrige.
- Gemini Flash (grátis) assiste o vídeo do YouTube UMA vez e o resumo fica salvo no banco.
"""

import json
import re
import unicodedata

from config import CHAT_MODEL, GEMINI_STT_MODEL
from services.llm import _client, _need, _usage


def _tool_call(system: str, user: str, tool: dict, api_key: str | None, max_tokens: int = 1800) -> tuple[dict, dict]:
    resp = _client(_need(api_key)).messages.create(
        model=CHAT_MODEL, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}],
        tools=[tool], tool_choice={"type": "tool", "name": tool["name"]},
    )
    for b in resp.content:
        if b.type == "tool_use":
            return dict(b.input), _usage(resp, CHAT_MODEL)
    raise RuntimeError("O modelo não devolveu uma resposta válida.")


# --- Tradutor -------------------------------------------------------------------------
TRANSLATE_TOOL = {
    "name": "translate",
    "description": "Translate between English and Brazilian Portuguese and explain the meaning.",
    "input_schema": {
        "type": "object",
        "properties": {
            "source_lang": {"type": "string", "enum": ["en", "pt"]},
            "translation": {"type": "string", "description": "Best natural translation into the other language."},
            "english": {"type": "string", "description": "The English version (original or translation), for pronunciation."},
            "meaning_pt": {"type": "string", "description": "Short explanation of the meaning in Brazilian Portuguese."},
            "alternatives": {"type": "array", "items": {"type": "string"}, "description": "Up to 3 other common translations."},
            "examples": {
                "type": "array",
                "items": {"type": "object", "properties": {"en": {"type": "string"}, "pt": {"type": "string"}},
                          "required": ["en", "pt"]},
                "description": "2 short example sentences in English with Portuguese translation.",
            },
            "tip_pt": {"type": "string", "description": "Optional short usage tip in Portuguese (formal/informal, false friend...)."},
        },
        "required": ["source_lang", "translation", "english", "meaning_pt", "examples"],
    },
}


def translate(text: str, api_key: str | None) -> tuple[dict, dict]:
    system = ("You are a friendly bilingual dictionary for a Brazilian learner of English. Detect whether the input is "
              "English or Portuguese and translate it into the other language. If it is a single word or expression, "
              "explain its meaning and how it is used. Keep everything short and clear.")
    return _tool_call(system, text.strip(), TRANSLATE_TOOL, api_key, max_tokens=900)


# --- Exercícios de gramática -------------------------------------------------------------
EXERCISE_TOOL = {
    "name": "exercise",
    "description": "A short grammar exercise.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short title in Portuguese."},
            "explanation_pt": {"type": "string", "description": "Clear explanation of the grammar point in Brazilian Portuguese, 2-5 short sentences."},
            "examples": {"type": "array", "items": {"type": "string"}, "description": "2-3 example sentences in English."},
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["mc", "fill"]},
                        "prompt": {"type": "string", "description": "The question. For 'fill', use ___ for the gap."},
                        "options": {"type": "array", "items": {"type": "string"}, "description": "For 'mc': 3 or 4 options."},
                        "answer": {"type": "string", "description": "Correct option text (mc) or the word(s) for the gap (fill)."},
                        "accept": {"type": "array", "items": {"type": "string"}, "description": "Other accepted answers (fill), e.g. contractions."},
                        "explain_pt": {"type": "string", "description": "One short sentence in Portuguese explaining the answer."},
                    },
                    "required": ["type", "prompt", "answer", "explain_pt"],
                },
                "description": "Exactly 6 questions, mixing mc and fill.",
            },
        },
        "required": ["title", "explanation_pt", "examples", "questions"],
    },
}


def make_exercise(level_guide: str, cefr: str, topic: str, rnd: int, api_key: str | None) -> tuple[dict, dict]:
    system = ("You are an experienced English teacher writing original grammar exercises for Brazilian learners. "
              "Write everything from scratch (never copy textbooks). Vocabulary and sentences must match the level. "
              f"Level {cefr}. Level guidance: {level_guide}")
    user = (f"Grammar point: {topic}.\n"
            + (f"This is review round {rnd}: use completely new sentences and situations.\n" if rnd > 1 else "")
            + "Create the exercise with exactly 6 questions (mix 'mc' and 'fill'). For 'fill', the gap answer must be "
              "short and unambiguous. Each question must have only one correct answer.")
    data, usage = _tool_call(system, user, EXERCISE_TOOL, api_key)
    data["questions"] = [q for q in data.get("questions", []) if q.get("prompt") and q.get("answer")][:8]
    return data, usage


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s or "")).strip().lower()
    s = s.replace("’", "'").replace("‘", "'")
    s = re.sub(r"[.!?,;:\"]", "", s)
    return re.sub(r"\s+", " ", s)


def check_answer(q: dict, given: str | None) -> bool:
    if given is None:
        return False
    ok = {_norm(q.get("answer"))} | {_norm(a) for a in (q.get("accept") or [])}
    return _norm(given) in ok


# --- Vídeos -------------------------------------------------------------------------------
def youtube_id(url: str) -> str | None:
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([A-Za-z0-9_-]{11})", url or "")
    return m.group(1) if m else None


def video_summary(url: str, gemini_key: str) -> tuple[str, dict]:
    """O Gemini assiste o vídeo uma vez (plano grátis) e devolve resumo + vocabulário em JSON."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=gemini_key)
    prompt = ("Watch this English-learning video. Return JSON with: "
              '"title" (short), "summary" (6-10 sentences in simple English describing what happens and what people say), '
              '"key_lines" (up to 8 short quotes or close paraphrases of important lines), '
              '"vocab" (up to 10 items: {"en": word or expression, "pt": Brazilian Portuguese meaning}), '
              '"level_hint" (A1/A2/B1/B2). Return only the JSON.')
    r = client.models.generate_content(
        model=GEMINI_STT_MODEL,
        contents=[types.Part(file_data=types.FileData(file_uri=url)), prompt],
        config={"response_mime_type": "application/json"},
    )
    text = (r.text or "").strip()
    data = json.loads(text[text.find("{"): text.rfind("}") + 1])
    return json.dumps(data, ensure_ascii=False), {"model": GEMINI_STT_MODEL}


QUESTIONS_TOOL = {
    "name": "questions",
    "description": "Listening comprehension questions about a video.",
    "input_schema": {
        "type": "object",
        "properties": {"questions": {"type": "array", "items": {"type": "string"}, "description": "5 short questions in English."}},
        "required": ["questions"],
    },
}


def video_questions(video_json: str, cefr: str, api_key: str | None, avoid: list[str] | None = None) -> tuple[list[str], dict]:
    system = (f"You write listening comprehension questions for a {cefr} learner who just watched a video. "
              "Use simple English at that level. Ask about facts, details and the meaning of key expressions; "
              "include one personal opinion question at the end.")
    user = f"VIDEO NOTES (JSON):\n{video_json}\n\nWrite 5 NEW questions."
    if avoid:
        user += "\nDo not repeat these questions:\n- " + "\n- ".join(avoid[-15:])
    data, usage = _tool_call(system, user, QUESTIONS_TOOL, api_key, max_tokens=600)
    return [q for q in data.get("questions", []) if q][:6], usage


GRADE_TOOL = {
    "name": "grade",
    "description": "Feedback on the learner's answers.",
    "input_schema": {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "correct": {"type": "boolean"},
                        "comment_pt": {"type": "string", "description": "Short feedback in Brazilian Portuguese."},
                        "better": {"type": "string", "description": "A good model answer in English (natural, at the learner's level)."},
                    },
                    "required": ["correct", "comment_pt", "better"],
                },
            },
            "overall_pt": {"type": "string", "description": "1-2 sentences of encouraging overall feedback in Portuguese."},
        },
        "required": ["results", "overall_pt"],
    },
}


def grade_answers(video_json: str, questions: list[str], answers: list[str], cefr: str,
                  api_key: str | None) -> tuple[dict, dict]:
    system = (f"You are a kind English teacher checking a {cefr} learner's answers about a video they watched. "
              "Judge whether each answer shows understanding (content), even with small grammar mistakes. "
              "Opinion questions are correct if they are understandable answers. Be encouraging.")
    qa = "\n".join(f"{i + 1}. Q: {q}\n   A: {a or '(no answer)'}" for i, (q, a) in enumerate(zip(questions, answers)))
    return _tool_call(system, f"VIDEO NOTES (JSON):\n{video_json}\n\nANSWERS:\n{qa}", GRADE_TOOL, api_key, max_tokens=1200)
