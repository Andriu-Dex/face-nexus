"""Características HOG por rostro y clasificador k-NN propio."""

import cv2
import numpy as np


FACE_SIZE = (64, 64)
HOG = cv2.HOGDescriptor(FACE_SIZE, (16, 16), (8, 8), (8, 8), 9)
FEATURE_COUNT = HOG.getDescriptorSize()
PEOPLE = ("K01", "K02", "K03", "K04")


def describe_face(crop):
    """Ecualiza en gris y resume las orientaciones de bordes del recorte."""
    grey = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    grey = cv2.resize(grey, FACE_SIZE, interpolation=cv2.INTER_AREA)
    vector = HOG.compute(cv2.equalizeHist(grey)).reshape(-1)
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 0 and np.isfinite(norm) else None


def face_features(frame, detector, *, require_single=False):
    """Devuelve caja y vector por cada rostro válido del mismo fotograma."""
    if (not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3
            or frame.dtype != np.uint8 or not frame.size):
        raise ValueError("Se requiere un fotograma BGR uint8.")
    height, width = frame.shape[:2]
    scale = min(1., 640 / max(width, height))
    size = max(1, round(width * scale)), max(1, round(height * scale))
    detector.setInputSize(size)
    _, detections = detector.detect(cv2.resize(frame, size, interpolation=cv2.INTER_AREA))
    if detections is None or (require_single and len(detections) != 1):
        return []
    faces = []
    for detection in detections:
        x, y, w, h = detection[:4]
        if not np.isfinite([x, y, w, h]).all() or w <= 0 or h <= 0:
            continue
        left = max(0, round(x * width / size[0]))
        top = max(0, round(y * height / size[1]))
        right = min(width, round((x + w) * width / size[0]))
        bottom = min(height, round((y + h) * height / size[1]))
        if right <= left or bottom <= top:
            continue
        features = describe_face(frame[top:bottom, left:right])
        if features is not None:
            faces.append(((left, top, right, bottom), features))
    return faces


def knn_candidate(train, labels, query, k=3):
    """Usa distancia euclidiana y voto; un empate deja el resultado ambiguo."""
    distances = np.linalg.norm(train - query, axis=1)
    indices = np.argsort(distances, kind="stable")[:k]
    candidates, votes = np.unique(labels[indices], return_counts=True)
    winners = candidates[votes == votes.max()]
    if len(winners) != 1:
        return None, None
    winner = str(winners[0])
    nearest_winner = distances[indices][labels[indices] == winner].min()
    return winner, float(nearest_winner)


def recognize(train, labels, query, *, k=3, max_distance=None):
    """Acepta solo con un umbral calibrado y un ganador entre los vecinos."""
    if (train.ndim != 2 or train.shape[1] != FEATURE_COUNT or labels.shape != (len(train),)
            or query.shape != (FEATURE_COUNT,) or type(k) is not int or not 1 <= k <= len(train)
            or not np.isfinite(train).all() or not np.isfinite(query).all()
            or not set(labels).issubset(PEOPLE)):
        raise ValueError("Vectores, etiquetas o número de vecinos incompatibles.")
    if max_distance is None:
        return "UNKNOWN"
    if not np.isfinite(max_distance) or max_distance < 0:
        raise ValueError("Umbral de distancia inválido.")
    winner, distance = knn_candidate(train, labels, query, k)
    return winner if winner is not None and distance <= max_distance else "UNKNOWN"
