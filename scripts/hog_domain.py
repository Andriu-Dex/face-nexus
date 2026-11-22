"""Compara HOG del celular con las medias de S01. No reentrena."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from scripts.calibrate_hog import MODELS, frame_vote, load_saved_models
from scripts.capture_manifest import child, utc_now, write_synced
from scripts.compare_hog_models import read_split
from scripts.dataset_capture import verify_vault
from scripts.evaluate_hog_knn import MANIFEST_FOLDER, validate_manifest
from scripts.hog_knn import FEATURE_COUNT, PEOPLE


def cosine(left, right):
    denom = float(np.linalg.norm(left) * np.linalg.norm(right))
    return float(np.dot(left, right) / denom) if denom > 0 and np.isfinite(denom) else None


def class_means(vectors, labels):
    means = {}
    for person in PEOPLE:
        subset = vectors[labels == person]
        if len(subset) == 0:
            raise ValueError(f"S01 no tiene vectores de {person}.")
        means[person] = subset.mean(axis=0)
    return means


def nearest_means(queries, means):
    rows = []
    for vector in queries:
        scores = {person: cosine(vector, means[person]) for person in PEOPLE}
        nearest = max(PEOPLE, key=lambda person: scores[person] if scores[person] is not None else -2)
        rows.append({"nearest": nearest, "cosine": scores})
    return rows


def vote_counts(rows):
    counts = {person: 0 for person in PEOPLE}
    for row in rows:
        counts[row["nearest"]] += 1
    return counts


def describe_phone(npz_path):
    with np.load(npz_path, allow_pickle=False) as file:
        vectors, labels, ids = file["vectors"], file["labels"], file["sample_ids"]
    if (vectors.ndim != 2 or vectors.shape[1] != FEATURE_COUNT or not np.isfinite(vectors).all()
            or len(labels) != len(vectors) or len(ids) != len(vectors)):
        raise ValueError("El lote del celular no contiene vectores HOG válidos.")
    return vectors, labels, ids


def report_phone_against_s01(phone_vectors, gallery, gallery_labels, models=None):
    means = class_means(gallery, gallery_labels)
    geometry = nearest_means(phone_vectors, means)
    summary = {
        "n_phone": len(phone_vectors),
        "nearest_s01_mean": vote_counts(geometry),
        "median_cosine_to_s01": {
            person: float(np.median([row["cosine"][person] for row in geometry])) for person in PEOPLE
        },
    }
    if models:
        summary["frozen_models"] = {}
        for name, model in models.items():
            votes = []
            for vector in phone_vectors:
                scores = np.asarray(model(vector[None, :], training=False), dtype=np.float64)[0]
                result = frame_vote(scores)
                votes.append(result[0] if result else "none")
            labels, counts = np.unique(votes, return_counts=True)
            summary["frozen_models"][name] = {str(label): int(count)
                                              for label, count in zip(labels, counts)}
    return summary, geometry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--phone", required=True, help="Ruta relativa al volumen, por ejemplo "
                        "experiments/hog_phone_adapt/K01/k01_phone_v3/hog.npz")
    args = parser.parse_args()
    root = verify_vault(args.vault)
    folder = child(root, *MANIFEST_FOLDER)
    baseline = child(folder, "knn_baseline_v1")
    manifest = json.loads(child(folder, "manifest.json").read_bytes().decode("utf-8-sig"))
    validate_manifest(manifest)
    records = json.loads(child(baseline, "records.json").read_text(encoding="utf-8-sig"))
    gallery, labels = read_split(baseline, "train", records["train"], manifest["train"])
    phone_path = child(root, *Path(args.phone).parts)
    phone_vectors, phone_labels, _ids = describe_phone(phone_path)
    models, hashes = load_saved_models(child(folder, "hog_comparison_v1"))
    summary, geometry = report_phone_against_s01(phone_vectors, gallery, labels, models)
    summary.update({
        "at_utc": utc_now(),
        "phone_labels": sorted(set(map(str, phone_labels.tolist()))),
        "s01_sha256": sha256(child(baseline, "train.npz").read_bytes()).hexdigest(),
        "model_hashes": hashes,
    })
    out = child(phone_path.parent, "domain_vs_s01.json")
    write_synced(out, json.dumps({"summary": summary, "per_frame_nearest": [
        row["nearest"] for row in geometry
    ]}, indent=2, allow_nan=False).encode("utf-8"))
    print(json.dumps(summary, indent=2, allow_nan=False))
    print(f"Informe privado: {out}")


if __name__ == "__main__":
    main()
