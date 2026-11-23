"""Ensayo exploratorio K01–K04 + OTHER. LFW por identidad. No consume TEST."""

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
from scripts.compare_identity_k01 import load_gallery, vote_knn, write_gallery
from scripts.dataset_capture import verify_vault
from scripts.evaluate_hog_knn import K
from scripts.face_pipeline import describe, load_detector
from scripts.hog_knn import PEOPLE
from scripts.identity_artifacts import load_verified_knn
from scripts.identity_four import DATA_ROOT, RUN as FOUR_RUN, extract_split, score_four, sessions_from_record
from scripts.identity_k01 import EPOCHS, LEARNING_RATE, L2, load_lfw_hog
from scripts.phone_demo_manifest import (
    MANIFEST_PARTS, load_manifest, load_phase_vectors, phase_file_hashes, phone_tune_ready,
)


BATCH = 32
HIDDEN = 32
SEED = 17
RUN = "identity_four_other_v1"
CLASSES = PEOPLE + ("OTHER",)


def class_weights(labels):
    labels = np.asarray(labels)
    total = len(labels)
    return {index: total / (len(CLASSES) * max(1, int((labels == name).sum())))
            for index, name in enumerate(CLASSES)}


def score_open_classes(true, predicted):
    """Inscritos vs OTHER. Una confusión entre K01–K04 no cuenta como acierto."""
    true = np.asarray(true)
    predicted = np.array([label if label in CLASSES else "OTHER" for label in predicted])
    enrolled = np.isin(true, PEOPLE)
    other = true == "OTHER"
    pred_enrolled = np.isin(predicted, PEOPLE)
    return {
        "n": int(len(true)),
        "enrolled_n": int(enrolled.sum()),
        "other_n": int(other.sum()),
        "enrolled_correct": int((enrolled & (true == predicted)).sum()),
        "confused_accepted": int((enrolled & pred_enrolled & (true != predicted)).sum()),
        "enrolled_as_other": int((enrolled & (predicted == "OTHER")).sum()),
        "other_as_enrolled": int((other & pred_enrolled).sum()),
        "accuracy": float((true == predicted).mean()) if len(true) else None,
        "enrolled_four": score_four(true[enrolled], predicted[enrolled]) if enrolled.any() else None,
    }


def pick_winner(models):
    usable = [name for name, row in models.items()
              if row["validation"].get("enrolled_n") == 0
              or row["validation"]["enrolled_correct"] > 0]
    if not usable:
        raise ValueError("Ningún modelo acertó un inscrito en VALIDATION.")

    def key(name):
        val = models[name]["validation"]
        train = models[name].get("train") or {}
        latency = val["classify_ms"].get("median", 0.)
        enrolled = val["enrolled_correct"] if val.get("enrolled_n") else train.get("enrolled_correct", 0)
        return (val["other_as_enrolled"], val["confused_accepted"], -enrolled, latency, name)

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
                            verbose=0, class_weight=class_weights(labels))
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
    if not np.isfinite(scores).all() or scores.shape != (len(CLASSES),):
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
    summary = score_open_classes(labels, predicted)
    summary["classify_ms"] = describe(timings)
    return summary, predicted


def assemble(root, data_root, models):
    four = child(root, "experiments", "identity_four", FOUR_RUN)
    bundle, reason = load_verified_knn(four)
    if bundle is None:
        raise ValueError(f"Galería de cuatro no verificada: {reason}.")
    summary = json.loads((four / "summary.json").read_text(encoding="utf-8-sig"))
    sessions = sessions_from_record(summary)
    detector = load_detector(models)
    val_x, val_y, _ids, val_missed = extract_split(data_root, detector, "validation", sessions)
    lfw_train, lfw_val, n_people, n_lfw, lfw_names, lfw_samples = load_lfw_hog(
        with_train_identities=True)
    other_y = np.full(len(lfw_train), "OTHER")
    train_x = np.concatenate([bundle["vectors"], lfw_train.astype(np.float32)])
    train_y = np.concatenate([bundle["labels"].astype(str), other_y])
    val_all_x = np.concatenate([val_x, lfw_val.astype(np.float32)])
    val_all_y = np.concatenate([val_y.astype(str), np.full(len(lfw_val), "OTHER")])
    return {
        "train": (train_x, train_y),
        "validation": (val_all_x, val_all_y),
        "calibration": (lfw_train.astype(np.float32), other_y, lfw_samples, lfw_names),
        "counts": {
            "train_enrolled": int(np.isin(train_y, PEOPLE).sum()),
            "train_other": int((train_y == "OTHER").sum()),
            "val_enrolled": int(len(val_y)),
            "val_other": int(len(lfw_val)),
            "lfw_identities": n_people,
            "lfw_hog": n_lfw,
            "val_missed": val_missed,
        },
        "four_sha256": bundle["gallery_sha256"],
        "source": "historical_four",
    }


