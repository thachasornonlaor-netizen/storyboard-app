# StoryboardAI

Find any movie, pull frames from its YouTube trailer, and turn them into a
storyboard in minutes. No editing software, no manual scrubbing through videos —
just search, pick your shots, and you're done.

## Quick Start

```bash
docker-compose up --build
```

Then open http://localhost:5173.

## Making the AI understand cinematography

Searching for a movie is easy. The interesting part is how the app figures out
*which* frames actually fit your shot — and that's where the two-stage pipeline
comes in:   ``

1. **CLIP** does the fast, cheap pass — it finds candidate frames that loosely
   match your description.
2. **Gemini** (a vision-language model) takes those candidates and re-ranks
   them by camera angle, shot size, lighting, and mood. This is the step that
   actually understands what you mean by "low angle close up at night, tense
   mood, neon lighting."

Don't worry about costs — Gemini's free tier is plenty for normal use. Grab a
free API key from https://aistudio.google.com/apikey and drop it in your `.env`:

```bash
echo "GEMINI_API_KEY=your_key_here" >> .env
```

Optional — override the model:

```bash
echo "GEMINI_MODEL=gemini-3.6-flash-lite" >> .env
```

No key? No problem. The app still works, it just falls back to CLIP-only
ranking.

## How It Works

1. **Search** — Type a movie name (e.g. "Inception", "Mad Max").
2. **Extract** — The app grabs the trailer and pulls out frames every few seconds.
3. **Browse** — Flip through all the frames in a grid.
4. **Build** — Click "+ Add to Storyboard" to put together your shot list.

Frames are cached locally, so repeat searches are instant.

## Tech Stack

- React + Vite (frontend)
- Node.js + Express (API proxy)
- Python + FastAPI + yt-dlp + ffmpeg (YouTube trailer frame extraction)
- Docker (deployment)
