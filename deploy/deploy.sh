#!/usr/bin/env bash
# Deploy by hand from the repo root on your Mac:
#   DROPLET_IP=1.2.3.4 ./deploy/deploy.sh [--rotate-key]
set -euo pipefail

ROTATE_KEY=0
for arg in "$@"; do
  case "$arg" in
    --rotate-key) ROTATE_KEY=1 ;;
    *) echo "Unknown argument: $arg (only --rotate-key is supported)" >&2; exit 2 ;;
  esac
done

: "${DROPLET_IP:?Set DROPLET_IP, e.g. DROPLET_IP=1.2.3.4 ./deploy/deploy.sh}"
[[ "$DROPLET_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "DROPLET_IP must be an IPv4 address" >&2; exit 2; }

cd "$(git rev-parse --show-toplevel)"
REMOTE="root@$DROPLET_IP"
REMOTE_DIR=/opt/school-ai
DOMAIN="${DROPLET_IP//./-}.sslip.io"
SSH_OPTS=(-o StrictHostKeyChecking=accept-new)
ssh_run() { ssh "${SSH_OPTS[@]}" "$REMOTE" "$@"; }

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Refusing to deploy: uncommitted changes. Commit or stash first." >&2
  exit 1
fi
echo "==> Deploying $(git log -1 --format='%h %s') to $DROPLET_IP"

HAS_ENV=1
ssh_run "test -f $REMOTE_DIR/.env" || HAS_ENV=0
if [[ $HAS_ENV == 0 || $ROTATE_KEY == 1 ]]; then
  [[ -f claude-key ]] || { echo "Local file ./claude-key not found (needed for the API key)." >&2; exit 1; }
fi

echo "==> Syncing files"
ssh_run "mkdir -p $REMOTE_DIR"
rsync -az --delete \
  -e "ssh ${SSH_OPTS[*]}" \
  --exclude '.git' --exclude '.claude' --exclude 'data/' --exclude 'claude-key' \
  --exclude '.env*' --exclude '.venv' --exclude '__pycache__' --exclude '*.rtf' \
  ./ "$REMOTE:$REMOTE_DIR/"

# The key travels over ssh stdin only: never in argv, never echoed, never written locally.
if [[ $HAS_ENV == 0 ]]; then
  echo "==> First run: creating $REMOTE_DIR/.env"
  ssh_run "umask 077; read -r KEY; SECRET=\$(openssl rand -hex 32); \
    printf 'ANTHROPIC_API_KEY=%s\nSESSION_SECRET=%s\nDOMAIN=%s\n' \"\$KEY\" \"\$SECRET\" '$DOMAIN' > $REMOTE_DIR/.env; \
    chmod 600 $REMOTE_DIR/.env" < claude-key
elif [[ $ROTATE_KEY == 1 ]]; then
  echo "==> Rotating ANTHROPIC_API_KEY"
  ssh_run "umask 077; read -r KEY; cd $REMOTE_DIR; \
    { grep -v '^ANTHROPIC_API_KEY=' .env || true; printf 'ANTHROPIC_API_KEY=%s\n' \"\$KEY\"; } > .env.new; \
    chmod 600 .env.new; mv .env.new .env" < claude-key
else
  echo "==> Keeping existing .env"
fi

echo "==> Building and starting containers"
ssh_run "cd $REMOTE_DIR && docker compose --env-file .env -f deploy/docker-compose.yml up -d --build"

echo "==> Waiting for https://$DOMAIN/healthz (up to 120s)"
deadline=$((SECONDS + 120))
until curl -fsS --max-time 5 "https://$DOMAIN/healthz" >/dev/null 2>&1; do
  if (( SECONDS >= deadline )); then
    echo "Timed out. Check: ssh $REMOTE 'cd $REMOTE_DIR && docker compose -f deploy/docker-compose.yml logs --tail 50'" >&2
    exit 1
  fi
  sleep 3
done
echo "==> Healthy: https://$DOMAIN"
