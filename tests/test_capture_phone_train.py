from types import SimpleNamespace

import cv2
import numpy as np
import pytest

import json
from pathlib import Path

from scripts.capture_phone_train import (
    caption_frame, commit_phone_session, register_phone_session, store_session,
)
from scripts.phone_demo_manifest import (
    LOT_PARTS, MANIFEST_PARTS, load_manifest, recover_unpublished_lot, save_manifest,
)
from scripts.hog_knn import FEATURE_COUNT


def test_phone_train_keeps_failed_crops_and_usable_hog(tmp_path):
    blank = np.zeros((80, 80, 3), np.uint8)
    textured = blank.copy()
    cv2.rectangle(textured, (10, 10), (30, 70), (255, 255, 255), -1)
    detector = SimpleNamespace(
        setInputSize=lambda size: None,
        detect=lambda image: (1, None) if image.mean() < 1 else (1, np.array([[0., 0., 80., 80.]])),
    )
    summary = store_session(
        tmp_path, "K01", [blank, textured], 0, detector, encounter_id="enc-k01-pilot")
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
        store_session(tmp_path, "K01", [textured], 0, detector, encounter_id="enc-k01-pilot")


def test_register_phone_session_warns_until_four_identities(tmp_path):
    blank = np.zeros((80, 80, 3), np.uint8)
    textured = blank.copy()
    cv2.rectangle(textured, (10, 10), (30, 70), (255, 255, 255), -1)
    detector = SimpleNamespace(
        setInputSize=lambda size: None,
        detect=lambda image: (1, np.array([[0., 0., 80., 80.]])),
    )
    folder = tmp_path / "K01" / "k01_tune"
    folder.mkdir(parents=True)
    summary = store_session(
        folder, "K01", [textured], 0, detector, role="tune", encounter_id="enc-k01-tune")
    warnings = register_phone_session(tmp_path, summary, "k01_tune")
    assert any("tune" in item and "K02" in item for item in warnings)


def _detector():
    return SimpleNamespace(
        setInputSize=lambda size: None,
        detect=lambda image: (1, np.array([[0., 0., 80., 80.]])),
    )


def _shot(seed):
    frame = np.zeros((80, 80, 3), np.uint8)
    cv2.rectangle(frame, (seed, 10), (seed + 20, 70), (255, 255, 255), -1)
    return frame


def test_two_commits_then_rejected_duplicate_leaves_no_orphan(tmp_path):
    detector = _detector()
    first, _ = commit_phone_session(
        tmp_path, "K01", "run_a", [_shot(5)], 0, detector, "tune", "enc-k01-a")
    second, _ = commit_phone_session(
        tmp_path, "K01", "run_b", [_shot(30)], 0, detector, "tune", "enc-k01-a")
    assert first["usable_frames"] == 1 and second["usable_frames"] == 1
    manifest = load_manifest(tmp_path.joinpath(*MANIFEST_PARTS))
    assert len(manifest["sessions"]) == 2
    with pytest.raises(ValueError, match="repetida|idénticas"):
        commit_phone_session(tmp_path, "K01", "run_c", [_shot(5)], 0, detector, "tune", "enc-k01-a")
    assert not (tmp_path / "experiments" / "hog_phone_adapt" / "K01" / "run_c").exists()
    assert not (tmp_path / "experiments" / "hog_phone_adapt" / "K01" / ".pending-run_c").exists()


def test_caption_marks_a_saved_shot_without_changing_the_original():
    frame = np.zeros((200, 400, 3), np.uint8)
    preview = caption_frame(frame, "FOTO 3/20", flash=True)
    assert preview.shape[0] <= 960
    assert not np.array_equal(preview, frame)
    assert frame.sum() == 0


def test_recover_keeps_unlisted_destination(tmp_path):
    dest = tmp_path.joinpath(*LOT_PARTS, "K01", "old_run")
    dest.mkdir(parents=True)
    marker = dest / "keep.txt"
    marker.write_text("historical", encoding="utf-8")
    with pytest.raises(FileExistsError, match="no se borra"):
        recover_unpublished_lot(tmp_path, "K01", "old_run")
    assert marker.read_text(encoding="utf-8") == "historical"


