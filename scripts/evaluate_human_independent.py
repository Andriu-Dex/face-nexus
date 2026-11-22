"""Comprueba humano/no humano aparte de la identidad. No veta YuNet."""

import argparse
import json
from pathlib import Path

import numpy as np

import cv2

from scripts.capture_manifest import child, utc_now, write_synced
from scripts.dataset_capture import verify_vault
from scripts.face_pipeline import load_detector
from scripts.hog_knn import detect_boxes
from scripts.human_cnn import HUMAN, NONHUMAN, predict_labels, resize_rgb, score
from scripts.live_k01 import HUMAN_RUN, load_keras


def independent_report(true, predicted):
    """Métricas de la CNN sin usarla como identidad ni liveness."""
    row = score(true, predicted)
    row["used_as_identity"] = False
    row["vetoes_yunet"] = False
    row["not_liveness"] = True
    return row


def cifar_nonhuman(limit, seed=17):
    """Test oficial CIFAR-10: objetos, no integrantes."""
    from keras.datasets import cifar10

    _train, (images, _labels) = cifar10.load_data()
    rng = np.random.default_rng(seed)
    n = min(limit, len(images))
    choice = rng.choice(len(images), size=n, replace=False)
    return resize_rgb(images[choice]), np.full(n, NONHUMAN)


def phone_hold_crops(root, detector, hold=5):
    """Recortes YuNet de las últimas fotos del celular, como en el vivo."""
    folder = child(root, "experiments", "hog_phone_adapt", "K01", "k01_phone_v3", "frames")
    paths = sorted(folder.glob("*.png"))
    if len(paths) < hold:
        raise ValueError("Faltan fotogramas del celular para la reserva.")
    images = []
    for path in paths[-hold:]:
        frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if frame is None:
            continue
        boxes = detect_boxes(frame, detector)
        if len(boxes) != 1:
            continue
        left, top, right, bottom, _score = boxes[0]
        images.append(cv2.cvtColor(frame[top:bottom, left:right], cv2.COLOR_BGR2RGB))
    if not images:
        raise ValueError("Ningún recorte YuNet en la reserva del celular.")
    return resize_rgb(images), np.full(len(images), HUMAN)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--run-name", default=HUMAN_RUN)
    parser.add_argument("--cifar-limit", type=int, default=500)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    args = parser.parse_args()
    root = verify_vault(args.vault)
    folder = child(root, "experiments", "human_cnn", args.run_name)
    out = folder / "independent.json"
    if out.exists():
        raise FileExistsError("Esa comprobación independiente ya existe.")
    model = load_keras(folder / "model.keras")
    cifar_x, cifar_y = cifar_nonhuman(args.cifar_limit)
    phone_x, phone_y = phone_hold_crops(root, load_detector(args.models))
    images = np.concatenate([phone_x, cifar_x])
    labels = np.concatenate([phone_y, cifar_y])
    predicted = predict_labels(model, images)
    summary = independent_report(labels, predicted)
    summary["at_utc"] = utc_now()
    summary["run"] = args.run_name
    summary["phone_hold"] = int(len(phone_y))
    summary["cifar_test"] = int(len(cifar_y))
    summary["note"] = "YuNet crops of held-out phone frames plus CIFAR-10 test. Not identity. Not YuNet veto."
    write_synced(out, json.dumps(summary, indent=2, allow_nan=False).encode("utf-8"))
    print(json.dumps({key: summary[key] for key in (
        "n", "accuracy", "human_recall", "nonhuman_recall", "confusion",
        "vetoes_yunet", "used_as_identity")}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
