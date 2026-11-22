from scripts.access import (
    DENIED, GRANTED, UNKNOWN, decide, decide_scene, default_permissions,
    simulate_authorize, validate_permissions,
)
from scripts.hog_knn import PEOPLE


def test_unknown_and_revoked_permission_never_grant():
    empty = decide(face_count=0, candidate="K01", accepted=True, permission_active=True)
    assert empty == {"outcome": DENIED, "reason": "no_face", "identity": UNKNOWN}
    crowd = decide(face_count=2, candidate="K01", accepted=True, permission_active=True)
    assert crowd["reason"] == "multiple_faces"
    unknown = decide(face_count=1, candidate="K03", accepted=False, permission_active=True)
    assert unknown["reason"] == "unknown_identity" and unknown["identity"] == UNKNOWN
    revoked = decide(face_count=1, candidate="K01", accepted=True, permission_active=False)
    assert revoked == {"outcome": DENIED, "reason": "permission_inactive", "identity": "K01"}
    ok = decide(face_count=1, candidate="K01", accepted=True, permission_active=True)
    assert ok == {"outcome": GRANTED, "reason": "authorized", "identity": "K01"}
    missing = decide(face_count=1, candidate="K01", accepted=True, permission_active=True,
                     model_ready=False)
    assert missing["reason"] == "model_unavailable"


def test_scene_grants_if_one_authorized_region_exists():
    denied = decide(face_count=1, candidate="K02", accepted=True, permission_active=False)
    granted = decide(face_count=1, candidate="K01", accepted=True, permission_active=True)
    scene = decide_scene([denied, granted])
    assert scene["outcome"] == GRANTED and scene["identity"] == "K01" and scene["event_id"]
    only_denied = decide_scene([denied])
    assert only_denied["outcome"] == DENIED
    simulated = simulate_authorize(scene)
    assert simulated["state"] == "SIMULATED" and simulated["physical_open"] is False
    assert set(validate_permissions(default_permissions())) == set(PEOPLE)
