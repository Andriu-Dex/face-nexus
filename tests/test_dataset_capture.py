import json
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from scripts import capture_manifest as manifest
from scripts import dataset_capture as capture


def session(person, number, round_number, split, first_light="diffuse"):
    return {
        "person_id": person, "session_id": f"{person}_S{number:02d}",
        "round_id": f"R{round_number:02d}", "split": split,
        "first_light": first_light, "consent_ref": "synthetic",
        "setup": "Condiciones de prueba",
    }


def create_session(root, row):
    folder = root / row["session_id"]
    snapshot = {"source": "synthetic", "plan": row}
    manifest.publish_directory(folder, snapshot)
    return folder, snapshot


@pytest.fixture
def frame():
    return np.zeros(manifest.FRAME_SHAPE, dtype=np.uint8)


def test_plan_enforces_unique_sessions_rounds_and_unknown_groups():
    first = session("U01", 2, 1, "VALIDATION")
    with pytest.raises(ValueError, match="desconocido"):
        manifest.validate_plan([first, session("U01", 3, 2, "TEST")])
    with pytest.raises(ValueError, match="desconocido"):
        manifest.validate_plan([session("U01", 2, 1, "TRAIN")])
    with pytest.raises(ValueError, match="partición"):
        manifest.validate_plan([first, session("K01", 2, 1, "TRAIN")])
    with pytest.raises(ValueError, match="repetid"):
        manifest.validate_plan([first, {**first, "round_id": "R02"}])
    with pytest.raises(ValueError, match="repetid"):
        manifest.validate_plan([first, session("U01", 3, 1, "VALIDATION")])
    with pytest.raises(ValueError, match="histórica"):
        manifest.validate_plan([session("K01", 1, 1, "TRAIN")])
    with pytest.raises(ValueError, match="inválido"):
        manifest.validate_plan([{**first, "session_id": ".."}])


def test_full_synthetic_acquisition_and_integrity(tmp_path, frame):
    rows = [
        session("K01", 2, 1, "TRAIN"),
        session("K01", 3, 2, "VALIDATION", "lateral"),
        session("U01", 2, 2, "VALIDATION", "lateral"),
        session("U02", 2, 3, "TEST"),
    ]
    plan = manifest.validate_plan(rows)
    for index, row in enumerate(rows):
        folder, snapshot = create_session(tmp_path, row)
        shots = manifest.shots_for(row)
        assert [shot["lighting"] for shot in shots[:10]] == [row["first_light"]] * 10
        assert len({shot["lighting"] for shot in shots[10:]}) == 1
        assert shots[10]["lighting"] != shots[0]["lighting"]
        for number, shot in enumerate(shots, 1):
            frame[0, 0] = (index, number, 97)
            record = manifest.record_attempt(
                folder, snapshot, "saved", frame=frame, distance=shot["distance_m"],
            )
            assert record["shot_number"] == number
    audit = manifest.audit_dataset(plan, tmp_path)
    assert not audit["issues"] and not audit["exact_duplicates"]
    assert sum(row["accepted"] for row in audit["sessions"].values()) == 80
    original = tmp_path / "K01_S02" / "attempts" / "A000001" / "K01_S02_A000001.png"
    decoded = cv2.imdecode(np.frombuffer(original.read_bytes(), np.uint8), cv2.IMREAD_UNCHANGED)
    assert decoded[0, 0].tolist() == [0, 1, 97]
    original.write_bytes(original.read_bytes() + b"corruption")
    assert any("SHA-256" in issue for issue in manifest.audit_dataset(plan, tmp_path)["issues"])


def test_repeat_and_exclusion_keep_original_and_record_reason(tmp_path, frame):
    row = session("K01", 2, 1, "TRAIN")
    row["difficult"] = [{"label": "Perfil", "lighting": "lateral", "distance_m": .8}]
    folder, snapshot = create_session(tmp_path, row)
    assert len(manifest.shots_for(row)) == 21
    original = manifest.record_attempt(folder, snapshot, "saved", frame=frame, distance=.83)
    excluded = manifest.record_attempt(folder, snapshot, "excluded", reason="Encuadre")
    rejected = manifest.record_attempt(folder, snapshot, "rejected", reason="Interrupción")
    replaced = manifest.record_attempt(folder, snapshot, "saved", frame=frame, distance=.85)
    assert excluded["reason"] == "Encuadre" and rejected["reason"] == "Interrupción"
    for event in (excluded, rejected, replaced):
        assert event["related_attempt"] == original["attempt"]
        assert event["shot_number"] == 1
    assert (folder / "attempts" / "A000001" / original["relative_path"]).is_file()
    assert replaced["distance_approx_m"] == .85
    assert manifest.replay_attempts(folder, snapshot, verify_images=True)[:3] == (4, [4], {1: 1})


def test_interrupted_attempt_never_publishes_half_record(tmp_path, frame, monkeypatch):
    row = session("K01", 2, 1, "TRAIN")
    folder, snapshot = create_session(tmp_path, row)
    write = manifest.write_synced

    def fail_manifest(path, payload):
        if path.name == "record.json":
            raise OSError("Fallo de escritura simulado")
        write(path, payload)

    monkeypatch.setattr(manifest, "write_synced", fail_manifest)
    with pytest.raises(OSError, match="simulado"):
        manifest.record_attempt(folder, snapshot, "saved", frame=frame, distance=.8)
    assert not (folder / "attempts" / "A000001").exists()
    assert not manifest.replay_attempts(folder, snapshot)[1]
    audit = manifest.audit_dataset(manifest.validate_plan([row]), tmp_path)
    assert any("interrumpida" in issue for issue in audit["issues"])
    with pytest.raises(ValueError, match="interrumpida"):
        manifest.record_attempt(folder, snapshot, "saved", frame=frame, distance=.8)


