"""Entrena desde cero una CNN que convierte un rostro gris 64×64 en un vector de 128.

Datos: salida de prepare_hyperface.py (mismo recorte y ecualización que el vivo).
Entrenamiento: clasificar las identidades de TRAIN con pérdida CosFace.
  cos θ_j = <e/‖e‖, w_j/‖w_j‖>;  logit_j = s·(cos θ_j − m·[j = clase correcta])
  Restar el margen m obliga a que la clase correcta gane con holgura, así los
  vectores de una misma persona quedan juntos y los de personas distintas lejos.
Validación: las últimas identidades preparadas NO se entrenan. Se comparan pares
de la misma identidad y de identidades distintas con coseno y se reporta la tasa
de aceptación correcta (TAR) cuando la de aceptación falsa (FAR) es 1 % y 0,1 %.
"""

import argparse
import json
import math
from pathlib import Path
from time import perf_counter

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

EMBEDDING = 128


def conv_block(cin, cout):
    """Dos convoluciones 3×3 con normalización y ReLU; luego reduce a la mitad."""
    return nn.Sequential(
        nn.Conv2d(cin, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
        nn.Conv2d(cout, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
        nn.MaxPool2d(2),
    )


class FaceNet(nn.Module):
    """64×64 → 32 → 16 → 8 → 4 píxeles; 256 mapas de 4×4 → vector de 128."""

    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            conv_block(1, 32), conv_block(32, 64), conv_block(64, 128), conv_block(128, 256))
        self.embed = nn.Sequential(
            nn.Flatten(), nn.Dropout(0.2), nn.Linear(256 * 4 * 4, EMBEDDING), nn.BatchNorm1d(EMBEDDING))

    def forward(self, x):
        return self.embed(self.features(x))


class CosFaceHead(nn.Module):
    def __init__(self, classes, scale=30.0, margin=0.35):
        super().__init__()
        self.weight = nn.Parameter(torch.randn(classes, EMBEDDING) * 0.01)
        self.scale, self.margin = scale, margin

    def forward(self, embedding, labels):
        cosine = F.linear(F.normalize(embedding.float()), F.normalize(self.weight))
        margin = F.one_hot(labels, cosine.shape[1]).float() * self.margin
        return self.scale * (cosine - margin), cosine


def to_input(batch_uint8, device):
    """uint8 [0, 255] → float [-1, 1] con canal único."""
    return batch_uint8.to(device, non_blocking=True).unsqueeze(1).float().div_(127.5).sub_(1)


def augment(x):
    """Espejo horizontal, desplazamiento de hasta 4 px y cambio leve de brillo/contraste."""
    flip = torch.rand(x.shape[0], device=x.device) < 0.5
    x = torch.where(flip[:, None, None, None], x.flip(3), x)
    dy, dx = np.random.randint(-4, 5, size=2)
    x = torch.roll(x, shifts=(int(dy), int(dx)), dims=(2, 3))
    gain = 1 + 0.2 * (torch.rand(x.shape[0], 1, 1, 1, device=x.device) - 0.5)
    bias = 0.2 * (torch.rand(x.shape[0], 1, 1, 1, device=x.device) - 0.5)
    return (x * gain + bias).clamp_(-1, 1)


@torch.no_grad()
def embed_all(model, faces, device, batch=1024):
    model.eval()
    out = []
    for begin in range(0, len(faces), batch):
        x = to_input(faces[begin:begin + batch], device)
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
            out.append(F.normalize(model(x).float()))
    return torch.cat(out)


def verification_pairs(labels, pairs, seed=2026):
    """Índices fijos de pares genuinos (misma identidad) e impostores (distinta)."""
    rng = np.random.default_rng(seed)
    by_id = {}
    for index, label in enumerate(labels):
        by_id.setdefault(int(label), []).append(index)
    ids = [i for i, rows in by_id.items() if len(rows) >= 2]
    genuine = []
    for _ in range(pairs):
        rows = by_id[ids[rng.integers(len(ids))]]
        a, b = rng.choice(len(rows), 2, replace=False)
        genuine.append((rows[a], rows[b]))
    impostor = []
    while len(impostor) < pairs:
        a, b = rng.integers(len(labels), size=2)
        if labels[a] != labels[b]:
            impostor.append((a, b))
    return np.array(genuine), np.array(impostor)


def tar_at_far(genuine_scores, impostor_scores, far):
    """Umbral que deja pasar a lo sumo `far` de impostores y TAR con ese umbral."""
    threshold = torch.quantile(impostor_scores.float(), 1 - far).item()
    return float((genuine_scores > threshold).float().mean()), threshold


def evaluate(model, val_faces, genuine, impostor, device):
    emb = embed_all(model, val_faces, device)
    g = (emb[genuine[:, 0]] * emb[genuine[:, 1]]).sum(1)
    i = (emb[impostor[:, 0]] * emb[impostor[:, 1]]).sum(1)
    tar1, thr1 = tar_at_far(g, i, 0.01)
    tar01, thr01 = tar_at_far(g, i, 0.001)
    return {"tar_far1": tar1, "thr_far1": thr1, "tar_far01": tar01, "thr_far01": thr01,
            "genuine_mean": float(g.mean()), "impostor_mean": float(i.mean())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="Carpeta de prepare_hyperface.py")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--identities", type=int, default=5000, help="Identidades de TRAIN (las primeras)")
    parser.add_argument("--val-identities", type=int, default=500, help="Últimas identidades, nunca entrenadas")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch", type=int, default=256)
    parser.add_argument("--lr", type=float, default=2e-3)
    parser.add_argument("--val-pairs", type=int, default=100_000)
    parser.add_argument("--max-train-steps", type=int, default=0, help="Solo para pruebas rápidas")
    args = parser.parse_args()
    if not torch.cuda.is_available():
        parser.error("PyTorch no ve la GPU; el entrenamiento en CPU sería demasiado lento.")
    args.out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda")
    torch.manual_seed(2026)
    np.random.seed(2026)

    faces = np.load(args.data / "faces.npy", mmap_mode="r")
    labels = np.load(args.data / "labels.npy")
    total = int(labels.max()) + 1
    first_val = total - args.val_identities
    if args.identities > first_val:
        parser.error(f"TRAIN ({args.identities}) se solaparía con VALIDATION (desde {first_val}).")
    train_rows = np.flatnonzero(labels < args.identities)
    val_rows = np.flatnonzero(labels >= first_val)
    print(f"TRAIN {len(train_rows)} imágenes de {args.identities} identidades · "
          f"VALIDATION {len(val_rows)} de {args.val_identities} identidades no entrenadas", flush=True)
    train_faces = torch.from_numpy(np.ascontiguousarray(faces[train_rows]))
    train_labels = torch.from_numpy(labels[train_rows].astype(np.int64))
    val_faces = torch.from_numpy(np.ascontiguousarray(faces[val_rows]))
    genuine, impostor = verification_pairs(labels[val_rows], args.val_pairs)

    model = FaceNet().to(device)
    head = CosFaceHead(args.identities).to(device)
    params = list(model.parameters()) + list(head.parameters())
    optimizer = torch.optim.AdamW(params, lr=args.lr, weight_decay=5e-4)
    steps_per_epoch = len(train_rows) // args.batch
    if args.max_train_steps:
        steps_per_epoch = min(steps_per_epoch, args.max_train_steps)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer, max_lr=args.lr, total_steps=args.epochs * steps_per_epoch, pct_start=0.1)

    config = vars(args) | {"data": str(args.data), "out": str(args.out),
                           "train_images": len(train_rows), "val_images": len(val_rows)}
    (args.out / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    log = (args.out / "log.jsonl").open("a", encoding="utf-8")
    best = -1.0
    for epoch in range(1, args.epochs + 1):
        model.train()
        head.train()
        order = torch.randperm(len(train_rows))
        start = perf_counter()
        loss_sum = correct = seen = 0
        for step in range(steps_per_epoch):
            index = order[step * args.batch:(step + 1) * args.batch]
            x = augment(to_input(train_faces[index], device))
            y = train_labels[index].to(device, non_blocking=True)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                embedding = model(x)
            logits, cosine = head(embedding, y)
            loss = F.cross_entropy(logits, y)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            scheduler.step()
            loss_sum += loss.item() * len(y)
            correct += int((cosine.argmax(1) == y).sum())
            seen += len(y)
            if step % 200 == 0:
                print(f"  época {epoch} paso {step}/{steps_per_epoch} pérdida {loss.item():.3f} "
                      f"{seen / (perf_counter() - start):.0f} img/s", flush=True)
            if not math.isfinite(loss.item()):
                raise RuntimeError("La pérdida dejó de ser finita; revisar la tasa de aprendizaje.")
        metrics = evaluate(model, val_faces, genuine, impostor, device)
        row = {"epoch": epoch, "loss": loss_sum / seen, "train_acc": correct / seen,
               "seconds": round(perf_counter() - start, 1), "lr": scheduler.get_last_lr()[0]} | metrics
        log.write(json.dumps(row) + "\n")
        log.flush()
        print(json.dumps(row), flush=True)
        torch.save({"model": model.state_dict(), "epoch": epoch, "metrics": metrics}, args.out / "last.pt")
        if metrics["tar_far1"] > best:
            best = metrics["tar_far1"]
            torch.save({"model": model.state_dict(), "epoch": epoch, "metrics": metrics}, args.out / "best.pt")
    log.close()
    print(f"Mejor TAR@FAR=1 %: {best:.4f}. Pesos en {args.out / 'best.pt'}")


if __name__ == "__main__":
    main()
