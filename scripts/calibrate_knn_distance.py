"""Fija T de k-NN con VALIDATION (celular + LFW). No usa TEST ni inventa K02–K04."""

import argparse
import json
from pathlib import Path

from scripts.capture_manifest import child, utc_now, write_synced
from scripts.compare_identity_k01 import (
    GALLERY_NAME, assemble, knn_max_distance, load_gallery,
)
from scripts.dataset_capture import verify_vault


COMPARE_RUN = "identity_k01_compare_v1"
DISTANCE_NAME = "knn_max_distance.json"
SLACK = 1.1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--run-name", default=COMPARE_RUN)
    parser.add_argument("--slack", type=float, default=SLACK)
    args = parser.parse_args()
    if args.slack < 1:
        parser.error("La holgura debe ser >= 1.")
    root = verify_vault(args.vault)
    folder = child(root, "experiments", "identity_k01", args.run_name)
    path = child(folder, DISTANCE_NAME)
    if path.exists():
        raise FileExistsError("Ese umbral ya existe.")
    gallery, labels = load_gallery(folder / GALLERY_NAME)
    val_x, val_y = assemble(root)["validation"]
    row = knn_max_distance(gallery, labels, val_x, val_y, slack=args.slack)
    row["at_utc"] = utc_now()
    row["gallery"] = GALLERY_NAME
    write_synced(path, json.dumps(
        {key: row[key] for key in row if key != "impostor_distances"},
        indent=2, allow_nan=False,
    ).encode("utf-8"))
    print(json.dumps({
        "max_distance": row["max_distance"],
        "raw_max_k01_val": row["raw_max_k01_val"],
        "lfw_as_k01_before": row["lfw_as_k01_before"],
        "lfw_as_k01_after": row["lfw_as_k01_after"],
        "path": str(path),
    }, indent=2))


if __name__ == "__main__":
    main()
