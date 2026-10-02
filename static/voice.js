// Voice input (SpeechRecognition) and read-aloud (speechSynthesis). Browser-only, no server cost.
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const TTS = "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
const STORE_KEY = "sa_read_aloud";

const BLOCKED = "Microphone access was blocked. Allow it in your browser settings to talk.";
const ERRORS = {
  "not-allowed": BLOCKED,
  "service-not-allowed": BLOCKED,
  "no-speech": "I didn't hear anything. Tap the mic and try again.",
  "audio-capture": "No microphone found.",
  "network": "Voice recognition needs a network connection. Please type instead.",
};

// Cheap Spanish detection: inverted punctuation / ñ, or a high share of common Spanish words.
const ES_WORDS = /\b(el|la|los|las|de|que|y|en|es|por|para|con|su|sus|una|un|hora|horas|niños|niño|cuánto|cuándo|dónde|qué|puede|pueden|centro|almuerzo|tarifa|favor|gracias|hola)\b/gi;
export function detectLang(text, fallback) {
  if (/[¿¡ñ]/i.test(text)) return "es";
  const hits = (text.match(ES_WORDS) || []).length;
  const words = text.split(/\s+/).length;
  return hits >= 3 && hits / words > 0.2 ? "es" : fallback;
}

function stripMarkdown(t) {
  return t
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/^\s{0,3}#{1,6}\s+/gm, "")
    .replace(/^\s*[-*+]\s+/gm, "")
    .replace(/^\s*\d+[.)]\s+/gm, "")
    .replace(/^\s*>\s?/gm, "")
    .replace(/[*_`~|]/g, "")
    .replace(/([.:;!?])\s*\n\s*/g, "$1 ")
    .replace(/\s*\n\s*/g, ". ")
    .replace(/\.\s*\./g, ".")
    .trim();
}

function loadPref() { try { return localStorage.getItem(STORE_KEY) === "1"; } catch { return false; } }
function savePref(v) { try { localStorage.setItem(STORE_KEY, v ? "1" : "0"); } catch { /* ignore */ } }

function btn(cls, label, svg) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = `btn voice-btn ${cls}`;
  b.setAttribute("aria-label", label);
  b.title = label;
  b.innerHTML = svg;
  return b;
}
const MIC = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V22h2v-3.08A7 7 0 0 0 19 12h-2z"/></svg>';
const SPK = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M3 9v6h4l5 5V4L7 9H3zm13.5 3a4.5 4.5 0 0 0-2.5-4.03v8.05A4.5 4.5 0 0 0 16.5 12zM14 3.23v2.06a7 7 0 0 1 0 13.42v2.06a9 9 0 0 0 0-17.54z"/></svg>';

// container: element the buttons are appended to (the input row). send(text): submits a question.
export function mountVoice(container, { input, send, getLang = () => navigator.language || "en-US" }) {
  if (!SR && !TTS) return container;
  if (!document.getElementById("voice-css")) {
    const l = document.createElement("link");
    l.id = "voice-css"; l.rel = "stylesheet"; l.href = "/static/voice.css";
    document.head.append(l);
  }
  // Inline message line, placed under the input row the first time it is needed.
  const status = document.createElement("div");
  status.className = "voice-status";
  status.setAttribute("role", "status");
  const say = (msg) => {
    if (!status.isConnected && input.parentElement) input.parentElement.after(status);
    status.textContent = msg;
  };
  let lastInputLang = null;

  // ---- Read aloud ----
  let readAloud = TTS && loadPref();
  let speaker = null;
  const stopSpeaking = () => { if (TTS) speechSynthesis.cancel(); };
  function speak(text) {
    const clean = stripMarkdown(text);
    if (!clean) return;
    const lang = detectLang(clean, lastInputLang || (getLang() || "en").slice(0, 2).toLowerCase());
    const u = new SpeechSynthesisUtterance(clean);
    const v = speechSynthesis.getVoices().find((x) => x.lang.toLowerCase().startsWith(lang));
    if (v) { u.voice = v; u.lang = v.lang; } else u.lang = lang;
    stopSpeaking();
    speechSynthesis.speak(u);
  }
  if (TTS) {
    speaker = btn("voice-speaker", "Read answers aloud", SPK);
    const sync = () => {
      speaker.setAttribute("aria-pressed", String(readAloud));
      speaker.title = readAloud ? "Read answers aloud: on" : "Read answers aloud: off";
    };
    sync();
    speaker.addEventListener("click", () => {
      readAloud = !readAloud;
      savePref(readAloud);
      if (!readAloud) stopSpeaking();
      sync();
    });
    document.addEventListener("chat:answer", (e) => { if (readAloud && e.detail?.text) speak(e.detail.text); });
    // Stop speaking when the user types or sends.
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") stopSpeaking(); });
    input.addEventListener("input", stopSpeaking);
    window.addEventListener("pagehide", stopSpeaking);
  }

  // ---- Mic ----
  let mic = null;
  if (SR) {
    mic = btn("voice-mic", "Talk to ask a question", MIC);
    mic.setAttribute("aria-pressed", "false");
    let rec = null;
    let finalText = "";
    let errored = false;
    const fire = () => input.dispatchEvent(new Event("input", { bubbles: true }));

    const setListening = (on) => {
      mic.setAttribute("aria-pressed", String(on));
      mic.classList.toggle("listening", on);
      mic.title = on ? "Stop listening" : "Talk to ask a question";
      if (on) say("Listening…");
      else if (!errored) say("");
    };

    mic.addEventListener("click", () => {
      if (rec) { rec.stop(); return; }
      stopSpeaking();
      errored = false;
      finalText = "";
      rec = new SR();
      rec.lang = getLang() || navigator.language || "en-US";
      rec.interimResults = true;
      rec.continuous = false;
      rec.onstart = () => setListening(true);
      rec.onresult = (e) => {
        let interim = "";
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const r = e.results[i];
          if (r.isFinal) finalText += r[0].transcript; else interim += r[0].transcript;
        }
        input.value = (finalText + interim).trim();
        fire();
      };
      rec.onerror = (e) => {
        if (e.error === "aborted") return;
        errored = true;
        say(ERRORS[e.error] || "Voice input didn't work. Please type instead.");
      };
      rec.onend = () => {
        rec = null;
        setListening(false);
        const text = finalText.trim();
        if (text) {
          lastInputLang = detectLang(text, (navigator.language || "en").slice(0, 2).toLowerCase());
          send(text);
        } else if (!errored) {
          input.value = "";
          fire();
        }
      };
      try { rec.start(); } catch { rec = null; errored = true; say("Voice input didn't start. Please try again."); }
    });
  }

  const wrap = document.createElement("div");
  wrap.className = "voice-controls";
  if (mic) wrap.append(mic);
  if (speaker) wrap.append(speaker);
  container.append(wrap);
  return container;
}
