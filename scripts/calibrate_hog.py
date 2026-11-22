"""Mide el margen de identificación y prepara el rechazo de SVM y MLP."""

import argparse
from collections import Counter
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
from time import monotonic

import cv2
import numpy as np

from scripts.capture_manifest import child, read_json, utc_now, write_synced
from scripts.compare_hog_models import read_split
from scripts.dataset_capture import verify_vault
from scripts.evaluate_hog_knn import MANIFEST_FOLDER, validate_manifest
from scripts.face_pipeline import describe, load_detector
from scripts.hog_knn import PEOPLE, inspect_live_frame
from scripts.phone_serial_bench import local_stream_url


MODELS = ("svm", "mlp")
SAMPLES = 5
VOTES = 3
INTERVAL = .3
TIME_LIMIT = 2.5
PROFILE = "hog-margin-5x3-v1"
ROTATE = {0: None, 90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180,
          270: cv2.ROTATE_90_COUNTERCLOCKWISE}
PROBE_SAMPLES = 3


def frame_vote(scores):
    """El margen es la diferencia entre las dos mayores puntuaciones."""
    scores = np.asarray(scores)
    if scores.shape != (len(PEOPLE),) or not np.isfinite(scores).all():
        return None
    second, best = np.argsort(scores)[-2:]
    margin = float(scores[best]) - float(scores[second])
    return (PEOPLE[best], margin) if margin > 0 and math.isfinite(margin) else None


def attempt_vote(votes):
    """Requiere tres votos por una misma identidad y retiene el tercer mejor margen."""
    counts = Counter(person for person, _ in votes)
    for person, count in counts.items():
        if count >= VOTES:
            margins = sorted((margin for label, margin in votes if label == person), reverse=True)
            return {"candidate": person, "margin": margins[VOTES - 1]}
    return None


def load_saved_models(folder):
    os.environ["KERAS_BACKEND"] = "jax"
    os.environ["JAX_PLATFORMS"] = "cpu"
    import keras

    paths = {name: child(folder, f"{name}.keras") for name in MODELS}
    hashes = {name: sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}
    models = {name: keras.models.load_model(path, compile=False) for name, path in paths.items()}
    return models, hashes


def public_frame(report, model_votes=None):
    """Quita el vector HOG. Conserva calidad de detección y votos por fotograma."""
    row = {key: value for key, value in report.items() if key != "vector"}
    if model_votes is not None:
        row["votes"] = model_votes
    return row


def score_models(vector, models):
    votes = {}
    results = []
    for name, model in models.items():
        scores = np.asarray(model(vector[None, :], training=False), dtype=np.float64)[0]
        result = frame_vote(scores)
        if result is None:
            continue
        person, margin = result
        votes[name] = {
            "candidate": person,
            "margin": margin,
            "scores": {label: float(scores[index]) for index, label in enumerate(PEOPLE)},
        }
        results.append((name, result))
    return votes, results


def collect_frames(url, count, interval, time_limit):
    """Lee fotogramas crudos. El reloj empieza después de abrir el video."""
    capture = cv2.VideoCapture()
    frames = []
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
            if now < next_sample:
                continue
            ok, frame = capture.retrieve()
            if not ok or frame is None:
                return "invalid_frame", frames
            frames.append(frame)
            next_sample = now + interval
            if monotonic() - start > time_limit:
                return "time_limit", frames
    except (cv2.error, ValueError, RuntimeError):
        return "processing_error", frames
    finally:
        capture.release()
    return "sampled", frames


def read_attempt(url, detector, models, rotation=0):
    status, frames = collect_frames(url, SAMPLES, INTERVAL, TIME_LIMIT)
    count = usable = 0
    votes = {name: [] for name in models}
    reports = []
    if status == "stream_unavailable":
        return status, count, usable, {}, reports
    rotate = ROTATE[rotation]
    try:
        for frame in frames:
            if rotate is not None:
                frame = cv2.rotate(frame, rotate)
            info = inspect_live_frame(frame, detector)
            count += 1
            model_votes = None
            if info["reason"] == "usable":
                usable += 1
                model_votes, scored = score_models(info["vector"], models)
                for name, result in scored:
                    votes[name].append(result)
            reports.append(public_frame(info, model_votes))
    except (cv2.error, ValueError, RuntimeError):
        return "processing_error", count, usable, {}, reports
    if status != "sampled":
        return status, count, usable, {}, reports
    return ("usable" if usable >= VOTES else "insufficient_faces"), count, usable, {
        name: attempt_vote(results) for name, results in votes.items()
    }, reports


