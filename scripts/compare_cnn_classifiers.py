"""Compara SVM, Random Forest, k-NN y MLP sobre los vectores de la CNN facial propia.

Mismas entradas y particiones para los cuatro: vectores de 128 de la CNN, video 04 del
celular para entrenar, video 05 para evaluar, rostros LFW como desconocidos.

Se reportan dos cosas por separado:
1. Conjunto cerrado: exactitud, macro-F1 y matriz de confusión en el video 05.
2. Rechazo de desconocidos: cada modelo acepta solo si su confianza supera un umbral.
   El umbral se fija con LFW de ajuste (≤ 1 % de desconocidos aceptados) y se mide en
   LFW de validación, personas distintas. El video 05 nunca participa en ese ajuste.
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from sklearn.datasets import fetch_lfw_people
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

from scripts.capture_manifest import child, write_synced
from scripts.compare_aligned_phone import collect, evaluate as evaluate_knn_rule, phone_data
from scripts.compare_classifiers import build_models
from scripts.dataset_capture import verify_vault
from scripts.face_pipeline import load_models
from scripts.hog_knn import PEOPLE
from scripts.human_cnn import split_by_identity
from scripts.identity_k01 import to_bgr
from scripts.import_frames import spread_indices

TARGET_UNKNOWN_RATE = 0.01


def confidence(model, vectors):
    """Confianza de la clase ganadora: margen del SVM o probabilidad en los demás."""
    if hasattr(model, "predict_proba"):
        return model.predict_proba(vectors).max(axis=1)
    return model.decision_function(vectors).max(axis=1)


def pick_threshold(unknown_scores, target=TARGET_UNKNOWN_RATE):
    """Menor umbral que deja pasar como mucho `target` de los desconocidos de ajuste."""
    ordered = np.sort(unknown_scores)[::-1]
    allowed = int(np.floor(target * len(ordered)))
    # Aceptar exige score > umbral, así que solo pasan los `allowed` más altos.
    return float(ordered[allowed]) if allowed < len(ordered) else float(ordered[-1])


def open_set_scores(model, threshold, test, expected, unknown):
    predicted = model.predict(test)
    accepted = confidence(model, test) > threshold
    unknown_accepted = confidence(model, unknown) > threshold
    return {
        "threshold": threshold,
        "known_correct_accepted": int((accepted & (predicted == expected)).sum()),
        "known_confused_accepted": int((accepted & (predicted != expected)).sum()),
        "known_rejected": int((~accepted).sum()),
        "known_total": len(expected),
        "unknown_accepted": int(unknown_accepted.sum()),
        "unknown_total": len(unknown),
        "unknown_acceptance_rate": float(unknown_accepted.mean()),
    }


def compare(gallery, labels, test, expected, tune_unknown, test_unknown):
    results = {}
    for name, model in build_models().items():
        model.fit(gallery, labels)
        predicted = model.predict(test)
        threshold = pick_threshold(confidence(model, tune_unknown))
        results[name] = {
            "closed_set_accuracy": float(accuracy_score(expected, predicted)),
            "closed_set_macro_f1": float(f1_score(expected, predicted, average="macro")),
            "confusion_rows_actual": confusion_matrix(expected, predicted, labels=PEOPLE).tolist(),
            "open_set": open_set_scores(model, threshold, test, expected, test_unknown),
        }
    return results


def lfw_unknowns(detector, aligner, cnn):
    lfw = fetch_lfw_people(color=True, min_faces_per_person=2, resize=.5, download_if_missing=False)
    groups = []
    for mask, count in zip(split_by_identity(lfw.target), (1500, 1000), strict=True):
        indices = np.flatnonzero(mask)
        sample = indices[spread_indices(len(indices), count)]
        frames = (cv2.resize(to_bgr(lfw.images[i]), (188, 250)) for i in sample)
        groups.append(collect(frames, detector, aligner, cnn=cnn)[-1])
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    parser.add_argument("--cnn", required=True, type=Path, help="ONNX de la CNN facial elegida")
    parser.add_argument("--tune", nargs=4, type=Path, required=True, help="Video 04, orden K01–K04")
    parser.add_argument("--eval", nargs=4, type=Path, required=True, help="Video 05, orden K01–K04")
    parser.add_argument("--output", default="cnn_classifier_comparison.json")
    args = parser.parse_args()
    root = verify_vault(args.vault)
    out = child(root, "experiments", args.output)
    if out.exists():
        raise FileExistsError(out)
    cnn = cv2.dnn.readNetFromONNX(str(args.cnn))
    detector, aligner = load_models(args.models)
    # La última columna de phone_data/collect es la de la CNN.
    columns, labels = phone_data(args.tune, 70, detector, aligner, cnn=cnn)
    gallery = columns[-1]
    columns, expected = phone_data(args.eval, 20, detector, aligner, cnn=cnn)
    test = columns[-1]
    print("Celular procesado. Procesando desconocidos LFW.", flush=True)
    tune_unknown, test_unknown = lfw_unknowns(detector, aligner, cnn)
    result = {
        "extractor": args.cnn.name,
        "train_counts": {person: int((labels == person).sum()) for person in PEOPLE},
        "eval_counts": {person: int((expected == person).sum()) for person in PEOPLE},
        "unknown_counts": {"tune": len(tune_unknown), "validation": len(test_unknown)},
        "target_unknown_rate": TARGET_UNKNOWN_RATE,
        "classifiers": compare(gallery, labels, test, expected, tune_unknown, test_unknown),
        # Regla desplegada: k-NN k=3 con distancia máxima T y holgura G (open_set_knn).
        "deployed_knn_distance_rule": evaluate_knn_rule(
            gallery, labels, tune_unknown, test_unknown, test, expected),
    }
    payload = json.dumps(result, indent=2, allow_nan=False).encode("utf-8")
    write_synced(out, payload)
    print(payload.decode("utf-8"))


if __name__ == "__main__":
    main()
