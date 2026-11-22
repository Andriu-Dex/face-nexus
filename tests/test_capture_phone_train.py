from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from scripts.capture_phone_train import caption_frame, store_session
from scripts.hog_knn import FEATURE_COUNT


def test_phone_train_keeps_failed_crops_and_usable_hog(tmp_path):
    blank = np.zeros((80, 80, 3), np.uint8)
    textured = blank.copy()
    cv2.rectangle(textured, (10, 10), (30, 70), (255, 255, 255), -1)
    detector = SimpleNamespace(
        setInputSize=lambda size: None,
        detect=lambda image: (1, None) if image.mean() < 1 else (1, np.array([[0., 0., 80., 80.]])),
    )
    summary = store_session(tmp_path, "K01", [blank, textured], 0, detector)
    assert summary["sampled_frames"] == 2
    assert summary["usable_frames"] == 1
    assert summary["records"][0]["reason"] == "no_face"
    assert "quality" not in summary["records"][0] or summary["records"][0].get("quality") is None
    assert summary["records"][1]["quality"]["laplacian_var"] > 0
    assert (tmp_path / "frames" / "K01_PHONE_0001.png").is_file()
    loaded = np.load(tmp_path / "hog.npz")
    assert loaded["vectors"].shape == (1, FEATURE_COUNT)
    assert loaded["labels"].tolist() == ["K01"]
    with pytest.raises(FileExistsError):
        store_session(tmp_path, "K01", [textured], 0, detector)


def test_caption_marks_a_saved_shot_without_changing_the_original():
    frame = np.zeros((200, 400, 3), np.uint8)
    preview = caption_frame(frame, "FOTO 3/20", flash=True)
    assert preview.shape[0] <= 960
    assert not np.array_equal(preview, frame)
    assert frame.sum() == 0