def probe_orientations(url, detector):
    """Prueba los cuatro giros sobre los mismos fotogramas. No evalúa identidad."""
    status, frames = collect_frames(url, PROBE_SAMPLES, INTERVAL, TIME_LIMIT)
    summary = {"status": status, "sampled_frames": len(frames), "rotations": []}
    if not frames:
        return summary
    for rotation, rotate in ROTATE.items():
        reasons = []
        heights = []
        for frame in frames:
            if rotate is not None:
                frame = cv2.rotate(frame, rotate)
            info = inspect_live_frame(frame, detector)
            reasons.append(info["reason"])
            if info["box_height_px"]:
                heights.append(info["box_height_px"])
        usable = reasons.count("usable")
        summary["rotations"].append({
            "rotation": rotation,
            "usable": usable,
            "no_face": reasons.count("no_face"),
            "multiple_faces": reasons.count("multiple_faces"),
            "empty_hog": reasons.count("empty_hog"),
            "median_box_height_px": describe(heights)["median"] if heights else None,
        })
    ranked = sorted(summary["rotations"],
                    key=lambda row: (row["usable"], row["median_box_height_px"] or 0),
                    reverse=True)
    best = ranked[0]
    summary["suggested_rotation"] = best["rotation"] if best["usable"] else None
    return summary


def review_r01(folder, models):
    baseline = child(folder, "knn_baseline_v1")
    original = read_json(child(folder, "hog_comparison_v1", "summary.json"))
    manifest_bytes = child(folder, "manifest.json").read_bytes()
    vector_bytes = child(baseline, "validation.npz").read_bytes()
    if (sha256(manifest_bytes).hexdigest() != original["manifest_sha256"]
            or sha256(vector_bytes).hexdigest() != original["hog_inputs_sha256"]["validation"]):
        raise ValueError("El manifiesto o los vectores difieren de la comparación.")
    manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
    validate_manifest(manifest)
    records = read_json(child(baseline, "records.json"))["validation"]
    vectors, labels = read_split(baseline, "validation", records, manifest["validation"])
    summary = {}
    for name, model in models.items():
        correct, wrong = [], []
        scores = np.asarray(model(vectors, training=False))
        for scores_row, true_label in zip(scores, labels, strict=True):
            result = frame_vote(scores_row)
            if result is not None:
                winner, margin = result
                (correct if winner == true_label else wrong).append(margin)
        summary[name] = {"correct": describe(correct), "wrong_identity": describe(wrong),
                         "without_vote": len(labels) - len(correct) - len(wrong)}
    return {"usable_frames": len(labels), "original_frames": len(records), "models": summary}


def inspect_attempts(records):
    """Resume intentos incompletos: útil para ver dominio celular vs TMCAM."""
    by_person = {}
    for row in records:
        person = row["participant"]
        entry = by_person.setdefault(person, {
            "total": 0, "usable": 0, "other_status": {},
            "models": {name: {"correct": 0, "wrong": 0, "no_vote": 0, "candidates": {}}
                       for name in MODELS},
        })
        entry["total"] += 1
        if row["status"] != "usable":
            entry["other_status"][row["status"]] = entry["other_status"].get(row["status"], 0) + 1
            continue
        entry["usable"] += 1
        for name in MODELS:
            vote = (row.get("votes") or {}).get(name)
            stats = entry["models"][name]
            if vote is None:
                stats["no_vote"] += 1
                continue
            candidate = vote["candidate"]
            stats["candidates"][candidate] = stats["candidates"].get(candidate, 0) + 1
            if candidate == person:
                stats["correct"] += 1
            else:
                stats["wrong"] += 1
    usable = [row for row in records if row["status"] == "usable"]
    return {
        "status": "progress",
        "total": len(records),
        "usable": len(usable),
        "missing_known": [person for person in PEOPLE
                          if not any(row["participant"] == person for row in usable)],
        "unknown_people": sorted({row["participant"] for row in usable
                                  if str(row["participant"]).startswith("A")}),
        "by_participant": by_person,
    }


