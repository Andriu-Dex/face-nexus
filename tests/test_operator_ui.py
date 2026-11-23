import json
from pathlib import Path
import tkinter as tk

import cv2
import numpy as np
import pytest

from scripts.hog_knn import PEOPLE
from time import monotonic, sleep

from scripts.operator_ui import (
    OperatorApp, decision_view, display_person, launch_preflight, load_camera_config,
    load_identity_labels, parse_camera_url, save_camera_config, technical_lines,
)


def fake_recognize(outcome="DENIED", reason="no_face", identity="UNKNOWN"):
    def recognize(frame, permissions):
        return {
            "outcome": outcome,
            "reason": reason,
            "identity": identity,
            "event_id": "e1",
            "regions": [],
            "permissions": permissions,
        }
    return recognize


def test_display_person_shows_code_and_private_label():
    assert display_person("K01", {}) == "K01"
    assert display_person("K01", {"K01": "Alpha"}) == "K01 · Alpha"
    assert display_person("UNKNOWN", {"K01": "Alpha"}) == "Desconocido"


def test_load_identity_labels_ignores_unknown_keys(tmp_path):
    folder = tmp_path / "private"
    folder.mkdir()
    (folder / "identity_labels.json").write_text(
        json.dumps({"K01": "Alpha", "extra": "skip", "K02": "  "}), encoding="utf-8")
    labels = load_identity_labels(tmp_path)
    assert labels == {"K01": "Alpha"}
    assert load_identity_labels(tmp_path / "missing", fallback=None) == {}
    mapping = tmp_path / "map.json"
    mapping.write_text(json.dumps({"Alpha": "K01"}), encoding="utf-8")
    assert load_identity_labels(tmp_path / "missing", fallback=mapping) == {"K01": "Alpha"}


def test_decision_view_uses_text_and_color():
    granted = decision_view("GRANTED", "authorized", "K01", {"K01": "Alpha"})
    denied = decision_view("DENIED", "unknown_identity", "UNKNOWN", {})
    wait = decision_view(None, None, None, {})
    lost = decision_view("SIGNAL_LOST", "camera_signal_lost", "K01", {"K01": "Alpha"})
    assert granted["title"] == "Autorizado" and "Alpha" in granted["identity"]
    assert denied["title"] == "Denegado" and denied["tone"] != granted["tone"]
    assert wait["title"] == "Espera"
    assert lost["title"] == "Señal perdida" and lost["identity"] == "—"
    unseen = decision_view("DENIED", "unknown_identity", "UNKNOWN", {}, face_seen=False)
    seen = decision_view("DENIED", "unknown_identity", "UNKNOWN", {}, face_seen=True)
    assert "Rostro detectado" in seen["detail"]
    assert "Rostro detectado" not in unseen["detail"]


def test_parse_camera_url_rejects_public_or_empty():
    with pytest.raises(ValueError, match="IP local"):
        parse_camera_url("")
    with pytest.raises(ValueError, match="IP Webcam|IP local"):
        parse_camera_url("https://example.com/video")
    assert parse_camera_url("http://192.168.1.20:8080/video").startswith("http://192.168.1.")
    built = parse_camera_url("192.168.1.20", "8080")
    assert built == "http://192.168.1.20:8080/video"
    assert parse_camera_url("192.168.1.20:8080") == "http://192.168.1.20:8080/video"
    assert parse_camera_url("http://192.168.1.20:8080") == "http://192.168.1.20:8080/video"
    with pytest.raises(ValueError, match="puerto de cámara"):
        parse_camera_url("192.168.1.20", "abc")


def test_camera_config_keeps_full_url(tmp_path):
    path = tmp_path / "cam.json"
    url = parse_camera_url("http://192.168.1.20:8080/video")
    assert save_camera_config(url, "192.168.1.20", "8080", 90, path) is True
    loaded = load_camera_config(path)
    assert loaded["url"] == url
    assert loaded["rotation"] == 90
    restored = parse_camera_url(loaded["url"])
    assert restored == url
    not_dir = tmp_path / "not-a-dir"
    not_dir.write_text("x", encoding="utf-8")
    assert save_camera_config(url, "192.168.1.20", "8080", 0, not_dir / "cam.json") is False


