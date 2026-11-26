"""Interfaz local: cámara o imagen, decisión, permisos e historial sin fotos."""

import argparse
from datetime import datetime
import os
import threading
from pathlib import Path
from time import monotonic, sleep
from urllib.parse import urlsplit, urlunsplit
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import math

import cv2

from scripts.access import default_permissions, require_everyone_authorized, simulate_authorize
from scripts.calibrate_hog import ROTATE
from scripts.dataset_capture import verify_vault
from scripts.face_pipeline import load_detector, load_models
from scripts.hog_knn import PEOPLE
from scripts.latch_serial import (
    HOLD_MAX_SECONDS, HOLD_MIN_SECONDS, SERVO_CLOSED, SERVO_MAX, SERVO_MIN, SERVO_OPEN, latch_ready,
    open_latch_port, ping_firmware, run_servo_test, send_decision, send_servo_test, set_hold,
)
from scripts.live_k01 import HUMAN_RUN, build_identify, face_descriptor, load_keras, paint_regions, recognize_frame
from scripts.phone_serial_bench import local_stream_url
from scripts.presentation_gate import PresentationGate, scene_kind


BG = "#EDF2F6"
MODEL_OPTIONS = {
    "CNN propia + SFace (final)": "identity_four_other/identity_four_0406_real_fusion_w075",
    "CNN propia": "identity_four_other/identity_four_phone_04_cnn_run1",
    "HOG original": "identity_four/identity_four_v2",
    "HOG ampliado": "identity_four_other/identity_four_phone_04_expanded",
    "HOG alineado": "identity_four_other/identity_four_phone_04_aligned",
    "SFace (comparación)": "identity_four_other/identity_four_phone_04_sface",
}
SURFACE = "#FFFFFF"
INK = "#142B3D"
VIEWER = "#122636"
ACCENT = "#006B68"
DENIED_INK = "#7A2436"
WAIT_INK = "#4A5C6A"
HINT = "#D7E3EC"
HEADER = "#0F2233"
ACCENT_SOFT = "#4FB3A9"
CHIP_IDLE = "#3A4F61"
SURFACE_ALT = "#F4F7FA"
TRACK = "#E3EAF0"
TAG_BG = "#0F2233"
AMBER = "#C98A16"
REJECT = "#D9475B"
ICON_FONT = "Segoe MDL2 Assets"
ICON_LOCK = "\uE72E"
ICON_UNLOCK = "\uE785"
ICON_WARNING = "\uE7BA"
ICON_SHIELD = "\uEA18"
ICON_EDIT = "\uE70F"
# Conexiones del celular que se recuerdan en la ventana C\u00E1mara.
RECENT_CAMERAS = 3
# L\u00EDmites de las reglas de apertura. El cierre m\u00EDnimo supera con margen el latido de 0,5 s:
# con un cierre igual o menor el ESP32 cerrar\u00EDa entre dos renovaciones.
FRAMES_MIN, FRAMES_MAX = 3, 60
LATCH_HOLD_SECONDS = 3
PIPELINE_STEPS = (
    ("phone", "Celular (captura)"),
    ("detect", "YuNet (rostro)"),
    ("identify", "CNN propia + SFace → k-NN"),
    ("decide", "Permiso"),
    ("esp32", "ESP32 (pestillo)"),
)
# Resumen de cada variante; sus cifras medidas están en RESULT_TABLES.
MODEL_FACTS = {
    "identity_four_other/identity_four_0406_real_fusion_w075":
        "CNN propia (75 %) + SFace de apoyo (25 %) · k-NN, k = 3 · T = 1,011 · G = 0,114 · "
        "galería videos 04 + 06",
    "identity_four_other/identity_four_phone_04_cnn_run1":
        "CNN propia sola · k-NN, k = 3 · galería del video 04",
}
# Tablas medidas del informe (docs/decisions.md D-88 a D-92). Se muestran tal cual; no se recalculan.
# Cada tabla: (título, nota, encabezados, filas). La fila marcada con «*» es la variante en uso.
RESULT_TABLES = (
    ("Entrenamiento de la CNN propia",
     "PyTorch, CosFace (s = 30, m = 0,35), vector de 128. TAR con 100 000 pares de 500 identidades no vistas.",
     ("Corrida", "Identidades", "Imágenes", "TAR@1 %", "TAR@0,1 %"),
     (("1 *", "5000", "259 980", "99,0 %", "96,1 %"),
      ("2", "20 000", "1 043 297", "99,7 %", "98,8 %"))),
    ("Extractor: HOG frente a la CNN propia",
     "k-NN con rechazo; galería video 04, prueba video 05, umbral ≤ 1 % de LFW.",
     ("Extractor", "Integrantes", "LFW aceptados", "Confusiones"),
     (("HOG de caja", "43/75", "10/999", "0"),
      ("HOG alineado", "53/75", "8/999", "0"),
      ("CNN propia, corrida 1 *", "68/75", "2/999", "0"),
      ("CNN propia, corrida 2", "72/75", "14/999", "0"))),
    ("Clasificadores sobre la CNN propia",
     "Mismos vectores y particiones. Exactitud y macro-F1 en conjunto cerrado; rechazo con ≤ 1 % de LFW.",
     ("Clasificador", "Exactitud", "Macro-F1", "Integrantes", "LFW aceptados"),
     (("k-NN, distancia y holgura *", "100 %", "1,000", "68/75", "2/999"),
      ("SVM (RBF)", "98,7 %", "0,987", "69/75", "10/999"),
      ("Random Forest", "98,7 %", "0,987", "46/75", "6/999"),
      ("MLP", "93,3 %", "0,933", "53/75", "17/999"))),
    ("Influencia de cada parte: CNN propia y SFace",
     "Distancia² = w·d²CNN + (1 − w)·d²SFace; w es la fracción que aporta la red propia.",
     ("Variante", "Peso CNN (w)", "Integrantes", "LFW aceptados"),
     (("Solo CNN propia", "100 %", "68/75", "2/999"),
      ("Fusión *", "75 %", "74/75", "5/999"),
      ("Fusión", "50 %", "75/75", "10/999"),
      ("Fusión", "25 %", "75/75", "13/999"),
      ("Solo SFace", "0 %", "75/75", "11/999"))),
    ("Recalibración con desconocidos reales",
     "Galería videos 04 + 06; cada desconocido se evalúa con un umbral calibrado sin él.",
     ("Variante", "Desconocidos que abren", "LFW", "Fotogramas integrantes", "Integrantes que abren"),
     (("Solo CNN propia", "0/5", "0/999", "79 %", "4/4"),
      ("CNN 75 % + SFace 25 % *", "0/5", "0/999", "89 %", "4/4"),
      ("CNN 50 % + SFace 50 %", "1/5", "0/999", "90 %", "4/4"))),
    ("Otras mediciones",
     "",
     ("Medición", "Resultado"),
     (("CNN humano / no humano (Keras, LFW + CIFAR-10)", "99,96 % en 12 627 ejemplos"),
      ("Inferencia por fotograma en vivo", "22 a 33 ms"),
      ("Vista en vivo", "13 a 14 fps"),
      ("Personas no calibradas en el ensayo en vivo", "8/8 rechazadas"))),
)
# Arquitectura de FaceNet (scripts/train_face_cnn.py) para la pestaña «Red neuronal».
# (nombre, canales, lado en píxeles, operación, forma de los pesos, parámetros entrenables).
# Parámetros = 9·cin·cout por convolución + 2·cout por normalización; lineal = 4096·128 + 128.
NETWORK_LAYERS = (
    ("Entrada", 1, 64, "Rostro recortado por YuNet, gris, ecualizado", "—", 0),
    ("Bloque 1", 32, 32, "2 × (conv 3×3 + BN + ReLU), max pooling 2×2", "3×3×1×32 y 3×3×32×32", 9632),
    ("Bloque 2", 64, 16, "2 × (conv 3×3 + BN + ReLU), max pooling 2×2", "3×3×32×64 y 3×3×64×64", 55552),
    ("Bloque 3", 128, 8, "2 × (conv 3×3 + BN + ReLU), max pooling 2×2", "3×3×64×128 y 3×3×128×128", 221696),
    ("Bloque 4", 256, 4, "2 × (conv 3×3 + BN + ReLU), max pooling 2×2", "3×3×128×256 y 3×3×256×256", 885760),
    ("Vector", 128, 1, "Aplanar 4096 → dropout 0,2 → y = W·x + b → BN", "W: 4096×128, b: 128", 524672),
)
MAP_PARTS = ("private", "identity_labels.json")
NAME_MAP = Path(__file__).resolve().parents[1] / "private" / "external_frames_mapping_20261117.json"
DEFAULT_VAULT = Path("V:/FaceNexus")
DEFAULT_CAM_PORT = 8080
HISTORY_LIMIT = 40
CAMERA_MODEL = "identity_four_v2 · k-NN"
BOX_TTL = 0.45
RESULT_MAX_AGE = 1.0
DECISION_TTL = 1.0

SPANISH = {
    "K01": "K01",
    "K02": "K02",
    "K03": "K03",
    "K04": "K04",
    "UNKNOWN": "Desconocido",
    "GRANTED": "Autorizado",
    "DENIED": "Denegado",
    "authorized": "identidad con permiso",
    "no_face": "sin rostro",
    "unknown_identity": "identidad desconocida",
    "permission_inactive": "permiso inactivo",
    "model_unavailable": "modelo no verificado",
    "multiple_faces": "varios rostros ambiguos",
    "exception": "fallo interno",
    "not_human": "no humano",
    "SIGNAL_LOST": "Señal perdida",
    "STALE": "Espera",
    "REARM": "Pestillo rearmado",
    "stale_measurement": "sin medición reciente",
    "unauthorized_present": "hay una persona no autorizada en la escena",
    "camera_signal_lost": "se perdió la señal de la cámara",
}


def may_send_physical(source, kind, gate, recognition_actuation=False):
    """Solo la cámara en vivo acciona, y solo si el operador abrió con --actuate."""
    if source != "camera" or recognition_actuation is not True:
        return False
    return gate.on_frame(kind)


def _read_json_object(path):
    if not Path(path).is_file():
        return {}
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_identity_labels(vault, fallback=NAME_MAP):
    """Mapa privado código → etiqueta. Si falta, se usa el código."""
    labels = {}
    payload = _read_json_object(Path(vault).joinpath(*MAP_PARTS))
    for person in PEOPLE:
        value = payload.get(person)
        if isinstance(value, str) and value.strip():
            labels[person] = value.strip()
    if labels:
        return labels
    inverted = _read_json_object(fallback) if fallback else {}
    for name, code in inverted.items():
        if code in PEOPLE and isinstance(name, str) and name.strip() and code not in labels:
            labels[code] = name.strip()
    return labels


def display_person(person, labels):
    if person not in PEOPLE:
        return SPANISH.get(person, person)
    extra = labels.get(person)
    return f"{person} · {extra}" if extra else person


