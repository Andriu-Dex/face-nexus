import numpy as np
import pytest

from scripts.evaluate_human_independent import independent_report, phone_hold_crops
from scripts.human_cnn import HUMAN, NONHUMAN


def test_independent_report_is_not_identity_or_veto():
    true = np.array([HUMAN, HUMAN, NONHUMAN, NONHUMAN])
    pred = np.array([HUMAN, NONHUMAN, NONHUMAN, HUMAN])
    row = independent_report(true, pred)
    assert row["n"] == 4
    assert row["used_as_identity"] is False
    assert row["vetoes_yunet"] is False
    assert row["not_liveness"] is True
    assert row["confusion"]["true_human_pred_nonhuman"] == 1
    assert row["confusion"]["true_nonhuman_pred_human"] == 1


def test_phone_hold_requires_a_unique_yunet_box(tmp_path, monkeypatch):
    import cv2

    frames = tmp_path / "experiments" / "hog_phone_adapt" / "K01" / "k01_phone_v3" / "frames"
    frames.mkdir(parents=True)
    for index in range(5):
        cv2.imwrite(str(frames / f"{index:04d}.png"), np.zeros((20, 20, 3), np.uint8))
    monkeypatch.setattr("scripts.evaluate_human_independent.detect_boxes", lambda *_a, **_k: [])
    with pytest.raises(ValueError, match="recorte"):
        phone_hold_crops(tmp_path, detector=None, hold=5)
