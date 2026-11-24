"""Configuração central do app. Mude aqui modelos, vozes e limites."""

# --- Modelos -----------------------------------------------------------------
# Claude conduz a conversa e gera as correções.
CHAT_MODEL = "claude-haiku-5-5"        # rápido e barato; troque por "claude-sonnet-5-5" se quiser mais qualidade
SUMMARY_MODEL = "claude-sonnet-5-5"    # usado só 1x por sessão, no resumo final
CHAT_MAX_TOKENS = 700
SUMMARY_MAX_TOKENS = 1500

# --- Voz (ordem de tentativa em services/voice.py: grátis primeiro) -----------
# Ouvir sua fala
GROQ_STT_MODEL = "whisper-large-v3-turbo"      # grátis (precisa GROQ_API_KEY)
GEMINI_STT_MODEL = "gemini-3.8-flash"          # precisa GEMINI_API_KEY
OPENAI_STT_MODEL = "gpt-4o-mini-transcribe"    # pago; a OpenAI desliga em 26/02/2027 → trocar por "gpt-transcribe"

# Falar as respostas
EDGE_VOICE = "en-US-AvaNeural"                 # grátis, sem chave (vozes neurais da Microsoft)
EDGE_RATES = {"slow": "-25%", "calm": "-12%", "normal": "+0%", "brisk": "+6%"}   # "slow" = botão ouvir devagar
GEMINI_TTS_MODEL = "gemini-3.8-flash-lite-tts"
GEMINI_VOICE = "Kore"
OPENAI_TTS_MODEL = "gpt-4o-mini-tts"
OPENAI_TTS_VOICE = "nova"

# --- Níveis ------------------------------------------------------------------
# pace = ritmo padrão da voz nesse nível (o botão "ouvir devagar" sempre usa "slow")
LEVELS = {
    "basico": {
        "label": "🌱 Básico", "cefr": "A2", "pace": "calm",
        "guide": "Use very simple, common words and short sentences (max ~20 words per reply). "
                 "Ask one simple question at a time, often yes/no or either/or. Speak about concrete, everyday things. "
                 "Correct only mistakes that change the meaning or are very basic.",
    },
    "intermediario": {
        "label": "🌿 Intermediário", "cefr": "B1", "pace": "normal",
        "guide": "Use natural everyday English at B1 level, 1-3 sentences (max ~40 words). Avoid rare idioms. "
                 "Ask open questions that make the learner explain and give reasons. "
                 "Correct grammar and unnatural word choices.",
    },
    "avancado": {
        "label": "🌳 Avançado", "cefr": "B2-C1", "pace": "brisk",
        "guide": "Talk like a native speaker at natural speed: phrasal verbs, common idioms, nuanced vocabulary, "
                 "up to ~60 words per reply. Challenge the learner: ask for opinions, examples and counter-arguments. "
                 "Correct also subtle naturalness issues (collocations, register, word choice).",
    },
}
DEFAULT_LEVEL = "intermediario"

# --- Custos estimados (US$) — conferidos em 24/11/2026; ajuste se os preços mudarem -------
PRICES = {
    # Claude: US$ por 1 milhão de tokens (entrada, saída)
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    # OpenAI voz
    "gpt-4o-mini-transcribe_per_min": 0.003,
    "gpt-4o-mini-tts_per_min": 0.015,   # estimativa: ~US$ 0,015 por minuto de fala gerada
}
FREE_PROVIDERS = {"Groq", "Edge", "gTTS", "Gemini"}   # Gemini: plano gratuito do AI Studio

# --- Aluno -------------------------------------------------------------------
LEARNER_PROFILE = (
    "Brazilian adult, native Portuguese speaker, works in corporate treasury and data "
    "analytics. Reads well; main difficulty is building sentences when speaking, and "
    "some difficulty understanding spoken English."
)

# --- Limites -----------------------------------------------------------------
MAX_HISTORY_TURNS = 30   # quantas falas anteriores vão para o modelo (controla custo)
