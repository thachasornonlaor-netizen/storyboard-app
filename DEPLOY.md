# Deploy for Free (Netlify + Oracle Cloud)

Total cost: **$0/yr**. The site keeps running even when your computer is off.

Architecture:

```
Browser → Netlify (static frontend, https://yourname.netlify.app)
                │  (calls VITE_API_URL)
                ▼
          Oracle free VM → backend (:3001) → ai-service (:8000)
                        → yt-dlp / ffmpeg / CLIP / Gemini
```

---

## 1. Backend + AI service → Oracle Cloud "Always Free" VM

1. Sign up at https://cloud.oracle.com (free tier; asks for a card for
   identity only, never charges).
2. Create a VM:
   - Shape: **VM.Standard.A1.Flex** (4 OCPU / 24 GB — the free ARM shape).
   - Ubuntu 22.04+, disk ~50 GB.
   - Attach a **static public IP** (Network → Reserved Public IP).
   - Firewall/NSG: allow TCP **3001**.
3. SSH into the VM and run:

   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
   sudo systemctl enable --now docker

   git clone <your-repo-url>
   cd storyboard-app

   # real Gemini key (free from https://aistudio.google.com/apikey)
   echo "GEMINI_API_KEY=your_real_key" > .env

   sudo docker compose -f docker-compose.onprem.yml up -d --build

   # check it's healthy
   curl http://localhost:3001/api/health
   ```

   The compose file has `restart: unless-stopped`, so it survives VM reboots.

> Optional: put Caddy in front for HTTPS to the backend:
> `sudo apt install -y caddy` then
> `echo "<backend.yourname.com> { reverse_proxy localhost:3001 }" | sudo tee /etc/caddy/Caddyfile`
> and set `<backend.yourname.com>` to the VM IP.

---

## 2. Frontend → Netlify (free)

1. Build locally with the backend URL, or set it as a build var on Netlify:

   ```bash
   cd frontend
   npm install
   VITE_API_URL=https://<your-vm-public-ip>:3001 npm run build
   # dist/ is now production-ready
   ```

   Or point Netlify at your GitHub repo and set env var
   `VITE_API_URL = https://<your-vm-public-ip>:3001` plus build command
   `npm run build` and publish dir `dist`.

2. Drag-and-drop `frontend/dist` into https://app.netlify.com (or use Git).
   You get `https://yourname.netlify.app` — free HTTPS included.

3. Done. No custom domain needed; skip it and stay at $0.

---

## Health checks

- Backend: `https://<vm-ip>:3001/api/health`
- AI service VLM status: `https://<vm-ip>:3001/api/health` → `vlm.configured`
  must be `true` (i.e. a real `GEMINI_API_KEY`, not the placeholder).

Set a real Gemini key or matching quality drops to CLIP-only (weak).

---

## Notes

- Oracle free ARM is always free; free *x86* VMs have a limited monthly
  allowance — use the A1 ARM shape for "free forever".
- Every search downloads a trailer + extracts frames, so bandwidth and CPU
  are used per search — normal, just slower on a free VM (still works).