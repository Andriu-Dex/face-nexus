import numpy as np

from scripts.calibrate_hog import MODELS, attempt_vote, compare_attempts, frame_vote
from scripts.hog_knn import PEOPLE


def test_attempt_uses_third_margin_of_same_identity():
    assert frame_vote(np.array([.9, .9, .2, .3])) is None
    assert frame_vote(np.array([.9, np.nan, .2, .3])) is None
    assert frame_vote(np.array([1., .5, -.2, 0.])) == ("K01", .5)
    votes = [("K01", .3), ("K02", .9), ("K01", .8), ("K01", .4)]
    assert attempt_vote(votes[:3]) is None
    assert attempt_vote(votes) == {"candidate": "K01", "margin": .3}


def test_threshold_requires_unknown_and_excludes_wrong_known_predictions():
    def attempt(participant, label, margin):
        return {"participant": participant, "status": "usable",
                "votes": {name: {"candidate": label, "margin": margin} for name in MODELS}}

    known = [attempt(person, person, .9) for person in PEOPLE]
    assert compare_attempts(known)["status"] == "insufficient_live_data"
    result = compare_attempts(known + [attempt("K02", "K01", .9), attempt("A01", "K03", .8)])
    assert result["models"]["svm"]["candidate_threshold"] > .9
    assert result["models"]["svm"]["known_correct_at_threshold"] == 0
    assert result["models"]["svm"]["accepted_unknown_before_threshold"] == 1
