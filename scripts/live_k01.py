"""Reconocimiento en vivo de K01: YuNet, CNN humano y el clasificador elegido."""

import argparse
import json
import os
import re
from pathlib import Path

import cv2
import numpy as np

from scripts.access import decide, decide_scene, default_permissions, simulate_authorize
from scripts.calibrate_hog import ROTATE
from scripts.capture_phone_train import WINDOW, show
from scripts.compare_identity_k01 import vote_knn
from scripts.hog_knn import (
    PEOPLE, accepts_open_set, align_detected_face, describe_face, describe_face_cnn, describe_fusion, describe_sface,
    detect_faces, runner_up_distance,
)
from scripts.identity_artifacts import load_verified_knn
from scripts.dataset_capture import verify_vault
from scripts.evaluate_hog_knn import K
from scripts.face_pipeline import load_detector, load_models
from scripts.human_cnn import HUMAN, resize_rgb
from scripts.identity_k01 import accept_k01, binary_vote
from scripts.phone_serial_bench import local_stream_url


FOUR_RUN = "identity_four_v2"
SVM_RUN = "identity_k01_v1"
HUMAN_RUN = "human_cnn_phone_v1"
TRIAL_FAMILIES = ("identity_four", "identity_four_other")
TRIAL_NAME = re.compile(r"^[a-z0-9_]{3,40}$")


def cnn_mark(human_model, bgr):
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    scores = np.asarray(human_model(resize_rgb([rgb]), training=False))[0]
    return int(np.argmax(scores)) == HUMAN, "H" if int(np.argmax(scores)) == HUMAN else "N"


def load_keras(path):
    os.environ.setdefault("KERAS_BACKEND", "jax")
    os.environ.setdefault("JAX_PLATFORMS", "cpu")
    import keras
    return keras.models.load_model(path, compile=False)


def overlay_text(decision, label, score_text, cnn_human, backend):
    cnn = "H" if cnn_human else "N"
    return f"{decision['outcome']}  {decision['reason']}  {label} {score_text} {backend} cnn={cnn}"


def identify_knn(gallery, labels, max_distance=None, min_gap=0.):
    def identify(vector):
        label, distance = vote_knn(gallery, labels, vector, k=K)
        gap = None
        if label in PEOPLE and distance is not None:
            runner = runner_up_distance(gallery, labels, vector, label)
            gap = None if runner is None else runner - distance
        limit = max_distance if max_distance is not None else float("inf")
        accepted = accepts_open_set(label, distance, gap, limit, min_gap)
        score = f"d={distance:.3f}" if distance is not None else "d=?"
        if max_distance is not None:
            score += f" T={max_distance:.3f}"
        if min_gap > 0:
            score += f" G={min_gap:.3f}"
            if gap is not None:
                score += f" g={gap:.3f}"
        # Cifras para la interfaz: confianza visual = cuánto margen queda bajo el umbral T.
        return label, accepted, score, {"distance": distance, "max_distance": max_distance}
    return identify


def identify_svm(model, threshold):
    def identify(vector):
        result = binary_vote(np.asarray(model(vector[None, :], training=False), dtype=np.float64)[0])
        label, margin = result if result is not None else ("OTHER", 0.)
        return label, accept_k01(label, margin, threshold), f"m={margin:.2f}"
    return identify


def recognize_crop(crop, human_model, identify, permissions, *,
                   trust_detector=True, backend="knn", model_ready=True, describe=None):
    """Si YuNet ya recortó un rostro, no se deja que LFW/CIFAR anule esa detección."""
    if model_ready is not True or identify is None:
        return decide(face_count=1, candidate=None, accepted=False, permission_active=False,
                      model_ready=False)
    vector = (describe or describe_face)(crop)
    if vector is None:
        return decide(face_count=1, candidate=None, accepted=False, permission_active=False)
    cnn_human, _mark = cnn_mark(human_model, crop)
    is_human = True if trust_detector else cnn_human
    label, accepted, score_text, *extra = identify(vector)
    candidate = label if accepted and label in PEOPLE else None
    row = decide(
        face_count=1,
        candidate=candidate,
        accepted=candidate is not None,
        permission_active=bool(permissions.get(candidate)) if candidate else False,
        is_human=is_human,
    )
    row["nearest"] = label
    row["score_text"] = score_text
    row["human"] = bool(cnn_human)
    if extra:
        row.update(extra[0])
    row["model"] = backend
    row["overlay"] = overlay_text(row, label, score_text, cnn_human, backend)
    return row


