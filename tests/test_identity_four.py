import numpy as np
import pytest

from scripts.identity_four import apply_threshold, four_max_distance, load_sessions, score_four
from scripts.import_frames import spread_indices


def test_spread_does_not_repeat_on_a_short_list():
    assert spread_indices(5, 5) == [0, 1, 2, 3, 4]
    assert len(set(spread_indices(100, 24))) == 24


def test_four_threshold_and_confusion():
    from scripts import identity_four as mod

    def fake_vote(gallery, labels, vector, k=3):
        if vector[0] < .5:
            return "K01", 0.1
        return "K02", 0.8

    original = mod.vote_knn
    mod.vote_knn = fake_vote
    try:
        val_x = np.array([[0.], [1.]])
        val_y = np.array(["K01", "K02"])
        row = four_max_distance(None, None, val_x, val_y, slack=1.0)
        assert row["raw_max_val"] == 0.8
        predicted = apply_threshold(None, None, val_x, 0.2)
    finally:
        mod.vote_knn = original
    assert predicted.tolist() == ["K01", "UNKNOWN"]
    scored = score_four(["K01", "K02"], ["K01", "K02"])
    assert scored["accuracy"] == 1
    assert scored["per_person"]["K01"] == 1


def test_session_map_requires_four_ids(tmp_path):
    path = tmp_path / "map.json"
    path.write_text('{"K01": {"train": ["a"], "validation": ["b"]}}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_sessions(path)
