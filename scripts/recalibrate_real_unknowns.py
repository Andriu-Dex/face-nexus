"""Recalibra T y G con desconocidos reales del aula, además de LFW.

Motivo: LFW es mayoritariamente masculino, y en vivo una compañera desconocida fue aceptada
como K02. Aquí:
- Galería: videos 04 + 06 de cada integrante (más poses e iluminaciones).
- Calibración: (T, G) debe cumplir dos metas a la vez: ≤ 1 % de LFW de ajuste y ≤ 1 % de
  fotogramas de desconocidos reales. Entre los que cumplen, se eligen más aciertos LOO.
- Evaluación honesta: se deja fuera a un desconocido real, se calibra con los demás y se
  mide si a esa persona se le abriría la puerta (racha de CONSENSUS_FRAMES fotogramas
  aceptados seguidos, a ~15 fps). Se repite con cada desconocido.
- Integrantes: video 05, que no entra a la galería, con el mismo criterio de racha.

Variantes: CNN propia sola (w = 1) y fusión con SFace como apoyo (w = 0,75 y 0,5).
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from sklearn.datasets import fetch_lfw_people

from scripts.capture_manifest import child, write_synced
from scripts.capture_phone_train import natural_key, sample_phone_frames
from scripts.compare_identity_k01 import write_gallery
from scripts.dataset_capture import verify_vault
from scripts.face_pipeline import load_models
from scripts.hog_knn import (
    PEOPLE, accepts_open_set, align_detected_face, describe_face_cnn, describe_sface,
    detect_faces, fuse_vectors,
)
from scripts.human_cnn import split_by_identity
from scripts.identity_artifacts import DISTANCE_NAME, FACE_CNN_NAME, file_digest
from scripts.identity_k01 import to_bgr
from scripts.import_frames import spread_indices
from scripts.open_set_knn import (
    _quantiles, genuine_loo_rows, open_set_row, score_known_rows, score_unknown_rows, unknown_rows,
)
from scripts.presentation_gate import CONSENSUS_FRAMES

NAMES = {"K01": "Andriu", "K02": "Maybelline", "K03": "Gabriel", "K04": "Erick"}
WEIGHTS = (1.0, 0.75, 0.5)
TARGET_FAR = 0.01
GALLERY_FRAMES = 70      # por video
REAL_CALIBRATION_FRAMES = 120  # por desconocido real
SEQUENCE_STEP = 2        # videos a ~30 fps → ~15 fps, parecido al vivo
SEQUENCE_LIMIT = 400


def video_dirs(folder):
    return sorted(path for path in folder.iterdir() if path.is_dir() and any(path.glob("*.png")))


def pair(frame, detector, aligner, net):
    """(CNN, SFace) del único rostro, o None si hay 0 o varios o falla alguna parte."""
    faces = detect_faces(frame, detector)
    if len(faces) != 1:
        return None
    left, top, right, bottom, *_ = faces[0]
    cnn = describe_face_cnn(frame[top:bottom, left:right], net)
    aligned = align_detected_face(frame, faces[0], aligner)
    sface = None if aligned is None else describe_sface(aligned, aligner)
    return None if cnn is None or sface is None else (cnn, sface)


def spread_pairs(directory, count, models):
    frames = sample_phone_frames(directory, min(count, len(list(directory.glob("*.png")))))[0]
    return [item for item in (pair(frame, *models) for frame in frames) if item is not None]


def sequence_pairs(directory, models):
    """Fotogramas en orden; None conserva el hueco para que corte la racha."""
    paths = sorted(directory.glob("*.png"), key=natural_key)[::SEQUENCE_STEP][:SEQUENCE_LIMIT]
    return [pair(cv2.imread(str(path)), *models) for path in paths]


def stack(pairs, weight):
    return np.stack([fuse_vectors(cnn, sface, weight) for cnn, sface in pairs])


def longest_streak(accepted):
    best = run = 0
    for value in accepted:
        run = run + 1 if value else 0
        best = max(best, run)
    return best


def sequence_accepts(gallery, labels, sequence, weight, limits, expected=None):
    flags = []
    for item in sequence:
        if item is None:
            flags.append(False)
            continue
        winner, distance, gap = open_set_row(gallery, labels, fuse_vectors(*item, weight))
        ok = accepts_open_set(winner, distance, gap, *limits)
        flags.append(ok and (expected is None or winner == expected))
    return flags


def pick(genuine, lfw_rows, real_rows):
    """Ambas metas de desconocidos; luego más aciertos LOO, menos confusiones, T menor."""
    everything = genuine + lfw_rows + real_rows
    distances = [row[-2] for row in everything]
    gaps = [max(0., row[-1]) for row in everything if row[-1] is not None and np.isfinite(row[-1])]
    best = None
    for max_distance in _quantiles(distances, 40):
        for min_gap in _quantiles(gaps, 24):
            lfw = score_unknown_rows(lfw_rows, max_distance, min_gap)
            real = score_unknown_rows(real_rows, max_distance, min_gap) if real_rows else {"far": 0}
            if lfw["far"] > TARGET_FAR or real["far"] > TARGET_FAR:
                continue
            known = score_known_rows(genuine, max_distance, min_gap)
            key = (known["correct_accepted"], -known["confused_accepted"], -max_distance)
            if best is None or key > best[0]:
                best = (key, float(max_distance), float(min_gap), lfw, real, known)
    if best is None:
        raise ValueError("Ningún (T, G) cumple las dos metas de desconocidos.")
    _, max_distance, min_gap, lfw, real, known = best
    return {"max_distance": max_distance, "min_gap": min_gap, "lfw_calibration": lfw,
            "real_calibration": real, "loo_known": known}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path, help="Carpeta con '<Nombre> 04' y Desconocidos")
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    parser.add_argument("--cnn", required=True, type=Path)
    parser.add_argument("--publish", help="Nombre del candidato a publicar")
    parser.add_argument("--weight", type=float, help="Peso w de la CNN para --publish (1 = CNN sola)")
    args = parser.parse_args()
    if bool(args.publish) != (args.weight is not None):
        parser.error("--publish y --weight van juntos.")
    root = verify_vault(args.vault)
    out = child(root, "experiments", "real_unknown_recalibration.json")
    net = cv2.dnn.readNetFromONNX(str(args.cnn))
    detector, aligner = load_models(args.models)
    models = (detector, aligner, net)

    gallery_pairs, labels = [], []
    known_sequences = {}
    for person, name in NAMES.items():
        for session in ("04", "06"):
            for directory in video_dirs(args.data / f"{name} {session}"):
                found = spread_pairs(directory, GALLERY_FRAMES, models)
                gallery_pairs += found
                labels += [person] * len(found)
        known_sequences[person] = [item for directory in video_dirs(args.data / f"{name} 05")
                                   for item in sequence_pairs(directory, models)]
    labels = np.array(labels)
    print("Integrantes procesados:", {p: int((labels == p).sum()) for p in PEOPLE}, flush=True)

    unknown_dirs = {folder.name: video_dirs(folder)
                    for folder in sorted((args.data / "Desconocidos").iterdir()) if folder.is_dir()}
    real_calibration = {name: [item for d in dirs for item in spread_pairs(d, REAL_CALIBRATION_FRAMES, models)]
                        for name, dirs in unknown_dirs.items()}
    real_sequences = {name: [item for d in dirs for item in sequence_pairs(d, models)]
                      for name, dirs in unknown_dirs.items()}
    print("Desconocidos reales:", {n: len(v) for n, v in real_calibration.items()}, flush=True)

    lfw = fetch_lfw_people(color=True, min_faces_per_person=2, resize=.5, download_if_missing=False)
    lfw_pairs = []
    for mask, count in zip(split_by_identity(lfw.target), (1500, 1000), strict=True):
        indices = np.flatnonzero(mask)
        sample = indices[spread_indices(len(indices), count)]
        frames = (cv2.resize(to_bgr(lfw.images[i]), (188, 250)) for i in sample)
        lfw_pairs.append([item for item in (pair(frame, *models) for frame in frames) if item is not None])

    weights = (args.weight,) if args.publish else WEIGHTS
    result = {"consensus_frames": CONSENSUS_FRAMES, "target_far": TARGET_FAR,
              "gallery_counts": {p: int((labels == p).sum()) for p in PEOPLE}, "variants": {}}
    for weight in weights:
        gallery = stack(gallery_pairs, weight)
        genuine = genuine_loo_rows(gallery, labels)
        lfw_tune = unknown_rows(gallery, labels, stack(lfw_pairs[0], weight))
        lfw_val = stack(lfw_pairs[1], weight)
        real_rows = {name: unknown_rows(gallery, labels, stack(items, weight))
                     for name, items in real_calibration.items()}
        held_out = {}
        for name in real_rows:
            others = [row for other, rows in real_rows.items() if other != name for row in rows]
            chosen = pick(genuine, lfw_tune, others)
            limits = chosen["max_distance"], chosen["min_gap"]
            flags = sequence_accepts(gallery, labels, real_sequences[name], weight, limits)
            held_out[name] = {"max_distance": limits[0], "min_gap": limits[1],
                              "frames": len(flags), "accepted": int(sum(flags)),
                              "longest_streak": longest_streak(flags),
                              "door_would_open": longest_streak(flags) >= CONSENSUS_FRAMES}
        final = pick(genuine, lfw_tune, [row for rows in real_rows.values() for row in rows])
        limits = final["max_distance"], final["min_gap"]
        members = {}
        for person, sequence in known_sequences.items():
            flags = sequence_accepts(gallery, labels, sequence, weight, limits, expected=person)
            members[person] = {"frames": len(flags), "accepted": int(sum(flags)),
                               "longest_streak": longest_streak(flags),
                               "door_would_open": longest_streak(flags) >= CONSENSUS_FRAMES}
        result["variants"][f"w{weight:.2f}"] = {
            "cnn_weight": weight,
            "held_out_unknowns": held_out,
            "final": {**final,
                      "lfw_validation": score_unknown_rows(unknown_rows(gallery, labels, lfw_val), *limits),
                      "members_video_05": members},
        }
        print(f"w={weight}: listo", flush=True)

    payload = json.dumps(result, indent=2, allow_nan=False).encode("utf-8")
    if args.publish:
        folder = child(root, "experiments", "identity_four_other", args.publish)
        if folder.exists():
            raise FileExistsError(folder)
        folder.mkdir()
        write_synced(folder / FACE_CNN_NAME, args.cnn.read_bytes())
        if args.weight == 1:
            # CNN sola: galería de 128, igual que identity_four_phone_04_cnn_run1.
            vectors, preprocessing = np.stack([cnn for cnn, _ in gallery_pairs]), "face_cnn"
        else:
            vectors, preprocessing = stack(gallery_pairs, args.weight), "fusion"
        variant = result["variants"][f"w{args.weight:.2f}"]["final"]
        threshold = {
            "max_distance": variant["max_distance"], "min_gap": variant["min_gap"],
            "cnn_weight": args.weight, "preprocessing": preprocessing,
            "gallery_sha256": write_gallery(folder / "gallery.npz", vectors, labels),
            "face_cnn_sha256": file_digest(folder / FACE_CNN_NAME),
        }
        write_synced(folder / "summary.json", payload)
        write_synced(folder / DISTANCE_NAME, json.dumps(threshold, indent=2).encode("utf-8"))
    else:
        write_synced(out, payload)
    print(payload.decode("utf-8"))


if __name__ == "__main__":
    main()
