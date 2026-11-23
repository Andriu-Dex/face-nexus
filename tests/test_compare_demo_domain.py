from hashlib import sha256
import json

import numpy as np
import pytest

from scripts.compare_demo_domain import (
    bind_npz_rows, disjoint_status, identities_disjoint, load_bound_identity_ids,
    per_person_report, provenance_from_npz, write_trial_calibration,
)
from scripts.hog_knn import FEATURE_COUNT, PEOPLE


def test_per_person_counts_correct_confused_and_rejected():
    true = np.array(["K01", "K01", "K02", "K03"])
    pred = np.array(["K01", "K04", "OTHER", "K03"])
    rows = per_person_report(true, pred)
    assert rows["K01"] == {"n": 2, "correct": 1, "confused": 1, "rejected": 0}
    assert rows["K02"] == {"n": 1, "correct": 0, "confused": 0, "rejected": 1}
    assert rows["K03"]["correct"] == 1
    assert set(rows) == set(PEOPLE)


def test_unknown_group_must_be_disjoint_from_calibration():
    assert identities_disjoint(["lfw_train"], ["lfw_val", "U01"])
    assert not identities_disjoint(["U01", "U02"], ["U02"])
    assert disjoint_status(None, None)["verified"] is False


def _write_npz(path, labels, sample_ids=None, identity_ids=None):
    vectors = np.zeros((len(labels), FEATURE_COUNT), np.float32)
    payload = {"vectors": vectors, "labels": np.array(labels, dtype=str)}
    if sample_ids is not None:
        payload["sample_ids"] = np.array(sample_ids, dtype=str)
    if identity_ids is not None:
        payload["identity_ids"] = np.array(identity_ids, dtype=str)
    np.savez(path, **payload)
    return sha256(path.read_bytes()).hexdigest()


