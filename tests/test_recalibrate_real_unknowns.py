from scripts.recalibrate_real_unknowns import longest_streak, pick


def test_longest_streak_counts_consecutive_acceptances():
    assert longest_streak([True, True, False, True, True, True, False]) == 3
    assert longest_streak([]) == 0


def test_pick_respects_both_unknown_targets():
    genuine = [("K01", "K01", 0.2, 0.5)] * 50 + [("K02", "K02", 0.3, 0.5)] * 50
    lfw = [("K01", 0.9, 0.5)] * 200
    real = [("K02", 0.35, 0.5)] * 200
    chosen = pick(genuine, lfw, real)
    assert chosen["real_calibration"]["far"] <= 0.01
    assert chosen["lfw_calibration"]["far"] <= 0.01
    assert chosen["max_distance"] < 0.35
