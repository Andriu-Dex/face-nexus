"""Manifiesto privado de lotes del celular. Ajuste y evaluación son encuentros distintos."""

from collections import Counter
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path

import numpy as np

from scripts.capture_manifest import child, utc_now, write_synced
from scripts.hog_knn import FEATURE_COUNT, PEOPLE


ROLES = ("tune", "eval")
ROLE_SPLIT = {"tune": "TRAIN", "eval": "VALIDATION"}
MANIFEST_PARTS = ("experiments", "phone_demo", "manifest.json")
LOT_PARTS = ("experiments", "hog_phone_adapt")


def empty_manifest():
    return {"at_utc": utc_now(), "source": "phone_mjpeg", "revision": 0, "sessions": []}


def derived_encounter_name(person, role, run_name):
    """Nombre automático. No acredita un encuentro real."""
    return f"{person}-{role}-{run_name}"


def require_explicit_encounter(encounter_id, person, role, run_name):
    if not isinstance(encounter_id, str) or not encounter_id.strip():
        raise ValueError("Falta el identificador de encuentro.")
    text = encounter_id.strip()
    if text in {derived_encounter_name(person, role, run_name), f"{person}-{role}"}:
        raise ValueError(
            "El identificador de encuentro no puede derivarse del papel y el nombre de ejecución.")
    return text


def session_record(person, run_name, role, rotation, hashes, *, sampled, usable,
                   encounter_id, at=None):
    if person not in PEOPLE or role not in ROLES:
        raise ValueError("Identidad o papel de encuentro inválido.")
    if not hashes or len(hashes) != len(set(hashes)):
        raise ValueError("La ráfaga debe tener huellas SHA-256 únicas.")
    encounter_id = require_explicit_encounter(encounter_id, person, role, run_name)
    return {
        "person_id": person,
        "run_name": run_name,
        "role": role,
        "split": ROLE_SPLIT[role],
        "encounter_id": encounter_id.strip(),
        "rotation": int(rotation),
        "at_utc": at or utc_now(),
        "sampled_frames": int(sampled),
        "usable_frames": int(usable),
        "image_sha256": list(hashes),
    }


