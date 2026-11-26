"""Interface em inglês para o perfil adulto (o infantil e a área dos pais continuam em português).

Como funciona: install() embrulha as funções do Streamlit (botões, abas, textos, avisos...) e, quando a sessão
está em inglês (st.session_state["_ui_en"]), troca o texto em português pela versão em inglês:
  1) frase inteira igual a uma chave de EN → tradução direta;
  2) senão, troca trechos de FRAG dentro do texto (cobre textos montados com variáveis, ex.: "Concluídos: 3 de 50").
Textos que não estão no dicionário aparecem como estão (nada quebra).
"""
import functools

import streamlit as st

EN = {
    # --- navegação e telas ---
    "Falar": "Talk", "Aprender": "Learn", "Histórico": "History", "Ajustes": "Settings", "Usuários": "Users",
    "Pais": "Parents", "Menu": "Menu",
    "📚 Aprender": "📚 Learn", "⚙️ Ajustes": "⚙️ Settings", "👥 Usuários": "👥 Users", "📊 Histórico e uso": "📊 History & usage",
    # --- Falar ---
    "Pronto para conversar?": "Ready to talk?",
    "Escolha o nível, o modo e o assunto. Ela responde e te ajuda a soar mais natural.":
        "Pick your level, mode and topic. She replies and helps you sound more natural.",
    "Nível": "Level", "**Nível**": "**Level**", "Modo": "Mode", "**Modo**": "**Mode**", "Cenário": "Scenario",
    "**Cenário**": "**Scenario**", "Situação": "Situation", "**Situação**": "**Situation**", "Assunto": "Topic",
    "**Assunto**": "**Topic**",
    "🎧 Mãos livres": "🎧 Hands-free", "👆 Apertar para falar": "👆 Push to talk", "⚡ Ao vivo": "⚡ Live",
    "⌨️ Só texto": "⌨️ Text only", "Mãos livres": "Hands-free", "Apertar para falar": "Push to talk", "Ao vivo": "Live",
    "Só texto": "Text only",
    "Sobre o que você quer conversar hoje?": "What do you want to talk about today?",
    "ex.: taxa de juros, minha viagem de intercâmbio, futebol... (ou deixe vazio)":
        "e.g. interest rates, my exchange trip, football... (or leave it empty)",
    "▶️ Começar conversa": "▶️ Start conversation",
    "Dica: use fone de ouvido. A transcrição e o resumo aparecem quando a chamada terminar.":
        "Tip: use headphones. The transcript and summary show up when the call ends.",
    "↩️ Voltar sem ligar": "↩️ Go back without calling",
    "Use só se a chamada ainda não começou. Para encerrar uma chamada em andamento, toque no botão dela.":
        "Only if the call hasn't started yet. To end a call in progress, tap its own button.",
    "👀 Mostrar texto": "👀 Show text", "👀 Ver texto": "👀 See text", "🔁 Ouvir de novo": "🔁 Listen again",
    "🐢 Falar devagar": "🐢 Speak slowly", "🐢 Devagar: ligado": "🐢 Slow: on",
    "Liga/desliga a voz devagar para o resto da conversa (e repete esta fala).":
        "Turns slow voice on/off for the rest of the conversation (and repeats this line).",
    "🆘 Travou? Ideias de resposta": "🆘 Stuck? Answer ideas",
    "↩️ Não foi isso que eu disse": "↩️ That's not what I said",
    "Apaga esta fala e a resposta; é só falar de novo.": "Deletes this line and the reply; just say it again.",
    "🏁 Encerrar": "🏁 End", "Encerra a conversa, desliga o microfone e mostra o resumo.":
        "Ends the conversation, turns off the mic and shows the summary.",
    "🎙️ Grave sua resposta": "🎙️ Record your answer", "Ou digite sua resposta em inglês...": "Or type your answer in English...",
    "📋 Resumo da sessão": "📋 Session summary", "⬇️ Baixar resumo (PDF)": "⬇️ Download summary (PDF)",
    "⬇️ Baixar resumo": "⬇️ Download summary", "✅ Concluir e voltar ao início": "✅ Finish and go back",
    "Pensando...": "Thinking...", "Ouvindo...": "Listening...", "Montando seu resumo...": "Building your summary...",
    "_Não consegui gerar o resumo desta vez._": "_I couldn't build the summary this time._",
    "Você chegou ao limite de falas de hoje. Volte amanhã! 🙂": "You've reached today's limit. Come back tomorrow! 🙂",
    "A cota grátis do Gemini acabou por hoje — use o modo normal.": "Gemini's free quota is over for today — use normal mode.",
    "🔊 Texto escondido — ouça e tente entender": "🔊 Text hidden — listen and try to understand",
    "Aluno": "Learner", "Parceira": "Partner", "Sessão de inglês": "English session", "Transcrição": "Transcript",
    # --- cenários e situações ---
    "⚡ ao vivo": "⚡ live", "🛒 Dia a dia": "🛒 Everyday life", "💼 Trabalho": "💼 Work", "✈️ Intercâmbio / viagem": "✈️ Study abroad / travel",
    "🧠 Assuntos": "🧠 Topics", "💬 Conversa livre": "💬 Free talk",
    "Restaurante": "Restaurant", "Supermercado": "Supermarket", "Pedir informação na rua": "Asking for directions",
    "Farmácia": "Pharmacy", "Small talk com vizinho": "Small talk with a neighbour", "Reunião de status": "Status meeting",
    "Explicar um dashboard": "Explaining a dashboard", "Entrevista de emprego": "Job interview",
    "Colega estrangeiro": "Foreign colleague", "Explicar um processo": "Explaining a process",
    "Imigração no aeroporto": "Airport immigration", "Primeiro dia na escola": "First day at school",
    "Check-in no Airbnb": "Airbnb check-in", "Fazer amigos na escola": "Making friends at school",
    "Chip de celular": "Buying a SIM card", "Mercado financeiro": "Financial markets", "Câmbio e moedas": "FX & currencies",
    "Tesouraria e dados": "Treasury & data", "Tecnologia e IA": "Tech & AI", "Viagens e culturas": "Travel & cultures",
    "Notícias e atualidades": "News & current affairs", "Filmes e séries": "Movies & series",
    "Esportes e saúde": "Sports & health",
    # --- níveis ---
    "🚀 Infantil": "🚀 Kids", "🍼 Iniciante (A1)": "🍼 Beginner (A1)", "🌱 Básico (A2)": "🌱 Elementary (A2)",
    "🌿 Intermediário (B1)": "🌿 Intermediate (B1)", "🌳 Avançado (B2+)": "🌳 Advanced (B2+)",
    "Infantil": "Kids", "Iniciante\n(A1)": "Beginner\n(A1)", "Básico\n(A2)": "Elementary\n(A2)",
    "Intermediário\n(B1)": "Intermediate\n(B1)", "Avançado\n(B2+)": "Advanced\n(B2+)",
    # --- Aprender ---
    "Gramática": "Grammar", "Vídeos": "Videos", "Tradutor": "Translator", "Corrida": "Race",
    "📝 Gramática": "📝 Grammar", "🎬 Vídeos": "🎬 Videos", "🔤 Tradutor": "🔤 Translator",
    "Trilhas separadas da conversa: gramática por nível, vídeos para treinar a escuta e um tradutor.":
        "Tracks apart from the conversation: grammar by level, videos to train your listening, and a translator.",
    "Bloco": "Block", "Exercício": "Exercise", "➕ Mostrar mais 10 exercícios": "➕ Show 10 more exercises",
    "✨ Abrir exercício": "✨ Open exercise", "Preparando o exercício (só na primeira vez)...":
        "Preparing the exercise (first time only)...", "🔁 Refazer exercício (admin)": "🔁 Rebuild exercise (admin)",
    "Gera uma nova versão deste número, para todos do nível.": "Creates a new version of this number for everyone at this level.",
    "✅ Corrigir": "✅ Check", "Escolha a resposta certa": "Choose the right answer",
    "A trilha de vídeos precisa do banco ligado.": "The video track needs the database.",
    "➕ Adicionar vídeo do YouTube": "➕ Add a YouTube video", "Link do YouTube (público)": "YouTube link (public)",
    "Título (opcional — o Gemini preenche ao ler o vídeo)": "Title (optional — Gemini fills it in)",
    "Adicionar": "Add", "Importar": "Import", "Não reconheci esse link do YouTube.": "I didn't recognise that YouTube link.",
    "Vídeo adicionado.": "Video added.", "📥 Importar uma playlist inteira": "📥 Import a whole playlist",
    "Link da playlist do YouTube (tem 'list=' no endereço)": "YouTube playlist link (has 'list=' in it)",
    "Nome da série": "Series name", "ex.: American English File — Rob & Jenny": "e.g. American English File — Rob & Jenny",
    "Separar por nível pela numeração AEF (AEF 1 → Iniciante, 2 → Básico, 3 → Intermediário, 4-5 → Avançado)":
        "Split by level using AEF numbers (AEF 1 → Beginner, 2 → Elementary, 3 → Intermediate, 4-5 → Advanced)",
    "Nível dos vídeos sem numeração": "Level for videos without a number", "Lendo a playlist...": "Reading the playlist...",
    "📦 Séries e níveis": "📦 Series & levels", "Apagar a série": "Delete series",
    "Ainda não há vídeos neste nível.": "No videos at this level yet.", "Série": "Series", "Avulsos": "Single videos",
    "Legendas em inglês": "English captions", "Assistir em sequência": "Autoplay next",
    "▶️ Não tocou aqui? Abrir no YouTube": "▶️ Not playing? Open on YouTube",
    "📖 Preparar perguntas": "📖 Prepare questions", "O Gemini está assistindo o vídeo...": "Gemini is watching the video...",
    "📒 Vocabulário do vídeo": "📒 Video vocabulary", "🔄 Novas perguntas": "🔄 New questions",
    "Preparando perguntas...": "Preparing questions...", "✅ Enviar respostas": "✅ Submit answers",
    "Corrigindo...": "Checking...", "💬 Conversar sobre este vídeo": "💬 Talk about this video",
    "O que você quer traduzir?": "What do you want to translate?",
    "ex.: 'cash flow' ou 'fazer hora extra'": "e.g. 'fluxo de caixa' or 'work overtime'", "…ou fale": "…or say it",
    "🔤 Traduzir": "🔤 Translate", "Traduzindo...": "Translating...", "🔊 Ouvir em inglês": "🔊 Listen in English",
    "**Outras formas:** ": "**Other ways:** ",
    # --- Revisar frase / pronúncia ---
    "☝️ Escolha a opção correta.": "☝️ Choose the correct option.", "Revisar frase": "Check my sentence", "✍️ Revisar frase": "✍️ Check my sentence",
    "Sua frase em inglês": "Your sentence in English", "ex.: I got a customer too": "e.g. I got a customer too",
    "🔍 Analisar frase": "🔍 Check sentence", "Analisando...": "Checking...", "**💬 Mais natural**": "**💬 More natural**",
    "🔊 Normal": "🔊 Normal", "🐢 Devagar": "🐢 Slow", "🎯 Praticar": "🎯 Practise",
    "Toque no microfone, fale a frase inteira e toque de novo para parar.":
        "Tap the mic, say the whole sentence, then tap again to stop.",
    "🔁 Tentar de novo": "🔁 Try again", "🔄 Começar outra rodada": "🔄 Start another round", "Eu falei certo": "I said it right",
    "🟢 chegou · 🟡 quase · 🔴 não chegou. O reconhecimento de voz às vezes erra: se você tem certeza de que falou "
    "certo, marque abaixo.": "🟢 got it · 🟡 almost · 🔴 didn't come through. Speech recognition sometimes gets it "
    "wrong: if you're sure you said it right, mark it below.",
    "🎤 O teste de pronúncia precisa do reconhecimento de voz ligado.": "🎤 The pronunciation test needs speech recognition on.",
    "🌟 Excelente! Saiu muito claro.": "🌟 Excellent! That was very clear.", "👏 Muito bom! Só um ou outro ajuste.":
        "👏 Very good! Just a couple of tweaks.",
    "🙂 Boa! Ouça as palavras em amarelo/vermelho e tente de novo.": "🙂 Nice! Listen to the yellow/red words and try again.",
    "🎧 Vamos de novo: ouça a frase devagar e repita junto. O microfone às vezes não pega bem — tente mais perto.":
        "🎧 Let's go again: listen to the slow version and repeat along. The mic sometimes misses — try closer.",
    # --- Corrida / Desafio (adulto) ---
    "⚡ Desafio Relâmpago": "⚡ Lightning Challenge", "🏳️ Parar": "🏳️ Stop", "🔊 Ouvir de novo": "🔊 Listen again",
    "Faça pelo menos um exercício de gramática para liberar o desafio.":
        "Do at least one grammar exercise to unlock the challenge.",
    "🤝 Amigos": "🤝 Friends", "**Convide alguém para correr com você!** A pessoa precisa aceitar.":
        "**Invite someone to race with you!** They need to accept.", "Quem?": "Who?",
    "📨 Mandar convite": "📨 Send invite", "Ninguém novo para convidar agora.": "No one new to invite right now.",
    "Convite enviado! 🚀": "Invite sent! 🚀", "✅ Aceitar": "✅ Accept", "Agora não": "Not now", "Sair": "Leave",
    "criança": "kid", "adulto": "adult",
    # --- Histórico ---
    "Quais IAs foram usadas, quanto custou (estimado) e suas conversas anteriores.":
        "Which AIs were used, estimated cost, and your past conversations.",
    "Pessoa": "Person", "Período": "Period", "Custo estimado": "Estimated cost", "Ao vivo hoje": "Live today",
    "Chamadas à OpenAI": "OpenAI calls", "A OpenAI só entra quando os serviços grátis falham.":
        "OpenAI is only used when the free services fail.",
    "Nenhum uso da OpenAI no período: só serviços grátis e o Claude.": "No OpenAI usage in this period: only free services and Claude.",
    "Nenhum uso registrado ainda neste período.": "No usage recorded in this period yet.",
    "🕒 Últimas chamadas (inclui falhas e trocas de serviço)": "🕒 Latest calls (including failures and service switches)",
    "### 🗂️ Conversas anteriores": "### 🗂️ Past conversations", "Abrir conversa": "Open conversation",
    "Nenhuma conversa registrada ainda.": "No conversations yet.", "📋 Resumo dessa conversa": "📋 Summary of this conversation",
    "### 📚 Trilhas concluídas": "### 📚 Completed tracks", "Exercícios de gramática": "Grammar exercises",
    "**📝 Gramática**": "**📝 Grammar**", "**🎬 Vídeos**": "**🎬 Videos**",
    "Nenhum exercício ou vídeo concluído ainda.": "No exercises or videos completed yet.",
    "**⚡ Recordes do Desafio Relâmpago**": "**⚡ Lightning Challenge records**",
    "📨 Resumo da semana para a família": "📨 Weekly family summary", "Resumo": "Summary", "📨 Enviar agora": "📨 Send now",
    "O registro não está ligado: falta o **DATABASE_URL** (Neon) nos Secrets do app.":
        "Logging is off: **DATABASE_URL** (Neon) is missing from the app Secrets.",
    # --- Ajustes ---
    "Do seu jeito: voz, texto e sua conta.": "Your way: voice, text and your account.",
    "🐢 Voz devagar": "🐢 Slow voice", "A parceira fala mais devagar sempre.": "Your partner always speaks more slowly.",
    "👀 Mostrar texto das respostas": "👀 Show reply text",
    "Desligue para treinar a escuta: o texto fica escondido até você abrir.":
        "Turn off to train your listening: the text stays hidden until you open it.",
    "Visual do app": "App look", "🇬🇧 Londres (imersivo)": "🇬🇧 London (immersive)", "🤍 Clássico (claro)": "🤍 Classic (light)",
    "No nível Infantil o app vira sempre o tema Espaço.": "At the Kids level the app always uses the Space theme.",
    "🪐 Planetas novos por dia (perfil infantil)": "🪐 New planets per day (kids profile)",
    "⏳ Tempo de uso por dia (perfil infantil)": "⏳ Daily screen time (kids profile)",
    "3 por dia": "3 a day", "5 por dia": "5 a day", "10 por dia": "10 a day", "Sem limite": "No limit", "1 hora": "1 hour",
    "Refazer planetas que ele já visitou e o ⚡ Desafio nunca contam no limite.":
        "Replaying visited planets and the ⚡ Challenge never count towards the limit.",
    "Conta só o tempo usando de verdade. Quando acaba, o Bip se despede e o app só volta no dia seguinte.":
        "Counts only active time. When it runs out, Bip says goodbye and the app is back the next day.",
    "Limite atualizado ✅": "Limit updated ✅", "Tempo atualizado ✅": "Time updated ✅",
    "🔊 Sons e música": "🔊 Sounds & music", "🎵 Música de fundo": "🎵 Background music",
    "👆 Som quando toca nos botões": "👆 Button sounds", "🎉 Sons de acerto, erro e festa": "🎉 Right/wrong & party sounds",
    "Volume da música": "Music volume",
    "Também dá para mudar o volume ou silenciar tudo no botão 🔊 no canto de cima da tela. "
    "A música abaixa sozinha quando o app fala ou um vídeo toca, e fica desligada durante a conversa por voz.":
        "You can also change the volume or mute everything with the 🔊 button at the top. Music lowers itself when "
        "the app speaks or a video plays, and stays off during voice conversations.",
    "🔒 Privacidade e dados": "🔒 Privacy & data",
    "Quero apagar todas as conversas desta conta (não dá para desfazer).":
        "I want to delete all conversations in this account (can't be undone).",
    "🗑️ Apagar minhas conversas": "🗑️ Delete my conversations", "📲 Instalar no celular e no Mac": "📲 Install on phone & Mac",
    "- **iPhone (Safari):** Compartilhar → *Adicionar à Tela de Início*.\n- **Mac (Safari):** Arquivo → *Adicionar ao Dock*. "
    "**Chrome:** menu ⋮ → *Transmitir, salvar e compartilhar* → *Instalar página como app*.":
        "- **iPhone (Safari):** Share → *Add to Home Screen*.\n- **Mac (Safari):** File → *Add to Dock*. "
        "**Chrome:** menu ⋮ → *Cast, save and share* → *Install page as app*.",
    "Sair da conta": "Sign out", "Salvar meus minutos": "Save my minutes", "Meus minutos ao vivo por dia": "My live minutes per day",
    "sem limite": "no limit", "Salvo.": "Saved.", "Salvo ✅": "Saved ✅", "🌐 Idioma dos menus": "🌐 Menu language",
    # --- Usuários ---
    "Libere pessoas, escolha o nível delas, o limite por dia e quais chaves de API usam.":
        "Let people in, choose their level, daily limit and which API keys they use.",
    "Precisa do banco (DATABASE_URL) ligado para cadastrar usuários.": "Needs the database (DATABASE_URL) to register users.",
    "### 👨‍👩‍👧 Famílias": "### 👨‍👩‍👧 Families",
    "Quando um pai cria a conta da família:": "When a parent creates a family account:",
    "✋ Eu aprovo antes": "✋ I approve first", "✅ Entra direto": "✅ Straight in", "✅ Aprovar": "✅ Approve",
    "Família": "Family", "🔑 Zerar PIN": "🔑 Reset PIN",
    "PIN zerado: no próximo acesso à área dos pais, eles criam outro.": "PIN reset: they'll create a new one next time.",
    "não registrada": "not recorded",
    "Nenhuma família ainda. Quando um pai entrar com o Google pela primeira vez, ele cria a conta.":
        "No families yet. When a parent signs in with Google for the first time, they create the account.",
    "Editar": "Edit", "➕ Novo usuário": "➕ New user", "E-mail Google": "Google e-mail", "Nome (opcional)": "Name (optional)",
    "Acesso liberado": "Access granted", "(livre)": "(free)", "padrão": "default", "nível": "level", "não": "no",
    "Travar o nível (a pessoa não pode trocar)": "Lock the level (they can't change it)",
    "Limite de falas por dia (0 = sem limite)": "Daily message limit (0 = no limit)",
    "Pode usar o modo ao vivo (Gemini grátis)": "Can use live mode (free Gemini)", "Minutos ao vivo por dia": "Live minutes per day",
    "👨‍👩‍👧 Os pais autorizaram (obrigatório para contas do nível Infantil)":
        "👨‍👩‍👧 Parents have consented (required for Kids accounts)",
    "**Chaves de API, serviço por serviço**": "**API keys, service by service**",
    "Só é usada se escolher 'Chave própria'. Deixe em branco para manter a atual.":
        "Only used with 'Own key'. Leave blank to keep the current one.",
    "💾 Salvar usuário": "💾 Save user", "Informe um e-mail válido.": "Enter a valid e-mail.",
    "Lembrete: se o login do Google estiver em modo de teste, adicione o e-mail também como usuário de teste no Google Cloud "
    "(Google Auth Platform → Público-alvo → Usuários de teste).":
        "Reminder: if Google sign-in is in testing mode, also add the e-mail as a test user in Google Cloud "
        "(Google Auth Platform → Audience → Test users).",
}

