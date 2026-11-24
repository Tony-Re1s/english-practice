"""Visual do app: paleta suave (branco, verde Tiffany, azul-bebê, amarelo claro) e balões de conversa."""

import html

import streamlit as st

TIFFANY = "#81D8D0"
TIFFANY_DARK = "#139C94"
BABY_BLUE = "#DCEFFC"
SOFT_YELLOW = "#FFF6CF"
INK = "#21414A"
MUTED = "#5D7A82"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');
.stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp input, .stApp textarea, .stApp button p, .hero, .msg, .tip, .pill {{ font-family: 'Nunito', system-ui, sans-serif !important; }}
[data-testid="stIconMaterial"], .material-symbols-rounded {{ font-family: 'Material Symbols Rounded' !important; }}
.block-container {{ padding-top: 2.2rem; max-width: 760px; }}
h1, h2, h3 {{ color: {INK}; letter-spacing: -.01em; }}

.hero {{ background: linear-gradient(135deg, #E9F8F6 0%, #EEF6FD 55%, #FFFBEA 100%);
  border: 1px solid #D8F0ED; border-radius: 22px; padding: 22px 24px; margin-bottom: 18px; }}
.hero h1 {{ font-size: 1.9rem; margin: 0 0 4px; font-weight: 800; }}
.hero p {{ margin: 0; color: {MUTED}; font-size: 1rem; }}

.pill {{ display:inline-block; background:#E9F8F6; color:{TIFFANY_DARK}; border:1px solid #CDEDE9;
  border-radius:999px; padding:4px 12px; font-size:.85rem; font-weight:700; }}

.msg {{ display:flex; gap:10px; margin: 10px 0; align-items:flex-end; }}
.msg.me {{ justify-content:flex-end; }}
.avatar {{ width:34px; height:34px; border-radius:50%; background:#E9F8F6; display:flex; align-items:center;
  justify-content:center; font-size:18px; flex-shrink:0; border:1px solid #CDEDE9; }}
.bubble {{ max-width: 82%; padding: 12px 16px; border-radius: 20px; line-height: 1.45; font-size: 1.02rem;
  color: {INK}; box-shadow: 0 2px 10px rgba(33,65,74,.06); }}
.msg.ai .bubble {{ background:#FFFFFF; border:1.5px solid {TIFFANY}; border-bottom-left-radius: 6px; }}
.msg.me .bubble {{ background:{BABY_BLUE}; border:1.5px solid #C4E2F7; border-bottom-right-radius: 6px; }}
.bubble.hidden {{ color:{MUTED}; font-style: italic; }}
.tip {{ margin: -2px 0 12px auto; max-width: 82%; background:{SOFT_YELLOW}; border:1px solid #F5E6A3;
  border-radius: 14px; padding: 10px 14px; font-size: .95rem; color:{INK}; }}
.tip .why {{ color:{MUTED}; font-size:.9rem; }}

.stButton > button {{ border-radius: 999px !important; font-weight: 700 !important; }}
.stButton > button[kind="secondary"] {{ border-color: #CDEDE9 !important; color: {TIFFANY_DARK} !important; background:#FFFFFF !important; }}
.stButton > button[kind="secondary"]:hover {{ background:#E9F8F6 !important; }}
[data-testid="stExpander"] {{ border-radius: 14px !important; border-color:#E3F1EF !important; background:#FBFEFE; }}
[data-testid="stSidebar"] {{ background: #F3FBFA; }}
.summary {{ background:#FFFFFF; border:1.5px solid #D8F0ED; border-radius:18px; padding: 6px 20px 14px; }}

/* cara de aplicativo: sem barra lateral nem cabeçalho do Streamlit */
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stSidebarNav"] {{ display:none !important; }}
header[data-testid="stHeader"] {{ display:none !important; }}
footer {{ display:none !important; }}
.block-container {{ padding-top: 1.2rem !important; }}

/* barra de navegação no rodapé */
[data-testid="stBottom"] [data-testid="stButtonGroup"] {{ width:100%; }}
[data-testid="stBottom"] [data-testid="stButtonGroup"] > div {{ width:100%; display:flex; }}
[data-testid="stBottom"] [data-testid="stButtonGroup"] button {{ flex:1; border-radius:14px !important; font-weight:700; }}
.brand {{ display:flex; align-items:center; gap:10px; margin-bottom:6px; }}
.brand img {{ width:38px; height:38px; border-radius:10px; box-shadow:0 2px 8px rgba(33,65,74,.12); }}
.brand span {{ font-weight:800; font-size:1.15rem; color:{INK}; }}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def _fmt(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")


def hero(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="hero"><h1>{_fmt(title)}</h1><p>{_fmt(subtitle)}</p></div>', unsafe_allow_html=True)


def pill(text: str) -> None:
    st.markdown(f'<span class="pill">{_fmt(text)}</span>', unsafe_allow_html=True)


def ai_bubble(text: str, hidden: bool = False) -> None:
    body = "🔊 Texto escondido — ouça e tente entender" if hidden else _fmt(text)
    cls = "bubble hidden" if hidden else "bubble"
    st.markdown(f'<div class="msg ai"><div class="avatar">🧑‍🏫</div><div class="{cls}">{body}</div></div>',
                unsafe_allow_html=True)


def user_bubble(text: str) -> None:
    st.markdown(f'<div class="msg me"><div class="bubble">{_fmt(text)}</div></div>', unsafe_allow_html=True)


def correction(better: str, tip_pt: str) -> None:
    st.markdown(
        f'<div class="tip">✏️ <b>Mais natural:</b> {_fmt(better)}<br><span class="why">💡 {_fmt(tip_pt)}</span></div>',
        unsafe_allow_html=True,
    )


def brand() -> None:
    st.markdown('<div class="brand"><img src="app/static/logo-192.png" alt=""><span>English Practice</span></div>',
                unsafe_allow_html=True)


_HEAD_JS = """
export default function () {
  // No Streamlit Cloud o app roda num iframe dentro da página do Streamlit (que tem o ícone da coroa).
  // Ajustamos as duas: a nossa e a de fora (mesmo domínio), e vigiamos para o Streamlit não trocar de volta.
  const L = window.location, k = L.pathname.indexOf('/~/+/');
  const B = L.origin + (k >= 0 ? L.pathname.slice(0, k) + '/~/+/' : '/');
  const I = B + 'app/static/apple-touch-icon.png', F = B + 'app/static/favicon.png', T = 'English';
  function fix(d) {
    const h = d.head; if (!h) return;
    const link = (rel) => { let l = h.querySelector('link[rel="' + rel + '"]');
      if (!l) { l = d.createElement('link'); l.rel = rel; h.appendChild(l); } return l; };
    const meta = (n, v) => { let m = h.querySelector('meta[name="' + n + '"]');
      if (!m) { m = d.createElement('meta'); m.name = n; h.appendChild(m); } if (m.content !== v) m.content = v; };
    h.querySelectorAll('link[rel~="icon"]').forEach(l => { if (l.href !== F) { l.href = F; l.type = 'image/png'; } });
    if (!h.querySelector('link[rel~="icon"]')) { const l = link('icon'); l.href = F; l.type = 'image/png'; }
    h.querySelectorAll('link[rel="apple-touch-icon"],link[rel="apple-touch-icon-precomposed"]').forEach(l => {
      if (l.href !== I) l.href = I; if (l.getAttribute('sizes') !== '180x180') l.setAttribute('sizes', '180x180'); });
    if (!h.querySelector('link[rel="apple-touch-icon"]')) { const a = link('apple-touch-icon'); a.href = I; a.setAttribute('sizes', '180x180'); }
    h.querySelectorAll('link[rel="manifest"],link[rel="mask-icon"]').forEach(l => l.remove());  // manifesto do Streamlit = coroa
    meta('apple-mobile-web-app-title', T); meta('application-name', T); meta('theme-color', '#3FB8AF');
    meta('apple-mobile-web-app-capable', 'yes'); meta('mobile-web-app-capable', 'yes');
    meta('apple-mobile-web-app-status-bar-style', 'default');
    if (!d.getElementById('ep-sem-selo')) { const s = d.createElement('style'); s.id = 'ep-sem-selo';
      s.textContent = '[data-testid="manage-app-button"],[class*="viewerBadge"],[class*="_profileContainer"]{display:none!important}';
      h.appendChild(s); }
  }
  const docs = [document];
  try { if (window.parent && window.parent !== window && window.parent.document) docs.push(window.parent.document); } catch (e) {}
  docs.forEach(d => {
    try {
      fix(d);
      const W = d.defaultView;
      if (!W.__epIcon) { W.__epIcon = new W.MutationObserver(() => { try { fix(d); } catch (e) {} });
        W.__epIcon.observe(d.head, { subtree: true, childList: true, attributes: true }); }
    } catch (e) {}
  });
}
"""
_head = st.components.v2.component("english_head_tags", js=_HEAD_JS)


def install_app_icons() -> None:
    """Ícone e nome do app quando você salva na tela de início (iPhone) ou instala no Mac."""
    _head(key="head_tags")


# --- Temas imersivos (Londres para adultos, Espaço para o nível Criança) --------------------
# O fundo é uma foto fixa em camadas: a foto se mexe de leve (zoom lento + parallax com o
# mouse ou a inclinação do celular) e o conteúdo fica num painel de vidro por cima.
# Tudo é CSS; as imagens são WebP pequenos e só a do tema em uso é baixada.
THEMES = {
    "london": {
        "bg": "app/static/theme/lon_bg.webp", "bg_wide": "app/static/theme/lon_bg_wide.webp",
        "font": "Cormorant+Garamond:wght@600;700", "title_font": "'Cormorant Garamond', Georgia, serif",
        "panel": "rgba(13,20,36,.60)", "edge": "rgba(201,168,92,.55)", "text": "#F4ECDC", "muted": "#CBBFA6",
        "accent": "#C9A85C", "accent2": "#E6CD8E", "accent_ink": "#1B1408",
        "overlay": "linear-gradient(180deg, rgba(10,14,26,.10) 0%, rgba(10,14,26,.35) 45%, rgba(10,14,26,.70) 100%)",
    },
    "space": {
        "bg": "app/static/theme/space_bg.webp", "bg_wide": "app/static/theme/space_bg_wide.webp",
        "font": "Exo+2:wght@600;800", "title_font": "'Exo 2', 'Nunito', sans-serif",
        "panel": "rgba(10,12,38,.48)", "edge": "rgba(126,232,255,.35)", "text": "#EAF2FF", "muted": "#AFC0E8",
        "accent": "#38D6F5", "accent2": "#A78BFA", "accent_ink": "#061021",
        "overlay": "radial-gradient(120% 80% at 50% 0%, rgba(0,0,0,0) 0%, rgba(4,6,20,.35) 70%)",
    },
}


def theme_css(name: str) -> str:
    t = THEMES[name]
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family={t['font']}&display=swap');
.stApp {{ background:#05070F !important; }}
.stApp::before {{ content:''; position:fixed; inset:-6%; z-index:0; pointer-events:none;
  background:url('{t['bg']}') center/cover no-repeat;
  translate: calc(var(--px,0) * -14px) calc(var(--py,0) * -10px);
  animation: ep-kb 48s ease-in-out infinite alternate; }}
@media (min-aspect-ratio: 1/1) {{ .stApp::before {{ background-image:url('{t['bg_wide']}'); }} }}
.stApp::after {{ content:''; position:fixed; inset:0; z-index:0; pointer-events:none; background:{t['overlay']}; }}
@keyframes ep-kb {{ from {{ scale:1.02 }} to {{ scale:1.10 }} }}
@media (prefers-reduced-motion: reduce) {{ .stApp::before {{ animation:none; translate:none; }} }}
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] {{ background:transparent !important; position:relative; z-index:1; }}
.block-container {{ background:{t['panel']}; backdrop-filter: blur(10px) saturate(1.2); -webkit-backdrop-filter: blur(10px) saturate(1.2);
  border:1px solid {t['edge']}; border-radius:26px; margin-top:12px; margin-bottom:12px;
  padding:1.3rem 1.3rem 2rem !important; box-shadow:0 20px 60px rgba(0,0,0,.45); animation: ep-in .45s ease-out; }}
@keyframes ep-in {{ from {{ opacity:0; transform: translateY(10px) scale(.985) }} to {{ opacity:1; transform:none }} }}
.stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp span,
[data-testid="stCaptionContainer"], [data-testid="stMarkdownContainer"] {{ color:{t['text']}; }}
[data-testid="stCaptionContainer"] p {{ color:{t['muted']} !important; }}
.hero {{ background:transparent !important; border:none !important; padding:8px 2px 4px !important; }}
.hero h1 {{ font-family:{t['title_font']} !important; font-size:2.3rem !important; color:{t['text']} !important;
  text-shadow:0 2px 18px rgba(0,0,0,.55); letter-spacing:.01em; }}
.hero p {{ color:{t['muted']} !important; }}
.brand span {{ color:{t['text']} !important; font-family:{t['title_font']} !important; font-size:1.3rem !important; }}
.pill {{ background:rgba(255,255,255,.08) !important; color:{t['accent2']} !important; border-color:{t['edge']} !important; }}
/* botões, pílulas e abas */
.stButton > button[kind="secondary"], button[data-variant] {{
  background:rgba(255,255,255,.07) !important; color:{t['text']} !important; border:1px solid {t['edge']} !important;
  transition: transform .15s ease, background .2s ease; }}
.stButton > button[kind="secondary"] p, button[data-variant] p {{ color:{t['text']} !important; }}
.stButton > button:active, button[data-variant]:active {{ transform:scale(.96); }}
button[data-variant][aria-checked="true"], button[data-variant][data-selected="true"],
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] button {{
  background:linear-gradient(135deg, {t['accent2']}, {t['accent']}) !important; color:{t['accent_ink']} !important;
  border:none !important; box-shadow:0 6px 20px rgba(0,0,0,.35); }}
button[data-variant][aria-checked="true"] p, button[data-variant][data-selected="true"] p,
.stButton > button[kind="primary"] p, [data-testid="stFormSubmitButton"] button p {{ color:{t['accent_ink']} !important; }}
[data-testid="stTab"] p {{ color:{t['muted']} !important; }}
[data-testid="stTab"][aria-selected="true"] p {{ color:{t['accent2']} !important; }}
[data-testid="stExpander"], [data-testid="stVerticalBlockBorderWrapper"] {{ background:rgba(255,255,255,.05) !important; border-color:{t['edge']} !important; }}
[data-testid="stBottom"] {{ background:linear-gradient(180deg, rgba(0,0,0,0), rgba(5,7,15,.85) 40%) !important; }}
.summary {{ background:rgba(255,255,255,.06) !important; border-color:{t['edge']} !important; }}
.bubble, .tip, .tip *, .msg .bubble * {{ color:#21414A !important; }}
hr {{ border-color:{t['edge']} !important; }}
</style>"""


_PARALLAX_JS = """
export default function () {
  const W = window.parent && window.parent !== window ? window : window;
  if (W.__epPar) return; W.__epPar = 1;
  const root = document.documentElement;
  let tx = 0, ty = 0, x = 0, y = 0;
  const set = (a, b) => { tx = Math.max(-1, Math.min(1, a)); ty = Math.max(-1, Math.min(1, b)); };
  window.addEventListener('mousemove', e => set(e.clientX / innerWidth * 2 - 1, e.clientY / innerHeight * 2 - 1), { passive: true });
  window.addEventListener('deviceorientation', e => { if (e.gamma != null) set(e.gamma / 25, (e.beta - 45) / 25); }, { passive: true });
  (function tick() {   // suaviza o movimento; quase nada de CPU
    x += (tx - x) * .06; y += (ty - y) * .06;
    root.style.setProperty('--px', x.toFixed(3)); root.style.setProperty('--py', y.toFixed(3));
    requestAnimationFrame(tick);
  })();
}
"""
_parallax = st.components.v2.component("english_parallax", js=_PARALLAX_JS)


def apply_theme(name: str) -> None:
    """name: 'classic' (visual claro de antes), 'london' ou 'space'."""
    if name not in THEMES:
        return
    st.markdown(theme_css(name), unsafe_allow_html=True)
    _parallax(key="parallax")


# --- Cartões com foto (cenários do tema Londres) ---------------------------------------------
_CARDS_CSS = """
.sc { display:grid; grid-template-columns:repeat(2, 1fr); gap:10px; font-family:'Nunito',system-ui,sans-serif; }
.sc-c { position:relative; height:112px; border-radius:18px; overflow:hidden; cursor:pointer; border:1px solid rgba(201,168,92,.45);
  background-size:cover; background-position:center; box-shadow:0 8px 24px rgba(0,0,0,.35);
  transition: transform .35s cubic-bezier(.2,.8,.2,1), box-shadow .35s ease, filter .35s ease; }
.sc-c::after { content:''; position:absolute; inset:0; background:linear-gradient(180deg, rgba(0,0,0,0) 35%, rgba(5,8,18,.82)); }
.sc-c span { position:absolute; left:12px; bottom:10px; z-index:1; color:#F7F0E1; font-weight:800; font-size:15px;
  text-shadow:0 1px 6px rgba(0,0,0,.6); }
.sc-c:hover { transform:translateY(-2px); }
.sc-c.on { border:2px solid #E6CD8E; box-shadow:0 0 0 3px rgba(230,205,142,.25), 0 10px 28px rgba(0,0,0,.45); }
.sc-c.zoom { transform:scale(1.07); filter:brightness(1.15); z-index:2; }
.sc-c.wide { grid-column: span 2; }
"""
_CARDS_JS = """
export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  const old = parentElement.querySelector('.sc'); if (old) old.remove();
  const box = document.createElement('div'); box.className = 'sc';
  (data.items || []).forEach((it, i, arr) => {
    const c = document.createElement('div');
    c.className = 'sc-c' + (it.key === data.selected ? ' on' : '') + (arr.length % 2 && i === arr.length - 1 ? ' wide' : '');
    c.style.backgroundImage = `url('${it.img}')`;
    c.innerHTML = `<span>${it.label}</span>`;
    c.addEventListener('click', () => { c.classList.add('zoom'); setTimeout(() => setTriggerValue('pick', it.key), 260); });
    box.appendChild(c);
  });
  parentElement.appendChild(box);
}
"""
_cards = st.components.v2.component("english_scene_cards", css=_CARDS_CSS, js=_CARDS_JS)


def scene_cards(items: list[dict], selected: str, key: str):
    """items: [{'key','label','img'}]. Retorna a chave tocada (ou None)."""
    res = _cards(key=key, data={"items": items, "selected": selected}, on_pick_change=lambda: None)
    return getattr(res, "pick", None)
