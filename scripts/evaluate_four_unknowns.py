"""Mide cuántos rostros no inscritos pasa la galería de cuatro con T."""

import argparse
import json
from pathlib import Path

import numpy as np

from scripts.capture_manifest import child, utc_now, write_synced
from scripts.compare_identity_k01 import load_gallery
from scripts.dataset_capture import verify_vault
from scripts.hog_knn import PEOPLE
from scripts.identity_artifacts import load_verified_knn
from scripts.identity_four import RUN as FOUR_RUN
from scripts.identity_four import apply_threshold


def other_vectors(vectors, labels):
    """HOG etiquetados OTHER: humanos que nunca fueron K01–K04."""
    mask = np.asarray(labels).astype(str) == "OTHER"
    if not mask.any():
        raise ValueError("No hay vectores OTHER en esa galería.")
    return np.asarray(vectors, np.float32)[mask]


def score_unregistered(gallery, labels, unknown_x, threshold):
    """Aceptación indebida: un extraño queda como K01–K04 bajo T."""
    predicted = apply_threshold(gallery, labels, unknown_x, threshold)
    accepted = np.isin(predicted, PEOPLE)
    return {
        "n": int(len(unknown_x)),
        "accepted": int(accepted.sum()),
        "rejected": int((~accepted).sum()),
        "as_person": {person: int((predicted == person).sum()) for person in PEOPLE},
        "threshold": float(threshold),
        "task": "four_identities_vs_unregistered",
        "not_test": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--four-run", default=FOUR_RUN)
    parser.add_argument("--unknown-run", default="identity_k01_compare_v1",
                        help="Galería K01/OTHER; se usan solo las filas OTHER.")
    args = parser.parse_args()
    root = verify_vault(args.vault)
    four = child(root, "experiments", "identity_four", args.four_run)
    unknown_path = child(root, "experiments", "identity_k01", args.unknown_run, "gallery.npz")
    out = four / "unregistered.json"
    if out.exists():
        raise FileExistsError("Ese ensayo de extraños ya existe.")
    bundle, reason = load_verified_knn(four)
    if bundle is None:
        raise ValueError(f"Galería de cuatro no verificada: {reason}.")
    other_x, other_y = load_gallery(unknown_path)
    unknown_x = other_vectors(other_x, other_y)
    row = score_unregistered(
        bundle["vectors"], bundle["labels"], unknown_x, bundle["max_distance"])
    row["at_utc"] = utc_now()
    row["four_run"] = args.four_run
    row["unknown_run"] = args.unknown_run
    row["unknown_source"] = "LFW TRAIN of K01/OTHER; not enrolled as K01-K04"
    row["gallery_sha256"] = bundle["gallery_sha256"]
    write_synced(out, json.dumps(row, indent=2, allow_nan=False).encode("utf-8"))
    print(json.dumps({key: row[key] for key in ("n", "accepted", "rejected", "as_person",
                                                "threshold", "gallery_sha256")},
                     indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
