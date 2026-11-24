"""Navegação: barra de baixo (ícone + nome pequeno, cabe no iPhone) e um menu lateral (☰) que abre e fecha.

O ☰ aparece em todas as telas, inclusive durante a conversa, para sempre dar para voltar.
"""

import streamlit as st

CSS = """
.nv { font-family:'Nunito',system-ui,sans-serif; }
.nv-bar { display:flex; gap:6px; padding:6px 4px 2px; }
.nv-b { flex:1; min-width:0; display:flex; flex-direction:column; align-items:center; gap:2px; padding:7px 2px 6px;
  border-radius:16px; border:1px solid var(--edge); background:var(--glass); color:var(--text); cursor:pointer;
  font-family:inherit; transition: transform .12s ease, background .2s ease; }
.nv-b:active { transform:scale(.94); }
.nv-b .i { font-size:21px; line-height:1; }
.nv-b .t { font-size:11px; font-weight:800; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:100%; }
.nv-b.on { background:linear-gradient(135deg, var(--acc2), var(--acc)); color:var(--ink); border-color:transparent; }
.nv-b.menu { flex:0 0 52px; }
@media (min-width: 700px) { .nv-b { flex-direction:row; justify-content:center; gap:8px; padding:9px 6px; }
  .nv-b .t { font-size:14px; } .nv-b.menu { flex:0 0 58px; } }
.nv-fab { position:fixed; top:12px; left:12px; z-index:1000; width:46px; height:46px; border-radius:14px; border:1px solid var(--edge);
  background:var(--solid); color:var(--text); font-size:22px; cursor:pointer; box-shadow:0 6px 20px rgba(0,0,0,.35); }
.nv-shade { position:fixed; inset:0; z-index:1001; background:rgba(0,0,0,.45); opacity:0; pointer-events:none; transition: opacity .25s ease; }
.nv-drawer { position:fixed; top:0; bottom:0; left:0; z-index:1002; width:min(78vw, 300px); padding:22px 14px;
  background:var(--solid); border-right:1px solid var(--edge); color:var(--text); transform: translateX(-105%);
  transition: transform .3s cubic-bezier(.2,.8,.2,1); display:flex; flex-direction:column; gap:8px; box-shadow: 10px 0 40px rgba(0,0,0,.4); }
.nv.open .nv-shade { opacity:1; pointer-events:auto; }
.nv.open .nv-drawer { transform:none; }
.nv-drawer h4 { margin:0 6px 10px; font-size:18px; font-weight:800; }
.nv-item { display:flex; align-items:center; gap:14px; padding:13px 14px; border-radius:14px; border:1px solid transparent;
  background:transparent; color:var(--text); font-size:17px; font-weight:700; cursor:pointer; font-family:inherit; text-align:left; }
.nv-item .i { font-size:22px; width:28px; text-align:center; }
.nv-item:hover { background:var(--glass); }
.nv-item.on { background:linear-gradient(135deg, var(--acc2), var(--acc)); color:var(--ink); }
"""

JS = """
export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  const old = parentElement.querySelector('.nv'); if (old) old.remove();
  const c = data.colors || {};
  const nv = document.createElement('div'); nv.className = 'nv';
  Object.entries({ '--text': c.text, '--edge': c.edge, '--glass': c.glass, '--solid': c.solid, '--acc': c.accent,
                   '--acc2': c.accent2, '--ink': c.ink }).forEach(([k, v]) => nv.style.setProperty(k, v));
  const items = data.items || [];
  const go = (k) => { nv.classList.remove('open'); if (k !== data.current) setTimeout(() => setTriggerValue('go', k), 120); };
  let html = '';
  if (data.bar) {
    html += '<div class="nv-bar"><button class="nv-b menu" data-menu="1" aria-label="Menu"><span class="i">☰</span><span class="t">Menu</span></button>';
    items.forEach(it => { html += `<button class="nv-b ${it.key === data.current ? 'on' : ''}" data-k="${it.key}" aria-label="${it.label}">
      <span class="i">${it.icon}</span><span class="t">${it.label}</span></button>`; });
    html += '</div>';
  } else {
    html += '<button class="nv-fab" data-menu="1" aria-label="Menu">☰</button>';
  }
  html += '<div class="nv-shade"></div><nav class="nv-drawer"><h4>' + (data.title || 'Menu') + '</h4>';
  items.forEach(it => { html += `<button class="nv-item ${it.key === data.current ? 'on' : ''}" data-k="${it.key}">
    <span class="i">${it.icon}</span><span>${it.label}</span></button>`; });
  html += '</nav>';
  nv.innerHTML = html;
  nv.querySelectorAll('[data-menu]').forEach(b => b.addEventListener('click', () => nv.classList.add('open')));
  nv.querySelector('.nv-shade').addEventListener('click', () => nv.classList.remove('open'));
  nv.querySelectorAll('[data-k]').forEach(b => b.addEventListener('click', () => go(b.dataset.k)));
  parentElement.appendChild(nv);
}
"""

_nav = st.components.v2.component("english_nav", css=CSS, js=JS)

COLORS = {
    "london": {"text": "#F4ECDC", "edge": "rgba(201,168,92,.55)", "glass": "rgba(13,20,36,.55)", "solid": "#121B2E",
               "accent": "#C9A85C", "accent2": "#E6CD8E", "ink": "#1B1408"},
    "space": {"text": "#EAF2FF", "edge": "rgba(126,232,255,.40)", "glass": "rgba(10,12,38,.55)", "solid": "#0D1030",
              "accent": "#38D6F5", "accent2": "#A78BFA", "ink": "#061021"},
    "classic": {"text": "#21414A", "edge": "#CDEDE9", "glass": "#FFFFFF", "solid": "#FFFFFF",
                "accent": "#3FB8AF", "accent2": "#81D8D0", "ink": "#FFFFFF"},
}


def nav(items: list[dict], current: str, theme: str, bar: bool = True, key: str = "nav_bar", title: str = "Menu"):
    """items: [{'key','icon','label'}]. Retorna a chave escolhida (ou None)."""
    res = _nav(key=key, data={"items": items, "current": current, "bar": bar, "title": title,
                              "colors": COLORS.get(theme, COLORS["classic"])}, on_go_change=lambda: None)
    return getattr(res, "go", None)
