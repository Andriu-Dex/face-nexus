from argparse import ArgumentTypeError

import pytest

from scripts import phone_serial_bench as bench


@pytest.mark.parametrize("url", [
    "http://8.8.8.8:8080/video",
    "http://user:secret@192.168.1.20:8080/video",
    "rtsp://192.168.1.20:554/video",
])
def test_source_requires_local_http_without_credentials(url):
    with pytest.raises(ArgumentTypeError):
        bench.local_stream_url(url)


def test_interrupted_stream_reports_denied_with_matching_event(monkeypatch):
    exchanges = []

    def reply(connection, command, expected):
        exchanges.append(command)
        return expected

    monkeypatch.setattr(bench, "check_reply", reply)
    monkeypatch.setattr(bench, "load_detector", lambda models: object())
    monkeypatch.setattr(bench, "inspect_video", lambda url, model: (2, (320, 240), "STREAM_INTERRUPTED"))

    result = bench.run_trial(object(), "http://127.0.0.1/video", "models", 22)

    assert result == (2, (320, 240), "STREAM_INTERRUPTED", "ACK 22 UNKNOWN DENIED SIMULATED")
    assert exchanges == ["PING", "CHECK 22 UNKNOWN DENIED"]


def test_failed_acknowledgement_does_not_resend(monkeypatch):
    exchanges = []

    def reply(connection, command, expected):
        exchanges.append(command)
        if command.startswith("CHECK"):
            raise TimeoutError
        return expected

    monkeypatch.setattr(bench, "check_reply", reply)
    monkeypatch.setattr(bench, "load_detector", lambda models: object())
    monkeypatch.setattr(bench, "inspect_video", lambda url, model: (5, (320, 240), "NO_FACE"))

    with pytest.raises(TimeoutError):
        bench.run_trial(object(), "http://127.0.0.1/video", "models", 22)
    assert exchanges == ["PING", "CHECK 22 UNKNOWN DENIED"]
