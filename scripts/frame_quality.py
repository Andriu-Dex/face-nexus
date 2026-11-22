"""Nitidez y exposición del recorte. Umbrales a partir de fotos propias, no copiados."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

from scripts.capture_manifest import child, utc_now, write_synced
from scripts.dataset_capture import verify_vault
from scripts.evaluate_hog_knn import MANIFEST_FOLDER, validate_manifest
from scripts.face_pipeline import describe, load_detector, crop_quality
from scripts.hog_knn import detect_boxes
from scripts.identity_k01 import PHONE, PHONE_HOLD


# Umbral que circula en apuntes; aquí solo se cuenta cuántas caras propias lo incumplirían.
COPIED_LAPLACIAN = 85.


def quality_flags(row, floors, *, check_size=True):
    """Aviso, no descarte. El lado mínimo no se cruza entre cámaras distintas."""
    flags = []
    if row["laplacian_var"] < floors["laplacian_var"]:
        flags.append("blur")
    if row["dark_fraction"] > floors["dark_fraction"]:
        flags.append("underexposed")
    if row["bright_fraction"] > floors["bright_fraction"]:
        flags.append("overexposed")
    if check_size and min(row["width_px"], row["height_px"]) < floors["min_side_px"]:
        flags.append("small_box")
    return flags


def floors_from_rows(rows):
    """Pisos del lote: p05 de nitidez y lado; p95 de colas. No es el mínimo (tautológico)."""
    if not rows:
        raise ValueError("No hay recortes usables para fijar pisos.")
    laplacian = [row["laplacian_var"] for row in rows]
    dark = [row["dark_fraction"] for row in rows]
    bright = [row["bright_fraction"] for row in rows]
    sides = [min(row["width_px"], row["height_px"]) for row in rows]
    return {
        "laplacian_var": float(np.percentile(laplacian, 5, method="lower")),
        "dark_fraction": float(np.percentile(dark, 95, method="higher")),
        "bright_fraction": float(np.percentile(bright, 95, method="higher")),
        "min_side_px": int(np.percentile(sides, 5, method="lower")),
        "n": len(rows),
        "copied_laplacian": COPIED_LAPLACIAN,
        "below_copied_laplacian": int(sum(value < COPIED_LAPLACIAN for value in laplacian)),
    }


def measure_crop_from_frame(frame, detector):
    boxes = detect_boxes(frame, detector)
    if len(boxes) != 1:
        return None
    left, top, right, bottom, _score = boxes[0]
    row = crop_quality(frame[top:bottom, left:right])
    if row is None:
        return None
    row["box"] = [left, top, right, bottom]
    return row


def load_phone_frames(root):
    folder = child(root, *PHONE[:-1], "frames")
    paths = sorted(folder.glob("K01_PHONE_*.png"))
    frames = []
    for path in paths:
        frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError(f"No se pudo leer {path.name}.")
        frames.append((path.name, frame))
    return frames


def load_s01_k01_frames(root):
    folder = child(root, *MANIFEST_FOLDER)
    manifest = json.loads(child(folder, "manifest.json").read_bytes().decode("utf-8-sig"))
    validate_manifest(manifest)
    frames = []
    for row in manifest["train"]:
        if row["person_id"] != "K01":
            continue
        payload = child(root, *Path(row["image"]).parts).read_bytes()
        if sha256(payload).hexdigest() != row["image_sha256"]:
            raise ValueError("El hash de un fotograma S01 no coincide.")
        frame = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)
        if frame is not None:
            frames.append((row["sample_id"], frame))
    return frames


def collect(name, pairs, detector):
    rows = []
    missed = 0
    for sample, frame in pairs:
        row = measure_crop_from_frame(frame, detector)
        if row is None:
            missed += 1
            continue
        row["sample_id"] = sample
        rows.append(row)
    metrics = {
        "laplacian_var": describe([row["laplacian_var"] for row in rows]),
        "mean": describe([row["mean"] for row in rows]),
        "dark_fraction": describe([row["dark_fraction"] for row in rows]),
        "bright_fraction": describe([row["bright_fraction"] for row in rows]),
        "min_side_px": describe([min(row["width_px"], row["height_px"]) for row in rows]),
    }
    return {"source": name, "n": len(rows), "no_unique_face": missed, "metrics": metrics, "rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    parser.add_argument("--run-name", default="frame_quality_v2")
    args = parser.parse_args()
    root = verify_vault(args.vault)
    folder = child(root, "experiments", "frame_quality", args.run_name)
    if folder.exists():
        raise FileExistsError("Ese ensayo ya existe.")
    detector = load_detector(args.models)
    phone = collect("k01_phone_v3", load_phone_frames(root), detector)
    s01 = collect("s01_k01", load_s01_k01_frames(root), detector)
    floors = floors_from_rows(phone["rows"])
    summary = {
        "at_utc": utc_now(),
        "task": "capture_quality_from_own_crops",
        "phone_hold": PHONE_HOLD,
        "floors_from_phone": floors,
        "phone": {key: phone[key] for key in ("n", "no_unique_face", "metrics")},
        "s01_k01": {key: s01[key] for key in ("n", "no_unique_face", "metrics")},
        "s01_below_phone_exposure_floors": int(
            sum(bool(quality_flags(row, floors, check_size=False)) for row in s01["rows"])),
        "phone_below_own_floors": int(sum(bool(quality_flags(row, floors)) for row in phone["rows"])),
        "note": "Los pisos avisan en capturas nuevas del mismo montaje. No se borra TRAIN ni se veta el vivo.",
    }
    compact = []
    for row in phone["rows"]:
        compact.append({
            "sample_id": row["sample_id"],
            "source": "phone",
            "laplacian_var": row["laplacian_var"],
            "mean": row["mean"],
            "dark_fraction": row["dark_fraction"],
            "bright_fraction": row["bright_fraction"],
            "width_px": row["width_px"],
            "height_px": row["height_px"],
            "flags": quality_flags(row, floors),
        })
    for row in s01["rows"]:
        compact.append({
            "sample_id": row["sample_id"],
            "source": "s01",
            "laplacian_var": row["laplacian_var"],
            "mean": row["mean"],
            "dark_fraction": row["dark_fraction"],
            "bright_fraction": row["bright_fraction"],
            "width_px": row["width_px"],
            "height_px": row["height_px"],
            "flags": quality_flags(row, floors, check_size=False),
        })
    folder.mkdir(parents=True)
    write_synced(folder / "summary.json", json.dumps(summary, indent=2, allow_nan=False).encode("utf-8"))
    write_synced(folder / "crops.json", json.dumps(compact, indent=2, allow_nan=False).encode("utf-8"))
    print(json.dumps({
        "floors_from_phone": floors,
        "phone_laplacian": phone["metrics"]["laplacian_var"],
        "phone_dark": phone["metrics"]["dark_fraction"],
        "phone_bright": phone["metrics"]["bright_fraction"],
        "s01_laplacian": s01["metrics"]["laplacian_var"],
        "s01_min_side": s01["metrics"]["min_side_px"],
        "s01_dark": s01["metrics"]["dark_fraction"],
        "s01_below_phone_exposure_floors": summary["s01_below_phone_exposure_floors"],
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
