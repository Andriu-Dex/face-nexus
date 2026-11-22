"""Compara k-NN, MLP y SVM lineal con el mismo HOG K01 frente a LFW."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from time import perf_counter
import warnings

import numpy as np

from scripts.capture_manifest import child, utc_now, write_synced
from scripts.compare_hog_models import svm_margin
from scripts.dataset_capture import verify_vault
from scripts.evaluate_hog_knn import K
from scripts.face_pipeline import describe
from scripts.hog_knn import FEATURE_COUNT, knn_candidate
from scripts.identity_k01 import CLASSES, EPOCHS, LEARNING_RATE, L2, load_k01_gallery, load_lfw_hog


BATCH = 32
HIDDEN = 32
SEED = 17
GALLERY_NAME = "gallery.npz"


def write_gallery(path, vectors, labels):
    path = Path(path)
    np.savez_compressed(path, vectors=np.asarray(vectors, np.float32), labels=np.asarray(labels))
    return sha256(path.read_bytes()).hexdigest()


def load_gallery(path):
    with np.load(path, allow_pickle=False) as file:
        vectors = np.asarray(file["vectors"], np.float32)
        labels = np.asarray(file["labels"])
    if vectors.ndim != 2 or vectors.shape[1] != FEATURE_COUNT or len(labels) != len(vectors):
        raise ValueError("La galería HOG no coincide con el ensayo.")
    return vectors, labels


def vote_knn(gallery, labels, vector, k=K):
    winner, distance = knn_candidate(gallery, labels, vector, k)
    return (winner or "OTHER"), (None if distance is None else float(distance))


def knn_max_distance(gallery, labels, val_x, val_y, *, slack=1.1, k=K):
    """T = máximo d de K01 en VALIDATION (voto K01) × holgura. No usa TEST."""
    genuines = []
    impostors = []
    for vector, true in zip(val_x, val_y):
        winner, distance = vote_knn(gallery, labels, vector, k)
        if distance is None:
            continue
        if true == "K01" and winner == "K01":
            genuines.append(distance)
        elif true != "K01" and winner == "K01":
            impostors.append(distance)
    if not genuines:
        raise ValueError("No hay distancias genuínas de K01 para fijar T.")
    raw = float(max(genuines))
    threshold = raw * slack
    return {
        "max_distance": threshold,
        "raw_max_k01_val": raw,
        "slack": slack,
        "k": k,
        "val_k01_accepted": len(genuines),
        "lfw_as_k01_before": len(impostors),
        "lfw_as_k01_after": int(sum(distance <= threshold for distance in impostors)),
        "impostor_distances": impostors,
    }


def assemble(root):
    """Las mismas particiones que identity_k01: S01+celular TRAIN, LFW por identidad."""
    s01, phone_train, phone_val = load_k01_gallery(root)
    lfw_train, lfw_val, n_people, n_lfw = load_lfw_hog()
    train_x = np.concatenate([s01, phone_train, lfw_train])
    train_y = np.concatenate([
        np.full(len(s01) + len(phone_train), "K01"),
        np.full(len(lfw_train), "OTHER"),
    ])
    val_x = np.concatenate([phone_val, lfw_val])
    val_y = np.concatenate([np.full(len(phone_val), "K01"), np.full(len(lfw_val), "OTHER")])
    counts = {
        "s01_k01": int(len(s01)),
        "phone_train_k01": int(len(phone_train)),
        "phone_val_k01": int(len(phone_val)),
        "lfw_identities": n_people,
        "lfw_hog": n_lfw,
        "lfw_train": int(len(lfw_train)),
        "lfw_val": int(len(lfw_val)),
        "train": int(len(train_y)),
        "validation": int(len(val_y)),
    }
    return {"train": (train_x, train_y), "validation": (val_x, val_y), "counts": counts}


def weights_for(labels):
    n_k01 = int((labels == "K01").sum())
    n_other = int((labels == "OTHER").sum())
    total = n_k01 + n_other
    return {0: total / (2. * n_other), 1: total / (2. * n_k01)}


def score_binary(true, predicted):
    """K01 es el positivo de acceso. Un empate k-NN cuenta como OTHER, no como aceptación."""
    true = np.asarray(true)
    predicted = np.asarray(predicted)
    if true.shape != predicted.shape or not true.size:
        raise ValueError("Etiquetas y predicciones incompatibles.")
    pred = np.array(["OTHER" if label not in CLASSES else label for label in predicted])
    k01 = true == "K01"
    other = true == "OTHER"
    pred_k01 = pred == "K01"
    tp = int((k01 & pred_k01).sum())
    fn = int((k01 & ~pred_k01).sum())
    fp = int((other & pred_k01).sum())
    tn = int((other & ~pred_k01).sum())
    precision = tp / (tp + fp) if tp + fp else 0.
    k01_recall = tp / (tp + fn) if tp + fn else 0.
    other_recall = tn / (tn + fp) if tn + fp else 0.
    other_precision = tn / (tn + fn) if tn + fn else 0.
    f1_k01 = 2 * precision * k01_recall / (precision + k01_recall) if precision + k01_recall else 0.
    f1_other = (2 * other_precision * other_recall / (other_precision + other_recall)
                if other_precision + other_recall else 0.)
    return {
        "n": int(len(true)),
        "n_k01": int(k01.sum()),
        "n_other": int(other.sum()),
        "true_k01_pred_k01": tp,
        "true_k01_pred_other": fn,
        "true_other_pred_k01": fp,
        "true_other_pred_other": tn,
        "accuracy": (tp + tn) / len(true),
        "k01_recall": k01_recall,
        "other_recall": other_recall,
        "false_accepts": fp,
        "false_rejects": fn,
        "macro_f1": (f1_k01 + f1_other) / 2.,
    }


def pick_winner(models):
    """Descarta quien no reconoce a K01. Luego menos LFW aceptados, menos rechazos, latencia."""
    usable = [name for name, row in models.items() if row["validation"]["k01_recall"] > 0]
    if not usable:
        raise ValueError("Ningún modelo reconoció a K01 en validación.")

    def key(name):
        val = models[name]["validation"]
        latency = val["classify_ms"].get("median", 0.)
        return (val["false_accepts"], val["false_rejects"], latency, name)

    return min(usable, key=key)


def train_keras(keras, name, vectors, labels):
    keras.utils.set_random_seed(SEED)
    regularizer = keras.regularizers.L2(L2)
    layers = [keras.Input(shape=(vectors.shape[1],))]
    if name == "mlp":
        layers.append(keras.layers.Dense(HIDDEN, activation="relu", kernel_regularizer=regularizer))
        loss = keras.losses.CategoricalCrossentropy(from_logits=True)
    else:
        def loss(targets, scores):
            return svm_margin(keras.ops, targets, scores)

    layers.append(keras.layers.Dense(len(CLASSES), kernel_regularizer=regularizer))
    model = keras.Sequential(layers, name=name)
    model.compile(optimizer=keras.optimizers.Adam(LEARNING_RATE), loss=loss)
    index = np.array([CLASSES.index(label) for label in labels])
    targets = np.eye(len(CLASSES), dtype=np.float32)[index]
    started = perf_counter()
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        history = model.fit(vectors, targets, batch_size=BATCH, epochs=EPOCHS,
                            verbose=0, class_weight=weights_for(labels))
    losses = history.history["loss"]
    if len(losses) != EPOCHS or not np.isfinite(losses).all():
        raise RuntimeError(f"Entrenamiento incompleto en {name}.")
    return model, {
        "ms": (perf_counter() - started) * 1000,
        "final_loss": float(losses[-1]),
        "warnings": [str(item.message) for item in notices],
    }


def predict_keras(model, vector):
    scores = np.asarray(model(vector[None, :], training=False), dtype=np.float64)[0]
    if not np.isfinite(scores).all() or scores.shape != (2,):
        return "OTHER"
    return CLASSES[int(np.argmax(scores))]


def measure(predict, vectors, labels):
    for vector in vectors[:3]:
        predict(vector)
    predicted, timings = [], []
    for vector in vectors:
        started = perf_counter()
        predicted.append(predict(vector))
        timings.append((perf_counter() - started) * 1000)
    summary = score_binary(labels, predicted)
    summary["classify_ms"] = describe(timings)
    return summary, predicted


def run(vault, run_name):
    root = verify_vault(vault)
    destination = child(root, "experiments", "identity_k01", run_name)
    if destination.exists():
        raise FileExistsError("Ese ensayo ya existe.")
    data = assemble(root)
    train_x, train_y = data["train"]
    os.environ["KERAS_BACKEND"] = "jax"
    os.environ["JAX_PLATFORMS"] = "cpu"
    import keras
    import jax

    summary = {
        "at_utc": utc_now(),
        "task": "K01_vs_OTHER",
        "classes": CLASSES,
        "counts": data["counts"],
        "versions": {"keras": keras.__version__, "jax": jax.__version__, "numpy": np.__version__},
        "config": {
            "k": K, "seed": SEED, "epochs": EPOCHS, "batch": BATCH,
            "adam_learning_rate": LEARNING_RATE, "l2": L2, "mlp_hidden": HIDDEN,
        },
        "models": {},
    }
    predictions = {}
    destination.mkdir(parents=True)
    summary["gallery_sha256"] = write_gallery(destination / GALLERY_NAME, train_x, train_y)
    for name in ("knn", "mlp", "svm"):
        details = {}
        if name == "knn":
            def predict(vector, gallery=train_x, gallery_y=train_y):
                winner, _ = knn_candidate(gallery, gallery_y, vector, k=K)
                return winner or "OTHER"
        else:
            model, details["fit"] = train_keras(keras, name, train_x, train_y)
            path = destination / f"{name}.keras"
            model.save(path)
            restored = keras.models.load_model(path, compile=False)
            if not np.allclose(np.asarray(model(train_x[:8], training=False)),
                               np.asarray(restored(train_x[:8], training=False))):
                raise RuntimeError(f"El modelo guardado {name} cambió sus puntuaciones.")
            details["sha256"] = sha256(path.read_bytes()).hexdigest()

            def predict(vector, loaded=restored):
                return predict_keras(loaded, vector)

        predictions[name] = {}
        for split in ("train", "validation"):
            vectors, labels = data[split]
            details[split], predictions[name][split] = measure(predict, vectors, labels)
        summary["models"][name] = details
    summary["winner"] = pick_winner(summary["models"])
    write_synced(destination / "summary.json", json.dumps(summary, indent=2, allow_nan=False).encode("utf-8"))
    write_synced(destination / "predictions.json",
                 json.dumps(predictions, indent=2, allow_nan=False).encode("utf-8"))
    return summary


def export_existing_gallery(vault, run_name):
    """Reconstruye la galería TRAIN del ensayo ya medido, sin reentrenar."""
    root = verify_vault(vault)
    destination = child(root, "experiments", "identity_k01", run_name)
    if not destination.exists():
        raise FileNotFoundError("No existe ese ensayo de comparación.")
    train_x, train_y = assemble(root)["train"]
    digest = write_gallery(destination / GALLERY_NAME, train_x, train_y)
    return {"n": int(len(train_y)), "sha256": digest, "path": str(destination / GALLERY_NAME)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--run-name", default="identity_k01_compare_v1")
    parser.add_argument("--export-gallery", action="store_true")
    args = parser.parse_args()
    if args.export_gallery:
        print(json.dumps(export_existing_gallery(args.vault, args.run_name), indent=2))
        return
    summary = run(args.vault, args.run_name)
    print(json.dumps({
        "winner": summary["winner"],
        "counts": summary["counts"],
        "validation": {name: {key: row["validation"][key] for key in (
            "true_k01_pred_k01", "true_k01_pred_other", "true_other_pred_k01",
            "true_other_pred_other", "k01_recall", "false_accepts", "macro_f1",
        )} for name, row in summary["models"].items()},
    }, indent=2))


if __name__ == "__main__":
    main()