def assemble_phone(root, other_train_x, other_train_y, other_samples, other_ids,
                   other_val_x, other_val_y):
    """Ajuste con tune del celular más OTHER. Los lotes eval no entran al entrenamiento."""
    manifest = load_manifest(child(root, *MANIFEST_PARTS))
    issues, warnings, ready = phone_tune_ready(manifest, root)
    if not ready:
        raise ValueError(" ".join(issues) or "El ajuste del celular no cubre las cuatro clases.")
    tune_x, tune_y = load_phase_vectors(root, manifest, "tune")
    if set(map(str, tune_y)) != set(PEOPLE):
        raise ValueError("Los vectores de ajuste no cubren las cuatro clases.")
    other_train_x = np.asarray(other_train_x, np.float32)
    other_train_y = np.asarray(other_train_y, dtype=str)
    train_x = np.concatenate([tune_x, other_train_x])
    train_y = np.concatenate([np.asarray(tune_y, dtype=str), other_train_y])
    eval_pack = None
    try:
        eval_pack = load_phase_vectors(root, manifest, "eval")
    except ValueError:
        eval_pack = None
    return {
        "train": (train_x, train_y),
        "validation": (np.asarray(other_val_x, np.float32), np.asarray(other_val_y, dtype=str)),
        "eval": eval_pack,
        "calibration": (other_train_x, other_train_y, other_samples, other_ids),
        "counts": {
            "train_enrolled": int(np.isin(train_y, PEOPLE).sum()),
            "train_other": int((train_y == "OTHER").sum()),
            "val_enrolled": 0,
            "val_other": int(len(other_val_y)),
            "eval_held_out": None if eval_pack is None else int(len(eval_pack[0])),
        },
        "four_sha256": None,
        "source": "phone_tune",
        "phone_warnings": warnings,
        "tune_hashes": phase_file_hashes(root, manifest, "tune"),
        "eval_hashes": phase_file_hashes(root, manifest, "eval"),
        "eval_in_train": False,
        "n_tune": int(len(tune_x)),
    }


def run(vault, data_root, models, run_name, *, phone_tune=False):
    root = verify_vault(vault)
    destination = child(root, "experiments", "identity_four_other", run_name)
    if destination.exists():
        raise FileExistsError("Ese ensayo ya existe.")
    if phone_tune:
        lfw_train, lfw_val, n_people, n_lfw, lfw_names, lfw_samples = load_lfw_hog(
            with_train_identities=True)
        other_train_y = np.full(len(lfw_train), "OTHER")
        other_val_y = np.full(len(lfw_val), "OTHER")
        data = assemble_phone(
            root, lfw_train.astype(np.float32), other_train_y, lfw_samples, lfw_names,
            lfw_val.astype(np.float32), other_val_y)
        data["counts"]["lfw_identities"] = n_people
        data["counts"]["lfw_hog"] = n_lfw
    else:
        data = assemble(root, data_root, models)
    train_x, train_y = data["train"]
    os.environ["KERAS_BACKEND"] = "jax"
    os.environ["JAX_PLATFORMS"] = "cpu"
    import keras
    import jax

    summary = {
        "at_utc": utc_now(),
        "task": "K01_K04_vs_OTHER",
        "classes": list(CLASSES),
        "counts": data["counts"],
        "four_gallery_sha256": data["four_sha256"],
        "source": data.get("source"),
        "eval_in_train": data.get("eval_in_train"),
        "tune_hashes": data.get("tune_hashes"),
        "eval_hashes": data.get("eval_hashes"),
        "not_test": True,
        "live_unchanged": True,
        "simulation": True,
        "versions": {"keras": keras.__version__, "jax": jax.__version__, "numpy": np.__version__},
        "config": {
            "k": K, "seed": SEED, "epochs": EPOCHS, "batch": BATCH,
            "adam_learning_rate": LEARNING_RATE, "l2": L2, "mlp_hidden": HIDDEN,
        },
        "models": {},
    }
    predictions = {}
    destination.mkdir(parents=True)
    summary["gallery_sha256"] = write_gallery(destination / "gallery.npz", train_x, train_y)
    cal_x, cal_y, cal_samples, cal_ids = data["calibration"]
    cal_path = destination / "calibration.npz"
    np.savez(cal_path, vectors=cal_x, labels=cal_y, sample_ids=cal_samples, identity_ids=cal_ids)
    summary["calibration_npz_sha256"] = sha256(cal_path.read_bytes()).hexdigest()
    summary["calibration_n"] = int(len(cal_x))
    for name in ("knn", "mlp", "svm"):
        details = {}
        if name == "knn":
            def predict(vector, gallery=train_x, gallery_y=train_y):
                winner, _ = vote_knn(gallery, gallery_y, vector, k=K)
                return winner if winner in CLASSES else "OTHER"
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=DATA_ROOT)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    parser.add_argument("--run-name", default=RUN)
    parser.add_argument("--phone-tune", action="store_true",
                        help="Entrena con tune del celular más OTHER. No usa eval.")
    args = parser.parse_args()
    summary = run(args.vault, args.data, args.models, args.run_name, phone_tune=args.phone_tune)
    print(json.dumps({
        "winner": summary["winner"],
        "counts": summary["counts"],
        "validation": {name: {key: row["validation"][key] for key in (
            "enrolled_correct", "confused_accepted", "enrolled_as_other",
            "other_as_enrolled", "enrolled_n", "other_n",
        )} for name, row in summary["models"].items()},
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
