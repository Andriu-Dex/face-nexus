"""CNN propia humano / no humano. Entrena con LFW y CIFAR-10, no identifica a K01–K04."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from time import perf_counter
import warnings

import cv2
import numpy as np

from scripts.capture_manifest import child, utc_now, write_synced
from scripts.dataset_capture import PROJECT, verify_vault


SEED = 17
SIZE = 64
EPOCHS = 8
BATCH = 32
LEARNING_RATE = .001
HUMAN = 1
NONHUMAN = 0
SOURCES = {
    "lfw": {
        "role": "human",
        "origin": "Labeled Faces in the Wild, University of Massachusetts",
        "use": "investigación académica; no se republican imágenes",
        "note": "Identidades de LFW no son K01–K04. Solo la etiqueta humano.",
    },
    "cifar10": {
        "role": "nonhuman",
        "origin": "CIFAR-10, Krizhevsky / University of Toronto, vía Keras",
        "use": "conjunto de referencia de objetos y animales, sin clase persona",
        "note": "Diez clases: avión, auto, ave, gato, ciervo, perro, rana, caballo, barco, camión.",
    },
}


def split_by_identity(identities, train_ratio=.7, seed=SEED):
    """Parte por persona, no por foto. Evita que la misma identidad quede en ambos lotes."""
    identities = np.asarray(identities)
    people = np.unique(identities)
    if len(people) < 2:
        raise ValueError("Se necesitan al menos dos identidades humanas para partir.")
    rng = np.random.default_rng(seed)
    order = rng.permutation(people)
    n_train = max(1, min(len(people) - 1, round(len(people) * train_ratio)))
    train_people = set(order[:n_train].tolist())
    train = np.array([item in train_people for item in identities])
    return train, ~train


def resize_rgb(images, size=SIZE):
    batch = np.empty((len(images), size, size, 3), np.float32)
    for index, image in enumerate(images):
        if image.ndim == 2:
            image = np.stack((image, image, image), axis=-1)
        if image.shape[2] == 4:
            image = image[:, :, :3]
        scaled = cv2.resize(image, (size, size), interpolation=cv2.INTER_AREA)
        batch[index] = scaled.astype(np.float32) / 255. if scaled.max() > 1.5 else scaled
    return batch


def subsample(images, labels, extra, limit, seed=SEED):
    rng = np.random.default_rng(seed)
    if limit is None or len(images) <= limit:
        choice = np.arange(len(images))
    else:
        choice = rng.choice(len(images), size=limit, replace=False)
    return images[choice], labels[choice], extra[choice]


def build_model(keras):
    """Dos convoluciones y una capa densa. Salida: logits no humano / humano."""
    regularizer = keras.regularizers.L2(.0005)
    model = keras.Sequential([
        keras.Input(shape=(SIZE, SIZE, 3)),
        keras.layers.Conv2D(16, 3, activation="relu", kernel_regularizer=regularizer),
        keras.layers.MaxPooling2D(2),
        keras.layers.Conv2D(32, 3, activation="relu", kernel_regularizer=regularizer),
        keras.layers.MaxPooling2D(2),
        keras.layers.Flatten(),
        keras.layers.Dense(32, activation="relu", kernel_regularizer=regularizer),
        keras.layers.Dense(2),
    ], name="human_nonhuman")
    model.compile(optimizer=keras.optimizers.Adam(LEARNING_RATE),
                  loss=keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                  metrics=["accuracy"])
    return model


def score(labels, predicted):
    labels = np.asarray(labels)
    predicted = np.asarray(predicted)
    correct = int((labels == predicted).sum())
    return {
        "n": int(len(labels)),
        "accuracy": correct / len(labels) if len(labels) else None,
        "human_recall": float(((predicted == HUMAN) & (labels == HUMAN)).sum()
                              / max(1, (labels == HUMAN).sum())),
        "nonhuman_recall": float(((predicted == NONHUMAN) & (labels == NONHUMAN)).sum()
                                 / max(1, (labels == NONHUMAN).sum())),
        "confusion": {
            "true_nonhuman_pred_nonhuman": int(((labels == NONHUMAN) & (predicted == NONHUMAN)).sum()),
            "true_nonhuman_pred_human": int(((labels == NONHUMAN) & (predicted == HUMAN)).sum()),
            "true_human_pred_nonhuman": int(((labels == HUMAN) & (predicted == NONHUMAN)).sum()),
            "true_human_pred_human": int(((labels == HUMAN) & (predicted == HUMAN)).sum()),
        },
    }


def load_public(limit):
    """LFW = humano por identidad. CIFAR-10 = no humano con partición oficial."""
    from sklearn.datasets import fetch_lfw_people
    from keras.datasets import cifar10

    lfw = fetch_lfw_people(color=True, min_faces_per_person=2, resize=.5, download_if_missing=True)
    human = resize_rgb(lfw.images)
    human_ids = np.asarray(lfw.target)
    train_mask, val_mask = split_by_identity(human_ids)
    human_train = subsample(human[train_mask], np.full(train_mask.sum(), HUMAN),
                            human_ids[train_mask], limit)
    human_val = subsample(human[val_mask], np.full(val_mask.sum(), HUMAN),
                          human_ids[val_mask], None if limit is None else max(50, limit // 4))

    (cifar_x, _), (cifar_xt, _) = cifar10.load_data()
    cifar_train = subsample(resize_rgb(cifar_x), np.full(len(cifar_x), NONHUMAN),
                            cifar_x[:, 0, 0, 0], limit)
    cifar_val = subsample(resize_rgb(cifar_xt), np.full(len(cifar_xt), NONHUMAN),
                          cifar_xt[:, 0, 0, 0], None if limit is None else max(50, limit // 4))
    return {
        "lfw_people": int(human_ids.max()) + 1,
        "lfw_images": int(len(human)),
        "train": _stack(human_train, cifar_train),
        "validation": _stack(human_val, cifar_val),
    }


def _stack(human_pack, other_pack):
    images = np.concatenate([human_pack[0], other_pack[0]])
    labels = np.concatenate([human_pack[1], other_pack[1]])
    rng = np.random.default_rng(SEED)
    order = rng.permutation(len(labels))
    return images[order], labels[order]


def predict_labels(model, images, batch=256):
    chunks = []
    for start in range(0, len(images), batch):
        logits = np.asarray(model(images[start:start + batch], training=False))
        chunks.append(np.argmax(logits, axis=1))
    return np.concatenate(chunks) if chunks else np.array([], dtype=int)


def class_weights(labels):
    """Invierte la frecuencia para que CIFAR no ahogue a LFW."""
    n_human = int((labels == HUMAN).sum())
    n_other = int((labels == NONHUMAN).sum())
    total = n_human + n_other
    if n_human == 0 or n_other == 0:
        raise ValueError("TRAIN debe contener ambas clases.")
    return {
        HUMAN: total / (2. * n_human),
        NONHUMAN: total / (2. * n_other),
        "n_human": n_human,
        "n_nonhuman": n_other,
    }


def train(keras, train_images, train_labels, val_images, val_labels):
    keras.utils.set_random_seed(SEED)
    model = build_model(keras)
    weights = class_weights(train_labels)
    started = perf_counter()
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        history = model.fit(
            train_images, train_labels, validation_data=(val_images, val_labels),
            batch_size=BATCH, epochs=EPOCHS, verbose=0,
            class_weight={HUMAN: weights[HUMAN], NONHUMAN: weights[NONHUMAN]},
        )
    elapsed = (perf_counter() - started) * 1000
    return model, {
        "ms": elapsed,
        "epochs": EPOCHS,
        "class_weight": {str(HUMAN): weights[HUMAN], str(NONHUMAN): weights[NONHUMAN]},
        "n_train_human": weights["n_human"],
        "n_train_nonhuman": weights["n_nonhuman"],
        "n_val_human": int((val_labels == HUMAN).sum()),
        "n_val_nonhuman": int((val_labels == NONHUMAN).sum()),
        "loss": [float(x) for x in history.history["loss"]],
        "val_loss": [float(x) for x in history.history["val_loss"]],
        "warnings": [str(item.message) for item in notices],
        "train": score(train_labels, predict_labels(model, train_images)),
        "validation": score(val_labels, predict_labels(model, val_images)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, help="Si se indica, guarda el modelo en VeraCrypt.")
    parser.add_argument("--run-name", default="human_cnn_v1")
    parser.add_argument("--limit", type=int, default=2000,
                        help="Máximo de imágenes por clase en TRAIN. None no está permitido aquí; usa 0 para no recortar.")
    args = parser.parse_args()
    limit = None if args.limit == 0 else args.limit
    os.environ["KERAS_BACKEND"] = "jax"
    os.environ["JAX_PLATFORMS"] = "cpu"
    import keras
    import jax

    data = load_public(limit)
    model, metrics = train(keras, *data["train"], *data["validation"])
    summary = {
        "at_utc": utc_now(),
        "task": "human_vs_nonhuman",
        "sources": SOURCES,
        "input_size": [SIZE, SIZE, 3],
        "limit_per_class_train": limit,
        "lfw_identities": data["lfw_people"],
        "lfw_images": data["lfw_images"],
        "versions": {"keras": keras.__version__, "jax": jax.__version__, "numpy": np.__version__},
        "metrics": metrics,
        "not_identity_recognition": True,
    }
    if args.vault:
        folder = child(verify_vault(args.vault), "experiments", "human_cnn", args.run_name)
    else:
        folder = PROJECT / "outputs" / "human_cnn" / args.run_name
    if folder.exists():
        raise FileExistsError("Ese ensayo ya existe. Usa otro --run-name.")
    folder.mkdir(parents=True)
    model.save(folder / "model.keras")
    digest = sha256((folder / "model.keras").read_bytes()).hexdigest()
    summary["model_sha256"] = digest
    write_synced(folder / "summary.json", json.dumps(summary, indent=2, allow_nan=False).encode("utf-8"))
    print(json.dumps({
        "n_train_human": metrics["n_train_human"],
        "n_train_nonhuman": metrics["n_train_nonhuman"],
        "n_val_human": metrics["n_val_human"],
        "n_val_nonhuman": metrics["n_val_nonhuman"],
        "train": metrics["train"],
        "validation": metrics["validation"],
        "saved": str(folder),
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
