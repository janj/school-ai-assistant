# Track C: Frontend (picker + chat)

**Branch:** `track/c-frontend` · **Port:** 8103 · **Owns:** `static/index.html`, `static/chat.js`, `static/chat.css` (new), `static/base.css` (values + new rules only; the token names are fixed), `docs/features/frontend.md`

## Goal
A mobile-first single page at `/`, with two states, driven by `GET /api/session`.

### State 1: no session (401) → the picker
- Pick a center: cards from `GET /api/centers` showing name and tagline. Tint each card with
  its `theme.primary`.
- Pick a role: Parent or Admin. Admin shows a required "Your name" field and a note that admin
  mode can edit the center's information.
- Continue → `POST /api/session`. Show the server's `detail` text on 400.
- Explain in one line that this is a demo and the choice can be changed with "Start over".

### State 2: has a session → the chat
- **Header:** the center name and `logo_text` badge, a role pill, an **Admin** link to `/admin`
  (admins only), and a **Start over** button (`DELETE /api/session`, then back to the picker).
  These stay visible on every screen.
- Apply the theme: set `--brand-primary`, `--brand-accent` and `--brand-bg` on
  `document.documentElement` from `session.center.theme`. Keep text contrast readable.
- **Empty state:** a greeting plus 4 suggested question chips (e.g. hours, late pickup, sick
  policy, lunch). Tapping a chip sends it.
- **Message list:** user and assistant bubbles. Render the assistant's light markdown safely:
  escape HTML first, then support `**bold**`, `- ` lists and line breaks only.
- **Sources:** show `sources` as small chips with friendly labels (map `policy:late_pickup` →
  "Late pickup policy", `hours` → "Hours", and so on; fall back to the raw ID).
- **Not found** (`found=false`): show a distinct "Contact the center" card with tappable
  `tel:` and `mailto:` links from `contact`.
- **Errors:**
  - 429: show `detail`, and use different copy for `kind` rate vs. budget.
  - 400: show `detail`.
  - 401: the session is gone, so go back to the picker.
  - 503 or a network error: "temporarily unavailable" with a retry button.
- **Input:** a textarea that grows with its content, up to 4 lines. Enter sends, Shift+Enter
  adds a new line. Disable it while waiting and show a typing indicator. Limit to 1,000
  characters with a counter near the limit.
- **Conversation id:** keep a `conversationId` (from `crypto.randomUUID()`) in a module
  variable, send it with every message, and mint a new one on Start over. Track G will use it.
  Leave a clear hook comment for G and for J (voice):
  `// HOOK(voice): mic button mounts here`.
- **Accessibility:** a labelled input, `aria-live="polite"` on the message list, visible focus
  styles, tap targets ≥ 40px.

### Layout
- Works at 360px wide with no sideways scrolling.
- The input bar is sticky at the bottom and stays usable when the iOS keyboard is open (use
  `100dvh`).
- Max content width ~720px on desktop.
- Light and dark mode via the existing tokens.

## Check
The chat backend is a stub on `main` (it echoes the question), which is enough to build the
whole UI. To test the error and not-found states, temporarily change the stub **locally only,
without committing**, or use the browser devtools. Check at 360px and at desktop width. Check
both roles, and Start over from every state.
