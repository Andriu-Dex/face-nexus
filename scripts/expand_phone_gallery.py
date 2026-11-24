"""Construye y audita una galería HOG del celular para simulación."""

import argparse
import json
from pathlib import Path

import numpy as np

from scripts.capture_manifest import child, write_synced
from scripts.capture_phone_train import sample_phone_frames
from scripts.compare_identity_k01 import write_gallery
from scripts.dataset_capture import verify_vault
from scripts.face_pipeline import load_detector
from scripts.hog_knn import PEOPLE, inspect_live_frame
from scripts.identity_artifacts import DISTANCE_NAME, load_verified_knn
from scripts.identity_k01 import load_lfw_hog
from scripts.open_set_knn import (
    genuine_loo_rows, open_set_row, pick_operating_point, score_known_rows,
    score_unknown_rows, unknown_rows,
)
from scripts.phone_demo_manifest import MANIFEST_PARTS, load_manifest, load_phase_vectors


def build_gallery(directories, detector, count):
    vectors, labels = [], []
    for person, directory in zip(PEOPLE, directories, strict=True):
        frames, _ = sample_phone_frames(directory, count)
        distinct = {}
        for frame in frames:
            result = inspect_live_frame(frame, detector)
            if result["reason"] == "usable":
                vector = result["vector"].astype(np.float32)
                distinct.setdefault(vector.tobytes(), vector)
        if len(distinct) < 4:
            raise ValueError(f"Muestras utilizables insuficientes para {person}.")
        vectors.extend(distinct.values())
        labels.extend([person] * len(distinct))
    return np.array(vectors), np.array(labels)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--run", required=True)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    parser.add_argument("--count", type=int, default=70)
    parser.add_argument("directories", nargs=len(PEOPLE), type=Path, help="PNG tune en orden K01–K04")
    args = parser.parse_args()
    vault = verify_vault(args.vault)
    folder = child(vault, "experiments", "identity_four_other", args.run)
    if folder.exists():
        raise FileExistsError(folder)
    gallery, labels = build_gallery(args.directories, load_detector(args.models), args.count)
    print("Galería preparada. Calculando calibración y validación LFW.", flush=True)
    lfw_train, lfw_validation, _, _ = load_lfw_hog()
    selected = pick_operating_point(
        genuine_loo_rows(gallery, labels), unknown_rows(gallery, labels, lfw_train))
    limits = selected["max_distance"], selected["min_gap"]
    manifest = load_manifest(child(vault, *MANIFEST_PARTS))
    eval_x, eval_y = load_phase_vectors(vault, manifest, "eval")
    rows = [(str(person), *open_set_row(gallery, labels, query))
            for query, person in zip(eval_x, eval_y, strict=True)]
    summary = {
        "gallery_counts": {person: int((labels == person).sum()) for person in PEOPLE},
        "gallery_source": "phone_video_tune",
        "samples_requested_per_person": args.count,
        **selected,
        "unknown_validation": score_unknown_rows(unknown_rows(gallery, labels, lfw_validation), *limits),
        "phone_eval_exploratory": {
            person: score_known_rows([row for row in rows if row[0] == person], *limits)
            for person in PEOPLE
        },
    }
    folder.mkdir()
    summary["gallery_sha256"] = write_gallery(folder / "gallery.npz", gallery, labels)
    payload = json.dumps(summary, indent=2, allow_nan=False).encode("utf-8")
    write_synced(folder / "summary.json", payload)
    write_synced(folder / DISTANCE_NAME, payload)
    bundle, reason = load_verified_knn(folder)
    if bundle is None:
        raise RuntimeError(f"El candidato no pasó la verificación: {reason}")
    print(payload.decode("utf-8"))


if __name__ == "__main__":
    main()
