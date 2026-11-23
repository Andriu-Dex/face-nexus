"""Entrena K01 frente a otros humanos (LFW). No finge las cuatro identidades."""

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
from scripts.compare_hog_models import read_split, svm_margin
from scripts.dataset_capture import verify_vault
from scripts.evaluate_hog_knn import MANIFEST_FOLDER, validate_manifest
from scripts.hog_knn import FEATURE_COUNT, describe_face
from scripts.human_cnn import split_by_identity


SEED = 17
EPOCHS = 80
BATCH = 32
LEARNING_RATE = .01
L2 = .001
CLASSES = ("OTHER", "K01")
PHONE = ("experiments", "hog_phone_adapt", "K01", "k01_phone_v3", "hog.npz")
PHONE_HOLD = 5


def binary_vote(scores):
    """K01 es la clase 1. El margen es |s_K01 - s_OTHER|."""
    scores = np.asarray(scores, dtype=np.float64)
    if scores.shape != (2,) or not np.isfinite(scores).all():
        return None
    if scores[1] > scores[0]:
        return "K01", float(scores[1] - scores[0])
    return "OTHER", float(scores[0] - scores[1])


def to_bgr(image):
    array = np.asarray(image)
    if array.max() <= 1.5:
        array = array * 255.
    array = np.clip(array, 0, 255).astype(np.uint8)
    if array.ndim == 2:
        return cv2.cvtColor(array, cv2.COLOR_GRAY2BGR)
    return cv2.cvtColor(array, cv2.COLOR_RGB2BGR)


def hog_vector(image):
    return describe_face(to_bgr(image))


def hog_collection(images, identities):
    vectors, labels = [], []
    for image, identity in zip(images, identities, strict=True):
        vector = hog_vector(image)
        if vector is not None:
            vectors.append(vector.astype(np.float32))
            labels.append(identity)
    if not vectors:
        raise ValueError("Ningún recorte LFW produjo HOG.")
    return np.stack(vectors), np.array(labels)


def train_binary_svm(keras, vectors, labels):
    keras.utils.set_random_seed(SEED)
    regularizer = keras.regularizers.L2(L2)
    model = keras.Sequential([
        keras.Input(shape=(FEATURE_COUNT,)),
        keras.layers.Dense(len(CLASSES), kernel_regularizer=regularizer),
    ], name="identity_k01")

    def loss(targets, scores):
        return svm_margin(keras.ops, targets, scores)

    model.compile(optimizer=keras.optimizers.Adam(LEARNING_RATE), loss=loss)
    index = np.array([CLASSES.index(label) for label in labels])
    targets = np.eye(len(CLASSES), dtype=np.float32)[index]
    n_k01 = int((labels == "K01").sum())
    n_other = int((labels == "OTHER").sum())
    total = n_k01 + n_other
    weights = {0: total / (2. * n_other), 1: total / (2. * n_k01)}
    started = perf_counter()
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        history = model.fit(vectors, targets, batch_size=BATCH, epochs=EPOCHS,
                            verbose=0, class_weight=weights)
    if len(history.history["loss"]) != EPOCHS:
        raise RuntimeError("Entrenamiento incompleto.")
    return model, {
        "ms": (perf_counter() - started) * 1000,
        "n_k01": n_k01,
        "n_other": n_other,
        "loss": [float(x) for x in history.history["loss"]],
        "warnings": [str(item.message) for item in notices],
    }


def votes(model, vectors):
    scores = np.asarray(model(vectors, training=False), dtype=np.float64)
    rows = []
    for row in scores:
        result = binary_vote(row)
        rows.append(result if result is not None else ("OTHER", 0.))
    return rows


def threshold_for_others(other_votes):
    """El menor umbral que rechaza a todos los OTHER de validación etiquetados como K01."""
    unsafe = [margin for label, margin in other_votes if label == "K01"]
    if not unsafe:
        return 0.
    return float(np.nextafter(max(unsafe), np.inf))


