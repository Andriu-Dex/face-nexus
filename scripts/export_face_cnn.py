"""Exporta la CNN facial entrenada a ONNX para usarla con OpenCV en FaceNexus.

Entrada del ONNX: gris 64×64 escalado a [-1, 1], forma (1, 1, 64, 64).
Salida: vector de 128 sin normalizar; FaceNexus lo normaliza antes del k-NN.
"""

import argparse
from pathlib import Path

import torch

from train_face_cnn import FaceNet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, help="best.pt de train_face_cnn.py")
    parser.add_argument("output", type=Path, help="Ruta del .onnx")
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"{args.output} ya existe.")
    model = FaceNet()
    model.load_state_dict(torch.load(args.checkpoint, map_location="cpu", weights_only=True)["model"])
    model.eval()
    example = torch.zeros(1, 1, 64, 64)
    torch.onnx.export(model, (example,), str(args.output), input_names=["face"],
                      output_names=["embedding"], dynamo=False, opset_version=17)
    print(f"Exportado {args.output}")


if __name__ == "__main__":
    main()
