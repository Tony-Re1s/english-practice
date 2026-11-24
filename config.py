"""Configuração central do app. Mude aqui modelos, vozes e limites."""

# --- Modelos -----------------------------------------------------------------
# Claude conduz a conversa e gera as correções.
CHAT_MODEL = "claude-haiku-5-5"        # rápido e barato; troque por "claude-sonnet-5-5" se quiser mais qualidade
SUMMARY_MODEL = "claude-sonnet-5-5"    # usado só 1x por sessão, no resumo final
CHAT_MAX_TOKENS = 700
SUMMARY_MAX_TOKENS = 1500

# OpenAI faz a parte de voz (ouvir e falar).
STT_MODEL = "whisper-1"                # transcrição da sua fala
TTS_MODEL = "tts-1"                    # voz da parceira de conversa
TTS_VOICE = "nova"                     # opções: alloy, echo, fable, onyx, nova, shimmer
TTS_SPEED_NORMAL = 1.0
TTS_SPEED_SLOW = 0.8                   # botão "ouvir devagar"

# --- Aluno -------------------------------------------------------------------
LEARNER_LEVEL = "B1"
LEARNER_PROFILE = (
    "Brazilian adult, native Portuguese speaker, works in corporate treasury and data "
    "analytics. Reads well; main difficulty is building sentences when speaking, and "
    "some difficulty understanding spoken English."
)

# --- Limites -----------------------------------------------------------------
MAX_HISTORY_TURNS = 30   # quantas falas anteriores vão para o modelo (controla custo)
