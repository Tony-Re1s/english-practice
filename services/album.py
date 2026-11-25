"""Álbum de figurinhas do modo Infantil: planetas concluídos + figurinhas especiais por conquistas.

Cada figurinha tem curiosidade em português e em inglês (frase curta, para ele ouvir e repetir).
Imagens: static/theme/<arquivo>. Se a imagem ainda não existir, mostra um emoji grande no lugar.
"""
from pathlib import Path

from services import space

STATIC = Path(__file__).resolve().parent.parent / "static" / "theme"
URL = "app/static/theme/"

# Curiosidade em inglês simples para cada parada da trilha (o português vem de space.GALAXIES).
EN_FACT = {
    "mercury": "Mercury is the closest planet to the Sun. A year there is only 88 days!",
    "venus": "Venus is the hottest planet. Its thick clouds trap the heat.",
    "earth": "Earth is our home. It is the only planet with life that we know.",
    "mars": "Mars is the red planet. It has the tallest volcano in the Solar System.",
    "jupiter": "Jupiter is the biggest planet. The Great Red Spot is a giant storm.",
    "saturn": "Saturn's rings are made of ice and rock.",
    "uranus": "Uranus spins on its side, like a rolling ball.",
    "neptune": "Neptune has the strongest winds in the Solar System.",
    "pluto": "Pluto is a dwarf planet. It has a big heart on it!",
    "sun": "The Sun is a star! It gives light and heat to all the planets.",
    "proxima_b": "Proxima b is the closest planet outside our Solar System.",
    "trappist_1e": "TRAPPIST-1e goes around a small star with six other planets.",
    "kepler_452b": "Kepler-452b is called Earth's cousin.",
    "kepler_22b": "Kepler-22b may be covered by a big ocean.",
    "kepler_16b": "Kepler-16b has two suns in the sky!",
    "cancri_55e": "55 Cancri e is very, very hot.",
    "hd_189733b": "HD 189733b is blue, and it may rain glass there!",
    "pegasi_51b": "51 Pegasi b was the first planet found around a star like our Sun.",
    "k2_18b": "K2-18b may have an ocean under its cloudy sky.",
    "sgr_a": "Sagittarius A* is a giant black hole in the center of our galaxy.",
    "p_red": "Rubra is an imaginary planet with red deserts.",
    "p_ice": "Frostia is an imaginary planet of blue ice.",
    "p_ringgold": "Aurelia is an imaginary planet with golden rings.",
    "p_ocean": "Marina is an imaginary planet with green seas.",
    "p_purple": "Violetta is an imaginary planet with purple storms.",
    "p_earth": "Nova Terra is an imaginary planet that looks like Earth.",
    "p_lava": "Vulkan is an imaginary planet full of volcanoes.",
    "p_ringpink": "Rosalia is an imaginary planet with pink rings.",
    "p_moon": "Cratera is an imaginary moon full of craters.",
}
EN_FACT_ANDROMEDA_HEART = "Andromeda is the closest big galaxy to ours."