def test_snapshot_prevents_reassignment_and_audit_flags_cross_split_duplicates(tmp_path, frame):
    train = session("K01", 2, 1, "TRAIN")
    test = session("K01", 3, 2, "TEST")
    for row in (train, test):
        folder, snapshot = create_session(tmp_path, row)
        manifest.record_attempt(folder, snapshot, "saved", frame=frame, distance=.8)
    report = manifest.audit_dataset(manifest.validate_plan([train, test]), tmp_path)
    assert any("idénticos entre particiones" in issue for issue in report["issues"])
    plan_path = tmp_path.parent / f"{tmp_path.name}.json"
    plan_path.write_text(json.dumps([{**train, "split": "VALIDATION"}, test]), encoding="utf-8")
    with pytest.raises(ValueError, match="cambió"):
        manifest.load_schedule(plan_path, tmp_path)


def test_camera_check_and_capture_guard_with_doubles(tmp_path, monkeypatch):
    device = SimpleNamespace(index=1, path="usb-device")
    fake_camera = SimpleNamespace(release=lambda: None)
    measurement = {
        "status": "completed", "observed_dimensions": {"1920x1080": 1700},
        "failed_reads_including_warmup": 0, "delivery_fps": 29.21, "gaps_over_threshold": 0,
    }
    answers = iter(["TMCAM", "APROBAR"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(capture, "tmcamera", lambda _: device)
    monkeypatch.setattr(capture.cv2, "VideoCapture", lambda *args: fake_camera)
    monkeypatch.setattr(capture.cv2, "destroyAllWindows", lambda: None)
    monkeypatch.setattr(capture, "configure_camera", lambda _: {})
    monkeypatch.setattr(capture, "measure_capture", lambda *args, **kwargs: measurement)
    monkeypatch.setattr(capture, "inspect_bands", lambda *args: False)
    assert capture.check_camera(tmp_path, "R01", 1, "unconfirmed") == 0
    check = next(iter(manifest.active_records(tmp_path / "checks").values()))
    assert check["antiflicker_60hz"] == "unconfirmed"
    assert check["visible_bands"] == {"diffuse": False, "lateral": False}
    assert not list(tmp_path.rglob("*.png"))
    row = session("K01", 2, 1, "TRAIN")
    capture.validate_check(check, row, device)
    with pytest.raises(ValueError, match="comprobación"):
        capture.validate_check(check, row, SimpleNamespace(index=1, path="other-device"))
    with pytest.raises(ValueError, match="comprobación"):
        capture.validate_check({**check, "visible_bands": {"diffuse": True, "lateral": False}},
                               row, device)
    with pytest.raises(ValueError, match="comprobación"):
        wrong = {**measurement, "observed_dimensions": {"1280x720": 1700}}
        capture.validate_check({**check, "measurement": wrong}, row, device)

    manifest.write_synced(tmp_path / "plan.json", json.dumps([row]).encode())
    monkeypatch.setattr(capture, "verify_vault", lambda _: tmp_path)
    monkeypatch.setattr("sys.argv", [
        "dataset_capture", "--vault", str(tmp_path), "capture",
        "--session", row["session_id"], "--check", "R01-" + "a" * 32,
    ])
    assert capture.main() == 1
    assert not (tmp_path / "sessions").exists()


def test_vault_rejects_unmounted_location(tmp_path):
    with pytest.raises(ValueError, match="volumen montado|VeraCrypt"):
        capture.verify_vault(Path(tmp_path))


def test_guided_capture_with_controlled_frames_and_operator(tmp_path, frame, monkeypatch):
    row = session("K01", 2, 1, "TRAIN")
    device = SimpleNamespace(index=1, path="usb-device")
    config = {"backend": "DSHOW", "driver_reported": {}}
    check = {
        "round_id": "R01", "approved": True, "camera": "TMCAM 8305",
        "device_path": device.path, "index": 1, "config": config,
        "visible_bands": {"diffuse": False, "lateral": False},
        "measurement": {
            "status": "completed", "observed_dimensions": {"1920x1080": 1700},
            "failed_reads_including_warmup": 0, "delivery_fps": 29.2,
        },
    }
    fake_camera = SimpleNamespace(read=lambda: (True, frame), release=lambda: None)
    keys = iter(map(ord, "x rd q"))
    answers = iter(["CAPTURAR", "Encuadre", "Movimiento", "0,82"])
    ticks = iter([0, 5, 7, 10])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(capture, "tmcamera", lambda _: device)
    monkeypatch.setattr(capture.cv2, "VideoCapture", lambda *args: fake_camera)
    monkeypatch.setattr(capture.cv2, "destroyAllWindows", lambda: None)
    monkeypatch.setattr(capture, "configure_camera", lambda _: config)
    monkeypatch.setattr(capture, "frame_key", lambda *args: next(keys))
    monkeypatch.setattr(capture, "time", SimpleNamespace(perf_counter=lambda: next(ticks)))
    folder = tmp_path / row["session_id"]
    assert capture.capture_session(folder, row, check, 1, resume=False) == 1
    entries = list(manifest.active_records(folder / "attempts").values())
    assert [entry["status"] for entry in entries] == ["rejected", "saved", "excluded", "saved"]
    assert entries[-1]["related_attempt"] == 2
    assert entries[-1]["distance_approx_m"] == .82
