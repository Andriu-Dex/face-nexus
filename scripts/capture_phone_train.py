"""Captura fotogramas del celular para TRAIN de adaptación. No calibra rechazo."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
from time import monotonic

import cv2
import numpy as np

from scripts.calibrate_hog import ROTATE, public_frame
from scripts.capture_manifest import child, utc_now, write_synced
from scripts.dataset_capture import verify_vault
from scripts.face_pipeline import load_detector
from scripts.hog_knn import FEATURE_COUNT, PEOPLE, inspect_live_frame
from scripts.phone_demo_manifest import (
    LOT_PARTS, MANIFEST_PARTS, ROLE_SPLIT, append_registered_session, listed_run,
    load_manifest, recover_unpublished_lot, require_explicit_encounter,
    require_phone_manifest, reserve_lot_directory, session_record,
)
from scripts.phone_serial_bench import local_stream_url


DEFAULT_COUNT = 20
DEFAULT_INTERVAL = 1.2
FOLDER = LOT_PARTS
WINDOW = "FaceNexus - captura celular"


def caption_frame(frame, text, *, flash=False):
    """Copia reducida para la ventana. El original no se modifica."""
    height, width = frame.shape[:2]
    scale = min(1., 960 / max(height, width))
    size = max(1, round(width * scale)), max(1, round(height * scale))
    view = cv2.resize(frame, size, interpolation=cv2.INTER_AREA) if scale < 1 else frame.copy()
    if flash:
        view = cv2.addWeighted(view, .65, np.full_like(view, 255), .35, 0)
        cv2.rectangle(view, (8, 8), (view.shape[1] - 8, view.shape[0] - 8), (0, 220, 0), 12)
    cv2.putText(view, text, (24, 72), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 0), 8, cv2.LINE_AA)
    cv2.putText(view, text, (24, 72), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 3, cv2.LINE_AA)
    return view


def beep():
    try:
        import winsound
        winsound.Beep(1200, 90)
    except (ImportError, RuntimeError):
        pass


def show(frame, text, *, flash=False, wait=1):
    cv2.imshow(WINDOW, caption_frame(frame, text, flash=flash))
    return cv2.waitKey(wait)


def countdown(seconds=5):
    canvas = np.zeros((480, 854, 3), np.uint8)
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    try:
        cv2.setWindowProperty(WINDOW, cv2.WND_PROP_TOPMOST, 1)
    except cv2.error:
        pass
    for remaining in range(seconds, 0, -1):
        print(f"Empieza a moverte en {remaining}...", flush=True)
        show(canvas, str(remaining), wait=1000)
    print("YA — cambia pose cuando parpadee FOTO.", flush=True)
    show(canvas, "YA", flash=True, wait=500)
    beep()


def collect_with_preview(url, count, interval, time_limit, rotation=0):
    """Muestra el video y avisa con flash y pitido en cada toma."""
    capture = cv2.VideoCapture()
    frames = []
    rotate = ROTATE[rotation]
    try:
        if not capture.open(url, cv2.CAP_FFMPEG, [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3500, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 400,
        ]):
            return "stream_unavailable", frames
        start = next_sample = monotonic()
        while len(frames) < count:
            if not capture.grab():
                return "stream_interrupted", frames
            now = monotonic()
            if now - start > time_limit:
                return "time_limit", frames
            ok, frame = capture.retrieve()
            if not ok or frame is None:
                return "invalid_frame", frames
            shown = cv2.rotate(frame, rotate) if rotate is not None else frame
            if now >= next_sample:
                frames.append(frame)
                print(f"FOTO {len(frames)}/{count}", flush=True)
                show(shown, f"FOTO {len(frames)}/{count}", flash=True, wait=180)
                beep()
                next_sample = now + interval
            else:
                wait = next_sample - now
                show(shown, f"Siguiente en {wait:.1f}s  |  {len(frames)}/{count}", wait=1)
    except (cv2.error, ValueError, RuntimeError):
        return "processing_error", frames
    finally:
        capture.release()
    return "sampled", frames


def encode_png(frame):
    ok, payload = cv2.imencode(".png", frame)
    if not ok:
        raise ValueError("No se pudo codificar el fotograma.")
    return payload.tobytes()


def preview_hashes(frames, rotation):
    """Huellas de la ráfaga antes de publicarla."""
    rotate = ROTATE[rotation]
    hashes = []
    for frame in frames:
        if rotate is not None:
            frame = cv2.rotate(frame, rotate)
        hashes.append(sha256(encode_png(frame)).hexdigest())
    return hashes


def store_session(folder, person, frames, rotation, detector, *, role="tune",
                  encounter_id, run_name="session"):
    """Guarda PNG, ficha y vectores HOG usables. Conserva también los fallos de recorte."""
    split = ROLE_SPLIT[role]
    rotate = ROTATE[rotation]
    records = []
    vectors = []
    labels = []
    ids = []
    images = child(folder, "frames")
    images.mkdir()
    for index, frame in enumerate(frames, 1):
        if rotate is not None:
            frame = cv2.rotate(frame, rotate)
        sample = f"{person}_PHONE_{index:04d}"
        png = encode_png(frame)
        write_synced(child(images, f"{sample}.png"), png)
        info = inspect_live_frame(frame, detector)
        row = public_frame(info)
        row.update({
            "sample_id": sample,
            "person_id": person,
            "split": split,
            "source": "phone_mjpeg",
            "rotation": rotation,
            "image_sha256": sha256(png).hexdigest(),
            "width": int(frame.shape[1]),
            "height": int(frame.shape[0]),
        })
        records.append(row)
        if info["reason"] == "usable":
            vectors.append(info["vector"].astype(np.float32))
            labels.append(person)
            ids.append(sample)
    summary = {
        "at_utc": utc_now(),
        "person_id": person,
        "role": role,
        "encounter_id": require_explicit_encounter(encounter_id, person, role, run_name),
        "split": split,
        "source": "phone_mjpeg",
        "rotation": rotation,
        "sampled_frames": len(frames),
        "usable_frames": len(vectors),
        "records": records,
    }
    write_synced(child(folder, "records.json"),
                 json.dumps(summary, indent=2, allow_nan=False).encode("utf-8"))
    np.savez(child(folder, "hog.npz"),
             vectors=np.asarray(vectors, np.float32).reshape(-1, FEATURE_COUNT),
             labels=np.array(labels, dtype=str),
             sample_ids=np.array(ids, dtype=str))
    return summary


def register_phone_session(vault, summary, run_name):
    """Añade la ráfaga al manifiesto privado y avisa si falta una clase."""
    hashes = [row["image_sha256"] for row in summary["records"]]
    return append_registered_session(
        child(vault, *MANIFEST_PARTS),
        session_record(
            summary["person_id"], run_name, summary["role"], summary["rotation"], hashes,
            sampled=summary["sampled_frames"], usable=summary["usable_frames"],
            encounter_id=summary.get("encounter_id"),
            at=summary["at_utc"]))


def commit_phone_session(vault, person, run_name, frames, rotation, detector, role="tune",
                         encounter_id=None):
    """Valida el manifiesto, publica en staging y registra de forma atómica."""
    vault = Path(vault)
    recover_unpublished_lot(vault, person, run_name)
    hashes = preview_hashes(frames, rotation)
    encounter_id = require_explicit_encounter(encounter_id, person, role, run_name)
    trial = load_manifest(child(vault, *MANIFEST_PARTS))
    trial.setdefault("sessions", [])
    trial["sessions"] = list(trial["sessions"])
    trial["sessions"].append(session_record(
        person, run_name, role, rotation, hashes,
        sampled=len(frames), usable=1, encounter_id=encounter_id))
    require_phone_manifest(trial)
    dest, staging = reserve_lot_directory(vault, person, run_name)
    registered = False
    try:
        summary = store_session(staging, person, frames, rotation, detector,
                                role=role, encounter_id=encounter_id, run_name=run_name)
        warnings = register_phone_session(vault, summary, run_name)
        registered = True
        staging.rename(dest)
    except Exception:
        listed = listed_run(load_manifest(child(vault, *MANIFEST_PARTS)), person, run_name)
        if staging.exists() and not (registered or listed):
            shutil.rmtree(staging)
        raise
    return summary, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--url", type=local_stream_url, required=True)
    parser.add_argument("--person", required=True, choices=PEOPLE)
    parser.add_argument("--run-name", required=True, help="Nombre único, por ejemplo k01_phone_tune_v1.")
    parser.add_argument("--encounter-id", required=True,
                        help="Identificador del encuentro real. No usar el papel ni el run-name.")
    parser.add_argument("--role", choices=tuple(ROLE_SPLIT), default="tune",
                        help="tune = ajuste (TRAIN). eval = evaluación (VALIDATION). Encuentros distintos.")
    parser.add_argument("--rotation", type=int, choices=(0, 90, 180, 270), default=0)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9_]{3,40}", args.run_name) or args.count < 5 or args.interval < .3:
        parser.error("Nombre de ensayo, cantidad o intervalo inválidos.")
    vault = verify_vault(args.vault)
    limit = args.count * args.interval + 8
    print("Captura de adaptación | mira la ventana FaceNexus en el PC.", flush=True)
    detector = load_detector(args.models)
    try:
        countdown()
        status, frames = collect_with_preview(
            args.url, args.count, args.interval, limit, args.rotation)
        if status != "sampled":
            raise RuntimeError(f"La captura no completó los fotogramas ({status}, {len(frames)}).")
        summary, warnings = commit_phone_session(
            vault, args.person, args.run_name, frames, args.rotation, detector, args.role,
            args.encounter_id)
        for warning in warnings:
            print(warning, flush=True)
        canvas = np.zeros((480, 854, 3), np.uint8)
        message = f"LISTO {summary['usable_frames']}/{summary['sampled_frames']}"
        print(f"Guardado {summary['usable_frames']}/{summary['sampled_frames']} recortes HOG usables "
              f"en {args.person}/{args.run_name}", flush=True)
        show(canvas, message, flash=True, wait=2500)
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
