# Track F: Deploy (droplet + Docker + Caddy)

**Branch:** `track/f-deploy` · **Owns:** `deploy/` (everything), `.dockerignore`, `.env.example`, `docs/DEPLOY.md`, `docs/features/deploy.md`

## Goal
The operator deploys **by hand from their Mac** to a **new, separate** DigitalOcean droplet
($6/month, 1 vCPU / 1 GB, Ubuntu LTS). The site is served at `https://<droplet-ip-with-dashes>.sslip.io`
with automatic HTTPS from Caddy (sslip.io resolves `1-2-3-4.sslip.io` to `1.2.3.4`). No GitHub
Actions deploy. For conventions, look at `~/src/civic-mined/deploy/` and
`~/src/civic-mined/docs/DROPLET_SETUP.md` **read-only**: never edit that repo or touch its
droplet.

## Files
- **`deploy/Dockerfile`:**
  - Python 3.12 slim + `uv`. `uv sync --frozen --no-dev`. Copy `app/`, `static/`, `seed/`.
  - Run `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1` with `--proxy-headers`.
  - **Exactly one worker:** the rate limiter is in memory.
  - Run as a non-root user.
- **`deploy/docker-compose.yml`:**
  - `app`: env from `/opt/school-ai/.env`, a named volume mounted at `/app/data` with
    `DB_PATH=/app/data/school.db`, `restart: unless-stopped`, and a healthcheck on `/healthz`.
  - `caddy` (the official image): ports 80/443, a `caddy_data` volume for certificates, and
    `DOMAIN` from env.
- **`deploy/Caddyfile`:**
  - `{$DOMAIN} { encode zstd gzip; reverse_proxy app:8000 }`.
  - Header hygiene: drop `Server`, and add sensible security headers.
  - Pass `X-Forwarded-For` (Caddy's default is fine). The app uses it only for in-memory rate
    limits.
- **`deploy/deploy.sh`:** run from the repo root on the Mac. `DROPLET_IP=1.2.3.4 ./deploy/deploy.sh`.
  1. Refuse to run with uncommitted changes. Print the commit being deployed.
  2. `rsync` the repo, excluding `.git`, `data/`, `claude-key`, `.env*`, `.venv` and
     `__pycache__`, to `root@$DROPLET_IP:/opt/school-ai/`.
  3. **First run only:** if `/opt/school-ai/.env` is missing on the server, create it over ssh
     with `ANTHROPIC_API_KEY` taken from the local `claude-key` file (streamed over stdin;
     **never** echoed, never on the command line, never written locally), a random
     `SESSION_SECRET`, and `DOMAIN=<ip-dashes>.sslip.io`. Then `chmod 600`. Later runs leave it
     alone. Add a `--rotate-key` flag to replace only `ANTHROPIC_API_KEY`.
  4. `docker compose up -d --build`, then poll `https://$DOMAIN/healthz` until it's healthy
     (time out after 120s). Print the URL.
  5. Use `set -euo pipefail` and clear messages throughout.
- **`.dockerignore`:** at least `.git`, `data/`, `claude-key`, `.env*`, `.venv`, `.claude/`.
- **`.env.example`:** every variable in `app/config.py`, with comments. No real values.
- **`docs/DEPLOY.md`:**
  - Creating the droplet. Give both the `doctl` command and the UI steps. Use an SSH key and
    the smallest size.
  - A DO Cloud Firewall: 22 from the operator's IP only; 80/443 from anywhere.
  - A one-time bootstrap: install Docker + the compose plugin, unattended-upgrades, and a 1 GB
    swap file (1 GB of RAM is tight while building).
  - The first deploy, later deploys, rotating the key, viewing logs
    (`docker compose logs -f app`), backing up the SQLite volume, rollback (check out the
    previous commit and redeploy), and tearing it down.
  - The operator runs every command. Don't create any cloud resources yourself.

## Check
Run `docker compose -f deploy/docker-compose.yml build` locally if Docker is available. Run
`bash -n deploy/deploy.sh` and `shellcheck` if it's installed. Run Caddy locally with
`DOMAIN=localhost` if you can. **Don't** create droplets or run `deploy.sh` against a server.
