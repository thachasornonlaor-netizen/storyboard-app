# Database Research: Best Sources for StoryboardAI Frame Data

## Project Context
StoryboardAI is an AI-powered storyboard tool that uses CLIP embeddings + ChromaDB to search curated movie frames by cinematographic metadata (camera_angle, shot_size, camera_movement, mood, tone, lighting).

Current dataset: 62 frames across 30 films in `frames.json` with no actual image files present.

---

## Top Options Ranked by Fit

### 1. ShotDeck (Best Overall Match)
- **URL:** https://shotdeck.com
- **Scale:** 1.1M+ HD stills from 5,000+ films, TV, commercials, music videos
- **Metadata:** 30+ categories hand-tagged per frame:
  - Camera: type, lens, focal length, aspect ratio
  - Lighting: style, direction, quality
  - Composition: framing, shot type, camera angle
  - Color: palette swatches (15 colors), temperature
  - Mood/emotion on actors' faces
  - Director, DP, crew credits
  - Genre, year, location
- **API:** `api.shotdeck.com` (documentation behind login)
- **Scraper:** https://github.com/mahmud3535/shotdeck-scraper (Selenium, MIT license)
- **Pricing:**
  - Free: 2-week trial
  - Monthly: $12.95/mo
  - Yearly: $99.95/yr ($8.33/mo, 36% savings)
  - Students: Discounted (contact them)
  - Enterprise: Custom
- **Verdict:** Best metadata-to-cost ratio. Tagging system maps directly to our `frames.json` schema.

---

### 2. types-of-film-shots (HuggingFace) — Best Free Dataset
- **URL:** https://huggingface.co/datasets/szymonrucinski/types-of-film-shots
- **Scale:** 54,312 film frames from film-grab.com
- **Metadata:**
  - `label`: closeUp, detail, extremeLongShot, fullShot, longShot, mediumCloseUp, mediumShot, ambiguous
  - `annotator`: human (863 gold-standard) or ai (DINOv2 + Opus review)
  - `confidence`: 0.0–1.0
  - `movie`: source film name
- **License:** CC-BY-4.0 (commercially usable!)
- **Pre-trained models:**
  - `pszemraj/beit-large-patch16-512-film-shot-classifier` (0.3B)
  - `pszemraj/dinov2-small-film-shot-classifier` (22M)
- **Verdict:** Free, large, CC-BY-4.0, pre-built classifiers. Only covers shot_size — need to add other metadata fields.

---

### 3. CineTechBench (HuggingFace) — Best Metadata Breadth
- **URL:** https://huggingface.co/datasets/Xinran0906/CineTechBench
- **ArXiv:** 2505.15145
- **Scale:** 600+ annotated movie images
- **Categories & Labels:**
  | Category | Labels |
  |---|---|
  | Scale | Extreme Close-Up, Close-Up, Medium Close-Up, Medium Shot, Medium Long Shot, Long Shot, Extreme Long Shot |
  | Angle | High Angle, Low Angle, Bird's Eye, Worm's Eye, Diagonal, Profile, Back Shot |
  | Composition | Central, Rule of Thirds, Diagonal, Framing, Symmetrical |
  | Lighting | High Key, Low Key, Hard Light, Soft Light, Side Light, Back Light, Top Light |
  | Color | Red, Blue, Green, Yellow, Black and White, etc. |
  | Focal Length | Wide, Standard, Medium, Telephoto |
  | Movement | Static, Pan, Tilt, Tracking, etc. |
- **License:** CC-BY-NC-ND-4.0 (non-commercial only!)
- **Note:** Dataset viewer broken on HuggingFace. Download raw files directly.
- **Verdict:** Richest metadata but non-commercial license. Good for schema mapping/bootstrapping.

---

### 4. FilmGrab (Free, No API)
- **URL:** https://film-grab.com
- **Scale:** Hundreds of curated films, high-quality frames
- **Metadata:** None (just film title + director)
- **Downloader:** https://github.com/roperi/film-grab-downloader (downloads galleries as zips)
- **Verdict:** Great raw image source. Combine with vision LLM to auto-tag metadata.

---

### 5. Flim.ai
- **URL:** https://flim.ai
- **Scale:** 2M+ frames (films, TV, commercials, music videos)
- **Features:** AI semantic search, color picker, frame size filter, similar images
- **API:** No public API
- **Pricing:** Freemium
- **Verdict:** Good for manual reference, no programmatic access.

---

### 6. StillsLab
- **URL:** https://stillslab.com
- **Scale:** Growing library with semantic search
- **Pricing:** Freemium
- **Verdict:** Newer platform, worth monitoring.

---

## Open Research Datasets

| Source | Frames | Metadata | License | URL |
|---|---|---|---|---|
| CineScale2 | 25,000 | Camera angle + level | Research | https://data.mendeley.com/datasets/h4n3gn93gz/3 |
| HISTORIAN | 10,593 shots | Shot boundaries, types, movements | Research | https://zenodo.org/records/6184281 |
| MovieNet | 1,100 movies | Characters, scenes, tags, cinematic style | Research | https://movienet.github.io |
| Flikforge Dataset | 5-30s clips | 50+ camera/lighting attributes | Rights-cleared | https://huggingface.co/datasets/forgemaster444/camera_and_lighting_controls |

---

## Not a Good Fit
- **Clip.Cafe** — Movie quotes/clips, not frames. Paid API, wrong metadata.
- **TMDb** — Movie metadata only, no frame images.
- **Kaggle movie datasets** — Text/metadata, no frames.

---

## Recommended Strategy

### Phase 1: Free Bootstrap
1. Download `types-of-film-shots` from HuggingFace (54k frames + shot_scale labels, CC-BY-4.0)
2. Use FilmGrab downloader to get high-res frames from specific films
3. Reuse pre-trained classifiers (`pszemraj/beit-large-patch16-512-film-shot-classifier`) for shot_size
4. Use vision LLM (GPT-4o / LLaVA) to auto-tag: camera_angle, mood, tone, lighting, camera_movement

### Phase 2: Premium Enrichment
1. Subscribe to ShotDeck ($100/yr)
2. Use scraper or API to pull frames with full 30-category metadata
3. Map ShotDeck categories to `frames.json` schema

### Phase 3: Pipeline Integration
1. Ingest frames into `ai-service/data/frames/`
2. Generate CLIP embeddings → ChromaDB
3. Update `frames.json` with all metadata fields
4. All existing search/filter code works as-is

---

## Key Schema Mapping

| Our Field | ShotDeck Tag | CineTechBench | types-of-film-shots |
|---|---|---|---|
| `shot_size` | Shot Type | Scale | label (closeUp, mediumShot, etc.) |
| `camera_angle` | Camera Angle | Angle | — |
| `camera_movement` | Camera Movement | Movement | — |
| `mood` | Emotion/Mood | — | — |
| `tone` | Color/Temperature | Color | — |
| `lighting` | Lighting Style | Lighting | — |
| `description` | Scene Description | — | — |
