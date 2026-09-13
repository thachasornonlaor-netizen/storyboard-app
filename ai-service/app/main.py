import os
import re
import time
import json
import threading
import subprocess
import tempfile
from typing import List
from uuid import uuid4
import numpy as np
import clip
import torch
from PIL import Image
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from filter_parser import parse_filters_from_text, FILTER_SYNONYMS, CATEGORIES
from vision import (
    compute_composition_features,
    score_shot_size_geometry,
    score_camera_angle_geometry,
)
import vlm

device = "cuda" if torch.cuda.is_available() else "cpu"
model = None
preprocess = None
model_ready = threading.Event()

EXTRACTED_DIR = "/app/data/extracted_frames"
os.makedirs(EXTRACTED_DIR, exist_ok=True)

TEMP_VIDEO_DIR = "/tmp/storyboard_videos"
os.makedirs(TEMP_VIDEO_DIR, exist_ok=True)

MAX_VIDEOS_TO_PROCESS = 5
FRAME_INTERVAL = 60
TOP_FRAMES_PER_VIDEO = 8
MAX_RESULTS = 24
COOKIES_FILE = "/app/data/cookies.txt"

def _cookies_args():
    if os.path.exists(COOKIES_FILE):
        return ["--cookies", COOKIES_FILE]
    return []

def slugify(text):
    s = text.lower().strip()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    return s.strip('_')

STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "at", "with", "and", "or", "but",
    "to", "for", "from", "into", "over", "under", "during", "while", "through",
    "shot", "shots", "scene", "scenes", "frame", "still", "looking", "shows",
    "cinematic", "film", "movie", "camera", "angle", "angles", "view", "views",
    "mood", "moods", "tone", "tones", "lighting", "style", "very", "really",
    "some", "one", "two", "use", "using", "show", "like", "just", "you", "your",
}

CINEMA_WORDS = set(STOPWORDS)
for _cat in CATEGORIES:
    for _phrase, _val in FILTER_SYNONYMS[_cat]:
        for _tok in _phrase.split():
            CINEMA_WORDS.add(_tok)


def extract_search_keywords(text):
    """Pull the subject nouns out of a shot description so it can be used as a
    YouTube trailer search. Only multi-word cinematography phrases are removed
    (e.g. "low angle", "close up") so useful subject words like "night" or
    "neon" survive.

    "low angle close up of a car at night, tense mood, neon lighting"
    -> "car night neon lighting tense mood"  (subject + descriptive keywords)
    """
    if not text:
        return ""
    lowered = text.lower()
    for _cat in CATEGORIES:
        for _phrase, _val in FILTER_SYNONYMS[_cat]:
            if _phrase.count(" ") >= 1:
                lowered = re.sub(rf"\b{re.escape(_phrase)}\b", " ", lowered)
    tokens = re.findall(r"[a-z0-9]+", lowered)
    kept = [
        t for t in tokens
        if len(t) >= 3 and t not in STOPWORDS
    ]
    return " ".join(dict.fromkeys(kept))


NON_MOVIE_MARKERS = (
    "music video", "official mv", "gameplay", "reaction", "let's play",
    "lego", "minecraft", "gta", "fortnite", "roblox", "explained",
    "review", "analysis", "cgi animation", "blender", "3d animation",
    "short film", "animation demo", "modeling",
)


def _looks_like_non_movie(title):
    low = title.lower()
    return any(m in low for m in NON_MOVIE_MARKERS)


def search_youtube(query, max_results=12):
    """Find movie trailers/teasers for the query, falling back to real movie
    scene clips when a shot description has no trailer to point at.

    Trailers are always preferred and processed first. Scene clips only enter
    the pool when fewer than 3 trailers are found, so a shot like "car chase at
    night" still gets real cinematic footage to match against.
    """
    keywords = extract_search_keywords(query)
    base = keywords or query

    trailer_queries = [
        f"{base} official trailer",
        f"{base} teaser",
        f"{base} movie trailer",
        f"{base} trailer",
    ]
    scene_queries = [
        f"{base} movie scene",
        f"{base} movie clip",
        f"{base} scene film",
    ]

    trailer_ids = {}
    scene_ids = {}

    def run_search(search_query, allow_scenes):
        stdout = ""
        for attempt in range(3):
            try:
                proc = subprocess.Popen(
                    ["yt-dlp",
                     "--print", "%(id)s\t%(title)s\t%(duration)s",
                     "--no-warnings", "--ignore-errors",
                     "--remote-components", "ejs:github",
                     *_cookies_args(), *_proxy_args(),
                     f"ytsearch{max_results}:{search_query}"],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
                )
                try:
                    stdout, _ = proc.communicate(timeout=45)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, _ = proc.communicate()
            except Exception:
                stdout = ""
            if stdout:
                break
            if attempt < 2:
                time.sleep(4)
        if not stdout:
            return
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            video_id = parts[0]
            title = parts[1]
            duration = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 0
            if _looks_like_non_movie(title):
                continue
            if not (60 <= duration < 600):
                continue
            lower = title.lower()
            is_trailer = "trailer" in lower or "teaser" in lower
            if video_id in trailer_ids:
                continue
            if is_trailer:
                if video_id in scene_ids:
                    scene_ids.pop(video_id, None)
                trailer_ids[video_id] = (video_id, title, duration)
            elif allow_scenes and video_id not in scene_ids:
                scene_ids[video_id] = (video_id, title, duration)

    for q in trailer_queries:
        run_search(q, allow_scenes=False)
        if len(trailer_ids) >= 5:
            break

    if len(trailer_ids) < 3:
        for q in scene_queries:
            run_search(q, allow_scenes=True)
            if len(trailer_ids) + len(scene_ids) >= 6:
                break

    trailers = list(trailer_ids.values())
    trailers.sort(key=lambda v: (0 if "official" in v[1].lower() else 1, v[1].lower()))
    scenes = list(scene_ids.values())
    videos = trailers + scenes
    return videos

