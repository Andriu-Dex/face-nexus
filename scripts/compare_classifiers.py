"""Compara cuatro clasificadores conocidos con TRAIN y VALIDATION."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import time
import warnings

import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import normalize
from sklearn.svm import SVC
from threadpoolctl import threadpool_limits

from scripts.capture_manifest import child, load_schedule, read_json, write_synced
from scripts.dataset_capture import PROJECT, verify_vault


PEOPLE = ("K01", "K02", "K03", "K04")
SEED = 17


def read_features(path):
    with np.load(path, allow_pickle=False) as dataset:
        return {key: dataset[key] for key in ("vectors", "labels", "sample_ids")}


def validate_features(dataset, historical=False):
    vectors, labels, sample_ids = (dataset[key] for key in ("vectors", "labels", "sample_ids"))
    if (vectors.ndim != 2 or vectors.shape[1] != 128 or vectors.dtype.kind != "f"
            or labels.shape != (len(vectors),) or sample_ids.shape != labels.shape
            or labels.dtype.kind != "U" or sample_ids.dtype.kind != "U"):
        raise ValueError("Se requieren vectores faciales, etiquetas e IDs coherentes.")
    if set(labels) != set(PEOPLE) or len(set(sample_ids)) != len(sample_ids):
        raise ValueError("Cada lote debe tener las cuatro identidades y muestras únicas.")
    norms = np.linalg.norm(vectors.astype(np.float64), axis=1)
    if not np.isfinite(norms).all() or (norms == 0).any():
        raise ValueError("Los vectores deben ser finitos y de norma positiva.")
    sessions = set()
    for label, sample in zip(labels, sample_ids, strict=True):
        match = re.fullmatch(r"(K0[1-4])_(S[0-9]{2,})_[A-Za-z0-9_]+", sample)
        if match is None or match[1] != label or (match[2] == "S01") != historical:
            raise ValueError("La identidad o sesión de la muestra no coincide con el lote.")
        sessions.add((match[1], match[2]))
    return sessions


def evaluate(train, validation):
    # L2 divide cada vector por su propia norma; no aprende de VALIDATION.
    x_train = normalize(train["vectors"].astype(np.float64))
    x_validation = normalize(validation["vectors"].astype(np.float64))
    models = {
        "SVM": SVC(C=1, kernel="rbf"),
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=SEED, n_jobs=1),
        "k-NN": KNeighborsClassifier(n_neighbors=3, n_jobs=1),
        "MLP": MLPClassifier(hidden_layer_sizes=(32,), solver="lbfgs", max_iter=400,
                             random_state=SEED),
    }
    results = {}
    with threadpool_limits(limits=1):
        for name, model in models.items():
            start = time.perf_counter()
            with warnings.catch_warnings(record=True) as notices:
                warnings.simplefilter("always")
                model.fit(x_train, train["labels"])
            training_ms = (time.perf_counter() - start) * 1000
            train_prediction = model.predict(x_train)
            start = time.perf_counter()
            prediction = model.predict(x_validation)
            validation_ms = (time.perf_counter() - start) * 1000
            results[name] = {
                "parameters": model.get_params(),
                "training_ms": training_ms,
                "validation_prediction_ms_batch": validation_ms,
                "warnings": [f"{warning.category.__name__}: {warning.message}" for warning in notices],
                "train_accuracy": accuracy_score(train["labels"], train_prediction),
                "validation_accuracy": accuracy_score(validation["labels"], prediction),
                "validation_macro_f1": f1_score(validation["labels"], prediction, average="macro"),
                "validation_by_identity": {
                    label: metrics for label, metrics in classification_report(
                        validation["labels"], prediction, labels=PEOPLE, output_dict=True,
                        zero_division=0,
                    ).items() if label in PEOPLE
                },
                "validation_confusion_rows_actual": confusion_matrix(
                    validation["labels"], prediction, labels=PEOPLE,
                ).tolist(),
            }
    return results


def verify_partition(dataset, schedule, split):
    for person, session in validate_features(dataset):
        key = f"{person}_{session}"
        if key not in schedule or schedule[key]["split"] != split:
            raise ValueError(f"La sesión {key} no pertenece a {split} en el plan privado.")


def read_session_features(path, schedule, split):
    dataset = read_features(path)
    verify_partition(dataset, schedule, split)
    evidence = read_json(child(path.parent, "records.json"))
    records = evidence["records"]
    if (evidence["split"] != split
            or [row["sample_id"] for row in records if row["status"] == "ok"]
            != dataset["sample_ids"].tolist()):
        raise ValueError("El lote y su registro de extracción no coinciden.")
    sources = {row["video_sha256"] for row in records}
    frames = {row["image_sha256"] for row in records}
    return dataset, sources, frames, evidence["statuses"]


def compare(train, validation, historical=None):
    train_sessions = validate_features(train)
    validation_sessions = validate_features(validation)
    if train_sessions & validation_sessions:
        raise ValueError("TRAIN y VALIDATION comparten una sesión.")
    validation_vectors = {row.tobytes() for row in validation["vectors"].astype(np.float64)}
    conditions = {"new_train": train}
    if historical is not None:
        validate_features(historical, historical=True)
        conditions["new_train_plus_s01"] = {
            key: np.concatenate((train[key], historical[key])) for key in train
        }
    for batch in conditions.values():
        if any(row.tobytes() in validation_vectors for row in batch["vectors"].astype(np.float64)):
            raise ValueError("Se encontraron vectores idénticos en TRAIN y VALIDATION.")
    return {
        "identity_order": PEOPLE, "normalization": "L2 por vector", "seed": SEED,
        "sklearn_version": sklearn.__version__, "numpy_version": np.__version__,
        "validation_samples": len(validation["labels"]),
        "conditions": {name: {"train_samples": len(batch["labels"]),
                              "classifiers": evaluate(batch, validation)}
                       for name, batch in conditions.items()},
    }


def synthetic_features():
    rng = np.random.default_rng(SEED)
    centers = rng.normal(0, .38, (len(PEOPLE), 128))
    for session in ("S02", "S03", "S01"):
        vectors, labels, ids = [], [], []
        for label, center in zip(PEOPLE, centers, strict=True):
            shift = rng.normal(0, .25, 128)
            for number in range(12):
                vectors.append(center + shift + rng.normal(0, 1, 128))
                labels.append(label)
                ids.append(f"{label}_{session}_{number:04d}")
        yield {"vectors": np.array(vectors), "labels": np.array(labels), "sample_ids": np.array(ids)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--vault", type=Path, help="Raíz verificada de VeraCrypt para datos reales.")
    parser.add_argument("--train", help="NPZ relativo al volumen con sesiones TRAIN nuevas.")
    parser.add_argument("--validation", help="NPZ relativo al volumen con sesiones VALIDATION nuevas.")
    parser.add_argument("--historical", help="NPZ opcional relativo al volumen, solo S01.")
    parser.add_argument("--output", required=True, help="JSON relativo a la raíz de salida.")
    args = parser.parse_args()
    try:
        if args.synthetic:
            if any((args.vault, args.train, args.validation, args.historical)):
                raise ValueError("El modo sintético genera todos sus datos localmente.")
            output = child(child(PROJECT, "outputs"), args.output)
            train, validation, historical = synthetic_features()
            inputs = {}
            source = "synthetic"
        else:
            if not all((args.vault, args.train, args.validation)):
                raise ValueError("Indica el volumen y los archivos de TRAIN y VALIDATION.")
            vault = verify_vault(args.vault)
            output = child(vault, args.output)
            paths = {"train": child(vault, args.train), "validation": child(vault, args.validation)}
            if args.historical:
                paths["historical"] = child(vault, args.historical)
            inputs = {name: sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}
            schedule = load_schedule(child(vault, "plan.json"), child(vault, "sessions"))
            train, train_sources, train_frames, train_statuses = read_session_features(
                paths["train"], schedule, "TRAIN",
            )
            validation, validation_sources, validation_frames, validation_statuses = read_session_features(
                paths["validation"], schedule, "VALIDATION",
            )
            if train_sources & validation_sources or train_frames & validation_frames:
                raise ValueError("TRAIN y VALIDATION comparten fuentes o imágenes idénticas.")
            historical = read_features(paths["historical"]) if args.historical else None
            source = "camera_embeddings"
        if output.suffix != ".json" or output.exists():
            raise ValueError("La salida debe ser un JSON nuevo.")
        result = {"source": source, "input_sha256": inputs, **compare(train, validation, historical)}
        if not args.synthetic:
            result["extraction_statuses"] = {"train": train_statuses, "validation": validation_statuses}
        output.parent.mkdir(parents=True, exist_ok=True)
        write_synced(output, json.dumps(result, indent=2, allow_nan=False).encode("utf-8"))
        print(f"Comparación {source} guardada en {output.name}.")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Comparación detenida: {exc}\n")


if __name__ == "__main__":
    main()
