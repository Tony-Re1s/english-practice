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
