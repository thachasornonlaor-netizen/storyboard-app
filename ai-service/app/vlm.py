import base64
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
MAX_IMAGES_PER_REQUEST = 8
TIMEOUT = 60
MAX_RETRIES = 2

PLACEHOLDER_KEYS = {
    "", "your_key_here", "your_api_key", "your-api-key", "put_your_key_here",
    "changeme", "change_me", "none", "null", "sample_key", "api_key",
}


def vlm_configured():
    key = GEMINI_API_KEY.strip()
    if not key:
        return False
    if key.lower() in PLACEHOLDER_KEYS:
        return False
    return True


def _extract_json(text):
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except Exception:
        return None


def _call_gemini(parts):
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}"
        f":generateContent?key={GEMINI_API_KEY}"
    )
    payload = {"contents": [{"role": "user", "parts": parts}]}
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GEMINI_API_KEY,
        },
    )
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates") or []
            if not candidates:
                return None
            out_parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in out_parts)
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                time.sleep(2 * (attempt + 1))
                continue
            return None
        except Exception as e:
            last_error = e
            return None
    return None


def build_shot_prompt(shot_text, requirements, count):
    lines = [
        "You are an expert cinematographer and director selecting film stills for a storyboard.",
        f'The shot the user wants: "{shot_text}"',
    ]
    if requirements:
        req = "; ".join(
            f"{cat}: {', '.join(vals)}" for cat, vals in requirements.items()
        )
        lines.append(
            f"Explicit cinematography requirements (ALL are mandatory - do not ignore any): {req}"
        )
        lines.append(
            "A still that lacks any stated requirement is a poor match even if it matches "
            "everything else. A still must satisfy EVERY stated requirement to score high."
        )
    lines.append(
        f"\nYou will receive {count} images. For EACH image, return one JSON object "
        "rating that still against the request with integer scores 0-100:"
    )
    lines.append(
        '{"overall":0-100, "camera_angle":0-100, "shot_size":0-100, "camera_movement":0-100, '
        '"mood":0-100, "tone":0-100, "lighting":0-100, "reason":"one short phrase"}'
    )
    lines.append(
        "When explicit requirements are given, base 'overall' on the WEAKEST stated requirement "
        "(a chain is only as strong as its weakest link). When no requirements are given, base "
        "'overall' on how well the still matches the shot description."
    )
    lines.append(
        "How to judge the image itself (do NOT guess from the text alone): "
        "'shot_size' comes from how much of the frame the subject/face occupies - extreme close up = "
        "a single detail fills the frame, close up = face fills most of the frame, medium = waist up, "
        "wide = full body with room around it. "
        "'camera_angle' comes from the camera's vertical position relative to the subject - look at "
        "whether you are seeing the subject from below (low angle, subject above the horizon of the lens), "
        "level with their eyes, or from above (high angle, looking down on them). "
        "'camera_movement' comes from motion blur / background streaking in the still."
    )
    lines.append(
        f"Return ONLY a JSON array with exactly {count} objects, one per image, in the SAME ORDER "
        "the images are given. No markdown, no extra text."
    )
    return "\n".join(lines)


def _score_batch(image_paths, shot_text, requirements):
    parts = [{"text": build_shot_prompt(shot_text, requirements, len(image_paths))}]
    for path in image_paths:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})

    text = _call_gemini(parts)
    if not text:
        return [None] * len(image_paths)
    parsed = _extract_json(text)
    if not isinstance(parsed, list) or len(parsed) != len(image_paths):
        return [None] * len(image_paths)
    return parsed


def score_frames_with_vlm(image_paths, shot_text, requirements=None):
    """Score frames with Gemini. Returns a list aligned with image_paths where
    each entry is a dict of scores or None if that frame could not be scored.
    Returns None entirely if VLM is not configured."""
    if not vlm_configured() or not image_paths:
        return None

    results = [None] * len(image_paths)
    batches = [
        image_paths[i:i + MAX_IMAGES_PER_REQUEST]
        for i in range(0, len(image_paths), MAX_IMAGES_PER_REQUEST)
    ]

    with ThreadPoolExecutor(max_workers=min(4, len(batches))) as pool:
        futures = {}
        for batch in batches:
            idx = image_paths.index(batch[0])
            futures[pool.submit(_score_batch, batch, shot_text, requirements)] = idx
        for future, idx in futures.items():
            try:
                batch_scores = future.result()
                for j, score in enumerate(batch_scores):
                    if score is not None:
                        results[idx + j] = score
            except Exception:
                pass

    return results
