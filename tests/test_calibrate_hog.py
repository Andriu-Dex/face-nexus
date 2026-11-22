from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from scripts.calibrate_hog import (
    MODELS, attempt_vote, compare_attempts, frame_vote, inspect_attempts, public_frame,
)
from scripts.hog_knn import PEOPLE, inspect_live_frame


def test_attempt_uses_third_margin_of_same_identity():
    assert frame_vote(np.array([.9, .9, .2, .3])) is None
    assert frame_vote(np.array([.9, np.nan, .2, .3])) is None
    assert frame_vote(np.array([1., .5, -.2, 0.])) == ("K01", .5)
    votes = [("K01", .3), ("K02", .9), ("K01", .8), ("K01", .4)]
    assert attempt_vote(votes[:3]) is None
    assert attempt_vote(votes) == {"candidate": "K01", "margin": .3}


def test_threshold_requires_unknown_and_excludes_wrong_known_predictions():
    def attempt(participant, label, margin):
        return {"participant": participant, "status": "usable",
                "votes": {name: {"candidate": label, "margin": margin} for name in MODELS}}

    known = [attempt(person, person, .9) for person in PEOPLE]
    assert compare_attempts(known)["status"] == "insufficient_live_data"
    result = compare_attempts(known + [attempt("K02", "K01", .9), attempt("A01", "K03", .8)])
    assert result["models"]["svm"]["candidate_threshold"] > .9
    assert result["models"]["svm"]["known_correct_at_threshold"] == 0
    assert result["models"]["svm"]["accepted_unknown_before_threshold"] == 1


def test_inspect_attempts_reports_missing_people_without_a_threshold():
    records = [
        {"participant": "K01", "status": "usable",
         "votes": {"svm": {"candidate": "K02", "margin": .4}, "mlp": {"candidate": "K01", "margin": .2}}},
        {"participant": "A01", "status": "insufficient_faces", "votes": {"svm": None, "mlp": None}},
    ]
    report = inspect_attempts(records)
    assert report["missing_known"] == ["K02", "K03", "K04"]
    assert report["unknown_people"] == []
    assert report["by_participant"]["K01"]["models"]["svm"]["wrong"] == 1
    assert report["by_participant"]["K01"]["models"]["mlp"]["correct"] == 1
    assert compare_attempts(records)["status"] == "insufficient_live_data"
    assert "by_participant" in compare_attempts(records)


def test_public_frame_drops_hog_vector():
    report = public_frame({"reason": "usable", "vector": np.ones(4), "face_count": 1},
                          {"svm": {"candidate": "K01", "margin": .2}})
    assert "vector" not in report
    assert report["votes"]["svm"]["candidate"] == "K01"


def test_live_inspection_separates_missing_and_multiple_faces():
    frame = np.zeros((80, 80, 3), dtype=np.uint8)
    empty = SimpleNamespace(setInputSize=lambda size: None, detect=lambda image: (1, None))
    assert inspect_live_frame(frame, empty)["reason"] == "no_face"
    two = SimpleNamespace(
        setInputSize=lambda size: None,
        detect=lambda image: (1, np.array([[0, 0, 40, 40, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, .95],
                                           [40, 0, 40, 40, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, .7]])),
    )
    many = inspect_live_frame(frame, two)
    assert many["reason"] == "multiple_faces"
    assert many["face_count"] == 2
    assert many["max_detection_score"] == pytest.approx(.95)
    cv2.rectangle(frame, (10, 10), (30, 70), (255, 255, 255), -1)
    one = SimpleNamespace(
        setInputSize=lambda size: None,
        detect=lambda image: (1, np.array([[0., 0., 80., 80.]])),
    )
    usable = inspect_live_frame(frame, one)
    assert usable["reason"] == "usable"
    assert usable["vector"] is not None
    assert usable["box_height_px"] == 80
    assert usable["quality"]["laplacian_var"] > 0
    assert usable["quality"]["width_px"] == 80
