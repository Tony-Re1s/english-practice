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


SENTENCE_TOOL = {
    "name": "sentence_check",
    "description": "Feedback on a sentence a Brazilian learner wrote in English, in layers, without being picky.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["perfect", "clear", "awkward", "unclear"],
                        "description": "perfect = correct and natural; clear = understood, small grammar/style issues; "
                                       "awkward = understood but sounds strange or translated from Portuguese; "
                                       "unclear = a native would misunderstand or the meaning changes."},
            "understanding_pt": {"type": "string", "description": "In Portuguese, 1-2 sentences: would a native understand, and WHAT they would understand."},
            "grammar_ok": {"type": "boolean"},
            "grammar_pt": {"type": "string", "description": "In Portuguese: the grammar issue(s) explained simply, or 'Está correta.' Never call style choices errors."},
            "corrected": {"type": "string", "description": "Minimal correction: change as little as possible (same as input if already correct)."},
            "literal_pt": {"type": "string", "description": "What the learner's sentence literally says, translated word-for-word into Portuguese, so they see any hidden meaning."},
            "natural": {"type": "array", "items": {"type": "object", "properties": {
                "text": {"type": "string"}, "register": {"type": "string", "enum": ["informal", "neutro", "formal"]},
                "note_pt": {"type": "string", "description": "Very short note in Portuguese on when to use it."}},
                "required": ["text", "register", "note_pt"]},
                "description": "2-3 natural ways a native would say the same idea."},
            "words": {"type": "array", "items": {"type": "object", "properties": {
                "word": {"type": "string"}, "say_like": {"type": "string", "description": "Pronunciation with Portuguese sounds, stressed syllable in CAPS, e.g. 'KLAI-ent'."},
                "tip_pt": {"type": "string", "description": "Short pronunciation tip in Portuguese (optional)."}},
                "required": ["word", "say_like"]},
                "description": "The 3-6 words of the corrected sentence that Brazilians most often mispronounce."},
        },
        "required": ["verdict", "understanding_pt", "grammar_ok", "grammar_pt", "corrected", "literal_pt", "natural", "words"],
    },
}


def check_sentence(text: str, level_label: str, api_key: str | None) -> tuple[dict, dict]:
    """Analisa a frase em camadas: entendimento, gramática, literal e jeitos mais naturais (sem ser 'ao pé da letra')."""
    system = ("You are a kind, experienced English teacher for Brazilian adults. The learner wrote a sentence in English "
              "and wants honest feedback in layers. Priority: communication. If a native would understand it, say so "
              "clearly and never treat it as a failure. Separate real grammar errors from style or naturalness. Keep the "
              "minimal correction minimal. Explanations in simple Brazilian Portuguese, short. "
              f"Learner level: {level_label}. If the input is in Portuguese, treat it as what they want to say and give "
              "the English in 'corrected' and 'natural', with verdict 'clear'.")
    return _tool_call(system, text.strip(), SENTENCE_TOOL, api_key, max_tokens=1400)


KIDS_TRANSLATE_TOOL = {
    "name": "kids_word",
    "description": "A word or tiny phrase translated for a Brazilian child aged 7-8.",
    "input_schema": {
        "type": "object",
        "properties": {
            "english": {"type": "string", "description": "The English word or tiny phrase (simple, the most common way a child says it)."},
            "portuguese": {"type": "string", "description": "The Portuguese meaning."},
            "emoji": {"type": "string", "description": "1-3 emojis that show the meaning."},
            "say_like": {"type": "string", "description": "How to pronounce the English, written with Portuguese sounds, syllables separated by '-', stressed syllable in CAPS (e.g. 'DÓ-gui')."},
            "example_en": {"type": "string", "description": "A tiny, happy example sentence in English (max 6 words)."},
            "example_pt": {"type": "string", "description": "The example in Portuguese."},
        },
        "required": ["english", "portuguese", "emoji", "say_like", "example_en", "example_pt"],
    },
}


