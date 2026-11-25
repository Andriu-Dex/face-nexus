import numpy as np

from scripts.access import DENIED, GRANTED, decide, default_permissions
from scripts.hog_knn import FEATURE_COUNT
from scripts.identity_k01 import accept_k01, binary_vote, hog_vector, threshold_for_others, to_bgr
from scripts.compare_identity_k01 import vote_knn
from scripts.live_k01 import identify_knn, recognize_crop


def test_binary_vote_and_threshold_reject_others_labeled_k01():
    assert binary_vote(np.array([.2, .9])) == ("K01", .7)
    assert binary_vote(np.array([1., 0.]))[0] == "OTHER"
    threshold = threshold_for_others([("K01", .4), ("OTHER", .8)])
    assert threshold > .4
    assert not accept_k01("K01", .4, threshold)
    assert accept_k01("K01", threshold, threshold)


def test_hog_from_uint8_and_float_rgb():
    rgb = np.zeros((40, 40, 3), np.float32)
    rgb[:, :20, 0] = 1
    assert hog_vector(rgb) is not None
    assert to_bgr(np.full((10, 10), 1., np.float32)).shape[2] == 3


def test_not_human_denies_even_if_identity_would_match():
    row = decide(face_count=1, candidate="K01", accepted=True, permission_active=True, is_human=False)
    assert row == {"outcome": DENIED, "reason": "not_human", "identity": "UNKNOWN"}


class _Scores:
    def __init__(self, row):
        self.row = np.asarray(row, np.float32)

    def __call__(self, _x, training=False):
        return self.row[None, :]


def test_recognize_crop_grants_k01_and_denies_object(monkeypatch):
    monkeypatch.setattr("scripts.live_k01.describe_face", lambda _crop: np.ones(FEATURE_COUNT, np.float32))
    crop = np.zeros((64, 64, 3), np.uint8)

    def identify_k01(_vector):
        return "K01", True, "d=0.01"

    granted = recognize_crop(crop, _Scores([1., 0.]), identify_k01, default_permissions(),
                             trust_detector=True)
    assert granted["outcome"] == GRANTED and granted["identity"] == "K01"
    denied = recognize_crop(crop, _Scores([1., 0.]), identify_k01, default_permissions(),
                            trust_detector=False)
    assert denied["reason"] == "not_human"
    revoked = dict(default_permissions())
    revoked["K01"] = False
    held = recognize_crop(crop, _Scores([1., 0.]), identify_k01, revoked, trust_detector=True)
    assert held["outcome"] == DENIED and held["reason"] == "permission_inactive"


def test_knn_vote_follows_nearest_labelled_neighbours():
    gallery = np.array([[1., 0., 0.], [0.9, 0.1, 0.], [0., 1., 0.], [0.1, 0.9, 0.]], np.float32)
    labels = np.array(["K01", "K01", "OTHER", "OTHER"])
    label, distance = vote_knn(gallery, labels, np.array([1., 0., 0.], np.float32), k=3)
    assert label == "K01" and distance is not None
    other, _ = vote_knn(gallery, labels, np.array([0., 1., 0.], np.float32), k=3)
    assert other == "OTHER"
    identify = identify_knn(gallery, labels)
    chosen, accepted, text, _ = identify(np.array([1., 0., 0.], np.float32))
    assert chosen == "K01" and accepted and text.startswith("d=")