def _proxy_args():
    proxy = os.environ.get("YT_PROXY", "").strip()
    return ["--proxy", proxy] if proxy else []


DOWNLOAD_CLIENTS = ["android", "tv_embedded", "mweb", "web", "tv", "ios"]


def download_video(video_id):
    output_path = os.path.join(TEMP_VIDEO_DIR, f"{video_id}.mp4")
    if os.path.exists(output_path):
        return output_path

    # YouTube periodically force-flags datacenter IPs with a bot challenge that
    # answers "Sign in to confirm you're not a bot". It's time-varying: retry
    # across player clients with short backoff until one slips through.
    last_err = ""
    for attempt in range(3):
        for client in DOWNLOAD_CLIENTS:
            base_args = [
                "yt-dlp",
                "-f", "b[height<=480][ext=mp4]/best[ext=mp4]/best",
                "-o", output_path,
                "--no-warnings", "--ignore-errors",
                "--retries", "3", "--fragment-retries", "3",
                "--remote-components", "ejs:github",
                "--extractor-args", f"youtube:player_client={client}",
                *_cookies_args(), *_proxy_args(),
                f"https://www.youtube.com/watch?v={video_id}",
            ]
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            try:
                proc = subprocess.Popen(
                    base_args,
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
                )
                try:
                    _, stderr = proc.communicate(timeout=180)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    last_err = "timeout"
                    continue
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                    return output_path
                if stderr:
                    last_err = stderr.strip()[-300:]
            except Exception as e:
                last_err = str(e)
        print(f"  (attempt {attempt + 1}/3 failed for {video_id})")
        time.sleep(6)

    print(f"  yt-dlp error for {video_id}: {last_err}")
    return None

def get_video_info(video_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate,duration",
         "-of", "json", video_path],
        capture_output=True, text=True, timeout=15
    )
    try:
        info = json.loads(result.stdout)
        stream = info.get("streams", [{}])[0]
        r_frame_rate = stream.get("r_frame_rate", "30/1")
        num, den = r_frame_rate.split("/")
        fps = float(num) / float(den) if float(den) > 0 else 30
        duration = float(stream.get("duration", 0))
        return fps, duration
    except Exception:
        return 30, 0

def extract_frames(video_path):
    frames = []
    fps, duration = get_video_info(video_path)
    if fps <= 0:
        fps = 30

    extract_fps = max(0.5, fps / FRAME_INTERVAL)
    tmp_dir = tempfile.mkdtemp()
    out_pattern = os.path.join(tmp_dir, "frame_%06d.jpg")

    try:
        subprocess.run(
            ["ffmpeg", "-i", video_path, "-vf", f"fps={extract_fps}",
             "-q:v", "3", out_pattern],
            capture_output=True, timeout=300
        )

        frame_files = sorted(os.listdir(tmp_dir))
        for i, fname in enumerate(frame_files):
            fpath = os.path.join(tmp_dir, fname)
            try:
                img = Image.open(fpath).convert("RGB")
                timestamp = i / extract_fps
                frames.append((img, timestamp))
            except Exception:
                pass
            os.remove(fpath)
    except Exception:
        pass

    try:
        os.rmdir(tmp_dir)
    except Exception:
        pass

    return frames

def _dhash_bits(pil_img, hash_size=9):
    """Perceptual hash (gradient hash). 9x8 grayscale -> 72 bits."""
    small = pil_img.convert("L").resize((hash_size + 1, hash_size), Image.LANCZOS)
    arr = np.asarray(small, dtype=np.int16)
    return (arr[:, 1:] > arr[:, :-1]).flatten()

def _hamming(a, b):
    return int((a != b).sum())

def dedupe_similar_frames(scored_frames, similarity_threshold=18):
    """Thin out near-identical frames so the top-N isn't wasted on duplicates.

    scored_frames is a list of (img, timestamp, score) tuples. Frames that are
    perceptually indistinguishable from a higher-scoring frame already selected
    are dropped. Kept frames preserve their original scores.
    """
    ordered = sorted(scored_frames, key=lambda x: -x[2])
    hashes = []
    kept = []
    for img, ts, score in ordered:
        h = _dhash_bits(img)
        if any(_hamming(h, kh) <= similarity_threshold for kh in hashes):
            continue
        hashes.append(h)
        kept.append((img, ts, score))
    return kept

