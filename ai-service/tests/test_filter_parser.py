import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from filter_parser import parse_filters_from_text


def test_basic_camera_angle_detection():
    assert parse_filters_from_text("low angle shot of a car")["camera_angle"] == ["low_angle"]
    assert parse_filters_from_text("aerial drone shot over the city")["camera_angle"] == ["aerial"]


def test_shot_size_specific_over_generic():
    assert parse_filters_from_text("extreme wide shot")["shot_size"] == ["extreme_wide"]
    assert parse_filters_from_text("extreme close up")["shot_size"] == ["extreme_close_up"]
    assert parse_filters_from_text("medium close up")["shot_size"] == ["medium_close_up"]
    assert parse_filters_from_text("medium wide shot")["shot_size"] == ["medium_wide"]
    assert parse_filters_from_text("close up of a face")["shot_size"] == ["close_up"]


def test_mood_and_lighting_detection():
    res = parse_filters_from_text("tense mood, low key lighting, dark")
    assert res["mood"] == ["tense"]
    assert res["lighting"] == ["low_key"]
    assert res["tone"] == ["dark"]


def test_empty_input():
    assert parse_filters_from_text("") == {}
    assert parse_filters_from_text(None) == {}


def test_full_description():
    res = parse_filters_from_text("aerial drone shot over the city at golden hour, warm light, mysterious")
    assert res["camera_angle"] == ["aerial"]
    assert "golden_hour" in res["tone"]
    assert "warm" in res["tone"]
    assert res["mood"] == ["mysterious"]


def test_no_false_positives_on_plain_text():
    assert parse_filters_from_text("a car driving through a rainy street") == {}
