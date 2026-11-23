from copy import deepcopy

from scripts.compare_demo_domain import disjoint_status, identities_disjoint
from scripts.phone_demo_manifest import (
    MANIFEST_PARTS, check_phone_manifest, empty_manifest, load_manifest, phone_eval_ready,
    phone_tune_ready, require_explicit_encounter, require_phone_manifest, save_manifest,
    session_record, synthetic_manifest,
)


def test_synthetic_manifest_is_complete_and_flags_missing_class():
    issues, warnings = check_phone_manifest(synthetic_manifest())
    assert issues == []
    assert warnings == []
    _, missing = check_phone_manifest(synthetic_manifest(missing={"K02"}))
    assert any("K02" in item for item in missing)


def test_duplicate_hash_across_tune_and_eval_is_an_error():
    broken = synthetic_manifest(duplicate_across=True)
    issues, _warnings = check_phone_manifest(broken)
    assert any("idénticas" in item for item in issues)
    try:
        require_phone_manifest(broken)
        assert False
    except ValueError as error:
        assert "idénticas" in str(error)


def test_phone_eval_ready_false_on_errors_or_zero_usable():
    _, _, ok = phone_eval_ready(synthetic_manifest())
    assert ok is True
    _, _, broken = phone_eval_ready(synthetic_manifest(duplicate_across=True))
    assert broken is False
    _, _, empty = phone_eval_ready(synthetic_manifest(zero_usable=True))
    assert empty is False
    _, _, crossed = phone_eval_ready(synthetic_manifest(shared_encounter=True))
    assert crossed is False
    _, _, missing = phone_eval_ready(synthetic_manifest(missing={"K02"}))
    assert missing is False
    _, _, tune_ok = phone_tune_ready(synthetic_manifest())
    assert tune_ok is True


def test_disjoint_status_unverified_without_identity_lists():
    assert identities_disjoint(["a"], ["b"])
    assert disjoint_status(None, ["U01"]) == {"verified": False, "disjoint": None}
    assert disjoint_status(["lfw_train"], ["lfw_val"]) == {"verified": False, "disjoint": None}
    assert disjoint_status(
        ["lfw_train"], ["lfw_val"], calibration_bound=True, evaluation_bound=True
    ) == {"verified": True, "disjoint": True}


def test_explicit_encounter_rejects_role_derived_name():
    try:
        require_explicit_encounter("K01-tune-run_a", "K01", "tune", "run_a")
        assert False
    except ValueError as error:
        assert "no puede derivarse" in str(error)


def test_two_writers_from_same_revision_reject_stale(tmp_path):
    path = tmp_path.joinpath(*MANIFEST_PARTS)
    save_manifest(path, empty_manifest())
    first = load_manifest(path)
    second = deepcopy(first)
    assert first["revision"] == second["revision"] == 0

    def apply(snapshot, run_name, digest):
        payload = deepcopy(snapshot)
        payload.setdefault("sessions", [])
        payload["sessions"] = list(payload["sessions"])
        payload["sessions"].append(session_record(
            "K01", run_name, "tune", 0, [digest],
            sampled=1, usable=1, encounter_id="enc-k01-lock"))
        require_phone_manifest(payload)
        payload["revision"] = int(payload.get("revision") or 0) + 1
        save_manifest(path, payload, expected_revision=int(snapshot.get("revision") or 0))

    apply(first, "run_a", "aa" * 32)
    try:
        apply(second, "run_b", "bb" * 32)
        assert False
    except ValueError as error:
        assert "desactualizada" in str(error)
    kept = load_manifest(path)
    assert len(kept["sessions"]) == 1
    assert kept["sessions"][0]["run_name"] == "run_a"
