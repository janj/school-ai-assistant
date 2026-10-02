# Track J: Voice

**Branch:** `track/j-voice` · **Port:** 8114 · **Owns:** `static/voice.js` (new), `static/voice.css` (new), the single `// HOOK(voice)` line in `static/chat.js` (replace it with the mount call; no other `chat.js` edits), `docs/features/voice.md`

## Goal
Parents can speak a question and have the answer read aloud. It uses only the browser's Web
Speech API, so there's no server cost and no audio leaves the browser except through the
browser's own speech service.

## Scope
- **`static/voice.js`:** `export function mountVoice(container, { input, send, getLang })`.
  - **Mic button** (SpeechRecognition / webkitSpeechRecognition):
    - Tap to talk, tap again to stop. Show interim text in the input, then send on final.
    - Visible listening state with `aria-pressed` and a pulsing indicator.
    - Handle errors: permission denied, no speech, network. Show a friendly inline message.
  - **Read aloud** (speechSynthesis): a small speaker toggle in the input row. When on, each
    new assistant answer is spoken, with markdown symbols stripped. Remember the toggle in
    `localStorage`, wrapped in try/catch. Stop speaking when the user starts talking or sends.
  - **Language:** recognition uses `navigator.language` by default. Spanish answers should be
    spoken with a Spanish voice when one exists: detect it simply (e.g. the answer contains
    common Spanish words or ¿/¡) or use the language of the last recognized input.
  - **Feature detection:** if recognition isn't supported (e.g. Firefox), hide the mic. If
    synthesis isn't supported, hide the speaker. Nothing breaks.
- **Hooking in:** `chat.js` currently has `// HOOK(voice): mic button mounts here` in the input
  row. Replace that one line with the import and mount call. To get new answers, listen for a
  `CustomEvent("chat:answer", {detail: {text}})` on `document`.
  - Track G owns `chat.js`. Ask it to dispatch that event by **noting it in your summary**; at
    merge time the operator adds the one-line dispatch if G didn't.
  - Until then, test with a temporary local dispatch that you **don't commit**.
- **Server headers:** the Caddyfile already allows `microphone=(self)`. Speech recognition needs
  HTTPS or localhost, so test locally on `localhost`.

## Check
Chrome desktop: speak a question in English and in Spanish, and hear both answers read aloud.
Check mobile layout at 360px wide: the input row must not overflow with the two new buttons.
Firefox: the mic is hidden and nothing errors. Describe what you couldn't test, such as real
mobile Safari.
