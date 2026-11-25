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
.vid-title {{ text-align:center; font-weight:800; font-size:1.05rem; line-height:1.3; }}
.vid-title small {{ display:block; font-weight:600; font-size:.8rem; opacity:.7; }}
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


def ai_bubble(text: str, hidden: bool = False, avatar: str = "🧑‍🏫") -> None:
    body = "🔊 Texto escondido — ouça e tente entender" if hidden else _fmt(text)
    cls = "bubble hidden" if hidden else "bubble"
    st.markdown(f'<div class="msg ai"><div class="avatar">{avatar}</div><div class="{cls}">{body}</div></div>',
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
  const M = B + 'app/static/manifest.json';
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
    // troca o manifesto do Streamlit (coroa) pelo nosso, que aponta para o nosso logo
    h.querySelectorAll('link[rel="mask-icon"]').forEach(l => l.remove());
    h.querySelectorAll('link[rel="manifest"]').forEach(l => { if (l.href !== M) l.remove(); });
    if (!h.querySelector('link[rel="manifest"]')) { const m = link('manifest'); m.href = M; }
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
        "btn_bg": "linear-gradient(180deg, #2C3A5E, #1E2945)", "btn_text": "#F4ECDC", "btn_edge": "#C9A85C",
        "btn_shadow": "#0B101E",
        "pri_bg": "linear-gradient(180deg, #E6CD8E, #C9A85C)", "pri_text": "#1B1408", "pri_shadow": "#6E5824",
        "pill_bg": "#1E2945", "pill_edge": "#C9A85C", "pill_on_bg": "linear-gradient(180deg, #E6CD8E, #C9A85C)",
        "pill_on_text": "#1B1408", "tab_bg": "#1E2945", "tab_text": "#F4ECDC",
        "tab_on_bg": "linear-gradient(180deg, #E6CD8E, #C9A85C)", "tab_on_text": "#1B1408", "mic": "#E6CD8E",
        "overlay": "linear-gradient(180deg, rgba(10,14,26,.10) 0%, rgba(10,14,26,.35) 45%, rgba(10,14,26,.70) 100%)",
    },
    "space": {
        "bg": "app/static/theme/space_bg.webp", "bg_wide": "app/static/theme/space_bg_wide.webp",
        "font": "Exo+2:wght@600;800", "title_font": "'Exo 2', 'Nunito', sans-serif",
        "panel": "rgba(10,12,38,.48)", "edge": "rgba(126,232,255,.35)", "text": "#EAF2FF", "muted": "#AFC0E8",
        "accent": "#38D6F5", "accent2": "#A78BFA", "accent_ink": "#061021",
        "radius": "22px", "btn_h": "54px",
        "btn_bg": "linear-gradient(180deg, #7C6CFF, #5B47E8)", "btn_text": "#FFFFFF", "btn_edge": "#B8AEFF",
        "btn_shadow": "#2E2380",
        "pri_bg": "linear-gradient(180deg, #FFE066, #FFB020)", "pri_text": "#2A1600", "pri_shadow": "#A86A00",
        "pill_bg": "#1C2A66", "pill_edge": "#5FE3FF", "pill_on_bg": "linear-gradient(180deg, #FFE066, #FFB020)",
        "pill_on_text": "#2A1600", "tab_on_bg": "linear-gradient(180deg, #FFE066, #FFB020)", "tab_on_text": "#2A1600",
        "tab_bg": "#1C2A66", "tab_text": "#EAF2FF", "mic": "#FFD23F",
        "extra_css": (".stButton button p, button[data-variant] p { font-weight:800 !important; font-size:1.05rem !important; } "
                      ".stButton button:active, button[data-variant]:active { animation: ep-pop .35s ease !important; } "
                      "@keyframes ep-pop { 0% { transform:scale(.9) } 55% { transform:scale(1.06) } 100% { transform:scale(1) } }"),
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
/* botões, pílulas e abas: cores sólidas e fortes, que aparecem bem no fundo escuro */
.stButton button[kind="secondary"], [data-testid="stPopover"] button, [data-testid="stLinkButton"] a,
[data-testid="stDownloadButton"] button {{
  background:{t['btn_bg']} !important; color:{t['btn_text']} !important; border:2px solid {t['btn_edge']} !important;
  box-shadow:0 5px 0 {t['btn_shadow']}, 0 8px 18px rgba(0,0,0,.35) !important;
  transition: transform .12s ease, box-shadow .12s ease, filter .2s ease; }}
.stButton button[kind="secondary"] *, [data-testid="stPopover"] button *, [data-testid="stLinkButton"] a *,
[data-testid="stDownloadButton"] button * {{ color:{t['btn_text']} !important; fill:{t['btn_text']} !important; }}
.stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button {{
  background:{t['pri_bg']} !important; color:{t['pri_text']} !important; border:none !important;
  box-shadow:0 5px 0 {t['pri_shadow']}, 0 8px 22px rgba(0,0,0,.4) !important; }}
.stButton button[kind="primary"] *, [data-testid="stFormSubmitButton"] button * {{ color:{t['pri_text']} !important; font-weight:800 !important; }}
button[data-variant] {{ background:{t['pill_bg']} !important; border:2px solid {t['pill_edge']} !important;
  box-shadow:0 4px 0 rgba(0,0,0,.45) !important; transition: transform .12s ease, box-shadow .12s ease; }}
button[data-variant] * {{ color:{t['btn_text']} !important; font-weight:700; }}
button[data-variant][aria-checked="true"], button[data-variant][data-selected="true"] {{
  background:{t['pill_on_bg']} !important; border-color:transparent !important; }}
button[data-variant][aria-checked="true"] *, button[data-variant][data-selected="true"] * {{ color:{t['pill_on_text']} !important; font-weight:800 !important; }}
.stButton button, button[data-variant], [data-testid="stFormSubmitButton"] button, [data-testid="stPopover"] button,
[data-testid="stLinkButton"] a, [data-testid="stDownloadButton"] button {{
  border-radius:{t.get('radius', '14px')} !important; min-height:{t.get('btn_h', '44px')}; -webkit-tap-highlight-color: transparent; }}
@media (hover:hover) {{ .stButton button:hover, button[data-variant]:hover, [data-testid="stFormSubmitButton"] button:hover,
  [data-testid="stPopover"] button:hover {{ transform:translateY(-2px); filter:brightness(1.12); }} }}
.stButton button:active, button[data-variant]:active, [data-testid="stFormSubmitButton"] button:active,
[data-testid="stPopover"] button:active {{
  transform:translateY(4px) scale(.98) !important; box-shadow:0 1px 0 rgba(0,0,0,.4) !important; }}
.stButton button:disabled {{ filter:grayscale(.5) brightness(.75); }}
.stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button {{ animation: ep-glow 2.6s ease-in-out infinite; }}
@keyframes ep-glow {{ 0%,100% {{ filter:brightness(1); }} 50% {{ filter:brightness(1.15) drop-shadow(0 0 10px {t['accent']}); }} }}
/* abas grandes, como botões */
[data-testid="stTabs"] [role="tablist"] {{ gap:8px; border:none !important; flex-wrap:wrap; }}
[data-testid="stTab"] {{ background:{t['tab_bg']} !important; border:2px solid {t['pill_edge']} !important;
  border-radius:{t.get('radius', '14px')} !important; padding:10px 16px !important; height:auto !important;
  box-shadow:0 4px 0 rgba(0,0,0,.45); transition: transform .12s ease; }}
[data-testid="stTab"] p {{ color:{t['tab_text']} !important; font-weight:800 !important; font-size:1.05rem !important; }}
[data-testid="stTab"][aria-selected="true"] {{ background:{t['tab_on_bg']} !important; border-color:transparent !important; }}
[data-testid="stTab"][aria-selected="true"] p {{ color:{t['tab_on_text']} !important; }}
[data-testid="stTab"]:active {{ transform:translateY(3px); }}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{ display:none !important; }}
/* janelas que abrem (loja, álbum, listas): fundo escuro, texto claro */
[data-testid="stPopoverBody"], [data-baseweb="popover"] > div, [data-baseweb="popover"] ul, [data-baseweb="menu"] {{
  background:#0E1430 !important; color:#F2F5FF !important; border:2px solid {t['pill_edge']} !important;
  border-radius:18px !important; }}