def decision_view(outcome, reason, identity, labels, face_seen=False):
    """Texto y color para autorización, denegación, espera o señal perdida."""
    if outcome == "GRANTED":
        tone, title = ACCENT, "Autorizado"
    elif outcome == "DENIED":
        tone, title = DENIED_INK, "Denegado"
    elif outcome == "SIGNAL_LOST":
        tone, title = WAIT_INK, "Señal perdida"
    else:
        tone, title = WAIT_INK, "Espera"
    if outcome == "SIGNAL_LOST" or not identity:
        who = "—"
    else:
        who = display_person(identity, labels)
    detail = SPANISH.get(reason, reason or "sin presentación")
    if outcome == "SIGNAL_LOST":
        detail = "sin fotograma de cámara; la autorización anterior no sigue vigente"
    elif outcome == "STALE":
        detail = "sin medición reciente; la autorización anterior no sigue vigente"
        who = "—"
    elif outcome == "DENIED" and reason == "unknown_identity" and face_seen:
        detail = "Rostro detectado · identidad no confirmada"
    return {
        "tone": tone,
        "title": title,
        "identity": who,
        "detail": f"{title} · {detail}",
        "caption": f"{who}",
    }


def technical_lines(scene, labels):
    """Causa, modelo y distancias. El candidato rechazado no autoriza."""
    if not scene:
        return "Sin medición."
    regions = scene.get("regions") or []
    if len(regions) > 1:
        return "\n\n".join(
            f"Rostro {index}\n{technical_lines(row, labels)}"
            for index, row in enumerate(regions, start=1)
        )
    row = next((item for item in regions if item.get("nearest")), regions[0] if regions else scene)
    nearest = row.get("nearest")
    access = display_person(scene.get("identity"), labels) if scene.get("identity") else "—"
    lines = [
        f"Modelo {row.get('model') or CAMERA_MODEL}",
        f"Causa: {SPANISH.get(scene.get('reason'), scene.get('reason') or '—')}",
        f"Identidad de acceso: {access}",
    ]
    if nearest:
        lines.append(f"Candidato diagnóstico: {display_person(nearest, labels)}")
    score = row.get("score_text")
    if score:
        lines.append(score)
    if "human" in row:
        lines.append(f"CNN humano/no humano (diagnóstico): {'humano' if row['human'] else 'no humano'}")
    return "\n".join(lines)


def history_key(scene, source):
    origin = "camera" if source == "camera" else str(source)
    return (scene.get("outcome"), scene.get("reason"), scene.get("identity"), origin)


def camera_config_path():
    root = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(root) / "FaceNexus" / "operator_camera.json"


def load_camera_config(path=None):
    payload = _read_json_object(path or camera_config_path())
    url = payload.get("url") if isinstance(payload.get("url"), str) else ""
    ip = payload.get("ip") if isinstance(payload.get("ip"), str) else ""
    port = payload.get("camera_port")
    rotation = payload.get("rotation", 0)
    try:
        rotation = int(rotation)
    except (TypeError, ValueError):
        rotation = 0
    if rotation not in ROTATE:
        rotation = 0
    raw_recent = payload.get("recent")
    recent = [
        {"url": item["url"], "rotation": item["rotation"]}
        for item in (raw_recent if isinstance(raw_recent, list) else [])
        if isinstance(item, dict) and isinstance(item.get("url"), str)
        and item.get("rotation") in ROTATE
    ][:RECENT_CAMERAS]
    return {
        "url": url.strip(),
        "ip": ip.strip(),
        "camera_port": str(port or DEFAULT_CAM_PORT),
        "rotation": rotation,
        "recent": recent,
    }


def _write_camera_config(payload, path):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def save_camera_config(url, ip, camera_port, rotation, path=None):
    path = Path(path or camera_config_path())
    return _write_camera_config({
        "url": url,
        "ip": ip,
        "camera_port": str(camera_port),
        "rotation": int(rotation),
        "recent": load_camera_config(path)["recent"],
    }, path)


def clamp_number(text, low, high, fallback):
    """Lee un número escrito a mano (acepta coma decimal) y lo ajusta al rango [low, high]."""
    try:
        value = float(str(text).strip().replace(",", "."))
    except ValueError:
        return fallback
    if not math.isfinite(value):
        return fallback
    return min(max(value, low), high)


def format_seconds(seconds):
    # Punto decimal en el campo: las flechas del Spinbox de Tk no leen la coma.
    return f"{seconds:.1f}"


def remember_camera(url, rotation, path=None):
    """Guarda una conexión que sí dio video; las más recientes primero, sin repetir."""
    path = Path(path or camera_config_path())
    config = load_camera_config(path)
    recent = [{"url": url, "rotation": int(rotation)}] + [
        item for item in config["recent"] if item["url"] != url]
    config["recent"] = recent[:RECENT_CAMERAS]
    return _write_camera_config(config, path)


def split_camera_fields(url):
    if not url:
        return "", str(DEFAULT_CAM_PORT)
    parts = urlsplit(url)
    host = parts.hostname or ""
    port = parts.port or DEFAULT_CAM_PORT
    return host, str(port)


class LatestSlot:
    """Un solo hueco: el consumidor siempre ve el ítem más reciente."""

    def __init__(self):
        self._lock = threading.Lock()
        self._item = None
        self.dropped = 0

    def put(self, item):
        with self._lock:
            if self._item is not None:
                self.dropped += 1
            self._item = item

    def peek(self):
        with self._lock:
            return self._item

    def clear(self):
        with self._lock:
            self._item = None


def open_cv_capture(url):
    capture = cv2.VideoCapture()
    ok = capture.open(url, cv2.CAP_FFMPEG, [
        cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3500, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 400,
    ])
    if not ok:
        capture.release()
        return None
    return capture


def launch_preflight(repo_root, vault=DEFAULT_VAULT):
    """Comprueba .venv y el volumen antes de abrir la interfaz."""
    python = Path(repo_root) / ".venv" / "Scripts" / "python.exe"
    if not python.is_file():
        return False, "Falta el entorno virtual .venv. Prepara el entorno en el repositorio."
    if not Path(vault).is_dir():
        return False, (
            "No está montado V:\\FaceNexus. Monta el volumen VeraCrypt y vuelve a abrir FaceNexus.")
    return True, str(python)


def _camera_port_number(port):
    try:
        number = int(str(port if port not in (None, "") else DEFAULT_CAM_PORT))
    except (TypeError, ValueError) as error:
        raise ValueError("El puerto de cámara debe ser un número, por ejemplo 8080.") from error
    if not 1 <= number <= 65535:
        raise ValueError("El puerto de cámara no es válido.")
    return number


def parse_camera_url(text, port=None):
    """IP, IP:puerto, o URL completa. El puerto serie no entra aquí."""
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Indica la IP local del celular.")
    try:
        if "://" not in raw and raw.count(":") == 1 and "/" not in raw:
            host, maybe_port = raw.split(":")
            if host and maybe_port.isdigit():
                number = _camera_port_number(maybe_port)
                return local_stream_url(f"http://{host}:{number}/video")
        if "://" in raw or "/" in raw:
            candidate = raw if "://" in raw else f"http://{raw}"
            parts = urlsplit(candidate)
            if not parts.path or parts.path == "/":
                candidate = urlunsplit((parts.scheme, parts.netloc, "/video", parts.query, ""))
            return local_stream_url(candidate)
        number = _camera_port_number(port)
        return local_stream_url(f"http://{raw}:{number}/video")
    except argparse.ArgumentTypeError as error:
        raise ValueError(
            "Indica la IP local del celular, IP:puerto o la URL HTTP del IP Webcam.") from error


def fit_bgr(frame, max_w, max_h):
    height, width = frame.shape[:2]
    scale = min(max(1, max_w) / width, max(1, max_h) / height, 1.)
    size = max(1, int(width * scale)), max(1, int(height * scale))
    if size != (width, height):
        frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
    return frame


def viewer_layout(frame, canvas_w, canvas_h):
    shown = fit_bgr(frame, canvas_w, canvas_h)
    shown_h, shown_w = shown.shape[:2]
    origin_x = (canvas_w - shown_w) // 2
    origin_y = (canvas_h - shown_h) // 2
    return shown, origin_x, origin_y, shown_w, shown_h


def face_style(item):
    """Color y texto por rostro: autorizado, permiso revocado o desconocido."""
    if item.get("granted"):
        return ACCENT_SOFT, "Autorizado"
    if item.get("reason") == "permission_inactive":
        return AMBER, "Permiso revocado"
    return REJECT, "Desconocido"


def overlay_boxes(scene):
    boxes = []
    for row in scene.get("regions") or []:
        box = row.get("box")
        if box:
            boxes.append({
                "box": list(box),
                "granted": row.get("outcome") == "GRANTED",
                "identity": row.get("identity") or "UNKNOWN",
                "reason": row.get("reason"),
                "human": row.get("human", True),
            })
    return boxes


