"""Compara k-NN, MLP y SVM lineal con el mismo HOG privado de S01 y R01."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from time import perf_counter
import warnings

import numpy as np

from scripts.capture_manifest import child, read_json, utc_now, write_synced
from scripts.dataset_capture import verify_vault
from scripts.evaluate_hog_knn import K, MANIFEST_FOLDER, score_predictions, validate_manifest
from scripts.face_pipeline import describe
from scripts.hog_knn import FEATURE_COUNT, PEOPLE, knn_candidate


SEED = 17
EPOCHS = 150
BATCH_SIZE = 16
LEARNING_RATE = .01
L2 = .001
HIDDEN_UNITS = 32


def read_split(baseline, split, records, manifest):
    if [(row["sample_id"], row["person_id"]) for row in records] != [
        (row["sample_id"], row["person_id"]) for row in manifest
    ]:
        raise ValueError("Los registros HOG no coinciden con el manifiesto congelado.")
    usable = [row for row in records if row["status"] == "ok"]
    with np.load(child(baseline, f"{split}.npz"), allow_pickle=False) as file:
        vectors, labels, ids = (file[key] for key in ("vectors", "labels", "sample_ids"))
    if (vectors.shape != (len(usable), FEATURE_COUNT) or vectors.dtype != np.float32
            or not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), 1)
            or set(labels) != set(PEOPLE)
            or labels.tolist() != [row["person_id"] for row in usable]
            or ids.tolist() != [row["sample_id"] for row in usable]):
        raise ValueError("Los vectores HOG o sus etiquetas no coinciden con los registros.")
    return vectors, labels


def svm_margin(ops, targets, scores):
    """Por clase exige que su puntuación supere en uno a la mejor rival."""
    correct = ops.sum(targets * scores, axis=-1)
    competitor = ops.max(ops.where(targets > 0, float("-inf"), scores), axis=-1)
    return ops.maximum(0., 1. + competitor - correct)


def train_model(keras, name, vectors, labels):
    keras.utils.set_random_seed(SEED)
    regularizer = keras.regularizers.L2(L2)
    layers = [keras.Input(shape=(FEATURE_COUNT,))]
    if name == "mlp":
        layers.append(keras.layers.Dense(HIDDEN_UNITS, activation="relu", kernel_regularizer=regularizer))
        loss = keras.losses.CategoricalCrossentropy(from_logits=True)
    else:
        def loss(targets, scores):
            return svm_margin(keras.ops, targets, scores)

    layers.append(keras.layers.Dense(len(PEOPLE), kernel_regularizer=regularizer))
    model = keras.Sequential(layers, name=name)
    model.compile(optimizer=keras.optimizers.Adam(LEARNING_RATE), loss=loss)
    targets = np.eye(len(PEOPLE), dtype=np.float32)[np.searchsorted(PEOPLE, labels)]
    started = perf_counter()
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        history = model.fit(vectors, targets, batch_size=BATCH_SIZE, epochs=EPOCHS, verbose=0)
    elapsed_ms = (perf_counter() - started) * 1000
    losses = history.history["loss"]
    if len(losses) != EPOCHS or not np.isfinite(losses).all():
        raise RuntimeError(f"Entrenamiento incompleto o no finito en {name}.")
    return model, {"ms": elapsed_ms, "loss": losses, "warnings": [str(item.message) for item in notices]}


def predict_keras(model, vector):
    scores = np.asarray(model(vector[None, :], training=False))[0]
    if not np.isfinite(scores).all():
        raise RuntimeError("Puntuaciones no finitas.")
    winners = np.flatnonzero(scores == scores.max())
    return PEOPLE[winners[0]] if len(winners) == 1 else "AMBIGUOUS"


def measure(predict, vectors, labels, records):
    for vector in vectors[:3]:
        predict(vector)
    predictions, timings = [], []
    for vector in vectors:
        started = perf_counter()
        predictions.append(predict(vector))
        timings.append((perf_counter() - started) * 1000)
    summary = score_predictions(labels, predictions, records)
    summary["classify_ms"] = describe(timings)
    return summary, predictions


def run(vault, run_name):
    root = verify_vault(vault)
    folder = child(root, *MANIFEST_FOLDER)
    baseline = child(folder, "knn_baseline_v1")
    destination = child(folder, run_name)
    if destination.exists():
        raise FileExistsError("El ensayo ya existe. Usa otro nombre.")
    manifest_bytes = child(folder, "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
    validate_manifest(manifest)
    manifest_hash = sha256(manifest_bytes).hexdigest()
    if manifest_hash != read_json(child(baseline, "summary.json"))["manifest_sha256"]:
        raise ValueError("El manifiesto no es el usado por la referencia k-NN.")
    records = read_json(child(baseline, "records.json"))
    data = {split: read_split(baseline, split, records[split], manifest[split])
            for split in ("train", "validation")}
    train, labels = data["train"]

    os.environ["KERAS_BACKEND"] = "jax"
    os.environ["JAX_PLATFORMS"] = "cpu"
    import keras
    import jax

    summary = {
        "at_utc": utc_now(),
        "manifest_sha256": manifest_hash,
        "hog_inputs_sha256": {split: sha256(child(baseline, f"{split}.npz").read_bytes()).hexdigest()
                              for split in data},
        "versions": {"keras": keras.__version__, "jax": jax.__version__, "numpy": np.__version__},
        "people_order": PEOPLE,
        "config": {"k": K, "seed": SEED, "epochs": EPOCHS, "batch_size": BATCH_SIZE,
                   "adam_learning_rate": LEARNING_RATE, "l2": L2, "mlp_hidden_units": HIDDEN_UNITS},
        "models": {},
    }
    predictions = {}
    with TemporaryDirectory(prefix=".compare-", dir=folder) as temporary:
        staging = Path(temporary) / "run"
        staging.mkdir()
        for name in ("knn", "mlp", "svm"):
            details = {}
            if name == "knn":
                def predict(vector):
                    candidate, _ = knn_candidate(train, labels, vector, k=K)
                    return candidate or "AMBIGUOUS"
            else:
                model, details["fit"] = train_model(keras, name, train, labels)
                model_path = staging / f"{name}.keras"
                model.save(model_path)
                restored = keras.models.load_model(model_path, compile=False)
                if not np.allclose(np.asarray(model(train, training=False)),
                                   np.asarray(restored(train, training=False))):
                    raise RuntimeError(f"El modelo guardado {name} cambió sus puntuaciones.")

                def predict(vector):
                    return predict_keras(restored, vector)

            predictions[name] = {}
            for split, (vectors, true_labels) in data.items():
                details[split], predictions[name][split] = measure(predict, vectors, true_labels, records[split])
            summary["models"][name] = details
        for filename, content in (("summary.json", summary), ("predictions.json", predictions)):
            write_synced(staging / filename, json.dumps(content, indent=2, allow_nan=False).encode("utf-8"))
        staging.rename(destination)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--run-name", default="hog_comparison_v1")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run_name):
        parser.error("El nombre del ensayo debe ser un nombre de carpeta simple.")
    summary = run(args.vault, args.run_name)
    for name, detail in summary["models"].items():
        result = detail["validation"]
        print(f"{name}: {result['correct']}/{result['usable']} usables, "
              f"{result['correct']}/{result['frames_total']} totales, macro-F1 {result['macro_f1']:.3f}")


if __name__ == "__main__":
    main()
