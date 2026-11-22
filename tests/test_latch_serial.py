import pytest

from scripts.latch_serial import LATCH_PONG, format_check, latch_ready, read_ack, send_decision


class _Lines:
    def __init__(self, lines):
        self.lines = [line.encode("ascii") + b"\n" for line in lines]
        self.written = []

    def write(self, payload):
        self.written.append(payload)

    def readline(self):
        return self.lines.pop(0) if self.lines else b""


def test_check_line_rejects_unknown_granted():
    assert format_check(12, "K02", "GRANTED") == "CHECK 12 K02 GRANTED"
    assert format_check("3", "UNKNOWN", "DENIED") == "CHECK 3 UNKNOWN DENIED"
    with pytest.raises(ValueError):
        format_check(1, "UNKNOWN", "GRANTED")
    with pytest.raises(ValueError):
        format_check("abc", "K01", "GRANTED")
    assert latch_ready(LATCH_PONG)
    assert not latch_ready("PONG FACENEXUS BENCH 1")


def test_ack_requires_exact_line():
    expected = "ACK 1 K01 GRANTED ACTUATED"
    assert read_ack(_Lines(["READY FACENEXUS LATCH 1", expected]), expected) == expected
    with pytest.raises(RuntimeError, match="inesperada"):
        read_ack(_Lines(["ACK 1 K01 GRANTED ACTUATED_EXTRA"]), expected)


def test_send_reports_pulse_not_position():
    connection = _Lines(["ACK 9 K02 GRANTED ACTUATED"])
    result = send_decision(connection, 9, "K02", "GRANTED")
    assert result["pulse_confirmed"] is True
    assert "physical_open" not in result
