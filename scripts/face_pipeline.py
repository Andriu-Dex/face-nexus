"""Validación en TRAIN: YuNet -> rostro único -> alignCrop -> SFace."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time

import cv2
import numpy as np

from scripts.download_face_models import MODELS


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def private_path(path, allowed_root):
    """Evita escapes, incluidos enlaces/junctions ya existentes."""
    path, root = Path(path).resolve(), Path(allowed_root).resolve()
    if path == root or not path.is_relative_to(root):
        raise ValueError("El resultado debe quedar dentro de la raíz privada.")
    return path


def validate_embedding(vector, expected_dimension=128):
    vector = np.asarray(vector)
    if vector.shape not in ((expected_dimension,), (1, expected_dimension)):
        raise ValueError("embedding_shape")
    if vector.dtype != np.float32 or not np.isfinite(vector).all():
        raise ValueError("embedding_dtype_or_nonfinite")
    vector = vector.reshape(-1)
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm <= 0:
        raise ValueError("embedding_zero_or_invalid_norm")
    return vector, norm


def verified_model_path(folder, name):
    _, filename, size, digest, _ = MODELS[name]
    path = Path(folder) / filename
    if path.stat().st_size != size or sha256(path) != digest:
        raise ValueError("Peso ausente, modificado o no verificado.")
    return path


def load_detector(folder):
    path = verified_model_path(folder, "yunet")
    return cv2.FaceDetectorYN.create(str(path), "", (320, 320), .9, .3, 5000,
                                     cv2.dnn.DNN_BACKEND_OPENCV, cv2.dnn.DNN_TARGET_CPU)


def load_models(folder):
    detector = load_detector(folder)
    extractor = cv2.FaceRecognizerSF.create(str(verified_model_path(folder, "sface")), "",
                                          cv2.dnn.DNN_BACKEND_OPENCV, cv2.dnn.DNN_TARGET_CPU)
    return detector, extractor


def process_image(image, detector, extractor):
    result = {"status": "invalid_image", "face_count": 0, "timings_ms": {}}
    if image is None or image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        return result, None, None
    h, w = image.shape[:2]
    if not h or not w:
        return result, None, None
    result["image_size"] = [w, h]
    # Reducir para detectar acota coste; nunca ampliar ni modificar originales.
    scale = min(1., 640 / max(w, h))
    dw, dh = max(1, round(w * scale)), max(1, round(h * scale))
    detection_input = cv2.resize(image, (dw, dh), interpolation=cv2.INTER_AREA)
    result["detector_input_size"] = [dw, dh]
    started = time.perf_counter()
    try:
        detector.setInputSize((dw, dh))
        _, faces = detector.detect(detection_input)
        result["timings_ms"]["detection"] = (time.perf_counter() - started) * 1000
        if faces is None or len(faces) == 0:
            result["status"] = "no_face"
            result["faces"] = []
            return result, None, None
        faces = np.asarray(faces, dtype=np.float32).copy()
        result["face_count"] = len(faces)
        if faces.ndim != 2 or faces.shape[1] != 15 or not np.isfinite(faces).all():
            result["status"] = "invalid_detection"
            return result, None, None
        # Coordenadas de vuelta al fotograma original, usando escalas reales redondeadas.
        faces[:, [0, 2, 4, 6, 8, 10, 12]] *= w / dw
        faces[:, [1, 3, 5, 7, 9, 11, 13]] *= h / dh
        result["faces"] = faces.tolist()
        if len(faces) != 1:
            result["status"] = "multiple_faces"
            return result, None, None
        face = faces[0]
        x, y, width, height = map(float, face[:4])
        landmarks = face[4:14].reshape(5, 2)
        if width <= 0 or height <= 0 or not (
            (landmarks[:, 0] >= 0).all() and (landmarks[:, 0] < w).all()
            and (landmarks[:, 1] >= 0).all() and (landmarks[:, 1] < h).all()
        ):
            result["status"] = "invalid_geometry"
            return result, None, None
        left, top = max(0, int(x)), max(0, int(y))
        right, bottom = min(w, int(np.ceil(x + width))), min(h, int(np.ceil(y + height)))
        if right <= left or bottom <= top:
            result["status"] = "invalid_geometry"
            return result, None, None
        roi = cv2.cvtColor(image[top:bottom, left:right], cv2.COLOR_BGR2GRAY)
        result["quality"] = {
            "box_width_px": width, "box_height_px": height,
            "clipped_box": x < 0 or y < 0 or x + width > w or y + height > h,
            "face_area_fraction": width * height / (w * h),
            "roi_mean_intensity": float(roi.mean()),
            "roi_dark_fraction": float((roi <= 10).mean()),
            "roi_bright_fraction": float((roi >= 245).mean()),
            "roi_laplacian_variance": float(cv2.Laplacian(roi, cv2.CV_64F).var()),
        }
        started = time.perf_counter()
        aligned = extractor.alignCrop(image, face)
        result["timings_ms"]["alignment"] = (time.perf_counter() - started) * 1000
        if aligned.shape != (112, 112, 3) or aligned.dtype != np.uint8:
            result["status"] = "invalid_alignment"
            return result, None, None
        started = time.perf_counter()
        feature = extractor.feature(aligned)
        result["timings_ms"]["extraction"] = (time.perf_counter() - started) * 1000
        result["feature_shape_observed"] = list(feature.shape)
        result["feature_dtype_observed"] = str(feature.dtype)
        vector, norm = validate_embedding(feature)
        result.update(status="ok", embedding_dimension=vector.size, embedding_norm=norm,
                      aligned_size=[112, 112])
        return result, aligned, vector
    except (cv2.error, ValueError, AttributeError) as error:
        result["status"] = "processing_error"
        result["error_type"] = type(error).__name__
        return result, None, None


DARK = 10
BRIGHT = 245


def crop_quality(crop):
    """Laplaciano, media y colas del histograma sobre el recorte en gris."""
    if crop is None or not crop.size:
        return None
    grey = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    if grey.dtype != np.uint8:
        grey = np.clip(grey, 0, 255).astype(np.uint8)
    height, width = grey.shape[:2]
    return {
        "width_px": int(width),
        "height_px": int(height),
        "laplacian_var": float(cv2.Laplacian(grey, cv2.CV_64F).var()),
        "mean": float(grey.mean()),
        "dark_fraction": float((grey <= DARK).mean()),
        "bright_fraction": float((grey >= BRIGHT).mean()),
    }


def describe(values):
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        return {"n": 0}
    return {"n": int(array.size), "min": float(array.min()), "p05": float(np.percentile(array, 5)),
            "median": float(np.median(array)), "p95": float(np.percentile(array, 95)),
            "max": float(array.max())}


def explore(vectors, labels, ids):
    normalized = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    matrix = np.clip(normalized @ normalized.T, -1, 1)
    same = np.equal.outer(labels, labels)
    triangle = np.triu(np.ones(matrix.shape, bool), 1)
    summary = {"intra": describe(matrix[same & triangle]),
               "inter": describe(matrix[~same & triangle]), "by_identity": {}}
    for person in sorted(set(labels)):
        mask = np.equal(labels, person)
        summary["by_identity"][person] = {
            "intra": describe(matrix[triangle & mask[:, None] & mask[None, :]]),
            "inter": describe(matrix[mask[:, None] & ~mask[None, :]])}
    # Atípico exploratorio: menor mediana de similitud a sus compañeros, sin excluir.
    outliers = []
    for index, sample in enumerate(ids):
        peers = np.equal(labels, labels[index]) & (np.arange(len(labels)) != index)
        if peers.any():
            outliers.append({"sample_id": sample, "intra_median": float(np.median(matrix[index, peers]))})
    summary["review_candidates"] = sorted(outliers, key=lambda r: r["intra_median"])[:8]
    return summary, matrix


def write_png(path, frame):
    ok, encoded = cv2.imencode(".png", frame)
    if not ok:
        raise RuntimeError("No se pudo codificar una salida privada.")
    with Path(path).open("xb") as file:
        file.write(encoded.tobytes())


def run(prepared, model_folder, output):
    prepared = Path(prepared).resolve()
    output = private_path(output, prepared)
    active = json.loads((prepared / "CURRENT.json").read_text(encoding="utf-8"))["active_collection"]
    collection = private_path(prepared / active, prepared)
    paths = sorted((collection / "candidates").rglob("*.png"))
    if len(paths) != 80:
        raise ValueError("Se esperaban exactamente las 80 candidatas activas.")
    cv2.setNumThreads(1)
    detector, extractor = load_models(model_folder)
    output.mkdir(parents=True, exist_ok=False)
    for folder in ("detections", "aligned"):
        (output / folder).mkdir()
    # Tres warmups por etapa, no incluidos en tiempos de las 80 imágenes.
    first = cv2.imdecode(np.frombuffer(paths[0].read_bytes(), np.uint8), cv2.IMREAD_COLOR)
    for _ in range(3):
        process_image(first, detector, extractor)
        extractor.feature(np.zeros((112, 112, 3), np.uint8))
    records, vectors, labels, ids = [], [], [], []
    initial_hashes = {}
    for path in paths:
        meta = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        sample = meta["sample_id"]
        if (not re.fullmatch(r"K0[1-4]_S01_SEG\d{2}_F\d{6}", sample)
                or meta["split"] != "TRAIN" or meta["person_id"] != sample[:3]
                or meta["session_id"] != "S01" or meta["source_segment_id"] != sample[8:13]):
            raise ValueError("Identificador o partición inválida.")
        if sha256(path) != meta["sha256"]:
            raise ValueError("Candidata modificada desde la auditoría.")
        original = (prepared.parent / meta["source_relative_path"]).resolve()
        if not original.is_relative_to(prepared.parent) or sha256(original) != meta["sha256"]:
            raise ValueError("Origen inválido o modificado.")
        initial_hashes[path] = meta["sha256"]
        initial_hashes[original] = meta["sha256"]
        frame = cv2.imdecode(np.frombuffer(path.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
        started = time.perf_counter()
        record, aligned, feature = process_image(frame, detector, extractor)
        record["timings_ms"]["processing_total"] = (time.perf_counter() - started) * 1000
        record.update(sample_id=sample, person_id=meta["person_id"],
                      source_segment_id=meta["source_segment_id"], input_sha256=meta["sha256"])
        records.append(record)
        annotated = frame.copy() if frame is not None else None
        for face in record.get("faces", []):
            x, y, w, h = map(int, face[:4])
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
            for px, py in np.asarray(face[4:14]).reshape(5, 2):
                cv2.circle(annotated, (int(px), int(py)), 2, (0, 255, 255), -1)
        if annotated is not None:
            write_png(output / "detections" / (sample + ".png"), annotated)
        if feature is not None:
            write_png(output / "aligned" / (sample + ".png"), aligned)
            vectors.append(feature)
            labels.append(meta["person_id"])
            ids.append(sample)
        print(f"{sample}: {record['status']}", flush=True)
    if any(sha256(path) != digest for path, digest in initial_hashes.items()):
        raise RuntimeError("Se detectó un cambio de originales/candidatas.")
    summary = {"at_utc": datetime.now(timezone.utc).isoformat(), "count": len(records),
               "statuses": dict(Counter(record["status"] for record in records)),
               "by_identity": {}, "opencv": cv2.__version__, "threads": 1,
               "detector": {"score_threshold": .9, "nms": .3, "max_input_side": 640},
               "originals_and_candidates_unchanged": True,
               "visual_review": "pending", "warmup_pipeline_calls": 3,
               "warmup_extra_sface_calls": 3}
    for person in sorted({r["person_id"] for r in records}):
        rows = [r for r in records if r["person_id"] == person]
        summary["by_identity"][person] = {"statuses": dict(Counter(r["status"] for r in rows)),
            "quality": {key: describe([r["quality"][key] for r in rows if "quality" in r])
                        for key in ("box_width_px", "box_height_px", "face_area_fraction",
                                    "roi_mean_intensity", "roi_laplacian_variance")}}
    summary["timings_ms"] = {key: describe([r["timings_ms"][key] for r in records if key in r["timings_ms"]])
                              for key in ("detection", "alignment", "extraction", "processing_total")}
    if vectors:
        array = np.stack(vectors)
        with (output / "embeddings.npz").open("xb") as file:
            np.savez_compressed(file, vectors=array, labels=np.array(labels), sample_ids=np.array(ids))
        summary["exploration"], similarity = explore(array, labels, ids)
        with (output / "similarity.npy").open("xb") as file:
            np.save(file, similarity, allow_pickle=False)
    with (output / "records.json").open("x", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2, allow_nan=False)
    with (output / "summary.json").open("x", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2, allow_nan=False)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = run(args.prepared, args.models, args.output)
    print(json.dumps({k: summary[k] for k in ("count", "statuses", "timings_ms")}, indent=2))


if __name__ == "__main__":
    main()
