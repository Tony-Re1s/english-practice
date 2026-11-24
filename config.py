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
EDGE_RATE_NORMAL = "+0%"
EDGE_RATE_SLOW = "-20%"                        # botão "ouvir devagar"
GEMINI_TTS_MODEL = "gemini-3.8-flash-lite-tts"
GEMINI_VOICE = "Kore"
OPENAI_TTS_MODEL = "gpt-4o-mini-tts"
OPENAI_TTS_VOICE = "nova"

# --- Aluno -------------------------------------------------------------------
LEARNER_LEVEL = "B1"
LEARNER_PROFILE = (
    "Brazilian adult, native Portuguese speaker, works in corporate treasury and data "
    "analytics. Reads well; main difficulty is building sentences when speaking, and "
    "some difficulty understanding spoken English."
)

# --- Limites -----------------------------------------------------------------
MAX_HISTORY_TURNS = 30   # quantas falas anteriores vão para o modelo (controla custo)
