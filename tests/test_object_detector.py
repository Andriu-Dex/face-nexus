from pathlib import Path

import numpy as np
import pytest

from scripts.object_detector import (
    COCO_LABELS, INPUT_SIZE, inside_screen, letterbox, load_object_detector,
)
from scripts.operator_ui import OperatorApp

MODELS = Path("models/verified")


def test_coco_labels_and_screen_rule():
    assert len(COCO_LABELS) == 80 and COCO_LABELS[67] == "celular" and COCO_LABELS[63] == "laptop"
    phone = {"label": "celular", "score": .9, "box": [100, 100, 300, 400]}
    bottle = {"label": "botella", "score": .9, "box": [100, 100, 300, 400]}
    assert inside_screen([150, 150, 250, 250], [phone])
    assert not inside_screen([150, 150, 250, 250], [bottle])
    assert not inside_screen([400, 400, 500, 500], [phone])


def test_letterbox_keeps_aspect_ratio():
    canvas, scale = letterbox(np.zeros((832, 416, 3), np.uint8))
    assert canvas.shape == (INPUT_SIZE, INPUT_SIZE, 3) and scale == .5


@pytest.mark.skipif(not (MODELS / "object_detection_nanodet_2022nov.onnx").is_file(),
                    reason="NanoDet no descargado")
def test_real_model_runs_on_blank_image():
    from scripts.object_detector import detect_objects
    assert detect_objects(load_object_detector(MODELS), np.zeros((480, 640, 3), np.uint8)) == []


def test_face_inside_screen_is_denied_but_real_face_passes(tmp_path, monkeypatch):
    def granted(_frame, _permissions):
        regions = [{"outcome": "GRANTED", "reason": "authorized", "identity": "K01",
                    "box": [150, 150, 250, 250]}]
        return {**regions[0], "event_id": "1", "regions": regions}

    screens = [{"label": "celular", "score": .8, "box": [100, 100, 300, 400]}]
    monkeypatch.setattr("scripts.operator_ui.detect_objects", lambda _net, _frame: screens)
    monkeypatch.setattr("scripts.operator_ui.load_object_detector", lambda _path: object())
    app = OperatorApp(granted, config_path=tmp_path / "cam.json")
    app.window.withdraw()
    frame = np.zeros((480, 640, 3), np.uint8)
    app.objects_var.set(True)
    app._toggle_objects()
    shown = app.recognize_frame(frame)
    assert shown["outcome"] == "GRANTED" and shown["objects"][0]["label"] == "celular"
    app.screens_var.set(True)
    app._toggle_objects()
    blocked = app.recognize_frame(frame)
    assert blocked["outcome"] == "DENIED" and blocked["reason"] == "face_on_screen"
    screens.clear()
    assert app.recognize_frame(frame)["outcome"] == "GRANTED"
    app.window.destroy()
