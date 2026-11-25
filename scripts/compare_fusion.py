"""Ablación: CNN propia sola, SFace solo y su fusión con distintos pesos.

Vector fusionado = [√w · CNN, √(1−w) · SFace], con cada parte ya normalizada a norma 1.
Así la distancia al cuadrado es w·d²_CNN + (1−w)·d²_SFace: w es el peso de la CNN propia.
Cada variante recibe su propio T y G con LFW de ajuste y se mide con LFW de validación
(otras personas) y con el video 05. Mismos fotogramas para todas las variantes.
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from sklearn.datasets import fetch_lfw_people

from scripts.capture_manifest import child, write_synced
from scripts.compare_aligned_phone import collect, evaluate, phone_data
from scripts.compare_identity_k01 import write_gallery
from scripts.dataset_capture import verify_vault
from scripts.face_pipeline import load_models
from scripts.hog_knn import PEOPLE, fuse_vectors as fuse
from scripts.human_cnn import split_by_identity
from scripts.identity_artifacts import DISTANCE_NAME, FACE_CNN_NAME, file_digest
from scripts.identity_k01 import to_bgr
from scripts.import_frames import spread_indices

WEIGHTS = (1.0, 0.75, 0.5, 0.25, 0.0)




def variant_name(weight):
    return {1.0: "cnn_only", 0.0: "sface_only"}.get(weight, f"fusion_w{weight:.2f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    parser.add_argument("--cnn", required=True, type=Path)
    parser.add_argument("--tune", nargs=4, type=Path, required=True, help="Video 04, orden K01–K04")
    parser.add_argument("--eval", nargs=4, type=Path, required=True, help="Video 05, orden K01–K04")
    parser.add_argument("--publish", help="Nombre del candidato fusionado a publicar")
    parser.add_argument("--weight", type=float, help="Peso w de la CNN para --publish")
    args = parser.parse_args()
    if bool(args.publish) != (args.weight is not None) or (
            args.weight is not None and not 0 < args.weight < 1):
        parser.error("--publish requiere --weight entre 0 y 1 (exclusivo).")
    root = verify_vault(args.vault)
    out = child(root, "experiments", "fusion_ablation.json")
    if args.publish:
        folder = child(root, "experiments", "identity_four_other", args.publish)
        if folder.exists():
            raise FileExistsError(folder)
    elif out.exists():
        raise FileExistsError(out)
    cnn = cv2.dnn.readNetFromONNX(str(args.cnn))
    detector, aligner = load_models(args.models)
    options = {"include_sface": True, "cnn": cnn}
    # Columnas: box_hog, aligned_hog, sface, cnn.
    train, labels = phone_data(args.tune, 70, detector, aligner, **options)
    test, expected = phone_data(args.eval, 20, detector, aligner, **options)
    print("Celular procesado. Procesando desconocidos LFW.", flush=True)
    lfw = fetch_lfw_people(color=True, min_faces_per_person=2, resize=.5, download_if_missing=False)
    unknown = []
    for mask, count in zip(split_by_identity(lfw.target), (1500, 1000), strict=True):
        indices = np.flatnonzero(mask)
        sample = indices[spread_indices(len(indices), count)]
        unknown.append(collect((cv2.resize(to_bgr(lfw.images[i]), (188, 250)) for i in sample),
                               detector, aligner, **options))
    weights = (args.weight,) if args.publish else WEIGHTS
    result = {"train_counts": {person: int((labels == person).sum()) for person in PEOPLE}}
    for weight in weights:
        fused = [fuse(group[3], group[2], weight) for group in (train, test, *unknown)]
        result[variant_name(weight)] = {
            "cnn_weight": weight,
            **evaluate(fused[0], labels, fused[2], fused[3], fused[1], expected),
        }
    payload = json.dumps(result, indent=2, allow_nan=False).encode("utf-8")
    if args.publish:
        folder.mkdir()
        write_synced(folder / FACE_CNN_NAME, args.cnn.read_bytes())
        record = result[variant_name(args.weight)]
        threshold = {
            **record,
            "gallery_sha256": write_gallery(folder / "gallery.npz",
                                            fuse(train[3], train[2], args.weight), labels),
            "preprocessing": "fusion",
            "face_cnn_sha256": file_digest(folder / FACE_CNN_NAME),
        }
        write_synced(folder / "summary.json", payload)
        write_synced(folder / DISTANCE_NAME, json.dumps(threshold, indent=2).encode("utf-8"))
    else:
        write_synced(out, payload)
    print(payload.decode("utf-8"))


if __name__ == "__main__":
    main()
