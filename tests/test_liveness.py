from scripts.liveness import MIN_SPAN, LivenessCheck, turn_ratio
from scripts.presentation_gate import AUTHORIZED, UNCERTAIN


def face(nose_x, identity="K01", outcome="GRANTED"):
    # Ojo derecho en x=100, ojo izquierdo en x=200: distancia 100, punto medio 150.
    return {"outcome": outcome, "identity": identity,
            "landmarks": [[100, 100], [200, 100], [nose_x, 150], [120, 200], [180, 200]]}


def scene(*regions):
    return {"regions": list(regions)}


def test_turn_ratio_is_nose_offset_over_eye_distance():
    assert turn_ratio(face(150)["landmarks"]) == 0
    assert turn_ratio(face(180)["landmarks"]) == 0.3
    # Perfil completo: los ojos casi coinciden; la muestra se descarta.
    assert turn_ratio([[100, 100], [101, 100], [140, 150]]) is None


def test_flat_photo_never_passes_and_real_turn_does():
    check = LivenessCheck()
    # Una foto inclinada mueve la nariz muy poco respecto de los ojos.
    for step, nose in enumerate((150, 155, 145, 158, 142)):
        assert check.update(scene(face(nose)), step * .1) is False
    # La cabeza real gira: la razón recorre más que MIN_SPAN.
    assert check.update(scene(face(150 + 100 * (MIN_SPAN + .05))), .6) is True


def test_another_person_cannot_lend_the_turn():
    check = LivenessCheck()
    check.update(scene(face(110, identity="K02")), 0)
    check.update(scene(face(190, identity="K02")), .1)
    assert check.passed
    # Aparece otra identidad: debe repetir la prueba.
    assert check.update(scene(face(150, identity="K01")), .2) is False


def test_unknown_faces_do_not_count_and_absence_resets():
    check = LivenessCheck()
    check.update(scene(face(100, outcome="DENIED")), 0)
    check.update(scene(face(200, outcome="DENIED")), .1)
    assert not check.passed
    check.update(scene(face(110)), .2)
    check.update(scene(face(190)), .3)
    assert check.passed
    assert check.update(scene(), 1.0) is True
    assert check.update(scene(), 1.5) is False


def test_operator_ui_holds_latch_until_turn(tmp_path, monkeypatch):
    from scripts.operator_ui import OperatorApp

    kinds = []
    monkeypatch.setattr("scripts.operator_ui.may_send_physical",
                        lambda source, kind, gate, actuate: kinds.append(kind) or False)
    app = OperatorApp(lambda _f, _p: {}, config_path=tmp_path / "cam.json")
    app.window.withdraw()
    app.liveness_var.set(True)
    app._toggle_liveness()
    granted = {"outcome": "GRANTED", "reason": "authorized", "identity": "K01",
               "regions": [face(150)]}
    app._commit_scene(granted, "camera")
    assert kinds[-1] == UNCERTAIN
    app._commit_scene({**granted, "regions": [face(195)]}, "camera")
    assert kinds[-1] == AUTHORIZED
    app.window.destroy()
