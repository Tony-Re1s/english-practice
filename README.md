# 🗣️ English Practice

Parceira de conversação em inglês (nível B1) com voz, correções curtas a cada fala e resumo no fim da sessão.

## O que tem
- **4 cenários**: Dia a dia, Trabalho, Intercâmbio/viagem e Conversa livre (você escolhe o assunto). 15 situações prontas de role-play.
- **Voz nos dois sentidos**: você grava a resposta, ela responde falando. Botão **🐢 Ouvir devagar**.
- **Treino de escuta**: desligue "Mostrar texto das respostas" e o texto só aparece se você abrir.
- **✏️ Dica a cada fala**: versão mais natural da sua frase + explicação curta em português.
- **🆘 Ideias de resposta**: duas frases simples para quando travar.
- **🏁 Resumo**: erros recorrentes, frases para levar, vocabulário novo e foco da próxima sessão. Download em `.md`.

## Estrutura
```
app.py               # interface Streamlit
config.py            # modelos, voz, velocidade, nível — mude aqui
prompts.py           # cenários, situações e prompts do tutor
services/llm.py      # Claude (conversa, correções, resumo)
services/voice.py    # OpenAI Whisper (ouvir) + TTS (falar); gTTS como reserva
```

## Chaves de API
| Chave | Para quê | Obrigatória? |
|---|---|---|
| `ANTHROPIC_API_KEY` | Conversa e correções (console.anthropic.com) | Sim |
| `OPENAI_API_KEY` | Microfone e voz natural (platform.openai.com) | Não: sem ela, só texto digitado + voz gTTS |
| `APP_PASSWORD` | Senha do app publicado, para ninguém usar suas chaves | Recomendado |

As duas APIs cobram por uso. Configure um limite de gasto mensal em cada painel.

## Publicar (sem instalar nada no Mac)
1. Crie um repositório no GitHub (pode ser privado) e suba todos os arquivos desta pasta — **menos** um eventual `.streamlit/secrets.toml`.
2. Em **share.streamlit.io** → *Create app* → escolha o repositório, branch `main`, arquivo `app.py`.
3. Em *Advanced settings → Secrets*, cole o conteúdo de `.streamlit/secrets.toml.example` com suas chaves reais.
4. *Deploy*. No celular, abra o link e permita o microfone.

## Ajustes rápidos (config.py)
- Mais qualidade na conversa: `CHAT_MODEL = "claude-sonnet-5-5"`.
- Outra voz: `TTS_VOICE` (alloy, echo, fable, onyx, nova, shimmer).
- Velocidade do "ouvir devagar": `TTS_SPEED_SLOW`.
- Nova situação: adicione uma linha em `SCENARIOS` no `prompts.py`.