def translate_kids(text: str, api_key: str | None) -> tuple[dict, dict]:
    system = ("You help a Brazilian child aged 7-8 learn English words. The child types or says a word or tiny phrase, "
              "usually in Portuguese (sometimes in English). Give the simple, child-friendly English (or Portuguese) "
              "version. Never explain grammar. Keep it short, warm and safe for children; if the request is not "
              "appropriate for a child, answer with a friendly neutral word instead.")
    return _tool_call(system, text.strip(), KIDS_TRANSLATE_TOOL, api_key, max_tokens=400)


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
                        "instruction_pt": {"type": "string", "description": "Exactly what to do, in Brazilian Portuguese, "
                                           "short (e.g. 'Escreva o passado de GO (1 palavra).' or 'Escolha a frase correta.')."},
                        "prompt": {"type": "string", "description": "The question. For 'fill': ONE sentence with exactly ONE "
                                   "gap written ___ (never two gaps); put the base word in brackets when needed, e.g. "
                                   "'She ___ (go) to bed early.'"},
                        "options": {"type": "array", "items": {"type": "string"}, "description": "For 'mc': 3 or 4 options."},
                        "answer": {"type": "string", "description": "Correct option text (mc) or the word(s) for the gap (fill)."},
                        "accept": {"type": "array", "items": {"type": "string"}, "description": "ALL other correct answers for the gap (fill): contractions and full forms (didn't / did not), British/American spellings."},
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
              "short and unambiguous. Each question must have exactly ONE correct answer: in 'mc', every wrong "
              "option must contain a clear grammar error (never two acceptable options that differ only in extra "
              "words). Rules for 'fill': exactly ONE gap ___ per sentence; the answer is ONLY what goes in that gap "
              "(1-3 words); instruction_pt says exactly what to type and how many words; list every other correct "
              "form in 'accept'. Never write instructions like 'write the missing word for the gap in ...' that "
              "point to another sentence. Before answering, check each question yourself.")
    data, usage = _tool_call(system, user, EXERCISE_TOOL, api_key)
    data["questions"] = [q for q in data.get("questions", []) if q.get("prompt") and q.get("answer")][:8]
    return data, usage


KIDS_EXERCISE_TOOL = {
    "name": "kids_exercise",
    "description": "A short English mission for a Brazilian child aged 7-8 who is starting English.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Fun short title in Portuguese, with the English words in parentheses."},
            "explanation_pt": {"type": "string", "description": "2-4 very short, friendly sentences in Brazilian Portuguese a 7-year-old understands."},
            "examples": {"type": "array", "items": {"type": "string"}, "description": "3 very short English sentences (2-6 words)."},
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["mc", "fill"]},
                        "instruction_pt": {"type": "string", "description": "What to do, in simple Portuguese (e.g. 'Toque na palavra que significa vermelho')."},
                        "instruction_en": {"type": "string", "description": "The same instruction in VERY simple English (e.g. 'Tap the red one!')."},
                        "say": {"type": "string", "description": "Short English text the robot reads aloud for this question (the word or sentence to hear)."},
                        "prompt": {"type": "string", "description": "Short English text shown on screen (a word or a 2-6 word sentence). For 'fill' use ___ for the gap. Can be empty if the instruction is enough."},
                        "options": {"type": "array", "items": {"type": "string"}, "description": "For 'mc': 3 short options (one or two words each), in English unless the instruction asks for Portuguese."},
                        "emojis": {"type": "array", "items": {"type": "string"}, "description": "For 'mc': one emoji per option, same order, that shows its meaning (e.g. 🍎 for apple). Use '' if none fits."},
                        "picture": {"type": "string", "description": "The picture shown BIG above the question: 1-4 emojis making a little scene (e.g. '🖊️', '📕', '👽🐸', '👦👋🚪'). REQUIRED whenever the child must look at something: 'look and choose', 'look and write', every yes/no question (the picture decides the answer) and any sentence about colours/objects that needs a picture to be answerable. Never put the answer as text in the picture."},
                        "answer": {"type": "string", "description": "Correct option text (mc) or the 1-2 words for the gap (fill)."},
                        "accept": {"type": "array", "items": {"type": "string"}, "description": "Other accepted answers (fill)."},
                        "hint_pt": {"type": "string", "description": "Portuguese translation/hint of the English on screen, WITHOUT giving the answer away."},
                        "explain_pt": {"type": "string", "description": "One short, encouraging sentence in Portuguese explaining the answer."},
                    },
                    "required": ["type", "instruction_pt", "instruction_en", "say", "answer", "hint_pt", "explain_pt"],
                },
                "description": "Exactly 6 questions: at least 4 'mc'; at most 2 'fill', whose answer is 1-2 words the child just saw.",
            },
        },
        "required": ["title", "explanation_pt", "examples", "questions"],
    },
}