def test_bind_npz_rows_requires_hash_and_other_labels(tmp_path):
    npz = tmp_path / "unknowns.npz"
    digest = _write_npz(npz, ["OTHER", "OTHER"], ["u1", "u2"])
    rows = tmp_path / "unknown_rows.json"
    rows.write_text(json.dumps({
        "file_sha256": digest,
        "rows": [
            {"index": 0, "identity_id": "U01", "label": "OTHER", "sample_id": "u1"},
            {"index": 1, "identity_id": "U02", "label": "OTHER", "sample_id": "u2"},
        ],
    }), encoding="utf-8")
    _vectors, labels, ids = bind_npz_rows(npz, rows, id_key="identity_id", expected_label="OTHER")
    assert ids == ["U01", "U02"]
    assert set(map(str, labels)) == {"OTHER"}
    wrong = tmp_path / "wrong_hash.json"
    wrong.write_text(json.dumps({
        "file_sha256": "00" * 32,
        "rows": json.loads(rows.read_text(encoding="utf-8"))["rows"],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="huella"):
        bind_npz_rows(npz, wrong, id_key="identity_id", expected_label="OTHER")


def test_count_match_does_not_bind_unknowns(tmp_path):
    npz = tmp_path / "unknowns.npz"
    digest = _write_npz(npz, ["K01", "K01"], ["u1", "u2"])
    rows = tmp_path / "rows.json"
    rows.write_text(json.dumps({
        "file_sha256": digest,
        "rows": [
            {"index": 0, "identity_id": "U01", "label": "OTHER", "sample_id": "u1"},
            {"index": 1, "identity_id": "U02", "label": "OTHER", "sample_id": "u2"},
        ],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="OTHER"):
        bind_npz_rows(npz, rows, id_key="identity_id", expected_label="OTHER")


def test_unknowns_require_sample_ids(tmp_path):
    npz = tmp_path / "unknowns.npz"
    digest = _write_npz(npz, ["OTHER"])
    rows = tmp_path / "rows.json"
    rows.write_text(json.dumps({
        "file_sha256": digest,
        "rows": [{"index": 0, "identity_id": "U01", "label": "OTHER"}],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="sample_ids"):
        bind_npz_rows(npz, rows, id_key="identity_id", expected_label="OTHER")


def test_calibration_ids_unbound_even_with_gallery_hash(tmp_path):
    artifact = tmp_path / "gallery.npz"
    _write_npz(artifact, ["K01"], ["g1"])
    listed = tmp_path / "cal.json"
    listed.write_text(json.dumps({
        "file_sha256": sha256(artifact.read_bytes()).hexdigest(),
        "identity_ids": ["lfw_train"],
    }), encoding="utf-8")
    ids, bound = load_bound_identity_ids(listed, artifact)
    assert ids == ["lfw_train"] and bound is False
    assert disjoint_status(ids, ["U01"], calibration_bound=bound, evaluation_bound=True)[
        "verified"] is False


def test_calibration_provenance_comes_from_used_rows(tmp_path):
    npz = tmp_path / "cal.npz"
    _write_npz(npz, ["OTHER", "OTHER"], ["s1", "s2"], ["U01", "U02"])
    ids, bound, rows = provenance_from_npz(npz)
    assert bound is False
    assert ids == ["U01", "U02"]
    assert rows[0]["sample_id"] == "s1"
    missing = tmp_path / "only_hash.npz"
    _write_npz(missing, ["OTHER"], ["s1"])
    ids, bound, rows = provenance_from_npz(missing)
    assert bound is False and ids is None


def test_foreign_or_vectorless_calibration_stays_unverified(tmp_path):
    gallery_digest = "ab" * 32
    used = tmp_path / "used.npz"
    record = write_trial_calibration(
        used,
        np.zeros((2, FEATURE_COUNT), np.float32),
        ["OTHER", "OTHER"],
        ["s1", "s2"],
        ["U01", "U02"],
        gallery_sha256=gallery_digest,
    )
    summary = {
        "calibration_npz_sha256": record["calibration_npz_sha256"],
        "gallery_sha256": gallery_digest,
    }
    ids, bound, _rows = provenance_from_npz(
        used, trial_summary=summary, gallery_sha256=gallery_digest)
    assert bound is True and ids == ["U01", "U02"]

    other = tmp_path / "other_trial.npz"
    write_trial_calibration(
        other,
        np.ones((2, FEATURE_COUNT), np.float32),
        ["OTHER", "OTHER"],
        ["t1", "t2"],
        ["U10", "U11"],
        gallery_sha256=gallery_digest,
    )
    _ids, bound, _rows = provenance_from_npz(
        other, trial_summary=summary, gallery_sha256=gallery_digest)
    assert bound is False

    bare = tmp_path / "no_vectors.npz"
    np.savez(bare, labels=np.array(["OTHER"], dtype=str),
             sample_ids=np.array(["s1"], dtype=str),
             identity_ids=np.array(["U01"], dtype=str))
    _ids, bound, _rows = provenance_from_npz(
        bare, trial_summary=summary, gallery_sha256=gallery_digest)
    assert bound is False


def test_enrolled_rows_need_sample_ids(tmp_path):
    npz = tmp_path / "enrolled.npz"
    digest = _write_npz(npz, ["K01"], ["K01_PHONE_0001"])
    rows = tmp_path / "enrolled_rows.json"
    rows.write_text(json.dumps({
        "file_sha256": digest,
        "rows": [{"index": 0, "person_id": "K01", "label": "K01", "sample_id": "K01_PHONE_0001"}],
    }), encoding="utf-8")
    _vectors, labels, ids = bind_npz_rows(npz, rows, id_key="person_id")
    assert ids == ["K01"] and str(labels[0]) == "K01"
    missing = tmp_path / "no_ids.npz"
    digest2 = _write_npz(missing, ["K01"])
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({
        "file_sha256": digest2,
        "rows": [{"index": 0, "person_id": "K01", "label": "K01"}],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="sample_ids"):
        bind_npz_rows(missing, bad, id_key="person_id")
