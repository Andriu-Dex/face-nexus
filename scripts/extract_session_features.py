"""Extrae SFace de fotogramas seleccionados de sesiones nuevas TRAIN o VALIDATION."""

import argparse
from collections import Counter
from hashlib import file_digest, sha256
import json
from pathlib import Path
import tempfile

import cv2
import numpy as np

from scripts.capture_manifest import FRAME_SHAPE, child, load_schedule, read_json, write_synced
from scripts.dataset_capture import PROJECT, verify_vault
from scripts.face_pipeline import load_models, process_image


def hash_file(path):
    with path.open("rb") as handle:
        return file_digest(handle, "sha256").hexdigest()


def extract(vault, entries, plan, split, detector, extractor, *, allow_848x478=False):
    vectors, labels, ids, records = [], [], [], []
    video_sessions, frame_hashes = {}, set()
    allowed_shapes = {FRAME_SHAPE}
    if allow_848x478:
        if split != "TRAIN":
            raise ValueError("La excepción 848×478 se permite únicamente en TRAIN.")
        allowed_shapes.add((478, 848, 3))
    if not isinstance(entries, list) or not entries:
        raise ValueError("El manifiesto debe contener al menos un fotograma.")
    for number, entry in enumerate(entries, 1):
        session = entry["session_id"]
        row = plan.get(session)
        if row is None or row["split"] != split:
            raise ValueError(f"La sesión {session} no está asignada a {split}.")
        path = child(vault, entry["image"])
        video = child(vault, entry["video"])
        if path.suffix.lower() not in (".png", ".jpg", ".jpeg") or not video.is_file():
            raise ValueError("Se requiere el fotograma exportado y el vídeo fuente.")
        video_digest, existing_session = video_sessions.get(video, (None, session))
        if existing_session != session:
            raise ValueError("Un vídeo fuente no puede pertenecer a dos sesiones.")
        if video_digest is None:
            video_digest = hash_file(video)
            video_sessions[video] = (video_digest, session)
        frame_index = entry["frame_index"]
        if type(frame_index) is not int or frame_index < 0:
            raise ValueError("El índice del fotograma debe ser un entero no negativo.")
        encoded = path.read_bytes()
        digest = sha256(encoded).hexdigest()
        if digest in frame_hashes:
            raise ValueError("El lote contiene un fotograma duplicado.")
        frame_hashes.add(digest)
        frame = cv2.imdecode(np.frombuffer(encoded, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if frame is None or frame.shape not in allowed_shapes or frame.dtype != np.uint8:
            raise ValueError("El fotograma debe conservar el formato BGR y una resolución permitida.")
        sample = f"{session}_F{number:06d}"
        result, _, vector = process_image(frame, detector, extractor)
        records.append({
            **entry, "sample_id": sample, "person_id": row["person_id"],
            "image_sha256": digest, "video_sha256": video_digest,
            "width": frame.shape[1], "height": frame.shape[0],
            "status": result["status"], "timings_ms": result["timings_ms"],
        })
        if vector is not None:
            vectors.append(vector)
            labels.append(row["person_id"])
            ids.append(sample)
    return {"vectors": np.asarray(vectors, dtype=np.float32).reshape(-1, 128),
            "labels": np.array(labels, dtype=str), "sample_ids": np.array(ids, dtype=str)}, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--manifest", required=True, help="JSON relativo al volumen.")
    parser.add_argument("--split", choices=("TRAIN", "VALIDATION"), required=True)
    parser.add_argument("--allow-848x478", action="store_true",
                        help="Permite fotogramas nativos de 848×478 únicamente en TRAIN.")
    parser.add_argument("--output", required=True, help="Carpeta nueva relativa al volumen.")
    args = parser.parse_args()
    try:
        vault = verify_vault(args.vault)
        output = child(vault, args.output)
        if output.exists():
            raise ValueError("La carpeta de resultado ya existe.")
        schedule = load_schedule(child(vault, "plan.json"), child(vault, "sessions"))
        entries = read_json(child(vault, args.manifest))
        detector, extractor = load_models(PROJECT / "models" / "verified")
        cv2.setNumThreads(1)
        features, records = extract(
            vault, entries, schedule, args.split, detector, extractor,
            allow_848x478=args.allow_848x478,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".pending-", dir=output.parent))
        with (staging / "embeddings.npz").open("xb") as handle:
            np.savez_compressed(handle, **features)
        statuses = Counter(row["status"] for row in records)
        summary = {"split": args.split, "allow_848x478": args.allow_848x478,
                   "statuses": statuses, "records": records}
        write_synced(staging / "records.json", json.dumps(summary, indent=2).encode("utf-8"))
        staging.rename(output)
        print(f"{len(records)} fotogramas procesados. Resultado: {dict(statuses)}.")
    except (OSError, ValueError, KeyError, TypeError, cv2.error) as exc:
        parser.exit(1, f"Extracción detenida: {exc}\n")


if __name__ == "__main__":
    main()
