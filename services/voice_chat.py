"""Microfone mãos-livres: ouve, detecta o fim da fala, envia, toca a resposta e volta a ouvir.

Tudo que é microfone/áudio roda no navegador (funciona no Mac e no iPhone/Safari).
O Python só recebe o áudio gravado (trigger 'utterance') e devolve a resposta em 'data'.
"""

import streamlit as st

CSS = """
.vc { display:flex; flex-direction:row; align-items:center; gap:14px; padding:6px 2px; font-family: 'Nunito', system-ui, sans-serif; }
.vc-btn { position:relative; flex-shrink:0; width:64px; height:64px; border-radius:50%; border:none; cursor:pointer;
  background: radial-gradient(circle at 30% 30%, #A8E6E0, #3FB8AF 70%); color:#fff; font-size:28px;
  box-shadow: 0 6px 18px rgba(63,184,175,.35); transition: transform .15s ease, background .3s ease; }
.vc-btn:active { transform: scale(.95); }
.vc-ring { position:absolute; inset:-7px; border-radius:50%; border:3px solid rgba(129,216,208,.55);
  transform: scale(var(--lvl,1)); transition: transform .08s linear; pointer-events:none; }
.vc[data-state=listening] .vc-ring { border-color: rgba(63,184,175,.85); }
.vc[data-state=thinking] .vc-btn { background: radial-gradient(circle at 30% 30%, #FFF3B8, #F4D35E 75%); }
.vc[data-state=thinking] .vc-ring { animation: vc-spin 1.1s linear infinite; border-style: dashed; }
.vc[data-state=speaking] .vc-btn { background: radial-gradient(circle at 30% 30%, #D9EEFC, #8CC8F0 75%); }
.vc[data-state=speaking] .vc-ring { animation: vc-pulse 1.2s ease-in-out infinite; border-color: rgba(140,200,240,.7); }
.vc[data-state=paused] .vc-btn, .vc[data-state=idle] .vc-btn { background: radial-gradient(circle at 30% 30%, #E8F7F5, #9ED9D3 80%); }
.vc-text { display:flex; flex-direction:column; gap:2px; min-width:0; }
.vc-status { font-size:15px; font-weight:800; color:#21414A; }
.vc-hint { font-size:12.5px; color:#5D7A82; line-height:1.3; }
@keyframes vc-pulse { 0%,100% { transform: scale(1); opacity:.9 } 50% { transform: scale(1.12); opacity:.5 } }
@keyframes vc-spin { to { transform: rotate(360deg) } }
"""

