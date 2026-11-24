"""Modo infantil: a trilha de exercícios vira uma viagem pela galáxia.

Cada exercício é um planeta; o 10º de cada bloco é um sol ou uma lua especial.
Tudo é CSS + emoji (sem imagens), para continuar leve no celular.
"""

import streamlit as st

CSS = """
.gx { font-family:'Nunito',system-ui,sans-serif; border-radius:22px; padding:14px 12px 18px; color:#fff;
  background-color:rgba(10,12,38,.35);
  background-image: radial-gradient(1.5px 1.5px at 12% 18%, #fff 50%, transparent 51%),
    radial-gradient(1px 1px at 78% 12%, #fff 50%, transparent 51%),
    radial-gradient(1.2px 1.2px at 40% 70%, #fff 50%, transparent 51%),
    radial-gradient(1px 1px at 88% 60%, #fff 50%, transparent 51%),
    radial-gradient(1.5px 1.5px at 25% 92%, #FFF3B8 50%, transparent 51%),
    radial-gradient(1px 1px at 60% 35%, #D9EEFC 50%, transparent 51%),
    radial-gradient(120% 80% at 80% 0%, #3B2A7A 0%, transparent 60%),
    radial-gradient(100% 70% at 0% 100%, #0F5C6E 0%, transparent 65%); }
.gx-top { display:flex; align-items:flex-start; gap:10px; margin-bottom:10px; }
.gx-bot { width:64px; height:72px; flex-shrink:0; animation: gx-float 3s ease-in-out infinite;
  background-size:contain; background-repeat:no-repeat; background-position:center bottom; filter:drop-shadow(0 6px 12px rgba(0,0,0,.45)); }
.gx-party .gx-bot { width:84px; height:92px; }
.gx-say { background:#fff; color:#21414A; border-radius:16px 16px 16px 4px; padding:8px 12px; font-size:15px;
  font-weight:700; line-height:1.3; box-shadow:0 4px 14px rgba(0,0,0,.25); }
.gx-say small { display:block; font-weight:600; color:#5D7A82; font-size:12.5px; margin-top:2px; }
.gx-stats { display:flex; justify-content:space-between; font-size:13px; font-weight:800; margin:0 4px 6px; opacity:.95; }
.gx-map { display:grid; grid-template-columns:repeat(3,1fr); row-gap:14px; }
.gx-cell { display:flex; flex-direction:column; align-items:center; gap:3px; position:relative; }
.gx-p { width:70px; height:70px; border-radius:50%; border:none; cursor:pointer; color:#fff; font-size:18px; font-weight:900;
  font-family:inherit; text-shadow:0 1px 4px rgba(0,0,0,.9); position:relative; padding:0;
  background:transparent center/contain no-repeat; filter: drop-shadow(0 0 10px rgba(140,200,255,.25));
  transition: transform .45s cubic-bezier(.2,.8,.2,1), filter .45s ease, opacity .45s ease; }
.gx-p.zoom { transform:scale(1.5); filter:brightness(1.3) drop-shadow(0 0 30px rgba(255,255,255,.6)); z-index:5; }
.gx-p:active { transform:scale(.93); }
.gx-p.lock { filter:grayscale(1) brightness(.55); cursor:default; }
.gx-p.cur { animation: gx-pulse 1.6s ease-in-out infinite; border-radius:50%; }
.gx-p.sel { outline:3px solid #FFE27A; outline-offset:4px; border-radius:50%; }
.gx-p.boss { width:90px; height:90px; font-size:20px; }
.gx-p.sun { filter: drop-shadow(0 0 18px rgba(255,160,50,.75)); animation: gx-sun 4s ease-in-out infinite; }
@keyframes gx-sun { 50% { filter: drop-shadow(0 0 30px rgba(255,190,80,.95)) } }
.gx-stars { font-size:12px; letter-spacing:1px; min-height:15px; }
.gx-name { font-size:13px; font-weight:800; color:#EAF2FF; text-shadow:0 1px 4px rgba(0,0,0,.9); margin-top:2px; text-align:center; line-height:1.1; }
.gx-title { font-family:'Exo 2','Nunito',sans-serif; font-size:20px; font-weight:800; margin:2px 4px 8px; letter-spacing:.02em; }
.gx-title small { display:block; font-size:12px; font-weight:600; opacity:.75; letter-spacing:0; }
.gx { transition: transform .6s cubic-bezier(.6,0,.4,1), opacity .6s ease; }
.gx.dive { transform: scale(3.4); opacity:0; }
.gx-ship { position:absolute; top:-16px; right:-6px; width:34px; height:34px; animation: gx-float 2.2s ease-in-out infinite; z-index:2;
  background:url('app/static/theme/rocket.webp') center/contain no-repeat; filter:drop-shadow(0 4px 8px rgba(0,0,0,.5)); }
.gx-num { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; }
.gx-foot { text-align:center; font-size:12.5px; opacity:.85; margin-top:12px; }
@keyframes gx-pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(255,226,122,.7) } 50% { box-shadow: 0 0 0 10px rgba(255,226,122,0) } }
@keyframes gx-float { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-4px) } }
.gx-party { position:relative; overflow:hidden; }
.gx-party i { position:absolute; top:-20px; font-style:normal; animation: gx-fall 1.8s ease-in forwards; }
@keyframes gx-fall { to { transform: translateY(240px) rotate(200deg); opacity:0 } }
@media (prefers-reduced-motion: reduce) { .gx-bot, .gx-ship, .gx-p.cur, .gx-party i, .gx-p.sun { animation:none } }
"""

