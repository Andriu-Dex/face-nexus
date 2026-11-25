import pytest

from scripts.latch_serial import LATCH_PONG, format_check, latch_ready, read_ack, send_decision, send_servo_test


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


def test_manual_angle_checks_firmware_range_and_sends_one_move(monkeypatch):
    class Port(_Lines):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def reset_input_buffer(self):
            pass

    port = Port([LATCH_PONG, "SERVO RANGE 0 180", "SERVO ACK 45"])
    monkeypatch.setattr("serial.Serial", lambda **_kwargs: port)
    monkeypatch.setattr("scripts.latch_serial.sleep", lambda _seconds: None)
    with pytest.raises(ValueError, match="ángulo"):
        send_servo_test("COM5", "move", 181)
    assert not port.written
    assert send_servo_test("COM5", "move", 45) == "SERVO ACK 45"
    assert port.written == [b"PING\n", b"SERVO RANGE\n", b"SERVO MOVE 45\n"]
