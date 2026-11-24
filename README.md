# 🗣️ English Practice

Parceira de conversação em inglês (nível B1) com voz, correções curtas a cada fala e resumo no fim da sessão.

## O que tem
- **5 níveis**: 🧒 Criança (7-8 anos), 🍼 Iniciante (A1), 🌱 Básico (A2), 🌿 Intermediário (B1), 🌳 Avançado (B2+).
- **Correção falada**: quando você erra, ela confirma o que você quis dizer ("Do you mean: …?") e segue a conversa.
- **3 modos**: 🎧 mãos livres, 👆 apertar para falar e ⚡ ao vivo (Gemini Live grátis, com limite de minutos por dia; nunca usa a OpenAI).
- **👥 Usuários** (admin): liberar e-mails, travar o nível, limite de falas por dia, minutos ao vivo e, serviço por serviço, usar a chave do dono, uma chave própria (criptografada) ou desligar.
- **📚 Aprender** (separado da conversa):
  - **Gramática por nível**: trilha numerada seguindo a progressão do Quadro Europeu (A1→B2); cada exercício é criado pelo Claude na primeira vez e fica salvo, então o nº 5 é sempre o mesmo para o mesmo nível. Correção automática e registro do que cada pessoa concluiu.
  - **Vídeos** (ouvir e interpretar): o admin cola links públicos do YouTube por nível; o Gemini assiste cada vídeo uma única vez (plano grátis) e o resumo fica salvo; o Claude faz perguntas novas a cada vez, corrige e dá para conversar sobre o vídeo.
  - **Tradutor** EN↔PT por texto ou voz, com exemplos e pronúncia.
- **Cara de app**: navegação no rodapé, logo e ícone para a tela de início do iPhone/Mac.
- **5 cenários**: Dia a dia, Trabalho, Intercâmbio/viagem, 🧠 Assuntos (mercado financeiro, câmbio, tesouraria, tecnologia...) e Conversa livre.
- **📊 Uso e histórico**: cada IA usada (conversa, ouvir, falar), falhas e trocas de serviço, custo estimado, alerta se a OpenAI foi usada, e todas as conversas antigas com correções e resumo (precisa `DATABASE_URL`).
- **Encerrar**: botão ou diga *"let's stop here"* — desliga o microfone e mostra o resumo.
- **Conversa contínua (mãos livres)**: toque no microfone uma vez; ele para sozinho quando você termina de falar, toca a resposta e volta a ouvir. Toque de novo para pausar. Também há o modo **Apertar para falar**.
- **Voz nos dois sentidos** com botão **🐢 Ouvir devagar**.
- **Voz com reserva**: ouvir usa Groq → Gemini → OpenAI; falar usa Edge (grátis) → Gemini → OpenAI → gTTS. Só cai no pago se o grátis falhar.
- **Treino de escuta**: desligue "Mostrar texto das respostas" e o texto só aparece se você abrir.
- **✏️ Dica a cada fala**: versão mais natural da sua frase + explicação curta em português.
- **🆘 Ideias de resposta**: duas frases simples para quando travar.
- **🏁 Resumo**: erros recorrentes, frases para levar, vocabulário novo e foco da próxima sessão. Download em `.md`.

## Estrutura
```
app.py               # fluxo do app
ui.py                # visual: cores, balões de conversa
services/voice_chat.py  # microfone mãos-livres (componente no navegador)
config.py            # modelos, voz, velocidade, nível — mude aqui
prompts.py           # cenários, situações e prompts do tutor
services/llm.py      # Claude (conversa, correções, resumo)
services/db.py       # registro de uso, sessões e falas (Postgres/Neon)
services/voice.py    # voz com fallback: grátis primeiro, OpenAI por último
```

## Chaves de API
| Chave | Para quê | Obrigatória? |
|---|---|---|
| `ANTHROPIC_API_KEY` | Conversa e correções (console.anthropic.com) | Sim |
| `GROQ_API_KEY` | Ouvir sua fala, grátis (console.groq.com) | Não |
| `GEMINI_API_KEY` | Ouvir e falar, 2ª opção (aistudio.google.com) | Não |
| `OPENAI_API_KEY` | Ouvir e falar, reserva paga (platform.openai.com) | Não |
| `DATABASE_URL` | Registro de uso e histórico (Neon, grátis) | Recomendado |
| `[auth]` + `ALLOWED_EMAILS` | Login com Google; os e-mails da lista são administradores. Outras pessoas entram se forem liberadas em 👥 Usuários | Recomendado |

As duas APIs cobram por uso. Configure um limite de gasto mensal em cada painel.

## Publicar (sem instalar nada no Mac)
1. Crie um repositório no GitHub (pode ser privado) e suba todos os arquivos desta pasta — **menos** um eventual `.streamlit/secrets.toml`.
2. Em **share.streamlit.io** → *Create app* → escolha o repositório, branch `main`, arquivo `app.py`.
3. Em *Advanced settings → Secrets*, cole o conteúdo de `.streamlit/secrets.toml.example` com suas chaves reais.
4. *Deploy*. No celular, abra o link e permita o microfone.

## Login com Google
1. Google Cloud Console → *APIs & Services → Credentials → Create credentials → OAuth client ID* → tipo **Web application**.
2. Em *Authorized redirect URIs*, coloque `https://tony-english-practice.streamlit.app/oauth2callback`.
3. Copie o *Client ID* e o *Client secret* para a seção `[auth]` dos Secrets, junto com um `cookie_secret` aleatório.
4. Em `ALLOWED_EMAILS`, liste os e-mails que podem entrar.

## Ajustes rápidos (config.py)
- Mais qualidade na conversa: `CHAT_MODEL = "claude-sonnet-5-5"`.
- Outra voz grátis: `EDGE_VOICE` (ex.: en-US-AndrewNeural, en-GB-SoniaNeural).
- Velocidade do "ouvir devagar": `EDGE_RATE_SLOW`.
- Nova situação: adicione uma linha em `SCENARIOS` no `prompts.py`.

## Manter o app acordado
`.github/workflows/keep-awake.yml` roda a cada 6 horas: abre os apps num navegador e, se algum estiver dormindo, clica em "Yes, get this app back up". Para rodar na hora: GitHub → Actions → "Manter apps acordados" → Run workflow.
Opcional: com o secret `DATABASE_URL` no repositório (Settings → Secrets and variables → Actions), ele também acorda o banco Neon.
