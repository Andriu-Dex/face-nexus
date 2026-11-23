"""Compara YuNet solo frente a CNN antes de identificar. No cambia el vivo por defecto."""

import argparse
import json
from pathlib import Path

import numpy as np

from scripts.access import default_permissions
from scripts.adapt_human_cnn import collect_phone
from scripts.capture_manifest import child, utc_now, write_synced
from scripts.dataset_capture import verify_vault
from scripts.live_k01 import HUMAN_RUN, load_keras, recognize_crop


def veto_counts(without_cnn, with_cnn):
    """Casos que la CNN cierra y los que deja pasar siendo no humano."""
    if len(without_cnn) != len(with_cnn):
        raise ValueError("Las dos pasadas deben tener el mismo número de recortes.")
    false_veto = 0
    blocked = 0
    leaked_negative = 0
    for plain, vetoed, in zip(without_cnn, with_cnn):
        if vetoed["reason"] == "not_human":
            blocked += 1
            if plain["outcome"] == "GRANTED" and vetoed.get("true_human") is True:
                false_veto += 1
        if plain.get("true_human") is False and vetoed["reason"] != "not_human":
            leaked_negative += 1
    return {
        "n": len(without_cnn),
        "blocked_by_cnn": blocked,
        "false_veto_of_granted": false_veto,
        "leaked_nonhuman": leaked_negative,
    }


def classify_crops(crops, identify, human_model, permissions, *, trust_detector, true_human):
    rows = []
    for crop in crops:
        row = recognize_crop(crop, human_model, identify, permissions,
                             trust_detector=trust_detector)
        row["true_human"] = true_human
        rows.append(row)
    return rows


def bgr_from_rgb_unit(batch):
    import cv2
    frames = []
    for image in batch:
        array = np.clip(image * 255., 0, 255).astype(np.uint8) if image.max() <= 1.5 else image
        frames.append(cv2.cvtColor(array, cv2.COLOR_RGB2BGR))
    return frames


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    args = parser.parse_args()
    root = verify_vault(args.vault)
    phone = collect_phone(root, args.models)
    human_model = load_keras(root / "experiments" / "human_cnn" / HUMAN_RUN / "model.keras")

    def identify(_vector):
        return "K01", True, "forced"

    permissions = default_permissions()
    faces = bgr_from_rgb_unit(np.concatenate([phone["human"]["train"], phone["human"]["validation"]]))
    objects = bgr_from_rgb_unit(np.concatenate([
        phone["nonhuman"]["train"], phone["nonhuman"]["validation"]]))
    faces_plain = classify_crops(faces, identify, human_model, permissions,
                                 trust_detector=True, true_human=True)
    faces_veto = classify_crops(faces, identify, human_model, permissions,
                                trust_detector=False, true_human=True)
    objects_plain = classify_crops(objects, identify, human_model, permissions,
                                   trust_detector=True, true_human=False)
    objects_veto = classify_crops(objects, identify, human_model, permissions,
                                  trust_detector=False, true_human=False)
    summary = {
        "at_utc": utc_now(),
        "run": HUMAN_RUN,
        "not_liveness": True,
        "diagnostic_mixed_adaptation_split": True,
        "live_default_trusts_yunet": True,
        "faces": veto_counts(faces_plain, faces_veto),
        "nonhuman_patches": veto_counts(objects_plain, objects_veto),
        "note": "Diagnostic only: adaptation train+val of k01_phone_v3, forced K01. Veto stays off.",
    }
    folder = child(root, "experiments", "human_cnn", HUMAN_RUN)
    out = folder / "veto_trial.json"
    if out.exists():
        raise FileExistsError("Ese ensayo de veto ya existe.")
    write_synced(out, json.dumps(summary, indent=2, allow_nan=False).encode("utf-8"))
    print(json.dumps(summary, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
