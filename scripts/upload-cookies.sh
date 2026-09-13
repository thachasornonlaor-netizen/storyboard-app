#!/usr/bin/env bash
# Upload a YouTube cookies.txt file to the VM's AI service so yt-dlp can
# bypass YouTube's bot check on the Oracle datacenter IP.
#
# How to get cookies.txt:
#   1. Install the "Get cookies.txt LOCALLY" browser extension.
#   2. Open youtube.com while logged in to your Google account.
#   3. Click the extension on the YouTube tab -> Export (saves cookies.txt).
#
# Usage:   ./scripts/upload-cookies.sh [path/to/cookies.txt]
set -euo pipefail

VM_IP="${VM_IP:-168.138.44.196}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/oracle_vm}"
SSH_USER="${SSH_USER:-ubuntu}"
COOKIES="${1:-$PWD/ai-service/data/cookies.txt}"

[ -f "$COOKIES" ] || { echo "ERROR: no file at $COOKIES"; exit 1; }
head -1 "$COOKIES" | grep -q "Netscape HTTP Cookie File" \
    && echo "OK: looks like a real cookie file" \
    || echo "WARN: does not look like a Netscape cookie file"

echo "==> Uploading to VM"
scp -i "$SSH_KEY" "$COOKIES" "$SSH_USER@$VM_IP:/tmp/cookies.txt"
ssh -i "$SSH_KEY" "$SSH_USER@$VM_IP" \
    'sudo mkdir -p /opt/storyboard-app/ai-service/data && \
     sudo cp /tmp/cookies.txt /opt/storyboard-app/ai-service/data/cookies.txt && \
     sudo docker exec storyboard-app-ai-service-1 test -f /app/data/cookies.txt && \
     echo "OK: container can see cookies at /app/data/cookies.txt"'

echo "==> Done. Try a search now."
echo "Tip: cookies expire eventually - re-export and re-run this script when searches come back empty."