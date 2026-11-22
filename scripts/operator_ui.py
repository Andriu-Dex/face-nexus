"""Interfaz local: cámara o imagen, decisión, permisos e historial sin fotos."""

import argparse
from pathlib import Path
from time import monotonic, sleep
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2

from scripts.access import default_permissions, simulate_authorize
from scripts.calibrate_hog import ROTATE
from scripts.dataset_capture import verify_vault
from scripts.face_pipeline import load_detector
from scripts.latch_serial import latch_ready, ping_firmware, send_decision
from scripts.live_k01 import HUMAN_RUN, build_identify, load_keras, paint_regions, recognize_frame
from scripts.phone_serial_bench import local_stream_url
from scripts.presentation_gate import PresentationGate, scene_kind


SPANISH = {
    "K01": "K01",
    "K02": "K02",
    "K03": "K03",
    "K04": "K04",
    "UNKNOWN": "Desconocido",
    "GRANTED": "Autorizado",
    "DENIED": "Denegado",
}


def may_send_physical(source, kind, gate, recognition_actuation=False):
    """La cámara no acciona hasta que el reconocimiento esté evaluado con extraños."""
    if source != "camera" or recognition_actuation is not True:
        return False
    return gate.on_frame(kind)


class OperatorApp:
    def __init__(self, vault, models, url, rotation, port):
        self.vault = vault
        self.url = url
        self.rotation = ROTATE[rotation]
        self.port = port
        self.connection = None
        self.capture = None
        self.latch_ok = False
        self.gate = PresentationGate()
        self.ack_text = "sin acuse"
        self.lock_text = "posición no confirmada"
        self.permissions = default_permissions()
        self.history = []
        human = load_keras(vault / "experiments" / "human_cnn" / HUMAN_RUN / "model.keras")
        identify, model_ready, reason = build_identify(vault, "knn", 0.)
        self.model_ready = model_ready
        detector = load_detector(models)
        self.recognize = lambda frame: recognize_frame(
            frame, detector, human, identify, self.permissions, "knn",
            model_ready=model_ready)
        self.window = tk.Tk()
        self.window.title("FaceNexus")
        self.photo = None
        self._build()
        if not model_ready:
            self.status.config(text=f"Modelo no verificado ({reason}). Todo denegado.")
        if port:
            self._open_port(port)
        self.window.after(40, self._tick)

    def _build(self):
        left = ttk.Frame(self.window, padding=8)
        left.grid(row=0, column=0, sticky="nsew")
        self.canvas = tk.Label(left, text="Sin imagen", width=80, height=20)
        self.canvas.pack()
        self.status = ttk.Label(left, text="Listo", font=("Segoe UI", 14))
        self.status.pack(pady=8)
        self.decision_lbl = ttk.Label(left, text="Decisión: —")
        self.decision_lbl.pack(anchor="w")
        self.ack_lbl = ttk.Label(left, text="Acuse ESP32: —")
        self.ack_lbl.pack(anchor="w")
        self.lock_lbl = ttk.Label(left, text="Pestillo: posición no confirmada")
        self.lock_lbl.pack(anchor="w")
        btns = ttk.Frame(left)
        btns.pack()
        ttk.Button(btns, text="Cámara", command=self._start_camera).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Abrir imagen…", command=self._open_image).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Probar carpeta…", command=self._open_folder).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Siguiente presentación", command=self._rearm).pack(side=tk.LEFT, padx=4)
        right = ttk.Frame(self.window, padding=8)
        right.grid(row=0, column=1, sticky="ns")
        ttk.Label(right, text="Permisos (sin reentrenar)").pack(anchor="w")
        self.perm_vars = {}
        for person in self.permissions:
            var = tk.BooleanVar(value=self.permissions[person])
            self.perm_vars[person] = var
            ttk.Checkbutton(right, text=person, variable=var,
                            command=self._sync_permissions).pack(anchor="w")
        ttk.Label(right, text="Historial técnico (sin imágenes)").pack(anchor="w", pady=(12, 0))
        self.log = tk.Listbox(right, width=48, height=18)
        self.log.pack()
        ttk.Label(
            right,
            text="Reconocimiento sin pestillo. Extraños y humano/no humano se evalúan aparte. "
                 "«Siguiente presentación» cuando la persona salga. Archivos: solo predicción.",
        ).pack(anchor="w")

    def _rearm(self):
        self.gate.rearm()
        self.log.insert(0, "operador: siguiente presentación")

    def _sync_permissions(self):
        for person, var in self.perm_vars.items():
            self.permissions[person] = bool(var.get())

    def _open_port(self, port):
        try:
            import serial
            self.connection = serial.Serial(port, 115200, timeout=.2, write_timeout=2)
            sleep(2)
            self.connection.reset_input_buffer()
            pong = ping_firmware(self.connection)
            self.latch_ok = latch_ready(pong)
            self.ack_text = pong
            if not self.latch_ok:
                self.connection.close()
                self.connection = None
                self.lock_text = "envío deshabilitado (no es firmware LATCH)"
                messagebox.showwarning("Serie", f"Firmware {pong}. No se envían órdenes.")
        except (OSError, ValueError, TimeoutError) as error:
            messagebox.showwarning("Serie", f"No se abrió {port}: {error}")
            self._invalidate_port()
        self._refresh_hw()

    def _invalidate_port(self):
        """Tras un error de transporte hay que volver a comprobar el firmware."""
        if self.connection is not None:
            try:
                self.connection.close()
            except OSError:
                pass
        self.connection = None
        self.latch_ok = False
        self.gate.note_fault()
        self.lock_text = "puerto invalidado; verificar firmware LATCH"

    def _start_camera(self):
        if self.capture is not None:
            self.capture.release()
            self.gate.note_disconnect()
        self.capture = cv2.VideoCapture()
        ok = self.capture.open(self.url, cv2.CAP_FFMPEG, [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3500, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 400,
        ])
        if not ok:
            messagebox.showerror("Cámara", "No hay stream.")
            self.capture = None
            self.gate.note_fault()

    def _open_image(self):
        path = filedialog.askopenfilename(filetypes=[("Imagen", "*.png;*.jpg;*.jpeg")])
        if not path:
            return
        frame = cv2.imread(path, cv2.IMREAD_COLOR)
        if frame is None:
            messagebox.showerror("Imagen", "No se pudo leer el archivo.")
            return
        self._apply(frame, source="file")

    def _open_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        paths = sorted(Path(folder).glob("*.png"))[:40]
        granted = denied = 0
        for path in paths:
            frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if frame is None:
                continue
            scene = self.recognize(frame)
            if scene["outcome"] == "GRANTED":
                granted += 1
            else:
                denied += 1
            self._record(scene, path.name)
        self.status.config(text=f"Carpeta: {granted} autorizados, {denied} denegados (máx. 40 PNG).")
        if paths:
            last = cv2.imread(str(paths[-1]), cv2.IMREAD_COLOR)
            if last is not None:
                self._show(paint_regions(last, self.recognize(last).get("regions") or []))

    def _tick(self):
        if self.capture is not None:
            ok, frame = self.capture.read()
            if not ok or frame is None:
                self.gate.note_fault()
            else:
                if self.rotation is not None:
                    frame = cv2.rotate(frame, self.rotation)
                self._apply(frame, source="camera")
        self.window.after(40, self._tick)

    def _apply(self, frame, source):
        scene = self.recognize(frame)
        simulate_authorize({
            key: scene[key] for key in ("outcome", "reason", "identity")
        } | {"event_id": scene.get("event_id")})
        if may_send_physical(source, scene_kind(scene), self.gate):
            self._send_latch(scene)
        self._show(paint_regions(frame, scene.get("regions") or []))
        identity = SPANISH.get(scene["identity"], scene["identity"])
        self.status.config(text=f"{SPANISH[scene['outcome']]} · {scene['reason']} · {identity}")
        self.decision_lbl.config(text=f"Decisión: {scene['outcome']} {scene['reason']} {identity}")
        self._refresh_hw()
        self._record(scene, source)
        return scene

    def _send_latch(self, scene):
        if not self.latch_ok or self.connection is None or not self.model_ready:
            self.gate.note_fault()
            return
        event = str(int(monotonic() * 1000))[-16:]
        try:
            result = send_decision(self.connection, event, scene["identity"], "GRANTED")
            self.ack_text = result["ack"]
            self.lock_text = ("pulso acusado; posición no confirmada"
                              if result["pulse_confirmed"] else "posición no confirmada")
            self.log.insert(0, f"serie {result['ack']}")
        except (OSError, RuntimeError, TimeoutError, ValueError) as error:
            self.ack_text = f"error {error}"
            self._invalidate_port()
            self.log.insert(0, f"pestillo error {error}")

    def _refresh_hw(self):
        self.ack_lbl.config(text=f"Acuse ESP32: {self.ack_text}")
        self.lock_lbl.config(text=f"Pestillo: {self.lock_text}")

    def _record(self, scene, source):
        line = f"{scene['outcome']} {scene['reason']} {scene['identity']} {source}"
        self.history.append(line)
        self.log.insert(0, line)
        if self.log.size() > 200:
            self.log.delete(200, tk.END)

    def _show(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width = rgb.shape[:2]
        scale = min(1., 720 / max(height, width))
        if scale < 1:
            rgb = cv2.resize(rgb, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
        header = f"P6 {rgb.shape[1]} {rgb.shape[0]} 255 ".encode("ascii")
        self.photo = tk.PhotoImage(data=header + rgb.tobytes())
        self.canvas.config(image=self.photo, text="", width=self.photo.width(), height=self.photo.height())

    def run(self):
        self.window.mainloop()
        if self.capture is not None:
            self.capture.release()
        if self.connection is not None:
            self.connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--url", type=local_stream_url, default="http://192.168.1.20:8080/video")
    parser.add_argument("--rotation", type=int, choices=(0, 90, 180, 270), default=0)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    parser.add_argument("--port", default="")
    args = parser.parse_args()
    app = OperatorApp(verify_vault(args.vault), args.models, args.url, args.rotation, args.port or None)
    app.run()


if __name__ == "__main__":
    main()
