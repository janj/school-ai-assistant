# Deploying to a DigitalOcean droplet

A separate $6/month droplet (1 vCPU / 1 GB, Ubuntu 24.04 LTS), deployed by hand from your Mac.
The site is served at `https://<ip-with-dashes>.sslip.io` (for `203.0.113.7` that is
`203-0-113-7.sslip.io`); Caddy gets the HTTPS certificate automatically. This droplet is **not**
shared with Civic Mined.

You run every command below. Nothing here is automated except `deploy/deploy.sh`.

## 1. Create the droplet

You need an SSH key (`ls ~/.ssh/*.pub`; make one with `ssh-keygen -t ed25519` if none).

**With `doctl`:**
```bash
doctl auth init                                   # once
doctl compute ssh-key import school-ai --public-key-file ~/.ssh/id_ed25519.pub
doctl compute ssh-key list                        # note the key ID
doctl compute droplet create school-ai \
  --region nyc3 --image ubuntu-24-04-x64 --size s-1vcpu-1gb \
  --ssh-keys <KEY_ID> --wait
doctl compute droplet list                        # note the public IPv4
```

**With the web UI:** Create > Droplets > Ubuntu 24.04 LTS > Basic, Regular SSD, the $6/mo
(1 GB / 1 vCPU) size > Authentication: SSH key (add yours) > hostname `school-ai` > Create.

### Cloud Firewall
22 from your IP only; 80 and 443 from anywhere.
```bash
MYIP=$(curl -s https://api.ipify.org)
doctl compute firewall create --name school-ai \
  --inbound-rules "protocol:tcp,ports:22,address:$MYIP/32 protocol:tcp,ports:80,address:0.0.0.0/0,address:::/0 protocol:tcp,ports:443,address:0.0.0.0/0,address:::/0" \
  --outbound-rules "protocol:tcp,ports:all,address:0.0.0.0/0,address:::/0 protocol:udp,ports:all,address:0.0.0.0/0,address:::/0 protocol:icmp,address:0.0.0.0/0,address:::/0" \
  --droplet-ids <DROPLET_ID>
```
UI: Networking > Firewalls > Create, same rules, apply to the droplet. If your home IP changes,
update the SSH rule. Port 443/UDP is not opened, so HTTP/3 is off; that's fine.

## 2. One-time bootstrap

```bash
export DROPLET_IP=203.0.113.7        # your droplet's IP
ssh root@$DROPLET_IP 'bash -s' <<'EOF'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl rsync unattended-upgrades

# Docker + compose plugin (official repo)
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Automatic security updates
dpkg-reconfigure -f noninteractive unattended-upgrades

# 1 GB swap: the image build is tight on 1 GB of RAM
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

mkdir -p /opt/school-ai
docker --version && docker compose version && free -h
EOF
```

## 3. First deploy

From the repo root on your Mac, with everything committed and `claude-key` present:
```bash
DROPLET_IP=$DROPLET_IP ./deploy/deploy.sh
```
It refuses to run with uncommitted changes, rsyncs the repo to `/opt/school-ai`, creates
`/opt/school-ai/.env` (API key streamed from `claude-key` over ssh, random `SESSION_SECRET`,
`DOMAIN`, mode 600), builds, starts, and waits up to 120 s for `https://<domain>/healthz`.
The first certificate takes a few seconds; the build takes a few minutes on this size.

## 4. Day-to-day

| Task | Command |
|---|---|
| Later deploys | `DROPLET_IP=$DROPLET_IP ./deploy/deploy.sh` (leaves `.env` alone) |
| Rotate the API key | Put the new key in `claude-key`, then `DROPLET_IP=$DROPLET_IP ./deploy/deploy.sh --rotate-key` |
| App logs | `ssh root@$DROPLET_IP 'cd /opt/school-ai && docker compose -f deploy/docker-compose.yml logs -f app'` |
| Caddy logs | same, with `logs -f caddy` |
| Status | `... docker compose -f deploy/docker-compose.yml ps` |
| Change a limit | edit `/opt/school-ai/.env` on the server (see `.env.example`), then `ssh root@$DROPLET_IP 'cd /opt/school-ai && docker compose -f deploy/docker-compose.yml up -d'` |

### Back up the SQLite volume
The data lives in the `school_data` volume (compose project `deploy`, so `deploy_school_data`).
Use SQLite's online backup so you never copy a half-written file:
```bash
ssh root@$DROPLET_IP 'cd /opt/school-ai && docker compose -f deploy/docker-compose.yml exec -T app \
  python -c "import sqlite3; s=sqlite3.connect(\"/app/data/school.db\"); d=sqlite3.connect(\"/app/data/backup.db\"); s.backup(d)"'
ssh root@$DROPLET_IP 'cd /opt/school-ai && docker compose -f deploy/docker-compose.yml cp app:/app/data/backup.db -' > school-backup.tar
```
(`cp ... -` streams a tar archive; `tar xf school-backup.tar` gives `backup.db`.) Admin edits and
Q/A logs live only in this file; the seed data can always be reloaded with the admin "reset".

### Roll back
Check out the previous commit locally and redeploy (the script deploys your working tree):
```bash
git log --oneline            # pick the good commit
git checkout <commit>
DROPLET_IP=$DROPLET_IP ./deploy/deploy.sh
git checkout main
```
The database volume is untouched by redeploys.

## 5. Tear down
Stop the app but keep data:
`ssh root@$DROPLET_IP 'cd /opt/school-ai && docker compose -f deploy/docker-compose.yml down'`.
Delete everything (data and certificates too): add `-v`. To stop paying, destroy the droplet and
the firewall:
```bash
doctl compute droplet delete school-ai
doctl compute firewall delete <FIREWALL_ID>
```
(UI: Droplet > Destroy; Networking > Firewalls > Delete.) Take a backup first if you want the data.

## Notes
- The app runs with exactly one worker because the per-IP rate limiter is in process memory.
  Restarting the container resets those counters.
- IPs are never stored; Caddy's access log is off by default.
- `sslip.io` is a third-party DNS service. If it is down, the site is unreachable by name; for a
  longer-lived setup use a real domain and set `DOMAIN` in `.env`.
- Let's Encrypt issues limits per hostname; don't recreate the droplet repeatedly with the same IP.