def test_launch_preflight_reports_venv_and_vault(tmp_path):
    ok, message = launch_preflight(tmp_path, tmp_path / "no-vault")
    assert ok is False and "entorno virtual" in message
    python = tmp_path / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_text("x", encoding="utf-8")
    ok, message = launch_preflight(tmp_path, tmp_path / "no-vault")
    assert ok is False and "VeraCrypt" in message
    vault = tmp_path / "vault"
    vault.mkdir()
    ok, message = launch_preflight(tmp_path, vault)
    assert ok is True and message.endswith("python.exe")


def test_launcher_script_quotes_python_and_vault():
    text = Path("FaceNexus.cmd").read_text(encoding="utf-8")
    assert '"%PY%"' in text
    assert '"%VAULT%"' in text
    assert "scripts.operator_ui" in text
    assert "--port" not in text
    assert r"V:\FaceNexus" in text


@pytest.fixture
def app(tmp_path):
    ui = OperatorApp(
        fake_recognize(), labels={"K01": "Alpha"}, config_path=tmp_path / "cam.json")
    ui.window.withdraw()
    ui.window.update_idletasks()
    yield ui
    ui.window.destroy()


def _texts(widget):
    found = []
    try:
        found.append(widget.cget("text"))
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        found.extend(_texts(child))
    return [item for item in found if item]


def test_initial_layout_placeholder_and_simulation_badge(app):
    app.window.geometry("1366x768")
    app.window.update_idletasks()
    labels = _texts(app.window)
    assert app.decision_title.cget("text") == "Espera"
    assert "FaceNexus" in labels and "Simulación" in labels
    hint = app.viewer.find_withtag("hint")
    assert hint
    assert "Abre una imagen" in app.viewer.itemcget(hint[0], "text")
    assert app.cam_btn.cget("text") == "Cámara"
    assert app.rearm_btn.cget("state") == "disabled"
    assert "simulación" in app.hw_lbl.cget("text").lower()
    assert "K01 · Alpha" in labels
    assert app.window.minsize()[0] >= 1100
    assert app.window.minsize()[1] >= 640


def test_apply_image_and_permission_toggle(tmp_path):
    granted = OperatorApp(
        fake_recognize("GRANTED", "authorized", "K01"), labels={"K01": "Alpha"},
        config_path=tmp_path / "cam.json")
    granted.window.withdraw()
    granted.window.update_idletasks()
    frame = np.zeros((120, 160, 3), np.uint8)
    cv2.rectangle(frame, (10, 10), (80, 80), (40, 180, 40), -1)
    image = tmp_path / "face.png"
    cv2.imwrite(str(image), frame)
    scene = granted.apply_path(image)
    granted.window.update_idletasks()
    assert scene["outcome"] == "GRANTED"
    assert granted.decision_title.cget("text") == "Autorizado"
    assert "K01 · Alpha" in granted.identity_lbl.cget("text")
    assert granted.log.size() == 1
    granted.perm_vars["K01"].set(False)
    granted._sync_permissions()
    assert granted.permissions["K01"] is False
    folder = tmp_path / "lote"
    folder.mkdir()
    cv2.imwrite(str(folder / "a.png"), frame)
    granted.window.destroy()
    denied_app = OperatorApp(
        fake_recognize("DENIED", "unknown_identity", "UNKNOWN"),
        config_path=tmp_path / "cam2.json")
    denied_app.window.withdraw()
    denied_app.window.update_idletasks()
    granted_n, denied_n = denied_app.apply_folder(folder)
    assert granted_n == 0 and denied_n == 1
    denied_app.window.destroy()


