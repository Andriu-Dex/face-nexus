from scripts.access import DENIED, GRANTED
from scripts.compare_cnn_veto import veto_counts


def test_veto_counts_false_blocks_and_leaked_objects():
    granted = {"outcome": GRANTED, "reason": "authorized", "true_human": True}
    blocked = {"outcome": DENIED, "reason": "not_human", "true_human": True}
    object_granted = {"outcome": GRANTED, "reason": "authorized", "true_human": False}
    object_blocked = {"outcome": DENIED, "reason": "not_human", "true_human": False}
    row = veto_counts(
        [granted, granted, object_granted],
        [granted, blocked, object_blocked],
    )
    assert row["false_veto_of_granted"] == 1
    assert row["blocked_by_cnn"] == 2
    assert row["leaked_nonhuman"] == 0
    leaked = veto_counts([object_granted], [object_granted])
    assert leaked["leaked_nonhuman"] == 1
