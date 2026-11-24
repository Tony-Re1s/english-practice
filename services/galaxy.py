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
.gx-p.zoom { transform:scale(2.4); filter:brightness(1.3) drop-shadow(0 0 30px rgba(255,255,255,.6)); opacity:.0; z-index:5; }
.gx-p:active { transform:scale(.93); }
.gx-p.lock { filter:grayscale(1) brightness(.55); cursor:default; }
.gx-p.cur { animation: gx-pulse 1.6s ease-in-out infinite; border-radius:50%; }
.gx-p.sel { outline:3px solid #FFE27A; outline-offset:4px; border-radius:50%; }
.gx-p.boss { width:90px; height:90px; font-size:20px; }
.gx-p.sun { filter: drop-shadow(0 0 18px rgba(255,160,50,.75)); animation: gx-sun 4s ease-in-out infinite; }
@keyframes gx-sun { 50% { filter: drop-shadow(0 0 30px rgba(255,190,80,.95)) } }
.gx-stars { font-size:12px; letter-spacing:1px; min-height:15px; }
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
const PLANETS = ['p_red','p_ice','p_ringgold','p_ocean','p_purple','p_earth','p_lava','p_ringpink','p_ice'];
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
    const img = pl.boss === 'sun' ? 'sun' : (pl.boss === 'moon' ? 'p_moon' : PLANETS[(pl.num - 1) % 10 % PLANETS.length]);
    const bg = img ? `background-image:url('${IMG}${img}.webp');` : '';
    const label = `<span class="gx-num">${pl.locked ? '🔒' : pl.num}</span>`;
    return `<div class="gx-cell">${pl.current ? '<span class="gx-ship"></span>' : ''}
      <button class="${cls.join(' ')}" style="${bg}" data-n="${pl.num}" ${pl.locked ? 'disabled' : ''}
        aria-label="Planeta ${pl.num}">${label}</button>
      <div class="gx-stars">${pl.done ? stars(pl.stars) : ''}</div></div>`;
  }
  box.innerHTML = html;
  box.querySelectorAll('button[data-n]').forEach(b => b.addEventListener('click', () => {
    if (b.disabled) return;
    b.classList.add('zoom');   // "voa" para dentro do planeta
    setTimeout(() => setTriggerValue('pick', parseInt(b.dataset.n, 10)), 380);
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
               total_stars: int = 0, foot: str = "", key: str = "galaxy"):
    """Mostra o mapa. Retorna o nº do planeta tocado (ou None)."""
    res = _component(key=key, data={"planets": planets, "say": say, "sub": sub, "name": name, "ship": ship,
                                    "total_stars": total_stars, "foot": foot},
                     on_pick_change=lambda: None)
    return getattr(res, "pick", None)


def mascot(say: str, sub: str = "", party: bool = False, key: str = "mascot") -> None:
    """Só o robozinho falando (com chuva de estrelas quando party=True)."""
    _component(key=key, data={"say": say, "sub": sub, "party": party})
