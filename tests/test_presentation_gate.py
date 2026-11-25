from scripts.operator_ui import may_send_physical
from scripts.presentation_gate import (
    AUTHORIZED, EMPTY, HEARTBEAT_SECONDS, UNCERTAIN, PresentationGate, scene_kind,
)


def test_recognition_does_not_actuate_until_enabled():
    gate = PresentationGate()
    assert may_send_physical("camera", AUTHORIZED, gate) is False
    assert may_send_physical("file", AUTHORIZED, gate, recognition_actuation=True) is False


def test_authorized_renews_open_once_per_heartbeat():
    gate = PresentationGate()
    assert gate.on_frame(AUTHORIZED, now=10.0) is True
    assert gate.on_frame(AUTHORIZED, now=10.1) is False
    assert gate.on_frame(AUTHORIZED, now=10.0 + HEARTBEAT_SECONDS) is True


def test_non_authorized_frames_send_nothing():
    gate = PresentationGate()
    for kind in (EMPTY, UNCERTAIN):
        assert gate.on_frame(kind, now=1.0) is False
    assert gate.last_sent is None


def test_fault_blocks_until_operator_rearms():
    gate = PresentationGate()
    gate.note_fault()
    assert gate.on_frame(AUTHORIZED, now=5.0) is False
    gate.rearm()
    assert gate.on_frame(AUTHORIZED, now=5.0) is True


def test_scene_kind_splits_empty_from_uncertain():
    assert scene_kind({"outcome": "GRANTED", "reason": "authorized"}) == AUTHORIZED
    assert scene_kind({"outcome": "DENIED", "reason": "no_face"}) == EMPTY
    assert scene_kind({"outcome": "DENIED", "reason": "unknown_identity"}) == UNCERTAIN
    assert scene_kind({"outcome": "DENIED", "reason": "permission_inactive"}) == UNCERTAIN