def test_rename_failure_keeps_registered_staging(tmp_path, monkeypatch):
    real_rename = Path.rename

    def boom(self, target):
        if ".pending-run_a" in str(self):
            raise OSError("simulated rename failure")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", boom)
    with pytest.raises(OSError, match="simulated"):
        commit_phone_session(
            tmp_path, "K01", "run_a", [_shot(5)], 0, _detector(), "tune", "enc-k01-a")
    pending = tmp_path.joinpath(*LOT_PARTS, "K01", ".pending-run_a")
    dest = tmp_path.joinpath(*LOT_PARTS, "K01", "run_a")
    assert pending.is_dir() and not dest.exists()
    manifest = load_manifest(tmp_path.joinpath(*MANIFEST_PARTS))
    assert any(row["run_name"] == "run_a" for row in manifest["sessions"])
    monkeypatch.undo()
    assert recover_unpublished_lot(tmp_path, "K01", "run_a") == "published_pending"
    assert dest.is_dir()
    assert (dest / "hog.npz").is_file()


def test_manifest_lock_rejects_second_writer(tmp_path):
    path = tmp_path.joinpath(*MANIFEST_PARTS)
    path.parent.mkdir(parents=True)
    lock = path.parent / ".manifest.lock"
    lock.write_text("held", encoding="utf-8")
    with pytest.raises(RuntimeError, match="índice"):
        save_manifest(path, {"at_utc": "t", "source": "phone_mjpeg", "revision": 0, "sessions": []})


def test_derived_encounter_id_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="no puede derivarse"):
        commit_phone_session(
            tmp_path, "K01", "run_a", [_shot(5)], 0, _detector(), "tune", "K01-tune-run_a")


def _pending_after_failed_rename(tmp_path, monkeypatch):
    real_rename = Path.rename

    def boom(self, target):
        if ".pending-run_a" in str(self):
            raise OSError("simulated rename failure")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", boom)
    with pytest.raises(OSError, match="simulated"):
        commit_phone_session(
            tmp_path, "K01", "run_a", [_shot(5)], 0, _detector(), "tune", "enc-k01-a")
    monkeypatch.undo()
    return tmp_path.joinpath(*LOT_PARTS, "K01", ".pending-run_a")


def test_corrupt_registered_pending_is_kept_for_review(tmp_path, monkeypatch):
    pending = _pending_after_failed_rename(tmp_path, monkeypatch)
    (pending / "hog.npz").write_bytes(b"not-an-npz")
    with pytest.raises(ValueError, match="conserva"):
        recover_unpublished_lot(tmp_path, "K01", "run_a")
    assert pending.is_dir()
    assert (pending / "hog.npz").read_bytes() == b"not-an-npz"
    assert not tmp_path.joinpath(*LOT_PARTS, "K01", "run_a").exists()


def test_second_commit_same_key_does_not_touch_first_pending(tmp_path):
    pending = tmp_path.joinpath(*LOT_PARTS, "K01", ".pending-run_a")
    pending.mkdir(parents=True)
    marker = pending / "first.txt"
    marker.write_text("first-writer", encoding="utf-8")
    with pytest.raises(FileExistsError, match="pendiente|reservada"):
        commit_phone_session(
            tmp_path, "K01", "run_a", [_shot(5)], 0, _detector(), "tune", "enc-k01-a")
    assert marker.read_text(encoding="utf-8") == "first-writer"
    assert pending.is_dir()
    assert not tmp_path.joinpath(*LOT_PARTS, "K01", "run_a").exists()


def test_pending_with_other_encounter_is_kept(tmp_path, monkeypatch):
    pending = _pending_after_failed_rename(tmp_path, monkeypatch)
    records_path = pending / "records.json"
    records = json.loads(records_path.read_text(encoding="utf-8-sig"))
    records["encounter_id"] = "enc-other-day"
    records_path.write_text(json.dumps(records), encoding="utf-8")
    with pytest.raises(ValueError, match="conserva"):
        recover_unpublished_lot(tmp_path, "K01", "run_a")
    assert pending.is_dir()
    assert json.loads(records_path.read_text(encoding="utf-8"))["encounter_id"] == "enc-other-day"
