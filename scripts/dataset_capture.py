"""Comprobación de cámara, captura guiada y auditoría del dataset definitivo."""

import argparse
import ctypes
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
from uuid import uuid4

import cv2

from scripts.camera_diagnostic import measure_capture
from scripts.capture_manifest import (
    FRAME_SHAPE, LIGHTS, audit_dataset, child, load_schedule, publish_directory,
    read_json, record_attempt, replay_attempts, shots_for, utc_now, valid_distance,
)


WINDOW = "FaceNexus - captura definitiva"
CHECK_WINDOW = "FaceNexus - diagnostico sin grabacion"
PROJECT = Path(__file__).resolve().parents[1]


def verify_vault(root):
    """Detecta montajes VeraCrypt y conserva una raíz NTFS de acceso restringido."""
    root = root.absolute()
    if (os.name != "nt" or not re.fullmatch(r"[A-Za-z]:", root.drive)
            or root == Path(root.anchor) or not root.is_dir()
            or root.resolve() != root or root.is_relative_to(PROJECT)):
        raise ValueError("Usa una carpeta privada existente en un volumen montado fuera del repo.")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    target = ctypes.create_unicode_buffer(32768)
    length = kernel.QueryDosDeviceW(ctypes.c_wchar_p(root.drive), target, len(target))
    expected = r"\Device\VeraCryptVolume" + root.drive[0].upper()
    if not length or target.value.casefold() != expected.casefold():
        raise ValueError("El destino no está montado como volumen VeraCrypt.")
    filesystem = ctypes.create_unicode_buffer(32)
    if not kernel.GetVolumeInformationW(
        ctypes.c_wchar_p(root.anchor), None, 0, None, None, None, filesystem, len(filesystem)
    ) or filesystem.value != "NTFS":
        raise ValueError("El volumen debe ser NTFS para conservar los permisos Windows.")
    command = """
        $ErrorActionPreference = 'Stop'
        $sidType = [System.Security.Principal.SecurityIdentifier]
        $me = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
        $allowed = @($me, 'S-1-5-18', 'S-1-5-32-544')
        $acl = Get-Acl -LiteralPath $env:FACENEXUS_VAULT
        $rules = $acl.GetAccessRules($true, $true, $sidType)
        if ($acl.GetOwner($sidType).Value -notin $allowed -or
            ($rules | Where-Object {
                $_.AccessControlType -eq 'Allow' -and $_.IdentityReference.Value -notin $allowed
            })) { exit 1 }
    """
    # Windows PowerShell debe usar sus módulos, aunque lo invoque PowerShell 7.
    environment = {key: value for key, value in os.environ.items()
                   if key.upper() != "PSMODULEPATH"}
    environment["FACENEXUS_VAULT"] = str(root)
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        env=environment, capture_output=True, check=False,
    )
    if result.returncode:
        raise ValueError("No se pudo comprobar el acceso restringido a la carpeta privada.")
    return root


def tmcamera(index):
    from cv2_enumerate_cameras import enumerate_cameras

    matches = [
        device for device in enumerate_cameras(cv2.CAP_DSHOW)
        if device.index == index and device.name == "USB CAMERA" and device.path
    ]
    if len(matches) != 1:
        raise ValueError("El índice no corresponde a la USB CAMERA esperada.")
    return matches[0]


