import threading

import numpy as np
import cv2

_face_cascade = None
_cascade_lock = threading.Lock()


def _get_face_cascade():
    global _face_cascade
    if _face_cascade is None:
        with _cascade_lock:
            if _face_cascade is None:
                try:
                    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                    cascade = cv2.CascadeClassifier(cascade_path)
                    if cascade.empty():
                        cascade = None
                except Exception:
                    cascade = None
                _face_cascade = cascade
    return _face_cascade


def compute_composition_features(pil_img):
    width, height = pil_img.size
    arr = np.asarray(pil_img.convert("L"))
    arr = np.ascontiguousarray(arr)

    features = {
        "width": width,
        "height": height,
        "face_count": 0,
        "has_face": False,
        "max_face_height_ratio": 0.0,
        "max_face_width_ratio": 0.0,
        "max_face_center_x": 0.5,
        "max_face_center_y": 0.5,
    }

    cascade = _get_face_cascade()
    if cascade is not None and height > 40:
        min_size = max(12, int(height * 0.04))
        try:
            faces = cascade.detectMultiScale(
                arr,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(min_size, min_size),
            )
        except Exception:
            faces = ()

        best_area = 0
        best = None
        for (x, y, w, h) in faces:
            area = w * h
            if area > best_area:
                best_area = area
                best = (x, y, w, h)

        if best is not None:
            x, y, w, h = best
            features["face_count"] = len(faces)
            features["has_face"] = True
            features["max_face_height_ratio"] = h / float(height)
            features["max_face_width_ratio"] = w / float(width)
            features["max_face_center_x"] = (x + w / 2.0) / float(width)
            features["max_face_center_y"] = (y + h / 2.0) / float(height)

    return features


def _tri(value, lo, hi):
    """Trapezoid membership scoring: 1.0 inside [lo, hi], decaying to 0 over
    one band-width beyond each edge."""
    if value <= 0:
        return 0.0
    if lo < 0:
        lo = 0.0
    if hi > 1.0:
        hi = 1.0
    if lo > hi:
        lo, hi = hi, lo
    width = 0.12
    if value < lo:
        return max(0.0, 1.0 - (lo - value) / width)
    if value > hi:
        return max(0.0, 1.0 - (value - hi) / width)
    return 1.0


# Face height (as a fraction of frame height) bands for shot sizes.
# CLIP is weak at judging framing size, so face geometry is the primary signal.
SHOT_SIZE_BANDS = {
    "extreme_close_up": (0.42, 1.00),
    "close_up": (0.22, 0.40),
    "medium_close_up": (0.12, 0.22),
    "medium": (0.06, 0.13),
    "medium_wide": (0.030, 0.065),
    "wide": (0.012, 0.035),
    "extreme_wide": (0.000, 0.015),
    "insert": (0.000, 0.015),
    "two_shot": (0.04, 0.14),
}


def score_shot_size_geometry(filter_val, feat):
    if not feat["has_face"]:
        return 0.5
    fr = feat["max_face_height_ratio"]
    band = SHOT_SIZE_BANDS.get(filter_val)
    if band is None:
        return 0.5
    return _tri(fr, band[0], band[1])


def score_camera_angle_geometry(filter_val, feat):
    if not feat["has_face"]:
        return 0.5
    cy = feat["max_face_center_y"]
    fr = feat["max_face_height_ratio"]

    if filter_val == "eye_level":
        return max(0.0, 1.0 - abs(cy - 0.42) / 0.35)
    if filter_val == "high_angle":
        return max(0.0, (0.5 - cy) / 0.25) * (1.0 - min(fr, 0.3) / 0.3)
    if filter_val == "low_angle":
        return max(0.0, (0.5 - cy) / 0.2) * min(fr, 0.5) / 0.5
    if filter_val == "birds_eye":
        return max(0.0, 1.0 - min(fr, 0.25) / 0.25) * max(0.0, 1.0 - abs(cy - 0.5) * 2.0)
    if filter_val == "point_of_view":
        return 0.6
    if filter_val in ("over_the_shoulder", "shoulder_level"):
        return 0.6 if fr < 0.35 else 0.4
    if filter_val in ("establishing", "aerial"):
        return 0.4
    return 0.5
