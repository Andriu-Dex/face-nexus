"""Galería HOG de cuatro identidades. TRAIN y VALIDATION son encuentros distintos."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

from scripts.capture_manifest import child, utc_now, write_synced
from scripts.compare_identity_k01 import vote_knn, write_gallery
from scripts.dataset_capture import verify_vault
from scripts.evaluate_hog_knn import K
from scripts.face_pipeline import load_detector
from scripts.hog_knn import PEOPLE, detect_boxes, describe_face
from scripts.identity_artifacts import DISTANCE_NAME, GALLERY_NAME
from scripts.identity_k01 import PHONE, PHONE_HOLD
from scripts.import_frames import natural_key, spread_indices


DATA_ROOT = Path(r"C:\Downloads\FaceNexus\data")
TRAIN_COUNT = 16
VAL_COUNT = 12
SLACK = 1.1
RUN = "identity_four_v2"


def sessions_from_record(payload):
    """K01–K04 con carpetas de TRAIN y VALIDATION. No publicar los nombres."""
    nested = payload.get("sessions", payload)
    sessions = {}
    for person in PEOPLE:
        row = nested.get(person) if isinstance(nested, dict) else None
        if not isinstance(row, dict) or "train" not in row or "validation" not in row:
            raise ValueError("El mapa de sesiones debe cubrir K01–K04 con train y validation.")
        sessions[person] = {
            "train": tuple(row["train"]),
            "validation": tuple(row["validation"]),
        }
    return sessions


def load_sessions(path):
    """Correspondencia ID → carpetas. El archivo vive fuera de Git."""
    return sessions_from_record(json.loads(Path(path).read_text(encoding="utf-8-sig")))


def list_pngs(folder):
    paths = sorted(folder.rglob("*.png"), key=natural_key)
    if not paths:
        raise ValueError(f"No hay PNG en {folder}.")
    return paths


def pick_pngs(root, folders, count):
    """Toma `count` fotogramas repartidos de cada carpeta, sin mezclar VALIDATION."""
    chosen = []
    seen = set()
    for name in folders:
        paths = list_pngs(root / name)
        for index in spread_indices(len(paths), count):
            path = paths[index]
            if path not in seen:
                chosen.append(path)
                seen.add(path)
    return chosen


def hog_from_png(path, detector):
    payload = path.read_bytes()
    frame = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return None, "undecodable"
    boxes = detect_boxes(frame, detector)
    if len(boxes) != 1:
        return None, "no_unique_face"
    left, top, right, bottom, _score = boxes[0]
    vector = describe_face(frame[top:bottom, left:right])
    if vector is None:
        return None, "empty_hog"
    return vector.astype(np.float32), sha256(payload).hexdigest()


def extract_split(data_root, detector, split, sessions):
    vectors, labels, ids, missed = [], [], [], Counter()
    for person, folders in sessions.items():
        for path in pick_pngs(data_root, folders[split], TRAIN_COUNT if split == "train" else VAL_COUNT):
            vector, detail = hog_from_png(path, detector)
            sample = f"{person}_{split}_{path.stem}"
            if vector is None:
                missed[detail] += 1
                continue
            vectors.append(vector)
            labels.append(person)
            ids.append(sample)
    if not vectors:
        raise ValueError(f"Ningún recorte usable en {split}.")
    return np.stack(vectors), np.array(labels), np.array(ids), dict(missed)


def add_phone_k01(root, train_x, train_y, train_ids):
    phone = np.load(child(root, *PHONE), allow_pickle=False)
    vectors = np.asarray(phone["vectors"], np.float32)
    if len(vectors) <= PHONE_HOLD:
        raise ValueError("El lote del celular de K01 es demasiado corto.")
    extra = vectors[:-PHONE_HOLD]
    labels = np.full(len(extra), "K01")
    ids = np.array([f"K01_phone_{index:04d}" for index in range(len(extra))])
    return (np.concatenate([train_x, extra]), np.concatenate([train_y, labels]),
            np.concatenate([train_ids, ids]))


def four_max_distance(gallery, labels, val_x, val_y, *, slack=SLACK, k=K):
    """T = máximo d de aciertos en VALIDATION × holgura. Las cuatro clases cuentan."""
    genuines = []
    for vector, true in zip(val_x, val_y):
        winner, distance = vote_knn(gallery, labels, vector, k)
        if winner == true and distance is not None:
            genuines.append(distance)
    if not genuines:
        raise ValueError("Ningún acierto de VALIDATION para fijar T.")
    raw = float(max(genuines))
    return {"max_distance": raw * slack, "raw_max_val": raw, "n_correct": len(genuines), "slack": slack}


def apply_threshold(gallery, labels, val_x, threshold, k=K):
    predicted = []
    for vector in val_x:
        winner, distance = vote_knn(gallery, labels, vector, k)
        if winner in PEOPLE and distance is not None and distance <= threshold:
            predicted.append(winner)
        else:
            predicted.append("UNKNOWN")
    return np.array(predicted)


def score_four(true, predicted):
    true, predicted = np.asarray(true), np.asarray(predicted)
    matrix = []
    for person in PEOPLE:
        row = [int(((true == person) & (predicted == other)).sum()) for other in PEOPLE]
        row.append(int(((true == person) & ~np.isin(predicted, PEOPLE)).sum()))
        matrix.append(row)
    correct = int((true == predicted).sum())
    return {
        "n": int(len(true)),
        "accuracy": correct / len(true) if len(true) else None,
        "per_person": {person: int(((true == person) & (predicted == person)).sum())
                       for person in PEOPLE},
        "counts": {person: int((true == person).sum()) for person in PEOPLE},
        "unknown": int((~np.isin(predicted, PEOPLE)).sum()),
        "confusion_rows_K01_K04_unknown": matrix,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=DATA_ROOT)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    parser.add_argument("--run-name", default=RUN)
    parser.add_argument("--map", type=Path, required=True,
                        help="JSON privado ID→carpetas, fuera de Git.")
    args = parser.parse_args()
    root = verify_vault(args.vault)
    sessions = load_sessions(args.map)
    folder = child(root, "experiments", "identity_four", args.run_name)
    if folder.exists():
        raise FileExistsError("Ese ensayo ya existe.")
    detector = load_detector(args.models)
    train_x, train_y, train_ids, train_missed = extract_split(args.data, detector, "train", sessions)
    train_x, train_y, train_ids = add_phone_k01(root, train_x, train_y, train_ids)
    val_x, val_y, val_ids, val_missed = extract_split(args.data, detector, "validation", sessions)
    predicted = np.array([vote_knn(train_x, train_y, vector, k=K)[0] for vector in val_x])
    distances = four_max_distance(train_x, train_y, val_x, val_y)
    with_t = apply_threshold(train_x, train_y, val_x, distances["max_distance"])
    summary = {
        "at_utc": utc_now(),
        "sessions": {person: {key: list(value) for key, value in folders.items()}
                     for person, folders in sessions.items()},
        "train_count": TRAIN_COUNT,
        "val_count": VAL_COUNT,
        "train_n": int(len(train_y)),
        "validation_n": int(len(val_y)),
        "train_labels": dict(Counter(train_y.tolist())),
        "val_labels": dict(Counter(val_y.tolist())),
        "train_missed": train_missed,
        "val_missed": val_missed,
        "validation_argmax": score_four(val_y, predicted),
        "validation_with_T": score_four(val_y, with_t),
        "distance": distances,
        "note": "VALIDATION es otro encuentro (02/03), no el final de la misma ráfaga. No es TEST.",
    }
    folder.mkdir(parents=True)
    digest = write_gallery(folder / GALLERY_NAME, train_x, train_y)
    summary["gallery_sha256"] = digest
    write_synced(folder / "summary.json", json.dumps(summary, indent=2, allow_nan=False).encode("utf-8"))
    write_synced(folder / DISTANCE_NAME, json.dumps({
        "max_distance": distances["max_distance"],
        "raw_max_val": distances["raw_max_val"],
        "slack": SLACK,
        "gallery_sha256": digest,
        "at_utc": utc_now(),
    }, indent=2, allow_nan=False).encode("utf-8"))
    print(json.dumps({
        "train_n": summary["train_n"],
        "train_labels": summary["train_labels"],
        "validation_argmax": summary["validation_argmax"],
        "validation_with_T": summary["validation_with_T"],
        "max_distance": distances["max_distance"],
        "gallery_sha256": digest,
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
