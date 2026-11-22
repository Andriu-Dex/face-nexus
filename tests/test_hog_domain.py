import numpy as np

from scripts.hog_domain import class_means, cosine, nearest_means, vote_counts
from scripts.hog_knn import FEATURE_COUNT, PEOPLE


def test_phone_like_queries_match_the_closest_s01_mean():
    gallery = np.zeros((8, FEATURE_COUNT), np.float32)
    labels = np.array([person for person in PEOPLE for _ in range(2)])
    for index, person in enumerate(PEOPLE):
        gallery[labels == person, index] = 1
    queries = np.zeros((3, FEATURE_COUNT), np.float32)
    queries[:, 2] = 1
    rows = nearest_means(queries, class_means(gallery, labels))
    assert vote_counts(rows)["K03"] == 3
    assert cosine(queries[0], gallery[4]) == 1.0