JS = r"""
const IMG = 'app/static/theme/';
export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  const root = parentElement;
  const old = root.querySelector('.gx'); if (old) old.remove();
  const d = data || {};
  const box = document.createElement('div');
  box.className = 'gx' + (d.party ? ' gx-party' : '');
  const stars = n => '⭐'.repeat(n) + '☆'.repeat(3 - n);
  const bot = IMG + (d.party ? 'robot_party.webp' : 'robot_wave.webp');
  let html = `<div class="gx-top"><div class="gx-bot" style="background-image:url('${bot}')"></div>
    <div class="gx-say">${d.say || ''}${d.sub ? `<small>${d.sub}</small>` : ''}</div></div>`;
  if (d.planets && d.planets.length) {
    if (d.galaxy) html += `<div class="gx-title">🌌 ${d.galaxy}<small>${d.where || ''}</small></div>`;
    html += `<div class="gx-stats"><span>${d.ship || '🚀'} ${d.name || ''}</span><span>⭐ ${d.total_stars || 0}</span></div>`;
    // caminho em "cobrinha": 1 2 3 / 6 5 4 / 7 8 9 / 10 no meio
    const p = d.planets, order = [];
    for (let r = 0; r * 3 < Math.min(9, p.length); r++) {
      const row = p.slice(r * 3, r * 3 + 3);
      order.push(...(r % 2 ? row.slice().reverse() : row));
    }
    html += '<div class="gx-map">';
    order.forEach(pl => { html += cell(pl); });
    if (p.length > 9) html += '<div class="gx-cell"></div>' + cell(p[9]) + '<div class="gx-cell"></div>';
    html += '</div>';
    if (d.foot) html += `<div class="gx-foot">${d.foot}</div>`;
  }
  function cell(pl) {
    const cls = ['gx-p'];
    if (pl.boss) cls.push('boss', pl.boss);
    if (pl.locked) cls.push('lock'); if (pl.current) cls.push('cur'); if (pl.selected) cls.push('sel');
    const bg = `background-image:url('${pl.img}');`;
    const label = `<span class="gx-num">${pl.locked ? '🔒' : pl.num}</span>`;
    return `<div class="gx-cell">${pl.current ? '<span class="gx-ship"></span>' : ''}
      <button class="${cls.join(' ')}" style="${bg}" data-n="${pl.num}" ${pl.locked ? 'disabled' : ''}
        aria-label="Planeta ${pl.num}">${label}</button>
      <div class="gx-name">${pl.name || ''}</div>
      <div class="gx-stars">${pl.done ? stars(pl.stars) : ''}</div></div>`;
  }
  box.innerHTML = html;
  box.querySelectorAll('button[data-n]').forEach(b => b.addEventListener('click', () => {
    if (b.disabled) return;
    // a câmera "mergulha" no planeta: o mapa inteiro aproxima a partir do planeta tocado
    const r = b.getBoundingClientRect(), R = box.getBoundingClientRect();
    box.style.transformOrigin = `${r.left - R.left + r.width / 2}px ${r.top - R.top + r.height / 2}px`;
    b.classList.add('zoom'); box.classList.add('dive');
    setTimeout(() => setTriggerValue('pick', parseInt(b.dataset.n, 10)), 600);
  }));
  if (d.party) {
    for (let i = 0; i < 18; i++) {
      const s = document.createElement('i');
      s.textContent = ['⭐', '✨', '🌟'][i % 3];
      s.style.left = (Math.random() * 95) + '%';
      s.style.animationDelay = (Math.random() * .7) + 's';
      s.style.fontSize = (14 + Math.random() * 14) + 'px';
      box.appendChild(s);
    }
  }
  root.appendChild(box);
}
"""

