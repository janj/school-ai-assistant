# Frontend (Track C)

A single page at `/` (`static/index.html` + `chat.js` + `chat.css`) with two states, chosen by
`GET /api/session` on load: 401 shows the picker, 200 shows the chat.

## Picker
Center cards (from `/api/centers`, tinted with `theme.primary`), a Parent/Admin choice, and a
required name field for admins. Continue calls `POST /api/session`; a 400 shows the server's
`detail`. A one-line note says this is a demo and the choice can be changed with Start over.

## Chat
- Header (always visible): `logo_text` badge, center name, role pill, an Admin link (admins
  only) and Start over (`DELETE /api/session`, new `conversationId`, back to the picker).
- Empty state with four suggestion chips. Messages render in bubbles; assistant text is
  HTML-escaped first, then only `**bold**`, `- ` lists and line breaks are turned into markup.
- Sources become chips (`policy:late_pickup` becomes "Late pickup policy"; unknown IDs show raw).
  `found=false` adds a "Contact the center" card with `tel:` and `mailto:` links.
- Errors: 429 (different lead text for `rate` and `budget`, then the server `detail`), 400
  (`detail`), 401 (back to the picker with a notice), 503/network ("temporarily unavailable" with
  Retry, which resends the last question without duplicating the bubble).
- Input: auto-growing textarea (max about 4 lines), Enter sends, Shift+Enter newline, disabled
  while waiting with a typing indicator, 1,000 character limit with a counter from 800.
- `conversationId` is a module variable (`crypto.randomUUID()`), sent with every message.
  Hook comments mark where the voice mic mounts (`HOOK(voice)`); Track G reads `conversationId`.

## Decisions
- Theme: `--brand-primary`, `--brand-accent`, `--brand-bg` are set on `:root` from the session's
  center. `--on-primary` (new, in `chat.css`) is white or near-black depending on the primary's
  luminance. In dark mode the center's `background` is ignored so text stays readable.
- No framework: small DOM-building helpers (`el`) and DOM text assignment, so user text never
  goes through `innerHTML` except via the escaping markdown renderer.
- Layout uses `100dvh` with a flex column so the input bar stays above the iOS keyboard; content
  is capped at 720px.
- `base.css`: values unchanged; added button/input font inheritance and a focus outline rule.