# Cada missão ganha uma "historinha" diferente, para as perguntas não parecerem sempre iguais.
KIDS_STORIES = [
    "Bip the robot lands on the planet and meets a friendly alien who asks him questions.",
    "a treasure hunt: each question is a clue that opens a space chest.",
    "a space TV quiz show with a funny host and a big prize.",
    "Bip lost his things on the planet; the child helps him find them.",
    "a picnic on the planet with alien friends and their pets.",
    "a space school where the child is the teacher for one day.",
    "a race between two rockets; each right answer gives fuel.",
    "Bip is sick and only English words make him feel better.",
    "a space zoo with strange animals that understand only English.",
    "a birthday party for an alien, with games and presents.",
]
KIDS_MIXES = [
    "Start with 2 'listen and choose', then 1 'yes or no', 1 'missing word', 1 'look and write', end with 1 'listen and choose'.",
    "Start with 1 'yes or no', then 2 'missing word', 1 'listen and choose', 1 'look and write', end with 1 'yes or no'.",
    "Start with 1 'look and write', then 2 'listen and choose', 2 'yes or no', end with 1 'missing word'.",
    "Alternate: 'listen and choose', 'missing word', 'yes or no', 'listen and choose', 'look and write', 'missing word'.",
]


def needs_picture(q: dict) -> bool:
    """True se a pergunta pede para olhar uma figura (ou é sim/não) e veio sem figura: não dá para responder."""
    if q.get("picture"):
        return False
    ins = (q.get("instruction_pt") or "").lower()
    yes_no = {o.lower() for o in (q.get("options") or [])} == {"yes", "no"}
    looks = re.search(r"\b(olhe|veja a (figura|imagem)|figura|imagem|desenho)\b", ins)
    if q.get("type") == "fill" and (q.get("emojis") or [""])[0]:
        return False   # exercícios antigos: o emoji vira a figura
    return bool(looks or yes_no)


def make_kids_exercise(level_guide: str, topic: str, rnd: int, api_key: str | None, num: int = 0) -> tuple[dict, dict]:
    system = ("You are a warm primary-school English teacher creating original missions for Brazilian children aged 7-8 "
              "who are beginning English (Cambridge Pre A1 Starters). Listening comes before reading: every question "
              "has text for the robot to read aloud. Use only very common, concrete words and tiny sentences. "
              "Follow the Cambridge Starters task styles: 'Listen and choose' (the robot says a word, the child picks it), "
              "'Look and read: yes or no' (options 'yes'/'no' about an emoji or a tiny sentence), 'Read and choose the "
              "missing word' and 'Look and write the word' (fill, 1-2 letters/words already seen). Recycle words from "
              "the topic several times (repetition helps children remember). "
              f"Level guidance: {level_guide}")
    user = (f"Topic: {topic}.\n"
            + (f"This is review round {rnd}: use new words and situations.\n" if rnd > 1 else "")
            + (f"Mission story (use it in the questions and examples, it makes each mission feel new): "
               f"{KIDS_STORIES[num % len(KIDS_STORIES)]}\nQuestion order: {KIDS_MIXES[num % len(KIDS_MIXES)]}\n"
               if num else "")
            + "Create the mission with exactly 6 questions. Each question must have exactly ONE correct answer, and "
              "every wrong option must be clearly wrong. Prefer 'mc' with emojis that show the meaning. 'fill' answers "
              "must be one or two easy words already shown in the examples, with exactly ONE gap ___, and instruction_pt "
              "must say exactly what to write (e.g. 'Escreva a palavra que falta: 1 palavra'). List other correct "
              "spellings in 'accept'. Every question that needs looking (look and choose/write, yes or no, "
              "'The ___ is red.') MUST have 'picture'. For 'mc' never show the right answer in 'prompt'. "
              "Check each question yourself.")
    data, usage = _tool_call(system, user, KIDS_EXERCISE_TOOL, api_key, max_tokens=2200)
    data["questions"] = [q for q in data.get("questions", []) if q.get("answer") and not needs_picture(q)][:8]
    data["kids"] = True
    return data, usage


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s or "")).strip().lower()
    s = s.replace("’", "'").replace("‘", "'")
    s = re.sub(r"[.!?,;:\"]", "", s)
    return re.sub(r"\s+", " ", s)


