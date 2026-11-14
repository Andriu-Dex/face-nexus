"""Auditoría estructural local del piloto. No demuestra identidad ni consentimiento."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from scripts.pilot_capture import PEOPLE, shot_plan


def audit_pilot(root, source="camera"):
    root = Path(root)
    issues = []
    counts = Counter()
    hashes = defaultdict(list)
    samples = []
    records = list(root.rglob("*.json")) if root.exists() else []
    for metadata_path in records:
        try:
            meta = json.loads(metadata_path.read_text(encoding="utf-8"))
            name = metadata_path.stem
            person = meta["person_id"]
            number = meta["plan"]["number"]
            if person not in PEOPLE or name != f"{person}_P01_{number:04d}":
                raise ValueError("Etiqueta/identificador incompatible")
            if metadata_path.parent.relative_to(root).as_posix() != f"{person}/P01":
                raise ValueError("Carpeta incompatible")
            if meta["relative_path"] != name + ".png" or meta["session_id"] != "P01":
                raise ValueError("Ruta/sesión incompatible")
            if meta["source"] != source or meta["split"] != "TRAIN":
                raise ValueError("Fuente o partición incorrecta")
            if meta["plan"] != shot_plan(number):
                raise ValueError("Pauta de condiciones incorrecta")
            if source == "camera" and not meta.get("consent_operator_confirmed"):
                raise ValueError("Falta declaración de consentimiento")
            image_path = metadata_path.with_suffix(".png")
            payload = image_path.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            if digest != meta["sha256"]:
                raise ValueError("Hash no coincide")
            if meta["width"] != 1920 or meta["height"] != 1080:
                raise ValueError("Dimensiones declaradas incorrectas")
            frame = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is None or frame.shape != (1080, 1920, 3):
                raise ValueError("PNG ilegible o resolución incorrecta")
            counts[person] += 1
            hashes[digest].append(name)
            grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            samples.append({"sample_id": name,
                            "laplacian_variance": float(cv2.Laplacian(grey, cv2.CV_64F).var()),
                            "mean_intensity": float(grey.mean())})
        except (OSError, ValueError, KeyError, TypeError, cv2.error) as error:
            issues.append({"record": metadata_path.name, "reason": str(error)})
    for path in root.rglob("*.png") if root.exists() else []:
        if not path.with_suffix(".json").exists():
            issues.append({"record": path.name, "reason": "PNG sin metadatos"})
    for person in PEOPLE:
        if counts[person] != 20:
            issues.append({"record": person, "reason": f"{counts[person]}/20 tomas válidas estructuralmente"})
    duplicates = [names for names in hashes.values() if len(names) > 1]
    return {"source": source, "counts": {p: counts[p] for p in PEOPLE},
            "total": sum(counts.values()), "issues": issues, "exact_duplicates": duplicates,
            "structural_pass": not issues and not duplicates,
            "manual_identity_pose_lighting_review": "pending",
            "consent_document_verification": "pending_local_custodian_review",
            "face_detection_and_embeddings": "not_implemented_no_weights",
            "perceptual_duplicate_review": "pending",
            "quality_measurements_no_threshold": samples}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("data/raw/pilot"))
    parser.add_argument("--source", choices=["camera", "synthetic"], default="camera")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_pilot(args.root, args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != "quality_measurements_no_threshold"},
                     ensure_ascii=False, indent=2))
    return 0 if report["structural_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