class OperatorApp:
    def __init__(self, recognize, *, model_ready=True, reason="", url="", rotation=0,
                 port=None, labels=None, config_path=None, open_capture=None,
                 trial_info=None, model_loader=None, actuate=False):
        self._core = recognize
        # Sin --actuate la interfaz nunca envía órdenes físicas desde el reconocimiento.
        self.actuate = actuate is True and bool(port)
        self.model_ready = model_ready
        self.trial_info = trial_info or {}
        self.model_loader = model_loader
        self.open_capture = open_capture or open_cv_capture
        self.config_path = Path(config_path) if config_path else camera_config_path()
        saved = load_camera_config(self.config_path)
        self.url = url
        if not self.url and saved.get("url"):
            try:
                self.url = parse_camera_url(saved["url"])
            except ValueError:
                self.url = ""
        if not self.url and saved["ip"]:
            try:
                self.url = parse_camera_url(saved["ip"], saved["camera_port"])
            except ValueError:
                self.url = ""
        self.camera_ip, self.camera_port = split_camera_fields(self.url)
        if not self.camera_port:
            self.camera_port = saved["camera_port"]
        self.rotation_deg = rotation or saved["rotation"]
        self.rotation = ROTATE[self.rotation_deg]
        self.port = port
        self.labels = labels or {}
        self.connection = None
        self.capture = None
        self.latch_ok = False
        self.gate = PresentationGate()
        # Reglas de apertura ajustables por el operador (sección «Reglas de apertura»).
        self.hold_seconds = LATCH_HOLD_SECONDS
        self.require_everyone = False
        self.hold_note = ""
        # Motivo del bloqueo del pestillo, visible en el panel hasta que el operador rearme.
        self.block_reason = ""
        self.ack_text = "sin acuse"
        self.lock_text = "posición no confirmada · simulación"
        self.permissions = default_permissions()
        self.history = []
        self._hist_key = None
        self._hist_count = 0
        self._last_bgr = None
        self._frame_stale = False
        self.hold_file = False
        self._file_caption = False
        self._live_requested = False
        self.photo = None
        self.cam_state = "idle"
        self._cam_gen = 0
        self._stop = threading.Event()
        self._preview_slot = LatestSlot()
        self._result_slot = LatestSlot()
        self._seq = 0
        self._done_seq = 0
        self._shown_seq = 0
        self._published_seq = 0
        self._overlay = None
        self._view_seq = None
        self._paint_key = None
        self._live_decision = False
        self._live_decision_at = None
        self._ui_streak = 0
        self._latch_open_until = 0.0
        self._hist_time = ""
        self._capture_thread = None
        self._infer_thread = None
        self.metrics = {"view_fps": 0.0, "infer_ms": 0.0, "frame_age_ms": 0.0}
        self._view_times = []
        self._tick_alive = True
        self._ui_lock = threading.Lock()
        self._ui_queue = []
        self.window = tk.Tk()
        self.window.title("FaceNexus")
        self.window.configure(bg=BG)
        self.window.minsize(1100, 640)
        self.window.geometry("1280x720")
        self._build()
        if not model_ready:
            self._set_status(f"Modelo no verificado ({reason}). Todo denegado.")
        if port:
            self._open_port(port)
        self._refresh_rearm()

    def _schedule_tick(self):
        if self._tick_alive:
            self._tick_id = self.window.after(40, self._tick)

    def _mode_text(self):
        return "Pestillo activo" if self.actuate else "Simulación"

    def _font(self, size, *, bold=False):
        return ("Segoe UI", size, "bold" if bold else "normal")

    def _build(self):
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(1, weight=1)
        style = ttk.Style(self.window)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", font=self._font(10, bold=True), padding=(18, 6))

        bar = tk.Frame(self.window, bg=HEADER, padx=22, pady=12)
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)
        brand = tk.Frame(bar, bg=HEADER)
        brand.grid(row=0, column=0, sticky="w")
        tk.Label(brand, text=ICON_SHIELD, font=(ICON_FONT, 22), fg=ACCENT_SOFT, bg=HEADER
                 ).pack(side=tk.LEFT, padx=(0, 10))
        titles = tk.Frame(brand, bg=HEADER)
        titles.pack(side=tk.LEFT)
        tk.Label(titles, text="FaceNexus", font=self._font(18, bold=True), fg=SURFACE, bg=HEADER
                 ).pack(anchor="w")
        tk.Label(titles, text="Control de acceso por reconocimiento facial",
                 font=self._font(9), fg=HINT, bg=HEADER).pack(anchor="w")
        chips = tk.Frame(bar, bg=HEADER)
        chips.grid(row=0, column=1, sticky="e")
        self.chip_camera = self._chip(chips, "Celular")
        self.chip_latch = self._chip(chips, "ESP32")
        self.chip_mode = self._chip(chips, self._mode_text())
        self.model_banner = tk.Label(bar, text=self._model_name(), font=self._font(9),
                                     fg=HINT, bg=HEADER, anchor="e")
        self.model_banner.grid(row=1, column=1, sticky="e", pady=(6, 0))

        tabs = ttk.Notebook(self.window)
        tabs.grid(row=1, column=0, sticky="nsew", padx=16, pady=(12, 16))
        body = tk.Frame(tabs, bg=BG)
        tabs.add(body, text="Reconocimiento")
        servo = tk.Frame(tabs, bg=BG)
        tabs.add(servo, text="Pestillo (ESP32)")
        self._build_servo_tab(servo)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        stage = tk.Frame(body, bg=BG)
        stage.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=(8, 0))
        stage.rowconfigure(1, weight=1)
        stage.columnconfigure(0, weight=1)
        self.pipeline = tk.Frame(stage, bg=BG)
        self.pipeline.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.pipe_steps = {}
        for index, (key, text) in enumerate(PIPELINE_STEPS):
            if index:
                tk.Label(self.pipeline, text="→", font=self._font(11), fg=WAIT_INK,
                         bg=BG).pack(side=tk.LEFT, padx=4)
            step = tk.Label(self.pipeline, text=text, font=self._font(9, bold=True),
                            fg=WAIT_INK, bg=SURFACE, padx=10, pady=4)
            step.pack(side=tk.LEFT)
            self.pipe_steps[key] = step
        self.viewer = tk.Canvas(stage, bg=VIEWER, highlightthickness=0, cursor="arrow")
        self.viewer.grid(row=1, column=0, sticky="nsew")
        self.viewer.bind("<Configure>", lambda _event: self._paint_viewer(force=True))
        self._hint_id = None

        controls = tk.Frame(stage, bg=BG, pady=10)
        controls.grid(row=2, column=0, sticky="ew")
        # Conectar usa la última cámara guardada; el lápiz abre la ventana para cambiarla.
        self.cam_btn = self._button(controls, "Conectar celular",
                                    self._quick_connect, primary=True)
        self.cam_btn.pack(side=tk.LEFT)
        self.cam_edit_btn = self._button(controls, ICON_EDIT, self._camera_dialog, primary=True)
        self.cam_edit_btn.config(font=(ICON_FONT, 12), padx=10)
        self.cam_edit_btn.pack(side=tk.LEFT, fill="y", padx=(1, 0))
        self.stop_btn = self._button(controls, "Detener video", self._stop_camera)
        self.stop_btn.config(state="disabled")
        self.stop_btn.pack(side=tk.LEFT, padx=(8, 0))
        self._button(controls, "Abrir imagen", self._open_image
                     ).pack(side=tk.LEFT, padx=(8, 0))
        self._button(controls, "Probar carpeta", self._open_folder
                     ).pack(side=tk.LEFT, padx=(8, 0))
        self.rearm_btn = self._button(controls, "Rearmar pestillo", self._rearm)
        self.rearm_btn.pack(side=tk.LEFT, padx=(16, 0))
        self.cam_state_lbl = tk.Label(controls, text="", font=self._font(9, bold=True),
                                      fg=WAIT_INK, bg=BG)
        self.cam_state_lbl.pack(side=tk.LEFT, padx=(16, 0))
        self.hint_lbl = tk.Label(controls, text="", font=self._font(9), fg=WAIT_INK, bg=BG)
        self.hint_lbl.pack(side=tk.LEFT, padx=(8, 0))

        side_outer = tk.Frame(body, bg=BG, width=380)
        side_outer.grid(row=0, column=1, sticky="ns", pady=(8, 0))
        side_outer.grid_propagate(False)
        side_outer.rowconfigure(0, weight=1)
        side_outer.columnconfigure(0, weight=1)
        side_canvas = tk.Canvas(side_outer, bg=BG, highlightthickness=0, width=364)
        side_scroll = tk.Scrollbar(side_outer, orient="vertical", command=side_canvas.yview)
        side = tk.Frame(side_canvas, bg=BG)
        side.bind("<Configure>", lambda _e: side_canvas.configure(scrollregion=side_canvas.bbox("all")))
        side_canvas.create_window((0, 0), window=side, anchor="nw", width=364)
        side_canvas.configure(yscrollcommand=side_scroll.set)
        side_canvas.grid(row=0, column=0, sticky="nsew")
        side_scroll.grid(row=0, column=1, sticky="ns")
        side_canvas.bind_all(
            "<MouseWheel>", lambda e: side_canvas.yview_scroll(int(-e.delta / 120), "units"))

        # Tarjeta de decisión: lo primero que debe leerse.
        self.decision_card = tk.Frame(side, bg=WAIT_INK, padx=16, pady=14)
        self.decision_card.pack(fill="x")
        top = tk.Frame(self.decision_card, bg=WAIT_INK)
        top.pack(fill="x")
        self.decision_icon = tk.Label(top, text=ICON_LOCK, font=(ICON_FONT, 30), fg=SURFACE,
                                      bg=WAIT_INK)
        self.decision_icon.pack(side=tk.LEFT, padx=(0, 12))
        texts = tk.Frame(top, bg=WAIT_INK)
        texts.pack(side=tk.LEFT, fill="x", expand=True)
        self.decision_title = tk.Label(texts, text="En espera", font=self._font(17, bold=True),
                                       fg=SURFACE, bg=WAIT_INK, anchor="w")
        self.decision_title.pack(anchor="w")
        self.identity_lbl = tk.Label(texts, text="Identidad: —", font=self._font(12, bold=True),
                                     fg=SURFACE, bg=WAIT_INK, anchor="w", wraplength=250,
                                     justify="left")
        self.identity_lbl.pack(anchor="w")
        self.detail_lbl = tk.Label(self.decision_card, text="Aún no hay una presentación.",
                                   font=self._font(10), fg=SURFACE, bg=WAIT_INK, anchor="w",
                                   wraplength=330, justify="left")
        self.detail_lbl.pack(anchor="w", pady=(10, 0))
        self._card_widgets = [self.decision_card, top, texts, self.decision_icon,
                              self.decision_title, self.identity_lbl, self.detail_lbl]

        # Verificación continua y estado del pestillo (nodo IoT).
        latch = self._section(side, "Pestillo · nodo IoT")
        self.streak_lbl = tk.Label(latch, text="", font=self._font(9), fg=WAIT_INK, bg=SURFACE,
                                   anchor="w")
        self.streak_lbl.pack(anchor="w")
        self.streak_bar = tk.Canvas(latch, height=10, bg=TRACK, highlightthickness=0)
        self.streak_bar.pack(fill="x", pady=(4, 10))
        row = tk.Frame(latch, bg=SURFACE)
        row.pack(fill="x")
        self.latch_icon = tk.Label(row, text=ICON_LOCK, font=(ICON_FONT, 20), fg=WAIT_INK,
                                   bg=SURFACE)
        self.latch_icon.pack(side=tk.LEFT, padx=(0, 10))
        self.latch_state_lbl = tk.Label(row, text="Cerrado", font=self._font(13, bold=True),
                                        fg=INK, bg=SURFACE, anchor="w", justify="left")
        self.latch_state_lbl.pack(side=tk.LEFT, fill="x")
        self.latch_note_lbl = tk.Label(latch, text="", font=self._font(9, bold=True), fg=AMBER,
                                       bg=SURFACE, anchor="w", justify="left", wraplength=320)
        self.latch_note_lbl.pack(anchor="w")
        self.command_lbl = tk.Label(latch, text="Última etiqueta enviada: —", font=self._font(9),
                                    fg=WAIT_INK, bg=SURFACE, anchor="w", justify="left",
                                    wraplength=320)
        self.command_lbl.pack(anchor="w", pady=(8, 0))

        perms = self._section(side, "Permisos de acceso")
        self.perm_vars = {}
        for person in self.permissions:
            var = tk.BooleanVar(value=self.permissions[person])
            self.perm_vars[person] = var
            line = tk.Frame(perms, bg=SURFACE)
            line.pack(fill="x", pady=1)
            tk.Checkbutton(
                line, text=display_person(person, self.labels), variable=var,
                command=self._sync_permissions, font=self._font(10, bold=True), fg=INK,
                bg=SURFACE, activebackground=SURFACE, selectcolor=SURFACE, anchor="w",
            ).pack(side=tk.LEFT)
            state = tk.Label(line, text="", font=self._font(8, bold=True), bg=SURFACE, padx=6)
            state.pack(side=tk.RIGHT)
            var.trace_add("write", lambda *_a, v=var, s=state: self._paint_permission(v, s))
            self._paint_permission(var, state)

        hist = self._section(side, "Historial (sin imágenes)")
        log_frame = tk.Frame(hist, bg=SURFACE)
        log_frame.pack(fill="both", expand=True)
        scroll = tk.Scrollbar(log_frame)
        scroll.pack(side=tk.RIGHT, fill="y")
        self.log = tk.Listbox(
            log_frame, width=40, height=9, font=self._font(9), fg=INK, bg=SURFACE_ALT,
            relief="flat", yscrollcommand=scroll.set, activestyle="none", highlightthickness=0)
        self.log.pack(side=tk.LEFT, fill="both", expand=True)
        scroll.config(command=self.log.yview)

        technical = tk.Frame(tabs, bg=BG)
        tabs.add(technical, text="Datos técnicos")
        self._build_tech_tab(technical)
        network = tk.Frame(tabs, bg=BG)
        tabs.add(network, text="Red neuronal")
        self._build_network_tab(network)
        self._refresh_hw()
        self._refresh_live_panel()
        self._paint_viewer()

    def _chip(self, parent, text):
        chip = tk.Label(parent, text=f"●  {text}", font=self._font(9, bold=True),
                        fg=SURFACE, bg=CHIP_IDLE, padx=12, pady=5)
        chip.pack(side=tk.LEFT, padx=(8, 0))
        return chip

    def _set_chip(self, chip, text, color):
        if chip.cget("text") != text or chip.cget("bg") != color:
            chip.config(text=text, bg=color)

    def _button(self, parent, text, command, primary=False):
        background = ACCENT if primary else SURFACE
        return tk.Button(
            parent, text=text, command=command,
            font=self._font(11 if primary else 10, bold=primary),
            bg=background, fg=SURFACE if primary else INK,
            activebackground="#005955" if primary else HINT,
            activeforeground=SURFACE if primary else INK,
            disabledforeground=HINT, relief="flat", padx=16 if primary else 12, pady=8,
            cursor="hand2")

    def _section(self, parent, title):
        frame = tk.Frame(parent, bg=SURFACE, padx=14, pady=12)
        frame.pack(fill="x", pady=(10, 0))
        tk.Label(frame, text=title.upper(), font=self._font(8, bold=True), fg=WAIT_INK,
                 bg=SURFACE).pack(anchor="w", pady=(0, 6))
        return frame

    def _paint_permission(self, var, label):
        if var.get():
            label.config(text="ACTIVO", fg=ACCENT)
        else:
            label.config(text="REVOCADO", fg=DENIED_INK)

    def _model_name(self):
        ref = self.trial_info.get("label") or ""
        name = next((name for name, trial in MODEL_OPTIONS.items() if trial == ref), ref)
        return f"Modelo activo: {name}" if name else "Modelo activo: —"

    def _refresh_model_card(self):
        facts = MODEL_FACTS.get(self.trial_info.get("label"))
        # Las cifras medidas de cada variante están en las tablas de esta pestaña.
        text = facts or "Modelo de comparación. Sus cifras están en las tablas y en el informe."
        self.model_lbl.config(text=text)
        self.model_banner.config(text=self._model_name())

    def _select_model(self, _event=None):
        trial = MODEL_OPTIONS[self.model_selection.get()]
        previous = self.trial_info.get("label")
        if trial == previous:
            return
        self._stop_camera()
        try:
            core, ready, reason, info = self.model_loader(trial)
            if not ready:
                raise ValueError(reason or "Galería no verificada.")
        except (OSError, RuntimeError, ValueError) as error:
            previous_name = next((name for name, ref in MODEL_OPTIONS.items() if ref == previous), "")
            self.model_selection.set(previous_name)
            messagebox.showerror("Modelo", f"No se cargó el modelo seleccionado. {error}",
                                 parent=self.window)
            return
        self._core, self.model_ready, self.trial_info = core, ready, info
        self._last_bgr = None
        self.hold_file = self._frame_stale = self._file_caption = False
        self._show_decision({})
        self.history.clear()
        self.log.delete(0, tk.END)
        self._hist_key = None
        self._refresh_model_card()
        self._refresh_hw()
        self._set_status("Modelo cargado. Conecta el celular para empezar.")
        self._paint_viewer(force=True)

    def _build_tech_tab(self, page):
        """Medición en vivo, modelo activo y las tablas medidas que respaldan la elección."""
        page.columnconfigure(1, weight=1)
        page.columnconfigure(2, weight=1)
        page.rowconfigure(0, weight=1)

        live = tk.Frame(page, bg=BG, width=380)
        live.grid(row=0, column=0, sticky="nsw", padx=(0, 12), pady=(0, 8))
        live.grid_propagate(False)
        live.columnconfigure(0, weight=1)
        model = self._section(live, "Modelo activo")
        self.model_lbl = tk.Label(model, text="", font=self._font(9), fg=INK, bg=SURFACE,
                                  anchor="w", justify="left", wraplength=330)
        self.model_lbl.pack(anchor="w")
        tk.Label(model, font=self._font(9), fg=WAIT_INK, bg=SURFACE, anchor="w", justify="left",
                 wraplength=330,
                 text="Regla de aceptación: d₁ ≤ T y d₂ − d₁ ≥ G, donde d₁ es la distancia al "
                      "integrante más cercano y d₂ al siguiente integrante distinto. Después se "
                      "revisa el permiso y la regla de la escena.").pack(anchor="w", pady=(8, 0))
        if self.model_loader is not None and not self.port:
            names = {trial: name for name, trial in MODEL_OPTIONS.items()}
            self.model_selection = tk.StringVar(value=names.get(self.trial_info.get("label"), ""))
            ttk.Label(model, text="Cambiar modelo para comparar", background=SURFACE
                      ).pack(anchor="w", pady=(8, 2))
            selector = ttk.Combobox(model, textvariable=self.model_selection,
                                    values=list(MODEL_OPTIONS), state="readonly")
            selector.pack(fill="x")
            selector.bind("<<ComboboxSelected>>", self._select_model)
        self._refresh_model_card()

        measure = self._section(live, "Último fotograma analizado")
        self.tech_lbl = tk.Label(measure, text="", font=("Consolas", 9), fg=INK, bg=SURFACE,
                                 anchor="w", justify="left", wraplength=330)
        self.tech_lbl.pack(anchor="w")
        self._scene = {}
        system = self._section(live, "Rendimiento y hardware")
        self.perf_lbl = tk.Label(system, text="", font=self._font(9), fg=INK, bg=SURFACE,
                                 anchor="w", justify="left")
        self.perf_lbl.pack(anchor="w")
        self.hw_lbl = tk.Label(system, text="", font=self._font(9), fg=WAIT_INK, bg=SURFACE,
                               wraplength=330, justify="left", anchor="w")
        self.hw_lbl.pack(anchor="w", pady=(6, 0))
        self.status = tk.Label(system, text="Listo", font=self._font(9), fg=WAIT_INK, bg=SURFACE,
                               wraplength=330, justify="left", anchor="w")
        self.status.pack(anchor="w", pady=(4, 0))

        # Las tablas medidas se reparten en dos columnas para verse sin desplazarse.
        columns = [tk.Frame(page, bg=BG) for _ in range(2)]
        for index, column in enumerate(columns, start=1):
            column.grid(row=0, column=index, sticky="nsew", padx=(0, 12 if index == 1 else 0))
        for index, table in enumerate(RESULT_TABLES):
            self._result_table(columns[0 if index < 3 else 1], *table)
        tk.Label(columns[1], text="* variante en uso. Cifras medidas y registradas en el informe.",
                 font=self._font(8), fg=WAIT_INK, bg=BG).pack(anchor="w", pady=(8, 0))
        self._refresh_tech()

    def _build_network_tab(self, page):
        """Explica la CNN propia: diagrama de capas, pesos, parámetros y entrenamiento."""
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)
        diagram = self._section(page, "CNN propia de identidad (PyTorch, entrenada desde cero)")
        diagram.pack_configure(fill="both", expand=True)
        self.network_canvas = tk.Canvas(diagram, bg=SURFACE, highlightthickness=0, height=300)
        self.network_canvas.pack(fill="both", expand=True)
        self.network_canvas.bind("<Configure>", lambda _event: self._draw_network())

        bottom = tk.Frame(page, bg=BG)
        bottom.pack(fill="x")
        bottom.columnconfigure(0, weight=3)
        bottom.columnconfigure(1, weight=2)
        layers = tk.Frame(bottom, bg=BG)
        layers.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        rows = [(name, f"{channels}×{side}×{side}" if side > 1 else str(channels), operation,
                 weights, f"{params:,}".replace(",", " ") if params else "—")
                for name, channels, side, operation, weights, params in NETWORK_LAYERS]
        total = sum(layer[5] for layer in NETWORK_LAYERS)
        rows.append(("Total en uso *", "rostro → 128", "", "", f"{total:,}".replace(",", " ")))
        self._result_table(layers, "Capas, pesos y parámetros",
                           "Cada convolución tiene un filtro de 3×3 por canal de entrada y de salida.",
                           ("Capa", "Salida", "Operación", "Pesos", "Parámetros"), rows)
        explain = tk.Frame(bottom, bg=BG)
        explain.grid(row=0, column=1, sticky="nsew")
        training = self._section(explain, "Cómo aprendió")
        tk.Label(training, font=self._font(9), fg=INK, bg=SURFACE, anchor="w", justify="left",
                 wraplength=600,
                 text="• Cada filtro de 3×3 recorre la imagen y responde a un patrón: los primeros "
                      "bloques detectan bordes, los siguientes partes del rostro y los últimos "
                      "rasgos que distinguen a una persona.\n"
                      "• Cada bloque reduce la imagen a la mitad y duplica los filtros.\n"
                      "• La última capa es y = W·x + b: convierte 4096 valores en un vector de 128, "
                      "la «huella» del rostro.\n"
                      "• Para entrenar se agregó una capa CosFace de 128 × 5000 (una neurona por "
                      "identidad sintética de HyperFace, s = 30, m = 0,35). Obliga a que la huella "
                      "quede más cerca de su identidad que de cualquier otra, con margen. Al terminar "
                      "se descarta: el k-NN compara huellas.\n"
                      "• 259 980 imágenes, 10 épocas de unos 50 s, AdamW, lotes de 256. "
                      "Pérdida 15,57 → 1,74; TAR@FAR 1 % en identidades no vistas: 81,9 % → 99,0 %.\n"
                      "• Se exporta a ONNX y se ejecuta con OpenCV en 22 a 33 ms por fotograma."
                 ).pack(anchor="w")

    def _draw_network(self):
        """Cada capa es un prisma: alto según el lado de la imagen, ancho según los canales."""
        canvas = self.network_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 200)
        height = max(canvas.winfo_height(), 200)
        slot = width / len(NETWORK_LAYERS)
        top_space = 60
        previous_right = None
        usable = height - top_space - 70
        for index, (name, channels, side, _operation, _weights, _params) in enumerate(NETWORK_LAYERS):
            # Escala logarítmica para que 4×4 y 64×64 se vean a la vez.
            box_h = max(14, usable * (math.log2(side) + 1) / 7)
            box_w = 14 + 12 * math.log2(channels) if side > 1 else 22
            center_x = slot * index + slot / 2
            center_y = top_space + usable / 2
            x0, y0 = center_x - box_w / 2, center_y - box_h / 2
            depth = min(18, box_h / 4)
            fill = ACCENT_SOFT if 0 < index < len(NETWORK_LAYERS) - 1 else ACCENT
            canvas.create_polygon(x0, y0, x0 + depth, y0 - depth, x0 + box_w + depth, y0 - depth,
                                  x0 + box_w, y0, fill=TRACK, outline=INK)
            canvas.create_polygon(x0 + box_w, y0, x0 + box_w + depth, y0 - depth,
                                  x0 + box_w + depth, y0 + box_h - depth, x0 + box_w, y0 + box_h,
                                  fill=HINT, outline=INK)
            canvas.create_rectangle(x0, y0, x0 + box_w, y0 + box_h, fill=fill, outline=INK)
            shape = f"{channels}×{side}×{side}" if side > 1 else f"{channels} valores"
            canvas.create_text(center_x, top_space - 40, text=name, fill=INK,
                               font=self._font(10, bold=True))
            canvas.create_text(center_x, top_space + usable + 22, text=shape, fill=INK,
                               font=self._font(10))
            if previous_right is not None:
                canvas.create_line(previous_right + 10, center_y, x0 - 10, center_y,
                                   arrow=tk.LAST, fill=WAIT_INK, width=2)
            previous_right = x0 + box_w + depth
        canvas.create_text(width / 2, height - 18, fill=WAIT_INK, font=self._font(9),
                           text="Alto: lado de la imagen (64 → 4 píxeles). Ancho: número de filtros "
                                "(1 → 256). Al final, un vector de 128 que el k-NN compara.")

    def _result_table(self, parent, title, note, headers, rows):
        frame = self._section(parent, title)
        if note:
            tk.Label(frame, text=note, font=self._font(8), fg=WAIT_INK, bg=SURFACE, anchor="w",
                     justify="left", wraplength=560).pack(anchor="w", pady=(0, 6))
        grid = tk.Frame(frame, bg=SURFACE)
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1)
        for column, text in enumerate(headers):
            tk.Label(grid, text=text, font=self._font(8, bold=True), fg=WAIT_INK, bg=SURFACE,
                     anchor="w" if column == 0 else "e").grid(row=0, column=column, sticky="ew",
                                                             padx=(0, 10))
        for row_index, row in enumerate(rows, start=1):
            in_use = row[0].endswith("*")
            for column, text in enumerate(row):
                tk.Label(grid, text=text, font=self._font(9, bold=in_use),
                         fg=ACCENT if in_use else INK, bg=SURFACE,
                         anchor="w" if column == 0 else "e").grid(
                    row=row_index, column=column, sticky="ew", padx=(0, 10), pady=1)

    def _build_servo_tab(self, page):
        panel = tk.Frame(page, bg=SURFACE, padx=24, pady=20)
        panel.pack(anchor="nw", fill="x", padx=16, pady=16)
        tk.Label(panel, text="Pestillo · ESP32 + servomotor SG90", font=self._font(18, bold=True),
                 bg=SURFACE, fg=INK).pack(anchor="w")
        tk.Label(
            panel, justify="left", anchor="w", bg=SURFACE, fg=WAIT_INK, font=self._font(10),
            wraplength=760,
            text=("Nodo de actuación del sistema. Windows envía por USB serie la etiqueta "
                  "«CHECK <evento> <K01–K04> GRANTED» mientras haya un integrante autorizado, "
                  "renovándola cada 0,5 s. El ESP32 abre a "
                  f"{SERVO_OPEN}° (señal PWM en GPIO25) y, si pasa el tiempo de cierre sin "
                  "renovación (3 s por defecto, ajustable abajo), cierra "
                  f"solo a {SERVO_CLOSED}°: ante cualquier falla el pestillo queda cerrado.")
        ).pack(anchor="w", pady=(6, 0))
        tk.Label(panel, text="PRUEBA MANUAL", font=self._font(8, bold=True), fg=WAIT_INK,
                 bg=SURFACE).pack(anchor="w", pady=(18, 0))
        ttk.Label(panel, text="Puerto del ESP32").pack(anchor="w", pady=(8, 4))
        self.servo_port = tk.StringVar(value="COM5")
        ttk.Entry(panel, textvariable=self.servo_port, width=12).pack(anchor="w")
        actions = tk.Frame(panel, bg=SURFACE)
        actions.pack(anchor="w", pady=(12, 0))
        self.servo_buttons = []
        for text, action, angle in (
            ("Verificar ESP32", "check", None),
            (f"Ir a cierre ({SERVO_CLOSED}°)", "move", SERVO_CLOSED),
            (f"Ir a apertura ({SERVO_OPEN}°)", "move", SERVO_OPEN),
            ("Probar ciclo", "cycle", None),
        ):
            button = ttk.Button(actions, text=text,
                                command=lambda a=action, d=angle: self._test_servo(a, d))
            button.pack(side="left", padx=(0, 8))
            self.servo_buttons.append(button)
        manual = tk.Frame(panel, bg=SURFACE)
        manual.pack(anchor="w", pady=12)
        ttk.Label(manual, text=f"Ángulo ({SERVO_MIN}° a {SERVO_MAX}°)").pack(side="left")
        self.servo_angle = tk.StringVar(value="45")
        ttk.Spinbox(manual, from_=SERVO_MIN, to=SERVO_MAX, textvariable=self.servo_angle,
                    width=6).pack(side="left", padx=8)
        move = ttk.Button(manual, text="Mover", command=lambda: self._test_servo("move"))
        move.pack(side="left")
        self.servo_buttons.append(move)
        self.servo_status = tk.StringVar(value="Selecciona una operación. Verifica el recorrido visualmente.")
        ttk.Label(panel, textvariable=self.servo_status, wraplength=680).pack(anchor="w")

        # Reglas de apertura: viven junto al pestillo porque gobiernan cuándo se le envía la orden.
        rules = tk.Frame(page, bg=SURFACE, padx=24, pady=20)
        rules.pack(anchor="nw", fill="x", padx=16, pady=(0, 16))
        tk.Label(rules, text="REGLAS DE APERTURA", font=self._font(8, bold=True), fg=WAIT_INK,
                 bg=SURFACE).pack(anchor="w", pady=(0, 6))
        self.policy_var = tk.StringVar(value="any")
        for value, text in (("any", "Basta un integrante autorizado"),
                            ("all", "Todos los rostros deben estar autorizados")):
            tk.Radiobutton(rules, text=text, value=value, variable=self.policy_var,
                           command=self._apply_rules, font=self._font(9), fg=INK, bg=SURFACE,
                           activebackground=SURFACE, selectcolor=SURFACE, anchor="w",
                           wraplength=300, justify="left").pack(anchor="w")
        self.frames_var = tk.StringVar(value=str(self.gate.consensus_frames))
        self.hold_var = tk.StringVar(value=format_seconds(self.hold_seconds))
        # Se escriben a mano (Enter o salir del campo aplica) o con las flechas.
        for text, variable, low, high, step in (
                ("Fotogramas seguidos para abrir", self.frames_var, FRAMES_MIN, FRAMES_MAX, 1),
                ("Segundos para cerrar tras salir", self.hold_var,
                 HOLD_MIN_SECONDS, HOLD_MAX_SECONDS, 0.5)):
            line = tk.Frame(rules, bg=SURFACE)
            line.pack(anchor="w", pady=(6, 0))
            tk.Label(line, text=text, font=self._font(9), fg=INK, bg=SURFACE, width=30,
                     anchor="w").pack(side=tk.LEFT)
            box = ttk.Spinbox(line, from_=low, to=high, increment=step, width=5,
                              textvariable=variable, command=self._apply_rules)
            box.pack(side=tk.LEFT)
            box.bind("<Return>", lambda _event: self._apply_rules())
            box.bind("<KP_Enter>", lambda _event: self._apply_rules())
            box.bind("<FocusOut>", lambda _event: self._apply_rules())
        self.rules_lbl = tk.Label(rules, text="", font=self._font(8), fg=WAIT_INK, bg=SURFACE,
                                  anchor="w", justify="left", wraplength=760)
        self.rules_lbl.pack(anchor="w", pady=(6, 0))
        self._describe_rules()

    def _set_status(self, text):
        self.status.config(text=text)

    def _overlay_key(self):
        layer = self._overlay
        if not layer:
            return None
        return (layer["until"], len(layer["boxes"]), layer["gen"])

    def _paint_viewer(self, force=False):
        width = max(self.viewer.winfo_width(), 2)
        height = max(self.viewer.winfo_height(), 2)
        key = (self._view_seq, self._overlay_key(), self._file_caption, self._frame_stale, width, height)
        if not force and key == self._paint_key and self._last_bgr is not None:
            return
        self._paint_key = key
        self.viewer.delete("all")
        self.viewer.create_rectangle(0, 0, width, height, fill=VIEWER, outline="")
        if self._last_bgr is None:
            self.viewer.create_text(
                width // 2, height // 2, text="Abre una imagen o conecta la cámara",
                fill=HINT, font=self._font(14), tags="hint")
            return
        shown, origin_x, origin_y, shown_w, shown_h = viewer_layout(self._last_bgr, width, height)
        rgb = cv2.cvtColor(shown, cv2.COLOR_BGR2RGB)
        header = f"P6 {rgb.shape[1]} {rgb.shape[0]} 255 ".encode("ascii")
        self.photo = tk.PhotoImage(master=self.viewer, data=header + rgb.tobytes())
        self.viewer.create_image(width // 2, height // 2, image=self.photo, anchor="center")
        self._draw_overlay(origin_x, origin_y, shown_w, shown_h)
        if self._file_caption:
            self.viewer.create_text(
                width // 2, height - 28, text="Predicción de archivo",
                fill=HINT, font=self._font(12), tags="file")
        elif self._frame_stale:
            self.viewer.create_text(
                width // 2, height - 28, text="Anterior · señal perdida",
                fill=HINT, font=self._font(12), tags="stale")

    def _draw_overlay(self, origin_x, origin_y, shown_w, shown_h):
        layer = self._overlay
        if not layer:
            return
        src_h, src_w = layer["size"]
        if src_w < 1 or src_h < 1:
            return
        for item in layer["boxes"]:
            left, top, right, bottom = item["box"]
            x0 = origin_x + left * shown_w / src_w
            y0 = origin_y + top * shown_h / src_h
            x1 = origin_x + right * shown_w / src_w
            y1 = origin_y + bottom * shown_h / src_h
            color, status = face_style(item)
            self._draw_brackets(x0, y0, x1, y1, color)
            name = display_person(item["identity"], self.labels)
            lines = [(name, self._font(11, bold=True)), (status, self._font(9)),
                     # YuNet confirma el rostro humano en vivo; la CNN binaria va al detalle técnico.
                     ("Rostro humano (YuNet)", self._font(8))]
            self._draw_tag(x0, y0, x1, lines, color)

    def _draw_brackets(self, x0, y0, x1, y1, color):
        """Esquinas marcadas y un contorno fino: se ve el rostro sin taparlo."""
        size = max(12, min(x1 - x0, y1 - y0) * 0.22)
        self.viewer.create_rectangle(x0, y0, x1, y1, outline=color, width=1, tags="box")
        for cx, cy, dx, dy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
            self.viewer.create_line(cx, cy, cx + dx * size, cy, fill=color, width=5,
                                    capstyle="round", tags="box")
            self.viewer.create_line(cx, cy, cx, cy + dy * size, fill=color, width=5,
                                    capstyle="round", tags="box")

    def _draw_tag(self, x0, y0, x1, lines, color):
        """Etiqueta sobre el recuadro: nombre, estado y confirmación de rostro humano."""
        pad, gap = 10, 2
        widths, heights = [], []
        for text, font in lines:
            probe = self.viewer.create_text(0, 0, text=text, font=font, anchor="nw")
            bx0, by0, bx1, by1 = self.viewer.bbox(probe)
            self.viewer.delete(probe)
            widths.append(bx1 - bx0)
            heights.append(by1 - by0)
        width = max(max(widths) + 2 * pad, x1 - x0)
        height = sum(heights) + gap * (len(lines) - 1) + 2 * pad
        top = y0 - height - 6
        if top < 4:
            top = y0 + 6
        self.viewer.create_rectangle(x0, top, x0 + width, top + height, fill=TAG_BG,
                                     outline=color, width=2, tags="face_label")
        self.viewer.create_rectangle(x0, top, x0 + 6, top + height, fill=color, outline="",
                                     tags="face_label")
        y = top + pad
        for (text, font), line_h, tone in zip(lines, heights, (SURFACE, color, HINT), strict=False):
            self.viewer.create_text(x0 + pad + 4, y, text=text, font=font, fill=tone,
                                    anchor="nw", tags="face_label")
            y += line_h + gap

    def _set_cam_state(self, state, text=""):
        self.cam_state = state
        labels = {
            "connecting": "Conectando",
            "live": "En vivo",
            "lost": "Señal perdida",
            "stopped": "Video detenido",
            "idle": "",
        }
        self.cam_state_lbl.config(text=text or labels.get(state, ""))
        colors = {"live": ACCENT, "connecting": AMBER, "lost": DENIED_INK}
        self._set_chip(self.chip_camera, f"●  Celular · {labels.get(state) or 'sin conectar'}",
                       colors.get(state, CHIP_IDLE))
        live = state in ("connecting", "live", "lost") and not self._stop.is_set()
        self.stop_btn.config(state=("normal" if live or self.capture is not None else "disabled"))

    def _show_decision(self, scene):
        self._scene = scene
        face_seen = bool(scene.get("regions"))
        view = decision_view(scene.get("outcome"), scene.get("reason"), scene.get("identity"),
                             self.labels, face_seen=face_seen)
        outcome = scene.get("outcome")
        if outcome == "GRANTED":
            tone, icon, title = ACCENT, ICON_UNLOCK, "Acceso concedido"
        elif outcome == "DENIED" and scene.get("reason") == "no_face":
            tone, icon, title = WAIT_INK, ICON_LOCK, "Sin rostro"
        elif outcome == "DENIED":
            tone, icon, title = DENIED_INK, ICON_LOCK, "Acceso denegado"
        elif outcome == "SIGNAL_LOST":
            tone, icon, title = WAIT_INK, ICON_WARNING, "Señal perdida"
        else:
            tone, icon, title = WAIT_INK, ICON_LOCK, "En espera"
        for widget in self._card_widgets:
            widget.config(bg=tone)
        self.decision_icon.config(text=icon)
        self.decision_title.config(text=title, fg=SURFACE)
        regions = scene.get("regions") or []
        if len(regions) > 1:
            identities = [display_person(row.get("identity") or "UNKNOWN", self.labels)
                          for row in regions]
            self.identity_lbl.config(text=f"{len(regions)} rostros: " + ", ".join(identities))
        else:
            self.identity_lbl.config(text=view["identity"])
        reason = SPANISH.get(scene.get("reason"), scene.get("reason") or "sin presentación")
        if outcome == "DENIED" and scene.get("reason") == "unknown_identity" and face_seen:
            reason = "rostro humano detectado, pero no coincide con ningún integrante"
        elif outcome == "GRANTED" and len(regions) > 1:
            reason = "al menos un integrante con permiso en la escena"
        self.detail_lbl.config(text=f"Motivo: {reason}")
        self._refresh_tech()

    def _refresh_live_panel(self):
        """Racha de verificación, estado estimado del pestillo y recorrido del dato."""
        now = monotonic()
        needed = self.gate.consensus_frames
        streak = min(self._ui_streak, needed)
        width = max(self.streak_bar.winfo_width(), 2)
        self.streak_bar.delete("all")
        fill = ACCENT if streak >= needed else ACCENT_SOFT
        self.streak_bar.create_rectangle(0, 0, width * streak / needed, 10,
                                         fill=fill, outline="")
        blocked = self.actuate and not self.gate.can_send
        if streak >= needed and blocked:
            text = "Identidad confirmada, pero el pestillo espera rearme"
        elif streak >= needed:
            text = f"Identidad confirmada en {needed} fotogramas seguidos"
        elif streak:
            text = f"Verificando identidad… {streak}/{needed} fotogramas"
        else:
            text = f"Abre tras {needed} fotogramas autorizados seguidos"
        self.streak_lbl.config(text=text)
        note = (f"Motivo: {self.block_reason or 'falla detectada'}. "
                "Pulsa «Rearmar pestillo» para volver a enviar órdenes." if blocked else "")
        if self.latch_note_lbl.cget("text") != note:
            self.latch_note_lbl.config(text=note)
        remaining = self._latch_open_until - now
        if not self.actuate:
            self.latch_icon.config(text=ICON_LOCK, fg=WAIT_INK)
            self.latch_state_lbl.config(
                text="Simulación\n" + ("abriría ahora" if streak >= needed
                                       else "no se envían órdenes"), fg=WAIT_INK)
        elif blocked:
            # Tras una falla no se envían órdenes; el ESP32 ya cerró solo por falta de renovación.
            self.latch_icon.config(text=ICON_WARNING, fg=AMBER)
            self.latch_state_lbl.config(text="BLOQUEADO", fg=AMBER)
        elif remaining > 0:
            self.latch_icon.config(text=ICON_UNLOCK, fg=ACCENT)
            self.latch_state_lbl.config(
                text=f"ABIERTO\ncierra en {remaining:.1f} s".replace(".", ","), fg=ACCENT)
        else:
            self.latch_icon.config(text=ICON_LOCK, fg=INK)
            self.latch_state_lbl.config(text="CERRADO", fg=INK)
        perf = (f"Vista: {self.metrics['view_fps']:.0f} fps · "
                f"inferencia: {self.metrics['infer_ms']:.0f} ms\n"
                f"Edad del fotograma mostrado: {self.metrics['frame_age_ms']:.0f} ms")
        if self.perf_lbl.cget("text") != perf:
            self.perf_lbl.config(text=perf)
        camera_ok = self.cam_state == "live"
        states = {
            "phone": camera_ok,
            "detect": camera_ok and bool(self._scene.get("regions")),
            "identify": camera_ok and bool(self._scene.get("regions")),
            "decide": camera_ok and self._scene.get("outcome") == "GRANTED",
            "esp32": self.actuate and remaining > 0,
        }
        for key, label in self.pipe_steps.items():
            on = states.get(key, False)
            label.config(bg=ACCENT if on else SURFACE, fg=SURFACE if on else WAIT_INK)


    def _refresh_tech(self):
        self.tech_lbl.config(text=trial_banner(self.trial_info) + technical_lines(self._scene, self.labels))

    def _refresh_rearm(self):
        self.rearm_btn.config(state=("normal" if not self.gate.can_send else "disabled"))

    def _rearm(self):
        # Si una falla serie cerró el puerto, rearmar lo vuelve a abrir y verificar con PING;
        # sin un PONG válido el pestillo sigue bloqueado.
        if self.port and self.connection is None:
            self._open_port(self.port)
            if not self.latch_ok:
                self._refresh_rearm()
                return
        self.gate.rearm()
        self.block_reason = ""
        self._record({"outcome": "REARM", "reason": "rearm", "identity": None}, "operador")
        self._refresh_rearm()

    def _apply_rules(self):
        """Lee las reglas (escritas a mano o con flechas), las ajusta al rango y las aplica."""
        require_everyone = self.policy_var.get() == "all"
        frames = round(clamp_number(self.frames_var.get(), FRAMES_MIN, FRAMES_MAX,
                                    self.gate.consensus_frames))
        seconds = round(clamp_number(self.hold_var.get(), HOLD_MIN_SECONDS, HOLD_MAX_SECONDS,
                                     self.hold_seconds), 1)
        self.frames_var.set(str(frames))
        self.hold_var.set(format_seconds(seconds))
        if (require_everyone, frames) != (self.require_everyone, self.gate.consensus_frames):
            self.require_everyone = require_everyone
            self.gate.consensus_frames = frames
            # Cambiar una regla exige una racha nueva medida con la regla nueva.
            self.gate.interrupt()
            self._ui_streak = 0
        if seconds != self.hold_seconds:
            self.hold_seconds = seconds
            self._push_hold()
        self._describe_rules()

    def _push_hold(self):
        """Envía el tiempo de cierre al ESP32; sin conexión se envía al conectar."""
        self.hold_note = ""
        if self.connection is None or not self.latch_ok:
            return
        try:
            set_hold(self.connection, self.hold_seconds)
        except (OSError, RuntimeError, TimeoutError, ValueError):
            # Firmware anterior sin HOLD: sigue cerrando a los 3 s de fábrica.
            self.hold_seconds = LATCH_HOLD_SECONDS
            self.hold_var.set(format_seconds(LATCH_HOLD_SECONDS))
            self.hold_note = ("El ESP32 no aceptó el cambio (carga el firmware actualizado); "
                              f"cierra a los {LATCH_HOLD_SECONDS} s.")

    def _describe_rules(self):
        frames = self.gate.consensus_frames
        seconds = f"{frames / 13:.1f}".replace(".", ",")
        hold = format_seconds(self.hold_seconds).replace(".", ",")
        text = (f"Abre tras {frames} fotogramas autorizados seguidos (≈ {seconds} s a 13 fps). "
                f"El ESP32 cierra solo {hold} s después del último autorizado.")
        if frames < 8:
            text += " Con menos de 8 fotogramas los rechazos de desconocidos no están medidos."
        if self.hold_note:
            text += " " + self.hold_note
        self.rules_lbl.config(text=text)

    def _sync_permissions(self):
        for person, var in self.perm_vars.items():
            self.permissions[person] = bool(var.get())

    def _open_port(self, port):
        try:
            self.connection = open_latch_port(port)
            pong = ping_firmware(self.connection)
            self.latch_ok = latch_ready(pong)
            self.ack_text = pong
            if self.latch_ok:
                self._push_hold()
                self._describe_rules()
            else:
                self.connection.close()
                self.connection = None
                self.lock_text = "simulación · firmware no LATCH"
                messagebox.showwarning("Serie", f"Firmware {pong}. No se envían órdenes.")
        except (OSError, ValueError, TimeoutError) as error:
            messagebox.showwarning("Serie", f"No se abrió {port}: {error}")
            self._invalidate_port()
        self._refresh_hw()

    def _invalidate_port(self):
        if self.connection is not None:
            try:
                self.connection.close()
            except OSError:
                pass
        self.connection = None
        self.latch_ok = False
        self.gate.note_fault()
        self.block_reason = "falla de comunicación con el ESP32"
        self.lock_text = "simulación · puerto invalidado"
        self._refresh_rearm()

    def _quick_connect(self):
        """Conecta a la última cámara usada; sin una guardada abre la ventana Cámara."""
        if self.url:
            self._start_camera()
        else:
            self._camera_dialog()

    def _camera_dialog(self):
        dialog = tk.Toplevel(self.window)
        dialog.title("Cámara")
        dialog.configure(bg=SURFACE)
        dialog.transient(self.window)
        dialog.grab_set()
        ip_value, port_value = split_camera_fields(self.url)
        tk.Label(dialog, text="IP del celular", font=self._font(10), fg=INK, bg=SURFACE
                 ).pack(anchor="w", padx=16, pady=(16, 4))
        ip_var = tk.StringVar(value=ip_value or self.camera_ip)
        # La lista ofrece las últimas conexiones que dieron video; también se puede escribir.
        recent = {}
        for item in load_camera_config(self.config_path)["recent"]:
            ip, port = split_camera_fields(item["url"])
            recent[f"{ip}:{port} · {item['rotation']}°"] = (ip, port, item["rotation"])
        entry = ttk.Combobox(dialog, textvariable=ip_var, values=list(recent), width=40,
                             font=self._font(10))
        entry.pack(padx=16, fill="x")

        def pick_recent(_event=None):
            ip, port, rotation = recent[ip_var.get()]
            ip_var.set(ip)
            port_var.set(port)
            rot_var.set(rotation)

        entry.bind("<<ComboboxSelected>>", pick_recent)
        tk.Label(dialog, text="Puerto de cámara", font=self._font(10), fg=INK, bg=SURFACE
                 ).pack(anchor="w", padx=16, pady=(12, 4))
        port_var = tk.StringVar(value=port_value or str(DEFAULT_CAM_PORT))
        tk.Entry(dialog, textvariable=port_var, width=12, font=self._font(10)).pack(
            padx=16, anchor="w")
        tk.Label(dialog, text="Orientación", font=self._font(10), fg=INK, bg=SURFACE
                 ).pack(anchor="w", padx=16, pady=(12, 4))
        rot_var = tk.IntVar(value=self.rotation_deg)
        rot = ttk.Combobox(dialog, textvariable=rot_var, values=(0, 90, 180, 270), state="readonly")
        rot.pack(padx=16, fill="x")
        note = tk.Label(
            dialog,
            text="IP Webcam: 192.168.1.20 y puerto 8080, o 192.168.1.20:8080, o la URL completa. "
                 "Despliega la lista para usar una de las últimas conexiones. "
                 "El puerto serie del pestillo es otro campo.",
            font=self._font(8), fg=WAIT_INK, bg=SURFACE, wraplength=360, justify="left")
        note.pack(anchor="w", padx=16, pady=8)

        def connect():
            if ip_var.get() in recent:
                pick_recent()
            try:
                self.url = parse_camera_url(ip_var.get(), port_var.get())
            except ValueError as error:
                note.config(text=str(error), fg=DENIED_INK)
                return
            self.camera_ip, self.camera_port = split_camera_fields(self.url)
            self.rotation_deg = int(rot_var.get())
            self.rotation = ROTATE[self.rotation_deg]
            saved = save_camera_config(
                self.url, self.camera_ip, self.camera_port, self.rotation_deg,
                self.config_path)
            dialog.destroy()
            if not saved:
                messagebox.showwarning(
                    "Cámara",
                    "No se guardó la configuración local. Se usa en esta sesión.")
            self._start_camera()

        tk.Button(dialog, text="Conectar", command=connect, bg=ACCENT, fg=SURFACE,
                  font=self._font(10, bold=True), relief="flat", padx=12, pady=6).pack(pady=(0, 16))
        dialog.bind("<Return>", lambda _event: connect())
        dialog.bind("<KP_Enter>", lambda _event: connect())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        entry.focus_set()

    def _ui(self, fn):
        with self._ui_lock:
            self._ui_queue.append(fn)

    def _drain_ui(self):
        with self._ui_lock:
            jobs = list(self._ui_queue)
            self._ui_queue.clear()
        for job in jobs:
            job()

    def _start_camera(self):
        if not self.url:
            self.hint_lbl.config(text="Falta la IP o la URL del IP Webcam.")
            messagebox.showinfo("Cámara", "Indica la IP local del celular o la URL HTTP antes de conectar.")
            return
        self._stop_camera(invalidate=self.cam_state in ("live", "lost") and not self.hold_file)
        self._stop.clear()
        self._live_requested = True
        self._cam_gen += 1
        gen = self._cam_gen
        self._preview_slot.clear()
        self._result_slot.clear()
        self._clear_overlay()
        self._clear_live_decision_clock()
        self._published_seq = 0
        self.hint_lbl.config(text="")
        self._set_cam_state("connecting")
        self.stop_btn.config(state="normal")
        self._capture_thread = threading.Thread(
            target=self._capture_loop, args=(self.url, gen), daemon=True)
        self._infer_thread = threading.Thread(
            target=self._infer_loop, args=(gen,), daemon=True)
        self._capture_thread.start()
        self._infer_thread.start()

    def _stop_camera(self, invalidate=True):
        self._cam_gen += 1
        self._stop.set()
        self._live_requested = False
        self.capture = None
        self._preview_slot.clear()
        self._result_slot.clear()
        self._shown_seq = 0
        self._published_seq = 0
        self._clear_overlay()
        self._clear_live_decision_clock()
        self._refresh_rearm()
        if invalidate:
            self._invalidate_live_decision()
        self._set_cam_state("stopped")
        self.stop_btn.config(state="disabled")

    def _invalidate_live_decision(self):
        self.gate.note_disconnect()
        self._refresh_rearm()
        if self.hold_file:
            self._file_caption = True
            self._frame_stale = False
            self._paint_viewer()
            return
        self._file_caption = False
        self._frame_stale = self._last_bgr is not None
        self._show_decision({
            "outcome": "SIGNAL_LOST",
            "reason": "camera_signal_lost",
            "identity": None,
        })
        self._set_status("Cámara detenida · la autorización anterior no sigue vigente")
        self._paint_viewer()

    def _capture_loop(self, url, gen):
        rotation = self.rotation
        try:
            capture = self.open_capture(url)
        except (cv2.error, OSError):
            capture = None
        if gen != self._cam_gen:
            closer = getattr(capture, "release", None)
            if capture is not None and closer is not None:
                closer()
            return
        if capture is None:
            self._ui(lambda: self._on_open_failed() if gen == self._cam_gen else None)
            return
        self.capture = capture
        try:
            while gen == self._cam_gen and not self._stop.is_set():
                ok, frame = capture.read()
                if gen != self._cam_gen:
                    return
                if not ok or frame is None:
                    self._preview_slot.put({"kind": "lost", "at": monotonic()})
                    self._ui(lambda: self._signal_lost() if gen == self._cam_gen else None)
                    return
                if rotation is not None:
                    frame = cv2.rotate(frame, rotation)
                self._seq += 1
                self._preview_slot.put({
                    "kind": "frame", "seq": self._seq, "bgr": frame, "at": monotonic(),
                })
        finally:
            closer = getattr(capture, "release", None)
            if closer is not None:
                closer()
            if self.capture is capture:
                self.capture = None

    def _on_open_failed(self):
        self.hint_lbl.config(text="No hay stream. Revisa IP Webcam, la IP y el puerto de cámara.")
        messagebox.showerror(
            "Cámara",
            "No hay stream. Abre IP Webcam en el celular y comprueba la IP y el puerto 8080.")
        self._signal_lost()

    def _infer_loop(self, gen):
        while gen == self._cam_gen and not self._stop.is_set():
            if not self._process_latest(gen):
                sleep(0.01)

    def _process_latest(self, gen=None):
        item = self._preview_slot.peek()
        if not item or item.get("kind") != "frame" or item["seq"] <= self._done_seq:
            return False
        self._done_seq = item["seq"]
        frame = item["bgr"]
        started = monotonic()
        scene = self.recognize_frame(frame)
        infer_ms = (monotonic() - started) * 1000
        session = self._cam_gen if gen is None else gen
        self._result_slot.put({
            "seq": item["seq"],
            "gen": session,
            "scene": scene,
            "infer_ms": infer_ms,
            "captured_at": item["at"],
            "size": frame.shape[:2],
        })
        return True

    def _clear_overlay(self):
        self._overlay = None
        self._paint_key = None

    def _clear_live_decision_clock(self):
        self._live_decision = False
        self._live_decision_at = None

    def _open_image(self):
        path = filedialog.askopenfilename(filetypes=[("Imagen", "*.png;*.jpg;*.jpeg")])
        if not path:
            return
        self.apply_path(path, source="file")

    def apply_path(self, path, source="file"):
        frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if frame is None:
            messagebox.showerror("Imagen", "No se pudo leer el archivo.")
            return None
        return self._apply(frame, source=source)

    def _open_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        self.apply_folder(folder)

    def apply_folder(self, folder):
        paths = sorted(Path(folder).glob("*.png"))[:40]
        granted = denied = 0
        last = None
        for path in paths:
            frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if frame is None:
                continue
            scene = self.recognize_frame(frame)
            if scene["outcome"] == "GRANTED":
                granted += 1
            else:
                denied += 1
            self._record(scene, path.name)
            last = path
        self._set_status(f"Carpeta: {granted} autorizados, {denied} denegados (máx. 40 PNG).")
        if last is not None:
            frame = cv2.imread(str(last), cv2.IMREAD_COLOR)
            if frame is not None:
                scene = self.recognize_frame(frame)
                self.hold_file = True
                self._file_caption = True
                self._frame_stale = False
                self._last_bgr = paint_regions(frame, scene.get("regions") or [])
                self._show_decision(scene)
                self._paint_viewer()
        return granted, denied

    def _signal_lost(self):
        """Fallo de cámara: deja de mostrar Autorizado de vivo y marca el fotograma.

        Es una falla real (no la salida normal de una persona): exige rearme del operador.
        """
        self.gate.note_fault()
        self.block_reason = "se perdió la señal de la cámara"
        self._preview_slot.clear()
        self._result_slot.clear()
        self._shown_seq = 0
        self._published_seq = 0
        self._clear_overlay()
        self._clear_live_decision_clock()
        self._refresh_rearm()
        self._set_cam_state("lost")
        self._record({
            "outcome": "SIGNAL_LOST",
            "reason": "camera_signal_lost",
            "identity": None,
        }, "camera")
        if self.hold_file:
            self._file_caption = True
            self._frame_stale = False
            self._paint_viewer()
            return
        self._file_caption = False
        self._frame_stale = self._last_bgr is not None
        self._show_decision({
            "outcome": "SIGNAL_LOST",
            "reason": "camera_signal_lost",
            "identity": None,
        })
        self._set_status("Señal perdida · la autorización anterior no sigue vigente")
        self._paint_viewer()

    def _ingest_camera(self):
        """Un ciclo síncrono para pruebas. El vivo usa hilos de captura e inferencia."""
        if self.hold_file and not self._live_requested:
            if self.capture is not None:
                ok, frame = self.capture.read()
                if not ok or frame is None:
                    self._preview_slot.put({"kind": "lost", "at": monotonic()})
                    self._signal_lost()
            return
        if self.capture is not None:
            ok, frame = self.capture.read()
            if not ok or frame is None:
                self._preview_slot.put({"kind": "lost", "at": monotonic()})
                self._signal_lost()
                return
            if self.rotation is not None:
                frame = cv2.rotate(frame, self.rotation)
            self._seq += 1
            self._preview_slot.put({
                "kind": "frame", "seq": self._seq, "bgr": frame, "at": monotonic(),
            })
        self._process_latest()
        self._tick_view()

    def _publish_result(self, result, now):
        if not result or result["seq"] == self._published_seq:
            return
        self._published_seq = result["seq"]
        self._shown_seq = result["seq"]
        active = result.get("gen", self._cam_gen) == self._cam_gen and not self._stop.is_set()
        age = now - result["captured_at"]
        if not active or age > RESULT_MAX_AGE:
            return
        self.metrics["infer_ms"] = result["infer_ms"]
        self._commit_scene(result["scene"], "camera", captured_at=result["captured_at"])
        boxes = overlay_boxes(result["scene"])
        if boxes:
            self._overlay = {
                "boxes": boxes,
                "until": now + BOX_TTL,
                "gen": self._cam_gen,
                "size": result["size"],
            }
        else:
            self._overlay = None
        if self.cam_state == "connecting":
            # Solo una conexión que entregó video entra al historial.
            remember_camera(self.url, self.rotation_deg, self.config_path)
        if self.cam_state != "stopped":
            self._set_cam_state("live")

    def _expire_overlay(self, now):
        layer = self._overlay
        if not layer:
            return
        if layer["gen"] != self._cam_gen or now >= layer["until"] or self._stop.is_set():
            self._overlay = None

    def _expire_live_decision(self, now):
        """El video puede seguir; Autorizado caduca si no hay resultado fresco."""
        if self.hold_file or not self._live_decision or self._live_decision_at is None:
            return
        if now - self._live_decision_at <= DECISION_TTL:
            return
        self._live_decision = False
        self._ui_streak = 0
        self.gate.interrupt()
        self._refresh_rearm()
        scene = {
            "outcome": "STALE",
            "reason": "stale_measurement",
            "identity": None,
        }
        self._show_decision(scene)
        self._set_status("Espera · sin medición reciente; la autorización anterior no sigue vigente")
        self._record(scene, "camera")

    def _tick_view(self):
        preview = self._preview_slot.peek()
        result = self._result_slot.peek()
        now = monotonic()
        self._publish_result(result, now)
        had_overlay = self._overlay is not None
        self._expire_overlay(now)
        self._expire_live_decision(now)
        if preview and preview.get("kind") == "frame" and (
                self._live_requested or not self.hold_file):
            self.hold_file = False
            self._file_caption = False
            self._frame_stale = False
            self.metrics["frame_age_ms"] = (now - preview["at"]) * 1000
            self._last_bgr = preview["bgr"]
            if preview["seq"] != self._view_seq:
                self._view_seq = preview["seq"]
                self._view_times.append(now)
                cutoff = now - 1
                self._view_times = [stamp for stamp in self._view_times if stamp >= cutoff]
                self.metrics["view_fps"] = float(len(self._view_times))
            self._paint_viewer()
        elif self.hold_file and self.cam_state in ("lost", "connecting", "live"):
            self._file_caption = True
            self._paint_viewer()
        elif had_overlay and self._overlay is None:
            self._paint_viewer(force=True)

    def _tick(self):
        if not self._tick_alive:
            return
        self._drain_ui()
        self._tick_view()
        self._refresh_live_panel()
        self._schedule_tick()

    def recognize_frame(self, frame):
        scene = self._core(frame, self.permissions)
        return require_everyone_authorized(scene) if self.require_everyone else scene

    def _commit_scene(self, scene, source, captured_at=None):
        simulate_authorize({
            key: scene[key] for key in ("outcome", "reason", "identity")
        } | {"event_id": scene.get("event_id")})
        if source == "camera":
            self._ui_streak = self._ui_streak + 1 if scene.get("outcome") == "GRANTED" else 0
        if may_send_physical(source, scene_kind(scene), self.gate, self.actuate):
            self._send_latch(scene)
        self._refresh_rearm()
        if source == "camera":
            self._live_decision = True
            self._live_decision_at = captured_at if captured_at is not None else monotonic()
        else:
            self._clear_live_decision_clock()
        self._show_decision(scene)
        identity = display_person(scene["identity"], self.labels)
        extra = ""
        if self.metrics["view_fps"] or self.metrics["infer_ms"]:
            extra = (
                f" · vista {self.metrics['view_fps']:.0f} fps"
                f" · inferencia {self.metrics['infer_ms']:.0f} ms"
                f" · edad {self.metrics['frame_age_ms']:.0f} ms")
        self._set_status(
            f"{SPANISH.get(scene['outcome'], scene['outcome'])} · "
            f"{SPANISH.get(scene['reason'], scene['reason'])} · {identity}{extra}")
        self._refresh_hw()
        self._record(scene, source)

    def _apply(self, frame, source):
        scene = self.recognize_frame(frame)
        self.hold_file = source != "camera"
        self._file_caption = self.hold_file
        self._frame_stale = False
        self._last_bgr = paint_regions(frame, scene.get("regions") or [])
        self._paint_viewer()
        self._commit_scene(scene, source)
        return scene

    def _test_servo(self, action, degrees=None):
        port = self.servo_port.get().strip().upper()
        if not port:
            self.servo_status.set("Indica el puerto del ESP32.")
            return
        if action == "move" and degrees is None:
            try:
                degrees = int(self.servo_angle.get())
                if not SERVO_MIN <= degrees <= SERVO_MAX:
                    raise ValueError
            except ValueError:
                self.servo_status.set(f"Escribe un ángulo entero entre {SERVO_MIN}° y {SERVO_MAX}°.")
                return
        if self.connection is not None:
            # El reconocimiento ya tiene el puerto: se usa la misma conexión en este hilo,
            # así nunca hay dos escrituras simultáneas en el puerto serie.
            try:
                ack = run_servo_test(self.connection, action, degrees)
            except (OSError, RuntimeError, TimeoutError, ValueError) as error:
                message = f"No se confirmó la operación. {error}"
            else:
                message = f"{self.port} · {ack}"
            self._finish_servo_test(message)
            return
        for button in self.servo_buttons:
            button.state(["disabled"])
        self.servo_status.set(f"Esperando respuesta del ESP32 en {port}…")
        threading.Thread(target=self._servo_test_worker, args=(port, action, degrees),
                         daemon=True).start()

    def _servo_test_worker(self, port, action="cycle", degrees=None):
        try:
            ack = send_servo_test(port, action, degrees)
        except (ImportError, OSError, RuntimeError, TimeoutError, ValueError) as error:
            message = f"No se confirmó la operación en {port}. {error}"
        else:
            message = f"{port} · {ack}"
            if action != "check":
                message += " · Comprueba el recorrido del brazo."
        self._ui(lambda: self._finish_servo_test(message))

    def _finish_servo_test(self, message):
        self.ack_text = message
        self._refresh_hw()
        self.servo_status.set(message)
        for button in self.servo_buttons:
            button.state(["!disabled"])

    def _send_latch(self, scene):
        if not self.latch_ok or self.connection is None or not self.model_ready:
            self.gate.note_fault()
            self.block_reason = "el pestillo o el modelo no estaban listos"
            return
        event = str(int(monotonic() * 1000))[-16:]
        try:
            result = send_decision(self.connection, event, scene["identity"], "GRANTED")
            self.ack_text = result["ack"]
            self._latch_open_until = monotonic() + self.hold_seconds
            self.command_lbl.config(
                text=f"Última etiqueta enviada: {result['command']}\nAcuse del ESP32: {result['ack']}")
            self.lock_text = (f"abierto: se cierra {format_seconds(self.hold_seconds)} s después del último autorizado"
                              if result["pulse_confirmed"] else "simulación · posición no confirmada")
        except (OSError, RuntimeError, TimeoutError, ValueError) as error:
            self.ack_text = f"error {error}"
            self._invalidate_port()
            self.log.insert(0, f"pestillo error {error}")

    def _refresh_hw(self):
        port = self.port or "sin puerto"
        if self.latch_ok:
            self._set_chip(self.chip_latch, f"●  ESP32 {port}", ACCENT)
        elif self.port:
            self._set_chip(self.chip_latch, "●  ESP32 sin conexión", DENIED_INK)
        else:
            self._set_chip(self.chip_latch, "●  ESP32 no usado", CHIP_IDLE)
        self._set_chip(self.chip_mode, f"●  {self._mode_text()}", ACCENT if self.actuate else CHIP_IDLE)
        mode = "firmware LATCH listo" if self.latch_ok else "simulación"
        self.hw_lbl.config(text=f"Puerto {port} · {mode}\nAcuse: {self.ack_text}\n{self.lock_text}")


    def _record(self, scene, source):
        key = history_key(scene, source)
        title = SPANISH.get(scene.get("outcome"), scene.get("outcome") or "estado")
        who = display_person(scene.get("identity"), self.labels) if scene.get("identity") else "—"
        origin = {"camera": "cámara", "operador": "operador"}.get(key[3], key[3])
        color = {"GRANTED": ACCENT, "DENIED": DENIED_INK}.get(scene.get("outcome"), WAIT_INK)
        if key == self._hist_key:
            self._hist_count += 1
            line = f"{self._hist_time}  {title} · {who} · {origin} ×{self._hist_count}"
            if self.log.size():
                self.log.delete(0)
            self.log.insert(0, line)
            self.log.itemconfig(0, fg=color)
            if self.history:
                self.history[-1] = line
            return
        self._hist_key = key
        self._hist_count = 1
        self._hist_time = datetime.now().strftime("%H:%M:%S")
        line = f"{self._hist_time}  {title} · {who} · {origin}"
        self.history.append(line)
        self.log.insert(0, line)
        self.log.itemconfig(0, fg=color)
        self.history = self.history[-HISTORY_LIMIT:]
        while self.log.size() > HISTORY_LIMIT:
            self.log.delete(HISTORY_LIMIT, tk.END)

    def run(self):
        self._tick_alive = True
        self._schedule_tick()
        try:
            self.window.mainloop()
        finally:
            self._stop.set()
            self._cam_gen += 1
            if self.connection is not None:
                self.connection.close()


def trial_banner(info):
    if not info or not info.get("label"):
        return ""
    digest = (info.get("gallery_sha256") or "")[:12] or "—"
    distance = info.get("max_distance")
    gap = info.get("min_gap")
    t_text = f"{distance:.3f}" if isinstance(distance, (int, float)) else "—"
    g_text = f"{gap:.3f}" if isinstance(gap, (int, float)) else "—"
    return f"Ensayo {info['label']} · T={t_text} · G={g_text} · hash {digest}\n"


def build_recognizer(vault, models, trial="identity_four_v2"):
    human = load_keras(Path(vault) / "experiments" / "human_cnn" / HUMAN_RUN / "model.keras")
    identify, model_ready, reason, info = build_identify(vault, "knn", 0., trial=trial)
    if info.get("preprocessing") in ("aligned_hog", "sface", "fusion"):
        detector, aligner = load_models(models)
    else:
        detector, aligner = load_detector(models), None
    describe = face_descriptor(info, aligner)

    def recognize(frame, permissions):
        return recognize_frame(
            frame, detector, human, identify, permissions, "knn",
            model_ready=model_ready, aligner=aligner, describe=describe)

    return recognize, model_ready, reason, info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--url", default="", help="URL HTTP del IP Webcam. También se puede indicar en Cámara.")
    parser.add_argument("--rotation", type=int, choices=(0, 90, 180, 270), default=0)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    parser.add_argument("--port", default="")
    parser.add_argument(
        "--trial", default="identity_four_other/identity_four_0406_real_fusion_w075",
        help="identity_four/identity_four_v2 o identity_four_other/<run>. No pisa v2.")
    parser.add_argument(
        "--actuate", action="store_true",
        help="Permite que un Autorizado de la cámara en vivo mueva el pestillo. Requiere --port.")
    args = parser.parse_args()
    if args.actuate and not args.port:
        parser.error("--actuate requiere --port con el ESP32 conectado.")
    vault = verify_vault(args.vault)
    url = parse_camera_url(args.url) if args.url else ""
    try:
        recognize, model_ready, reason, info = build_recognizer(vault, args.models, args.trial)
    except ValueError as error:
        parser.error(str(error))
    if args.port and info.get("preprocessing") in ("aligned_hog", "sface"):
        parser.error("Este candidato se prueba en simulación. Abre sin --port.")
    app = OperatorApp(
        recognize, model_ready=model_ready, reason=reason or "", url=url,
        rotation=args.rotation, port=args.port or None,
        labels=load_identity_labels(vault), trial_info=info,
        model_loader=lambda trial: build_recognizer(vault, args.models, trial),
        actuate=args.actuate)
    app.run()


if __name__ == "__main__":
    main()
