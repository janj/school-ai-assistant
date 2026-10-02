# Conversation context (Track G)

Follow-ups such as "And what time does it start?" after a question about late pickup work without
repeating context.

## How it works
- The browser mints a `conversation_id` (new on Start over and on **New conversation**) and sends
  it with every message.
- `app/history.py` keeps `(question, answer, time)` turns **in memory only**, keyed by
  `(session_id, conversation_id)` so one browser cannot read another's thread by guessing an id.
  Nothing raw reaches the database, and a restart clears everything.
- Limits: the last **4** turns go to the model; **8** turns per conversation, then `/api/chat`
  returns 400 `{detail, kind: "turn_cap"}`; a conversation idle for **30 minutes** is dropped and
  the next message starts fresh (override with `CONVERSATION_IDLE_SECONDS` to test); at most
  2,000 conversations are kept, oldest dropped first.
- `app/chat.py` puts prior turns in `messages` before the current user message, as alternating
  user/assistant messages (assistant turns are the plain answer text). The two system blocks are
  untouched, so prompt caching still hits on follow-ups. "Today is ..." appears only in the
  current message.
- **Rewrite:** when history exists, Haiku 4.5 turns the follow-up into a standalone question
  (structured output, text wrapped in tags and treated as data). The answering model still sees
  the original question plus history; the rewrite is stored in `qa_log.rewritten_query` (scrubbed
  by `qa_log`) so reviewers can read follow-ups in context. It runs in a thread alongside the
  answer call, so it adds no latency, fails to `None`, and its tokens count in `limits.record`.

## Front end
"New conversation" sits above the composer (Start over stays in the header). On a `turn_cap`
error the message shows an inline "Start a new conversation" button. Each answer dispatches a
`chat:answer` event (`detail.text`) for voice.

## Decisions
- The turn cap is checked before the rate limiter and before any model call, so a capped request
  costs nothing.
- All answers, including "not found" and refusals, are stored as turns; the follow-up may refer
  to them.
- The only edit outside this track's files is one `except` clause in `app/routes/public.py`.