def face_descriptor(info, aligner):
    """Elige la misma representación utilizada para construir la galería."""
    if info.get("preprocessing") == "sface":
        return lambda crop: describe_sface(crop, aligner)
    if info.get("preprocessing") == "face_cnn":
        net = cv2.dnn.readNetFromONNX(str(info["face_cnn_path"]))
        return lambda crop: describe_face_cnn(crop, net)
    if info.get("preprocessing") == "fusion":
        net = cv2.dnn.readNetFromONNX(str(info["face_cnn_path"]))
        weight = info["cnn_weight"]
        # Necesita la caja (CNN) y los landmarks (SFace): recibe fotograma y detección.
        describe = lambda frame, detection: describe_fusion(frame, detection, net, aligner, weight)
        describe.takes_detection = True
        return describe
    return describe_face


def recognize_frame(frame, detector, human_model, identify, permissions, backend,
                    model_ready=True, aligner=None, describe=None):
    """Una decisión por caja YuNet. La escena abre si al menos una región está autorizada."""
    boxes = detect_faces(frame, detector)
    if not boxes:
        row = decide(face_count=0, candidate=None, accepted=False, permission_active=False,
                     model_ready=model_ready)
        if model_ready and human_model is not None:
            _is_human, mark = cnn_mark(human_model, frame)
            row["overlay"] = f"{row['outcome']}  {row['reason']}  cnn={mark}"
        else:
            row["overlay"] = f"{row['outcome']}  {row['reason']}"
        row["regions"] = []
        return row
    regions = []
    for detection in boxes:
        left, top, right, bottom, *_ = detection
        crop = (align_detected_face(frame, detection, aligner) if aligner is not None
                else frame[top:bottom, left:right])
        if crop is None:
            row = decide(face_count=1, candidate=None, accepted=False, permission_active=False,
                         model_ready=model_ready)
        else:
            describe_region = describe
            if getattr(describe, "takes_detection", False):
                describe_region = lambda _crop, d=detection: describe(frame, d)
            row = recognize_crop(crop, human_model, identify, permissions,
                                 trust_detector=True, backend=backend, model_ready=model_ready,
                                 describe=describe_region)
        row["box"] = [left, top, right, bottom]
        regions.append(row)
    scene = decide_scene([{key: row[key] for key in ("outcome", "reason", "identity")}
                          for row in regions])
    scene["regions"] = regions
    labels = " ".join(row.get("overlay", row["identity"]) for row in regions)
    scene["overlay"] = (
        f"{scene['outcome']}  {scene['reason']}  {scene['identity']}  "
        f"n={len(regions)}  {backend} | {labels}"
    )
    return scene


def paint_regions(frame, regions):
    """Copia con cajas. Verde = autorizada; rojo = denegada."""
    view = frame.copy()
    for row in regions:
        box = row.get("box")
        if not box:
            continue
        left, top, right, bottom = box
        color = (40, 200, 40) if row["outcome"] == "GRANTED" else (40, 40, 220)
        cv2.rectangle(view, (left, top), (right, bottom), color, 3)
    return view


def run_stream(url, rotation, recognize_fn, limit):
    """Muestra cada fotograma y la decisión. Escape cierra."""
    capture = cv2.VideoCapture()
    rotate = ROTATE[rotation]
    last = None
    seen = 0
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    try:
        if not capture.open(url, cv2.CAP_FFMPEG, [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3500, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 400,
        ]):
            return "stream_unavailable", last
        while limit <= 0 or seen < limit:
            if not capture.grab():
                return "stream_interrupted", last
            ok, frame = capture.retrieve()
            if not ok or frame is None:
                return "invalid_frame", last
            shown = cv2.rotate(frame, rotate) if rotate is not None else frame
            last = recognize_fn(shown)
            executed = simulate_authorize({
                key: last[key] for key in ("outcome", "reason", "identity", "event_id")
                if key in last
            } if last.get("event_id") else decide_scene([
                {key: last[key] for key in ("outcome", "reason", "identity")}
            ]))
            painted = paint_regions(shown, last.get("regions") or [])
            text = last.get("overlay") or f"{executed['decision']}  {executed['reason']}"
            key = show(painted, text, flash=executed["decision"] == "GRANTED", wait=1)
            print(text, flush=True)
            seen += 1
            if key in (27, ord("q")):
                return "closed", last
    except (cv2.error, ValueError, RuntimeError):
        return "processing_error", last
    finally:
        capture.release()
        cv2.destroyAllWindows()
    return "done", last


def four_folder(root):
    return Path(root) / "experiments" / "identity_four" / FOUR_RUN


