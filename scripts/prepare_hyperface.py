"""Prepara rostros de HyperFace con el mismo recorte y preprocesamiento del vivo.

Lee el .tar.gz en streaming (las identidades vienen en carpetas consecutivas),
detecta con YuNet, recorta la caja y aplica face_grey: gris 64×64 ecualizado.
Guarda faces.npy (uint8, N×64×64), labels.npy (int32) y meta.json.
Las imágenes sin una única cara se descartan, igual que en vivo.
"""

import argparse
import json
import os
import tarfile
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np

from scripts.face_pipeline import load_detector
from scripts.hog_knn import FACE_SIZE, detect_boxes, face_grey

IMAGES_PER_IDENTITY = 64
# Las imágenes vienen recortadas muy justo; un borde negro ayuda a YuNet (86 % frente a 84 %).
PAD = 28
DEFAULT_ARCHIVE = Path(os.path.expandvars(
    r"%LOCALAPPDATA%\FaceNexus\datasets\HyperFace\HyperFace_50k_StyleGAN.tar.gz"))


def prepare_image(payload, detector):
    """PNG → gris 64×64 o None si no hay exactamente una cara."""
    image = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return None
    padded = cv2.copyMakeBorder(image, PAD, PAD, PAD, PAD, cv2.BORDER_CONSTANT)
    boxes = detect_boxes(padded, detector)
    if len(boxes) != 1:
        return None
    left, top, right, bottom, _score = boxes[0]
    return face_grey(padded[top:bottom, left:right])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--out", type=Path, default=DEFAULT_ARCHIVE.parent / "prepared_g64")
    parser.add_argument("--identities", type=int, default=20_500)
    parser.add_argument("--models", type=Path, default=Path("models/verified"))
    args = parser.parse_args()
    if args.identities < 2:
        parser.error("Se requieren al menos dos identidades.")
    if not args.archive.is_file():
        parser.error(f"No existe el archivo {args.archive}.")
    args.out.mkdir(parents=True, exist_ok=True)
    if (args.out / "meta.json").exists():
        parser.error(f"{args.out} ya contiene una preparación; usa otra carpeta.")

    detector = load_detector(args.models)
    capacity = args.identities * IMAGES_PER_IDENTITY
    faces = np.lib.format.open_memmap(
        args.out / "faces_partial.npy", mode="w+", dtype=np.uint8, shape=(capacity, *FACE_SIZE))
    labels = np.empty(capacity, dtype=np.int32)
    folders = []
    count = seen = 0
    start = perf_counter()
    with tarfile.open(args.archive, "r|gz") as archive:
        for member in archive:
            if not member.isfile() or not member.name.endswith(".png"):
                continue
            folder = member.name.rsplit("/", 2)[-2]
            if not folders or folders[-1] != folder:
                if len(folders) == args.identities:
                    break
                folders.append(folder)
            seen += 1
            grey = prepare_image(archive.extractfile(member).read(), detector)
            if grey is not None:
                faces[count] = grey
                labels[count] = len(folders) - 1
                count += 1
            if seen % 50_000 == 0:
                print(f"{seen} leídas · {count} útiles · {len(folders)} identidades · "
                      f"{perf_counter() - start:.0f} s", flush=True)

    faces.flush()
    del faces
    # Recorta el arreglo a las filas útiles sin cargarlo entero en memoria.
    partial = np.load(args.out / "faces_partial.npy", mmap_mode="r")
    final = np.lib.format.open_memmap(
        args.out / "faces.npy", mode="w+", dtype=np.uint8, shape=(count, *FACE_SIZE))
    for begin in range(0, count, 100_000):
        end = min(count, begin + 100_000)
        final[begin:end] = partial[begin:end]
    final.flush()
    del final, partial
    (args.out / "faces_partial.npy").unlink()
    np.save(args.out / "labels.npy", labels[:count])
    meta = {
        "source": args.archive.name,
        "identities": len(folders),
        "first_folder": folders[0],
        "last_folder": folders[-1],
        "images_read": seen,
        "images_kept": count,
        "pad_px": PAD,
        "preprocessing": "YuNet box -> gris 64x64 -> equalizeHist (face_grey)",
        "seconds": round(perf_counter() - start, 1),
    }
    (args.out / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(meta, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
