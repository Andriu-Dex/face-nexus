"""Ensayos de tiempos y fallos sin OpenCV, cámara ni imágenes personales."""

from types import SimpleNamespace

import pytest

from scripts.camera_diagnostic import measure_capture, percentile, positive


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class FakeCapture:
    def __init__(self, clock, durations, fail_at=None):
        self.clock = clock
        self.durations = iter(durations)
        self.calls = 0
        self.fail_at = fail_at

    def read(self):
        self.calls += 1
        self.clock.now += next(self.durations)
        if self.calls == self.fail_at:
            return False, None
        return True, SimpleNamespace(size=6, shape=(1080, 1920, 3))


def test_measures_deliveries_not_requested_fps():
    clock = FakeClock()
    camera = FakeCapture(clock, [.25] * 4)
    result = measure_capture(camera, 1, 0, .2, clock=clock)
    assert result["status"] == "completed"
    assert result["successful_reads"] == 4
    assert result["delivery_fps"] == 4
    assert result["observed_dimensions"] == {"1920x1080": 4}
    assert result["interval_ms_p95"] == 250
    assert result["gaps_over_threshold"] == 3


def test_read_failure_stops_without_reconnection():
    clock = FakeClock()
    camera = FakeCapture(clock, [.1] * 3, fail_at=2)
    result = measure_capture(camera, 1, 0, .25, clock=clock)
    assert result["status"] == "read_failed"
    assert result["failed_reads_including_warmup"] == 1
    assert result["successful_reads"] == 1
    assert result["delivery_fps"] is None
    assert camera.calls == 2


def test_warmup_not_counted_and_interruption_not_completed():
    clock = FakeClock()
    camera = FakeCapture(clock, [.25] * 4)
    result = measure_capture(camera, 1, .5, .25,
                             show_frame=lambda frame: clock.now < .75, clock=clock)
    assert result["status"] == "interrupted"
    assert result["successful_reads"] == 2


def test_failure_during_warmup_has_no_measurement():
    clock = FakeClock()
    result = measure_capture(FakeCapture(clock, [.1], fail_at=1),
                             1, 5, .25, clock=clock)
    assert result["successful_reads"] == 0
    assert result["measurement_elapsed_seconds"] == 0
    assert result["interval_ms_p95"] is None


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf"])
def test_duration_rejects_invalid_values(value):
    import argparse
    with pytest.raises(argparse.ArgumentTypeError):
        positive(value)


def test_percentile_empty_and_nearest_rank():
    assert percentile([], .95) is None
    assert percentile([4, 1, 3, 2], .95) == 4


def test_open_failure_releases_device_and_writes_technical_report(monkeypatch, tmp_path):
    import json
    import sys
    from scripts.camera_diagnostic import main

    released = []
    device = SimpleNamespace(isOpened=lambda: False, release=lambda: released.append(True))
    fake_cv = SimpleNamespace(__version__="fake", CAP_DSHOW=700, CAP_MSMF=1400,
                              VideoCapture=lambda index, backend: device)
    output = tmp_path / "failed.json"
    monkeypatch.setitem(sys.modules, "cv2", fake_cv)
    monkeypatch.setattr("builtins.input", lambda prompt: "TMCAM")
    monkeypatch.setattr(sys, "argv", ["diagnostic", "--camera", "2", "--no-preview",
                                    "--output", str(output)])
    assert main() == 1
    assert released == [True]
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "open_failed"
    assert report["camera_identity_verified_by_software"] is False
    assert list(tmp_path.iterdir()) == [output]


def test_cancel_does_not_import_opencv_or_open_camera(monkeypatch):
    import sys
    from scripts.camera_diagnostic import main

    monkeypatch.setitem(sys.modules, "cv2", None)
    monkeypatch.setattr("builtins.input", lambda prompt: "cancelar")
    monkeypatch.setattr(sys, "argv", ["diagnostic", "--camera", "1"])
    assert main() == 2
