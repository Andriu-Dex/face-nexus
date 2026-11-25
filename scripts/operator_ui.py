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

import cv2

from scripts.access import default_permissions, simulate_authorize
from scripts.calibrate_hog import ROTATE
from scripts.dataset_capture import verify_vault
from scripts.face_pipeline import load_detector, load_models
from scripts.hog_knn import PEOPLE
from scripts.latch_serial import (
    SERVO_CLOSED, SERVO_MAX, SERVO_MIN, SERVO_OPEN, latch_ready, open_latch_port, ping_firmware, run_servo_test, send_decision, send_servo_test,
)
from scripts.live_k01 import HUMAN_RUN, build_identify, face_descriptor, load_keras, paint_regions, recognize_frame
from scripts.phone_serial_bench import local_stream_url
from scripts.presentation_gate import CONSENSUS_FRAMES, PresentationGate, scene_kind


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
TRACK_DARK = "#2C4254"
TAG_BG = "#0F2233"
AMBER = "#C98A16"
REJECT = "#D9475B"
ICON_FONT = "Segoe MDL2 Assets"
ICON_LOCK = "\uE72E"
ICON_UNLOCK = "\uE785"
ICON_WARNING = "\uE7BA"
ICON_SHIELD = "\uEA18"
LATCH_HOLD_SECONDS = 3.0
PIPELINE_STEPS = (
    ("phone", "Celular (captura)"),
    ("detect", "YuNet (rostro)"),
    ("identify", "CNN propia + SFace → k-NN"),
    ("decide", "Permiso"),
    ("esp32", "ESP32 (pestillo)"),
)
# Cifras medidas y registradas en docs/decisions.md (D-90 a D-92); no se calculan aquí.
MODEL_FACTS = {
    "identity_four_other/identity_four_0406_real_fusion_w075": (
        "CNN propia (75 %) + SFace de apoyo (25 %) · k-NN, k = 3 · T = 1,011 · G = 0,114",
        ["Integrantes, video 05: 89 % de fotogramas aceptados; 4/4 abren",
         "Desconocidos reales reservados: 0/5 abren",
         "Desconocidos LFW de validación: 0/999 aceptados",
         "Confusiones entre integrantes: 0"],
    ),
    "identity_four_other/identity_four_phone_04_cnn_run1": (
        "CNN propia sola · k-NN, k = 3 · galería del video 04",
        ["Integrantes, video 05: 68/75 fotogramas aceptados",
         "Desconocidos LFW de validación: 2/999 aceptados",
         "Confusiones entre integrantes: 0"],
    ),
}
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
    return {
        "url": url.strip(),
        "ip": ip.strip(),
        "camera_port": str(port or DEFAULT_CAM_PORT),
        "rotation": rotation,
    }


def save_camera_config(url, ip, camera_port, rotation, path=None):
    path = Path(path or camera_config_path())
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "url": url,
            "ip": ip,
            "camera_port": str(camera_port),
            "rotation": int(rotation),
        }, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


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