def _dist(a: str, b: str) -> int:
    """Distância de edição (quantas letras trocar/tirar/pôr)."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


_HELPERS = {"did", "do", "does", "you", "i", "he", "she", "it", "we", "they", "the", "a", "an", "to", "not",
            "didn't", "don't", "doesn't", "is", "are", "was", "were", "am"}


def _words(s: str) -> list[str]:
    """Palavras sem as aspas das pontas ('did you' → did, you), mantendo contrações como didn't."""
    return [w.strip("'") for w in re.findall(r"[a-z0-9']+", _norm(s)) if w.strip("'")]


def check_answer(q: dict, given: str | None, lenient: bool = False) -> bool:
    """Corrige com bom senso: ignora maiúsculas, pontuação e apóstrofo diferente; aceita a resposta escrita dentro
    de uma frase (ex.: 'She went', 'did have') quando as outras palavras já estão na própria pergunta.
    lenient (modo infantil): aceita também um errinho de digitação em palavras de 4+ letras (ex.: 'bannana')."""
    if given is None:
        return False
    ok = {_norm(q.get("answer"))} | {_norm(a) for a in (q.get("accept") or [])}
    ok.discard("")
    g = _norm(given)
    if g in ok:
        return True
    if q.get("type") != "fill" or not g:
        return False
    gw = _words(given)
    context = set(_words(q.get("prompt", ""))) | _HELPERS
    for a in ok:
        aw = _words(a)
        if not aw:
            continue
        for i in range(len(gw) - len(aw) + 1):   # a resposta aparece inteira, e o resto veio da própria pergunta
            if gw[i:i + len(aw)] == aw and all(w in context for w in gw[:i] + gw[i + len(aw):]):
                return True
    if lenient:
        g2 = g.replace(" ", "")
        return any(len(a) >= 4 and _dist(g2, a.replace(" ", "")) <= 1 for a in ok)
    return False


def fill_hint(q: dict) -> str:
    """Orientação para perguntas de escrever: o que digitar e quantas palavras (vale para exercícios antigos também)."""
    if q.get("instruction_pt"):
        return q["instruction_pt"]
    n = max(1, len(_words(q.get("answer", ""))))
    return f"✍️ Escreva só o que vai na lacuna ({n} {'palavra' if n == 1 else 'palavras'})."


# --- Vídeos -------------------------------------------------------------------------------
def youtube_id(url: str) -> str | None:
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([A-Za-z0-9_-]{11})", url or "")
    return m.group(1) if m else None


def playlist_id(url: str) -> str | None:
    m = re.search(r"[?&]list=([A-Za-z0-9_-]{10,})", url or "")
    return m.group(1) if m else None


def _fetch(url: str) -> str:
    import urllib.request
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                      "Version/17.0 Safari/605.1.15",
        "Accept-Language": "en-US,en;q=0.9", "Cookie": "CONSENT=YES+1; SOCS=CAI"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def _walk(o, out: list) -> None:
    """Procura os itens de playlist (playlistVideoRenderer) dentro do JSON da página."""
    if isinstance(o, dict):
        r = o.get("playlistVideoRenderer")
        if isinstance(r, dict) and r.get("videoId"):
            t = r.get("title", {})
            title = t.get("simpleText") or "".join(x.get("text", "") for x in t.get("runs", []))
            out.append({"youtube_id": r["videoId"], "title": title.strip()})
            return
        for v in o.values():
            _walk(v, out)
    elif isinstance(o, list):
        for v in o:
            _walk(v, out)