_component = st.components.v2.component("english_galaxy", css=CSS, js=JS)


def stars_for(score: int, total: int) -> int:
    if not total:
        return 0
    r = score / total
    return 3 if r >= 1 else 2 if r >= 0.66 else 1 if r >= 0.5 else 0


def passed(score: int, total: int) -> bool:
    """Libera o próximo planeta quando acerta pelo menos metade."""
    return bool(total) and score * 2 >= total


def galaxy_map(planets: list[dict], say: str, sub: str = "", name: str = "", ship: str = "🚀",
               total_stars: int = 0, foot: str = "", galaxy: str = "", where: str = "", key: str = "galaxy"):
    """Mostra o mapa. Retorna o nº do planeta tocado (ou None)."""
    res = _component(key=key, data={"planets": planets, "say": say, "sub": sub, "name": name, "ship": ship,
                                    "total_stars": total_stars, "foot": foot, "galaxy": galaxy, "where": where},
                     on_pick_change=lambda: None)
    return getattr(res, "pick", None)


def mascot(say: str, sub: str = "", party: bool = False, key: str = "mascot") -> None:
    """Só o robozinho falando (com chuva de estrelas quando party=True)."""
    _component(key=key, data={"say": say, "sub": sub, "party": party})


# --- Dentro do planeta: trilha de paradas e montar frase ------------------------------------
def trail_html(n_stops: int, current: int, results: dict, icons: dict) -> str:
    """Caminho de paradas (0 = briefing). results: {i: True/False}; icons: {i: emoji}."""
    dots = []
    for i in range(n_stops):
        cls = "cur" if i == current else ("ok" if results.get(i) is True else "bad" if results.get(i) is False else "")
        mark = "✓" if results.get(i) is True else "✗" if results.get(i) is False else icons.get(i, str(i))
        ship = '<span class="tr-ship"></span>' if i == current else ""
        dots.append(f'<div class="tr-stop {cls}">{ship}<span>{mark}</span></div>')
    return f'<div class="tr">{"<i></i>".join(dots)}</div>'