def configure_camera(capture):
    if not capture.isOpened():
        raise ValueError("No se pudo abrir la TMCAM.")
    properties = {
        "fourcc": (cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG")),
        "width": (cv2.CAP_PROP_FRAME_WIDTH, 1920),
        "height": (cv2.CAP_PROP_FRAME_HEIGHT, 1080),
        "fps": (cv2.CAP_PROP_FPS, 30),
    }
    accepted = {name: bool(capture.set(prop, value)) for name, (prop, value) in properties.items()}
    reported = {name: capture.get(prop) for name, (prop, _) in properties.items()}
    return {
        "backend": capture.getBackendName(), "opencv_version": cv2.__version__,
        "target": {"width": 1920, "height": 1080, "fps": 30, "format": "MJPG"},
        "set_accepted": accepted, "driver_reported": {
            name: value if math.isfinite(value) else None for name, value in reported.items()
        },
    }


def frame_key(frame, window, lines):
    view = cv2.resize(frame, (960, 540))
    for row, line in enumerate(lines, 1):
        cv2.putText(view, line, (12, row * 26), cv2.FONT_HERSHEY_SIMPLEX, .60, (0, 255, 255), 2)
    cv2.imshow(window, view)
    key = cv2.waitKey(1) & 0xFF
    if key in (ord("q"), 27) or cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
        return ord("q")
    return key


def read_frame(capture):
    ok, frame = capture.read()
    if not ok or frame is None or frame.shape != FRAME_SHAPE:
        raise ValueError("Lectura fallida o fotograma distinto de BGR 1920×1080.")
    return frame


def inspect_bands(capture, light):
    while True:
        key = frame_key(read_frame(capture), CHECK_WINDOW, [
            f"Configura luz {light}; escena sin personas",
            "S: bandas visibles | N: sin bandas visibles | Q: cancelar",
        ])
        if key == ord("q"):
            raise ValueError("Comprobación visual cancelada.")
        if key in (ord("s"), ord("n")):
            return key == ord("s")


def usable_measurement(measurement):
    fps = measurement["delivery_fps"]
    return (measurement["status"] == "completed" and measurement["observed_dimensions"].keys()
            == {"1920x1080"} and measurement["failed_reads_including_warmup"] == 0
            and isinstance(fps, (int, float)) and math.isfinite(fps) and fps > 0)


def check_camera(root, round_id, index, hz):
    if not re.fullmatch(r"R[0-9]{2,}", round_id):
        raise ValueError("ID de ronda inválido.")
    device = tmcamera(index)
    if input("Confirma TMCAM 8305, escena sin personas y escribe TMCAM: ").strip() != "TMCAM":
        return 2
    check = {
        "round_id": round_id, "at_utc": utc_now(), "camera": "TMCAM 8305",
        "device_path": device.path, "index": index, "antiflicker_60hz": hz,
        "visible_bands": {light: None for light in LIGHTS}, "approved": False,
    }
    capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    try:
        check["config"] = configure_camera(capture)
        print("Midiendo entregas durante 60 segundos después de 5 segundos de calentamiento.")
        check["measurement"] = measure_capture(
            capture, 60, 5, .25,
            progress=lambda count, seconds: print(
                f"{seconds:.0f} s medidos; {count} lecturas válidas", flush=True
            ),
        )
        if usable_measurement(check["measurement"]):
            check["visible_bands"] = {light: inspect_bands(capture, light) for light in LIGHTS}
            print(f'FPS medidos: {check["measurement"]["delivery_fps"]:.3f}. Referencia: 29,241.')
            print(f'Intervalos mayores a 250 ms: {check["measurement"]["gaps_over_threshold"]}.')
            if not any(check["visible_bands"].values()):
                check["approved"] = input(
                    "Si la entrega fue estable y comparable, escribe APROBAR: "
                ).strip() == "APROBAR"
    except (ValueError, cv2.error) as exc:
        check["error"] = str(exc)
    finally:
        capture.release()
        cv2.destroyAllWindows()
    check_id = f"{round_id}-{uuid4().hex}"
    checks = child(root, "checks")
    checks.mkdir(exist_ok=True)
    publish_directory(child(checks, check_id), check)
    print(f"Comprobación {check_id}: " + ("aprobada" if check["approved"] else "pendiente"))
    return 0 if check["approved"] else 1


def validate_check(check, row, device):
    if (check["round_id"] != row["round_id"] or check["approved"] is not True
            or check["camera"] != "TMCAM 8305" or check["device_path"] != device.path
            or check["index"] != device.index or not usable_measurement(check["measurement"])
            or any(check["visible_bands"][light] is not False for light in LIGHTS)):
        raise ValueError("La ronda requiere una comprobación aprobada de esta TMCAM.")


def capture_session(folder, row, camera_check, index, resume):
    shots = shots_for(row)
    device = tmcamera(index)
    validate_check(camera_check, row, device)
    if folder.exists() != resume:
        raise ValueError("Indica reanudación solo para una sesión existente del mismo encuentro.")
    if input("Confirma consentimiento, aprobación de captura y destino; escribe CAPTURAR: "
             ).strip() != "CAPTURAR":
        return 2
    capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    try:
        config = configure_camera(capture)
        checked_config = camera_check["config"]
        if (config["backend"] != checked_config["backend"]
                or config["driver_reported"] != checked_config["driver_reported"]):
            raise ValueError("El modo cambió desde la comprobación; verifica la ronda de nuevo.")
        read_frame(capture)
        if resume:
            snapshot = read_json(child(folder, "record.json"))
            if snapshot["plan"] != row or snapshot["camera_check"] != camera_check:
                raise ValueError("La reanudación requiere el mismo plan y comprobación de cámara.")
        else:
            snapshot = {
                "schema_version": 1, "source": "camera", "plan": row,
                "started_at": datetime.now().astimezone().isoformat(),
                "camera_check": camera_check, "camera_config": config,
            }
            publish_directory(folder, snapshot)
        return guide_capture(capture, folder, snapshot, shots)
    finally:
        capture.release()
        cv2.destroyAllWindows()


def guide_capture(capture, folder, snapshot, shots):
    attempt_root = child(folder, "attempts")
    if any(attempt_root.glob(".pending-*")):
        raise ValueError("La sesión tiene registros pendientes de revisión.")
    _, accepted, _, _ = replay_attempts(folder, snapshot)
    slot = len(accepted)
    started = time.perf_counter()
    last_attempt = started
    adjusted_distance = None
    message = "Comprueba persona, luz y distancia antes de confirmar"
    while True:
        frame = read_frame(capture)
        complete = slot == len(shots)
        shot = shots[slot] if not complete else None
        distance = (adjusted_distance or shot["distance_m"]) if shot else None
        lines = [
            f'{snapshot["plan"]["session_id"]} - {slot}/{len(shots)} tomas',
            "R: excluir ultima guardada y repetir | Q: terminar",
            "Pauta completa" if complete else f'{shot["label"]} | {shot["lighting"]} | {distance:.2f} m',
            "" if complete else "ESPACIO confirma y guarda | D: ajustar m | X: rechazar intento",
            message,
        ]
        key = frame_key(frame, WINDOW, lines)
        if key == ord("q"):
            return 0 if complete else 1
        if key == ord("r") and slot:
            reason = input("Motivo de exclusión de la última toma (vacío cancela): ").strip()
            if reason:
                record_attempt(folder, snapshot, "excluded", reason=reason)
                slot -= 1
                adjusted_distance = None
                message = "Original conservado; repite esta toma"
        if complete:
            continue
        if key == ord("d"):
            try:
                distance = float(input("Distancia aproximada real en metros: ").replace(",", "."))
                if not valid_distance(distance):
                    raise ValueError
                adjusted_distance = distance
            except ValueError:
                message = "Distancia invalida; se conserva la anterior"
        if key == ord("x"):
            reason = input("Motivo de rechazo del intento (vacío cancela): ").strip()
            if reason:
                record_attempt(folder, snapshot, "rejected", reason=reason)
                message = "Intento anotado; vuelve a preparar la toma"
                last_attempt = time.perf_counter()
        if key == ord(" "):
            now = time.perf_counter()
            if now - started < 5 or now - last_attempt < 2:
                message = "Espera 5 s de calentamiento y 2 s entre tomas"
                continue
            record_attempt(folder, snapshot, "saved", frame=frame, distance=distance)
            slot += 1
            adjusted_distance = None
            message = "Toma guardada; cambia a la condicion siguiente"
            last_attempt = now


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("check-vault")
    check = actions.add_parser("check-camera")
    check.add_argument("--round", required=True)
    check.add_argument("--camera", type=int, required=True)
    check.add_argument("--antiflicker", choices=("confirmed_60hz", "other", "unconfirmed"),
                       required=True)
    capture = actions.add_parser("capture")
    capture.add_argument("--session", required=True)
    capture.add_argument("--check", required=True)
    capture.add_argument("--capture-approved", action="store_true")
    capture.add_argument("--resume", action="store_true")
    audit = actions.add_parser("audit")
    audit.add_argument("--session", action="append", help="Repetible; omitir para el plan completo.")
    args = parser.parse_args()
    try:
        root = verify_vault(args.vault)
        if args.action == "check-vault":
            print("Destino VeraCrypt/NTFS y acceso restringido comprobados.")
            return 0
        sessions = child(root, "sessions")
        plan = load_schedule(child(root, "plan.json"), sessions)
        if args.action == "audit":
            result = audit_dataset(plan, sessions, args.session)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return int(bool(result["issues"]))
        if args.action == "check-camera":
            if args.round not in {row["round_id"] for row in plan.values()}:
                raise ValueError("La ronda debe estar preasignada en el plan.")
            return check_camera(root, args.round, args.camera, args.antiflicker)
        if not args.capture_approved:
            raise ValueError("Falta la aprobación expresa para capturar.")
        if not re.fullmatch(r"R[0-9]{2,}-[0-9a-f]{32}", args.check):
            raise ValueError("Identificador de comprobación inválido.")
        camera_check = read_json(child(root, "checks", args.check, "record.json"))
        row = plan[args.session]
        sessions.mkdir(exist_ok=True)
        return capture_session(child(sessions, args.session), row, camera_check, camera_check["index"],
                               args.resume)
    except (OSError, ValueError, KeyError, TypeError, cv2.error, EOFError) as exc:
        print(f"Operación detenida: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
