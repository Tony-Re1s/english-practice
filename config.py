"""Configuração central do app. Mude aqui modelos, vozes e limites."""

# --- Modelos -----------------------------------------------------------------
# Claude conduz a conversa e gera as correções.
CHAT_MODEL = "claude-haiku-5-5"        # rápido e barato; troque por "claude-sonnet-5-5" se quiser mais qualidade
SUMMARY_MODEL = "claude-sonnet-5-5"    # usado só 1x por sessão, no resumo final
CHAT_MAX_TOKENS = 700
SUMMARY_MAX_TOKENS = 1500

# --- Voz (ordem de tentativa em services/voice.py: grátis primeiro) -----------
# Ouvir sua fala
GROQ_STT_MODEL = "whisper-large-v3"            # grátis (precisa GROQ_API_KEY); o modelo completo erra menos com sotaque que o "turbo"
GEMINI_STT_MODEL = "gemini-3.8-flash"          # precisa GEMINI_API_KEY
OPENAI_STT_MODEL = "gpt-4o-mini-transcribe"    # pago; a OpenAI desliga em 26/02/2027 → trocar por "gpt-transcribe"

# Falar as respostas
EDGE_VOICE = "en-US-AvaNeural"                 # grátis, sem chave (vozes neurais da Microsoft)
KID_EDGE_VOICE = "en-US-AnaNeural"             # voz infantil (criança), dicção bem clara — modo Criança
KID_PITCH = "+6Hz"                             # um pouco mais agudo, jeito de robozinho simpático
KID_STYLE = ("Speak like Bip, a cheerful little robot friend for young children: bright, warm and playful, "
             "with very clear diction and short pauses between phrases.")
EDGE_RATES = {"slow": "-25%", "calm": "-12%", "normal": "+0%", "brisk": "+6%"}   # "slow" = botão ouvir devagar
GEMINI_TTS_MODEL = "gemini-3.8-flash-lite-tts"
GEMINI_VOICE = "Kore"
OPENAI_TTS_MODEL = "gpt-4o-mini-tts"
OPENAI_TTS_VOICE = "nova"

# --- Níveis ------------------------------------------------------------------
# pace = ritmo padrão da voz (o botão "voz devagar" sempre usa "slow")
LEVELS = {
    "crianca": {
        "label": "🧒 Criança (7-8 anos)", "cefr": "Pre-A1 (kids)", "pace": "slow", "kids": True,
        "guide": "You are talking with a 7-8 year old child who is starting to learn English. Use only very common, "
                 "concrete words (animals, colors, food, toys, school, family). Max 10 words per reply, very short "
                 "sentences, present tense. Be playful, warm and encouraging (\"Great job!\", \"Wow!\"). "
                 "Ask one tiny question at a time, often with two options (\"Do you like cats or dogs?\"). "
                 "Corrections only for very simple, important mistakes.",
    },
    "iniciante": {
        "label": "🍼 Iniciante (A1)", "cefr": "A1", "pace": "slow",
        "guide": "The learner is a beginner. Use only very common words and very short sentences (max ~12 words per "
                 "reply), mostly present simple. Ask one simple question at a time, often yes/no or with two options. "
                 "Speak about concrete everyday things. Correct only mistakes that change the meaning.",
    },
    "basico": {
        "label": "🌱 Básico (A2)", "cefr": "A2", "pace": "calm",
        "guide": "Use simple, common words and short sentences (max ~18 words per reply). Present, past and future "
                 "with 'going to'; no idioms. Ask one clear question at a time. "
                 "Correct basic grammar and wrong words.",
    },
    "intermediario": {
        "label": "🌿 Intermediário (B1)", "cefr": "B1", "pace": "normal",
        "guide": "Use clear everyday English, 1-2 short sentences (max ~30 words). Prefer common words; if you use a "
                 "less common word or phrasal verb, keep the sentence simple around it. Ask open questions that make "
                 "the learner explain and give reasons. Correct grammar and unnatural word choices.",
    },
    "avancado": {
        "label": "🌳 Avançado (B2+)", "cefr": "B2", "pace": "brisk",
        "guide": "Talk like a native speaker at natural speed: phrasal verbs, common idioms, up to ~50 words per "
                 "reply. Ask for opinions, examples and counter-arguments. "
                 "Correct also subtle naturalness issues (collocations, register, word choice).",
    },
}
DEFAULT_LEVEL = "basico"

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

# --- Modo ao vivo (Gemini Live, só plano grátis — nunca usa OpenAI) -----------------
LIVE_MODEL = "gemini-3.8-live"
LIVE_DAILY_MINUTES = 10        # padrão por pessoa (o admin ajusta por usuário)
LIVE_MAX_SESSION_MIN = 14      # sessões só de áudio têm limite de ~15 min no Gemini
LIVE_RESET_HOUR_BRT = 5        # a cota grátis do Google renova à meia-noite do Pacífico (~5h em Brasília)

# --- Usuários -----------------------------------------------------------------
PROVIDERS = ["anthropic", "groq", "gemini", "openai"]
PROVIDER_LABEL = {"anthropic": "Anthropic (Claude)", "groq": "Groq", "gemini": "Gemini", "openai": "OpenAI"}
SECRET_NAME = {"anthropic": "ANTHROPIC_API_KEY", "groq": "GROQ_API_KEY",
               "gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}
DEFAULT_DAILY_TURNS = 60       # limite de falas por dia para usuários convidados (admin ajusta)