# trechos (para textos montados com variáveis); os mais longos são aplicados primeiro
FRAG = [
    ("Escreva do seu jeito. O app diz se dá para entender, o que muda na gramática, o que a frase diz ao pé da letra e "
     "como um nativo falaria.", "Write it your way. The app tells you if it's understandable, what changes in the "
     "grammar, what it literally says and how a native would put it."),
    ("✍️ Revisar frase", "✍️ Check my sentence"), ("✅ Perfeita", "✅ Perfect"),
    ("🟢 Entende-se — dá para melhorar", "🟢 Understood — can be improved"),
    ("🟡 Entende-se, mas soa estranho", "🟡 Understood, but sounds odd"), ("🔴 Muda o sentido ou confunde", "🔴 Changes the meaning or confuses"),
    ("**🧠 Entendimento**", "**🧠 Understanding**"), ("**📐 Gramática**", "**📐 Grammar**"),
    ("Correção mínima: **", "Minimal correction: **"),
    ("**🔍 Literal (o que a sua frase diz ao pé da letra)**", "**🔍 Literal (what your sentence says word for word)**"),
    ("sua frase, só com o mínimo ajustado", "your sentence, with only the minimum changed"), ("correção · ", "correction · "),
    ("neutro · ", "neutral · "),
    ("**🗣️ Palavras para caprichar na pronúncia** — toque para ouvir devagar",
     "**🗣️ Words to polish your pronunciation** — tap to hear them slowly"),
    ("🎯 Sua vez: fale esta frase", "🎯 Your turn: say this sentence"), ("O app ouviu: “", "The app heard: “"),
    (" · melhor: ", " · best: "), ("% · tentativa ", "% · try "), ("Não consegui analisar: ", "Couldn't check: "),
    ("Não consegui ouvir: ", "Couldn't listen: "), ("Não consegui falar agora: ", "Couldn't speak right now: "),
    ("Concluídos: **", "Completed: **"), ("** de ", "** of "), ("🪐 Planeta ", "🪐 Planet "), (" · revisão ", " · review "),
    ("Você já concluiu este exercício (melhor nota: ", "You've already finished this exercise (best score: "),
    ("). Pode refazer quando quiser.", "). You can redo it anytime."),
    ("Não consegui criar o exercício: ", "Couldn't create the exercise: "), ("### Nota: ", "### Score: "),
    (".** Certo! ", ".** Correct! "), (".** Resposta: **", ".** Answer: **"), ("Resposta: **", "Answer: **"),
    ("Você escreveu: *", "You wrote: *"), ("Sem resposta · ", "No answer · "),
    ("✍️ Escreva só o que vai na lacuna (", "✍️ Type only what goes in the gap ("), (" palavras).", " words)."),
    (" palavra).", " word)."),
    ("Muito bem! Você acertou ", "Well done! You got "), ("Quase! Você acertou ", "Almost! You got "),
    (" vídeos importados: ", " videos imported: "), ("Não consegui ler a playlist: ", "Couldn't read the playlist: "),
    ("O YouTube só deixou ler os 15 primeiros.", "YouTube only let me read the first 15."),
    ("Se a playlist tiver mais, adicione o resto pelo \"Adicionar vídeo\" (os que já existem não duplicam).",
     "If there are more, add the rest with \"Add video\" (existing ones won't duplicate)."),
    ("Não consegui ler o vídeo: ", "Couldn't read the video: "), ("Não consegui criar as perguntas: ", "Couldn't create the questions: "),
    ("Não consegui corrigir: ", "Couldn't check: "), ("Erro ao iniciar: ", "Couldn't start: "),
    ("Não entendi o áudio: ", "Couldn't understand the audio: "), ("Não consegui traduzir: ", "Couldn't translate: "),
    ("Não consegui entender o áudio. Detalhe técnico: ", "Couldn't understand the audio. Technical detail: "),
    ("Não consegui gerar o áudio: ", "Couldn't generate the audio: "), ("A chamada não começou. ", "The call didn't start. "),
    ("Detalhe: ", "Detail: "), ("Erro: ", "Error: "),
    ("Falas restantes hoje: ", "Messages left today: "), ("⚡ Ao vivo indisponível: ", "⚡ Live unavailable: "),
    ("sem chave do Gemini", "no Gemini key"), ("desativado para esta conta", "disabled for this account"),
    ("a cota grátis do Gemini acabou hoje (renova por volta das 5h)", "Gemini's free quota is over today (resets around 5am)"),
    (" minutos de hoje acabaram", " minutes for today are used up"), ("⚡ Ao vivo: ", "⚡ Live: "), (" min hoje", " min today"),
    ("**Nível:** ", "**Level:** "), ("- Nível: **", "- Level: **"), (" (definido pelo administrador)", " (set by the admin)"),
    ("**Conta:** ", "**Account:** "), (" · administrador", " · admin"),
    ("🏁 Corrida Espacial da semana", "🏁 This week's race"), (" (todo mundo)", " (everyone)"), (" (você e amigos)", " (you & friends)"),
    ("Cada um corre até a própria meta (criança ", "Everyone races to their own goal (kid "), (" pts, adulto ", " pts, adult "),
    (" pts). ⭐ estrela = 10 · 💬 fala = 2 · 🎬 vídeo = 15 · recomeça toda segunda",
     " pts). ⭐ star = 10 · 💬 message = 2 · 🎬 video = 15 · resets every Monday"),
    ("Cada um corre até a sua linha de chegada: criança ", "Everyone races to their own finish line: kid "),
    (" pts. ⭐ estrela = 10 · 💬 fala = 2 · 🎬 vídeo = 15 · recomeça toda segunda.",
     " pts. ⭐ star = 10 · 💬 message = 2 · 🎬 video = 15 · resets every Monday."),
    ("🏆 Recordes do desafio (semana)", "🏆 Challenge records (this week)"),
    ("60 segundos para acertar o máximo de questões ", "60 seconds to answer as many questions as you can "),
    ("dos seus exercícios de gramática", "from your grammar exercises"), (". Acerto rápido vale mais!", ". Fast answers score more!"),
    ("⚡ Começar desafio (seu recorde: ", "⚡ Start challenge (your record: "), ("🏆 Novo recorde: ", "🏆 New record: "),
    (" pontos. Seu recorde é ", " points. Your record is "), (" pontos!", " points!"), (" acertos", " correct"),
    ("Ninguém correu ainda esta semana. Seja o primeiro! 🚀", "Nobody has raced this week yet. Be the first! 🚀"),
    ("Ninguém pontuou ainda esta semana. Seja o primeiro! 🚀", "Nobody has scored this week yet. Be the first! 🚀"),
    (" (você)", " (you)"), ("</b> quer ser seu amigo na Corrida Espacial!", "</b> wants to be your friend in the race!"),
    ("🤝 Amigos (", "🤝 Friends ("), ("⏳ Esperando ", "⏳ Waiting for "), (" aceitar", " to accept"),
    ("📚 O que aprendeu no Infantil (", "📚 What they learned in Kids ("), (" palavras)", " words)"),
    ("**✅ Já acerta:** ", "**✅ Gets right:** "), ("**🔁 Ainda erra (vale treinar junto):** ", "**🔁 Still misses (practise together):** "),
    ("Canais escolhidos: ", "Channels: "), ("nenhum", "none"), (". Vai sozinho toda segunda de manhã.", ". Sent automatically every Monday morning."),
    ("A OpenAI (crédito pago) foi usada ", "OpenAI (paid credit) was used "), (" vez(es) nos últimos ", " time(s) in the last "),
    (" dias", " days"),
    ("Custos estimados pela tabela de preços do app. Valores oficiais:", "Costs estimated from the app's price table. Official figures:"),
    ("O Gemini ao vivo roda no plano grátis", "Live Gemini runs on the free plan"),
    (") · criança: **", ") · kid: **"), ("** · criada em ", "** · created on "), ("Autorização: ", "Consent: "),
    ("Chave própria (", "Own key ("), (") — atual: ", ") — current: "), ("Salvo: ", "Saved: "), ("🗑️ Remover ", "🗑️ Remove "),
    ("Pronto: ", "Done: "), (" conversa(s) apagada(s).", " conversation(s) deleted."),
    ("A conta ", "The account "), (" ainda não foi liberada. Peça ao administrador para liberar seu e-mail.",
                                    " hasn't been approved yet. Ask the admin to approve your e-mail."),
    ("🎬 Vídeo ", "🎬 Video "), ("Vídeo ", "Video "),
]
FRAG = sorted([f for f in FRAG if f[0]], key=lambda f: -len(f[0]))


