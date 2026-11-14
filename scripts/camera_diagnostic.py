"""Diagnóstico de captura: solo conserva tiempos y dimensiones, nunca imágenes."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import time


def percentile(values, fraction):
    """Percentil por rango más cercano; una lista vacía no tiene percentil."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def measure_capture(capture, duration, warmup, gap_seconds, show_frame=None,
                    clock=time.perf_counter, progress=None):
    """Mide entregas al programa; no certifica FPS únicos del sensor ni latencia óptica.

    El llamador abre y libera la cámara. Un fallo termina el ensayo, sin cambiar
    de índice ni reconectar automáticamente a otro dispositivo.
    """
    if duration <= 0 or warmup < 0 or gap_seconds <= 0:
        raise ValueError("Duración y límite de pausa positivos; calentamiento no negativo.")
    started = clock()
    measurement_start = started + warmup
    timestamps = []
    read_ms = []
    dimensions = Counter()
    failures = 0
    status = "completed"
    next_progress = measurement_start + 10
    while clock() < measurement_start + duration:
        read_start = clock()
        ok, frame = capture.read()
        read_end = clock()
        if not ok or frame is None or frame.size == 0:
            failures += 1
            status = "read_failed"
            break
        if read_end >= measurement_start:
            timestamps.append(read_end)
            read_ms.append((read_end - read_start) * 1000)
            height, width = frame.shape[:2]
            dimensions[f"{width}x{height}"] += 1
        if show_frame is not None and not show_frame(frame):
            status = "interrupted"
            break
        if progress is not None and read_end >= next_progress:
            progress(len(timestamps), read_end - measurement_start)
            next_progress = read_end + 10
    finished = clock()
    intervals = [b - a for a, b in zip(timestamps, timestamps[1:])]
    span = timestamps[-1] - timestamps[0] if len(timestamps) >= 2 else 0
    return {
        "status": status,
        "requested_duration_seconds": duration,
        "warmup_seconds": warmup,
        "measurement_elapsed_seconds": max(0, finished - measurement_start),
        "successful_reads": len(timestamps),
        "failed_reads_including_warmup": failures,
        "observed_dimensions": dict(dimensions),
        "delivery_fps": (len(timestamps) - 1) / span if span > 0 else None,
        "interval_ms_median": statistics.median(intervals) * 1000 if intervals else None,
        "interval_ms_p95": percentile(intervals, .95) * 1000 if intervals else None,
        "interval_ms_max": max(intervals) * 1000 if intervals else None,
        "read_ms_p95": percentile(read_ms, .95),
        "gap_threshold_seconds": gap_seconds,
        "gaps_over_threshold": sum(value > gap_seconds for value in intervals),
    }


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("Debe ser un número finito positivo.")
    return number


def nonnegative(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("Debe ser un número finito no negativo.")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, required=True, help="Índice USB confirmado manualmente.")
    parser.add_argument("--backend", choices=["dshow", "msmf"], default="dshow")
    parser.add_argument("--duration", type=positive, default=600)
    parser.add_argument("--warmup", type=nonnegative, default=5)
    parser.add_argument("--gap-seconds", type=positive, default=.25)
    parser.add_argument("--no-preview", action="store_true")
    parser.add_argument("--output", type=Path, help="JSON técnico; por defecto outputs/camera/.")
    args = parser.parse_args()
    if args.camera < 0:
        parser.error("El índice no puede ser negativo.")
    print("Confirma el índice de la TMCAM 8305 y apunta a una escena sin personas.")
    print("No se guardarán fotogramas. No se probará otra cámara automáticamente.")
    if input("Escribe TMCAM para iniciar (cualquier otra respuesta cancela): ").strip() != "TMCAM":
        print("Cancelado sin abrir la cámara.")
        return 2
    try:
        import cv2
    except ImportError:
        print("Falta OpenCV: instala requirements.txt en el entorno del proyecto.")
        return 2

    report = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "camera_label_operator_declared": "TMCAM 8305",
        "camera_identity_verified_by_software": False,
        "camera_index": args.camera,
        "opencv_version": cv2.__version__,
        "backend_requested": args.backend,
        "target": {"width": 1920, "height": 1080, "fps": 30},
        "antiflicker_60hz": "manual_pending_verification",
        "flicker_visual_check": "pending",
        "reconnection_check": "pending_separate_manual_trial",
        "preview_enabled": not args.no_preview,
        "status": "open_failed",
    }
    capture = None
    try:
        backend = cv2.CAP_DSHOW if args.backend == "dshow" else cv2.CAP_MSMF
        capture = cv2.VideoCapture(args.camera, backend)
        if capture.isOpened():
            # Un set aceptado es una petición, no evidencia de resolución/FPS reales.
            report["set_accepted"] = {
                "width": bool(capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)),
                "height": bool(capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)),
                "fps": bool(capture.set(cv2.CAP_PROP_FPS, 30)),
            }
            report["driver_reported"] = {
                "width": capture.get(cv2.CAP_PROP_FRAME_WIDTH),
                "height": capture.get(cv2.CAP_PROP_FRAME_HEIGHT),
                "fps": capture.get(cv2.CAP_PROP_FPS),
                "fourcc": capture.get(cv2.CAP_PROP_FOURCC),
                "backend": capture.getBackendName(),
            }

            def preview(frame):
                cv2.imshow("FaceNexus - diagnostico sin grabacion (Q para salir)", frame)
                return cv2.waitKey(1) & 0xFF not in (ord("q"), 27)

            report.update(measure_capture(
                capture, args.duration, args.warmup, args.gap_seconds,
                show_frame=None if args.no_preview else preview,
                progress=lambda count, seconds: print(
                    f"{seconds:.0f} s medidos; {count} lecturas válidas", flush=True),
            ))
    except KeyboardInterrupt:
        report["status"] = "interrupted_no_complete_metrics"
    except Exception as error:
        report["status"] = "capture_error"
        report["error_type"] = type(error).__name__
    finally:
        if capture is not None:
            capture.release()
        if not args.no_preview:
            cv2.destroyAllWindows()

    # JSON estricto: los drivers pueden devolver NaN en propiedades no soportadas.
    for name, value in report.get("driver_reported", {}).items():
        if isinstance(value, float) and not math.isfinite(value):
            report["driver_reported"][name] = None
    output = args.output or Path("outputs/camera") / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    print(f"Reporte técnico: {output}")
    print("No hay aprobación automática: revisar identidad, FPS, pausas y parpadeo.")
    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