def accept_k01(label, margin, threshold):
    return label == "K01" and margin >= threshold


def load_k01_gallery(root):
    folder = child(root, *MANIFEST_FOLDER)
    baseline = child(folder, "knn_baseline_v1")
    manifest = json.loads(child(folder, "manifest.json").read_bytes().decode("utf-8-sig"))
    validate_manifest(manifest)
    records = json.loads(child(baseline, "records.json").read_text(encoding="utf-8-sig"))
    train, labels = read_split(baseline, "train", records["train"], manifest["train"])
    s01 = train[labels == "K01"]
    phone = np.load(child(root, *PHONE), allow_pickle=False)
    phone_vectors = np.asarray(phone["vectors"], np.float32)
    if len(phone_vectors) <= PHONE_HOLD:
        raise ValueError("El lote del celular es demasiado pequeño para reservar validación.")
    return s01, phone_vectors[:-PHONE_HOLD], phone_vectors[-PHONE_HOLD:]


def load_lfw_hog(*, with_train_identities=False):
    from sklearn.datasets import fetch_lfw_people
    lfw = fetch_lfw_people(color=True, min_faces_per_person=2, resize=.5, download_if_missing=True)
    vectors, identities = hog_collection(lfw.images, lfw.target)
    train_mask, val_mask = split_by_identity(identities)
    n_people = int(identities.max()) + 1
    train, val = vectors[train_mask], vectors[val_mask]
    if not with_train_identities:
        return train, val, n_people, len(vectors)
    names = np.asarray(lfw.target_names, dtype=str)[identities[train_mask]]
    samples = np.array([f"{name}_{index:04d}" for index, name in enumerate(names)])
    return train, val, n_people, len(vectors), names, samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--run-name", default="identity_k01_v1")
    args = parser.parse_args()
    os.environ["KERAS_BACKEND"] = "jax"
    os.environ["JAX_PLATFORMS"] = "cpu"
    import keras

    root = verify_vault(args.vault)
    s01, phone_train, phone_val = load_k01_gallery(root)
    lfw_train, lfw_val, n_people, n_lfw = load_lfw_hog()
    other = np.full(len(lfw_train), "OTHER")
    k01 = np.full(len(s01) + len(phone_train), "K01")
    train_x = np.concatenate([s01, phone_train, lfw_train])
    train_y = np.concatenate([k01, other])
    model, fit = train_binary_svm(keras, train_x, train_y)
    val_k01 = votes(model, phone_val)
    val_other = votes(model, lfw_val)
    threshold = threshold_for_others(val_other)
    summary = {
        "at_utc": utc_now(),
        "classes": CLASSES,
        "s01_k01": int(len(s01)),
        "phone_train_k01": int(len(phone_train)),
        "phone_val_k01": int(len(phone_val)),
        "lfw_identities": n_people,
        "lfw_hog": n_lfw,
        "lfw_train": int(len(lfw_train)),
        "lfw_val": int(len(lfw_val)),
        "threshold": threshold,
        "phone_val_accepted": int(sum(accept_k01(label, margin, threshold)
                                      for label, margin in val_k01)),
        "lfw_val_as_k01": int(sum(accept_k01(label, margin, threshold)
                                  for label, margin in val_other)),
        "fit": {key: fit[key] for key in ("ms", "n_k01", "n_other")},
    }
    folder = child(root, "experiments", "identity_k01", args.run_name)
    if folder.exists():
        raise FileExistsError("Ese ensayo ya existe.")
    folder.mkdir(parents=True)
    model.save(folder / "model.keras")
    summary["model_sha256"] = sha256((folder / "model.keras").read_bytes()).hexdigest()
    write_synced(folder / "summary.json", json.dumps(summary, indent=2, allow_nan=False).encode("utf-8"))
    print(json.dumps(summary, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