def parse_trial_ref(trial):
    """Familia/nombre. Sin barra se usa identity_four. No pisa otra carpeta."""
    text = (trial or FOUR_RUN).strip().replace("\\", "/")
    if "/" in text:
        family, name = text.split("/", 1)
    else:
        family, name = "identity_four", text
    if family not in TRIAL_FAMILIES or not TRIAL_NAME.fullmatch(name):
        raise ValueError(
            "Indica el ensayo como identity_four/identity_four_v2 o "
            "identity_four_other/nombre_del_candidato.")
    return family, name


def resolve_knn_trial(vault, trial=FOUR_RUN):
    """Carga galería y T/G verificados. No escribe ni sustituye otro ensayo."""
    family, name = parse_trial_ref(trial)
    folder = Path(vault) / "experiments" / family / name
    bundle, reason = load_verified_knn(folder)
    if bundle is None:
        return folder, None, {
            "family": family,
            "name": name,
            "label": f"{family}/{name}",
            "reason": reason or "model_unavailable",
        }
    info = {
        "family": family,
        "name": name,
        "label": f"{family}/{name}",
        "gallery_sha256": bundle["gallery_sha256"],
        "max_distance": float(bundle["max_distance"]),
        "min_gap": float(bundle.get("min_gap") or 0.),
        "preprocessing": bundle["preprocessing"],
        "face_cnn_path": bundle.get("face_cnn_path"),
        "cnn_weight": bundle.get("cnn_weight"),
        "reason": None,
    }
    return folder, bundle, info


def build_identify(root, backend, margin, max_distance=None, trial=FOUR_RUN):
    """k-NN exige galería y T del mismo ensayo. SVM queda como diagnóstico sin pestillo."""
    if backend == "knn":
        folder, bundle, info = resolve_knn_trial(root, trial)
        if bundle is None:
            return None, False, info["reason"], info
        if max_distance is not None:
            bundle = dict(bundle)
            bundle["max_distance"] = max_distance
        identify = identify_knn(
            bundle["vectors"], bundle["labels"], bundle["max_distance"],
            bundle.get("min_gap", 0.))
        return identify, True, None, info
    model = load_keras(root / "experiments" / "identity_k01" / SVM_RUN / "model.keras")
    return identify_svm(model, margin), True, None, {"label": "svm/identity_k01_v1"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--url", type=local_stream_url, required=True)
    parser.add_argument("--rotation", type=int, choices=(0, 90, 180, 270), default=0)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    parser.add_argument("--frames", type=int, default=0, help="0 = hasta Escape")
    parser.add_argument("--backend", choices=("knn", "svm"), default="knn")
    parser.add_argument("--margin", type=float, default=0.)
    parser.add_argument("--max-distance", type=float, default=None,
                        help="Si se omite, se lee knn_max_distance.json o no hay T.")
    parser.add_argument(
        "--trial", default=FOUR_RUN,
        help="identity_four/identity_four_v2 o identity_four_other/<run>. No escribe galería.")
    args = parser.parse_args()
    root = verify_vault(args.vault)
    human_model = load_keras(root / "experiments" / "human_cnn" / HUMAN_RUN / "model.keras")
    try:
        identify, model_ready, reason, info = build_identify(
            root, args.backend, args.margin, args.max_distance, trial=args.trial)
    except ValueError as error:
        parser.error(str(error))
    if args.backend == "knn" and not model_ready:
        print(f"Galería o umbral no verificados ({reason}). Todo DENIED.", flush=True)
    else:
        print(
            f"Ensayo {info.get('label')} hash={(info.get('gallery_sha256') or '')[:12]} "
            f"T={info.get('max_distance')} G={info.get('min_gap')}",
            flush=True,
        )
    if info.get("preprocessing") in ("aligned_hog", "sface", "fusion"):
        detector, aligner = load_models(args.models)
    else:
        detector, aligner = load_detector(args.models), None
    permissions = default_permissions()
    describe = face_descriptor(info, aligner)

    def recognize(frame):
        return recognize_frame(frame, detector, human_model, identify, permissions, args.backend,
                               model_ready=model_ready, aligner=aligner,
                               describe=describe)

    print(
        f"Ventana FaceNexus ({args.backend}). Escape cierra. "
        "Un integrante autorizado: GRANTED; extraños: DENIED.",
        flush=True,
    )
    status, last = run_stream(args.url, args.rotation, recognize, args.frames)
    print(status)
    if last:
        print(json.dumps({key: last[key] for key in last if key != "overlay"}, indent=2, default=str))


if __name__ == "__main__":
    main()