[data-testid="stPopoverBody"] *, [data-baseweb="popover"] li, [data-baseweb="popover"] li * {{ color:#F2F5FF !important; }}
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] {{ background:rgba(255,255,255,.12) !important; }}
[data-testid="stPopoverBody"] .stButton button[kind="secondary"] *, [data-testid="stPopoverBody"] [data-testid="stCaptionContainer"] p {{ color:{t['btn_text']} !important; }}
[data-testid="stPopoverBody"] [data-testid="stHorizontalBlock"] {{ flex-wrap:nowrap !important; gap:8px; }}
[data-testid="stPopoverBody"] [data-testid="stHorizontalBlock"] > div {{ min-width:0 !important; flex:1 1 0 !important; }}
[data-testid="stPopoverBody"] .stButton button p {{ font-size:.92rem !important; white-space:pre-line; }}
[data-testid="stPopover"] button p {{ font-weight:800 !important; font-size:1.05rem !important; }}
{t.get('extra_css', '')}
/* microfone em destaque */
[data-testid="stAudioInput"] {{ border:3px solid {t['mic']} !important; border-radius:22px !important;
  background:rgba(255,255,255,.10) !important; animation: ep-mic 1.8s ease-in-out infinite; padding:8px 6px; min-height:64px; }}
[data-testid="stAudioInput"] button {{ transform:scale(1.6); color:{t['mic']} !important; }}
[data-testid="stAudioInput"] button svg, [data-testid="stAudioInput"] button * {{ fill:{t['mic']} !important; color:{t['mic']} !important; }}
@keyframes ep-mic {{ 0%,100% {{ box-shadow:0 0 0 0 {t['mic']}88; }} 60% {{ box-shadow:0 0 0 12px {t['mic']}00, 0 0 26px {t['mic']}66; }} }}
@media (prefers-reduced-motion: reduce) {{ .stButton button, [data-testid="stAudioInput"] {{ animation:none !important; }} }}
[data-testid="stExpander"], [data-testid="stVerticalBlockBorderWrapper"] {{ background:rgba(255,255,255,.05) !important; border-color:{t['edge']} !important; }}
[data-testid="stBottom"] {{ background:linear-gradient(180deg, rgba(0,0,0,0), rgba(5,7,15,.85) 40%) !important; }}
.summary {{ background:rgba(255,255,255,.06) !important; border-color:{t['edge']} !important; }}
.bubble, .tip, .tip *, .msg .bubble * {{ color:#21414A !important; }}
hr {{ border-color:{t['edge']} !important; }}
.vid-title {{ color:{t['text']}; }}
[data-testid="stMainBlockContainer"], .block-container {{ margin-bottom:110px !important; }}
/* elementos invisíveis (estilos, sons, parallax) não ocupam espaço nem deixam buraco no topo */
.st-key-head_tags, .st-key-parallax, .st-key-click_sounds,
[data-testid="stElementContainer"]:has(> .stMarkdown [data-testid="stMarkdownContainer"] > style:only-child) {{
  display:none !important; }}
/* celular e tablet */
@media (max-width: 640px) {{ .block-container {{ padding:1rem .85rem 1.6rem !important; border-radius:20px; margin-top:6px; }}
  .hero h1 {{ font-size:1.8rem !important; }} }}
@media (min-width: 641px) and (max-width: 1024px) {{ .block-container {{ max-width: 720px; }} }}
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

# Sons de toque (modo infantil): tudo sintetizado com Web Audio, sem baixar arquivos.
_CLICK_JS = """
export default function (component) {
  const on = !!(component.data && component.data.on);
  window.__epSfxOn = on;
  if (window.__epSfx) return;
  window.__epSfx = true;
  let ctx = null;
  const tone = (f1, f2, dur, type = 'sine', vol = .16, delay = 0) => {
    try {
      ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
      if (ctx.state === 'suspended') ctx.resume();
      const t = ctx.currentTime + delay, o = ctx.createOscillator(), g = ctx.createGain();
      o.type = type; o.frequency.setValueAtTime(f1, t); o.frequency.exponentialRampToValueAtTime(f2, t + dur);
      g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + .012);
      g.gain.exponentialRampToValueAtTime(.0001, t + dur);
      o.connect(g); g.connect(ctx.destination); o.start(t); o.stop(t + dur + .02);
    } catch (e) {}
  };
  const SOUNDS = {
    tap:    () => tone(660, 990, .09, 'triangle'),
    go:     () => { tone(523, 784, .12, 'triangle'); tone(784, 1175, .16, 'triangle', .14, .1); },
    pick:   () => tone(880, 1320, .07, 'square', .07),
    tab:    () => { tone(392, 587, .1, 'sine'); tone(587, 880, .12, 'sine', .12, .07); },
    open:   () => tone(300, 1200, .22, 'sawtooth', .06),
    back:   () => tone(700, 350, .14, 'triangle'),
  };
  document.addEventListener('pointerdown', (ev) => {
    if (!window.__epSfxOn) return;
    const el = ev.target.closest('button, [role="tab"], a[data-testid], [data-testid="stLinkButton"] a');
    if (!el || el.disabled) return;
    const txt = (el.innerText || '').trim();
    let k = 'tap';
    if (el.getAttribute('role') === 'tab') k = 'tab';
    else if (el.closest('[data-testid="stPopover"]')) k = 'open';
    else if (el.hasAttribute('data-variant')) k = 'pick';
    else if (el.getAttribute('kind') === 'primary' || el.closest('[data-testid="stFormSubmitButton"]')) k = 'go';
    else if (/^(🛰️|⬅|◀)|Voltar/.test(txt)) k = 'back';
    SOUNDS[k]();
  }, true);
}
"""
_clicks = st.components.v2.component("english_click_sounds", js=_CLICK_JS)


def apply_theme(name: str) -> None:
    """name: 'classic' (visual claro de antes), 'london' ou 'space'."""
    if name not in THEMES:
        return
    st.markdown(theme_css(name), unsafe_allow_html=True)
    _parallax(key="parallax")
    _clicks(key="click_sounds", data={"on": name == "space"})


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


# --- Cartões ilustrados do modo infantil (menu das abas e escolha de galáxia) ----------------
_TILES_CSS = """
.kt { display:grid; grid-template-columns:repeat(var(--n,3), 1fr); gap:clamp(6px, 2vw, 14px); font-family:'Nunito',system-ui,sans-serif; }
.kt-c { position:relative; display:flex; flex-direction:column; align-items:center; justify-content:flex-end; cursor:pointer;
  height:clamp(92px, 26vw, 150px); padding:6px 4px 8px; border-radius:20px; border:2px solid #5FE3FF;
  background:radial-gradient(120% 90% at 50% 20%, #2B3C8F 0%, #151E52 70%); box-shadow:0 5px 0 #0A0F2E, 0 10px 20px rgba(0,0,0,.35);
  transition: transform .15s ease, box-shadow .15s ease, filter .2s ease; -webkit-tap-highlight-color:transparent; overflow:hidden; }
.kt-c img { flex:1; min-height:0; max-width:92%; object-fit:contain; filter:drop-shadow(0 6px 10px rgba(0,0,0,.5));
  transition: transform .3s cubic-bezier(.2,.8,.2,1); }
.kt-c span { color:#FFFFFF; font-weight:900; font-size:clamp(13px, 3.6vw, 18px); line-height:1.1; text-align:center;
  text-shadow:0 2px 6px rgba(0,0,0,.6); margin-top:4px; }
.kt-c.on { background:linear-gradient(180deg, #FFE066, #FFB020); border-color:#FFF3B0; box-shadow:0 5px 0 #A86A00, 0 0 22px rgba(255,208,64,.55); }
.kt-c.on span { color:#2A1600; text-shadow:none; }
.kt-c.on img { transform:scale(1.08) rotate(-4deg); }
.kt-c.lock { filter:grayscale(.7) brightness(.6); }
.kt-c:active { transform:translateY(4px) scale(.97); box-shadow:0 1px 0 #0A0F2E; }
@media (hover:hover) { .kt-c:hover img { transform:scale(1.12) rotate(4deg); } }
@media (min-width: 641px) { .kt-c { height:118px; } }
.kt.sm .kt-c { flex-direction:row; justify-content:center; gap:6px; height:clamp(56px, 15vw, 72px); padding:6px 8px; }
.kt.sm .kt-c img { flex:0 0 auto; height:78%; max-width:32%; }
.kt.sm .kt-c span { margin:0; font-size:clamp(11px, 3vw, 16px); text-align:left; overflow-wrap:anywhere; min-width:0; }
.kt.sm .kt-c { gap:4px !important; padding:6px 5px !important; }
"""
_TILES_JS = """
export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  const old = parentElement.querySelector('.kt'); if (old) old.remove();
  const box = document.createElement('div'); box.className = 'kt' + (data.small ? ' sm' : '');
  box.style.setProperty('--n', (data.items || []).length);
  (data.items || []).forEach((it) => {
    const c = document.createElement('div');
    c.className = 'kt-c' + (it.key === data.selected ? ' on' : '') + (it.lock ? ' lock' : '');
    c.innerHTML = `<img src="${it.img}" alt=""><span>${it.label}</span>`;
    c.addEventListener('click', () => {
      try { const A = window.AudioContext || window.webkitAudioContext; const x = window.__epTileCtx || (window.__epTileCtx = new A());
        const o = x.createOscillator(), g = x.createGain(), t = x.currentTime; o.type = 'triangle';
        o.frequency.setValueAtTime(520, t); o.frequency.exponentialRampToValueAtTime(1040, t + .12);
        g.gain.setValueAtTime(.15, t); g.gain.exponentialRampToValueAtTime(.0001, t + .16); o.connect(g); g.connect(x.destination);
        o.start(t); o.stop(t + .18); } catch (e) {}
      if (it.key !== data.selected) setTriggerValue('pick', it.key);
    });
    box.appendChild(c);
  });
  parentElement.appendChild(box);
}
"""
_tiles = st.components.v2.component("english_kid_tiles", css=_TILES_CSS, js=_TILES_JS)


def kid_tiles(items: list[dict], selected: str, key: str, small: bool = False):
    """items: [{'key','label','img', 'lock'?}]. Cartões ilustrados lado a lado; retorna a chave tocada (ou None)."""
    res = _tiles(key=key, data={"items": items, "selected": selected, "small": small}, on_pick_change=lambda: None)
    return getattr(res, "pick", None)


# --- Álbum de figurinhas (modo infantil): toca para virar e ouvir a curiosidade em inglês -----
_ALBUM_CSS = """
.al { font-family:'Nunito',system-ui,sans-serif; color:#F2F5FF; }
.al-top { display:flex; align-items:center; gap:10px; margin:2px 0 12px; }
.al-top b { font-size:clamp(18px, 5vw, 24px); font-weight:900; }
.al-bar { flex:1; height:12px; border-radius:99px; background:rgba(255,255,255,.12); overflow:hidden; }
.al-bar i { display:block; height:100%; background:linear-gradient(90deg, #FFE066, #FFB020); border-radius:99px; }
.al h4 { margin:16px 4px 8px; font-size:15px; font-weight:900; color:#AFC0E8; letter-spacing:.04em; text-transform:uppercase; }
.al-g { display:grid; grid-template-columns:repeat(auto-fill, minmax(clamp(96px, 28vw, 140px), 1fr)); gap:10px; }
.st { perspective:800px; height:clamp(168px, 46vw, 210px); cursor:pointer; -webkit-tap-highlight-color:transparent; }
.st-in { position:relative; width:100%; height:100%; transition:transform .6s cubic-bezier(.2,.8,.2,1); transform-style:preserve-3d; }
.st.flip .st-in { transform:rotateY(180deg); }
.st-f, .st-b { position:absolute; inset:0; backface-visibility:hidden; -webkit-backface-visibility:hidden; border-radius:18px;
  display:flex; flex-direction:column; align-items:center; padding:8px 6px; box-shadow:0 5px 0 #0A0F2E, 0 10px 20px rgba(0,0,0,.35); }
.st-f { justify-content:flex-end; border:3px solid #FFE066;
  background:radial-gradient(110% 80% at 50% 25%, #3B4FB8 0%, #18215A 75%); }
.st-f img, .st-f .emo { flex:1; min-height:0; max-width:95%; object-fit:contain; filter:drop-shadow(0 6px 10px rgba(0,0,0,.5)); }
.st-f .emo { font-size:clamp(48px, 14vw, 72px); display:flex; align-items:center; }
.st-f span { font-weight:900; font-size:clamp(12px, 3.4vw, 15px); text-align:center; line-height:1.1; margin-top:4px; }
.st-f small { font-size:11px; color:#FFE066; font-weight:800; }
.st-b { transform:rotateY(180deg); background:linear-gradient(180deg, #FFF6D6, #FFE8A3); color:#2A1600; justify-content:space-between;
  border:3px solid #FFB020; text-align:center; overflow:hidden; }
.st-b p { margin:0; font-size:clamp(10.5px, 2.9vw, 12.5px); line-height:1.25; }
.st-b p.en { font-weight:800; color:#3A2A8A; }
.st-b button { border:none; border-radius:99px; padding:5px 12px; font-weight:900; font-size:13px; cursor:pointer;
  background:#5B47E8; color:#fff; box-shadow:0 3px 0 #2E2380; }
.st.lock .st-f { border:3px dashed rgba(255,255,255,.25); background:#11173D; }
.st.lock .st-f img, .st.lock .st-f .emo { filter:brightness(0) opacity(.35); }
.st.lock .st-f span { color:#8A97C2; }
.st.lock .st-f small { color:#AFC0E8; font-weight:700; }
.st.new .st-f { animation: st-new 1.4s ease-in-out 3; }
@keyframes st-new { 50% { transform:scale(1.06) rotate(-2deg); box-shadow:0 0 26px #FFE066; } }
"""
_ALBUM_JS = """
export default function (component) {
  const { data, parentElement } = component;
  const old = parentElement.querySelector('.al'); if (old) old.remove();
  const items = data.items || [];
  const got = items.filter(i => i.got).length;
  const root = document.createElement('div'); root.className = 'al';
  root.innerHTML = `<div class="al-top"><b>📒 ${got} de ${items.length}</b><div class="al-bar"><i style="width:${Math.round(100*got/Math.max(1,items.length))}%"></i></div></div>`;
  const say = (t) => { try { speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(t); u.lang = 'en-US'; u.rate = .85; u.pitch = 1.15;
    const v = speechSynthesis.getVoices().find(v => /en-US/.test(v.lang) && /(Samantha|Ava|Aria|Jenny|Google US)/.test(v.name));
    if (v) u.voice = v; speechSynthesis.speak(u); } catch (e) {} };
  const seen = JSON.parse((() => { try { return localStorage.getItem('ep_album_seen') || '[]'; } catch (e) { return '[]'; } })());
  let group = null, grid = null;
  items.forEach((it) => {
    if (it.group !== group) { group = it.group; const h = document.createElement('h4'); h.textContent = group; root.appendChild(h);
      grid = document.createElement('div'); grid.className = 'al-g'; root.appendChild(grid); }
    const c = document.createElement('div');
    c.className = 'st' + (it.got ? '' : ' lock') + (it.got && !seen.includes(it.key) ? ' new' : '');
    const pic = it.img ? `<img src="${it.img}" alt="">` : `<div class="emo">${it.emoji}</div>`;
    c.innerHTML = `<div class="st-in"><div class="st-f">${pic}<span>${it.got ? it.en : '???'}</span><small>${it.got ? it.pt : '🔒 ' + it.how}</small></div>
      <div class="st-b"><p class="en">${it.fact_en}</p><p>${it.fact_pt}</p><button>🔊 Ouvir</button></div></div>`;
    c.addEventListener('click', (ev) => {
      if (!it.got) { c.animate([{transform:'translateX(0)'},{transform:'translateX(-6px)'},{transform:'translateX(6px)'},{transform:'translateX(0)'}], {duration:300}); return; }
      if (ev.target.tagName === 'BUTTON') { ev.stopPropagation(); say(it.fact_en); return; }
      c.classList.toggle('flip'); c.classList.remove('new');
      if (c.classList.contains('flip')) { say(it.en + '! ' + it.fact_en);
        if (!seen.includes(it.key)) { seen.push(it.key); try { localStorage.setItem('ep_album_seen', JSON.stringify(seen)); } catch (e) {} } }
    });
    grid.appendChild(c);
  });
  parentElement.appendChild(root);
}
"""
_album = st.components.v2.component("english_album", css=_ALBUM_CSS, js=_ALBUM_JS)


def album_grid(items: list[dict], key: str = "album") -> None:
    _album(key=key, data={"items": items})


def dive_bg(url: str, surface: bool = True) -> None:
    """Fundo de "dentro do planeta": entra com um zoom de mergulho e depois segue com o movimento lento."""
    bg = (f"url('{url}') center/cover no-repeat" if surface else
          f"url('{url}') center 78%/95% auto no-repeat, url('{THEMES['space']['bg']}') center/cover no-repeat")
    st.markdown(f"""<style>
.stApp::before {{ background: {bg} !important; background-color:#05070F !important;
  animation: ep-dive 1.2s cubic-bezier(.2,.8,.2,1), ep-kb 48s 1.2s ease-in-out infinite alternate !important; }}
@keyframes ep-dive {{ from {{ scale:2.6; filter: blur(12px) brightness(1.8) }} to {{ scale:1.02; filter:none }} }}
.stApp::after {{ background: linear-gradient(180deg, rgba(3,4,14,.55) 0%, rgba(3,4,14,.15) 35%, rgba(3,4,14,.55) 100%) !important; }}
.block-container {{ background: rgba(8,10,32,.30) !important; }}
</style>""", unsafe_allow_html=True)


# --- Vídeo do YouTube com legenda ligada/desligada --------------------------------------------
_YT_JS = """
export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  const src = `https://www.youtube-nocookie.com/embed/${data.id}?rel=0&modestbranding=1&playsinline=1&hl=en&enablejsapi=1`
            + `&origin=${encodeURIComponent(location.origin)}` + (data.autoplay ? '&autoplay=1' : '')
            + (data.cc ? '&cc_load_policy=1&cc_lang_pref=en' : '&cc_load_policy=0');
  let box = parentElement.querySelector('.yt');
  if (box && box.dataset.src === src) return;
  if (box) box.remove();
  box = document.createElement('div'); box.className = 'yt'; box.dataset.src = src;
  box.innerHTML = `<iframe src="${src}" title="Vídeo" allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
    allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>`;
  parentElement.appendChild(box);
  const frame = box.querySelector('iframe');
  // pede ao YouTube para avisar quando o vídeo termina (para tocar o próximo em sequência)
  frame.addEventListener('load', () => {
    const hello = () => frame.contentWindow && frame.contentWindow.postMessage(JSON.stringify({ event: 'listening', id: data.id }), '*');
    hello(); setTimeout(hello, 1000);
  });
  if (window.__ytListener) window.removeEventListener('message', window.__ytListener);
  window.__ytListener = (ev) => {
    if (!/youtube/.test(ev.origin || '')) return;
    let m; try { m = typeof ev.data === 'string' ? JSON.parse(ev.data) : ev.data; } catch (e) { return; }
    const st = m && m.info && m.info.playerState;
    if (st === 0 && box.isConnected && !box.dataset.ended) { box.dataset.ended = '1'; setTriggerValue('ended', data.id); }
  };
  window.addEventListener('message', window.__ytListener);
}
"""
_YT_CSS = """
.yt { position:relative; width:100%; aspect-ratio:16/9; border-radius:16px; overflow:hidden; background:#000;
  box-shadow:0 10px 30px rgba(0,0,0,.35); }
.yt iframe { position:absolute; inset:0; width:100%; height:100%; border:0; }
"""
_yt = st.components.v2.component("english_youtube", css=_YT_CSS, js=_YT_JS)


def youtube(video_id: str, captions: bool = True, autoplay: bool = False):
    """Mostra o vídeo. Retorna o id do vídeo quando ele termina (para tocar o próximo)."""
    res = _yt(key="yt_player", data={"id": video_id, "cc": bool(captions), "autoplay": bool(autoplay)},
              on_ended_change=lambda: None)
    return getattr(res, "ended", None)


# --- Resumo da conversa em PDF ---------------------------------------------------------------
def _latin(text: str) -> str:
    import re
    text = re.sub(r"[*_#`>]", "", text or "")
    return text.encode("latin-1", "ignore").decode("latin-1")


def summary_pdf(title: str, summary: str, transcript: str) -> bytes:
    from fpdf import FPDF
    pdf = FPDF()
    pdf.set_auto_page_break(True, 15)
    _mc = pdf.multi_cell
    pdf.multi_cell = lambda w, h, txt: _mc(w, h, txt or " ", new_x="LMARGIN", new_y="NEXT")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 9, _latin("Sessão de inglês"))
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, _latin(title))
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 13)
    pdf.multi_cell(0, 8, "Resumo")
    pdf.set_font("Helvetica", "", 11)
    for line in _latin(summary).splitlines():
        pdf.multi_cell(0, 6, line)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.multi_cell(0, 8, _latin("Transcrição"))
    pdf.set_font("Helvetica", "", 10)
    for line in _latin(transcript).splitlines():
        pdf.multi_cell(0, 5.5, line)
    return bytes(pdf.output())