def check_phone_manifest(manifest):
    """Errores: ráfaga mezclada, duplicada o encuentros cruzados. Avisos: falta una clase."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get("sessions"), list):
        raise ValueError("Manifiesto de celular inválido.")
    issues, warnings = [], []
    by_role = {role: [] for role in ROLES}
    seen = {}
    encounters = {role: set() for role in ROLES}
    for row in manifest["sessions"]:
        if row.get("role") not in ROLES or row.get("split") != ROLE_SPLIT[row["role"]]:
            issues.append("Una sesión mezcla o contradice la partición de su encuentro.")
            continue
        if row.get("person_id") not in PEOPLE:
            issues.append("Hay una identidad que no es K01–K04.")
            continue
        encounter_id = row.get("encounter_id")
        if not isinstance(encounter_id, str) or not encounter_id.strip():
            issues.append("Falta el identificador de encuentro.")
        else:
            encounters[row["role"]].add(encounter_id)
        hashes = row.get("image_sha256") or []
        if len(hashes) != len(set(hashes)):
            issues.append(f"Ráfaga repetida dentro de {row.get('run_name')}.")
        split = row["split"]
        for digest in hashes:
            previous = seen.get(digest)
            if previous == split:
                issues.append("Hay una huella repetida en la misma partición.")
            elif previous is not None:
                issues.append("Hay imágenes idénticas entre ajuste y evaluación.")
            seen[digest] = split
        by_role[row["role"]].append(row["person_id"])
    if encounters["tune"] & encounters["eval"]:
        issues.append("Ajuste y evaluación comparten identificador de encuentro.")
    for role, people in by_role.items():
        present = set(people)
        if not present:
            warnings.append(f"Aún no hay encuentro de {role} para ninguna identidad.")
        elif present != set(PEOPLE):
            missing = " ".join(person for person in PEOPLE if person not in present)
            warnings.append(f"El encuentro {role} pierde una clase: {missing}.")
        counts = Counter(people)
        repeated = [person for person, n in counts.items() if n > 1]
        if repeated:
            warnings.append(f"Hay más de una ráfaga de {role} para {', '.join(repeated)}.")
    return issues, warnings


def require_phone_manifest(manifest):
    issues, warnings = check_phone_manifest(manifest)
    if issues:
        raise ValueError(" ".join(issues))
    return warnings


def listed_session(manifest, person, run_name):
    rows = [row for row in manifest.get("sessions", [])
            if row.get("person_id") == person and row.get("run_name") == run_name]
    if len(rows) != 1:
        return None
    return rows[0]


def listed_run(manifest, person, run_name):
    return listed_session(manifest, person, run_name) is not None


def verify_lot_matches_row(folder, row):
    """Coteja ficha, encuentro, fase, huellas y filas HOG con una fila del manifiesto."""
    folder = Path(folder)
    records_path = folder / "records.json"
    hog_path = folder / "hog.npz"
    if not records_path.is_file() or not hog_path.is_file():
        raise ValueError("Falta la ficha o el HOG del lote.")
    records = json.loads(records_path.read_text(encoding="utf-8-sig"))
    if (records.get("person_id") != row.get("person_id")
            or records.get("role") != row.get("role")
            or records.get("split") != row.get("split")
            or records.get("encounter_id") != row.get("encounter_id")):
        raise ValueError("La ficha no coincide con identidad, fase o encuentro del manifiesto.")
    file_hashes = []
    usable_ids = []
    for item in records.get("records", []):
        png = folder / "frames" / f"{item['sample_id']}.png"
        digest = sha256(png.read_bytes()).hexdigest() if png.is_file() else None
        if digest != item.get("image_sha256"):
            raise ValueError("La huella de un fotograma no coincide con el registro.")
        file_hashes.append(digest)
        if item.get("reason") == "usable":
            usable_ids.append(item["sample_id"])
    if file_hashes != list(row.get("image_sha256") or []):
        raise ValueError("Las huellas del lote no coinciden con el manifiesto.")
    with np.load(hog_path, allow_pickle=False) as hog:
        hog_x = np.asarray(hog["vectors"], np.float32)
        hog_y = np.asarray(hog["labels"]).astype(str)
        if "sample_ids" not in hog.files:
            raise ValueError("El NPZ no trae sample_ids.")
        hog_ids = np.asarray(hog["sample_ids"]).astype(str).tolist()
    if hog_x.ndim != 2 or hog_x.shape[1] != FEATURE_COUNT or len(hog_y) != len(hog_x):
        raise ValueError("HOG del lote inválido.")
    if len(hog_x) < 1 or set(hog_y) != {row["person_id"]}:
        raise ValueError("Hay etiquetas ajenas o ningún recorte usable.")
    if hog_ids != usable_ids or len(hog_ids) != len(hog_x):
        raise ValueError("Los sample_ids del NPZ no coinciden con los recortes usables.")
    return hog_x, hog_y


def load_phase_vectors(vault, manifest, role):
    """Carga HOG de lotes registrados, coteja huellas, etiquetas y sample_ids."""
    if role not in ROLES:
        raise ValueError("Fase desconocida.")
    issues, _warnings = check_phone_manifest(manifest)
    if issues:
        raise ValueError(" ".join(issues))
    vectors, labels = [], []
    for row in manifest["sessions"]:
        if row["role"] != role:
            continue
        folder = child(vault, *LOT_PARTS, row["person_id"], row["run_name"])
        hog_x, hog_y = verify_lot_matches_row(folder, row)
        vectors.append(hog_x)
        labels.append(hog_y)
    if not vectors:
        raise ValueError("No hay vectores usables en esa fase.")
    return np.concatenate(vectors), np.concatenate(labels)


def phone_phase_ready(manifest, role, vault=None):
    """Verdadero si hay recortes usables de K01–K04 en esa fase."""
    if role not in ROLES:
        raise ValueError("Fase desconocida.")
    issues, warnings = check_phone_manifest(manifest)
    rows = [row for row in manifest.get("sessions", []) if row.get("role") == role]
    people = {row.get("person_id") for row in rows}
    usable = all(int(row.get("usable_frames") or 0) >= 1 for row in rows) if rows else False
    ready = not issues and people == set(PEOPLE) and usable
    if ready and vault is not None:
        try:
            labels = load_phase_vectors(vault, manifest, role)[1]
            if set(map(str, labels)) != set(PEOPLE):
                ready = False
                issues = list(issues) + [f"Los vectores de {role} no cubren las cuatro clases."]
        except ValueError as error:
            ready = False
            issues = list(issues) + [str(error)]
    return issues, warnings, ready


def phone_eval_ready(manifest, vault=None):
    """Verdadero solo con manifiesto válido y recortes usables de K01–K04 en eval."""
    return phone_phase_ready(manifest, "eval", vault)


def phone_tune_ready(manifest, vault=None):
    """Verdadero solo con manifiesto válido y recortes usables de K01–K04 en tune."""
    return phone_phase_ready(manifest, "tune", vault)


def phase_file_hashes(vault, manifest, role):
    rows = []
    for row in manifest.get("sessions", []):
        if row.get("role") != role:
            continue
        hog = child(vault, *LOT_PARTS, row["person_id"], row["run_name"]) / "hog.npz"
        rows.append({
            "person_id": row["person_id"],
            "run_name": row["run_name"],
            "hog_sha256": sha256(hog.read_bytes()).hexdigest() if hog.is_file() else None,
        })
    return rows


def recover_unpublished_lot(vault, person, run_name):
    """Publica un pendiente verificado. No borra una carpeta final existente."""
    dest = child(vault, *LOT_PARTS, person, run_name)
    pending = dest.parent / f".pending-{run_name}"
    row = listed_session(load_manifest(child(vault, *MANIFEST_PARTS)), person, run_name)
    listed = row is not None
    if dest.exists():
        if not listed:
            raise FileExistsError(
                f"Hay un lote en {person}/{run_name} que no está en el manifiesto; no se borra.")
        if pending.exists():
            raise FileExistsError(
                f"El destino {person}/{run_name} ya existe; el pendiente no lo sustituye.")
        return "unchanged"
    if pending.exists() and listed:
        try:
            verify_lot_matches_row(pending, row)
        except FileExistsError:
            raise
        except Exception as error:
            raise ValueError(
                f"El pendiente de {person}/{run_name} no acredita procedencia; "
                "se conserva para revisión.") from error
        pending.rename(dest)
        return "published_pending"
    if pending.exists() and not listed:
        raise FileExistsError(
            f"Hay un pendiente de {person}/{run_name}; no se borra.")
    return "unchanged"


def reserve_lot_directory(vault, person, run_name):
    """Crea el staging de (person_id, run_name) sin borrar un pendiente ajeno."""
    dest = child(vault, *LOT_PARTS, person, run_name)
    pending = dest.parent / f".pending-{run_name}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    listed = listed_run(load_manifest(child(vault, *MANIFEST_PARTS)), person, run_name)
    if dest.exists() or listed:
        raise FileExistsError(
            f"La clave {person}/{run_name} ya está reservada; no se modifica el lote existente.")
    try:
        pending.mkdir()
    except FileExistsError as error:
        raise FileExistsError(
            f"La clave {person}/{run_name} ya tiene un pendiente; no se modifica.") from error
    return dest, pending


def synthetic_manifest(*, missing=None, duplicate_across=False, zero_usable=False,
                       shared_encounter=False):
    """Manifiesto de prueba. No usa fotos reales."""
    missing = set(missing or ())
    sessions = []
    digest = 0
    shared = "ab" * 32
    for role in ROLES:
        for person in PEOPLE:
            if person in missing and role == "eval":
                continue
            hashes = [f"{digest:064x}"]
            digest += 1
            if duplicate_across and role in ROLES and person == "K01":
                hashes = [shared]
            encounter_id = "enc-same-session" if shared_encounter else f"enc-{role}-aula"
            usable = 0 if zero_usable and role == "eval" else 1
            sessions.append(session_record(
                person, f"{person.lower()}_{role}_v1", role, 0, hashes,
                sampled=1, usable=usable, encounter_id=encounter_id,
                at="2026-11-22T00:00:00+00:00"))
    return {"at_utc": "2026-11-22T00:00:00+00:00", "source": "phone_mjpeg", "sessions": sessions}


def load_manifest(path):
    path = Path(path)
    if not path.is_file():
        return empty_manifest()
    return json.loads(path.read_text(encoding="utf-8-sig"))


@contextmanager
def manifest_lock(path):
    """Candado exclusivo mientras se lee, valida y escribe el índice."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.parent / ".manifest.lock"
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise RuntimeError("Otro proceso está actualizando el índice del celular.") from error
    try:
        yield
    finally:
        os.close(handle)
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def write_manifest_unlocked(path, manifest):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, indent=2, allow_nan=False).encode("utf-8")
    staging = path.parent / f".pending-{path.name}"
    if staging.exists():
        staging.unlink()
    write_synced(staging, payload)
    staging.replace(path)


def append_registered_session(path, row):
    """Carga, valida y escribe el índice bajo el mismo candado."""
    path = Path(path)
    with manifest_lock(path):
        manifest = load_manifest(path)
        manifest.setdefault("sessions", [])
        manifest["sessions"] = list(manifest["sessions"])
        manifest["sessions"].append(row)
        warnings = require_phone_manifest(manifest)
        manifest["warnings"] = warnings
        manifest["revision"] = int(manifest.get("revision") or 0) + 1
        write_manifest_unlocked(path, manifest)
        return warnings


def save_manifest(path, manifest, *, expected_revision=None):
    """Lee bajo candado si hay que comprobar la revisión y reemplaza el índice."""
    path = Path(path)
    with manifest_lock(path):
        if expected_revision is not None:
            disk_rev = int(load_manifest(path).get("revision") or 0)
            if disk_rev != expected_revision:
                raise ValueError("El índice cambió; se rechaza una revisión desactualizada.")
        write_manifest_unlocked(path, manifest)