def match_strength(distance, max_distance):
    """0–1 para la barra de la etiqueta: 1 si d ≤ T/2, 0 si d ≥ T. Solo es visual."""
    if not isinstance(distance, (int, float)) or not isinstance(max_distance, (int, float)):
        return None
    if max_distance <= 0:
        return None
    return float(min(1., max(0., (max_distance - distance) / (max_distance / 2))))


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
                "distance": row.get("distance"),
                "max_distance": row.get("max_distance"),
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
        self.cam_btn = self._button(controls, "Conectar celular",
                                    self._camera_dialog, primary=True)
        self.cam_btn.pack(side=tk.LEFT)
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

        model = self._section(side, "Modelo y exactitud medida")
        self.model_lbl = tk.Label(model, text="", font=self._font(9), fg=INK, bg=SURFACE,
                                  anchor="w", justify="left", wraplength=320)
        self.model_lbl.pack(anchor="w")
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

        tech = self._section(side, "Diagnóstico")
        self.tech_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            tech, text="Mostrar detalle técnico (distancias, umbrales, huella)",
            variable=self.tech_var, command=self._refresh_tech, font=self._font(9),
            fg=WAIT_INK, bg=SURFACE, activebackground=SURFACE, selectcolor=SURFACE, anchor="w",
            wraplength=320, justify="left").pack(anchor="w")
        self.tech_lbl = tk.Label(tech, text="", font=("Consolas", 8), fg=WAIT_INK, bg=SURFACE,
                                 anchor="w", justify="left", wraplength=320)
        self.tech_lbl.pack(anchor="w")
        self._scene = {}
        self.hw_lbl = tk.Label(tech, text="", font=self._font(8), fg=WAIT_INK, bg=SURFACE,
                               wraplength=320, justify="left", anchor="w")
        self.hw_lbl.pack(anchor="w", pady=(6, 0))
        self.status = tk.Label(tech, text="Listo", font=self._font(8), fg=WAIT_INK, bg=SURFACE,
                               wraplength=320, justify="left", anchor="w")
        self.status.pack(anchor="w", pady=(4, 0))
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
        if facts:
            title, lines = facts
            text = title + "\n" + "\n".join(f"•  {line}" for line in lines)
        else:
            text = "Modelo de comparación. Sus cifras están en el informe."
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
                  f"{SERVO_OPEN}° (señal PWM en GPIO25) y, si pasan 3 s sin renovación, cierra "
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
            match = match_strength(item.get("distance"), item.get("max_distance"))
            lines = [(name, self._font(11, bold=True))]
            detail = status if match is None else f"{status} · coincidencia {match:.0%}"
            lines.append((detail, self._font(9)))
            # YuNet es quien confirma el rostro humano en vivo; la CNN binaria va al detalle técnico.
            lines.append(("Rostro humano (YuNet)", self._font(8)))
            self._draw_tag(x0, y0, x1, lines, color, match)

    def _draw_brackets(self, x0, y0, x1, y1, color):
        """Esquinas marcadas y un contorno fino: se ve el rostro sin taparlo."""
        size = max(12, min(x1 - x0, y1 - y0) * 0.22)
        self.viewer.create_rectangle(x0, y0, x1, y1, outline=color, width=1, tags="box")
        for cx, cy, dx, dy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
            self.viewer.create_line(cx, cy, cx + dx * size, cy, fill=color, width=5,
                                    capstyle="round", tags="box")
            self.viewer.create_line(cx, cy, cx, cy + dy * size, fill=color, width=5,
                                    capstyle="round", tags="box")

    def _draw_tag(self, x0, y0, x1, lines, color, match):
        """Etiqueta sobre el recuadro: nombre, estado, CNN humano y barra de coincidencia."""
        pad, gap = 10, 2
        widths, heights = [], []
        for text, font in lines:
            probe = self.viewer.create_text(0, 0, text=text, font=font, anchor="nw")
            bx0, by0, bx1, by1 = self.viewer.bbox(probe)
            self.viewer.delete(probe)
            widths.append(bx1 - bx0)
            heights.append(by1 - by0)
        bar_h = 6 if match is not None else 0
        width = max(max(widths) + 2 * pad, x1 - x0)
        height = sum(heights) + gap * (len(lines) - 1) + 2 * pad + (bar_h + 6 if bar_h else 0)
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
        if bar_h:
            track_x0, track_x1 = x0 + pad + 4, x0 + width - pad
            self.viewer.create_rectangle(track_x0, y + 4, track_x1, y + 4 + bar_h, fill=TRACK_DARK,
                                         outline="", tags="face_label")
            self.viewer.create_rectangle(track_x0, y + 4,
                                         track_x0 + (track_x1 - track_x0) * match,
                                         y + 4 + bar_h, fill=color, outline="", tags="face_label")

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
        streak = min(self._ui_streak, CONSENSUS_FRAMES)
        width = max(self.streak_bar.winfo_width(), 2)
        self.streak_bar.delete("all")
        fill = ACCENT if streak >= CONSENSUS_FRAMES else ACCENT_SOFT
        self.streak_bar.create_rectangle(0, 0, width * streak / CONSENSUS_FRAMES, 10,
                                         fill=fill, outline="")
        if streak >= CONSENSUS_FRAMES:
            text = f"Identidad confirmada en {CONSENSUS_FRAMES} fotogramas seguidos"
        elif streak:
            text = f"Verificando identidad… {streak}/{CONSENSUS_FRAMES} fotogramas"
        else:
            text = f"Abre tras {CONSENSUS_FRAMES} fotogramas autorizados seguidos"
        self.streak_lbl.config(text=text)
        remaining = self._latch_open_until - now
        if not self.actuate:
            self.latch_icon.config(text=ICON_LOCK, fg=WAIT_INK)
            self.latch_state_lbl.config(
                text="Simulación\n" + ("abriría ahora" if streak >= CONSENSUS_FRAMES
                                       else "no se envían órdenes"), fg=WAIT_INK)
        elif remaining > 0:
            self.latch_icon.config(text=ICON_UNLOCK, fg=ACCENT)
            self.latch_state_lbl.config(
                text=f"ABIERTO\ncierra en {remaining:.1f} s".replace(".", ","), fg=ACCENT)
        else:
            self.latch_icon.config(text=ICON_LOCK, fg=INK)
            self.latch_state_lbl.config(text="CERRADO", fg=INK)
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
        if self.tech_var.get():
            self.tech_lbl.config(text=trial_banner(self.trial_info) + technical_lines(self._scene, self.labels))
        else:
            self.tech_lbl.config(text="")

    def _refresh_rearm(self):
        self.rearm_btn.config(state=("normal" if not self.gate.can_send else "disabled"))

    def _rearm(self):
        self.gate.rearm()
        self._record({"outcome": "REARM", "reason": "rearm", "identity": None}, "operador")
        self._refresh_rearm()

    def _sync_permissions(self):
        for person, var in self.perm_vars.items():
            self.permissions[person] = bool(var.get())

    def _open_port(self, port):
        try:
            self.connection = open_latch_port(port)
            pong = ping_firmware(self.connection)
            self.latch_ok = latch_ready(pong)
            self.ack_text = pong
            if not self.latch_ok:
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
        self.lock_text = "simulación · puerto invalidado"
        self._refresh_rearm()

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
        entry = tk.Entry(dialog, textvariable=ip_var, width=42, font=self._font(10))
        entry.pack(padx=16, fill="x")
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
            text="IP Webcam: 192.168.1.20 y puerto 8080, o 192.168.1.20:8080, o la URL completa. El puerto serie del pestillo es otro campo.",
            font=self._font(8), fg=WAIT_INK, bg=SURFACE, wraplength=360, justify="left")
        note.pack(anchor="w", padx=16, pady=8)

        def connect():
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
        return self._core(frame, self.permissions)

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
            return
        event = str(int(monotonic() * 1000))[-16:]
        try:
            result = send_decision(self.connection, event, scene["identity"], "GRANTED")
            self.ack_text = result["ack"]
            self._latch_open_until = monotonic() + LATCH_HOLD_SECONDS
            self.command_lbl.config(
                text=f"Última etiqueta enviada: {result['command']}\nAcuse del ESP32: {result['ack']}")
            self.lock_text = ("abierto: se cierra 3 s después del último autorizado"
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