def test_inaccessible_camera_without_url(app, monkeypatch):
    shown = []
    monkeypatch.setattr(
        "scripts.operator_ui.messagebox.showinfo",
        lambda *args, **kwargs: shown.append(args))
    app.url = ""
    app._start_camera()
    assert app.capture is None
    assert shown and "Cámara" in shown[0]
    assert "IP" in app.hint_lbl.cget("text") or "URL" in app.hint_lbl.cget("text")


class ScriptedCapture:
    def __init__(self, frames):
        self.frames = list(frames)

    def read(self):
        if not self.frames:
            return False, None
        frame = self.frames.pop(0)
        if frame is None:
            return False, None
        return True, frame


def _blank():
    return np.zeros((48, 64, 3), np.uint8)


def test_camera_fault_after_granted_clears_authorization(tmp_path):
    app = OperatorApp(
        fake_recognize("GRANTED", "authorized", "K01"), config_path=tmp_path / "cam.json")
    app.window.withdraw()
    app.window.update_idletasks()
    app.capture = ScriptedCapture([_blank()])
    app._ingest_camera()
    assert app.decision_title.cget("text") == "Autorizado"
    app.gate.can_send = False
    app._refresh_rearm()
    app.capture = ScriptedCapture([None])
    app._ingest_camera()
    assert app.decision_title.cget("text") == "Señal perdida"
    assert app.gate.can_send is False
    assert app.rearm_btn.cget("state") == "normal"
    assert app.viewer.find_withtag("stale")
    app._core = fake_recognize("GRANTED", "authorized", "K01")
    app.capture = ScriptedCapture([_blank()])
    app._ingest_camera()
    assert app.decision_title.cget("text") == "Autorizado"
    assert not app.viewer.find_withtag("stale")
    app.window.destroy()


def test_live_camera_does_not_replace_open_file(tmp_path):
    app = OperatorApp(
        fake_recognize("GRANTED", "authorized", "K01"), labels={"K01": "Alpha"},
        config_path=tmp_path / "cam.json")
    app.window.withdraw()
    app.window.update_idletasks()
    image = tmp_path / "face.png"
    cv2.imwrite(str(image), _blank())
    app.apply_path(image)
    assert app.hold_file is True
    assert app.decision_title.cget("text") == "Autorizado"
    app._core = fake_recognize("DENIED", "unknown_identity", "UNKNOWN")
    app.capture = ScriptedCapture([_blank(), None])
    app._ingest_camera()
    assert app.decision_title.cget("text") == "Autorizado"
    assert "K01 · Alpha" in app.identity_lbl.cget("text")
    app._ingest_camera()
    assert app.decision_title.cget("text") == "Autorizado"
    app.hold_file = False
    app._ingest_camera()
    app.window.destroy()


def test_cmd_from_other_directory(tmp_path):
    cmd = Path("FaceNexus.cmd").read_text(encoding="utf-8")
    assert r"set " in cmd and "ROOT=%~dp0" in cmd
    assert "cd /d" in cmd


def test_history_groups_repeated_camera_frames_then_signal_lost(tmp_path):
    app = OperatorApp(
        fake_recognize("DENIED", "unknown_identity", "UNKNOWN"),
        config_path=tmp_path / "cam.json")
    app.window.withdraw()
    app.window.update_idletasks()
    app.capture = ScriptedCapture([_blank(), _blank(), _blank(), None])
    app._ingest_camera()
    app._ingest_camera()
    app._ingest_camera()
    assert app.log.size() == 1
    assert "×3" in app.log.get(0)
    app._ingest_camera()
    assert app.decision_title.cget("text") == "Señal perdida"
    assert app.log.size() == 2
    app._stop_camera()
    assert app.capture is None
    assert app.stop_btn.cget("state") == "disabled"
    app.window.destroy()


