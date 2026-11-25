import numpy as np

from scripts.hog_knn import fuse_vectors


def test_fused_distance_is_weighted_sum_of_squared_distances():
    rng = np.random.default_rng(1)
    a_cnn, b_cnn, a_sface, b_sface = (v / np.linalg.norm(v) for v in rng.normal(size=(4, 128)))
    weight = 0.75
    a, b = fuse_vectors(a_cnn, a_sface, weight), fuse_vectors(b_cnn, b_sface, weight)
    assert a.shape == (256,)
    assert np.isclose(np.linalg.norm(a), 1)
    expected = weight * np.sum((a_cnn - b_cnn) ** 2) + (1 - weight) * np.sum((a_sface - b_sface) ** 2)
    assert np.isclose(np.sum((a - b) ** 2), expected)
