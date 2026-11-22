from scripts.compare_identity_k01 import pick_winner, score_binary


def test_score_binary_counts_false_accepts_and_treats_ties_as_other():
    true = ["K01", "K01", "OTHER", "OTHER", "OTHER"]
    pred = ["K01", "OTHER", "K01", "OTHER", "AMBIGUOUS"]
    row = score_binary(true, pred)
    assert row["true_k01_pred_k01"] == 1
    assert row["false_rejects"] == 1
    assert row["false_accepts"] == 1
    assert row["true_other_pred_other"] == 2
    assert row["n_k01"] == 2 and row["n_other"] == 3


def test_pick_winner_prefers_fewer_false_accepts_then_fewer_rejects():
    models = {
        "knn": {"validation": {"k01_recall": 1., "false_accepts": 10, "false_rejects": 0,
                               "classify_ms": {"median": 0.1}}},
        "mlp": {"validation": {"k01_recall": 0., "false_accepts": 0, "false_rejects": 5,
                               "classify_ms": {"median": 0.8}}},
        "svm": {"validation": {"k01_recall": 1., "false_accepts": 2, "false_rejects": 0,
                               "classify_ms": {"median": 0.4}}},
    }
    assert pick_winner(models) == "svm"