JS = r"""
const SILENCE_MS = 1300, MIN_SPEECH_MS = 350, MAX_UTTER_MS = 60000;
const LABELS = {
  idle:      ['🎙️', 'Toque para começar', 'Ouço sozinho e paro quando você termina de falar.'],
  listening: ['🎙️', 'Ouvindo… pode falar', 'Toque no botão para pausar.'],
  thinking:  ['💭', 'Pensando…', ''],
  speaking:  ['🔊', 'Respondendo…', 'Depois da resposta eu volto a ouvir.'],
  paused:    ['⏸️', 'Pausado', 'Toque para continuar.'],
  error:     ['⚠️', 'Não consegui usar o microfone', 'Permita o microfone no navegador e toque de novo.'],
};

const TARGET_RATE = 16000, PREROLL_SEC = 0.6;

function encodeWav(chunks, inRate) {
  // junta os pedaços, reduz para 16 kHz mono e grava como WAV 16-bit (aceito por Groq, Gemini e OpenAI)
  let len = 0; for (const c of chunks) len += c.length;
  const all = new Float32Array(len); let o = 0; for (const c of chunks) { all.set(c, o); o += c.length; }
  const ratio = inRate / TARGET_RATE;
  const outLen = Math.floor(all.length / ratio);
  const pcm = new Int16Array(outLen);
  for (let i = 0; i < outLen; i++) {
    const a = Math.floor(i * ratio), b = Math.min(all.length, Math.floor((i + 1) * ratio));
    let sum = 0; for (let j = a; j < b; j++) sum += all[j];
    const v = Math.max(-1, Math.min(1, sum / Math.max(1, b - a)));
    pcm[i] = v < 0 ? v * 0x8000 : v * 0x7fff;
  }
  const buf = new ArrayBuffer(44 + pcm.length * 2); const dv = new DataView(buf);
  const w = (off, str) => { for (let i = 0; i < str.length; i++) dv.setUint8(off + i, str.charCodeAt(i)); };
  w(0, 'RIFF'); dv.setUint32(4, 36 + pcm.length * 2, true); w(8, 'WAVE'); w(12, 'fmt ');
  dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 1, true);
  dv.setUint32(24, TARGET_RATE, true); dv.setUint32(28, TARGET_RATE * 2, true);
  dv.setUint16(32, 2, true); dv.setUint16(34, 16, true); w(36, 'data'); dv.setUint32(40, pcm.length * 2, true);
  new Int16Array(buf, 44).set(pcm);
  return new Uint8Array(buf);
}

function toBase64(bytes) {
  let bin = ''; const step = 0x8000;
  for (let i = 0; i < bytes.length; i += step) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + step));
  return btoa(bin);
}

export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  const root = parentElement;
  let S = root.__vc;

  if (!S) {
    S = root.__vc = { state: 'idle', paused: false, started: false, lastReply: null, sentToken: null,
                      pending: null, noise: 0.01, audio: new Audio() };
    S.audio.setAttribute('playsinline', '');
    const wrap = document.createElement('div');
    wrap.className = 'vc';
    wrap.innerHTML = '<button class="vc-btn" type="button"><span class="vc-ring"></span><span class="vc-ico"></span></button>' +
                     '<div class="vc-text"><div class="vc-status"></div><div class="vc-hint"></div></div>';
    root.appendChild(wrap);
    S.wrap = wrap; S.btn = wrap.querySelector('.vc-btn');
    S.ico = wrap.querySelector('.vc-ico'); S.status = wrap.querySelector('.vc-status'); S.hint = wrap.querySelector('.vc-hint');
    S.ring = wrap.querySelector('.vc-ring');
    S.btn.addEventListener('click', () => onTap(S));
    // conversa encerrada (componente saiu da tela) → desliga microfone e áudio
    S.watch = setInterval(() => {
      if (!S.wrap.isConnected) { try { S.audio.pause(); } catch (e) {} S.recording = false; shutdown(S); clearInterval(S.watch); }
    }, 700);
    setState(S, 'idle');
  }
  S.send = setTriggerValue;

  const d = data || {};
  const newReply = d.reply_id && d.reply_id !== S.lastReply;
  if (newReply) {
    S.lastReply = d.reply_id;
    if (d.audio_b64) {
      const r = { b64: d.audio_b64, mime: d.mime || 'audio/mpeg' };
      if (S.started && !S.paused) playReply(S, r);
      else { S.pending = r; if (S.started) setState(S, 'paused'); }
    } else if (S.state === 'thinking') startListening(S);
  } else if (S.state === 'thinking' && d.token !== undefined && d.token !== S.sentToken) {
    // o Python terminou de processar sem resposta nova (ex.: não entendeu) → volta a ouvir
    startListening(S);
  }
  S.lastSeenToken = d.token;
}

function setState(S, st) {
  S.state = st;
  S.wrap.dataset.state = st;
  const [ico, status, hint] = LABELS[st];
  S.ico.textContent = ico; S.status.textContent = status; S.hint.textContent = hint;
  if (st !== 'listening') S.ring.style.setProperty('--lvl', 1);
}

async function onTap(S) {
  if (!S.started) {
    S.started = true;
    // desbloqueia o áudio no iPhone com um toque do usuário
    try { S.audio.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YQAAAAA='; await S.audio.play(); } catch (e) {}
    try { await ensureMic(S); } catch (e) { S.started = false; setState(S, 'error'); return; }
    if (S.pending) { const r = S.pending; S.pending = null; playReply(S, r); } else startListening(S);
    return;
  }
  if (S.state === 'error') { S.started = false; return onTap(S); }
  if (S.paused) {
    S.paused = false;
    if (S.pending) { const r = S.pending; S.pending = null; playReply(S, r); }
    else if (S.state !== 'thinking') startListening(S);
    return;
  }
  // pausar
  S.paused = true;
  if (S.state === 'listening') stopRecording(S, true);
  if (S.state === 'speaking') { S.audio.pause(); }
  if (S.state !== 'thinking') setState(S, 'paused');
}

async function ensureMic(S) {
  if (S.stream) return;
  S.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
  const Ctx = window.AudioContext || window.webkitAudioContext;
  S.ctx = new Ctx();
  const src = S.ctx.createMediaStreamSource(S.stream);
  S.analyser = S.ctx.createAnalyser();
  S.analyser.fftSize = 1024;
  src.connect(S.analyser);
  S.buf = new Float32Array(S.analyser.fftSize);
  // captura do áudio cru (PCM) para gerar WAV
  S.proc = S.ctx.createScriptProcessor(4096, 1, 1);
  S.mute = S.ctx.createGain(); S.mute.gain.value = 0;
  src.connect(S.proc); S.proc.connect(S.mute); S.mute.connect(S.ctx.destination);
  S.recording = false; S.pcm = [];
  S.proc.onaudioprocess = (e) => {
    if (!S.recording) return;
    S.pcm.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    if (!S.speechStart) {  // antes de você começar a falar, guarda só um pedacinho (pré-roll)
      const keep = Math.ceil(PREROLL_SEC * S.ctx.sampleRate / 4096);
      if (S.pcm.length > keep) S.pcm.splice(0, S.pcm.length - keep);
    }
  };
}

function level(S) {
  S.analyser.getFloatTimeDomainData(S.buf);
  let s = 0; for (let i = 0; i < S.buf.length; i++) s += S.buf[i] * S.buf[i];
  return Math.sqrt(s / S.buf.length);
}

function startListening(S) {
  if (S.paused) { setState(S, 'paused'); return; }
  if (!S.stream) return;
  if (S.ctx && S.ctx.state === 'suspended') S.ctx.resume();
  S.pcm = []; S.discard = false; S.speechStart = null; S.lastVoice = null; S.t0 = performance.now();
  S.recording = true;
  setState(S, 'listening');
  
  loop(S);
}

function loop(S) {
  if (S.state !== 'listening') return;
  if (!S.wrap.isConnected) { shutdown(S); return; }
  const now = performance.now();
  const lv = level(S);
  const speaking = lv > Math.max(0.018, S.noise * 3.2);
  if (!speaking && !S.speechStart) S.noise = S.noise * 0.95 + lv * 0.05;
  if (speaking) { if (!S.speechStart) S.speechStart = now; S.lastVoice = now; }
  S.ring.style.setProperty('--lvl', (1 + Math.min(lv * 6, 0.35)).toFixed(3));
  if (S.speechStart && now - S.lastVoice > SILENCE_MS) { stopRecording(S, false); return; }
  if (S.speechStart && now - S.speechStart > MAX_UTTER_MS) { stopRecording(S, false); return; }
  requestAnimationFrame(() => loop(S));
}

function stopRecording(S, discard) {
  S.discard = discard;
  S.spoke = S.speechStart ? (S.lastVoice - S.speechStart) : 0;
  if (!S.recording) return;
  S.recording = false;
  onStopped(S);
}

function onStopped(S) {
  if (S.discard) return;
  if (S.spoke < MIN_SPEECH_MS) { startListening(S); return; }  // foi só um barulho
  setState(S, 'thinking');
  const wav = encodeWav(S.pcm, S.ctx.sampleRate);
  S.pcm = [];
  S.sentToken = S.lastSeenToken;
  S.send('utterance', { b64: toBase64(wav), mime: 'audio/wav' });
}

function playReply(S, r) {
  if (S.state === 'listening') stopRecording(S, true);
  setState(S, 'speaking');
  S.audio.src = 'data:' + r.mime + ';base64,' + r.b64;
  S.audio.onended = () => { if (!S.wrap.isConnected) { shutdown(S); return; } if (S.paused) setState(S, 'paused'); else startListening(S); };
  S.audio.play().catch(() => { S.pending = r; S.paused = true; setState(S, 'paused'); });
}

function shutdown(S) {
  try { S.stream && S.stream.getTracks().forEach(t => t.stop()); } catch (e) {}
  try { S.ctx && S.ctx.close(); } catch (e) {}
  S.stream = null;
}
"""

_component = st.components.v2.component("english_voice_chat", css=CSS, js=JS)


def voice_chat(reply_id: int, audio_b64: str | None, mime: str | None, token: int, key: str = "voice_chat"):
    """Mostra o botão de microfone mãos-livres. Retorna {'b64', 'mime'} quando o usuário terminar de falar."""
    result = _component(
        key=key,
        data={"reply_id": reply_id, "audio_b64": audio_b64, "mime": mime, "token": token},
        on_utterance_change=lambda: None,
    )
    return getattr(result, "utterance", None)
