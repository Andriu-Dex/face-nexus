from scripts.adapt_human_cnn import overlap_fraction


def test_overlap_is_zero_when_boxes_are_apart():
    assert overlap_fraction((0, 0, 10, 10), (20, 20, 30, 30)) == 0
    assert overlap_fraction((0, 0, 10, 10), (0, 0, 10, 10)) == 1
    assert 0.2 < overlap_fraction((0, 0, 10, 10), (5, 0, 15, 10)) < 0.6
