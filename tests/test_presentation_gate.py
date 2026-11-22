from scripts.operator_ui import may_send_physical
from scripts.presentation_gate import AUTHORIZED, EMPTY, UNCERTAIN, PresentationGate, scene_kind


def test_recognition_does_not_actuate_until_enabled():
    gate = PresentationGate()
    assert may_send_physical("camera", AUTHORIZED, gate) is False
    assert may_send_physical("file", AUTHORIZED, gate, recognition_actuation=True) is False


def test_one_order_until_operator_rearms():
    gate = PresentationGate()
    assert may_send_physical("file", AUTHORIZED, gate, recognition_actuation=True) is False
    assert may_send_physical("camera", AUTHORIZED, gate, recognition_actuation=True) is True
    assert may_send_physical("camera", AUTHORIZED, gate, recognition_actuation=True) is False
    gate.rearm()
    assert may_send_physical("camera", AUTHORIZED, gate, recognition_actuation=True) is True


def test_no_face_streak_does_not_rearm_same_person():
    gate = PresentationGate()
    assert gate.on_frame(AUTHORIZED) is True
    for _ in range(8):
        assert gate.on_frame(EMPTY) is False
    assert gate.on_frame(AUTHORIZED) is False


def test_ambiguous_denials_do_not_rearm():
    gate = PresentationGate()
    assert gate.on_frame(AUTHORIZED) is True
    for _ in range(8):
        assert gate.on_frame(UNCERTAIN) is False
    assert gate.on_frame(AUTHORIZED) is False


def test_scene_kind_splits_empty_from_uncertain():
    assert scene_kind({"outcome": "GRANTED", "reason": "authorized"}) == AUTHORIZED
    assert scene_kind({"outcome": "DENIED", "reason": "no_face"}) == EMPTY
    assert scene_kind({"outcome": "DENIED", "reason": "unknown_identity"}) == UNCERTAIN
    assert scene_kind({"outcome": "DENIED", "reason": "permission_inactive"}) == UNCERTAIN
