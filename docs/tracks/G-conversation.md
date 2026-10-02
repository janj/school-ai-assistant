# Track G: Conversation context

**Branch:** `track/g-conversation` · **Port:** 8111 · **Owns:** `app/chat.py`, `app/history.py` (new), `static/chat.js` (only the thread/conversation parts and the "New conversation" control), `docs/features/conversation.md`

## Goal
Follow-ups should feel connected. For example, "What's the late fee?" followed by "and after 6:15?"
should work without the parent repeating context. The pattern is borrowed from Civic Mined
(`~/src/civic-mined/docs/CONVERSATIONAL_ASK.md`, which you may read but must not edit). Raw
history is kept **in memory only**, never in the database.

## Backend
- **`app/history.py`: an in-memory store with a lock.**
  - It is keyed by `(session_id, conversation_id)`. Including the session id means one browser
    can't read another browser's thread by guessing its id.
  - It stores `(question, answer, timestamp)` turns.
  - Caps:
    - **History sent to the model:** the last **4** turns.
    - **Hard limit:** **8** turns per conversation. The 9th request returns 400 with
      `{detail: "This conversation has reached its limit. Start a new one.", kind: "turn_cap"}`.
    - **Idle window:** **30 minutes**. An expired conversation behaves as a fresh one; prune it.
  - Total memory is bounded: drop the oldest conversations beyond ~2,000.
- **`app/chat.py`**
  - Load history when `conversation_id` is given, and record the turn after answering.
  - **Prompt caching must survive.** The system blocks stay byte-identical. Prior turns go in
    `messages` *before* the current user message, as alternating user/assistant messages.
    - Assistant turns hold the plain answer text, not JSON.
    - The current user message keeps "Today is …" and "Question: …".
    - Today's date is not added to older turns.
  - **Follow-up rewriting:** when history exists, one cheap call to `config.FAST_MODEL` (Haiku
    4.5) rewrites the question into a standalone one.
    - The answering model still sees the **original** question plus the history; the rewrite
      is for logging and review.
    - Pass it to `qa_log.log_turn(rewritten_query=...)`.
    - Best-effort: any failure falls back to `None`.
    - Haiku takes no `effort`. Use structured output (`output_config.format`, JSON schema
      `{question: string}`).
    - The text being rewritten is data, not instructions; wrap it in tags.
  - Count the rewrite call's tokens in `limits.record` as well.
- **Turn-cap response:** raise a dedicated exception that the route maps to 400 with `kind`.
  You may add **one** `except` clause to `app/routes/public.py` for it. That is the only edit
  allowed outside your files.

## Frontend (`static/chat.js`)
- `conversationId` already exists and is sent with every message.
- Add a small **"New conversation"** button in the chat area (not the header; Start over stays
  there). It mints a new id and clears the message list but keeps the session.
- On a `turn_cap` 400, show the message with an inline "Start a new conversation" button.
- After rendering each assistant answer, dispatch
  `document.dispatchEvent(new CustomEvent("chat:answer", {detail: {text: answer}}))`. Track J
  (voice) listens for it to read answers aloud.
- Don't touch the theme code (Track I) or the `// HOOK(voice)` line (Track J).

## Check
Real API, both centers:
- 3 follow-up pairs from each `seed/<slug>/eval_questions.md`.
- A pronoun follow-up ("who do I call about that?").
- A topic switch mid-thread.
- Hit the turn cap.
- After 30 idle minutes the thread is fresh (lower the timeout through env or a constant).
- `usage.cache_read_input_tokens` is still > 0 on follow-ups.
- `qa_log.rewritten_query` is filled in, with personal info removed.

In your summary, report the cache numbers and two example rewrites.