def score_frames_batch_multi(frames_pil, text_queries):
    if model is None or preprocess is None or not frames_pil or not text_queries:
        return [[0.5] * len(frames_pil) for _ in text_queries] if text_queries else []
    try:
        image_inputs = torch.stack([preprocess(img) for img in frames_pil]).to(device)
        texts = clip.tokenize(text_queries).to(device)
        with torch.no_grad():
            img_features = model.encode_image(image_inputs)
            text_features = model.encode_text(texts)
        img_features = img_features / img_features.norm(dim=-1, keepdim=True)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        similarities = img_features @ text_features.T
        results = []
        for t_idx in range(len(text_queries)):
            scores = [(similarities[i, t_idx].item() + 1) / 2 for i in range(len(frames_pil))]
            results.append([max(0.0, min(1.0, s)) for s in scores])
        return results
    except Exception:
        return [[0.0] * len(frames_pil) for _ in text_queries]

def save_frame(pil_img, video_id, timestamp):
    filename = f"{video_id}_{timestamp:.2f}.jpg"
    filepath = os.path.join(EXTRACTED_DIR, filename)
    pil_img.save(filepath, "JPEG", quality=85)
    return filename

def analyze_image_properties(pil_img):
    arr = np.array(pil_img).astype(np.float32) / 255.0
    h, w = arr.shape[:2]
    if h == 0 or w == 0:
        return {}
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    avg_lum = float(np.mean(lum))
    std_lum = float(np.std(lum))
    hsv_r, hsv_g, hsv_b = r, g, b
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin
    sat = np.where(delta > 0, delta / (cmax + 1e-10), 0)
    avg_sat = float(np.mean(sat))
    warm_mask = (r > g) & (r > b) & (lum > 0.15)
    if np.sum(warm_mask) > 10:
        warm_ratio = float(np.mean(r[warm_mask] / (b[warm_mask] + 1e-10)))
    else:
        warm_ratio = 1.0
    return {
        "avg_lum": avg_lum,
        "std_lum": std_lum,
        "avg_sat": avg_sat,
        "warm_ratio": warm_ratio
    }

def score_tone_filter(filter_val, props):
    avg_lum = props["avg_lum"]
    std_lum = props["std_lum"]
    avg_sat = props["avg_sat"]
    warm_ratio = props["warm_ratio"]
    scoring = {
        "dark": max(0, 1 - avg_lum / 0.35) ** 1.5,
        "bright": max(0, (avg_lum - 0.55) / 0.45) ** 1.5,
        "muted": max(0, 1 - avg_sat / 0.25) ** 1.5,
        "vibrant": max(0, (avg_sat - 0.35) / 0.65) ** 1.5,
        "cold": max(0, 1 - warm_ratio / 1.1) ** 1.5,
        "warm": max(0, (warm_ratio - 1.1) / 2.0) ** 1.5,
        "monochrome": max(0, 1 - avg_sat / 0.08) ** 2.0,
        "desaturated": max(0, 1 - avg_sat / 0.18) ** 1.5,
        "neon": max(0, (avg_sat - 0.55) / 0.45) ** 1.5 * max(0, (warm_ratio - 1.5) / 2.0) ** 0.5 if avg_sat > 0.4 else 0,
        "tungsten": max(0, (warm_ratio - 1.5) / 2.0) ** 1.5 * max(0, 1 - avg_lum / 0.5) ** 0.5,
        "golden_hour": max(0, (warm_ratio - 1.8) / 2.5) ** 1.5 * max(0, (avg_lum - 0.3) / 0.5) ** 1.0,
        "naturalistic": max(0, 1 - abs(avg_lum - 0.5) / 0.3) ** 1.5 * max(0, 1 - abs(avg_sat - 0.3) / 0.25) ** 1.0,
        "high_contrast": max(0, (std_lum - 0.15) / 0.35) ** 1.5,
        "overexposed": max(0, (avg_lum - 0.75) / 0.25) ** 2.0,
        "underwater": max(0, 1 - avg_lum / 0.5) ** 0.5 * max(0, (warm_ratio - 1.0) / 1.5) ** 1.0 * max(0, 1 - avg_sat / 0.4) ** 0.5 if avg_lum < 0.6 else 0,
        "fluorescent": max(0, 1 - warm_ratio / 1.0) ** 2.0 * max(0, (avg_lum - 0.4) / 0.5) ** 1.0,
    }
    return min(1.0, scoring.get(filter_val, 0.5))

