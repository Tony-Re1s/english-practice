"""Modo ao vivo (chamada de voz) com o Gemini Live — só a chave do Gemini, nunca a OpenAI.

O Python cria um token temporário (a chave verdadeira nunca vai para o navegador).
O navegador abre a chamada direto com o Gemini: manda o microfone em PCM 16 kHz e toca a resposta em PCM 24 kHz.
Ao encerrar (botão, tempo do dia esgotado ou erro), devolve a transcrição e os segundos usados.
"""

import datetime as dt

import streamlit as st

from config import LIVE_MODEL


def create_token(gemini_key: str) -> str:
    from google import genai

    client = genai.Client(api_key=gemini_key, http_options={"api_version": "v1alpha"})
    now = dt.datetime.now(tz=dt.timezone.utc)
    token = client.auth_tokens.create(config={
        "uses": 3,  # permite tentar as duas versões da API se a primeira recusar
        "expire_time": now + dt.timedelta(minutes=30),
        "new_session_expire_time": now + dt.timedelta(minutes=10),
    })
    return token.name


CSS = """
.lv { display:flex; flex-direction:column; align-items:center; gap:12px; padding:18px 6px 8px; font-family:'Nunito',system-ui,sans-serif; }
.lv-btn { width:120px; height:120px; border-radius:50%; border:none; cursor:pointer; font-size:46px; color:#fff;
  background: radial-gradient(circle at 30% 30%, #A8E6E0, #3FB8AF 70%); box-shadow:0 10px 28px rgba(63,184,175,.35); }
.lv[data-state=live] .lv-btn { background: radial-gradient(circle at 30% 30%, #FFD6D6, #F07B7B 75%); animation: lv-p 1.6s ease-in-out infinite; }
.lv[data-state=connecting] .lv-btn { background: radial-gradient(circle at 30% 30%, #FFF3B8, #F4D35E 75%); }
.lv-status { font-weight:800; color:#21414A; font-size:16px; text-align:center; }
.lv-hint { font-size:13px; color:#5D7A82; text-align:center; max-width:340px; }
.lv-bar { width:100%; max-width:360px; height:10px; background:#EAF6F5; border-radius:99px; overflow:hidden; }
.lv-fill { height:100%; width:0; background:linear-gradient(90deg,#81D8D0,#3FB8AF); transition:width .5s; }
.lv-time { font-size:12.5px; color:#5D7A82; }
.lv-cap { width:100%; max-width:520px; font-size:14px; color:#21414A; background:#FBFEFE; border:1px solid #E3F1EF;
  border-radius:14px; padding:10px 12px; min-height:44px; max-height:160px; overflow:auto; }
.lv-cap .me { color:#2F6F9F; } .lv-cap .ai { color:#139C94; }
@keyframes lv-p { 0%,100% { box-shadow:0 0 0 0 rgba(240,123,123,.45) } 50% { box-shadow:0 0 0 18px rgba(240,123,123,0) } }
"""

