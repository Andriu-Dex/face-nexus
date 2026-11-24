"""Galería HOG y umbral del mismo ensayo, ligados por SHA-256."""

from hashlib import sha256
import json
from pathlib import Path
import re
import zipfile

import numpy as np

from scripts.compare_identity_k01 import GALLERY_NAME, load_gallery
from scripts.evaluate_hog_knn import K
from scripts.hog_knn import FEATURE_COUNT, PEOPLE, SFACE_FEATURE_COUNT

DISTANCE_NAME = "knn_max_distance.json"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def file_digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def read_threshold_record(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Umbral de distancia k-NN inválido.")
    value = payload.get("max_distance")
    digest = payload.get("gallery_sha256")
    if type(value) is bool or type(value) not in (int, float):
        raise ValueError("Umbral de distancia k-NN inválido.")
    value = float(value)
    if not np.isfinite(value) or value < 0:
        raise ValueError("Umbral de distancia k-NN inválido.")
    if not isinstance(digest, str) or not HEX64.fullmatch(digest.lower()):
        raise ValueError("Falta la huella SHA-256 de la galería.")
    gap = payload.get("min_gap", 0)
    if type(gap) is bool or type(gap) not in (int, float):
        raise ValueError("Holgura entre identidades inválida.")
    gap = float(gap)
    if not np.isfinite(gap) or gap < 0:
        raise ValueError("Holgura entre identidades inválida.")
    preprocessing = payload.get("preprocessing", "box_hog")
    if preprocessing not in ("box_hog", "aligned_hog", "sface"):
        raise ValueError("Preprocesamiento de galería desconocido.")
    return value, digest.lower(), gap, preprocessing


def bind_threshold(folder):
    """Asocia T solo si summary.json confirma la huella de la galería actual."""
    folder = Path(folder)
    gallery = folder / GALLERY_NAME
    path = folder / DISTANCE_NAME
    if not gallery.is_file() or not path.is_file():
        raise FileNotFoundError("Falta galería o umbral en el ensayo.")
    summary = folder / "summary.json"
    if not summary.is_file():
        raise FileNotFoundError("Falta el registro del ensayo (summary.json).")
    digest = file_digest(gallery)
    recorded = json.loads(summary.read_text(encoding="utf-8-sig")).get("gallery_sha256")
    if recorded != digest:
        raise ValueError("La galería no coincide con el registro del ensayo.")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Umbral de distancia k-NN inválido.")
    payload["gallery_sha256"] = digest
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return digest


def _gallery_usable(vectors, labels, feature_count):
    names = set(map(str, labels))
    if (vectors.ndim != 2 or vectors.shape[1] != feature_count or len(vectors) < K
            or not np.isfinite(vectors).all() or labels.ndim != 1
            or labels.shape != (len(vectors),) or type(K) is not int or K < 1
            or names != set(PEOPLE)):
        return False
    return True


def load_verified_knn(folder):
    """Devuelve vectores, etiquetas y T, o un motivo de denegación."""
    folder = Path(folder)
    gallery_path = folder / GALLERY_NAME
    distance_path = folder / DISTANCE_NAME
    if not gallery_path.is_file() or not distance_path.is_file():
        return None, "model_unavailable"
    try:
        threshold, expected, min_gap, preprocessing = read_threshold_record(distance_path)
        digest = file_digest(gallery_path)
        if digest != expected:
            return None, "model_unavailable"
        feature_count = SFACE_FEATURE_COUNT if preprocessing == "sface" else FEATURE_COUNT
        vectors, labels = load_gallery(gallery_path, feature_count)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, zipfile.BadZipFile):
        return None, "model_unavailable"
    if not _gallery_usable(vectors, labels, feature_count):
        return None, "model_unavailable"
    return {"vectors": vectors, "labels": labels, "max_distance": threshold,
            "min_gap": min_gap, "gallery_sha256": digest, "preprocessing": preprocessing}, None
