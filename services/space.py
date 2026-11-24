"""Catálogo do modo infantil: galáxias e planetas (nomes reais em inglês + curiosidade em português).

Cada galáxia tem 10 paradas = 10 exercícios: 9 planetas + 1 "chefão" no fim.
Galáxia 1: Sistema Solar. Galáxia 2: exoplanetas reais da Via Láctea. Galáxia 3: Andrômeda, onde ainda
não se conhece nenhum planeta, então os planetas são imaginários (e o app avisa).
Imagens: static/theme/planet_<key>.webp (de longe) e surf_<key>.webp (de perto, ao "mergulhar").
"""

from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static" / "theme"
URL = "app/static/theme/"

GALAXIES = [
    {"name": "Sistema Solar", "where": "na Via Láctea", "imaginary": False, "stops": [
        ("mercury", "Mercury", "Mercúrio", "É o planeta mais perto do Sol e um ano lá dura só 88 dias."),
        ("venus", "Venus", "Vênus", "É o planeta mais quente de todos, por causa das nuvens grossas."),
        ("earth", "Earth", "Terra", "É a nossa casa, e o único planeta onde sabemos que existe vida."),
        ("mars", "Mars", "Marte", "É o planeta vermelho e tem o vulcão mais alto do Sistema Solar."),
        ("jupiter", "Jupiter", "Júpiter", "É o maior planeta, e a Grande Mancha Vermelha é uma tempestade gigante."),
        ("saturn", "Saturn", "Saturno", "Seus anéis são feitos de pedaços de gelo e rocha."),
        ("uranus", "Uranus", "Urano", "Ele gira deitado, como uma bola rolando."),
        ("neptune", "Neptune", "Netuno", "Tem os ventos mais fortes de todo o Sistema Solar."),
        ("pluto", "Pluto", "Plutão", "É um planeta-anão e tem uma planície em forma de coração."),
        ("sun", "The Sun", "Sol", "O Sol é uma estrela! Ele dá luz e calor para todos os planetas."),
    ]},
    {"name": "Via Láctea", "where": "outros sistemas", "imaginary": False, "stops": [
        ("proxima_b", "Proxima b", "Próxima b", "É o planeta fora do Sistema Solar mais perto de nós."),
        ("trappist_1e", "TRAPPIST-1e", "TRAPPIST-1e", "Gira em volta de uma estrela pequena junto com outros 6 planetas."),
        ("kepler_452b", "Kepler-452b", "Kepler-452b", "É chamado de 'primo da Terra', porque parece um pouco com ela."),
        ("kepler_22b", "Kepler-22b", "Kepler-22b", "Os cientistas acham que ele pode ser coberto por um oceano."),
        ("kepler_16b", "Kepler-16b", "Kepler-16b", "Ele tem dois sóis no céu!"),
        ("cancri_55e", "55 Cancri e", "55 Cancri e", "É muito quente, e já pensaram que podia ter muito diamante."),
        ("hd_189733b", "HD 189733b", "HD 189733b", "É azul e, lá, pode chover vidro de lado por causa do vento."),
        ("pegasi_51b", "51 Pegasi b", "51 Pegasi b", "Foi o primeiro planeta descoberto em volta de uma estrela como o Sol."),
        ("k2_18b", "K2-18b", "K2-18b", "Pode ter um oceano escondido embaixo de um céu nebuloso."),
        ("sgr_a", "Sagittarius A*", "Sagitário A*", "É o buraco negro gigante que fica bem no centro da nossa galáxia."),
    ]},
    {"name": "Andrômeda", "where": "planetas imaginários", "imaginary": True, "stops": [
        ("p_red", "Rubra", "Rubra", "Planeta imaginário de desertos vermelhos."),
        ("p_ice", "Frostia", "Frostia", "Planeta imaginário de gelo azul."),
        ("p_ringgold", "Aurelia", "Aurelia", "Planeta imaginário com anéis dourados."),
        ("p_ocean", "Marina", "Marina", "Planeta imaginário de mares verdes."),
        ("p_purple", "Violetta", "Violetta", "Planeta imaginário de tempestades roxas."),
        ("p_earth", "Nova Terra", "Nova Terra", "Planeta imaginário parecido com a Terra."),
        ("p_lava", "Vulkan", "Vulkan", "Planeta imaginário cheio de vulcões."),
        ("p_ringpink", "Rosalia", "Rosalia", "Planeta imaginário com anéis cor-de-rosa."),
        ("p_moon", "Cratera", "Cratera", "Lua imaginária cheia de crateras."),
        ("sun", "Andromeda's Heart", "Coração de Andrômeda", "Andrômeda é a galáxia grande mais perto da nossa."),
    ]},
]


def _img(key: str, kind: str) -> str | None:
    for name in ((f"{kind}_{key}", key) if kind == "planet" else (f"{kind}_{key}",)):
        if (STATIC / f"{name}.webp").exists():
            return f"{URL}{name}.webp"
    return None


def galaxy_of(num: int) -> dict:
    return GALAXIES[((num - 1) // 10) % len(GALAXIES)]


def galaxy_name(block: int) -> str:
    g = GALAXIES[block % len(GALAXIES)]
    lap = block // len(GALAXIES)
    return g["name"] + (f" {lap + 1}" if lap else "")


def stop(num: int) -> dict:
    """Informações da parada nº num (1, 2, 3...)."""
    g = galaxy_of(num)
    key, en, pt, fact = g["stops"][(num - 1) % 10]
    return {"num": num, "key": key, "en": en, "pt": pt, "fact": fact, "boss": (num % 10 == 0),
            "imaginary": g["imaginary"], "galaxy": g["name"],
            "img": _img(key, "planet") or f"{URL}planet_sun.webp",
            "surf": _img(key, "surf")}
