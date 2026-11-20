import cv2
import numpy as np
import pytest

from scripts import extract_session_features


def test_native_lower_resolution_requires_explicit_train_flag(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    (root / "source.mp4").write_bytes(b"synthetic source")
    frame = np.zeros((478, 848, 3), dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", frame)
    assert ok
    (root / "frame.png").write_bytes(encoded.tobytes())
    plan = {"K03_S02": {"split": "TRAIN", "person_id": "K03"}}
    manifest = [{"session_id": "K03_S02", "video": "source.mp4", "image": "frame.png",
                 "frame_index": 0}]

    def process(image, detector, extractor):
        assert image.shape == (478, 848, 3)
        return {"status": "ok", "timings_ms": {}}, None, np.ones(128, dtype=np.float32)

    monkeypatch.setattr(extract_session_features, "process_image", process)
    with pytest.raises(ValueError, match="resolución permitida"):
        extract_session_features.extract(root, manifest, plan, "TRAIN", None, None)
    with pytest.raises(ValueError, match="únicamente en TRAIN"):
        extract_session_features.extract(
            root, manifest, plan, "VALIDATION", None, None, allow_848x478=True,
        )
    features, records = extract_session_features.extract(
        root, manifest, plan, "TRAIN", None, None, allow_848x478=True,
    )
    assert features["vectors"].shape == (1, 128)
    assert (records[0]["width"], records[0]["height"]) == (848, 478)
