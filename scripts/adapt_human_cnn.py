"""Ajusta la CNN humano/no humano con recortes del celular. No identifica a K01."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from time import perf_counter
import warnings

import cv2
import numpy as np

from scripts.capture_manifest import child, utc_now, write_synced
from scripts.dataset_capture import verify_vault
from scripts.face_pipeline import load_detector
from scripts.hog_knn import detect_boxes
from scripts.human_cnn import (
    BATCH, HUMAN, NONHUMAN, SEED, class_weights, load_public, predict_labels, resize_rgb, score,
)


PHONE = ("experiments", "hog_phone_adapt", "K01", "k01_phone_v3", "frames")
PHONE_HOLD = 5
PATCHES = 3
PATCH = 160
EPOCHS = 8
LEARNING_RATE = .0003
PHONE_WEIGHT = 20.
PUBLIC_LIMIT = 2000
BASE_RUN = "human_cnn_full"


def overlap_fraction(face, patch):
    """Intersección del parche con la cara, relativa al área del parche."""
    ax1, ay1, ax2, ay2 = face
    bx1, by1, bx2, by2 = patch
    left, top = max(ax1, bx1), max(ay1, by1)
    right, bottom = min(ax2, bx2), min(ay2, by2)
    if right <= left or bottom <= top:
        return 0.
    return (right - left) * (bottom - top) / max(1, (bx2 - bx1) * (by2 - by1))


def to_rgb(bgr):
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def background_patches(frame, face, rng):
    height, width = frame.shape[:2]
    side = min(PATCH, height, width)
    patches = []
    tries = 0
    while len(patches) < PATCHES and tries < 80:
        tries += 1
        left = int(rng.integers(0, width - side + 1))
        top = int(rng.integers(0, height - side + 1))
        box = (left, top, left + side, top + side)
        if overlap_fraction(face, box) > .05:
            continue
        patches.append(to_rgb(frame[top:top + side, left:left + side]))
    return patches


def collect_phone(root, models):
    """Caras YuNet = humano. Parches sin solape = no humano. Parte como el holdout de K01."""
    detector = load_detector(models)
    folder = child(root, *PHONE)
    paths = sorted(folder.glob("K01_PHONE_*.png"))
    if len(paths) <= PHONE_HOLD:
        raise ValueError("No hay suficientes fotogramas del celular.")
    rng = np.random.default_rng(SEED)
    faces, patches, groups = [], [], []
    for index, path in enumerate(paths):
        frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
        boxes = detect_boxes(frame, detector)
        if len(boxes) != 1:
            continue
        left, top, right, bottom, _score = boxes[0]
        faces.append(to_rgb(frame[top:bottom, left:right]))
        split = "validation" if index >= len(paths) - PHONE_HOLD else "train"
        groups.append(split)
        for patch in background_patches(frame, (left, top, right, bottom), rng):
            patches.append((patch, split))
    if len(faces) != len(paths):
        raise RuntimeError("Algún fotograma del celular no tuvo un único recorte YuNet.")
    human = {"train": [], "validation": []}
    other = {"train": [], "validation": []}
    for image, split in zip(faces, groups, strict=True):
        human[split].append(image)
    for image, split in patches:
        other[split].append(image)
    return {
        "human": {key: resize_rgb(human[key]) for key in human},
        "nonhuman": {key: resize_rgb(other[key]) for key in other},
        "n_frames": len(paths),
    }


def pack(public, phone, split):
    public_images, public_labels = public[split]
    phone_h = phone["human"][split]
    phone_n = phone["nonhuman"][split]
    images = np.concatenate([public_images, phone_h, phone_n])
    labels = np.concatenate([
        public_labels,
        np.full(len(phone_h), HUMAN),
        np.full(len(phone_n), NONHUMAN),
    ])
    weights = np.concatenate([
        np.ones(len(public_labels), np.float32),
        np.full(len(phone_h) + len(phone_n), PHONE_WEIGHT, np.float32),
    ])
    rng = np.random.default_rng(SEED)
    order = rng.permutation(len(labels))
    return images[order], labels[order], weights[order]


def adapt(keras, base, train_images, train_labels, train_weights, val_images, val_labels):
    keras.utils.set_random_seed(SEED)
    model = keras.models.load_model(base)
    model.compile(optimizer=keras.optimizers.Adam(LEARNING_RATE),
                  loss=keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                  metrics=["accuracy"])
    weights = class_weights(train_labels)
    combined = np.asarray(train_weights, np.float32)
    combined[train_labels == HUMAN] *= np.float32(weights[HUMAN])
    combined[train_labels == NONHUMAN] *= np.float32(weights[NONHUMAN])
    started = perf_counter()
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        history = model.fit(
            train_images, train_labels, validation_data=(val_images, val_labels),
            batch_size=BATCH, epochs=EPOCHS, verbose=0, sample_weight=combined,
        )
    if len(history.history["loss"]) != EPOCHS:
        raise RuntimeError("Ajuste incompleto.")
    return model, {
        "ms": (perf_counter() - started) * 1000,
        "epochs": EPOCHS,
        "learning_rate": LEARNING_RATE,
        "phone_weight": PHONE_WEIGHT,
        "class_weight": {str(HUMAN): weights[HUMAN], str(NONHUMAN): weights[NONHUMAN]},
        "warnings": [str(item.message) for item in notices],
        "train": score(train_labels, predict_labels(model, train_images)),
        "validation": score(val_labels, predict_labels(model, val_images)),
    }


def phone_score(model, phone):
    return {
        "faces_train": score(np.full(len(phone["human"]["train"]), HUMAN),
                             predict_labels(model, phone["human"]["train"])),
        "faces_validation": score(np.full(len(phone["human"]["validation"]), HUMAN),
                                  predict_labels(model, phone["human"]["validation"])),
        "patches_train": score(np.full(len(phone["nonhuman"]["train"]), NONHUMAN),
                               predict_labels(model, phone["nonhuman"]["train"])),
        "patches_validation": score(np.full(len(phone["nonhuman"]["validation"]), NONHUMAN),
                                    predict_labels(model, phone["nonhuman"]["validation"])),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--run-name", default="human_cnn_phone_v1")
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    args = parser.parse_args()
    os.environ["KERAS_BACKEND"] = "jax"
    os.environ["JAX_PLATFORMS"] = "cpu"
    import keras
    import jax

    root = verify_vault(args.vault)
    base = child(root, "experiments", "human_cnn", BASE_RUN, "model.keras")
    folder = child(root, "experiments", "human_cnn", args.run_name)
    if folder.exists():
        raise FileExistsError("Ese ensayo ya existe.")
    phone = collect_phone(root, args.models)
    public = load_public(PUBLIC_LIMIT)
    train_x, train_y, train_w = pack(public, phone, "train")
    val_x, val_y, _val_w = pack(public, phone, "validation")
    model, fit = adapt(keras, base, train_x, train_y, train_w, val_x, val_y)
    domain = phone_score(model, phone)
    folder.mkdir(parents=True)
    model.save(folder / "model.keras")
    summary = {
        "at_utc": utc_now(),
        "task": "human_vs_nonhuman_phone_adapt",
        "base": BASE_RUN,
        "public_limit": PUBLIC_LIMIT,
        "phone_frames": phone["n_frames"],
        "phone_faces_train": int(len(phone["human"]["train"])),
        "phone_faces_validation": int(len(phone["human"]["validation"])),
        "phone_patches_train": int(len(phone["nonhuman"]["train"])),
        "phone_patches_validation": int(len(phone["nonhuman"]["validation"])),
        "not_liveness": True,
        "versions": {"keras": keras.__version__, "jax": jax.__version__, "numpy": np.__version__},
        "fit": fit,
        "phone": domain,
        "model_sha256": sha256((folder / "model.keras").read_bytes()).hexdigest(),
    }
    write_synced(folder / "summary.json", json.dumps(summary, indent=2, allow_nan=False).encode("utf-8"))
    print(json.dumps({
        "saved": str(folder),
        "phone": domain,
        "validation": fit["validation"],
        "model_sha256": summary["model_sha256"],
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
