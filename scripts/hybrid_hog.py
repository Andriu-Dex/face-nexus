"""Landmarks YuNet (5 puntos) concatenados al HOG completo. No recorta el descriptor."""

import numpy as np

from scripts.hog_knn import FEATURE_COUNT, describe_face, detect_faces


GEO_COUNT = 12
HYBRID_COUNT = GEO_COUNT + FEATURE_COUNT


def geometry_vector(landmarks, left, top, right, bottom):
    """10 coords en la caja [0,1] y dos distancias relativas. Luego L2."""
    width = right - left
    height = bottom - top
    points = np.asarray(landmarks, dtype=np.float64).reshape(5, 2)
    if width <= 0 or height <= 0 or points.shape != (5, 2) or not np.isfinite(points).all():
        return None
    local = np.empty_like(points)
    local[:, 0] = (points[:, 0] - left) / width
    local[:, 1] = (points[:, 1] - top) / height
    eye_right, eye_left, nose = local[0], local[1], local[2]
    interocular = float(np.linalg.norm(eye_right - eye_left))
    mid_eyes = (eye_right + eye_left) / 2
    eye_nose = float(np.linalg.norm(mid_eyes - nose))
    vector = np.concatenate([local.reshape(-1), [interocular, eye_nose]]).astype(np.float32)
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 0 and np.isfinite(norm) else None


def fuse(geo, hog):
    """Ambos bloques ya son unitarios: al concatenar, cada uno aporta la mitad de la energía."""
    geo = np.asarray(geo, np.float32).reshape(-1)
    hog = np.asarray(hog, np.float32).reshape(-1)
    if geo.shape != (GEO_COUNT,) or hog.shape != (FEATURE_COUNT,):
        return None
    fused = np.concatenate([geo, hog])
    norm = float(np.linalg.norm(fused))
    return fused / norm if norm > 0 and np.isfinite(norm) else None


def describe_pair(frame, detector):
    """Un solo rostro: HOG del recorte y vector híbrido. Si YuNet no da puntos, no hay híbrido."""
    faces = detect_faces(frame, detector)
    if len(faces) != 1:
        return None
    left, top, right, bottom, _score, landmarks = faces[0]
    if landmarks is None:
        return None
    hog = describe_face(frame[top:bottom, left:right])
    geo = geometry_vector(landmarks, left, top, right, bottom)
    if hog is None or geo is None:
        return None
    hybrid = fuse(geo, hog)
    if hybrid is None:
        return None
    return {"hog": hog.astype(np.float32), "hybrid": hybrid.astype(np.float32)}