def score_lighting_filter(filter_val, props):
    avg_lum = props["avg_lum"]
    std_lum = props["std_lum"]
    avg_sat = props["avg_sat"]
    warm_ratio = props["warm_ratio"]
    contrast = std_lum / (avg_lum + 0.01)
    scoring = {
        "low_key": max(0, (contrast - 0.6) / 1.5) ** 1.5 * max(0, 1 - avg_lum / 0.4) ** 1.0,
        "high_key": max(0, 1 - contrast / 0.5) ** 1.5 * max(0, (avg_lum - 0.55) / 0.45) ** 1.0,
        "natural": max(0, 1 - abs(avg_lum - 0.5) / 0.35) ** 1.0 * max(0, 1 - contrast / 0.6) ** 0.5,
        "artificial": max(0, (contrast - 0.3) / 0.8) ** 0.5 * max(0, 1 - abs(warm_ratio - 1.3) / 1.0) ** 0.5,
        "moonlight": max(0, 1 - avg_lum / 0.25) ** 2.0 * max(0, 1 - warm_ratio / 1.0) ** 1.5,
        "neon": max(0, (avg_sat - 0.5) / 0.5) ** 1.5 * max(0, (warm_ratio - 1.5) / 2.0) ** 0.5 if avg_sat > 0.4 else 0,
        "spotlight": max(0, (contrast - 0.6) / 1.5) ** 2.0,
        "backlit": max(0, (contrast - 0.4) / 1.0) ** 1.0 * max(0, 1 - avg_lum / 0.4) ** 0.5 if avg_lum < 0.5 else 0,
        "candlelight": max(0, (warm_ratio - 1.8) / 2.5) ** 2.0 * max(0, 1 - avg_lum / 0.3) ** 1.5,
        "diffused": max(0, 1 - contrast / 0.4) ** 2.0 * max(0, 1 - abs(avg_lum - 0.5) / 0.3) ** 0.5,
    }
    return min(1.0, scoring.get(filter_val, 0.5))

