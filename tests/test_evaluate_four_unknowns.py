import numpy as np
import pytest

from scripts.evaluate_four_unknowns import other_vectors, score_unregistered
from scripts.hog_knn import FEATURE_COUNT


def test_unregistered_far_under_threshold():
    gallery = np.zeros((4, FEATURE_COUNT), np.float32)
    gallery[:3, 0] = 1
    labels = np.array(["K01", "K01", "K01", "K02"])
    close = gallery[0].copy()
    far = np.ones(FEATURE_COUNT, np.float32)
    row = score_unregistered(gallery, labels, np.stack([close, far]), threshold=0.1)
    assert row["n"] == 2
    assert row["accepted"] == 1
    assert row["rejected"] == 1
    assert row["as_person"]["K01"] == 1
    assert row["not_test"] is True


def test_other_vectors_drop_enrolled_ids():
    vectors = np.zeros((3, 2), np.float32)
    labels = np.array(["K01", "OTHER", "OTHER"])
    other = other_vectors(vectors, labels)
    assert len(other) == 2
    with pytest.raises(ValueError, match="OTHER"):
        other_vectors(vectors[:1], labels[:1])