def on() -> bool:
    try:
        return bool(st.session_state.get("_ui_en"))
    except Exception:
        return False


def T(s):
    """Traduz um texto da interface se a sessão estiver em inglês."""
    if not isinstance(s, str) or not s or not on():
        return s
    if s in EN:
        return EN[s]
    out = s
    for a, b in FRAG:
        if a in out:
            out = out.replace(a, b)
    return out


def _wrap_fmt(fmt):
    def f(x):
        try:
            return T(fmt(x) if fmt is not None else str(x))
        except Exception:
            return T(str(x))
    return f


_TEXT_KW = ("label", "body", "placeholder", "help", "text", "value_text")
_FIRST = {"button", "link_button", "download_button", "form_submit_button", "toggle", "checkbox", "text_input",
          "text_area", "number_input", "slider", "select_slider", "selectbox", "multiselect", "radio", "pills",
          "segmented_control", "expander", "popover", "markdown", "caption", "info", "success", "warning", "error",
          "toast", "spinner", "header", "subheader", "title", "metric", "audio_input", "chat_input", "file_uploader"}
_FMT = {"selectbox", "multiselect", "radio", "pills", "segmented_control", "select_slider"}


def _patch(fn, name, method: bool):
    if getattr(fn, "_i18n", False):
        return fn

    @functools.wraps(fn)
    def w(*args, **kw):
        if on():
            args = list(args)
            # métodos do DeltaGenerator (colunas, containers) recebem self primeiro; st.* recebem o texto primeiro
            i = 1 if method else 0
            if len(args) > i and isinstance(args[i], str):
                args[i] = T(args[i])
            for k in _TEXT_KW:
                if isinstance(kw.get(k), str):
                    kw[k] = T(kw[k])
            if name in _FMT:
                kw["format_func"] = _wrap_fmt(kw.get("format_func"))
            if name == "tabs" and len(args) > i and isinstance(args[i], (list, tuple)):
                args[i] = [T(x) for x in args[i]]
        return fn(*args, **kw)
    w._i18n = True
    return w


def install() -> None:
    """Embrulha as funções do Streamlit uma vez por processo (vale para st.* e para colunas/containers)."""
    from streamlit.delta_generator import DeltaGenerator
    if getattr(DeltaGenerator, "_i18n_done", False):
        return
    for name in _FIRST | {"tabs"}:
        if hasattr(DeltaGenerator, name):
            setattr(DeltaGenerator, name, _patch(getattr(DeltaGenerator, name), name, True))
        if hasattr(st, name):
            setattr(st, name, _patch(getattr(st, name), name, False))
    DeltaGenerator._i18n_done = True
