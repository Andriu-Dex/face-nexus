import pytest

from scripts.latch_command_bench import latch_cases, require_disconnected_servo
from scripts.latch_serial import LATCH_PONG


def test_bench_requires_free_mechanism_and_latch_acks():
    with pytest.raises(ValueError, match="servo"):
        require_disconnected_servo(False)
    require_disconnected_servo(True)
    cases = dict(latch_cases())
    assert cases["PING"] == LATCH_PONG
    assert cases["CHECK 1 K01 DENIED"] == "ACK 1 K01 DENIED CLOSED"
    assert cases["CHECK 3 UNKNOWN GRANTED"] == "ERROR BAD_DECISION"
    assert cases["CHECK 4 K01 GRANTED"] == "ACK 4 K01 GRANTED ACTUATED"
