import json

import numpy as np
import pytest
from scripts.compare_identity_k01 import write_gallery
from scripts.hog_knn import FEATURE_COUNT, PEOPLE, SFACE_FEATURE_COUNT
from scripts.identity_artifacts import bind_threshold, file_digest, load_verified_knn
from scripts.live_k01 import identify_knn


def _bundle(folder, digest_override=None, threshold=0.5):
    vectors = np.zeros((4, FEATURE_COUNT), np.float32)
    labels = np.array(PEOPLE)
    digest = write_gallery(folder / "gallery.npz", vectors, labels)
    payload = {"max_distance": threshold, "gallery_sha256": digest_override or digest}
    (folder / "knn_max_distance.json").write_text(json.dumps(payload), encoding="utf-8")
    return digest


def test_sface_gallery_requires_matching_preprocessing(tmp_path):
    vectors = np.eye(len(PEOPLE), SFACE_FEATURE_COUNT, dtype=np.float32)
    digest = write_gallery(tmp_path / "gallery.npz", vectors, np.array(PEOPLE))
    path = tmp_path / "knn_max_distance.json"
    record = {"max_distance": 0.5, "gallery_sha256": digest}
    path.write_text(json.dumps(record), encoding="utf-8")
    assert load_verified_knn(tmp_path)[0] is None
    path.write_text(json.dumps({**record, "preprocessing": "sface"}), encoding="utf-8")
    bundle, reason = load_verified_knn(tmp_path)
    assert reason is None and bundle["preprocessing"] == "sface"
    np.testing.assert_array_equal(bundle["vectors"], vectors)


def test_verified_pair_and_failures(tmp_path):
    _bundle(tmp_path)
    bundle, reason = load_verified_knn(tmp_path)
    assert reason is None and bundle["max_distance"] == 0.5
    identify = identify_knn(bundle["vectors"], bundle["labels"], bundle["max_distance"])
    far = np.ones(FEATURE_COUNT, np.float32)
    far /= np.linalg.norm(far)
    _label, accepted, _ = identify(far)
    assert accepted is False

    other = tmp_path / "other"
    other.mkdir()
    _bundle(other, digest_override="0" * 64)
    assert load_verified_knn(other)[1] == "model_unavailable"
    empty = tmp_path / "empty"
    empty.mkdir()
    assert load_verified_knn(empty)[1] == "model_unavailable"
    bad = tmp_path / "bad"
    bad.mkdir()
    digest = write_gallery(bad / "gallery.npz", np.zeros((4, FEATURE_COUNT), np.float32),
                           np.array(PEOPLE))
    (bad / "knn_max_distance.json").write_text(
        json.dumps({"max_distance": -1, "gallery_sha256": digest}), encoding="utf-8")
    assert load_verified_knn(bad)[1] == "model_unavailable"
    text = tmp_path / "text"
    text.mkdir()
    digest = _bundle(text, threshold="0.5")
    assert load_verified_knn(text)[1] == "model_unavailable"
    flag = tmp_path / "flag"
    flag.mkdir()
    _bundle(flag, threshold=True)
    assert load_verified_knn(flag)[1] == "model_unavailable"
    gap = tmp_path / "gap"
    gap.mkdir()
    digest = write_gallery(gap / "gallery.npz", np.zeros((4, FEATURE_COUNT), np.float32),
                           np.array(PEOPLE))
    (gap / "knn_max_distance.json").write_text(
        json.dumps({"max_distance": 0.5, "min_gap": True, "gallery_sha256": digest}),
        encoding="utf-8")
    assert load_verified_knn(gap)[1] == "model_unavailable"


def test_bind_writes_gallery_hash_when_summary_matches(tmp_path):
    vectors = np.zeros((4, FEATURE_COUNT), np.float32)
    digest = write_gallery(tmp_path / "gallery.npz", vectors, np.array(PEOPLE))
    distance = tmp_path / "knn_max_distance.json"
    distance.write_text(json.dumps({"max_distance": 0.4}), encoding="utf-8")
    (tmp_path / "summary.json").write_text(
        json.dumps({"gallery_sha256": digest}), encoding="utf-8")
    assert bind_threshold(tmp_path) == digest
    bundle, reason = load_verified_knn(tmp_path)
    assert reason is None and bundle["gallery_sha256"] == digest


def test_bind_leaves_file_if_summary_missing_or_wrong(tmp_path):
    vectors = np.zeros((4, FEATURE_COUNT), np.float32)
    write_gallery(tmp_path / "gallery.npz", vectors, np.array(PEOPLE))
    distance = tmp_path / "knn_max_distance.json"
    original = json.dumps({"max_distance": 0.4})
    distance.write_text(original, encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="registro"):
        bind_threshold(tmp_path)
    assert distance.read_text(encoding="utf-8") == original
    (tmp_path / "summary.json").write_text(
        json.dumps({"gallery_sha256": "0" * 64}), encoding="utf-8")
    with pytest.raises(ValueError, match="no coincide"):
        bind_threshold(tmp_path)
    assert distance.read_text(encoding="utf-8") == original


def test_truncated_npz_and_missing_identities_are_unavailable(tmp_path):
    broken = tmp_path / "broken"
    broken.mkdir()
    npz = broken / "gallery.npz"
    npz.write_bytes(b"PK\x03\x04not-a-real-archive")
    digest = file_digest(npz)
    (broken / "knn_max_distance.json").write_text(
        json.dumps({"max_distance": 0.4, "gallery_sha256": digest}), encoding="utf-8")
    assert load_verified_knn(broken)[1] == "model_unavailable"

    only_k01 = tmp_path / "k01"
    only_k01.mkdir()
    vectors = np.zeros((3, FEATURE_COUNT), np.float32)
    digest = write_gallery(only_k01 / "gallery.npz", vectors, np.array(["K01", "K01", "K01"]))
    (only_k01 / "knn_max_distance.json").write_text(
        json.dumps({"max_distance": 0.4, "gallery_sha256": digest}), encoding="utf-8")
    assert load_verified_knn(only_k01)[1] == "model_unavailable"