JS = r"""
const IN_RATE = 16000, OUT_RATE = 24000;

function fmt(s) { s = Math.max(0, Math.floor(s)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); }
function b64FromBytes(bytes) { let bin = ''; for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000)); return btoa(bin); }
function bytesFromB64(b64) { const bin = atob(b64); const out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; }

export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  const root = parentElement;
  const d = data || {};
  let S = root.__lv;
  if (!S || S.sessionKey !== d.session_key) {
    S = root.__lv = { state: 'idle', sessionKey: d.session_key, transcript: [], seconds: 0, sent: false };
    const old = root.querySelector('.lv'); if (old) old.remove();   // não apaga o <style> do componente
    const w = document.createElement('div'); w.className = 'lv';
    w.innerHTML = '<button class="lv-btn" type="button">📞</button><div class="lv-status"></div><div class="lv-hint"></div>' +
                  '<div class="lv-bar"><div class="lv-fill"></div></div><div class="lv-time"></div><div class="lv-cap"></div>';
    root.appendChild(w);
    S.w = w; S.btn = w.querySelector('.lv-btn'); S.status = w.querySelector('.lv-status'); S.hint = w.querySelector('.lv-hint');
    S.fill = w.querySelector('.lv-fill'); S.time = w.querySelector('.lv-time'); S.cap = w.querySelector('.lv-cap');
    S.btn.addEventListener('click', () => (S.state === 'idle' ? start(S) : finish(S, 'encerrado')));
    S.watch = setInterval(() => { if (!S.w.isConnected) { cleanup(S); clearInterval(S.watch); } }, 700);
    setUi(S, 'idle');
  }
  S.d = d; S.send = setTriggerValue;
  updateTime(S);
}

function setUi(S, st, msg) {
  S.state = st; S.w.dataset.state = st;
  const t = {
    idle: ['📞', 'Toque para começar a chamada', 'Conversa ao vivo, sem apertar nada. Use fone de ouvido para não dar eco.'],
    connecting: ['⏳', 'Conectando…', ''],
    live: ['⏹️', 'Ao vivo — pode falar', 'Toque para encerrar. Você pode interromper a parceira a qualquer momento.'],
    ended: ['✅', 'Chamada encerrada', msg || ''],
    error: ['⚠️', 'Não deu para usar o modo ao vivo', msg || ''],
  }[st];
  S.btn.textContent = t[0]; S.status.textContent = t[1]; S.hint.textContent = t[2];
  S.btn.disabled = (st === 'connecting' || st === 'ended' || st === 'error');
}

function updateTime(S) {
  const used = (S.d.used_seconds || 0) + S.seconds, max = S.d.max_seconds || 600;
  S.fill.style.width = Math.min(100, used / max * 100).toFixed(1) + '%';
  S.time.textContent = fmt(used) + ' de ' + fmt(max) + ' hoje';
}

function addCaption(S, role, text) {
  if (!text) return;
  const last = S.transcript[S.transcript.length - 1];
  if (last && last.role === role) last.text += text; else S.transcript.push({ role, text });
  S.cap.innerHTML = S.transcript.slice(-6).map(t => '<div class="' + (t.role === 'user' ? 'me' : 'ai') + '">' +
    (t.role === 'user' ? '🙋 ' : '🧑‍🏫 ') + t.text.replace(/[<>&]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c])) + '</div>').join('');
  S.cap.scrollTop = S.cap.scrollHeight;
}

async function start(S) {
  setUi(S, 'connecting');
  try {
    S.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
  } catch (e) { setUi(S, 'error', 'Permita o microfone no navegador e tente de novo.'); return; }
  const Ctx = window.AudioContext || window.webkitAudioContext;
  S.ctx = new Ctx(); await S.ctx.resume();
  S.playHead = 0; S.sources = [];
  S.versions = (S.d.versions || ['v1alpha', 'v1beta']).slice();
  connect(S);
}

function connect(S) {
  const ver = S.versions.shift();
  const url = 'wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.' + ver +
              '.GenerativeService.BidiGenerateContentConstrained?access_token=' + encodeURIComponent(S.d.token);
  S.ready = false;
  const ws = new WebSocket(url); S.ws = ws;
  ws.onopen = () => ws.send(JSON.stringify({ setup: {
    model: 'models/' + S.d.model,
    generationConfig: { responseModalities: ['AUDIO'] },
    systemInstruction: { parts: [{ text: S.d.system }] },
    inputAudioTranscription: {}, outputAudioTranscription: {},
  } }));
  ws.onmessage = async (ev) => {
    let msg; try { msg = JSON.parse(typeof ev.data === 'string' ? ev.data : await ev.data.text()); } catch (e) { return; }
    if (msg.setupComplete) { S.ready = true; onReady(S); return; }
    const sc = msg.serverContent;
    if (sc) {
      if (sc.interrupted) stopPlayback(S);
      if (sc.inputTranscription && sc.inputTranscription.text) addCaption(S, 'user', sc.inputTranscription.text);
      if (sc.outputTranscription && sc.outputTranscription.text) addCaption(S, 'assistant', sc.outputTranscription.text);
      const parts = (sc.modelTurn && sc.modelTurn.parts) || [];
      for (const p of parts) if (p.inlineData && p.inlineData.data) play(S, p.inlineData.data);
    }
    if (msg.goAway) setTimeout(() => finish(S, 'tempo da sessão'), 1500);
  };
  ws.onclose = (ev) => {
    const reason = (ev.reason || '') + ' (código ' + ev.code + ')';
    if (S.state === 'ended' || S.state === 'error') return;
    if (!S.ready && S.versions.length) { connect(S); return; }   // tenta a outra versão da API
    const quota = /quota|exhaust|resource|limit|429/i.test(ev.reason || '');
    finish(S, S.ready ? 'conexão encerrada' : 'erro', quota ? 'cota' : (S.ready ? '' : reason));
  };
  ws.onerror = () => {};
}

function onReady(S) {
  setUi(S, 'live');
  S.t0 = performance.now();
  // começa a conversa: a parceira cumprimenta primeiro
  S.ws.send(JSON.stringify({ clientContent: { turns: [{ role: 'user', parts: [{ text: '(The call starts now. Greet me and ask your first question.)' }] }], turnComplete: true } }));
  const src = S.ctx.createMediaStreamSource(S.stream);
  S.proc = S.ctx.createScriptProcessor(4096, 1, 1);
  S.mute = S.ctx.createGain(); S.mute.gain.value = 0;
  src.connect(S.proc); S.proc.connect(S.mute); S.mute.connect(S.ctx.destination);
  const ratio = S.ctx.sampleRate / IN_RATE;
  S.proc.onaudioprocess = (e) => {
    if (!S.ws || S.ws.readyState !== 1) return;
    const inp = e.inputBuffer.getChannelData(0);
    const n = Math.floor(inp.length / ratio), pcm = new Int16Array(n);
    for (let i = 0; i < n; i++) {
      const a = Math.floor(i * ratio), b = Math.min(inp.length, Math.floor((i + 1) * ratio));
      let s = 0; for (let j = a; j < b; j++) s += inp[j];
      const v = Math.max(-1, Math.min(1, s / Math.max(1, b - a)));
      pcm[i] = v < 0 ? v * 0x8000 : v * 0x7fff;
    }
    S.ws.send(JSON.stringify({ realtimeInput: { audio: { mimeType: 'audio/pcm;rate=16000', data: b64FromBytes(new Uint8Array(pcm.buffer)) } } }));
  };
  S.tick = setInterval(() => {
    S.seconds = (performance.now() - S.t0) / 1000;
    updateTime(S);
    const left = Math.min((S.d.max_seconds || 600) - (S.d.used_seconds || 0), S.d.session_max_seconds || 840) - S.seconds;
    if (left <= 0) finish(S, 'limite de tempo de hoje');
  }, 500);
}

function play(S, b64) {
  const bytes = bytesFromB64(b64);
  const pcm = new Int16Array(bytes.buffer, bytes.byteOffset, Math.floor(bytes.length / 2));
  const buf = S.ctx.createBuffer(1, pcm.length, OUT_RATE);
  const ch = buf.getChannelData(0);
  for (let i = 0; i < pcm.length; i++) ch[i] = pcm[i] / 0x8000;
  const src = S.ctx.createBufferSource(); src.buffer = buf; src.connect(S.ctx.destination);
  const at = Math.max(S.ctx.currentTime + 0.02, S.playHead);
  src.start(at); S.playHead = at + buf.duration;
  S.sources.push(src); src.onended = () => { S.sources = S.sources.filter(x => x !== src); };
}

function stopPlayback(S) {
  for (const s of S.sources) { try { s.stop(); } catch (e) {} }
  S.sources = []; S.playHead = 0;
}

function cleanup(S) {
  try { clearInterval(S.tick); } catch (e) {}
  try { S.proc && (S.proc.onaudioprocess = null); } catch (e) {}
  try { S.ws && S.ws.readyState <= 1 && S.ws.close(); } catch (e) {}
  try { S.stream && S.stream.getTracks().forEach(t => t.stop()); } catch (e) {}
  stopPlayback(S);
  try { S.ctx && S.ctx.close(); } catch (e) {}
}

function finish(S, reason, errorKind) {
  if (S.sent) return;
  S.sent = true;
  cleanup(S);
  const err = errorKind || '';
  setUi(S, err && !S.ready ? 'error' : 'ended',
        err === 'cota' ? 'A cota grátis do Gemini acabou por hoje. Use o modo normal.' : (err ? 'Detalhe: ' + err : ''));
  S.send('live_end', { seconds: Math.round(S.seconds), transcript: S.transcript, reason: reason, error: err });
}
"""

_component = st.components.v2.component("english_live_call", css=CSS, js=JS)


def live_call(token: str, system: str, used_seconds: float, max_seconds: float, session_max_seconds: float,
              session_key: str, key: str = "live_call"):
    """Mostra a chamada ao vivo. Retorna {'seconds', 'transcript', 'reason', 'error'} quando ela termina."""
    result = _component(
        key=key,
        data={"token": token, "model": LIVE_MODEL, "system": system, "used_seconds": used_seconds,
              "max_seconds": max_seconds, "session_max_seconds": session_max_seconds,
              "session_key": session_key, "versions": ["v1alpha", "v1beta"]},
        on_live_end_change=lambda: None,
    )
    return getattr(result, "live_end", None)
