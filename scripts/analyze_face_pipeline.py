"""Análisis y figuras locales; no ajusta umbrales ni clasifica personas."""

import argparse
from collections import defaultdict
import json
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from scripts.face_pipeline import describe, private_path, write_png


def review_sheets(records, root, output):
    """Láminas privadas de detección y alineación, sin nombres personales."""
    for person in sorted({record["person_id"] for record in records}):
        rows = [record for record in records if record["person_id"] == person]
        canvas = np.full((4 * 210, 5 * 360, 3), 235, np.uint8)
        for index, record in enumerate(rows):
            x, y = (index % 5) * 360, (index // 5) * 210
            name = record["sample_id"] + ".png"
            image = cv2.imdecode(np.frombuffer((root / "detections" / name).read_bytes(), np.uint8), cv2.IMREAD_COLOR)
            thumb = cv2.resize(image, (240, round(image.shape[0] * 240 / image.shape[1])))
            canvas[y + 28:y + 28 + thumb.shape[0], x:x + 240] = thumb
            aligned = root / "aligned" / name
            if aligned.exists():
                crop = cv2.imdecode(np.frombuffer(aligned.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
                canvas[y + 28:y + 140, x + 244:x + 356] = crop
            cv2.putText(canvas, f"{index+1:02d} {record['status']}", (x + 5, y + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 0), 1)
            cv2.putText(canvas, record["sample_id"][8:], (x + 4, y + 188),
                        cv2.FONT_HERSHEY_SIMPLEX, .42, (0, 0, 0), 1)
        write_png(output / f"review_{person}.png", canvas)


def analyze(root, allowed_root):
    root = private_path(root, allowed_root)
    output = root / "analysis"
    output.mkdir(exist_ok=False)
    records = json.loads((root / "records.json").read_text(encoding="utf-8"))
    with np.load(root / "embeddings.npz", allow_pickle=False) as data:
        vectors, labels, ids = data["vectors"], data["labels"], data["sample_ids"]
    matrix = np.load(root / "similarity.npy", allow_pickle=False)
    triangle = np.triu(np.ones(matrix.shape, bool), 1)
    same = labels[:, None] == labels[None, :]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bins = np.linspace(-.15, 1, 35)
    ax.hist(matrix[triangle & same], bins=bins, density=True, histtype="step", linewidth=2,
            label="Misma identidad (desarrollo)")
    ax.hist(matrix[triangle & ~same], bins=bins, density=True, histtype="step", linewidth=2,
            label="Identidades distintas (desarrollo)")
    ax.set(xlabel="Similitud coseno", ylabel="Densidad", title="Pares relacionados; no evaluación independiente")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "similarity_distributions.png", dpi=160)
    plt.close(fig)
    groups = defaultdict(list)
    for record in records:
        groups[(record["person_id"], record["source_segment_id"])].append(record)
    segment_summary = {}
    id_to_index = {sample: index for index, sample in enumerate(ids)}
    for (person, segment), rows in groups.items():
        indices = [id_to_index[row["sample_id"]] for row in rows if row["sample_id"] in id_to_index]
        sub = matrix[np.ix_(indices, indices)]
        mask = np.triu(np.ones(sub.shape, bool), 1)
        segment_summary[f"{person}/{segment}"] = {
            "total": len(rows), "ok": len(indices), "intra_pairs": describe(sub[mask])}
    adjacent = []
    for rows in groups.values():
        rows.sort(key=lambda row: row["sample_id"])
        for a, b in zip(rows, rows[1:]):
            if a["sample_id"] in id_to_index and b["sample_id"] in id_to_index:
                adjacent.append({"a": a["sample_id"], "b": b["sample_id"],
                                 "cosine": float(matrix[id_to_index[a["sample_id"]], id_to_index[b["sample_id"]]])})
    analysis = {"by_segment": segment_summary,
                "adjacent_selected_frame_pairs": len(adjacent),
                "most_similar_adjacent_selected": sorted(adjacent, key=lambda row: -row["cosine"])[:8],
                "all_vectors_reloaded_finite": bool(np.isfinite(vectors).all()),
                "observed_stored_shape": list(vectors.shape),
                "raw_norms": describe(np.linalg.norm(vectors, axis=1)),
                "resolution_effect": "confounded_with_identity_not_causal"}
    with (output / "exploration.json").open("x", encoding="utf-8") as file:
        json.dump(analysis, file, ensure_ascii=False, indent=2)
    review_sheets(records, root, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--allowed-root", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.root, args.allowed_root)


if __name__ == "__main__":
    main()
