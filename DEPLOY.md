# Deploy for Free (Netlify + Oracle Cloud)

Total cost: **$0/yr**. The site keeps running even when your computer is off.

```
Browser → Netlify (static frontend, https://yourname.netlify.app)
                │  calls VITE_API_URL
                ▼
     Oracle free VM → Caddy (:443, free Let's Encrypt via DuckDNS)
                     → backend (:3001) → ai-service (:8000)
                     → yt-dlp / ffmpeg / CLIP / Gemini
```

Why DuckDNS + Caddy: the frontend is served over HTTPS, so the browser
refuses to call a plain `http://<ip>:3001` backend (mixed content). Caddy
gets a real certificate for a free `<you>.duckdns.org` name and gives you
`https://` for $0. No custom domain needed.

---

## 1. Backend + AI service → Oracle Cloud "Always Free" VM

1. Sign up at https://cloud.oracle.com (free tier; asks for a card for
   identity only, never charges).
2. Create a Compute **Instance**:
   - Image: **Ubuntu 24.04** (or 22.04).
   - Shape: **VM.Standard.A1.Flex** (4 OCPU / 24 GB — the free ARM shape).
   - Boot volume ~ **47 GB**.
   - Under SSH keys, paste the **public** key (see `~/.ssh/oracle_vm.pub`
     on the machine that generated it).
   - Network → assign a **Reserved public IP** (so the address never changes).
3. Add firewall rules **before** the instance boots, or right after:
   - Networking → Virtual Cloud Network → Security List:
     allow TCP **80**, **443** (and **3001** if you want direct backend access).
4. Free hostname (**2 minutes**, no card): https://www.duckdns.org
   - Sign up, create subdomain e.g. `storyboardai.duckdns.org`, and point it
     at the VM's public IP in the DuckDNS dashboard.
5. Run the deploy script over SSH (automates everything: docker, repo,
   build, Caddy HTTPS, health check):

   ```bash
   ssh -i ~/.ssh/oracle_vm ubuntu@<vm-public-ip> \
     "sudo curl -fsSL https://raw.githubusercontent.com/thachasornonlaor-netizen/storyboard-app/main/scripts/deploy-vm.sh | sudo bash -s storyboardai.duckdns.org YOUR_REAL_GEMINI_KEY"
   ```

   No real key yet? Run without the last argument; the script prints the
   one-line command to add/change it afterwards.

   > The user on the VM is `ubuntu` (Ubuntu images) or `opc` (Oracle Linux).
   > Sub in whichever you picked.

6. Verify:
   ```bash
   curl -s https://storyboardai.duckdns.org/api/health
   # => {"status":"ok","model_ready":true,...,"vlm":{"configured":true,...}}
   ```
   `vlm.configured` must be `true` (means a real `AIza...` key was set).

---

## 2. Frontend → Netlify (free)

1. In `frontend/`, set the backend URL, then build:
   ```bash
   cd frontend
   npm install
   VITE_API_URL=https://storyboardai.duckdns.org npm run build
   ```
2. Drag-and-drop the `frontend/dist` folder into https://app.netlify.com
   (or connect the GitHub repo and set env var
   `VITE_API_URL = https://storyboardai.duckdns.org`, build `npm run build`,
   publish dir `dist`).
3. You get `https://yourname.netlify.app` — free HTTPS included. Done. Stay
   at $0: no custom domain purchase.

---

## Notes on the current live setup (Cloudflare Tunnel, no port opening)

The production backend runs on the Oracle VM behind a **Cloudflare quick
tunnel** (`cloudflared` auto-starts via a systemd service). This needs **no**
inbound firewall rules, DuckDNS, or Caddy:

    Browser → Netlify (frontend, https://framefinderai.netlify.app)
                │  calls VITE_API_URL (trycloudflare https URL)
                ▼
        cloudflared tunnel (VM) → backend :3001 → ai-service :8000
                                              → yt-dlp / ffmpeg / CLIP / Gemini

- Tunnel URL changes on VM reboot. Refresh it (rebuild + redeploy frontend):
  `./scripts/refresh-tunnel.sh`
- The Oracle IP is flagged by YouTube as a bot, so yt-dlp needs cookies:
  export `cookies.txt` (see `scripts/upload-cookies.sh`) and upload with
  `./scripts/upload-cookies.sh`. Re-upload when searches go empty again.

## Health checks

- Backend + AI: `https://storyboardai.duckdns.org/api/health`
  → `model_ready: true`, `vlm.configured: true` (real key set).
- Frontend: `https://yourname.netlify.app`

---

## Updating after code changes

Rebuild the stack on the VM (new code + real key if changed):

```bash
ssh -i ~/.ssh/oracle_vm ubuntu@<vm-public-ip> \
  "cd /opt/storyboard-app && sudo git pull && sudo docker compose -f docker-compose.onprem.yml up -d --build"
```

Redploy only the frontend by re-uploading `frontend/dist` to Netlify
(Netlify connected to GitHub redeploys automatically on push).

---

## Notes

- Oracle free ARM is always free; free *x86* VMs have a limited monthly
  allowance — use the **A1 ARM** shape for "free forever".
- Every search downloads a trailer + extracts frames, so bandwidth and CPU
  are used per search — normal, just slower on a free VM (still works).
- Caddy auto-renews the Let's Encrypt certificate; no maintenance.
- `docker restart:unless-stopped` + enabled services = survives reboots.