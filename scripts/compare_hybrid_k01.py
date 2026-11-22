"""Compara HOG solo frente a landmarks+HOG, mismas filas K01 / OTHER."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np

from scripts.capture_manifest import child, utc_now, write_synced
from scripts.compare_identity_k01 import (
    measure, pick_winner, predict_keras, score_binary, train_keras, vote_knn,
)
from scripts.dataset_capture import verify_vault
from scripts.evaluate_hog_knn import K, MANIFEST_FOLDER, validate_manifest
from scripts.face_pipeline import load_detector
from scripts.hog_knn import FEATURE_COUNT
from scripts.human_cnn import split_by_identity
from scripts.hybrid_hog import GEO_COUNT, HYBRID_COUNT, describe_pair
from scripts.identity_k01 import CLASSES, PHONE, PHONE_HOLD, to_bgr


def load_s01_k01_frames(root):
    folder = child(root, *MANIFEST_FOLDER)
    manifest = json.loads(child(folder, "manifest.json").read_bytes().decode("utf-8-sig"))
    validate_manifest(manifest)
    frames = []
    for row in manifest["train"]:
        if row["person_id"] != "K01":
            continue
        payload = child(root, *Path(row["image"]).parts).read_bytes()
        if sha256(payload).hexdigest() != row["image_sha256"]:
            raise ValueError("El hash de un fotograma S01 no coincide.")
        frame = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            continue
        frames.append(frame)
    return frames


def load_phone_frames(root):
    folder = child(root, *PHONE[:-1], "frames")
    paths = sorted(folder.glob("K01_PHONE_*.png"))
    if len(paths) <= PHONE_HOLD:
        raise ValueError("El lote del celular es demasiado pequeño.")
    frames = []
    for path in paths:
        frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError(f"No se pudo leer {path.name}.")
        frames.append(frame)
    return frames[:-PHONE_HOLD], frames[-PHONE_HOLD:]


def extract_many(frames, detector):
    hog, hybrid = [], []
    for frame in frames:
        pair = describe_pair(frame, detector)
        if pair is None:
            continue
        hog.append(pair["hog"])
        hybrid.append(pair["hybrid"])
    if not hog:
        return None
    return np.stack(hog), np.stack(hybrid)


def extract_lfw(detector):
    from sklearn.datasets import fetch_lfw_people
    lfw = fetch_lfw_people(color=True, min_faces_per_person=2, resize=.5, download_if_missing=True)
    hog, hybrid, identities = [], [], []
    skipped = 0
    for image, identity in zip(lfw.images, lfw.target, strict=True):
        pair = describe_pair(to_bgr(image), detector)
        if pair is None:
            skipped += 1
            continue
        hog.append(pair["hog"])
        hybrid.append(pair["hybrid"])
        identities.append(identity)
    if not hog:
        raise RuntimeError("Ningún recorte LFW produjo landmarks y HOG.")
    hog, hybrid = np.stack(hog), np.stack(hybrid)
    identities = np.array(identities)
    train_mask, val_mask = split_by_identity(identities)
    return {
        "train_hog": hog[train_mask],
        "train_hybrid": hybrid[train_mask],
        "val_hog": hog[val_mask],
        "val_hybrid": hybrid[val_mask],
        "n_people": int(identities.max()) + 1,
        "kept": int(len(identities)),
        "skipped": skipped,
        "lfw_images": int(len(lfw.images)),
    }


def stack_k01(hog, hybrid, other_hog, other_hybrid):
    labels = np.concatenate([np.full(len(hog), "K01"), np.full(len(other_hog), "OTHER")])
    return (
        np.concatenate([hog, other_hog]),
        np.concatenate([hybrid, other_hybrid]),
        labels,
    )


def evaluate_knn(train_x, train_y, val_x, val_y):
    def predict(vector):
        label, _ = vote_knn(train_x, train_y, vector, k=K)
        return label
    return measure(predict, val_x, val_y)[0]


def evaluate_svm(keras, train_x, train_y, val_x, val_y):
    model, fit = train_keras(keras, "svm", train_x, train_y)

    def predict(vector, loaded=model):
        return predict_keras(loaded, vector)

    summary, _ = measure(predict, val_x, val_y)
    summary["fit_ms"] = fit["ms"]
    return summary


def run(vault, models_dir, run_name):
    root = verify_vault(vault)
    destination = child(root, "experiments", "hybrid_k01", run_name)
    if destination.exists():
        raise FileExistsError("Ese ensayo ya existe.")
    detector = load_detector(models_dir)
    s01 = extract_many(load_s01_k01_frames(root), detector)
    phone_train_frames, phone_val_frames = load_phone_frames(root)
    phone_train = extract_many(phone_train_frames, detector)
    phone_val = extract_many(phone_val_frames, detector)
    if s01 is None or phone_train is None or phone_val is None:
        raise RuntimeError("S01 o el celular no produjeron pares híbridos.")
    lfw = extract_lfw(detector)
    train_hog, train_hybrid, train_y = stack_k01(
        np.concatenate([s01[0], phone_train[0]]),
        np.concatenate([s01[1], phone_train[1]]),
        lfw["train_hog"], lfw["train_hybrid"],
    )
    val_hog, val_hybrid, val_y = stack_k01(
        phone_val[0], phone_val[1], lfw["val_hog"], lfw["val_hybrid"],
    )
    os.environ["KERAS_BACKEND"] = "jax"
    os.environ["JAX_PLATFORMS"] = "cpu"
    import keras

    started = perf_counter()
    models = {
        "knn_hog": {"validation": evaluate_knn(train_hog, train_y, val_hog, val_y)},
        "knn_hybrid": {"validation": evaluate_knn(train_hybrid, train_y, val_hybrid, val_y)},
        "svm_hog": {"validation": evaluate_svm(keras, train_hog, train_y, val_hog, val_y)},
        "svm_hybrid": {"validation": evaluate_svm(keras, train_hybrid, train_y, val_hybrid, val_y)},
    }
    summary = {
        "at_utc": utc_now(),
        "task": "hog_vs_hybrid_landmarks",
        "classes": CLASSES,
        "geo_count": GEO_COUNT,
        "hog_count": FEATURE_COUNT,
        "hybrid_count": HYBRID_COUNT,
        "s01_k01": int(len(s01[0])),
        "phone_train_k01": int(len(phone_train[0])),
        "phone_val_k01": int(len(phone_val[0])),
        "lfw": {key: lfw[key] for key in ("n_people", "kept", "skipped", "lfw_images")},
        "n_train": int(len(train_y)),
        "n_validation": int(len(val_y)),
        "models": models,
        "winner": pick_winner(models),
        "elapsed_ms": (perf_counter() - started) * 1000,
        "live_unchanged": True,
    }
    destination.mkdir(parents=True)
    write_synced(destination / "summary.json", json.dumps(summary, indent=2, allow_nan=False).encode("utf-8"))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    parser.add_argument("--run-name", default="hybrid_k01_v1")
    args = parser.parse_args()
    summary = run(args.vault, args.models, args.run_name)
    print(json.dumps({
        "winner": summary["winner"],
        "lfw": summary["lfw"],
        "phone_val_k01": summary["phone_val_k01"],
        "validation": {name: {key: row["validation"][key] for key in (
            "true_k01_pred_k01", "false_rejects", "false_accepts", "k01_recall", "macro_f1",
        )} for name, row in summary["models"].items()},
    }, indent=2))


if __name__ == "__main__":
    main()