def test_rejected_face_shows_unconfirmed_identity_and_diagnostic(tmp_path):
    def recognize(frame, permissions):
        return {
            "outcome": "DENIED",
            "reason": "unknown_identity",
            "identity": "UNKNOWN",
            "event_id": "e1",
            "permissions": permissions,
            "regions": [{
                "outcome": "DENIED",
                "reason": "unknown_identity",
                "identity": "UNKNOWN",
                "nearest": "K01",
                "score_text": "d=0.612 T=0.530 G=0.057 g=0.020",
                "model": "knn",
                "box": [1, 1, 20, 20],
            }],
        }

    app = OperatorApp(recognize, labels={"K01": "Alpha"}, config_path=tmp_path / "cam.json")
    app.window.withdraw()
    app.window.update_idletasks()
    app._apply(_blank(), source="file")
    assert "Rostro detectado" in app.detail_lbl.cget("text")
    assert app.identity_lbl.cget("text").endswith("Desconocido")
    app.tech_var.set(True)
    app._refresh_tech()
    text = app.tech_lbl.cget("text")
    assert "K01" in text and "d=0.612" in text and "T=0.530" in text
    assert "Desconocido" in text
    assert "Autorizado" not in app.decision_title.cget("text")
    app.window.destroy()


def test_stop_after_granted_invalidates_camera_decision(tmp_path):
    app = OperatorApp(
        fake_recognize("GRANTED", "authorized", "K01"), config_path=tmp_path / "cam.json")
    app.window.withdraw()
    app.window.update_idletasks()
    app.capture = ScriptedCapture([_blank()])
    app._ingest_camera()
    assert app.decision_title.cget("text") == "Autorizado"
    app._stop_camera()
    assert app.decision_title.cget("text") == "Señal perdida"
    assert app.capture is None
    app.window.destroy()


def test_file_prediction_survives_signal_lost(tmp_path):
    app = OperatorApp(
        fake_recognize("GRANTED", "authorized", "K01"), labels={"K01": "Alpha"},
        config_path=tmp_path / "cam.json")
    app.window.withdraw()
    app.window.update_idletasks()
    image = tmp_path / "face.png"
    cv2.imwrite(str(image), _blank())
    app.apply_path(image)
    app.capture = ScriptedCapture([None])
    app._ingest_camera()
    assert app.decision_title.cget("text") == "Autorizado"
    assert app.viewer.find_withtag("file")
    assert app.cam_state == "lost"
    app.window.destroy()


class RepeatCapture:
    def __init__(self, frame, delay=0):
        self.frame = frame
        self.delay = delay
        self.reads = 0

    def read(self):
        self.reads += 1
        if self.delay:
            sleep(self.delay)
        return True, self.frame.copy()

    def release(self):
        return None


def test_view_keeps_updating_with_slow_inference(tmp_path):
    def slow(frame, permissions):
        sleep(0.12)
        return fake_recognize()(frame, permissions)

    opened = []

    def open_capture(url):
        opened.append(url)
        sleep(0.05)
        return RepeatCapture(_blank())

    app = OperatorApp(
        slow, config_path=tmp_path / "cam.json", open_capture=open_capture)
    app.window.withdraw()
    app.url = "http://192.168.1.20:8080/video"
    app._start_camera()
    assert app.cam_state == "connecting"
    assert app.stop_btn.cget("state") == "normal"
    deadline = monotonic() + 2.0
    paints = 0
    while monotonic() < deadline:
        app._drain_ui()
        app._tick_view()
        app.window.update()
        if app._last_bgr is not None:
            paints += 1
        if app.metrics["view_fps"] >= 5 and app._shown_seq >= 1:
            break
        sleep(0.02)
    dropped = app._preview_slot.dropped
    app._stop_camera()
    app.window.update()
    assert paints >= 3
    assert app.decision_title.cget("text") == "Señal perdida"
    assert dropped >= 0
    app.window.destroy()


def _result(seq, gen, frame, scene, captured_at):
    return {
        "seq": seq,
        "gen": gen,
        "scene": scene,
        "infer_ms": 12.0,
        "captured_at": captured_at,
        "size": frame.shape[:2],
    }


