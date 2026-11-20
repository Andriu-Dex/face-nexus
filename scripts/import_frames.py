"""Audita frames externos y copia una selección sin modificar los originales."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import shutil

import cv2
import numpy as np


def natural_key(path):
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", str(path))]


def spread_indices(length, count):
    """Índices uniformes, sin rellenar una colección pequeña con duplicados."""
    if length <= 0 or count <= 0:
        return []
    count = min(count, length)
    return [round(index * (length - 1) / (count - 1)) for index in range(count)] if count > 1 else [length // 2]


def image_metrics(frame):
    # Se mide una vista reducida, sin usar ni guardar una representación facial.
    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(grey, (256, 256), interpolation=cv2.INTER_AREA)
    hashed = cv2.resize(grey, (9, 8), interpolation=cv2.INTER_AREA)
    bits = (hashed[:, 1:] > hashed[:, :-1]).reshape(-1)
    signature = sum(int(bit) << index for index, bit in enumerate(bits))
    return {"mean_intensity": float(small.mean()),
            "laplacian_variance_256": float(cv2.Laplacian(small, cv2.CV_64F).var()),
            "dhash": f"{signature:016x}"}


def regroup_manifest(source, previous, destination, per_person=20):
    """Reagrupa una auditoría ya ejecutada sin volver a decodificar imágenes.

    Cada persona queda en S01 por decisión conservadora. Se mantienen origen,
    segmento y hash; el número de vídeos reales no se declara comprobado.
    """
    source, previous, destination = Path(source).resolve(), Path(previous), Path(destination)
    groups = defaultdict(list)
    records = []
    for line in (previous / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        original = (source / record["source_relative_path"]).resolve()
        if not original.is_relative_to(source):
            raise ValueError("Origen fuera de raíz.")
        if hashlib.sha256(original.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError("El original cambió desde la auditoría.")
        segment_number = int(record["session_id"][1:])
        record["source_segment_id"] = f"SEG{segment_number:02d}"
        record["session_id"] = "S01"
        record["session_independence"] = "conservative_single_group_per_person"
        record["sample_id"] = (f"{record['person_id']}_S01_SEG{segment_number:02d}"
                               f"_F{record['source_frame_ordinal']:06d}")
        record["split"] = "TRAIN"
        records.append(record)
        if record["decode_status"] == "valid":
            groups[(record["person_id"], segment_number)].append(record)
    destination.mkdir(parents=True, exist_ok=False)
    with (destination / "manifest.jsonl").open("x", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    selected = Counter()
    for person in sorted({record["person_id"] for record in records}):
        segments = [group for (pid, seg), group in sorted(groups.items()) if pid == person]
        if not segments:
            continue
        base, remainder = divmod(per_person, len(segments))
        used_pixels = set()
        for index, segment in enumerate(segments):
            for position in spread_indices(len(segment), base + (index < remainder)):
                record = segment[position]
                if record["pixel_sha256_bgr"] in used_pixels:
                    continue
                used_pixels.add(record["pixel_sha256_bgr"])
                folder = destination / "candidates" / person / "S01"
                folder.mkdir(parents=True, exist_ok=True)
                target = folder / (record["sample_id"] + ".png")
                with (source / record["source_relative_path"]).open("rb") as src, target.open("xb") as dst:
                    shutil.copyfileobj(src, dst)
                if hashlib.sha256(target.read_bytes()).hexdigest() != record["sha256"]:
                    raise RuntimeError("Hash de copia incorrecto.")
                with target.with_suffix(".json").open("x", encoding="utf-8") as metadata:
                    json.dump(record, metadata, ensure_ascii=False, indent=2)
                selected[person] += 1
    summary = {"counts": dict(Counter(r["person_id"] for r in records)),
               "session_grouping": "one_conservative_group_per_person",
               "actual_video_count": "not_verified", "split": "TRAIN",
               "selection_counts": dict(selected), "selection_status": "candidate_manual_review_pending",
               "previous_audit_sha256": hashlib.sha256((previous / "audit.json").read_bytes()).hexdigest(),
               "manifest_sha256": hashlib.sha256((destination / "manifest.jsonl").read_bytes()).hexdigest()}
    with (destination / "audit.json").open("x", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
    return summary


def import_collection(source, destination, mapping, per_person=20):
    """mapping: carpeta privada -> ID; cada subcarpeta se inventaría por separado.

    No asigna particiones ni descarta por nitidez. La selección temporal es
    candidata, no demuestra diversidad de poses o rostro válido.
    """
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_dir() or not mapping or per_person <= 0:
        raise ValueError("Fuente, mapping y cantidad deben ser válidos.")
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("IDs repetidos en mapping.")
    for folder, person in mapping.items():
        if person not in ("K01", "K02", "K03", "K04"):
            raise ValueError("ID no permitido.")
        if (source / folder).resolve().parent != source or not (source / folder).is_dir():
            raise ValueError("Carpeta fuente inválida o fuera de la raíz.")
    # Nunca importar sobre una carpeta existente ni modificar la fuente.
    destination.mkdir(parents=True, exist_ok=False)
    file_hashes = defaultdict(list)
    pixel_hashes = defaultdict(list)
    summary = {"counts": {}, "sessions": {}, "dimensions": {}, "invalid": [],
               "selection_counts": {}, "near_adjacent_candidates": 0,
               "split": "UNASSIGNED", "session_origin": "provisional_segment_inventory_not_capture_sessions",
               "face_detection": "not_performed", "pose_and_identity_review": "pending"}
    with (destination / "manifest.jsonl").open("x", encoding="utf-8") as manifest:
        for folder, person in sorted(mapping.items(), key=lambda pair: pair[1]):
            sessions = sorted([p for p in (source / folder).iterdir() if p.is_dir()], key=natural_key)
            if list((source / folder).glob("*.png")):
                sessions = [source / folder] + sessions
            summary["counts"][person] = 0
            summary["sessions"][person] = len(sessions)
            dimensions = Counter()
            valid_by_session = []
            for session_number, session in enumerate(sessions, 1):
                session_id = f"S{session_number:02d}"
                valid = []
                last_signature = None
                for number, path in enumerate(sorted(session.glob("*.png"), key=natural_key), 1):
                    if not path.is_file() or not path.resolve().is_relative_to(source):
                        raise ValueError("Archivo fuente fuera de raíz.")
                    payload = path.read_bytes()
                    record = {"sample_id": f"{person}_{session_id}_F{number:06d}",
                              "person_id": person, "session_id": session_id,
                              "source_relative_path": path.relative_to(source).as_posix(),
                              "source_filename": path.name, "source_frame_ordinal": number,
                              "sha256": hashlib.sha256(payload).hexdigest(),
                              "source": "externally_extracted_video_frame",
                              "camera": "TMCAM 8305_operator_confirmed", "split": "UNASSIGNED",
                              "session_independence": "not_assessed",
                              "video_hash": None, "video_timestamp_seconds": None}
                    frame = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)
                    if frame is None:
                        record["decode_status"] = "invalid"
                        summary["invalid"].append(record["sample_id"])
                    else:
                        h, w = frame.shape[:2]
                        record.update({"decode_status": "valid", "width": w, "height": h,
                                       "pixel_sha256_bgr": hashlib.sha256(frame.tobytes()).hexdigest(),
                                       "metrics": image_metrics(frame)})
                        signature = int(record["metrics"]["dhash"], 16)
                        if last_signature is not None and (signature ^ last_signature).bit_count() <= 2:
                            summary["near_adjacent_candidates"] += 1
                        last_signature = signature
                        summary["counts"][person] += 1
                        dimensions[f"{w}x{h}"] += 1
                        file_hashes[record["sha256"]].append(record["sample_id"])
                        pixel_hashes[record["pixel_sha256_bgr"]].append(record["sample_id"])
                        valid.append(record)
                    manifest.write(json.dumps(record, ensure_ascii=False) + "\n")
                valid_by_session.append(valid)
                print(f"{person}/{session_id}: {len(valid)} PNG decodificados", flush=True)
            summary["dimensions"][person] = dict(dimensions)
            # Reparto equilibrado entre sesiones; luego posiciones uniformes.
            chosen = []
            if sessions:
                base, remainder = divmod(per_person, len(sessions))
                for index, valid in enumerate(valid_by_session):
                    chosen.extend(valid[position] for position in spread_indices(
                        len(valid), base + (index < remainder)))
            used_pixels = set()
            copied = 0
            for record in chosen:
                if record["pixel_sha256_bgr"] in used_pixels:
                    continue
                used_pixels.add(record["pixel_sha256_bgr"])
                target_dir = destination / "candidates" / person / record["session_id"]
                target_dir.mkdir(parents=True, exist_ok=True)
                target = target_dir / (record["sample_id"] + ".png")
                original = source / record["source_relative_path"]
                with original.open("rb") as original_file, target.open("xb") as target_file:
                    shutil.copyfileobj(original_file, target_file)
                if hashlib.sha256(target.read_bytes()).hexdigest() != record["sha256"]:
                    raise RuntimeError("Copia con hash distinto del original.")
                with target.with_suffix(".json").open("x", encoding="utf-8") as file:
                    json.dump(record, file, ensure_ascii=False, indent=2)
                copied += 1
            summary["selection_counts"][person] = copied
    summary["exact_file_duplicate_groups"] = [v for v in file_hashes.values() if len(v) > 1]
    summary["exact_pixel_duplicate_groups"] = [v for v in pixel_hashes.values() if len(v) > 1]
    summary["total_valid"] = sum(summary["counts"].values())
    summary["manifest_sha256"] = hashlib.sha256((destination / "manifest.jsonl").read_bytes()).hexdigest()
    summary["near_duplicate_method"] = "adjacent_in_session_dhash_hamming_le_2_review_only"
    with (destination / "audit.json").open("x", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, help="JSON privado carpeta -> Kxx")
    parser.add_argument("--regroup-from", type=Path, help="Auditoría previa a reagrupar en una S01 por persona")
    args = parser.parse_args()
    if args.regroup_from:
        result = regroup_manifest(args.source, args.regroup_from, args.destination)
    else:
        if not args.mapping:
            parser.error("Se requiere --mapping o --regroup-from.")
        result = import_collection(args.source, args.destination,
                                   json.loads(args.mapping.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