# --- Tela de login (tema Londres) ------------------------------------------------------------
_G_SVG = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'>"
          "<path fill='%23FFC107' d='M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z'/>"
          "<path fill='%23FF3D00' d='M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z'/>"
          "<path fill='%234CAF50' d='M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z'/>"
          "<path fill='%231976D2' d='M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z'/></svg>")


def login_screen(title: str, subtitle: str, restricted: bool = False) -> None:
    apply_theme("london")
    feats = "" if restricted else """
      <div class="lg-feats"><span>🎙️ Conversa por voz</span><span>📚 Trilhas por nível</span>
      <span>🎬 Vídeos com perguntas</span><span>🚀 Modo infantil</span></div>"""
    st.markdown(f"""<style>
.lg {{ text-align:center; padding:28px 6px 10px; animation: ep-in .6s ease-out; }}
.lg img {{ width:88px; height:88px; border-radius:24px; box-shadow:0 12px 34px rgba(0,0,0,.45); }}
.lg h1 {{ font-family:'Cormorant Garamond', Georgia, serif !important; font-size:2.6rem !important; margin:14px 0 2px !important;
  color:#F4ECDC !important; text-shadow:0 2px 18px rgba(0,0,0,.6); }}
.lg .sub {{ color:#E6CD8E; font-family:'Cormorant Garamond', Georgia, serif; font-size:1.25rem; font-style:italic; margin-bottom:6px; }}
.lg p {{ color:#CBBFA6 !important; max-width:430px; margin:6px auto 0; }}
.lg-feats {{ display:flex; flex-wrap:wrap; justify-content:center; gap:8px; margin:18px 0 6px; }}
.lg-feats span {{ font-size:.85rem; font-weight:700; color:#F4ECDC; padding:6px 12px; border-radius:999px;
  border:1px solid rgba(201,168,92,.55); background:rgba(255,255,255,.06); }}
.st-key-login_btn button {{ background:#FFFFFF !important; color:#1F1F1F !important; border:none !important;
  min-height:52px; border-radius:14px !important; box-shadow:0 10px 28px rgba(0,0,0,.4) !important; }}
.st-key-login_btn button p {{ color:#1F1F1F !important; font-weight:800 !important; font-size:1.05rem !important; }}
.st-key-login_btn button::before {{ content:''; width:22px; height:22px; margin-right:10px;
  background:url("{_G_SVG}") center/contain no-repeat; }}
.lg-foot {{ text-align:center; color:#CBBFA6; font-size:.8rem; margin-top:14px; opacity:.8; }}
</style>
<div class="lg"><img src="app/static/logo-192.png" alt="">
  <h1>{title}</h1><div class="sub">Speak. Learn. Grow.</div><p>{subtitle}</p>{feats}</div>""", unsafe_allow_html=True)
