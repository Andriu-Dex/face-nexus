"""Compara el candidato k-NN con inscritos de evaluación y extraños disjuntos."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from scripts.capture_manifest import child, utc_now, write_synced
from scripts.compare_identity_k01 import load_gallery, vote_knn
from scripts.dataset_capture import verify_vault
from scripts.evaluate_hog_knn import K
from scripts.hog_knn import FEATURE_COUNT, PEOPLE
from scripts.identity_four_other import CLASSES, score_open_classes
from scripts.phone_demo_manifest import MANIFEST_PARTS, load_manifest, load_phase_vectors, phone_eval_ready


def per_person_report(true, predicted):
    """Aciertos, confusiones y rechazos por integrante. No usa TEST."""
    true = np.asarray(true)
    predicted = np.asarray(predicted)
    rows = {}
    for person in PEOPLE:
        mask = true == person
        pred = predicted[mask]
        rows[person] = {
            "n": int(mask.sum()),
            "correct": int((pred == person).sum()),
            "confused": int((np.isin(pred, PEOPLE) & (pred != person)).sum()),
            "rejected": int((~np.isin(pred, PEOPLE)).sum()),
        }
    return rows


def identities_disjoint(calibration, evaluation):
    return set(map(str, calibration)).isdisjoint(set(map(str, evaluation)))


def load_identity_ids(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    ids = payload.get("identity_ids")
    if not isinstance(ids, list) or not ids or any(not str(item).strip() for item in ids):
        raise ValueError("El manifiesto de identidades debe listar identity_ids.")
    return [str(item) for item in ids]


def load_bound_identity_ids(path, artifact_path):
    """Lista externa. La huella del archivo no acredita procedencia por fila."""
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    ids = payload.get("identity_ids")
    if not isinstance(ids, list) or not ids or any(not str(item).strip() for item in ids):
        raise ValueError("El manifiesto de identidades debe listar identity_ids.")
    return [str(item) for item in ids], False


def write_trial_calibration(path, vectors, labels, sample_ids, identity_ids, *, gallery_sha256):
    """Guarda el NPZ de calibración en el mismo paso que se usan los vectores."""
    path = Path(path)
    vectors = np.asarray(vectors, np.float32)
    labels = np.asarray(labels, dtype=str)
    sample_ids = np.asarray(sample_ids, dtype=str)
    identity_ids = np.asarray(identity_ids, dtype=str)
    if (vectors.ndim != 2 or vectors.shape[1] != FEATURE_COUNT
            or not (len(vectors) == len(labels) == len(sample_ids) == len(identity_ids))
            or any(not str(item).strip() for item in list(sample_ids) + list(identity_ids))):
        raise ValueError("La calibración requiere vectores HOG e identidades por fila.")
    np.savez(path, vectors=vectors, labels=labels, sample_ids=sample_ids, identity_ids=identity_ids)
    digest = sha256(path.read_bytes()).hexdigest()
    return {
        "calibration_npz_sha256": digest,
        "gallery_sha256": gallery_sha256,
        "calibration_n": int(len(vectors)),
    }


def provenance_from_npz(npz_path, *, trial_summary=None, gallery_sha256=None):
    """Solo verifica si la huella coincide con el ensayo y el NPZ trae vectores."""
    npz_path = Path(npz_path)
    digest = sha256(npz_path.read_bytes()).hexdigest()
    try:
        with np.load(npz_path, allow_pickle=False) as file:
            names = set(file.files)
            if not {"vectors", "labels", "sample_ids", "identity_ids"} <= names:
                return None, False, []
            vectors = np.asarray(file["vectors"], np.float32)
            sample_ids = np.asarray(file["sample_ids"]).astype(str).tolist()
            identities = np.asarray(file["identity_ids"]).astype(str).tolist()
            labels = np.asarray(file["labels"]).astype(str).tolist()
    except (OSError, ValueError, KeyError):
        return None, False, []
    if (vectors.ndim != 2 or vectors.shape[1] != FEATURE_COUNT
            or len(vectors) != len(sample_ids) or len(identities) != len(labels)
            or len(labels) != len(vectors)
            or any(not item.strip() for item in sample_ids + identities)
            or not np.isfinite(vectors).all()):
        return None, False, []
    rows = [
        {"index": index, "sample_id": sample, "identity_id": identity, "label": label}
        for index, (sample, identity, label) in enumerate(zip(sample_ids, identities, labels))
    ]
    ids = [row["identity_id"] for row in rows]
    if (trial_summary is None or gallery_sha256 is None
            or trial_summary.get("calibration_npz_sha256") != digest
            or trial_summary.get("gallery_sha256") != gallery_sha256):
        return ids, False, rows
    return ids, True, rows


def bind_npz_rows(npz_path, manifest_path, *, id_key, expected_label=None):
    """Coteja huella del NPZ, índice, etiqueta y sample_id por fila."""
    npz_path = Path(npz_path)
    payload = json.loads(Path(manifest_path).read_text(encoding="utf-8-sig"))
    digest = sha256(npz_path.read_bytes()).hexdigest()
    if payload.get("file_sha256") != digest:
        raise ValueError("La huella del NPZ no coincide con el manifiesto de filas.")
    vectors, labels = load_gallery(npz_path)
    with np.load(npz_path, allow_pickle=False) as file:
        sample_ids = (
            np.asarray(file["sample_ids"]).astype(str).tolist()
            if "sample_ids" in file.files else None)
    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) != len(vectors):
        raise ValueError("El manifiesto de filas no cubre el NPZ. La cantidad no basta.")
    identities = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or int(row.get("index", -1)) != index:
            raise ValueError("El índice de una fila no coincide con el NPZ.")
        identity = str(row.get(id_key) or "").strip()
        if not identity:
            raise ValueError("Falta el identificador de una fila.")
        label = str(row.get("label") or "").strip()
        npz_label = str(labels[index])
        if expected_label is not None:
            if label != expected_label or npz_label != expected_label:
                raise ValueError("Hay filas que no están etiquetadas como OTHER.")
        elif label and label != npz_label:
            raise ValueError("La etiqueta del manifiesto no coincide con la fila del NPZ.")
        if id_key == "person_id" and identity != npz_label:
            raise ValueError("El person_id de la fila no coincide con la etiqueta del NPZ.")
        declared = str(row.get("sample_id") or "").strip()
        if sample_ids is None or not declared:
            raise ValueError("El NPZ y el manifiesto deben traer sample_ids cotejables.")
        if declared != sample_ids[index]:
            raise ValueError("El sample_id de la fila no coincide con el NPZ.")
        identities.append(identity)
    return vectors, labels, identities


def disjoint_status(calibration_ids, evaluation_ids, *, calibration_bound=False,
                    evaluation_bound=False):
    if (not calibration_bound or not evaluation_bound
            or calibration_ids is None or evaluation_ids is None):
        return {"verified": False, "disjoint": None}
    return {"verified": True, "disjoint": identities_disjoint(calibration_ids, evaluation_ids)}


def predict_gallery(gallery, labels, queries):
    predicted = []
    for vector in queries:
        winner, _ = vote_knn(gallery, labels, vector, k=K)
        predicted.append(winner if winner in CLASSES else "OTHER")
    return np.array(predicted)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--gallery-run", default="identity_four_other_v1")
    parser.add_argument("--report-name", required=True,
                        help="Nombre propio del resultado. No reutiliza demo_domain.json.")
    parser.add_argument("--enrolled-npz", type=Path, default=None)
    parser.add_argument("--enrolled-rows", type=Path, default=None,
                        help="JSON con file_sha256 y filas (index, person_id, sample_id).")
    parser.add_argument("--unknown-npz", type=Path, default=None)
    parser.add_argument("--unknown-rows", type=Path, default=None,
                        help="JSON con file_sha256 y filas (index, identity_id, label=OTHER).")
    parser.add_argument("--calibration-npz", type=Path, default=None,
                        help="NPZ de calibración con sample_ids e identity_ids por fila.")
    parser.add_argument("--calibration-ids", type=Path, default=None,
                        help="Lista externa. No verifica disjunción por sí sola.")
    parser.add_argument("--use-phone-eval", action="store_true",
                        help="Carga inscritos eval del manifiesto privado.")
    args = parser.parse_args()
    if not args.report_name.replace("_", "").isalnum():
        parser.error("report-name inválido.")
    root = verify_vault(args.vault)
    out = child(root, "experiments", "identity_four_other", args.gallery_run,
                f"domain_{args.report_name}.json")
    if out.exists():
        raise FileExistsError("Ese informe de dominio ya existe.")
    manifest = load_manifest(child(root, *MANIFEST_PARTS))
    issues, warnings, phone_ok = phone_eval_ready(manifest, root)
    gallery_path = child(root, "experiments", "identity_four_other", args.gallery_run, "gallery.npz")
    gallery, labels = load_gallery(gallery_path)
    gallery_digest = sha256(gallery_path.read_bytes()).hexdigest()
    summary_path = child(root, "experiments", "identity_four_other", args.gallery_run, "summary.json")
    trial_summary = json.loads(summary_path.read_text(encoding="utf-8-sig")) if summary_path.is_file() else {}
    cal_ids, cal_bound = None, False
    cal_path = args.calibration_npz
    if cal_path is None:
        bundled = child(root, "experiments", "identity_four_other", args.gallery_run, "calibration.npz")
        if bundled.is_file():
            cal_path = bundled
    if cal_path is not None:
        cal_ids, cal_bound, _cal_rows = provenance_from_npz(
            cal_path, trial_summary=trial_summary, gallery_sha256=gallery_digest)
    elif args.calibration_ids is not None:
        cal_ids, cal_bound = load_bound_identity_ids(args.calibration_ids, gallery_path)
    unk_ids, unk_bound = None, False
    if args.unknown_npz is not None:
        if args.unknown_rows is None:
            raise ValueError(
                "Los extraños requieren un manifiesto de filas con huella. El recuento no basta.")
        unknown_x, unknown_y, unk_ids = bind_npz_rows(
            args.unknown_npz, args.unknown_rows, id_key="identity_id", expected_label="OTHER")
        unk_bound = True
    disjoint = disjoint_status(
        cal_ids, unk_ids, calibration_bound=cal_bound, evaluation_bound=unk_bound)
    report = {
        "at_utc": utc_now(),
        "gallery_run": args.gallery_run,
        "report_name": args.report_name,
        "simulation": True,
        "phone_eval_ready": phone_ok,
        "manifest_issues": issues,
        "manifest_warnings": warnings,
        "unknowns_disjoint": disjoint["disjoint"],
        "unknowns_disjoint_verified": disjoint["verified"],
        "calibration_n_ids": None if cal_ids is None else len(cal_ids),
        "unknown_n_ids": None if unk_ids is None else len(unk_ids),
        "calibration_rows_bound": cal_bound,
    }
    if args.use_phone_eval:
        if not phone_ok:
            raise ValueError("La evaluación del celular no está lista.")
        enrolled_x, enrolled_y = load_phase_vectors(root, manifest, "eval")
        pred = predict_gallery(gallery, labels, enrolled_x)
        report["enrolled"] = score_open_classes(enrolled_y, pred)
        report["per_person"] = per_person_report(enrolled_y, pred)
        report["enrolled_source"] = "phone_eval_manifest"
    elif args.enrolled_npz:
        if args.enrolled_rows is None:
            raise ValueError("El NPZ de inscritos requiere manifiesto de filas con huella y sample_id.")
        enrolled_x, enrolled_y, _people = bind_npz_rows(
            args.enrolled_npz, args.enrolled_rows, id_key="person_id")
        pred = predict_gallery(gallery, labels, enrolled_x)
        report["enrolled"] = score_open_classes(enrolled_y, pred)
        report["per_person"] = per_person_report(enrolled_y, pred)
        report["enrolled_source"] = str(args.enrolled_npz)
        report["enrolled_rows_bound"] = True
    if args.unknown_npz:
        if not disjoint["verified"]:
            raise ValueError("Sin manifiestos de identidad no se persiste un FAR de extraños.")
        if disjoint["disjoint"] is not True:
            raise ValueError("Los extraños de evaluación coinciden con los de calibración.")
        pred = predict_gallery(gallery, labels, unknown_x)
        report["unknowns"] = score_open_classes(unknown_y, pred)
        report["unknown_source"] = str(args.unknown_npz)
        report["unknown_rows_bound"] = True
    write_synced(out, json.dumps(report, indent=2, allow_nan=False).encode("utf-8"))
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