def format_timestamp(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def cleanup_old_files(max_age=3600):
    now = time.time()
    for fname in os.listdir(EXTRACTED_DIR):
        fpath = os.path.join(EXTRACTED_DIR, fname)
        if os.path.isfile(fpath) and now - os.path.getmtime(fpath) > max_age:
            os.remove(fpath)
    for fname in os.listdir(TEMP_VIDEO_DIR):
        fpath = os.path.join(TEMP_VIDEO_DIR, fname)
        if os.path.isfile(fpath) and now - os.path.getmtime(fpath) > max_age:
            os.remove(fpath)

def load_clip_model():
    global model, preprocess
    try:
        model, preprocess = clip.load("ViT-B/16", device=device)
        model_ready.set()
        print(f"CLIP ViT-B/16 model loaded on {device}")
    except Exception as e:
        print(f"CLIP load failed: {e}")

FILTER_OPTIONS = {
    "camera_angle": [
        "eye_level", "low_angle", "high_angle", "birds_eye", "dutch_angle",
        "worms_eye", "aerial", "shoulder_level", "hip_level",
        "over_the_shoulder", "point_of_view", "establishing"
    ],
    "shot_size": [
        "extreme_close_up", "close_up", "medium_close_up", "medium",
        "medium_wide", "wide", "extreme_wide", "insert", "two_shot"
    ],
    "camera_movement": [
        "static", "tracking", "handheld", "steadicam", "crane",
        "dolly_in", "push_in", "slow_pan", "orbit", "zoom_in",
        "snap_zoom", "vertigo"
    ],
    "mood": [
        "tense", "peaceful", "melancholic", "joyful", "ominous",
        "romantic", "chaotic", "mysterious", "eerie", "dread",
        "somber", "electric", "surreal", "claustrophobic", "gritty",
        "hopeful", "whimsical"
    ],
    "tone": [
        "dark", "bright", "muted", "vibrant", "cold", "warm",
        "monochrome", "desaturated", "neon", "tungsten",
        "golden_hour", "naturalistic", "high_contrast",
        "overexposed", "underwater", "fluorescent"
    ],
    "lighting": [
        "low_key", "high_key", "natural", "artificial", "moonlight",
        "neon", "spotlight", "backlit", "candlelight", "diffused"
    ]
}

FILTER_PROMPTS = {
    "camera_angle": {
        "eye_level": "cinematic film still, eye level camera shot, camera at the subject's eye height, straight on neutral perspective, lens pointing horizontally",
        "low_angle": "cinematic film still, dramatic low angle shot, camera looking up at the subject from below, subject towering above the camera, upward perspective, imposing hero framing",
        "high_angle": "cinematic film still, high angle shot, camera positioned above the subject looking down, subject appears small and vulnerable below the camera, downward perspective",
        "birds_eye": "cinematic film still, birds eye view, camera directly overhead looking straight down at the scene, top down aerial perspective, flat composition",
        "dutch_angle": "cinematic film still, dutch angle shot, tilted canted camera with skewed horizon line, unbalanced diagonal composition, disorienting off-kilter framing",
        "worms_eye": "cinematic film still, worms eye view, extreme low angle camera at ground level looking straight up, vertical upward perspective toward the sky",
        "aerial": "cinematic film still, sweeping aerial shot from high above, drone or helicopter view of a vast landscape, expansive overhead establishing view",
        "shoulder_level": "cinematic film still, over the shoulder shot, camera positioned behind one character's shoulder, foreground blur of the shoulder, focus on the other character",
        "hip_level": "cinematic film still, hip level shot, camera positioned at hip height of the subject, cowboy framing, western style neutral perspective",
        "over_the_shoulder": "cinematic film still, over the shoulder shot, back of a character's head and shoulder in the foreground edge of frame, facing the other character",
        "point_of_view": "cinematic film still, point of view shot, the camera shows exactly what a character sees, first person perspective, character's viewpoint",
        "establishing": "cinematic film still, establishing wide shot, broad overview of the full location setting, environment and surrounding context clearly visible"
    },
    "shot_size": {
        "extreme_close_up": "cinematic film still, extreme close up, very tight framing filling the frame with a single small detail like an eye, mouth, or object, magnified intimate detail",
        "close_up": "cinematic film still, close up shot, the subject's face fills most of the frame, tight framing from chin to top of head, showing emotion and detail",
        "medium_close_up": "cinematic film still, medium close up shot, framing from chest up, head and shoulders visible, tighter than a medium shot but wider than a close up",
        "medium": "cinematic film still, medium shot, framing from the waist up, hands and torso visible, standard conversational distance between camera and subject",
        "medium_wide": "cinematic film still, medium wide shot, framing from the knees up, full upper body visible with some surrounding environment",
        "wide": "cinematic film still, wide shot, the full body of the subject visible from head to toe, surrounded by the environment, room to move in frame",
        "extreme_wide": "cinematic film still, extreme wide shot, vast view where the subject is very small within a large landscape, tiny figure in a huge environment",
        "insert": "cinematic film still, insert shot, tight close up on a specific object, prop, or small detail, emphasizing an important element, macro detail",
        "two_shot": "cinematic film still, two shot, two characters both visible in the same frame together, showing their interaction and relationship"
    },
    "camera_movement": {
        "static": "cinematic film still, static locked off camera, completely still tripod framing, no motion blur, stable fixed composition",
        "tracking": "cinematic film still, tracking shot, camera moving sideways alongside a moving subject, lateral motion blur, following the action",
        "handheld": "cinematic film still, handheld camera shot, slightly shaky amateur framing, documentary style motion blur, raw unstable frame",
        "steadicam": "cinematic film still, smooth steadicam shot, fluid gliding camera movement following a subject, stable motion with slight dynamic angle",
        "crane": "cinematic film still, crane shot, camera moving vertically upward or downward on a crane arm, sweeping elevation change over the scene",
        "dolly_in": "cinematic film still, dolly in shot, camera moving closer toward the subject, intensifying focus, the subject growing larger in frame",
        "push_in": "cinematic film still, slow push in, gradual camera movement toward the subject building emotional intensity, subject filling more of the frame",
        "slow_pan": "cinematic film still, slow pan, camera rotating horizontally across the scene, sweeping view revealing the environment sideways",
        "orbit": "cinematic film still, orbiting camera, circular movement around the subject, dynamic rotating perspective, subject at the center",
        "zoom_in": "cinematic film still, zoom in, focal length increasing to magnify the subject, subject getting larger while background compresses",
        "snap_zoom": "cinematic film still, rapid snap zoom, sudden dramatic lens zoom creating a jarring punch-in effect, quick emphasis on the subject",
        "vertigo": "cinematic film still, vertigo dolly zoom effect, background warping while subject stays the same size, distorted stretched perspective"
    },
    "mood": {
        "tense": "tense suspenseful atmosphere, dramatic high stakes tension, anxious anticipation, tight gripping mood, uneasy quiet before conflict",
        "peaceful": "peaceful calm atmosphere, serene tranquil scene, gentle relaxing mood, soft quiet stillness, balanced harmonious feeling",
        "melancholic": "melancholic mood, wistful sorrowful atmosphere, gentle sadness, nostalgic longing, quiet emotional depth, thoughtful sadness",
        "joyful": "joyful mood, happy cheerful scene, bright positive energy, warm delightful feeling, uplifting laughter and light",
        "ominous": "ominous mood, threatening foreboding atmosphere, sense of approaching danger, dark warning, menacing shadow over the scene",
        "romantic": "romantic mood, intimate loving atmosphere, warm tender connection, soft affectionate feeling, closeness between characters",
        "chaotic": "chaotic mood, frenetic disordered scene, wild unpredictable energy, confusion, turmoil, rapid frantic action",
        "mysterious": "mysterious mood, enigmatic puzzling atmosphere, hidden secrets, intrigue, uncertain unknown elements, curiosity and suspense",
        "eerie": "eerie mood, uncanny unsettling atmosphere, strange creepy feeling, supernatural unease, quiet wrongness in the scene",
        "dread": "dread mood, deep fear and doom, terrifying oppressive atmosphere, overwhelming dread, horror closing in",
        "somber": "somber mood, serious grave atmosphere, heavy solemn feeling, mournful respectful tone, subdued sorrow",
        "electric": "electric mood, crackling energetic atmosphere, excitement and anticipation, charged vibrant energy, adrenaline",
        "surreal": "surreal mood, dreamlike unreal atmosphere, bizarre impossible imagery, nightmarish fantasy, altered reality",
        "claustrophobic": "claustrophobic mood, confined tight space, feeling trapped, oppressive enclosure, walls closing in, breathless tension",
        "gritty": "gritty mood, raw rough atmosphere, urban decay, harsh realism, unpolished dirty textures, tough world-weary feeling",
        "hopeful": "hopeful mood, optimistic uplifting atmosphere, light breaking through, looking forward to something better, inspiring and warm",
        "whimsical": "whimsical mood, playful fanciful atmosphere, lighthearted magic, charming delight, curious wonder, imaginative joy"
    },
    "tone": {
        "dark": "dark tone, low brightness, deep black shadows, noir feeling, dimly lit frame, heavy shadow, little light",
        "bright": "bright tone, well lit frame, high brightness, clear daylight, open airy scene, white highlights, sunny",
        "muted": "muted tone, desaturated subdued colors, soft restrained palette, gentle color grading, subtle washed tones",
        "vibrant": "vibrant tone, highly saturated rich colors, bold vivid palette, intense saturated hues, colorful energetic image",
        "cold": "cold tone, blue color cast, cool temperature palette, icy blue hues, cold clinical steel blue feel",
        "warm": "warm tone, orange and amber color cast, golden sunlight warmth, cozy inviting warm palette, rich orange glow",
        "monochrome": "monochrome tone, black and white, grayscale palette, no color, classic film noir look, silver and charcoal",
        "desaturated": "desaturated tone, washed out pale colors, low saturation, faded vintage look, soft gray tones",
        "neon": "neon tone, electric glowing neon colors, cyberpunk aesthetic, bright artificial colorful glow, saturated neon signage",
        "tungsten": "tungsten tone, warm orange indoor lighting, practical lamp glow, amber incandescent light, cozy yellow warmth",
        "golden_hour": "golden hour tone, warm golden sunlight, sunset glow, rich amber orange hues, low sun casting long warm light",
        "naturalistic": "naturalistic tone, true to life colors, natural neutral grading, realistic unaltered appearance, balanced colors",
        "high_contrast": "high contrast tone, strong difference between light and dark, deep black shadows, bright white highlights, punchy contrast",
        "overexposed": "overexposed tone, intentionally too bright, blown out white highlights, washed out hazy image, ethereal light",
        "underwater": "underwater tone, blue green color cast, diffused soft light, aquatic submerged look, teal green depth",
        "fluorescent": "fluorescent tone, cold greenish white light, office institutional lighting, sterile cool tube light, flat sickly color"
    },
    "lighting": {
        "low_key": "low key lighting, strong chiaroscuro, high contrast shadows, dark moody illumination, dramatic noir lighting, pools of darkness",
        "high_key": "high key lighting, very bright even illumination, minimal shadows, upbeat clean bright lighting, soft white light",
        "natural": "natural lighting, sunlight illumination, organic soft daylight, warm sun rays, window light, realistic outdoor light",
        "artificial": "artificial lighting, man made lamp light, fixtures and bulbs, studio lighting feel, practical household lamps",
        "moonlight": "moonlight lighting, cool blue night illumination, silvery pale glow, dim nocturnal light, moonlit scene",
        "neon": "neon lighting, glowing electric signs, colorful artificial light, bright saturated neon glow, cyberpunk illumination",
        "spotlight": "spotlight lighting, single focused beam of light, subject isolated in a pool of light, stage spotlight, dark surroundings",
        "backlit": "backlit lighting, strong light source behind the subject, silhouetted figure, bright rim light glow, halo around edges",
        "candlelight": "candlelight lighting, warm flickering flame light, intimate dim orange glow, soft dancing shadows, cozy firelight",
        "diffused": "diffused lighting, soft scattered light, gentle even illumination, minimal harsh shadows, overcast softbox lighting"
    }
}

@asynccontextmanager
async def lifespan(app):
    threading.Thread(target=load_clip_model, daemon=True).start()
    cleanup_old_files(max_age=0)
    yield
    cleanup_old_files(max_age=0)

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.mount("/frames", StaticFiles(directory=EXTRACTED_DIR), name="extracted_frames")

JOBS = {}
JOBS_LOCK = threading.Lock()
JOB_TTL_SECONDS = 1800


def _run_search_pipeline(
    q="", film="",
    camera_angle=None, shot_size=None, camera_movement=None,
    mood=None, tone=None, lighting=None,
):
    camera_angle = camera_angle or []
    shot_size = shot_size or []
    camera_movement = camera_movement or []
    mood = mood or []
    tone = tone or []
    lighting = lighting or []

    if not q.strip() and not film:
        return {"frames": []}

    if film:
        search_text = film
        main_query = film
        parse_text = ""
    else:
        search_text = q.strip()
        main_query = q.strip()
        parse_text = search_text

    active_filters = {
        "camera_angle": [v for v in camera_angle if v.strip()],
        "shot_size": [v for v in shot_size if v.strip()],
        "camera_movement": [v for v in camera_movement if v.strip()],
        "mood": [v for v in mood if v.strip()],
        "tone": [v for v in tone if v.strip()],
        "lighting": [v for v in lighting if v.strip()],
    }
    active_filters = {k: v for k, v in active_filters.items() if v}

    # Interpret cinematography words typed directly into the description
    # (e.g. "low angle shot at night, tense mood") so they become real filters.
    parsed = parse_filters_from_text(parse_text)
    for cat, vals in parsed.items():
        existing = active_filters.setdefault(cat, [])
        for v in vals:
            if v not in existing:
                existing.append(v)

    print(f"Searching for: {search_text}  filters: {active_filters}")
    videos = search_youtube(search_text)

    if not videos:
        return {"frames": []}

    cleanup_old_files()

    all_results = []
    videos_to_process = videos[:MAX_VIDEOS_TO_PROCESS]

    for video_id, title, duration in videos_to_process:
        print(f"Downloading video: {title} ({video_id})")
        video_path = download_video(video_id)
        if not video_path:
            print(f"  Failed to download {video_id}")
            continue

        print(f"  Extracting frames...")
        extracted = extract_frames(video_path)
        if not extracted:
            print(f"  No frames extracted from {video_id}")
            continue

        print(f"  Extracted {len(extracted)} frames, scoring...")
        frame_images = [img for img, _ in extracted]

        main_variants = [
            main_query,
            f"cinematic film still of {main_query}, movie trailer",
        ]
        clip_texts = list(main_variants)
        filter_lookup = {}
        for cat, vals in active_filters.items():
            for v in vals:
                desc = FILTER_PROMPTS.get(cat, {}).get(v, v.replace('_', ' '))
                filter_lookup[(cat, v)] = len(clip_texts)
                clip_texts.append(desc)

        scores_matrix = score_frames_batch_multi(frame_images, clip_texts)

        combined_scores = []
        for i in range(len(frame_images)):
            main_s = max(scores_matrix[t][i] for t in range(len(main_variants)))
            props = analyze_image_properties(frame_images[i])
            feat = compute_composition_features(frame_images[i])

            # Best match within each category (selecting multiple options
            # means "any of these"), so a frame can never be diluted by
            # averaging away a strong match.
            category_best = {}
            aspect_best = 0.0
            for cat, vals in active_filters.items():
                best = 0.0
                for v in vals:
                    clip_s = scores_matrix[filter_lookup[(cat, v)]][i]
                    if clip_s > aspect_best:
                        aspect_best = clip_s
                    if cat == "shot_size":
                        geom_s = score_shot_size_geometry(v, feat)
                        w_clip, w_geom = (0.55, 0.45) if feat["has_face"] else (1.0, 0.0)
                        score = w_clip * clip_s + w_geom * geom_s
                    elif cat == "camera_angle":
                        geom_s = score_camera_angle_geometry(v, feat)
                        w_clip, w_geom = (0.7, 0.3) if feat["has_face"] else (1.0, 0.0)
                        score = w_clip * clip_s + w_geom * geom_s
                    elif cat == "tone":
                        score = 0.6 * clip_s + 0.4 * score_tone_filter(v, props)
                    elif cat == "lighting":
                        score = 0.6 * clip_s + 0.4 * score_lighting_filter(v, props)
                    else:
                        score = clip_s
                    if score > best:
                        best = score
                category_best[cat] = best

            if category_best:
                cat_mean = sum(category_best.values()) / len(category_best)
                combined = main_s * (0.3 + 0.7 * cat_mean ** 1.2)
            else:
                combined = main_s

            # Candidate survival score: a frame reaches the VLM stage if it
            # strongly matches ANY stated aspect, not only the overall sentence.
            # This stops the pre-filter from fixating on a single keyword and
            # discarding frames that match e.g. "neon lighting" or "low angle".
            candidate = max(combined, main_s, aspect_best)

            combined_scores.append(candidate)

        scored_triples = [(img, ts, score) for (img, ts), score in zip(extracted, combined_scores)]
        top_raw = sorted(scored_triples, key=lambda x: -x[2])[:TOP_FRAMES_PER_VIDEO * 2]
        top_frames = dedupe_similar_frames(top_raw)[:TOP_FRAMES_PER_VIDEO]

        for img, ts, score in top_frames:
            filename = save_frame(img, video_id, ts)
            all_results.append({
                "image_url": f"/frames/{filename}",
                "film": title,
                "timestamp": format_timestamp(ts),
                "timestamp_seconds": round(ts, 2),
                "score": round(score, 3),
                "video_id": video_id
            })

        os.remove(video_path)

    all_results.sort(key=lambda x: -x["score"])

    # Gemini (VLM) is the real judge. CLIP only gathers a broad candidate pool
    # (top frames per video, keeping anything that matches any stated aspect);
    # Gemini then scores every candidate against the FULL request and demands
    # ALL requirements are met. Skipped when there's nothing to judge against or
    # when no API key is configured (falls back to CLIP-only ranking).
    reranked = False
    if all_results and vlm.vlm_configured() and (parse_text or active_filters):
        image_paths = [
            os.path.join(EXTRACTED_DIR, os.path.basename(r["image_url"]))
            for r in all_results
        ]
        print(f"Scoring {len(image_paths)} candidates with Gemini...")
        vlm_scores = vlm.score_frames_with_vlm(image_paths, search_text, active_filters)
        if vlm_scores:
            clip_vals = [r["score"] for r in all_results]
            cmin, cmax = min(clip_vals), max(clip_vals)
            cspan = (cmax - cmin) or 1.0

            any_vlm = any(
                v is not None and "overall" in v for v in vlm_scores
            )
            if any_vlm:
                for r, v in zip(all_results, vlm_scores):
                    clip_norm = (r["score"] - cmin) / cspan
                    if v is None or "overall" not in v:
                        # Couldn't be verified by Gemini: sink below judged frames.
                        r["score"] = round(0.1 * clip_norm, 3)
                        continue
                    vlm_val = max(0.0, min(100.0, float(v.get("overall", 0)))) / 100.0
                    r["score"] = round(0.2 * clip_norm + 0.8 * vlm_val, 3)
                    r["vlm"] = {
                        "overall": round(vlm_val, 3),
                        "camera_angle": v.get("camera_angle"),
                        "shot_size": v.get("shot_size"),
                        "camera_movement": v.get("camera_movement"),
                        "mood": v.get("mood"),
                        "tone": v.get("tone"),
                        "lighting": v.get("lighting"),
                        "reason": v.get("reason", ""),
                    }
                    reranked = True
                all_results.sort(key=lambda x: -x["score"])

    all_results = all_results[:MAX_RESULTS]

    print(f"Returning {len(all_results)} matching frames (vlm_rerank={reranked})")
    return {
        "frames": all_results,
        "applied_filters": {cat: sorted(vals) for cat, vals in active_filters.items()},
        "vlm_rerank": reranked,
    }

SEARCH_LOCK = threading.Lock()


def _search_params(
    q: str = Query(default=""),
    film: str = Query(default=""),
    camera_angle: List[str] = Query(default=[]),
    shot_size: List[str] = Query(default=[]),
    camera_movement: List[str] = Query(default=[]),
    mood: List[str] = Query(default=[]),
    tone: List[str] = Query(default=[]),
    lighting: List[str] = Query(default=[])
):
    return (q, film, camera_angle, shot_size, camera_movement, mood, tone, lighting)


def _prune_jobs():
    now = time.time()
    for jid in list(JOBS.keys()):
        if now - JOBS[jid]["created_at"] > JOB_TTL_SECONDS:
            JOBS.pop(jid, None)


def _start_job(params):
    with JOBS_LOCK:
        _prune_jobs()
        job_id = uuid4().hex[:12]
        JOBS[job_id] = {"status": "queued", "created_at": time.time()}
    q, film, camera_angle, shot_size, camera_movement, mood, tone, lighting = params

    def worker():
        try:
            with SEARCH_LOCK:
                with JOBS_LOCK:
                    JOBS[job_id]["status"] = "running"
                result = _run_search_pipeline(
                    q, film,
                    camera_angle, shot_size, camera_movement, mood, tone, lighting,
                )
            with JOBS_LOCK:
                JOBS[job_id].update(result)
                JOBS[job_id]["status"] = "done"
        except Exception as e:
            with JOBS_LOCK:
                JOBS[job_id]["status"] = "error"
                JOBS[job_id]["error"] = str(e)
            print(f"Job {job_id} failed: {e}")

    threading.Thread(target=worker, daemon=True).start()
    return job_id


@app.get("/search")
def search_sync(
    q: str = Query(default=""),
    film: str = Query(default=""),
    camera_angle: List[str] = Query(default=[]),
    shot_size: List[str] = Query(default=[]),
    camera_movement: List[str] = Query(default=[]),
    mood: List[str] = Query(default=[]),
    tone: List[str] = Query(default=[]),
    lighting: List[str] = Query(default=[])
):
    with SEARCH_LOCK:
        return _run_search_pipeline(
            q, film,
            camera_angle, shot_size, camera_movement, mood, tone, lighting,
        )


@app.post("/search/jobs")
def start_search_job(
    q: str = Query(default=""),
    film: str = Query(default=""),
    camera_angle: List[str] = Query(default=[]),
    shot_size: List[str] = Query(default=[]),
    camera_movement: List[str] = Query(default=[]),
    mood: List[str] = Query(default=[]),
    tone: List[str] = Query(default=[]),
    lighting: List[str] = Query(default=[])
):
    job_id = _start_job((q, film, camera_angle, shot_size, camera_movement, mood, tone, lighting))
    return {"job_id": job_id}


@app.get("/search/jobs/{job_id}")
def search_job_status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if job is None:
        return {"status": "not_found"}
    body = {"status": job["status"]}
    for key in ("error", "frames", "applied_filters", "vlm_rerank"):
        if key in job:
            body[key] = job[key]
    return body

@app.get("/filters")
def get_filters():
    return FILTER_OPTIONS

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_ready": model_ready.is_set(),
        "device": device,
        "vlm": {
            "configured": vlm.vlm_configured(),
            "model": vlm.GEMINI_MODEL if vlm.vlm_configured() else None,
        },
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
