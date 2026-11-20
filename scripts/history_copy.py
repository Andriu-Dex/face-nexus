"""Copia y verifica archivos históricos de FaceNexus en el volumen cifrado."""

import argparse
from hashlib import file_digest
import json
import os
from pathlib import Path
import shutil
import stat

from scripts.capture_manifest import child, read_json, write_synced
from scripts.dataset_capture import PROJECT, verify_vault


SOURCES = {
    "external": Path(r"C:\Downloads\FaceNexus\data"),
    "pilot": PROJECT / "data" / "raw" / "pilot",
    "private": PROJECT / "private",
}


def file_mode(path):
    entry = path.lstat()
    attributes = getattr(entry, "st_file_attributes", 0)
    if stat.S_ISLNK(entry.st_mode) or attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        raise ValueError("Se detectó un enlace o una ruta redirigida.")
    return entry.st_mode


def inventory(root):
    if root.resolve(strict=True) != root or not stat.S_ISDIR(file_mode(root)):
        raise ValueError("El inventario requiere una carpeta local sin redirecciones.")
    files = {}
    pending = [root]
    while pending:
        for entry in pending.pop().iterdir():
            mode = file_mode(entry)
            if stat.S_ISDIR(mode):
                pending.append(entry)
            elif stat.S_ISREG(mode):
                with entry.open("rb") as handle:
                    digest = file_digest(handle, "sha256").hexdigest()
                    size = os.fstat(handle.fileno()).st_size
                files[entry.relative_to(root).as_posix()] = {"bytes": size, "sha256": digest}
            else:
                raise ValueError("Se detectó una entrada distinta de una carpeta o archivo.")
    return files


def verify_history(history, sources):
    recorded = read_json(child(history, "source_inventory.json"))
    if not isinstance(recorded, dict) or recorded.keys() != sources.keys():
        raise ValueError("Las categorías del inventario no coinciden con los orígenes.")
    counts = {}
    for label, source in sources.items():
        expected = recorded[label]
        if inventory(source) != expected:
            raise ValueError(f"El origen {label} difiere del inventario inicial.")
        if inventory(child(history, label)) != expected:
            raise ValueError(f"El destino {label} difiere del inventario inicial.")
        counts[label] = len(expected)
    return counts


def copy_history(history, sources):
    if history.exists():
        raise FileExistsError("Ya existe history; se conserva para revisión o verificación.")
    recorded = {label: inventory(root) for label, root in sources.items()}
    history.mkdir(exist_ok=False)
    encoded = json.dumps(recorded, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    write_synced(child(history, "source_inventory.json"), encoded)
    for label, source in sources.items():
        target = child(history, label)
        target.mkdir()
        for relative in recorded[label]:
            original = child(source, relative)
            destination = child(target, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with original.open("rb") as incoming, destination.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)
            modified = original.stat().st_mtime_ns
            os.utime(destination, ns=(modified, modified))
    return verify_history(history, sources)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("action", choices=("copy", "verify"))
    args = parser.parse_args()
    try:
        vault = verify_vault(args.vault)
        history = child(vault, "history")
        operation = copy_history if args.action == "copy" else verify_history
        counts = operation(history, SOURCES)
    except (OSError, ValueError, TypeError) as error:
        print(f"Verificación detenida: {error}")
        return 1
    print("SHA-256, rutas relativas y tamaños coinciden en origen y destino.")
    for category, count in counts.items():
        print(f"{category}: {count:,} archivos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
