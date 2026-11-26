"""Teste de pronúncia: compara a frase-alvo com o que o reconhecimento de voz ouviu, palavra por palavra.

O reconhecimento de voz erra às vezes (sotaque, microfone, barulho), então a nota é generosa:
  ok   = a palavra chegou igual
  near = chegou parecida (1-2 letras diferentes, ou soa igual: there/their, to/two...)
  miss = não chegou
A pessoa ainda pode marcar "Eu falei certo" numa palavra, e ela conta como ok.
"""
import difflib
import re

SOUND_ALIKE = [{"there", "their", "they're"}, {"to", "too", "two"}, {"your", "you're"}, {"its", "it's"},
               {"for", "four"}, {"hear", "here"}, {"right", "write"}, {"know", "no"}, {"by", "buy", "bye"},
               {"weather", "whether"}, {"one", "won"}, {"i", "eye"}, {"see", "sea"}, {"meet", "meat"}]


ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen " \
       "seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def _num(n: int) -> list[str]:
    if n < 20:
        return [ONES[n]]
    if n < 100:
        return [TENS[n // 10]] + ([ONES[n % 10]] if n % 10 else [])
    if n < 1000:
        return [ONES[n // 100], "hundred"] + (_num(n % 100) if n % 100 else [])
    return [str(n)]


def words(s: str) -> list[str]:
    s = (s or "").lower().replace("’", "'").replace("-", " ")
    out = []
    for w in re.findall(r"[a-z0-9']+", s):
        out += _num(int(w)) if w.isdigit() and len(w) <= 3 else [w]
    return out


def _dist(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _alike(a: str, b: str) -> bool:
    return any(a in g and b in g for g in SOUND_ALIKE)


def score(target: str, heard: str) -> dict:
    """{'words': [{'w','status'}], 'pct': 0-100} na ordem da frase-alvo."""
    tw, hw = words(target), words(heard)
    out = [{"w": w, "status": "miss"} for w in tw]
    sm = difflib.SequenceMatcher(a=tw, b=hw, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i1, i2):
                out[k]["status"] = "ok"
        elif tag == "replace":
            for k in range(i1, i2):
                cands = hw[j1:j2]
                if any(_alike(tw[k], c) for c in cands):
                    out[k]["status"] = "ok"
                elif any(_dist(tw[k], c) <= (1 if len(tw[k]) <= 4 else 2) for c in cands):
                    out[k]["status"] = "near"
    pts = sum(1 if o["status"] == "ok" else .6 if o["status"] == "near" else 0 for o in out)
    return {"words": out, "pct": round(100 * pts / max(1, len(out)))}


def cheer(pct: int, kids: bool = False) -> str:
    if pct >= 90:
        return "Perfect! You sound great! 🌟" if kids else "🌟 Excelente! Saiu muito claro."
    if pct >= 70:
        return "Great job! Almost there! 💪" if kids else "👏 Muito bom! Só um ou outro ajuste."
    if pct >= 40:
        return "Good try! Let's do it again! 🚀" if kids else "🙂 Boa! Ouça as palavras em amarelo/vermelho e tente de novo."
    return "Let's listen and try again! 🎧" if kids else ("🎧 Vamos de novo: ouça a frase devagar e repita junto. "
                                                          "O microfone às vezes não pega bem — tente mais perto.")
