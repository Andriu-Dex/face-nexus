"""Captura manual del piloto: originales PNG y un registro JSON por toma."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time

import cv2
import numpy as np


PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "data"
PEOPLE = ("K01", "K02", "K03", "K04")
INSTRUCTIONS = (
    ["Frontal neutro; reposiciona ligeramente"] * 4
    + ["Giro izquierda 15 grados", "Giro derecha 15 grados",
       "Giro izquierda 30 grados", "Giro derecha 30 grados"]
    + ["Mirada arriba suave", "Mirada abajo suave"] * 2
    + ["Distancia aprox. 0.6 m", "Distancia aprox. 0.8 m",
       "Distancia aprox. 1.0 m", "Distancia aprox. 1.2 m"]
    + ["Expresion neutra", "Sonrisa natural", "Expresion neutra", "Sonrisa natural"]
)
BLOCKS = ("frontal", "yaw", "pitch", "distance", "expression")


def shot_plan(number):
    if not 1 <= number <= 20:
        raise ValueError("El piloto contiene tomas 1 a 20.")
    # Dos luces por bloque evitan concentrar una condición en un único bloque.
    lighting = "diffuse" if (number - 1) % 4 < 2 else "lateral"
    return {"number": number, "block": BLOCKS[(number - 1) // 4],
            "instruction": INSTRUCTIONS[number - 1], "lighting": lighting,
            "distance_target_m": (.6, .8, 1., 1.2)[number - 13]
            if 13 <= number <= 16 else None}


def create_session(root, person, source):
    if person not in PEOPLE or source not in ("synthetic", "camera"):
        raise ValueError("Persona o fuente no válida.")
    session = Path(root) / person / "P01"
    session.mkdir(parents=True, exist_ok=False)
    return session


def save_sample(session, person, number, frame, source, camera_config=None):
    """Escritura exclusiva; un error no deja una imagen nueva sin su registro."""
    plan = shot_plan(number)
    if person not in PEOPLE or source not in ("synthetic", "camera"):
        raise ValueError("Persona o fuente no válida.")
    if not isinstance(frame, np.ndarray) or frame.dtype != np.uint8:
        raise ValueError("Se requiere una matriz uint8.")
    if frame.shape != (1080, 1920, 3):
        raise ValueError("Se requiere BGR 1920x1080; no se redimensiona el original.")
    name = f"{person}_P01_{number:04d}"
    image_path = Path(session) / f"{name}.png"
    meta_path = Path(session) / f"{name}.json"
    if image_path.exists() or meta_path.exists():
        raise FileExistsError("La toma existe: no se sobrescriben originales.")
    ok, encoded = cv2.imencode(".png", frame)
    if not ok:
        raise RuntimeError("No se pudo codificar PNG.")
    payload = encoded.tobytes()
    record = {
        "schema_version": 1, "sample_id": name, "person_id": person,
        "session_id": "P01", "source": source, "split": "TRAIN",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "consent_ref": f"{person}_consent" if source == "camera" else None,
        "consent_operator_confirmed": source == "camera",
        "relative_path": image_path.name, "sha256": hashlib.sha256(payload).hexdigest(),
        "width": 1920, "height": 1080, "plan": plan,
        "conditions_operator_confirmed": source == "camera",
        "distance_approx_m": None, "camera_config": camera_config,
        "quality_status": "manual_review_pending", "exclusion_reason": None,
    }
    # Se elimina solo el archivo recién creado si falla su registro; jamás uno previo.
    created = False
    try:
        with image_path.open("xb") as file:
            created = True
            file.write(payload)
        with meta_path.open("x", encoding="utf-8") as file:
            json.dump(record, file, ensure_ascii=False, indent=2)
    except Exception:
        if created:
            image_path.unlink()
        raise
    return record


def check_private_destination():
    """Comprueba exclusión Git; esto no certifica permisos ni ausencia de nube."""
    for directory in (DATA, PROJECT / "private"):
        if directory.resolve() != PROJECT.resolve() / directory.name:
            raise RuntimeError("El destino privado no puede ser un enlace a otra ubicación.")
        directory.mkdir(exist_ok=True)
    for path in ("data/raw/pilot", "private/consents"):
        tracked = subprocess.run(["git", "ls-files", "--", path], cwd=PROJECT,
                                 capture_output=True, text=True, check=True).stdout
        ignored = subprocess.run(["git", "check-ignore", "--", path + "/example"],
                                 cwd=PROJECT, capture_output=True).returncode == 0
        if tracked.strip() or not ignored:
            raise RuntimeError("El destino debe estar excluido y no registrado en Git.")


def run_camera(person, camera_index, duration):
    from cv2_enumerate_cameras import enumerate_cameras

    check_private_destination()
    devices = enumerate_cameras(cv2.CAP_DSHOW)
    matches = [device for device in devices
               if device.index == camera_index and device.name == "USB CAMERA"]
    if len(matches) != 1:
        raise RuntimeError("El índice elegido no corresponde a USB CAMERA. No se abrirá otra.")
    print(f"Participante {person}; solo TRAIN. Consentimiento declarado por el custodio.")
    print("Confirma luz, pose, encuadre y persona antes de cada ESPACIO. Q/Esc termina.")
    print("TMCAM debe ser USB CAMERA; destino local data/raw/pilot, sin nube.")
    if input("Escribe CAPTURAR para guardar fotos reales: ").strip() != "CAPTURAR":
        return 2
    session = None
    capture = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    try:
        if not capture.isOpened():
            raise RuntimeError("Cámara no disponible.")
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        capture.set(cv2.CAP_PROP_FPS, 30)
        config = {"model_operator_declared": "TMCAM 8305", "index": camera_index,
                  "backend": capture.getBackendName(), "fps_reported": capture.get(cv2.CAP_PROP_FPS),
                  "fourcc_reported": capture.get(cv2.CAP_PROP_FOURCC),
                  "opencv_version": cv2.__version__, "antiflicker_60hz": "unconfirmed"}
        start = time.perf_counter()
        last_saved = -float("inf")
        number = 1
        message = "Comprueba la escena antes de guardar"
        while number <= 20 and time.perf_counter() - start < duration:
            ok, frame = capture.read()
            if not ok or frame is None:
                raise RuntimeError("Lectura fallida; se detiene sin reconectar.")
            if frame.shape != (1080, 1920, 3):
                raise RuntimeError("Resolución recibida distinta de 1920x1080.")
            plan = shot_plan(number)
            # La vista es una copia reducida; se guarda exclusivamente frame sin marcas.
            view = cv2.resize(frame, (960, 540))
            lines = [f"{person} - toma {number}/20 - ESPACIO guarda - Q sale",
                     plan["instruction"], f"Luz: {plan['lighting']}", message]
            for row, line in enumerate(lines):
                cv2.putText(view, line, (12, 28 + row * 28), cv2.FONT_HERSHEY_SIMPLEX,
                            .60, (0, 255, 255), 2)
            cv2.imshow("FaceNexus - piloto manual", view)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27) or cv2.getWindowProperty(
                    "FaceNexus - piloto manual", cv2.WND_PROP_VISIBLE) < 1:
                break
            if key == ord(" "):
                now = time.perf_counter()
                if now - start < 5 or now - last_saved < 2:
                    message = "Espera calentamiento de 5 s / 2 s entre tomas"
                    continue
                if session is None:
                    session = create_session(DATA / "raw/pilot", person, "camera")
                save_sample(session, person, number, frame, "camera", config)
                last_saved = now
                message = f"Guardada toma {number}. Cambia a la condicion siguiente"
                print(f"{person}: guardada {number}/20", flush=True)
                number += 1
        print(f"Sesión terminada: {number - 1}/20. No se borran tomas parciales.")
        return 0 if number == 21 else 1
    finally:
        capture.release()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--person", choices=PEOPLE, required=True)
    parser.add_argument("--camera", type=int, required=True)
    parser.add_argument("--consent-confirmed", action="store_true")
    parser.add_argument("--duration", type=int, default=900, help="Límite de sesión en segundos.")
    args = parser.parse_args()
    if not args.consent_confirmed or args.camera < 0 or not 10 <= args.duration <= 1800:
        parser.error("Confirma consentimiento, índice >=0 y duración entre 10 y 1800 s.")
    try:
        return run_camera(args.person, args.camera, args.duration)
    except (RuntimeError, FileExistsError, ValueError) as error:
        print(f"Sesión detenida: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
