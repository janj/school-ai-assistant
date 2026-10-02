# Rules for every track (read first)

You are one of six parallel agents building a POC. Other agents are editing other files at the
same time, on other branches.

1. **Read first:** `docs/PROCESS.md` (goals, decisions), `docs/CONTRACTS.md` (fixed interfaces),
   and your own brief in `docs/tracks/`.
2. **Branch:** inside your worktree, run `git checkout -b track/<letter>-<slug>` (the name is in
   your brief) before your first commit.
3. **File ownership:** edit only the files your brief lists. Never edit `app/schema.sql`,
   `docs/CONTRACTS.md`, `docs/PROCESS.md`, or another track's files. If a contract blocks you,
   don't work around it: finish what you can and describe the problem in your summary.
4. **Secrets:** never read, print, copy or commit `claude-key` or any `.env`. For local runs that
   need the model, use
   `ANTHROPIC_API_KEY="$(cat /Users/janjirout/Documents/career/Companies/Brightwheel/school-ai-assisstant/claude-key)"` inline, or tell
   the reviewer the step needs a key. Never write a key into a file.
5. **No tests** (POC). Do run the app and use your feature for real:
   `uv sync && uv run uvicorn app.main:app --port <your port>` (pick a port from your brief so you
   don't collide with other agents).
6. **Style:** Python 3.12, standard library first, small modules, comments only where the reason
   isn't obvious. Plain JS ES modules, no build step, no frameworks, no CDN dependencies unless
   your brief allows one.
7. **Shared browser:** several agents share one browser, and cookies are per host, not per
   port. So other agents' sessions will overwrite yours on `localhost`. Use
   `http://127.0.0.1:<your port>`, prefer `curl` with your own cookie jar for API checks, and
   re-create your session right before any browser check.
8. **Deliverables:**
   - Commits on your branch.
   - `docs/features/<your-track>.md`: what it does, how it works, the decisions made and why.
     Under 1 page.
   - **A final reply** with: branch name; files changed; decisions you made that the brief
     didn't; anything unfinished or blocked; exact steps to try it.
