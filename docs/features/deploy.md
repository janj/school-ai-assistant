# Deploy (Track F)

## What it does
Runs the app on its own $6 DigitalOcean droplet behind Caddy with automatic HTTPS at
`https://<ip-with-dashes>.sslip.io`. Deployed by hand from the operator's Mac. Full runbook:
[DEPLOY.md](../DEPLOY.md).

## How it works
- `deploy/Dockerfile`: python:3.12-slim + `uv sync --frozen --no-dev`, copies `app/`, `static/`,
  `seed/`, runs as uid 1000, one uvicorn worker with `--proxy-headers`.
- `deploy/docker-compose.yml`: `app` (env from `/opt/school-ai/.env`, volume `school_data` at
  `/app/data`, healthcheck on `/healthz`) and `caddy` (80/443, `caddy_data` volume for certs).
  Caddy starts only once the app is healthy.
- `deploy/Caddyfile`: `{$DOMAIN}` reverse-proxy to `app:8000`, zstd/gzip, `Server` header
  dropped, HSTS/nosniff/frame-deny/referrer/permissions headers.
- `deploy/deploy.sh`: `DROPLET_IP=… ./deploy/deploy.sh [--rotate-key]`. Refuses a dirty tree,
  rsyncs, creates `.env` on first run, runs `docker compose up -d --build`, polls `/healthz`.

## Decisions
- **One worker**: the rate limiter is in memory (Track B).
- **API key never on a command line**: streamed from local `claude-key` over ssh stdin straight
  into a mode-600 file on the server; `--rotate-key` rewrites only that line.
- **`--forwarded-allow-ips "*"`**: safe because the app port is not published; only Caddy can
  reach it on the compose network. Needed so the limiter sees the real client IP.
- **`DOMAIN` is a compose variable** (not just app env). Compose reads `.env` from the compose
  file's directory, so `deploy.sh` links `deploy/.env -> ../.env` on the server; plain
  `docker compose -f deploy/docker-compose.yml ...` commands then work (fixed in Phase 2).
- **Permissions-Policy allows `microphone=(self)`** so the Phase 3 voice track works.
- **No HTTP/3**: the firewall opens 443/TCP only.
- `.dockerignore` excludes `docs/`, `.env*`, `claude-key`, `data/`, `.git`.
- Backups use SQLite's online backup API rather than copying the live file.

## Verified locally
Image builds; stack run with `DOMAIN=localhost`: app healthy, Caddy served `/healthz` over TLS
with security headers and no `Server` header, container runs non-root and can write the volume.
`deploy.sh` is only syntax-checked (`bash -n`); it has not been run against a host.
