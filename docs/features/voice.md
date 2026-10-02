# Voice input and read-aloud (Track J)

Parents can speak a question and have answers read aloud. It uses only the browser's Web Speech
API: no server cost, no audio sent by us (Chrome sends recognition audio to Google's speech
service; that is the browser's doing).

## How it works
- `static/voice.js` exports `mountVoice(container, {input, send, getLang})`. It appends a mic
  button and a speaker toggle to `container` and loads `static/voice.css` itself.
- **Mic:** tap to start, tap to stop. Interim text fills the input; the final text is passed to
  `send(text)`. `aria-pressed` and a pulsing ring show the listening state. Errors (blocked
  permission, no speech, no mic, network) show a friendly line under the input row.
- **Read aloud:** the speaker toggle is stored in `localStorage` (`sa_read_aloud`, try/catch).
  When on, each `chat:answer` event (`document`, `detail.text`) is spoken with markdown
  stripped. Speech stops when the user types, presses Enter, taps the mic, or leaves the page.
- **Language:** recognition uses `navigator.language`. The answer is spoken in Spanish if it
  contains `¿ ¡ ñ` or a high share of common Spanish words; otherwise it uses the language of
  the last spoken question, then the browser language. A matching installed voice is chosen if
  one exists.
- **Feature detection:** no SpeechRecognition hides the mic (Firefox); no speechSynthesis hides
  the speaker; with neither, nothing is mounted.

## Hook in `chat.js`
The single `HOOK(voice)` line is replaced by an inline slot element (`.voice-slot`, styled
`display: contents`) plus a dynamic `import("/static/voice.js")`. Dynamic import keeps it one
line and means a voice failure can never break the chat.

## Needs from Track G
`chat.js` must dispatch, after each answer is rendered:
`document.dispatchEvent(new CustomEvent("chat:answer", {detail: {text: data.answer}}))`.
Until then, read-aloud has nothing to speak (the mic works without it).

## Not tested
Real microphone input (the Browser pane blocks it; used a fake recognizer and a stubbed
`speechSynthesis.speak`), Safari/iOS, Firefox, real Spanish voices.