def playlist_videos(url: str) -> tuple[list[dict], bool]:
    """Lista os vídeos de uma playlist pública do YouTube (até ~100), na ordem da playlist.

    Lê a página da playlist; se o YouTube não entregar, usa o feed RSS (só os 15 primeiros).
    Retorna (vídeos, completo) — completo=False quando veio pelo RSS e pode faltar vídeo."""
    pid = playlist_id(url)
    if not pid:
        raise ValueError("Não achei o código da playlist no link (precisa ter 'list=').")
    vids: list[dict] = []
    for page in (f"https://www.youtube.com/playlist?list={pid}&hl=en&ucbcb=1",
                 f"https://m.youtube.com/playlist?list={pid}&hl=en&ucbcb=1"):
        try:
            html = _fetch(page)
        except Exception:
            continue
        m = re.search(r"ytInitialData[\"']?\]?\s*=\s*(\{.+?\});\s*</script>", html, re.S)
        if m:
            try:
                _walk(json.loads(m.group(1)), vids)
            except Exception:
                pass
        if not vids:  # plano B na mesma página: procura os itens direto no texto
            for vid, body in re.findall(r'"playlistVideoRenderer":\{"videoId":"([\w-]{11})"(.{0,1500}?)"index"', html, re.S):
                t = re.search(r'"title":\{"runs":\[\{"text":"(.*?)"\}', body) or re.search(r'"simpleText":"(.*?)"', body)
                vids.append({"youtube_id": vid, "title": json.loads(f'"{t.group(1)}"') if t else vid})
        if vids:
            break
    complete = bool(vids)
    if not vids:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(_fetch(f"https://www.youtube.com/feeds/videos.xml?playlist_id={pid}"))
        ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
        for e in root.findall("a:entry", ns):
            vids.append({"youtube_id": e.findtext("yt:videoId", "", ns), "title": e.findtext("a:title", "", ns)})
    seen, uniq = set(), []
    for v in vids:
        if v["youtube_id"] and v["youtube_id"] not in seen and v["title"] not in ("[Private video]", "[Deleted video]"):
            seen.add(v["youtube_id"])
            uniq.append(v)
    return uniq, complete or len(uniq) < 15


# Numeração do American English File (AEF) -> nossos níveis
AEF_LEVEL = {"starter": "iniciante", "1": "iniciante", "2": "basico", "3": "intermediario", "4": "avancado", "5": "avancado"}


def level_from_title(title: str) -> str | None:
    m = re.search(r"\b(?:AEF|American English(?: File)?)\s*(starter|[1-5])", title or "", re.I)
    return AEF_LEVEL.get(m.group(1).lower()) if m else None


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


def video_questions(video_json: str, cefr: str, api_key: str | None, avoid: list[str] | None = None,
                    kids: bool = False) -> tuple[list[str], dict]:
    if kids:
        system = ("You write 4 super simple questions for a Brazilian child aged 7-8 who just watched an English "
                  "cartoon lesson. Write each question in simple Brazilian Portuguese, asking about English words "
                  "or short phrases from the video (e.g. 'Como se diz *gato* em inglês?', 'O que o menino falou "
                  "quando chegou? (Hello / Goodbye)'). Put the possible answers in parentheses when it helps. "
                  "One-word or very short answers only. Friendly, with an emoji in each question.")
    else:
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
                  api_key: str | None, kids: bool = False) -> tuple[dict, dict]:
    system = (f"You are a kind English teacher checking a {cefr} learner's answers about a video they watched. "
              "Judge whether each answer shows understanding (content), even with small grammar mistakes. "
              "Opinion questions are correct if they are understandable answers. Be encouraging.")
    if kids:
        system += (" The learner is a 7-8 year-old child: accept small spelling mistakes, answers in Portuguese when "
                   "the question allows it, and write all feedback in very simple, cheerful Brazilian Portuguese.")
    qa = "\n".join(f"{i + 1}. Q: {q}\n   A: {a or '(no answer)'}" for i, (q, a) in enumerate(zip(questions, answers)))
    return _tool_call(system, f"VIDEO NOTES (JSON):\n{video_json}\n\nANSWERS:\n{qa}", GRADE_TOOL, api_key, max_tokens=1200)
