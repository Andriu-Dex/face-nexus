"""Pruebas con patrones sintéticos, sin abrir cámara ni almacenar rostros."""

import json

import numpy as np
import pytest

from scripts.pilot_audit import audit_pilot
from scripts.pilot_capture import PEOPLE, create_session, save_sample, shot_plan


def synthetic_frame(person_index, number):
    image = np.full((1080, 1920, 3), 30 + person_index * 30, dtype=np.uint8)
    image[100:300, number * 40:number * 40 + 100, :] = (100, 180, 250)
    image[500:700, 200:600, person_index % 3] = number * 10
    return image


def test_synthetic_80_photo_pilot_and_audit(tmp_path):
    for index, person in enumerate(PEOPLE):
        session = create_session(tmp_path, person, "synthetic")
        for number in range(1, 21):
            save_sample(session, person, number, synthetic_frame(index, number), "synthetic")
    report = audit_pilot(tmp_path, "synthetic")
    assert report["total"] == 80
    assert report["structural_pass"]
    assert report["counts"] == dict.fromkeys(PEOPLE, 20)
    assert len(report["quality_measurements_no_threshold"]) == 80
    assert not audit_pilot(tmp_path, "camera")["structural_pass"]


def test_refuses_overwrite_and_keeps_original(tmp_path):
    session = create_session(tmp_path, "K01", "synthetic")
    frame = synthetic_frame(0, 1)
    saved = save_sample(session, "K01", 1, frame, "synthetic")
    with pytest.raises(FileExistsError):
        save_sample(session, "K01", 1, synthetic_frame(0, 2), "synthetic")
    assert json.loads((session / "K01_P01_0001.json").read_text(encoding="utf-8")) == saved
    with pytest.raises(FileExistsError):
        create_session(tmp_path, "K01", "synthetic")


def test_detects_duplicate_corruption_missing_record_and_wrong_partition(tmp_path):
    session = create_session(tmp_path, "K01", "synthetic")
    for number in (1, 2, 3, 4):
        save_sample(session, "K01", number, synthetic_frame(0, 1), "synthetic")
    (session / "K01_P01_0003.png").write_bytes(b"corrupted")
    (session / "K01_P01_0004.json").unlink()
    meta_path = session / "K01_P01_0002.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["split"] = "TEST"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    report = audit_pilot(tmp_path, "synthetic")
    reasons = [issue["reason"] for issue in report["issues"]]
    assert "Hash no coincide" in reasons
    assert "PNG sin metadatos" in reasons
    assert "Fuente o partición incorrecta" in reasons
    save_sample(session, "K01", 5, synthetic_frame(0, 1), "synthetic")
    assert audit_pilot(tmp_path, "synthetic")["exact_duplicates"]


def test_save_failure_rolls_back_only_new_image(tmp_path, monkeypatch):
    import scripts.pilot_capture as module
    session = create_session(tmp_path, "K01", "synthetic")
    monkeypatch.setattr(module.json, "dump", lambda *a, **kw: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(OSError):
        save_sample(session, "K01", 1, synthetic_frame(0, 1), "synthetic")
    assert not (session / "K01_P01_0001.png").exists()
    # Un JSON parcial se conserva como incidencia auditable, nunca como toma válida.
    assert not audit_pilot(tmp_path, "synthetic")["structural_pass"]


@pytest.mark.parametrize("shape", [(480, 640, 3), (1080, 1920)])
def test_does_not_resize_invalid_original(tmp_path, shape):
    session = create_session(tmp_path, "K01", "synthetic")
    with pytest.raises(ValueError):
        save_sample(session, "K01", 1, np.zeros(shape, dtype=np.uint8), "synthetic")
    assert not list(session.iterdir())


def test_plan_has_ten_per_light_and_four_per_block():
    from collections import Counter
    plans = [shot_plan(number) for number in range(1, 21)]
    assert Counter(p["lighting"] for p in plans) == {"diffuse": 10, "lateral": 10}
    assert set(Counter(p["block"] for p in plans).values()) == {4}
    with pytest.raises(ValueError):
        shot_plan(21)


@pytest.mark.parametrize("read_result", [(False, None), (True, np.zeros((10, 10, 3), dtype=np.uint8))])
def test_camera_failure_releases_without_saving_or_fallback(monkeypatch, tmp_path, read_result):
    from types import SimpleNamespace
    import cv2_enumerate_cameras
    import scripts.pilot_capture as module

    released = []
    camera = SimpleNamespace(isOpened=lambda: True, set=lambda *args: True,
                             get=lambda *args: 30, getBackendName=lambda: "fake",
                             read=lambda: read_result, release=lambda: released.append(True))
    opened = []

    def open_camera(index, backend):
        opened.append(index)
        return camera

    monkeypatch.setattr(cv2_enumerate_cameras, "enumerate_cameras",
                        lambda backend: [SimpleNamespace(index=1, name="USB CAMERA")])
    monkeypatch.setattr(module, "check_private_destination", lambda: None)
    monkeypatch.setattr(module, "DATA", tmp_path)
    monkeypatch.setattr(module.cv2, "VideoCapture", open_camera)
    monkeypatch.setattr(module.cv2, "destroyAllWindows", lambda: None)
    monkeypatch.setattr("builtins.input", lambda prompt: "CAPTURAR")
    with pytest.raises(RuntimeError):
        module.run_camera("K01", 1, 10)
    assert opened == [1]
    assert released == [True]
    assert not list(tmp_path.iterdir())