# Figurinhas especiais: (chave, nome em inglês, nome em português, emoji, arquivo, curiosidade pt, curiosidade en, regra)
# regra: ("planet", n) = completar a parada n · ("stars", n) = juntar n estrelas · ("count", n) = n planetas concluídos
SPECIAL = [
    ("astronaut", "Astronaut", "Astronauta", "👩‍🚀", "sticker_astronaut.webp",
     "Astronautas flutuam na nave porque lá quase não sentimos o peso.",
     "Astronauts float in space. They sleep in sleeping bags on the wall!", ("planet", 1)),
    ("moon", "The Moon", "A Lua", "🌙", "planet_moon.webp",
     "A Lua não tem luz própria: ela brilha refletindo a luz do Sol.",
     "The Moon has no light. It shines with light from the Sun.", ("planet", 3)),
    ("iss", "Space Station", "Estação Espacial", "🛰️", "sticker_iss.webp",
     "A Estação Espacial dá uma volta na Terra a cada 90 minutos!",
     "The Space Station goes around the Earth every 90 minutes!", ("count", 5)),
    ("comet", "Comet", "Cometa", "☄️", "sticker_comet.webp",
     "Cometas são bolas de gelo e poeira. Quando chegam perto do Sol, ganham uma cauda brilhante.",
     "Comets are balls of ice and dust. Near the Sun, they get a long shiny tail.", ("stars", 15)),
    ("southern_cross", "Southern Cross", "Cruzeiro do Sul", "✨", "sticker_southern_cross.webp",
     "O Cruzeiro do Sul aparece na bandeira do Brasil e ajuda a achar o Sul.",
     "The Southern Cross is on the flag of Brazil. It helps people find the south.", ("planet", 10)),
    ("shooting_star", "Shooting Star", "Estrela cadente", "🌠", "sticker_shooting_star.webp",
     "Estrela cadente não é estrela: é uma pedrinha do espaço queimando no céu.",
     "A shooting star is not a star. It is a little space rock burning in the sky.", ("stars", 25)),
    ("orion", "Orion", "Órion", "⭐", "sticker_orion.webp",
     "Órion é um caçador no céu. As Três Marias são o cinto dele!",
     "Orion is a hunter in the sky. Three stars make his belt.", ("stars", 40)),
    ("milky_way", "Milky Way", "Via Láctea", "🌌", "sticker_milky_way.webp",
     "A Via Láctea é a nossa galáxia. Ela tem mais de 100 bilhões de estrelas!",
     "The Milky Way is our galaxy. It has more than 100 billion stars!", ("planet", 20)),
    ("big_dipper", "Big Dipper", "Ursa Maior", "🐻", "sticker_big_dipper.webp",
     "Sete estrelas da Ursa Maior formam uma concha gigante no céu.",
     "Seven stars in the Big Dipper look like a giant spoon.", ("stars", 60)),
    ("andromeda", "Andromeda Galaxy", "Galáxia de Andrômeda", "💫", "sticker_andromeda.webp",
     "Andrômeda é tão longe que a luz dela leva 2 milhões de anos para chegar aqui.",
     "Andromeda is so far away that its light travels for 2 million years to reach us.", ("planet", 21)),
    ("nebula", "Nebula", "Nebulosa", "🌈", "sticker_nebula.webp",
     "Nebulosas são nuvens coloridas de gás e poeira onde nascem as estrelas.",
     "A nebula is a colorful cloud where new stars are born.", ("stars", 80)),
    ("telescope", "Space Telescope", "Telescópio espacial", "🔭", "sticker_telescope.webp",
     "O telescópio James Webb fica no espaço e enxerga galáxias muito, muito antigas.",
     "The James Webb telescope lives in space and sees very old galaxies.", ("stars", 100)),
]


def _img(file: str) -> str:
    return URL + file if (STATIC / file).exists() else ""


def _rule_text(rule: tuple) -> str:
    kind, n = rule
    if kind == "planet":
        return f"Complete {space.stop(n)['pt']}"
    if kind == "stars":
        return f"Junte {n} ⭐"
    return f"Explore {n} planetas"


def stickers(passed_nums: set[int], stars: int, max_num: int = 30) -> list[dict]:
    """Lista de figurinhas (ganhas e por ganhar), na ordem do álbum."""
    out = []
    for n in range(1, max_num + 1):
        info = space.stop(n)
        en = EN_FACT.get(info["key"], "")
        if info["key"] == "sun" and info["imaginary"]:
            en = EN_FACT_ANDROMEDA_HEART
        out.append({"key": f"p{n}", "group": info["galaxy"], "en": info["en"], "pt": info["pt"], "img": info["img"],
                    "emoji": "🪐", "fact_pt": info["fact"], "fact_en": en, "got": n in passed_nums,
                    "how": f"Complete {info['pt']}"})
    for key, en, pt, emo, file, fpt, fen, rule in SPECIAL:
        kind, val = rule
        if kind == "planet":
            got = val in passed_nums
        elif kind == "stars":
            got = stars >= val
        else:
            got = len(passed_nums) >= val
        out.append({"key": key, "group": "Especiais", "en": en, "pt": pt, "img": _img(file), "emoji": emo,
                    "fact_pt": fpt, "fact_en": fen, "got": bool(got), "how": _rule_text(rule)})
    return out
