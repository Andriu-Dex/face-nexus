"""Descarga exclusivamente los ONNX revisados, comprobando licencia y hash."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request


REVISION = "48b10fa505aeb51fbd127fc60a5c660040e823b7"
MODELS = {
    "yunet": ("face_detection_yunet", "face_detection_yunet_2023mar.onnx", 232589,
              "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4", "MIT"),
    "sface": ("face_recognition_sface", "face_recognition_sface_2021dec.onnx", 38696353,
              "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79", "Apache 2.0"),
    # Apoyo opcional: objetos y rostros en pantallas. No interviene en la identidad.
    "nanodet": ("object_detection_nanodet", "object_detection_nanodet_2022nov.onnx", 3800954,
                "4b82da9944b88577175ee23a459dce2e26e6e4be573def65b1055dc2d9720186", "Apache 2.0"),
}


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "FaceNexus-model-audit"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main():
    root = Path(__file__).resolve().parents[1] / "models/verified"
    root.mkdir(parents=True, exist_ok=True)
    registry_path = root / "registry.json"
    # Un registro previo se amplía: los modelos ya verificados conservan su evidencia.
    previous = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else {}
    registry = {"repository": "https://github.com/opencv/opencv_zoo", "revision": REVISION,
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "models": previous.get("models", {})}
    for name, (folder, filename, size, digest, license_name) in MODELS.items():
        raw = f"https://raw.githubusercontent.com/opencv/opencv_zoo/{REVISION}/models/{folder}/"
        readme = fetch(raw + "README.md")
        license_text = fetch(raw + "LICENSE")
        pointer = fetch(raw + filename).decode("utf-8")
        if f"oid sha256:{digest}" not in pointer or f"size {size}" not in pointer:
            raise ValueError("La referencia publicada no coincide con el artefacto revisado.")
        if b"All files in this directory are licensed" not in readme:
            raise ValueError("No se confirma el alcance de licencia de la carpeta.")
        marker = b"MIT License" if name == "yunet" else b"Apache License"
        if marker not in license_text:
            raise ValueError("Licencia inesperada.")
        url = f"https://media.githubusercontent.com/media/opencv/opencv_zoo/{REVISION}/models/{folder}/{filename}"
        target = root / filename
        payload = target.read_bytes() if target.exists() else fetch(url)
        if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
            raise ValueError("Tamaño/hash local no coincide. No se incorpora el peso.")
        if not target.exists():
            with target.open("xb") as file:
                file.write(payload)
        for suffix, text in (("LICENSE", license_text), ("README.md", readme)):
            evidence = root / f"{name}_{suffix}"
            if evidence.exists() and evidence.read_bytes() != text:
                raise ValueError("Evidencia previa diferente; no se sobrescribe.")
            if not evidence.exists():
                with evidence.open("xb") as file:
                    file.write(text)
        registry["models"][name] = {"filename": filename, "url": url, "size": size,
                                     "sha256": digest, "license": license_name,
                                     "license_sha256": hashlib.sha256(license_text).hexdigest(),
                                     "published_pointer_verified": True, "local_hash_verified": True}
        print(f"{name}: {size} bytes; hash verificado", flush=True)
    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
