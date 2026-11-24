"""Mide el costo de entrenar una CNN facial con lotes simulados."""

import argparse
from time import perf_counter

import torch
from torch import nn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--steps", type=int, default=60)
    parser.add_argument("--identities", type=int, default=50_000)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()
    if min(args.batch, args.steps) < 1 or args.identities < 2:
        parser.error("Se requieren un lote y pasos positivos y al menos dos identidades.")
    if args.device == "cuda" and not torch.cuda.is_available():
        parser.error("PyTorch no tiene acceso a CUDA en este equipo.")

    device = torch.device(args.device)
    using_cuda = device.type == "cuda"
    torch.manual_seed(2026)
    # El vector de 128 atributos precede a la capa de clasificación.
    model = nn.Sequential(
        nn.Conv2d(3, 32, 3, stride=2, padding=1),
        nn.BatchNorm2d(32),
        nn.ReLU(),
        nn.Conv2d(32, 64, 3, stride=2, padding=1),
        nn.BatchNorm2d(64),
        nn.ReLU(),
        nn.Conv2d(64, 128, 3, stride=2, padding=1),
        nn.BatchNorm2d(128),
        nn.ReLU(),
        nn.AdaptiveAvgPool2d((4, 4)),
        nn.Flatten(),
        nn.Linear(128 * 4 * 4, 128),
        nn.Linear(128, args.identities),
    ).to(device)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01, momentum=0.9)
    loss_function = nn.CrossEntropyLoss()
    scaler = torch.amp.GradScaler(device.type, enabled=using_cuda)
    images = torch.rand(args.batch, 3, 112, 112, device=device)
    labels = torch.randint(args.identities, (args.batch,), device=device)

    # El calentamiento queda fuera de la medición. Los lotes ya están en memoria.
    warmup_steps = 5
    for step in range(warmup_steps + args.steps):
        if step == warmup_steps:
            if using_cuda:
                torch.cuda.synchronize()
                torch.cuda.reset_peak_memory_stats()
            start = perf_counter()
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type=device.type, enabled=using_cuda):
            loss = loss_function(model(images), labels)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()

    if using_cuda:
        torch.cuda.synchronize()
    elapsed = perf_counter() - start
    if not torch.isfinite(loss).item():
        raise RuntimeError("La pérdida del lote simulado no es finita.")
    rate = args.steps * args.batch / elapsed
    print(f"PyTorch {torch.__version__} | lote {args.batch} | clases {args.identities}")
    if using_cuda:
        print(f"GPU {torch.cuda.get_device_name()} | VRAM pico PyTorch "
              f"{torch.cuda.max_memory_allocated() / 1024**2:.0f} MiB")
    print(f"{rate:.0f} imágenes/s | {2_000_000 / rate / 60:.1f} min por 2M en memoria")


if __name__ == "__main__":
    main()
