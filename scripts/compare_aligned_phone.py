"""Compara HOG de caja y alineado con los mismos rostros y particiones."""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from sklearn.datasets import fetch_lfw_people

from scripts.capture_manifest import child, write_synced
from scripts.capture_phone_train import sample_phone_frames
from scripts.face_pipeline import load_models
from scripts.hog_knn import (
    PEOPLE, align_detected_face, describe_face, describe_face_cnn, describe_sface, detect_faces,
)
from scripts.compare_identity_k01 import write_gallery
from scripts.identity_artifacts import DISTANCE_NAME, FACE_CNN_NAME, file_digest
from scripts.human_cnn import split_by_identity
from scripts.identity_k01 import to_bgr
from scripts.import_frames import spread_indices
from scripts.open_set_knn import (
    genuine_loo_rows, open_set_row, pick_operating_point, score_known_rows,
    score_unknown_rows, unknown_rows,
)
from scripts.dataset_capture import verify_vault


def paired_features(frame, detector, aligner, *, include_sface=False, cnn=None):
    faces = detect_faces(frame, detector)
    if len(faces) != 1:
        return None
    left, top, right, bottom, *_ = faces[0]
    normalized = align_detected_face(frame, faces[0], aligner)
    if normalized is None:
        return None
    cropped = describe_face(frame[top:bottom, left:right])
    aligned = describe_face(normalized)
    if cropped is None or aligned is None:
        return None
    columns = [cropped, aligned]
    if include_sface:
        columns.append(describe_sface(normalized, aligner))
    if cnn is not None:
        # Misma caja YuNet sin alinear que HOG y que el vivo.
        columns.append(describe_face_cnn(frame[top:bottom, left:right], cnn))
    if any(column is None for column in columns):
        return None
    return tuple(columns)


def collect(frames, detector, aligner, *, include_sface=False, cnn=None):
    pairs = []
    for frame in frames:
        pair = paired_features(frame, detector, aligner, include_sface=include_sface, cnn=cnn)
        if pair is not None:
            pairs.append(pair)
    if not pairs:
        raise ValueError("No hay pares de características utilizables.")
    return tuple(np.stack(columns) for columns in zip(*pairs, strict=True))


def phone_data(directories, count, detector, aligner, *, include_sface=False, cnn=None):
    groups = [collect(sample_phone_frames(path, count)[0], detector, aligner,
                      include_sface=include_sface, cnn=cnn)
              for path in directories]
    labels = np.concatenate([np.repeat(person, len(group[0]))
                             for person, group in zip(PEOPLE, groups, strict=True)])
    return tuple(np.concatenate(columns) for columns in zip(*groups, strict=True)), labels


def evaluate(gallery, labels, tune_unknown, test_unknown, test, expected):
    chosen = pick_operating_point(genuine_loo_rows(gallery, labels),
                                  unknown_rows(gallery, labels, tune_unknown))
    limits = chosen["max_distance"], chosen["min_gap"]
    rows = [(person, *open_set_row(gallery, labels, vector))
            for person, vector in zip(expected, test, strict=True)]
    return {
        **chosen,
        "unknown_validation": score_unknown_rows(unknown_rows(gallery, labels, test_unknown), *limits),
        "phone_eval_exploratory": {
            person: score_known_rows([row for row in rows if row[0] == person], *limits)
            for person in PEOPLE
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    parser.add_argument("--tune", nargs=4, type=Path, required=True, help="PNG 04 en orden K01–K04")
    parser.add_argument("--eval", nargs=4, type=Path, required=True, help="PNG 05 en orden K01–K04")
    parser.add_argument("--publish", help="Nombre nuevo del candidato alineado o SFace")
    parser.add_argument("--compare-sface", action="store_true", help="Incluye embeddings SFace normalizados.")
    parser.add_argument("--cnn", type=Path, help="ONNX de la CNN propia (export_face_cnn.py)")
    args = parser.parse_args()
    root = verify_vault(args.vault)
    cnn = cv2.dnn.readNetFromONNX(str(args.cnn)) if args.cnn else None
    if args.cnn:
        report = f"phone_cnn_comparison_{args.cnn.stem}.json"
    elif args.compare_sface:
        report = "phone_sface_comparison.json"
    else:
        report = "phone_alignment_comparison.json"
    out = child(root, "experiments", report)
    if out.exists() and not args.publish:
        raise FileExistsError(out)
    if args.publish:
        folder = child(root, "experiments", "identity_four_other", args.publish)
        if folder.exists():
            raise FileExistsError(folder)
    detector, aligner = load_models(args.models)
    options = {"include_sface": args.compare_sface, "cnn": cnn}
    gallery, labels = phone_data(args.tune, 70, detector, aligner, **options)
    test, expected = phone_data(args.eval, 20, detector, aligner, **options)
    print("Capturas del celular procesadas. Procesando desconocidos LFW.", flush=True)
    lfw = fetch_lfw_people(color=True, min_faces_per_person=2, resize=.5, download_if_missing=False)
    train_mask, val_mask = split_by_identity(lfw.target)
    unknown = []
    for mask, count in ((train_mask, 1500), (val_mask, 1000)):
        indices = np.flatnonzero(mask)
        sample = indices[spread_indices(len(indices), count)]
        unknown.append(collect((cv2.resize(to_bgr(lfw.images[i]), (188, 250)) for i in sample),
                               detector, aligner, **options))
    methods = ("box_hog", "aligned_hog") + (("sface",) if args.compare_sface else ()) + (
        ("face_cnn",) if cnn is not None else ())
    result = {
        "train_counts": {person: int((labels == person).sum()) for person in PEOPLE},
        **{
            name: evaluate(gallery[i], labels, unknown[0][i], unknown[1][i], test[i], expected)
            for i, name in enumerate(methods)
        },
    }
    payload = json.dumps(result, indent=2, allow_nan=False).encode("utf-8")
    if args.publish:
        method = "face_cnn" if cnn is not None else "sface" if args.compare_sface else "aligned_hog"
        folder.mkdir()
        if method == "face_cnn":
            # El candidato lleva su propia red; la galería solo vale con estos pesos.
            write_synced(folder / FACE_CNN_NAME, args.cnn.read_bytes())
        threshold = {
            **result[method],
            "gallery_sha256": write_gallery(folder / "gallery.npz", gallery[methods.index(method)], labels),
            "preprocessing": method,
        }
        if method == "face_cnn":
            threshold["face_cnn_sha256"] = file_digest(folder / FACE_CNN_NAME)
        write_synced(folder / "summary.json", payload)
        write_synced(folder / DISTANCE_NAME, json.dumps(threshold, indent=2).encode("utf-8"))
    else:
        write_synced(out, payload)
    print(payload.decode("utf-8"))


if __name__ == "__main__":
    main()
