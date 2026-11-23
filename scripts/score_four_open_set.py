"""Vuelve a medir VALIDATION de las cuatro identidades con T y G. No usa TEST."""

import argparse
import json
from pathlib import Path

from scripts.capture_manifest import child, utc_now, write_synced
from scripts.dataset_capture import verify_vault
from scripts.face_pipeline import load_detector
from scripts.identity_artifacts import load_verified_knn
from scripts.identity_four import (
    DATA_ROOT, RUN, apply_threshold, extract_split, score_four, sessions_from_record,
)
from scripts.open_set_knn import predict_open_set


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=DATA_ROOT)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    parser.add_argument("--four-run", default=RUN)
    args = parser.parse_args()
    root = verify_vault(args.vault)
    four = child(root, "experiments", "identity_four", args.four_run)
    out = four / "validation_open_set.json"
    if out.exists():
        raise FileExistsError("Esa medición de VALIDATION con T y G ya existe.")
    bundle, reason = load_verified_knn(four)
    if bundle is None:
        raise ValueError(f"Galería de cuatro no verificada: {reason}.")
    summary = json.loads((four / "summary.json").read_text(encoding="utf-8-sig"))
    sessions = sessions_from_record(summary)
    detector = load_detector(args.models)
    val_x, val_y, _ids, missed = extract_split(args.data, detector, "validation", sessions)
    t_only = apply_threshold(
        bundle["vectors"], bundle["labels"], val_x, bundle["max_distance"])
    with_gap = predict_open_set(
        bundle["vectors"], bundle["labels"], val_x,
        bundle["max_distance"], bundle.get("min_gap", 0.))
    row = {
        "at_utc": utc_now(),
        "gallery_sha256": bundle["gallery_sha256"],
        "max_distance": bundle["max_distance"],
        "min_gap": bundle.get("min_gap", 0.),
        "val_n": int(len(val_y)),
        "val_missed": missed,
        "validation_T_only": score_four(val_y, t_only),
        "validation_T_and_G": score_four(val_y, with_gap),
        "note": "Downloads VALIDATION, other encounter. Not TEST. Not phone domain.",
    }
    write_synced(out, json.dumps(row, indent=2, allow_nan=False).encode("utf-8"))
    print(json.dumps({
        "val_n": row["val_n"],
        "max_distance": row["max_distance"],
        "min_gap": row["min_gap"],
        "validation_T_only": row["validation_T_only"],
        "validation_T_and_G": row["validation_T_and_G"],
        "gallery_sha256": row["gallery_sha256"],
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
