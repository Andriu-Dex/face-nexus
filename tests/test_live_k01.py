from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from scripts.access import DENIED, GRANTED, default_permissions
from scripts.compare_identity_k01 import knn_max_distance
from scripts.hog_knn import FEATURE_COUNT
from scripts.live_k01 import identify_knn, paint_regions, parse_trial_ref, recognize_frame


def _cnn():
    def model(batch, training=False):
        return np.tile(np.array([[0., 4.]]), (len(batch), 1))
    return model


def test_knn_threshold_rejects_far_k01_vote():
    query = np.zeros(FEATURE_COUNT, np.float32)
    gallery = np.stack([query, query + .01, query + 2])
    labels = np.array(["K01", "K01", "OTHER"])
    close = identify_knn(gallery, labels, max_distance=.05)
    far = identify_knn(gallery, labels, max_distance=.05)
    label, accepted, score, _ = close(query)
    assert label == "K01" and accepted and "T=" in score
    other = np.zeros(FEATURE_COUNT, np.float32)
    other[-1] = 1
    label, accepted, *_ = far(other)
    assert not accepted


def test_scene_grants_if_one_of_two_yunet_boxes_is_k01():
    frame = np.zeros((80, 160, 3), np.uint8)
    cv2.rectangle(frame, (5, 5), (70, 70), (255, 255, 255), -1)
    cv2.rectangle(frame, (90, 5), (150, 70), (180, 180, 180), -1)
    detector = SimpleNamespace(
        setInputSize=lambda size: None,
        detect=lambda image: (1, np.array([
            [0., 0., 80., 80., 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, .99],
            [80., 0., 80., 80., 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, .9],
        ])),
    )
    state = {"n": 0}

    def identify(vector):
        state["n"] += 1
        if state["n"] == 1:
            return "K01", True, "d=0.10"
        return "OTHER", False, "d=0.90"

    scene = recognize_frame(frame, detector, _cnn(), identify, default_permissions(), "knn")
    assert scene["outcome"] == GRANTED and scene["identity"] == "K01"
    assert len(scene["regions"]) == 2
    assert scene["regions"][1]["outcome"] == DENIED
    assert scene["regions"][0]["nearest"] == "K01"
    assert scene["regions"][1]["nearest"] == "OTHER"
    painted = paint_regions(frame, scene["regions"])
    assert not np.array_equal(painted, frame)


def test_knn_max_distance_uses_validation_only():
    dim = 8
    k01 = np.zeros(dim)
    other = np.ones(dim)
    gallery = np.stack([k01, k01 + .01, other])
    labels = np.array(["K01", "K01", "OTHER"])
    val_x = np.stack([k01, other * 3])
    val_y = np.array(["K01", "OTHER"])
    # vote_knn expects FEATURE_COUNT; skip this if dimension mismatches.
    # Covered by the 1764-D identify_knn test; this checks the aggregator with patched vote.
    from scripts import compare_identity_k01 as mod

    def fake_vote(gallery_in, labels_in, vector, k=3):
        if np.allclose(vector, k01):
            return "K01", 0.2
        return "K01", 0.9

    original = mod.vote_knn
    mod.vote_knn = fake_vote
    try:
        row = knn_max_distance(gallery, labels, val_x, val_y, slack=1.1, k=3)
    finally:
        mod.vote_knn = original
    assert row["raw_max_k01_val"] == 0.2
    assert row["max_distance"] == pytest.approx(0.22)
    assert row["lfw_as_k01_before"] == 1
    assert row["lfw_as_k01_after"] == 0


def test_parse_trial_ref_requires_known_family():
    assert parse_trial_ref("identity_four_v2") == ("identity_four", "identity_four_v2")
    assert parse_trial_ref("identity_four_other/identity_four_other_v1") == (
        "identity_four_other", "identity_four_other_v1")
    with pytest.raises(ValueError, match="ensayo"):
        parse_trial_ref("../secret")
    with pytest.raises(ValueError, match="ensayo"):
        parse_trial_ref("identity_four/identity_four_v2/extra")
