"""Plan y manifiesto privado de captura. Cada intento conserva su propia ficha."""

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile

import cv2
import numpy as np


FRAME_SHAPE = (1080, 1920, 3)
LIGHTS = ("diffuse", "lateral")
SPLITS = ("TRAIN", "VALIDATION", "TEST")
NOMINAL = (
    ("Frontal neutra", .8), ("Frontal con sonrisa", .8),
    ("Giro izquierda 20 grados", .8), ("Giro derecha 20 grados", .8),
    ("Inclinacion arriba 10 grados", .8), ("Inclinacion abajo 10 grados", .8),
    ("Frontal cercana", .6), ("Frontal alejada", 1.2),
    ("Giro lento", .8), ("Recolocacion natural", .8),
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def child(root, *parts):
    path = root.joinpath(*parts)
    if path.resolve() != path or not path.is_relative_to(root):
        raise ValueError("Ruta fuera del destino aprobado o redirigida.")
    return path


def valid_distance(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def validate_plan(rows):
    """Comprueba todo el calendario antes de que el operador elija una sesión."""
    if not isinstance(rows, list) or not rows:
        raise ValueError("El plan requiere una lista de sesiones.")
    sessions, rounds, encounters, unknown = {}, {}, set(), {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Ficha de sesión inválida.")
        person, session, round_id = (row[key] for key in ("person_id", "session_id", "round_id"))
        split, light = row["split"], row["first_light"]
        if not re.fullmatch(r"[KU][0-9]{2,}", person) or not re.fullmatch(
                re.escape(person) + r"_S[0-9]{2,}", session):
            raise ValueError("Identidad o ID de sesión inválido.")
        if person in ("K01", "K02", "K03", "K04") and session.endswith("_S01"):
            raise ValueError("S01 corresponde a la colección histórica de desarrollo.")
        if not re.fullmatch(r"R[0-9]{2,}", round_id) or split not in SPLITS or light not in LIGHTS:
            raise ValueError("Ronda, partición o iluminación inicial inválida.")
        if not all(isinstance(row[key], str) and row[key].strip()
                   for key in ("consent_ref", "setup")):
            raise ValueError("La sesión requiere referencia de consentimiento y montaje.")
        if sessions.get(session) or (person, round_id) in encounters:
            raise ValueError("Sesión repetida o participante repetido en la ronda.")
        if rounds.setdefault(round_id, (split, light)) != (split, light):
            raise ValueError("Una ronda debe conservar su partición y orden de luces.")
        if person.startswith("U") and (
                split == "TRAIN" or unknown.setdefault(person, split) != split):
            raise ValueError("Cada desconocido pertenece solo a VALIDATION o solo a TEST.")
        for shot in row.get("difficult", []):
            if (not isinstance(shot["label"], str) or not shot["label"].strip()
                    or shot["lighting"] not in LIGHTS or not valid_distance(shot["distance_m"])):
                raise ValueError("Toma difícil inválida.")
        encounters.add((person, round_id))
        sessions[session] = row
    return sessions


def shots_for(row):
    first = row["first_light"]
    second = LIGHTS[1 - LIGHTS.index(first)]
    nominal = [
        {"label": label, "lighting": light, "distance_m": distance, "condition": "nominal"}
        for light in (first, second) for label, distance in NOMINAL
    ]
    return nominal + [{**shot, "condition": "difficult"} for shot in row.get("difficult", [])]


def write_synced(path, payload):
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def publish_directory(destination, metadata, payload=None):
    """Publica PNG y ficha juntos con un renombrado dentro del mismo volumen."""
    if destination.exists():
        raise FileExistsError("Ya existe este registro.")
    staging = Path(tempfile.mkdtemp(prefix=".pending-", dir=destination.parent))
    if payload is not None:
        write_synced(staging / metadata["relative_path"], payload)
    serialized = json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False)
    write_synced(staging / "record.json", serialized.encode("utf-8"))
    # Un fallo conserva el directorio pendiente para que la auditoría lo señale.
    staging.rename(destination)


def active_records(root):
    if not root.exists():
        return {}
    return {
        folder.name: read_json(child(root, folder.name, "record.json"))
        for folder in sorted(root.iterdir()) if not folder.name.startswith(".pending-")
    }


def load_schedule(plan_path, sessions_root):
    plan = validate_plan(read_json(plan_path))
    for session, snapshot in active_records(sessions_root).items():
        if plan.get(session) != snapshot["plan"]:
            raise ValueError(f"El plan cambió para la sesión registrada {session}.")
    return plan


def replay_attempts(folder, session, verify_images=False):
    """Reconstruye el orden de las tomas a partir del manifiesto inmutable."""
    shots = shots_for(session["plan"])
    attempts_root = folder / "attempts"
    records = active_records(child(folder, "attempts"))
    accepted, excluded, hashes = [], {}, []
    for number, (attempt_id, record) in enumerate(records.items(), 1):
        expected_id = f"A{number:06d}"
        if number != record["attempt"] or attempt_id != expected_id:
            raise ValueError("La secuencia de intentos no es continua.")
        slot = len(accepted) + 1
        status = record["status"]
        if status == "excluded":
            slot -= 1
            if not accepted or record["related_attempt"] != accepted.pop():
                raise ValueError("La exclusión no corresponde a la última toma guardada.")
            excluded[slot] = record["related_attempt"]
        elif status not in ("saved", "rejected") or record["related_attempt"] != excluded.get(slot):
            raise ValueError("Estado o vínculo de repetición incorrecto.")
        if (not 1 <= slot <= len(shots) or record["shot_number"] != slot
                or record["shot"] != shots[slot - 1]):
            raise ValueError("El intento no coincide con la pauta de la sesión.")
        attempt_folder = child(attempts_root, attempt_id)
        if status == "saved":
            image_name = f'{session["plan"]["session_id"]}_{expected_id}.png'
            if (record["relative_path"] != image_name or not valid_distance(record["distance_approx_m"])
                    or record["lighting"] != shots[slot - 1]["lighting"]):
                raise ValueError("Imagen o condiciones incoherentes.")
            image = child(attempt_folder, image_name)
            if not image.is_file() or {p.name for p in attempt_folder.iterdir()} != {"record.json", image_name}:
                raise ValueError("El intento guardado debe contener su ficha y su PNG.")
            if verify_images:
                payload = image.read_bytes()
                if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise ValueError("El archivo carece de la firma PNG.")
                if hashlib.sha256(payload).hexdigest() != record["sha256"]:
                    raise ValueError("El SHA-256 de la imagen no coincide.")
                frame = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                if frame is None or frame.shape != FRAME_SHAPE or frame.dtype != np.uint8:
                    raise ValueError("PNG ilegible o con formato incorrecto.")
                hashes.append((record["sha256"], image_name))
            accepted.append(number)
        elif (not record["reason"] or record["relative_path"] is not None
                or record["sha256"] is not None
                or {p.name for p in attempt_folder.iterdir()} != {"record.json"}):
            raise ValueError("Un intento rechazado o excluido requiere un motivo y ficha sin imagen nueva.")
    return len(records), accepted, excluded, hashes


def record_attempt(folder, session, status, *, frame=None, distance=None, reason=None):
    attempts_root = child(folder, "attempts")
    attempts_root.mkdir(exist_ok=True)
    if any(attempts_root.glob(".pending-*")):
        raise ValueError("Hay una escritura interrumpida. Revisar el manifiesto antes de continuar.")
    count, accepted, excluded, _ = replay_attempts(folder, session)
    shots = shots_for(session["plan"])
    number = count + 1
    slot = len(accepted) + 1
    related = excluded.get(slot)
    payload = image_name = None
    if status == "excluded" and accepted:
        slot -= 1
        related = accepted[-1]
    if not 1 <= slot <= len(shots):
        raise ValueError("No queda una toma disponible para este intento.")
    if status == "saved":
        if (not isinstance(frame, np.ndarray) or frame.shape != FRAME_SHAPE
                or frame.dtype != np.uint8 or not valid_distance(distance)):
            raise ValueError("Se requiere BGR 1920×1080 uint8 y una distancia positiva.")
        ok, encoded = cv2.imencode(".png", frame)
        if not ok:
            raise ValueError("No se pudo codificar PNG.")
        payload = encoded.tobytes()
        image_name = f'{session["plan"]["session_id"]}_A{number:06d}.png'
    elif (status not in ("rejected", "excluded") or (status == "excluded" and not accepted)
          or not isinstance(reason, str) or not reason.strip()):
        raise ValueError("Se requiere un intento válido y un motivo para rechazar o excluir.")
    shot = shots[slot - 1]
    record = {
        "attempt": number, "shot_number": slot, "shot": shot, "status": status,
        "at_utc": utc_now(), "reason": reason, "related_attempt": related,
        "lighting": shot["lighting"] if payload is not None else None,
        "distance_approx_m": distance, "relative_path": image_name,
        "sha256": hashlib.sha256(payload).hexdigest() if payload is not None else None,
    }
    publish_directory(child(attempts_root, f"A{number:06d}"), record, payload)
    return record


def audit_dataset(plan, root, session_ids=None):
    issues, summary = [], {}
    by_hash = defaultdict(list)
    for pending in root.rglob(".pending-*"):
        issues.append(f"Escritura interrumpida: {pending.relative_to(root)}")
    selected = plan if session_ids is None else session_ids
    for session_id in selected:
        try:
            expected = plan[session_id]
            folder = child(root, session_id)
            snapshot = read_json(child(folder, "record.json"))
            if snapshot["plan"] != expected:
                raise ValueError("La ficha registrada difiere del plan.")
            count, accepted, _, hashes = replay_attempts(folder, snapshot, verify_images=True)
            for digest, name in hashes:
                by_hash[digest].append((expected["split"], name))
            summary[session_id] = {"attempts": count, "accepted": len(accepted)}
            if len(accepted) != len(shots_for(expected)):
                issues.append(f"{session_id}: sesión incompleta.")
        except (OSError, ValueError, KeyError, TypeError, cv2.error) as exc:
            issues.append(f"{session_id}: {exc}")
    duplicates = [items for items in by_hash.values() if len(items) > 1]
    if any(len({split for split, _ in items}) > 1 for items in duplicates):
        issues.append("Hay PNG idénticos entre particiones.")
    return {"sessions": summary, "issues": issues, "exact_duplicates": duplicates}
