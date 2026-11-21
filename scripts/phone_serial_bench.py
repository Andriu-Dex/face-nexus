"""Prueba de video local a ESP32 con el firmware de banco y el SG90 desconectado."""

import argparse
from ipaddress import ip_address
from pathlib import Path
from time import monotonic, sleep
from urllib.parse import urlsplit

import cv2

from scripts.face_pipeline import load_detector
from scripts.serial_bench import check_reply


SAMPLE_FRAMES = 5


def local_stream_url(value):
    """Solo se admiten direcciones IP locales, sin credenciales en la URL."""
    try:
        url = urlsplit(value)
        address = ip_address(url.hostname or "")
        port = url.port
    except ValueError:
        raise argparse.ArgumentTypeError("Indica una URL HTTP con IP local.") from None
    if (url.scheme != "http" or not address.is_private or address.is_unspecified
            or url.username is not None or url.fragment or port == 0):
        raise argparse.ArgumentTypeError("Indica una URL HTTP con IP local y sin credenciales.")
    return value


def inspect_video(url, detector):
    """Lee una muestra del video y devuelve medidas de captura y el motivo de denegación."""
    capture = cv2.VideoCapture()
    frames = 0
    size = None
    max_faces = 0
    try:
        opened = capture.open(url, cv2.CAP_FFMPEG, [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3500,
            cv2.CAP_PROP_READ_TIMEOUT_MSEC, 2000,
        ])
        if not opened:
            return frames, size, "STREAM_UNAVAILABLE"

        for _ in range(SAMPLE_FRAMES):
            read, frame = capture.read()
            if not read or frame is None or not frame.size:
                return frames, size, "STREAM_INTERRUPTED"
            frames += 1
            height, width = frame.shape[:2]
            size = width, height
            scale = min(1., 640 / max(size))
            detector_size = tuple(max(1, round(side * scale)) for side in size)
            detector.setInputSize(detector_size)
            _, faces = detector.detect(cv2.resize(frame, detector_size, interpolation=cv2.INTER_AREA))
            if faces is not None:
                max_faces = max(max_faces, len(faces))
    except cv2.error:
        return frames, size, "PROCESSING_ERROR"
    finally:
        capture.release()

    # La identidad todavía no se evalúa en el banco de comunicaciones.
    reason = "NO_FACE" if max_faces == 0 else "FACE_PRESENT"
    return frames, size, reason


def run_trial(connection, url, models, event_id):
    check_reply(connection, "PING", "PONG FACENEXUS BENCH 1")
    try:
        detector = load_detector(models)
    except (OSError, ValueError, cv2.error):
        frames, size, reason = 0, None, "MODEL_UNAVAILABLE"
    else:
        frames, size, reason = inspect_video(url, detector)
    # Se espera correlación exacta y no se reenvía el intento si falla el acuse.
    result = f"{event_id} UNKNOWN DENIED"
    acknowledgement = check_reply(connection, f"CHECK {result}", f"ACK {result} SIMULATED")
    return frames, size, reason, acknowledgement


def main():
    import serial

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, type=local_stream_url)
    parser.add_argument("--port", required=True)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    args = parser.parse_args()
    try:
        with serial.Serial(args.port, 115200, timeout=.2, write_timeout=2) as connection:
            sleep(2)
            connection.reset_input_buffer()
            event_id = int(monotonic() * 1000)
            frames, size, reason, acknowledgement = run_trial(connection, args.url, args.models, event_id)
    except (OSError, RuntimeError) as error:
        parser.exit(1, f"Ensayo serie sin confirmar ({type(error).__name__}).\n")
    resolution = f"{size[0]}x{size[1]}" if size else "sin imagen"
    print(f"Fotogramas: {frames} | Resolución: {resolution} | Motivo: {reason}")
    print(acknowledgement)
    if reason not in {"NO_FACE", "FACE_PRESENT"}:
        parser.exit(2, "Video o procesamiento incompleto.\n")


if __name__ == "__main__":
    main()