TRAIL_CSS = """
<style>
.tr { display:flex; align-items:center; gap:0; margin:6px 0 14px; padding:10px 6px 4px; overflow-x:auto; }
.tr i { flex:1; min-width:10px; height:3px; background: repeating-linear-gradient(90deg, rgba(255,255,255,.55) 0 6px, transparent 6px 11px); }
.tr-stop { position:relative; flex-shrink:0; width:34px; height:34px; border-radius:50%; display:flex; align-items:center;
  justify-content:center; font-weight:800; font-size:14px; color:#EAF2FF; background:rgba(255,255,255,.10);
  border:2px solid rgba(255,255,255,.35); backdrop-filter: blur(4px); }
.tr-stop.ok { background:linear-gradient(135deg,#7EF0B5,#2FBF83); border-color:#BFFCE0; color:#05301E; }
.tr-stop.bad { background:rgba(255,120,120,.25); border-color:#FF9C9C; }
.tr-stop.cur { width:44px; height:44px; background:linear-gradient(135deg,#A78BFA,#38D6F5); border-color:#fff; color:#061021;
  box-shadow:0 0 18px rgba(120,220,255,.7); animation: tr-pulse 1.6s ease-in-out infinite; }
.tr-ship { position:absolute; top:-20px; left:50%; width:28px; height:28px; transform:translateX(-50%);
  background:url('app/static/theme/rocket.webp') center/contain no-repeat; }
@keyframes tr-pulse { 50% { box-shadow:0 0 28px rgba(120,220,255,.95) } }
.kp-card { animation: kp-in .5s cubic-bezier(.2,.8,.2,1); background:rgba(8,10,32,.55); border:1px solid rgba(126,232,255,.35);
  border-radius:22px; padding:16px 18px; margin-bottom:12px; backdrop-filter: blur(8px); }
@keyframes kp-in { from { opacity:0; transform: translateY(30px) scale(.92) } to { opacity:1; transform:none } }
.kp-q { font-size:1.45rem; font-weight:800; line-height:1.35; color:#fff; }
.kp-head { display:flex; align-items:center; gap:12px; margin:4px 0 6px; }
.kp-head img { width:64px; height:64px; animation: kp-spin 30s linear infinite; filter: drop-shadow(0 0 14px rgba(140,200,255,.5)); }
@keyframes kp-spin { to { transform: rotate(360deg) } }
.kp-head h2 { margin:0 !important; font-family:'Exo 2','Nunito',sans-serif !important; font-size:2rem !important; color:#fff !important; }
.kp-head small { display:block; color:#AFC0E8; font-size:.9rem; }
.kp-fact { background:rgba(255,255,255,.08); border-radius:14px; padding:8px 12px; color:#EAF2FF; font-size:.95rem; }
@media (prefers-reduced-motion: reduce) { .kp-card, .kp-head img, .tr-stop.cur { animation:none } }
</style>
"""

_WB_CSS = """
.wb { font-family:'Nunito',system-ui,sans-serif; }
.wb-line { min-height:58px; border-radius:16px; border:2px dashed rgba(126,232,255,.55); padding:8px; display:flex; flex-wrap:wrap;
  gap:8px; align-items:center; background:rgba(255,255,255,.06); margin-bottom:12px; }
.wb-line:empty::before { content:'Toque nas palavras na ordem certa 👇'; color:#AFC0E8; font-size:14px; padding-left:6px; }
.wb-bank { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:12px; }
.wb-w { border:none; border-radius:14px; padding:10px 14px; font-size:18px; font-weight:800; cursor:pointer; font-family:inherit;
  background:linear-gradient(135deg,#FFFFFF,#DDE9FF); color:#122046; box-shadow:0 4px 0 #8FA6D8; transition: transform .12s ease; }
.wb-w:active { transform: translateY(3px); box-shadow:0 1px 0 #8FA6D8; }
.wb-line .wb-w { background:linear-gradient(135deg,#A78BFA,#38D6F5); color:#061021; box-shadow:0 4px 0 #2B6F99; }
.wb-go { width:100%; border:none; border-radius:999px; padding:12px; font-size:17px; font-weight:800; cursor:pointer;
  background:linear-gradient(135deg,#A78BFA,#38D6F5); color:#061021; font-family:inherit; }
.wb-go:disabled { opacity:.45; cursor:default; }
"""
_WB_JS = """
export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  const old = parentElement.querySelector('.wb'); if (old) old.remove();
  const box = document.createElement('div'); box.className = 'wb';
  const line = document.createElement('div'); line.className = 'wb-line';
  const bank = document.createElement('div'); bank.className = 'wb-bank';
  const go = document.createElement('button'); go.className = 'wb-go'; go.textContent = '🚀 Confirmar'; go.disabled = true;
  const words = data.words || [];
  const refresh = () => { go.disabled = bank.children.length > 0; };
  words.forEach(w => {
    const b = document.createElement('button'); b.className = 'wb-w'; b.textContent = w;
    b.addEventListener('click', () => { (b.parentElement === bank ? line : bank).appendChild(b); refresh(); });
    bank.appendChild(b);
  });
  go.addEventListener('click', () => setTriggerValue('answer', [...line.children].map(x => x.textContent).join(' ')));
  box.append(line, bank, go); parentElement.appendChild(box);
}
"""
_wb = st.components.v2.component("english_word_builder", css=_WB_CSS, js=_WB_JS)


def word_builder(words: list[str], key: str):
    """Palavras embaralhadas; a criança toca na ordem. Retorna a frase montada quando confirma."""
    res = _wb(key=key, data={"words": words}, on_answer_change=lambda: None)
    return getattr(res, "answer", None)
