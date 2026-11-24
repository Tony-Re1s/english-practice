"""Programa de gramática por nível, na ordem da progressão do Quadro Europeu (CEFR).

O exercício N de um nível usa o tema N da lista. Quando a lista acaba, recomeça com uma variação
(revisão com frases novas), então a trilha pode crescer sem limite: 1, 2, 3... sempre na mesma ordem.
Os exercícios são criados pelo Claude na primeira vez que alguém abre e ficam salvos no banco.
"""

SYLLABUS = {
    "crianca": [
        "Colors (red, blue, green, yellow)", "Numbers 1-10", "Animals (cat, dog, bird, fish)", "Family words (mom, dad, brother, sister)",
        "I am / You are", "My name is ...", "Fruits (apple, banana, orange)", "Toys (ball, doll, car, kite)",
        "This is / That is", "Big and small", "Body parts (head, eyes, hands)", "Clothes (shirt, shoes, hat)",
        "I like / I don't like", "Food (pizza, rice, bread, milk)", "Numbers 11-20", "Shapes (circle, square, triangle)",
        "School things (pen, book, bag)", "Can / can't (I can swim)", "Days of the week", "Weather (sunny, rainy, cold)",
        "Feelings (happy, sad, tired)", "Places at home (kitchen, bedroom)", "In / on / under", "Have got (I have got a dog)",
        "Actions (run, jump, sing, dance)", "Plurals (one cat, two cats)", "Opposites (hot/cold, up/down)", "Farm animals and sounds",
        "Sports (soccer, swimming)", "Questions: What is it?",
    ],
    "iniciante": [
        "Verb to be: I am, you are, he is", "Verb to be: negative and questions", "Subject pronouns", "Possessive adjectives (my, your, his, her)",
        "Articles a / an / the", "Plural nouns (regular and irregular)", "This / that / these / those", "There is / there are",
        "Present simple: affirmative", "Present simple: negative (don't / doesn't)", "Present simple: questions (do / does)", "Adverbs of frequency (always, usually, never)",
        "Can / can't for ability", "Prepositions of place (in, on, under, next to)", "Prepositions of time (in, on, at)", "Like + -ing",
        "Have got / has got", "Imperatives", "Object pronouns (me, him, her, us, them)", "Question words (what, where, when, who, how)",
        "Countable and uncountable nouns", "Some / any", "How much / how many", "Present continuous: affirmative",
        "Present continuous: questions and negatives", "Present simple vs present continuous", "Was / were", "Past simple: regular verbs",
        "Past simple: irregular verbs (common)", "Past simple: questions and negatives", "Possessive 's", "Would like",
        "Adjectives: order and position", "Telling the time", "Dates and ordinal numbers",
    ],
    "basico": [
        "Past simple review (regular and irregular)", "Past continuous", "Past simple vs past continuous (when / while)", "Comparative adjectives",
        "Superlative adjectives", "As ... as", "Going to (plans)", "Will (predictions and decisions)",
        "Present continuous for future arrangements", "Present perfect: ever / never", "Present perfect: just / already / yet", "Present perfect vs past simple",
        "Have to / don't have to", "Must / mustn't", "Should / shouldn't (advice)", "Might / may (possibility)",
        "Adverbs of manner (quickly, carefully)", "Too / enough", "Verb + -ing vs verb + to infinitive", "First conditional",
        "Something / anything / nothing / everything", "Quantifiers: a lot of, a little, a few", "Relative pronouns: who / which / that", "Used to",
        "Phrasal verbs: everyday (get up, turn on, look for)", "Prepositions of movement", "Object questions vs subject questions", "Possessive pronouns (mine, yours)",
        "Reflexive pronouns", "Linking words: and, but, because, so",
    ],
    "intermediario": [
        "Present perfect continuous", "Present perfect simple vs continuous", "Past perfect", "Narrative tenses together",
        "Future forms: will / going to / present continuous", "Second conditional", "First vs second conditional", "Zero conditional",
        "Passive voice: present and past", "Passive voice: other tenses", "Reported speech: statements", "Reported speech: questions",
        "Defining relative clauses", "Non-defining relative clauses", "Modals of deduction: must / might / can't (present)", "Used to / be used to / get used to",
        "Gerunds and infinitives after verbs", "So / such", "Question tags", "Indirect questions",
        "Make vs do collocations", "Phrasal verbs: work and business", "Too / enough / very", "Wish + past simple",
        "Countable/uncountable: much, many, a great deal of", "Linkers of contrast: although, however, despite", "Linkers of purpose and result", "Prepositions after adjectives (good at, interested in)",
        "Present tenses for habits (will / would for habits)", "Ability: can / could / be able to",
    ],
    "avancado": [
        "Third conditional", "Mixed conditionals", "Wish / if only (past and present)", "Modals of deduction in the past (must have, might have)",
        "Should have / could have (criticism and regret)", "Future continuous and future perfect", "Passive with reporting verbs (it is said that ...)", "Causative have / get something done",
        "Advanced relative clauses (whose, whom, where, prepositions)", "Participle clauses", "Inversion for emphasis (Never have I ...)", "Cleft sentences (What I need is ...)",
        "Reported speech: reporting verbs (suggest, deny, admit)", "Verb patterns with change of meaning (stop, remember, try)", "Articles: advanced uses", "Quantifiers: advanced (each, every, either, neither)",
        "Phrasal verbs: finance and negotiation", "Collocations for business and finance", "Hedging and softening language", "Linking words: formal register (moreover, nevertheless)",
        "Ellipsis and substitution (so, neither, do so)", "Would rather / had better / it's time", "Emphatic do / did", "Future in the past (was going to, would)",
        "Comparatives: advanced (the more ... the more)", "Nouns and prepositions (increase in, demand for)", "Formal vs informal emails", "Common mistakes of Brazilian speakers",
    ],
}


def topic_for(level: str, num: int) -> tuple[str, int]:
    """(tema, rodada): rodada 1 = primeira vez do tema; 2+ = revisão com frases novas."""
    topics = SYLLABUS.get(level) or SYLLABUS["basico"]
    idx = (num - 1) % len(topics)
    return topics[idx], (num - 1) // len(topics) + 1