def _granted_scene():
    return {
        "outcome": "GRANTED",
        "reason": "authorized",
        "identity": "K01",
        "event_id": "e2",
        "regions": [{
            "outcome": "GRANTED",
            "reason": "authorized",
            "identity": "K01",
            "box": [4, 4, 40, 40],
        }],
    }


def test_fresh_result_publishes_when_view_has_moved_ahead(tmp_path):
    app = OperatorApp(
        fake_recognize("GRANTED", "authorized", "K01"), config_path=tmp_path / "cam.json")
    app.window.withdraw()
    app.window.update_idletasks()
    frame = _blank()
    now = monotonic()
    app._cam_gen = 2
    app._preview_slot.put({"kind": "frame", "seq": 8, "bgr": frame, "at": now})
    app._result_slot.put(_result(3, 2, frame, _granted_scene(), now))
    app._tick_view()
    assert app.decision_title.cget("text") == "Autorizado"
    assert app._published_seq == 3
    assert app._view_seq == 8
    assert app.viewer.find_withtag("box")
    app._preview_slot.put({"kind": "frame", "seq": 9, "bgr": frame, "at": now})
    app._tick_view()
    assert app.viewer.find_withtag("box")
    empty = {
        "outcome": "DENIED", "reason": "no_face", "identity": "UNKNOWN",
        "event_id": "e3", "regions": [],
    }
    app._result_slot.put(_result(4, 2, frame, empty, monotonic()))
    app._tick_view()
    assert not app.viewer.find_withtag("box")
    app.window.destroy()


def test_overlay_expires_and_stop_discards_it(tmp_path):
    app = OperatorApp(
        fake_recognize("GRANTED", "authorized", "K01"), config_path=tmp_path / "cam.json")
    app.window.withdraw()
    app.window.update_idletasks()
    frame = _blank()
    now = monotonic()
    app._cam_gen = 1
    app._preview_slot.put({"kind": "frame", "seq": 1, "bgr": frame, "at": now})
    app._result_slot.put(_result(1, 1, frame, _granted_scene(), now))
    app._tick_view()
    assert app.viewer.find_withtag("box")
    fps_before = app.metrics["view_fps"]
    app._tick_view()
    assert app.metrics["view_fps"] == fps_before
    app._overlay["until"] = monotonic() - 0.01
    app._tick_view()
    assert not app.viewer.find_withtag("box")
    app._published_seq = 0
    app._result_slot.put(_result(2, 1, frame, _granted_scene(), monotonic()))
    app._preview_slot.put({"kind": "frame", "seq": 2, "bgr": frame, "at": monotonic()})
    app._tick_view()
    assert app.viewer.find_withtag("box")
    app._stop_camera()
    assert app._overlay is None
    assert not app.viewer.find_withtag("box")
    app.window.destroy()


def test_stale_result_is_not_authorized(tmp_path):
    app = OperatorApp(
        fake_recognize("GRANTED", "authorized", "K01"), config_path=tmp_path / "cam.json")
    app.window.withdraw()
    app.window.update_idletasks()
    frame = _blank()
    app._cam_gen = 1
    app._preview_slot.put({"kind": "frame", "seq": 4, "bgr": frame, "at": monotonic()})
    app._result_slot.put(_result(1, 1, frame, _granted_scene(), monotonic() - 5))
    app._tick_view()
    assert app.decision_title.cget("text") != "Autorizado"
    assert app._published_seq == 1
    app.window.destroy()


def test_technical_lines_keep_access_unknown():
    scene = {
        "outcome": "DENIED",
        "reason": "unknown_identity",
        "identity": "UNKNOWN",
        "regions": [{"nearest": "K01", "score_text": "d=0.80 T=0.53", "model": "knn"}],
    }
    text = technical_lines(scene, {"K01": "Alpha"})
    assert "Candidato diagnóstico" in text
    assert "Identidad de acceso: Desconocido" in text