def compare_attempts(records):
    usable = [row for row in records if row["status"] == "usable"]
    present = {row["participant"] for row in usable}
    if not set(PEOPLE).issubset(present) or not any(person.startswith("A") for person in present):
        progress = inspect_attempts(records)
        progress["status"] = "insufficient_live_data"
        return progress

    known = [row for row in usable if row["participant"] in PEOPLE]
    unknown = [row for row in usable if row["participant"].startswith("A")]
    result = {"status": "exploratory", "total": len(records), "usable_known": len(known),
              "usable_unknown": len(unknown), "unknown_people": len({row["participant"] for row in unknown}),
              "models": {}}
    for name in MODELS:
        unsafe = [vote["margin"] for row in usable if (vote := row["votes"][name]) is not None
                  and vote["candidate"] != row["participant"]]
        threshold = math.nextafter(max(unsafe), math.inf) if unsafe else 0.
        correct = sum(vote["candidate"] == row["participant"]
                      and vote["margin"] >= threshold for row in known if (vote := row["votes"][name]) is not None)
        wrong_before = sum(vote["candidate"] != row["participant"] for row in known
                           if (vote := row["votes"][name]) is not None)
        result["models"][name] = {
            "candidate_threshold": threshold,
            "known_correct_at_threshold": correct,
            "known_rejected_at_threshold": len(known) - correct,
            "wrong_known_before_threshold": wrong_before,
            "accepted_unknown_before_threshold": sum(row["votes"][name] is not None for row in unknown),
        }
    return result


def load_attempt_records(folder, hashes):
    attempts = child(folder, "rejection_calibration")
    records = [read_json(child(attempts, path.name)) for path in sorted(attempts.glob("*.json"))]
    if any(record["profile"] != PROFILE or record["model_hashes"] != hashes for record in records):
        raise ValueError("Los intentos se registraron con otra política de muestreo o modelos.")
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, help="Volumen VeraCrypt. Obligatorio salvo en probe.")
    modes = parser.add_subparsers(dest="mode", required=True)
    modes.add_parser("review-r01", help="Mide márgenes por fotograma, sin fijar umbrales.")
    attempt = modes.add_parser("attempt", help="Guarda una presentación de calibración sin imágenes.")
    attempt.add_argument("--url", type=local_stream_url, required=True)
    attempt.add_argument("--participant", required=True, help="Código K01 a K04 o A01, A02, etc.")
    attempt.add_argument("--number", type=int, required=True)
    attempt.add_argument("--rotation", type=int, choices=(0, 90, 180, 270), default=0,
                         help="Giro horario del fotograma para orientar el video.")
    attempt.add_argument("--models", type=Path, default=Path("models/verified"))
    modes.add_parser("compare-attempts", help="Calcula candidatos de umbral con las tomas en vivo.")
    modes.add_parser("inspect-attempts", help="Resume intentos aunque falten integrantes.")
    probe = modes.add_parser("probe", help="Elige el giro del celular sin guardar identidad.")
    probe.add_argument("--url", type=local_stream_url, required=True)
    probe.add_argument("--models", type=Path, default=Path("models/verified"))
    args = parser.parse_args()
    if args.mode == "probe":
        print(json.dumps(probe_orientations(args.url, load_detector(args.models)),
                         indent=2, allow_nan=False))
        return
    if args.vault is None:
        parser.error("--vault es obligatorio en este modo.")
    if args.mode == "attempt" and (
            not re.fullmatch(r"(?:K0[1-4]|A(?!00)[0-9]{2})", args.participant) or not 1 <= args.number <= 999):
        parser.error("Código de participante o número de intento inválido.")
    folder = child(verify_vault(args.vault), *MANIFEST_FOLDER)
    models, hashes = load_saved_models(child(folder, "hog_comparison_v1"))
    if args.mode == "review-r01":
        print(json.dumps(review_r01(folder, models), indent=2, allow_nan=False))
        return

    if args.mode in {"compare-attempts", "inspect-attempts"}:
        records = load_attempt_records(folder, hashes)
        report = inspect_attempts(records) if args.mode == "inspect-attempts" else compare_attempts(records)
        print(json.dumps(report, indent=2, allow_nan=False))
        return

    attempts = child(folder, "rejection_calibration")
    attempts.mkdir(exist_ok=True)
    path = child(attempts, f"{args.participant}-{args.number:03}.json")
    if path.exists():
        raise FileExistsError("Ese número de intento ya existe para el participante.")
    detector = load_detector(args.models)
    # Carga los modelos antes de iniciar el reloj de la presentación.
    for model in models.values():
        model(np.zeros((1, model.input_shape[-1]), np.float32), training=False)
    status, sampled, usable, votes, frames = read_attempt(args.url, detector, models, args.rotation)
    record = {"at_utc": utc_now(), "participant": args.participant, "attempt": args.number,
              "profile": PROFILE, "model_hashes": hashes, "status": status,
              "sampled_frames": sampled, "usable_frames": usable, "rotation": args.rotation,
              "votes": votes, "frames": frames}
    write_synced(path, json.dumps(record, indent=2, allow_nan=False).encode("utf-8"))
    print(f"Intento registrado | estado {status} | fotogramas usables {usable}/{sampled}")
    if frames:
        reasons = sorted({row["reason"] for row in frames})
        print(f"Detección por fotograma: {', '.join(reasons)}")


if __name__ == "__main__":
    main()
