import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import numpy as np
from PIL import Image

from vision import compute_composition_features, score_shot_size_geometry, score_camera_angle_geometry


def make_face_feature(ratio, cy=0.45):
    return {
        "has_face": True,
        "max_face_height_ratio": ratio,
        "max_face_center_y": cy,
        "max_face_center_x": 0.5,
    }


def test_compute_features_no_face():
    img = Image.fromarray(np.zeros((240, 320, 3), np.uint8))
    feat = compute_composition_features(img)
    assert feat["has_face"] is False
    assert feat["max_face_height_ratio"] == 0.0
    assert feat["width"] == 320
    assert feat["height"] == 240


def test_shot_size_geometry_discriminates():
    assert score_shot_size_geometry("close_up", make_face_feature(0.35)) > 0.9
    assert score_shot_size_geometry("close_up", make_face_feature(0.02)) < 0.1

    assert score_shot_size_geometry("wide", make_face_feature(0.02)) > 0.9
    assert score_shot_size_geometry("wide", make_face_feature(0.35)) < 0.1

    assert score_shot_size_geometry("extreme_wide", make_face_feature(0.008)) > 0.9
    assert score_shot_size_geometry("extreme_wide", make_face_feature(0.35)) < 0.1


def test_shot_size_top_choice_consistent():
    for ratio in (0.5, 0.35, 0.17, 0.09, 0.03, 0.008):
        feat = make_face_feature(ratio)
        best = max(
            ["extreme_close_up", "close_up", "medium_close_up", "medium", "wide", "extreme_wide"],
            key=lambda v: score_shot_size_geometry(v, feat),
        )
        if ratio >= 0.42:
            assert best == "extreme_close_up"
        elif ratio >= 0.22:
            assert best == "close_up"
        elif ratio >= 0.12:
            assert best == "medium_close_up"
        elif ratio >= 0.06:
            assert best == "medium"
        elif ratio >= 0.012:
            assert best == "wide"
        else:
            assert best == "extreme_wide"


def test_no_face_is_neutral():
    feat = {"has_face": False, "max_face_height_ratio": 0.0}
    assert score_shot_size_geometry("wide", feat) == 0.5
    assert score_camera_angle_geometry("low_angle", feat) == 0.5


def test_camera_angle_geometry():
    assert score_camera_angle_geometry("eye_level", make_face_feature(0.3, cy=0.42)) > 0.9
    assert score_camera_angle_geometry("high_angle", make_face_feature(0.15, cy=0.30)) > 0.35
    assert score_camera_angle_geometry("low_angle", make_face_feature(0.4, cy=0.25)) > 0.6
