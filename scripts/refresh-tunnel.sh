#!/usr/bin/env bash
# Re-point the frontend at the current Cloudflare tunnel URL and redeploy to Netlify.
# Only needed after the Oracle VM reboots (trycloudflare gives a new URL each restart).
#
# Usage:   ./scripts/refresh-tunnel.sh
# Requires: netlify-cli (authed) and the cloudflared systemd service on the VM.
set -euo pipefail

VM_IP="${VM_IP:-168.138.44.196}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/oracle_vm}"
SSH_USER="${SSH_USER:-ubuntu}"
NETLIFY_SITE_ID="${NETLIFY_SITE_ID:-157ec7c3-457f-481d-b55e-0e9c7ec01b2a}"
NETLIFY="${NETLIFY:-$HOME/.local/bin/netlify}"
[ -x "$NETLIFY" ] || NETLIFY="netlify"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND="$ROOT/frontend"

echo "==> Waiting for tunnel URL (up to 60s)"
URL=""
for _ in $(seq 1 12); do
    URL="$(ssh -i "$SSH_KEY" -o ConnectTimeout=10 "$SSH_USER@$VM_IP" \
        'grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" /var/log/cloudflared.log 2>/dev/null | tail -1' 2>/dev/null || true)"
    [ -n "$URL" ] && break
    sleep 5
done
[ -n "$URL" ] || { echo "ERROR: no tunnel URL found. VM reachable? cloudflared-tunnel service running?"; exit 1; }
echo "Tunnel URL: $URL"

echo "==> Building frontend against $URL"
[ -f "$FRONTEND/package-lock.json" ] || (cd "$FRONTEND" && npm install)
VITE_API_URL="$URL" npm --prefix "$FRONTEND" run build

echo "==> Deploying to Netlify ($NETLIFY_SITE_ID)"
"$NETLIFY" deploy --prod --dir="$FRONTEND/dist" --site "$NETLIFY_SITE_ID" --json

echo "==> Done. Site: https://framefinderai.netlify.app"