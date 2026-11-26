"""Permiso, autorización y controlador simulado. Falla cerrado. No abre hardware."""

from hashlib import sha256
import json
from pathlib import Path
from time import monotonic
from uuid import uuid4

from scripts.capture_manifest import child, utc_now, write_synced
from scripts.hog_knn import PEOPLE


GRANTED = "GRANTED"
DENIED = "DENIED"
UNKNOWN = "UNKNOWN"
REASONS = (
    "no_face", "multiple_faces", "not_human", "unknown_identity", "permission_inactive",
    "model_unavailable", "exception", "authorized", "unauthorized_present",
)


def default_permissions():
    return {person: True for person in PEOPLE}


def validate_permissions(mapping):
    if (not isinstance(mapping, dict) or set(mapping) != set(PEOPLE)
            or any(type(mapping[person]) is not bool for person in PEOPLE)):
        raise ValueError("Los permisos deben ser un booleano por cada K01 a K04.")
    return {person: mapping[person] for person in PEOPLE}


def load_permissions(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    return validate_permissions(json.loads(text))


def save_permissions(path, mapping):
    payload = json.dumps(validate_permissions(mapping), indent=2).encode("utf-8")
    path = Path(path)
    if path.exists():
        path.write_bytes(payload)
    else:
        write_synced(path, payload)


def decide(*, face_count, candidate, accepted, permission_active, error=None, is_human=True,
           model_ready=True):
    """Una región. Sin rostro confirmado y permitido, la salida es DENIED."""
    if error:
        return {"outcome": DENIED, "reason": "exception", "identity": UNKNOWN}
    if model_ready is not True:
        return {"outcome": DENIED, "reason": "model_unavailable", "identity": UNKNOWN}
    if type(face_count) is not int or face_count < 0:
        return {"outcome": DENIED, "reason": "exception", "identity": UNKNOWN}
    if face_count == 0:
        return {"outcome": DENIED, "reason": "no_face", "identity": UNKNOWN}
    if face_count != 1:
        return {"outcome": DENIED, "reason": "multiple_faces", "identity": UNKNOWN}
    if is_human is not True:
        return {"outcome": DENIED, "reason": "not_human", "identity": UNKNOWN}
    if not accepted or candidate not in PEOPLE:
        return {"outcome": DENIED, "reason": "unknown_identity", "identity": UNKNOWN}
    if permission_active is not True:
        return {"outcome": DENIED, "reason": "permission_inactive", "identity": candidate}
    return {"outcome": GRANTED, "reason": "authorized", "identity": candidate}


def decide_scene(regions):
    """Actúa si al menos una región está autorizada. Si no, deniega."""
    if not regions:
        return {"outcome": DENIED, "reason": "no_face", "identity": UNKNOWN, "event_id": None}
    granted = [row for row in regions if row["outcome"] == GRANTED]
    chosen = granted[0] if granted else regions[0]
    return {**chosen, "event_id": uuid4().hex[:16]}


def require_everyone_authorized(scene):
    """Regla estricta opcional: un rostro no autorizado en la escena deniega aunque haya un integrante."""
    if scene["outcome"] != GRANTED:
        return scene
    if all(row["outcome"] == GRANTED for row in scene.get("regions") or []):
        return scene
    return {**scene, "outcome": DENIED, "reason": "unauthorized_present", "identity": UNKNOWN}


def simulate_authorize(decision):
    """El simulador registra la decisión y no puede mover un pestillo."""
    if decision["outcome"] not in {GRANTED, DENIED} or decision["reason"] not in REASONS:
        raise ValueError("Decisión de acceso inválida.")
    return {
        "state": "SIMULATED",
        "physical_open": False,
        "decision": decision["outcome"],
        "reason": decision["reason"],
        "identity": decision["identity"],
        "event_id": decision.get("event_id"),
        "at_utc": utc_now(),
        "clock": monotonic(),
    }


def permission_hash(mapping):
    canonical = json.dumps(validate_permissions(mapping), sort_keys=True).encode("utf-8")
    return sha256(canonical).hexdigest()


def permissions_path(vault):
    return child(vault, "permissions.json")
