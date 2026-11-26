"""Detector de objetos preentrenado (NanoDet-Plus, COCO) usado solo como apoyo opcional.

No es un modelo del proyecto: se descarga de OpenCV Zoo con licencia Apache 2.0 y hash
verificado (download_face_models.py). Cumple dos funciones, ambas desactivadas por defecto:
  1. Mostrar en el video qué objetos hay (celular, laptop, botella...).
  2. Rechazar un rostro cuyo centro cae dentro de una pantalla detectada (celular, laptop,
     televisor o monitor), porque probablemente es una foto o un video y no una persona.
     No detecta fotos impresas: «papel» no es una de las 80 clases de COCO.

Entrada: imagen BGR de cualquier tamaño. Se reduce manteniendo la proporción y se rellena
hasta 416×416 (letterbox), se normaliza con la media y desviación de entrenamiento de NanoDet.
Salida: lista de {"label", "score", "box"} con la caja en píxeles de la imagen original.
"""

from pathlib import Path

import cv2
import numpy as np

MODEL_NAME = "object_detection_nanodet_2022nov.onnx"
INPUT_SIZE = 416
STRIDES = (8, 16, 32, 64)
# Cada lado de la caja se predice como una distribución sobre 0..7 celdas; su media es la distancia.
REG_MAX = 7
MEAN = np.array([103.53, 116.28, 123.675], dtype=np.float32)
STD = np.array([57.375, 57.12, 58.395], dtype=np.float32)
SCORE_THRESHOLD = 0.35
IOU_THRESHOLD = 0.6

# Las 80 clases de COCO en el orden del modelo, en español.
COCO_LABELS = (
    "persona", "bicicleta", "auto", "moto", "avión", "bus", "tren", "camión", "bote",
    "semáforo", "hidrante", "señal de pare", "parquímetro", "banca", "pájaro", "gato", "perro",
    "caballo", "oveja", "vaca", "elefante", "oso", "cebra", "jirafa", "mochila", "paraguas",
    "bolso", "corbata", "maleta", "frisbee", "esquís", "snowboard", "pelota", "cometa",
    "bate", "guante", "patineta", "tabla de surf", "raqueta", "botella", "copa", "taza",
    "tenedor", "cuchillo", "cuchara", "tazón", "plátano", "manzana", "sándwich", "naranja",
    "brócoli", "zanahoria", "hot dog", "pizza", "dona", "pastel", "silla", "sofá", "planta",
    "cama", "mesa", "inodoro", "televisor", "laptop", "mouse", "control remoto", "teclado",
    "celular", "microondas", "horno", "tostadora", "lavabo", "refrigerador", "libro", "reloj",
    "florero", "tijeras", "oso de peluche", "secador", "cepillo de dientes",
)
# Objetos que pueden mostrar un rostro que no es una persona presente.
SCREENS = {"celular", "laptop", "televisor"}


def load_object_detector(models_dir):
    path = Path(models_dir) / MODEL_NAME
    if not path.is_file():
        raise FileNotFoundError(f"Falta {MODEL_NAME}; ejecuta scripts/download_face_models.py.")
    return cv2.dnn.readNet(str(path))


def _anchors():
    """Centro de cada celda de cada escala; las cajas se predicen como distancias a ese centro."""
    centers = []
    for stride in STRIDES:
        cells = INPUT_SIZE // stride
        ys, xs = np.mgrid[0:cells, 0:cells]
        centers.append(np.column_stack((xs.ravel(), ys.ravel())) * stride + 0.5 * (stride - 1))
    return centers


ANCHORS = _anchors()


def letterbox(frame):
    """Reduce sin deformar y rellena con gris hasta 416×416. Devuelve la escala usada."""
    height, width = frame.shape[:2]
    scale = INPUT_SIZE / max(height, width)
    resized = cv2.resize(frame, (round(width * scale), round(height * scale)))
    canvas = np.full((INPUT_SIZE, INPUT_SIZE, 3), 114, np.uint8)
    canvas[:resized.shape[0], :resized.shape[1]] = resized
    return canvas, scale


def decode(outputs, scale):
    """Convierte las salidas de NanoDet en cajas, aplica umbral y supresión de no máximos."""
    boxes, scores = [], []
    for stride, cls_score, box_pred, anchors in zip(STRIDES, outputs[::2], outputs[1::2], ANCHORS):
        cls_score = cls_score.reshape(-1, len(COCO_LABELS))
        logits = box_pred.reshape(-1, REG_MAX + 1)
        weights = np.exp(logits - logits.max(axis=1, keepdims=True))
        weights /= weights.sum(axis=1, keepdims=True)
        # Media de la distribución por lado: izquierda, arriba, derecha, abajo.
        distance = (weights @ np.arange(REG_MAX + 1)).reshape(-1, 4) * stride
        boxes.append(np.column_stack((anchors - distance[:, :2], anchors + distance[:, 2:])))
        scores.append(cls_score)
    boxes = np.clip(np.concatenate(boxes), 0, INPUT_SIZE)
    scores = np.concatenate(scores)
    classes = scores.argmax(axis=1)
    confidence = scores.max(axis=1)
    wh_boxes = np.column_stack((boxes[:, :2], boxes[:, 2:] - boxes[:, :2]))
    keep = cv2.dnn.NMSBoxes(wh_boxes.tolist(), confidence.tolist(), SCORE_THRESHOLD, IOU_THRESHOLD)
    return [{"label": COCO_LABELS[classes[index]], "score": float(confidence[index]),
             "box": [int(value / scale) for value in boxes[index]]}
            for index in np.array(keep).ravel()]


def detect_objects(net, frame):
    canvas, scale = letterbox(frame)
    blob = cv2.dnn.blobFromImage((canvas.astype(np.float32) - MEAN) / STD)
    net.setInput(blob)
    return decode(net.forward(net.getUnconnectedOutLayersNames()), scale)


def inside_screen(face_box, objects):
    """True si el centro del rostro cae dentro de un celular, laptop o televisor detectado."""
    left, top, right, bottom = face_box
    center_x, center_y = (left + right) / 2, (top + bottom) / 2
    return any(item["label"] in SCREENS
               and item["box"][0] <= center_x <= item["box"][2]
               and item["box"][1] <= center_y <= item["box"][3]
               for item in objects)
