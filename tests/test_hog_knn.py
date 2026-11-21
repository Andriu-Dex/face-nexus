from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from scripts.compare_hog_models import svm_margin
from scripts.evaluate_hog_knn import validate_manifest
from scripts.hog_knn import FEATURE_COUNT, PEOPLE, face_features, knn_candidate, recognize


def test_hog_keeps_separate_regions_in_a_group():
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    cv2.rectangle(frame, (15, 5), (30, 90), (255, 255, 255), -1)
    cv2.rectangle(frame, (112, 35), (190, 60), (255, 255, 255), -1)
    detector = SimpleNamespace(
        setInputSize=lambda size: None,
        detect=lambda image: (1, np.array([[0, 0, 100, 100], [100, 0, 100, 100]])),
    )
    faces = face_features(frame, detector)
    assert [box for box, _ in faces] == [(0, 0, 100, 100), (100, 0, 200, 100)]
    assert all(vector.shape == (FEATURE_COUNT,) and np.isclose(np.linalg.norm(vector), 1)
               for _, vector in faces)
    assert not np.allclose(faces[0][1], faces[1][1])
    assert face_features(frame, detector, require_single=True) == []


def test_manifest_blocks_exact_duplicates_between_sessions():
    manifest = {}
    for split, encounter in (("train", "S01"), ("validation", "S02")):
        manifest[split] = [
            {"person_id": person, "session_id": f"{person}_{encounter}",
             "sample_id": f"{person}_{encounter}_F{index:06}",
             "image_sha256": f"{split}-{person}-{index}"}
            for person in PEOPLE for index in range(20)
        ]
    validate_manifest(manifest)
    manifest["validation"][0]["image_sha256"] = manifest["train"][0]["image_sha256"]
    with pytest.raises(ValueError, match="imágenes idénticas"):
        validate_manifest(manifest)


def test_knn_requires_threshold_and_rejects_distant_candidate():
    query = np.zeros(FEATURE_COUNT)
    train = np.stack([query, query + .001, query + 1])
    labels = np.array(["K01", "K01", "K02"])
    assert knn_candidate(train, labels, query) == ("K01", 0)
    assert recognize(train, labels, query) == "UNKNOWN"
    assert recognize(train, labels, query, max_distance=.05) == "K01"
    assert recognize(train, labels, query + 2, max_distance=.05) == "UNKNOWN"


def test_knn_does_not_resolve_a_tie_by_label_order():
    query = np.zeros(FEATURE_COUNT)
    train = np.stack([query, query + .001, query + .002])
    labels = np.array(["K02", "K01", "K03"])
    assert recognize(train, labels, query, max_distance=1) == "UNKNOWN"


def test_svm_margin_compares_with_best_real_competitor_even_if_negative():
    targets = np.array([[1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]])
    scores = np.array([[-1., -2., -4., -5.], [-2., -2.5, -3., -4.], [0., 2., 1., -1.]])
    np.testing.assert_allclose(svm_margin(np, targets, scores), [0., .5, 3.])
