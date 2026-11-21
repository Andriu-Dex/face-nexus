"""Entrena la referencia HOG + k-NN en S01 y la evalúa en la ronda R01."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from time import perf_counter

import cv2
import numpy as np
import sklearn
from sklearn.metrics import classification_report, confusion_matrix

from scripts.capture_manifest import child, utc_now, write_synced
from scripts.dataset_capture import verify_vault
from scripts.face_pipeline import describe, load_detector, verified_model_path
from scripts.hog_knn import FEATURE_COUNT, PEOPLE, face_features, knn_candidate


K = 3
MANIFEST_FOLDER = ("experiments", "hog_s01_r01")


def validate_manifest(manifest):
    ids = set()
    digests = {}
    for split, encounter in (("train", "S01"), ("validation", "S02")):
        rows = manifest[split]
        if Counter(row["person_id"] for row in rows) != Counter({person: 20 for person in PEOPLE}):
            raise ValueError("Cada lote debe conservar 20 fotogramas por identidad.")
        for row in rows:
            session = f'{row["person_id"]}_{encounter}'
            sample = row["sample_id"]
            digest = row["image_sha256"]
            if row["session_id"] != session or not sample.startswith(session + "_") or sample in ids:
                raise ValueError("Sesión o identificador inválido o repetido.")
            if digests.setdefault(digest, split) != split:
                raise ValueError("Hay imágenes idénticas entre TRAIN y VALIDATION.")
            ids.add(sample)


def extract(root, rows, detector):
    vectors, labels, ids, records, timings = [], [], [], [], []
    for row in rows:
        image = child(root, *Path(row["image"]).parts).read_bytes()
        if sha256(image).hexdigest() != row["image_sha256"]:
            raise ValueError("El hash de un fotograma difiere del manifiesto.")
        frame = cv2.imdecode(np.frombuffer(image, dtype=np.uint8), cv2.IMREAD_COLOR)
        started = perf_counter()
        faces = face_features(frame, detector, require_single=True) if frame is not None else []
        timings.append((perf_counter() - started) * 1000)
        status = "ok" if len(faces) == 1 else "no_unique_usable_face"
        if frame is None:
            status = "invalid_image"
        records.append({"sample_id": row["sample_id"], "person_id": row["person_id"], "status": status})
        if status == "ok":
            vectors.append(faces[0][1])
            labels.append(row["person_id"])
            ids.append(row["sample_id"])
    if set(labels) != set(PEOPLE):
        raise ValueError("El lote usable debe conservar las cuatro identidades.")
    return {
        "vectors": np.asarray(vectors, dtype=np.float32),
        "labels": np.asarray(labels),
        "sample_ids": np.asarray(ids),
    }, records, timings


def evaluate(train, dataset, records, extraction_ms):
    predictions, timings = [], []
    for vector in dataset["vectors"]:
        started = perf_counter()
        candidate, _ = knn_candidate(train["vectors"], train["labels"], vector, k=K)
        timings.append((perf_counter() - started) * 1000)
        predictions.append(candidate or "AMBIGUOUS")

    scores = score_predictions(dataset["labels"], predictions, records)
    scores.update(extract_ms=describe(extraction_ms), classify_ms=describe(timings))
    return scores


def score_predictions(labels, predictions, records):
    predictions = np.asarray(predictions)
    correct = int(np.sum(labels == predictions))
    metrics = classification_report(labels, predictions, labels=PEOPLE, output_dict=True, zero_division=0)
    return {
        "frames_total": len(records),
        "usable": len(labels),
        "correct": correct,
        "candidate_accuracy": correct / len(labels),
        "frame_accuracy": correct / len(records),
        "macro_f1": metrics["macro avg"]["f1-score"],
        "by_identity": {person: metrics[person] for person in PEOPLE},
        "candidate_confusion_rows_actual": confusion_matrix(labels, predictions, labels=PEOPLE).tolist(),
        "ties_by_identity": {person: int(np.sum((labels == person) & (predictions == "AMBIGUOUS")))
                             for person in PEOPLE},
        "unusable_by_identity": dict(Counter(row["person_id"] for row in records if row["status"] != "ok")),
    }


def run(vault, models, run_name):
    root = verify_vault(vault)
    folder = child(root, *MANIFEST_FOLDER)
    destination = child(folder, run_name)
    if destination.exists():
        raise FileExistsError("El ensayo ya existe. Usa un nombre nuevo para repetirlo.")
    manifest_bytes = child(folder, "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
    validate_manifest(manifest)
    cv2.setNumThreads(1)
    detector = load_detector(models)
    # El calentamiento no usa muestras ni cuenta en los tiempos.
    face_features(np.zeros((320, 320, 3), np.uint8), detector, require_single=True)
    train, train_records, train_timings = extract(root, manifest["train"], detector)
    validation, validation_records, validation_timings = extract(root, manifest["validation"], detector)
    summary = {
        "at_utc": utc_now(),
        "manifest_sha256": sha256(manifest_bytes).hexdigest(),
        "yunet_sha256": sha256(verified_model_path(models, "yunet").read_bytes()).hexdigest(),
        "versions": {"opencv": cv2.__version__, "numpy": np.__version__, "sklearn": sklearn.__version__},
        "hog_dimension": FEATURE_COUNT,
        "k": K,
        "people_order": PEOPLE,
        "rejection_threshold": None,
        "train": evaluate(train, train, train_records, train_timings),
        "validation": evaluate(train, validation, validation_records, validation_timings),
    }
    with TemporaryDirectory(prefix=".hog-", dir=folder) as temporary:
        staging = Path(temporary) / "run"
        staging.mkdir()
        np.savez_compressed(staging / "train.npz", **train)
        np.savez_compressed(staging / "validation.npz", **validation)
        for filename, content in (("summary.json", summary),
                                  ("records.json", {"train": train_records, "validation": validation_records})):
            write_synced(staging / filename, json.dumps(content, indent=2, allow_nan=False).encode("utf-8"))
        staging.rename(destination)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    parser.add_argument("--run-name", default="knn_baseline_v1")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run_name):
        parser.error("El nombre del ensayo debe ser un nombre de carpeta simple.")
    try:
        summary = run(args.vault, args.models, args.run_name)
    except (OSError, ValueError, KeyError, cv2.error):
        parser.exit(1, "Ensayo detenido. Comprueba el volumen, manifiesto, pesos y nombre del ensayo.\n")
    for split in ("train", "validation"):
        print(split.upper(), json.dumps(summary[split], allow_nan=False))


if __name__ == "__main__":
    main()
