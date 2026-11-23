import json
from hashlib import sha256

import numpy as np
import pytest

from scripts.capture_manifest import child, write_synced
from scripts.hog_knn import FEATURE_COUNT, PEOPLE
from scripts.identity_four_other import CLASSES, assemble_phone, pick_winner, score_open_classes
from scripts.phone_demo_manifest import (
    LOT_PARTS, MANIFEST_PARTS, ROLE_SPLIT, save_manifest, session_record,
)


def test_score_separates_confusion_from_other():
    true = np.array(["K01", "K02", "K03", "OTHER", "OTHER"])
    pred = np.array(["K01", "K03", "OTHER", "K04", "OTHER"])
    row = score_open_classes(true, pred)
    assert row["enrolled_correct"] == 1
    assert row["confused_accepted"] == 1
    assert row["enrolled_as_other"] == 1
    assert row["other_as_enrolled"] == 1
    assert set(CLASSES) == set(PEOPLE) | {"OTHER"}


def test_pick_winner_does_not_reward_enrolled_confusions():
    models = {
        "messy": {
            "validation": {
                "enrolled_correct": 8,
                "confused_accepted": 4,
                "other_as_enrolled": 1,
                "classify_ms": {"median": 1.},
            }
        },
        "strict": {
            "validation": {
                "enrolled_correct": 8,
                "confused_accepted": 0,
                "other_as_enrolled": 1,
                "classify_ms": {"median": 2.},
            }
        },
    }
    assert pick_winner(models) == "strict"
    with pytest.raises(ValueError, match="inscrito"):
        pick_winner({"none": {"validation": {
            "enrolled_correct": 0, "confused_accepted": 0, "enrolled_n": 4,
            "other_as_enrolled": 0, "classify_ms": {"median": 1.},
        }}})


def _write_phone_lot(vault, person, run_name, role, encounter, marker):
    folder = child(vault, *LOT_PARTS, person, run_name)
    frames = folder / "frames"
    frames.mkdir(parents=True)
    sample = f"{person}_PHONE_0001"
    png = f"{person}-{role}-{run_name}".encode("ascii")
    write_synced(frames / f"{sample}.png", png)
    digest = sha256(png).hexdigest()
    vector = np.zeros(FEATURE_COUNT, np.float32)
    vector[0] = marker
    np.savez(folder / "hog.npz", vectors=vector.reshape(1, -1),
             labels=np.array([person], dtype=str), sample_ids=np.array([sample], dtype=str))
    records = {
        "person_id": person,
        "role": role,
        "split": ROLE_SPLIT[role],
        "encounter_id": encounter,
        "records": [{
            "sample_id": sample,
            "person_id": person,
            "reason": "usable",
            "image_sha256": digest,
        }],
    }
    write_synced(folder / "records.json", json.dumps(records).encode("utf-8"))
    return digest


def test_phone_assemble_uses_tune_and_holds_eval(tmp_path):
    sessions = []
    for role, encounter, offset in (("tune", "enc-aula-tune", 1.), ("eval", "enc-aula-eval", 20.)):
        for index, person in enumerate(PEOPLE):
            run_name = f"{person.lower()}_{role}_v1"
            digest = _write_phone_lot(
                tmp_path, person, run_name, role, encounter, offset + index)
            sessions.append(session_record(
                person, run_name, role, 0, [digest],
                sampled=1, usable=1, encounter_id=encounter,
                at="2026-11-22T00:00:00+00:00"))
    save_manifest(tmp_path.joinpath(*MANIFEST_PARTS), {
        "at_utc": "2026-11-22T00:00:00+00:00",
        "source": "phone_mjpeg",
        "revision": 1,
        "sessions": sessions,
    })
    other = np.zeros((2, FEATURE_COUNT), np.float32)
    other[:, 2] = 7.
    other_y = np.array(["OTHER", "OTHER"])
    val = np.zeros((1, FEATURE_COUNT), np.float32)
    val[0, 3] = 9.
    data = assemble_phone(
        tmp_path, other, other_y, np.array(["o1", "o2"]), np.array(["U01", "U02"]),
        val, np.array(["OTHER"]))
    train_x, train_y = data["train"]
    eval_x, eval_y = data["eval"]
    enrolled = train_x[np.isin(train_y, PEOPLE)]
    assert set(map(str, train_y[np.isin(train_y, PEOPLE)])) == set(PEOPLE)
    assert data["eval_in_train"] is False
    assert data["n_tune"] == 4
    assert train_x.shape[0] == 6
    assert {round(float(value), 1) for value in enrolled[:, 0]} == {1., 2., 3., 4.}
    assert {round(float(value), 1) for value in eval_x[:, 0]} == {20., 21., 22., 23.}
    assert not np.any(np.isin(eval_x[:, 0], enrolled[:, 0]))
    assert set(map(str, eval_y)) == set(PEOPLE)
    assert data["counts"]["eval_held_out"] == 4
