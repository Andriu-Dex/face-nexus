import numpy as np
import pytest

from scripts.hog_knn import FEATURE_COUNT, accepts_open_set, runner_up_distance
from scripts.live_k01 import identify_knn
from scripts.open_set_knn import pick_operating_point, predict_open_set


def test_gap_rejects_ambiguous_neighbour():
    gallery = np.zeros((6, FEATURE_COUNT), np.float32)
    gallery[:3, 0] = 1
    gallery[3:, 0] = 0.95
    labels = np.array(["K01", "K01", "K01", "K02", "K02", "K02"])
    query = gallery[0].copy()
    query[0] = 0.97
    winner_d = 0.0
    gap = runner_up_distance(gallery, labels, query, "K01") - winner_d
    assert gap < 0.1
    assert accepts_open_set("K01", 0.02, 0.5, max_distance=1.0, min_gap=0.2)
    assert not accepts_open_set("K01", 0.02, 0.01, max_distance=1.0, min_gap=0.2)
    identify = identify_knn(gallery, labels, max_distance=1.0, min_gap=0.5)
    _label, accepted, text = identify(query)
    assert accepted is False and "G=" in text


def test_pick_far_limit_prefers_recall_then_small_t():
    genuine = [("K01", "K01", 0.1, 0.4), ("K02", "K02", 0.2, 0.4)]
    unknown = [("K01", 0.15, 0.01), ("K03", 0.9, 0.4)] * 50
    chosen = pick_operating_point(genuine, unknown, target_far=0.01)
    assert chosen["calibration_unknowns"]["far"] <= 0.01
    assert chosen["max_distance"] > 0
    assert chosen["min_gap"] >= 0
    assert chosen["loo_known"]["confused_accepted"] == 0


def test_pick_does_not_prefer_more_accepted_confusions():
    genuine = [
        ("K01", "K01", 0.10, 0.5),
        ("K02", "K03", 0.12, 0.5),
    ]
    unknown = [("K01", 0.90, 0.5)] * 40
    chosen = pick_operating_point(genuine, unknown, target_far=0.01)
    assert chosen["loo_known"]["correct_accepted"] == 1
    assert chosen["loo_known"]["confused_accepted"] == 0
    assert chosen["max_distance"] < 0.12


def test_predict_open_set_unknown_when_gap_fails():
    gallery = np.zeros((6, FEATURE_COUNT), np.float32)
    gallery[:3, 0] = 1
    gallery[3:, 0] = 1
    gallery[3:, 1] = 1
    labels = np.array(["K01", "K01", "K01", "K02", "K02", "K02"])
    query = gallery[0].copy()
    query[1] = 0.4
    predicted = predict_open_set(gallery, labels, np.stack([query]), 2.0, min_gap=0.5)
    assert predicted.tolist() == ["UNKNOWN"]
    loose = predict_open_set(gallery, labels, np.stack([query]), 2.0, min_gap=0.0)
    assert loose.tolist() == ["K01"]


def test_accepts_without_gap_keeps_old_distance_rule():
    assert accepts_open_set("K01", 0.3, None, max_distance=0.5, min_gap=0)
    assert not accepts_open_set("K01", 0.6, None, max_distance=0.5, min_gap=0)
    with pytest.raises(ValueError):
        pick_operating_point([("K01", "K01", 0.1, 0.1)], [("K01", 0.05, 0.5)] * 10, target_far=0.0)
