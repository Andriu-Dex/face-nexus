import hashlib
import json

import cv2
import numpy as np
import pytest

from scripts.import_frames import import_collection, natural_key, spread_indices, regroup_manifest


def write_frame(folder, name, value):
    folder.mkdir(parents=True, exist_ok=True)
    frame = np.full((32, 48, 3), value, np.uint8)
    assert cv2.imwrite(str(folder / name), frame)


def test_natural_order_and_no_repeated_indices():
    assert sorted(["frame_1000.png", "frame_999.png", "frame_01.png"], key=natural_key)[-1] == "frame_1000.png"
    assert spread_indices(3, 20) == [0, 1, 2]
    assert len(set(spread_indices(100, 20))) == 20


def test_import_preserves_source_and_tracks_sessions_and_copies(tmp_path):
    source = tmp_path / "source"
    for session in range(1, 3):
        for number in range(1, 6):
            write_frame(source / "participant" / f"seg{session}", f"frame_{number}.png", session * 10 + number)
    originals = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob("*.png")}
    result = import_collection(source, tmp_path / "result", {"participant": "K01"}, 4)
    assert result["total_valid"] == 10
    assert result["sessions"] == {"K01": 2}
    assert result["selection_counts"] == {"K01": 4}
    assert result["dimensions"]["K01"] == {"48x32": 10}
    records = [json.loads(line) for line in (tmp_path / "result/manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {r["split"] for r in records} == {"UNASSIGNED"}
    assert all(r["video_timestamp_seconds"] is None for r in records)
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == value for p, value in originals.items())
    with pytest.raises(FileExistsError):
        import_collection(source, tmp_path / "result", {"participant": "K01"})


def test_invalid_and_duplicate_are_reported_without_deleting(tmp_path):
    source = tmp_path / "source"
    folder = source / "participant/seg1"
    write_frame(folder, "frame_1.png", 10)
    write_frame(folder, "frame_2.png", 10)
    (folder / "frame_3.png").write_bytes(b"bad")
    result = import_collection(source, tmp_path / "result", {"participant": "K01"}, 3)
    assert len(result["invalid"]) == 1
    assert result["exact_pixel_duplicate_groups"]
    assert result["selection_counts"]["K01"] == 1
    assert len(list(folder.glob("*.png"))) == 3


def test_rejects_mapping_outside_source(tmp_path):
    with pytest.raises(ValueError):
        import_collection(tmp_path, tmp_path / "result", {"../outside": "K01"})


def test_regroup_keeps_segments_in_one_train_session(tmp_path):
    source = tmp_path / "source"
    for number in range(1, 3):
        write_frame(source / "participant" / f"seg{number}", "frame_1.png", number * 30)
    import_collection(source, tmp_path / "old", {"participant": "K01"})
    report = regroup_manifest(source, tmp_path / "old", tmp_path / "new")
    records = [json.loads(line) for line in (tmp_path / "new/manifest.jsonl").read_text().splitlines()]
    assert {record["session_id"] for record in records} == {"S01"}
    assert {record["split"] for record in records} == {"TRAIN"}
    assert {record["source_segment_id"] for record in records} == {"SEG01", "SEG02"}
    assert len({record["sample_id"] for record in records}) == 2
    assert report["selection_counts"]["K01"] == 2
    assert report["actual_video_count"] == "not_verified"
