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
