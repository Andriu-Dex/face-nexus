"""Rechazo abierto: distancia al ganador y holgura frente a otra identidad inscrita."""

import argparse
import json
from pathlib import Path

import numpy as np

from scripts.capture_manifest import child, utc_now, write_synced
from scripts.compare_identity_k01 import load_gallery, vote_knn
from scripts.dataset_capture import verify_vault
from scripts.evaluate_four_unknowns import other_vectors, score_unregistered
from scripts.evaluate_hog_knn import K
from scripts.hog_knn import PEOPLE, accepts_open_set, runner_up_distance
from scripts.identity_artifacts import DISTANCE_NAME, load_verified_knn
from scripts.identity_four import RUN as FOUR_RUN


TARGET_FAR = 0.01


def open_set_row(gallery, labels, query, k=K):
    winner, distance = vote_knn(gallery, labels, query, k)
    if winner not in PEOPLE or distance is None:
        return winner, distance, None
    runner = runner_up_distance(gallery, labels, query, winner)
    if runner is None:
        return winner, distance, None
    return winner, distance, runner - distance


def score_unknown_rows(rows, max_distance, min_gap):
    accepted = 0
    as_person = {person: 0 for person in PEOPLE}
    for winner, distance, gap in rows:
        if accepts_open_set(winner, distance, gap, max_distance, min_gap):
            accepted += 1
            as_person[winner] += 1
    n = len(rows)
    return {
        "n": n,
        "accepted": accepted,
        "rejected": n - accepted,
        "as_person": as_person,
        "far": accepted / n if n else None,
    }


def score_known_rows(rows, max_distance, min_gap):
    """Aciertos aceptados, confusiones aceptadas y rechazos. La etiqueta real cuenta."""
    correct = confused = rejected = 0
    for true, winner, distance, gap in rows:
        if accepts_open_set(winner, distance, gap, max_distance, min_gap):
            if winner == true:
                correct += 1
            else:
                confused += 1
        else:
            rejected += 1
    n = len(rows)
    return {
        "n": n,
        "correct_accepted": correct,
        "confused_accepted": confused,
        "rejected": rejected,
        "accepted": correct + confused,
    }


def genuine_loo_rows(gallery, labels, k=K):
    """Cada vector de TRAIN se compara con el resto. Conserva la etiqueta real."""
    rows = []
    labels = np.asarray(labels)
    for index in range(len(gallery)):
        mask = np.ones(len(gallery), bool)
        mask[index] = False
        if mask.sum() < k:
            continue
        winner, distance, gap = open_set_row(gallery[mask], labels[mask], gallery[index], k)
        rows.append((str(labels[index]), winner, distance, gap))
    return rows


def predict_open_set(gallery, labels, queries, max_distance, min_gap, k=K):
    """Etiqueta UNKNOWN si falla T o la holgura."""
    predicted = []
    for query in queries:
        winner, distance, gap = open_set_row(gallery, labels, query, k)
        if accepts_open_set(winner, distance, gap, max_distance, min_gap):
            predicted.append(winner)
        else:
            predicted.append("UNKNOWN")
    return np.array(predicted)


def unknown_rows(gallery, labels, unknown_x, k=K):
    return [open_set_row(gallery, labels, vector, k) for vector in unknown_x]


def _quantiles(values, count=24):
    values = np.asarray([item for item in values if item is not None and np.isfinite(item)], float)
    if len(values) == 0:
        return np.array([0.])
    return np.unique(np.quantile(values, np.linspace(0, 1, count)))


def pick_operating_point(genuine_rows, unknown_rows_in, target_far=TARGET_FAR):
    """FAR ≤ meta; luego más aciertos de identidad, menos confusiones, T más chico."""
    distances = [row[-2] for row in genuine_rows + unknown_rows_in]
    gaps = [row[-1] for row in genuine_rows + unknown_rows_in]
    best = None
    for max_distance in _quantiles(distances):
        for min_gap in _quantiles(gaps):
            unk = score_unknown_rows(unknown_rows_in, max_distance, min_gap)
            if unk["far"] is None or unk["far"] > target_far:
                continue
            gen = score_known_rows(genuine_rows, max_distance, min_gap)
            key = (gen["correct_accepted"], -gen["confused_accepted"], -max_distance)
            if best is None or key > best["key"]:
                best = {
                    "key": key,
                    "max_distance": float(max_distance),
                    "min_gap": float(min_gap),
                    "calibration_unknowns": unk,
                    "loo_known": gen,
                    "target_far": target_far,
                }
    if best is None:
        raise ValueError("Ningún (T, holgura) cumple la FAR de calibración.")
    del best["key"]
    return best


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--four-run", default=FOUR_RUN)
    parser.add_argument("--unknown-run", default="identity_k01_compare_v1")
    parser.add_argument("--target-far", type=float, default=TARGET_FAR)
    args = parser.parse_args()
    if not 0 <= args.target_far <= 1:
        parser.error("target-far debe estar en [0, 1].")
    root = verify_vault(args.vault)
    four = child(root, "experiments", "identity_four", args.four_run)
    out = four / "open_set.json"
    if out.exists():
        raise FileExistsError("Ese criterio abierto ya existe.")
    bundle, reason = load_verified_knn(four)
    if bundle is None:
        raise ValueError(f"Galería de cuatro no verificada: {reason}.")
    other_x, other_y = load_gallery(
        child(root, "experiments", "identity_k01", args.unknown_run, "gallery.npz"))
    unknown_x = other_vectors(other_x, other_y)
    genuines = genuine_loo_rows(bundle["vectors"], bundle["labels"])
    unknowns = unknown_rows(bundle["vectors"], bundle["labels"], unknown_x)
    chosen = pick_operating_point(genuines, unknowns, args.target_far)
    previous = bundle["max_distance"]
    old = score_unregistered(
        bundle["vectors"], bundle["labels"], unknown_x, previous)
    summary = {
        "at_utc": utc_now(),
        "formula": "accept if winner in K01-K04 and d_winner <= T and (d_other - d_winner) >= G",
        "previous_max_distance": previous,
        "previous_unknowns": old,
        "gallery_sha256": bundle["gallery_sha256"],
        "unknown_source": "LFW TRAIN of K01/OTHER; calibration only, not TEST",
        "loo_note": "LOO TRAIN counts correct_accepted vs confused_accepted. Not Downloads VALIDATION.",
        **chosen,
    }
    write_synced(out, json.dumps(summary, indent=2, allow_nan=False).encode("utf-8"))
    distance_path = four / DISTANCE_NAME
    payload = json.loads(distance_path.read_text(encoding="utf-8-sig"))
    payload["previous_max_distance"] = previous
    payload["max_distance"] = chosen["max_distance"]
    payload["min_gap"] = chosen["min_gap"]
    payload["open_set"] = True
    payload["target_far"] = args.target_far
    payload["gallery_sha256"] = bundle["gallery_sha256"]
    payload["at_utc"] = utc_now()
    distance_path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "max_distance": chosen["max_distance"],
        "min_gap": chosen["min_gap"],
        "loo_correct": chosen["loo_known"]["correct_accepted"],
        "loo_confused": chosen["loo_known"]["confused_accepted"],
        "calibration_far": chosen["calibration_unknowns"]["far"],
        "calibration_accepted": chosen["calibration_unknowns"]["accepted"],
        "previous_accepted": old["accepted"],
        "previous_n": old["n"],
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
