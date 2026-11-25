import numpy as np

from scripts.compare_cnn_classifiers import compare, pick_threshold
from scripts.hog_knn import PEOPLE


def test_threshold_lets_through_at_most_target_unknowns():
    scores = np.linspace(0, 1, 200)
    threshold = pick_threshold(scores, target=0.01)
    assert (scores > threshold).sum() <= 2


def test_compare_separates_clusters_and_rejects_far_unknowns():
    rng = np.random.default_rng(0)
    centers = np.eye(4, 128) * 3
    def sample(count):
        vectors = np.concatenate([center + rng.normal(0, .1, (count, 128)) for center in centers])
        return vectors, np.repeat(np.array(PEOPLE), count)
    gallery, labels = sample(20)
    test, expected = sample(5)
    unknown = rng.normal(0, .1, (100, 128)) - 3
    results = compare(gallery, labels, test, expected, unknown[:50], unknown[50:])
    assert set(results) == {"SVM", "Random Forest", "k-NN", "MLP"}
    for row in results.values():
        assert row["closed_set_accuracy"] == 1.0
        assert row["open_set"]["known_confused_accepted"] == 0
        assert row["open_set"]["unknown_total"] == 50
