"""Características HOG por rostro y clasificador k-NN propio."""

import cv2
import numpy as np

from scripts.face_pipeline import crop_quality


FACE_SIZE = (64, 64)
HOG = cv2.HOGDescriptor(FACE_SIZE, (16, 16), (8, 8), (8, 8), 9)
FEATURE_COUNT = HOG.getDescriptorSize()
SFACE_FEATURE_COUNT = 128
PEOPLE = ("K01", "K02", "K03", "K04")


def face_grey(crop):
    """Recorte BGR → gris 64×64 ecualizado. Lo comparten HOG y la CNN facial."""
    grey = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    grey = cv2.resize(grey, FACE_SIZE, interpolation=cv2.INTER_AREA)
    return cv2.equalizeHist(grey)


def describe_face(crop):
    """Ecualiza en gris y resume las orientaciones de bordes del recorte."""
    vector = HOG.compute(face_grey(crop)).reshape(-1)
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 0 and np.isfinite(norm) else None


def describe_face_cnn(crop, net):
    """Vector de 128 de la CNN propia (ONNX en OpenCV), con la misma entrada gris que HOG."""
    x = face_grey(crop).astype(np.float32) / 127.5 - 1
    net.setInput(x[None, None])
    vector = net.forward().reshape(-1)
    norm = float(np.linalg.norm(vector))
    if vector.size != SFACE_FEATURE_COUNT or not np.isfinite(norm) or norm <= 0:
        return None
    return vector / norm


def fuse_vectors(cnn, sface, weight):
    """[√w · CNN, √(1−w) · SFace]: distancia² = w·d²_CNN + (1−w)·d²_SFace; norma 1."""
    return np.concatenate((np.sqrt(weight) * cnn, np.sqrt(1 - weight) * sface), axis=-1)


def describe_fusion(frame, detection, net, aligner, weight):
    """CNN propia sobre la caja YuNet + SFace sobre el rostro alineado, como apoyo."""
    left, top, right, bottom, *_ = detection
    cnn = describe_face_cnn(frame[top:bottom, left:right], net)
    aligned = align_detected_face(frame, detection, aligner)
    sface = None if aligned is None else describe_sface(aligned, aligner)
    if cnn is None or sface is None:
        return None
    return fuse_vectors(cnn, sface, weight)


def describe_sface(crop, extractor):
    vector = extractor.feature(crop).reshape(-1)
    norm = np.linalg.norm(vector)
    if vector.size != SFACE_FEATURE_COUNT or not np.isfinite(norm) or norm <= 0:
        return None
    return vector / norm


def _require_bgr_frame(frame):
    if (not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3
            or frame.dtype != np.uint8 or not frame.size):
        raise ValueError("Se requiere un fotograma BGR uint8.")
    return frame.shape[:2]


def detect_faces(frame, detector):
    """Cajas y 5 landmarks de YuNet en píxeles del fotograma original."""
    height, width = _require_bgr_frame(frame)
    scale = min(1., 640 / max(width, height))
    size = max(1, round(width * scale)), max(1, round(height * scale))
    detector.setInputSize(size)
    _, detections = detector.detect(cv2.resize(frame, size, interpolation=cv2.INTER_AREA))
    faces = []
    if detections is None:
        return faces
    sx, sy = width / size[0], height / size[1]
    for detection in detections:
        x, y, w, h = detection[:4]
        if not np.isfinite([x, y, w, h]).all() or w <= 0 or h <= 0:
            continue
        left = max(0, round(x * sx))
        top = max(0, round(y * sy))
        right = min(width, round((x + w) * sx))
        bottom = min(height, round((y + h) * sy))
        if right <= left or bottom <= top:
            continue
        score = None
        landmarks = None
        if len(detection) >= 15:
            if np.isfinite(detection[14]):
                score = float(detection[14])
            points = np.asarray(detection[4:14], dtype=np.float64).reshape(5, 2)
            points[:, 0] *= sx
            points[:, 1] *= sy
            if np.isfinite(points).all():
                landmarks = points
        faces.append((left, top, right, bottom, score, landmarks))
    return faces


def detect_boxes(frame, detector):
    """Localiza cajas en el fotograma original. Conserva el recorte 640 del detector."""
    return [(left, top, right, bottom, score)
            for left, top, right, bottom, score, _landmarks in detect_faces(frame, detector)]


def align_detected_face(frame, detection, aligner):
    """Normaliza la pose en el plano con los cinco puntos de YuNet."""
    left, top, right, bottom, score, landmarks = detection
    if landmarks is None or np.linalg.norm(landmarks[0] - landmarks[1]) < 2:
        return None
    row = np.array([left, top, right - left, bottom - top,
                    *landmarks.ravel(), score or 0.], dtype=np.float32)
    return aligner.alignCrop(frame, row)


def face_features(frame, detector, *, require_single=False):
    """Devuelve caja y vector por cada rostro válido del mismo fotograma."""
    boxes = detect_boxes(frame, detector)
    if require_single and len(boxes) != 1:
        return []
    faces = []
    for left, top, right, bottom, _score in boxes:
        features = describe_face(frame[top:bottom, left:right])
        if features is not None:
            faces.append(((left, top, right, bottom), features))
    return faces


def inspect_live_frame(frame, detector):
    """Separa fallo de detección, varios rostros y recorte HOG usable. No guarda el vector."""
    boxes = detect_boxes(frame, detector)
    height, width = frame.shape[:2]
    scores = [score for *_box, score in boxes if score is not None]
    report = {
        "reason": "no_face",
        "face_count": len(boxes),
        "frame_width": width,
        "frame_height": height,
        "max_detection_score": max(scores) if scores else None,
        "box_width_px": None,
        "box_height_px": None,
        "vector": None,
    }
    if not boxes:
        return report
    if len(boxes) != 1:
        report["reason"] = "multiple_faces"
        return report
    left, top, right, bottom, score = boxes[0]
    report["box_width_px"] = right - left
    report["box_height_px"] = bottom - top
    report["max_detection_score"] = score
    crop = frame[top:bottom, left:right]
    report["quality"] = crop_quality(crop)
    features = describe_face(crop)
    if features is None:
        report["reason"] = "empty_hog"
        return report
    report["reason"] = "usable"
    report["vector"] = features
    return report


def runner_up_distance(gallery, labels, query, winner):
    """Menor distancia a una muestra cuya etiqueta no es la del ganador."""
    mask = np.asarray(labels).astype(str) != str(winner)
    if not mask.any():
        return None
    return float(np.linalg.norm(gallery[mask] - query, axis=1).min())


def accepts_open_set(winner, distance, gap, max_distance, min_gap):
    if winner not in PEOPLE or distance is None or distance > max_distance:
        return False
    if min_gap <= 0:
        return True
    return gap is not None and gap >= min_gap


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
