import numpy as np
import pytest

from scripts.human_cnn import (
    HUMAN, NONHUMAN, build_model, class_weights, resize_rgb, score, split_by_identity, train,
)


def test_identity_split_keeps_people_out_of_validation():
    ids = np.array(["a", "a", "b", "b", "c", "c"])
    train_mask, val_mask = split_by_identity(ids, train_ratio=.5, seed=0)
    assert not set(ids[train_mask]) & set(ids[val_mask])
    assert train_mask.sum() + val_mask.sum() == 6


def test_tiny_cnn_learns_a_synthetic_color_rule(monkeypatch):
    keras = pytest.importorskip("keras")
    os_environ = __import__("os").environ
    os_environ["KERAS_BACKEND"] = "jax"
    os_environ["JAX_PLATFORMS"] = "cpu"

    monkeypatch.setattr("scripts.human_cnn.EPOCHS", 3)
    humans = np.zeros((12, 64, 64, 3), np.float32)
    humans[:, :, :, 0] = 1
    objects = np.zeros((12, 64, 64, 3), np.float32)
    objects[:, :, :, 2] = 1
    images = np.concatenate([humans, objects])
    labels = np.array([HUMAN] * 12 + [NONHUMAN] * 12)
    model, metrics = train(keras, images, labels, images, labels)
    pred = np.argmax(np.asarray(model(images, training=False)), axis=1)
    assert metrics["train"]["n"] == 24
    assert score(labels, pred)["accuracy"] >= .8
    built = build_model(keras)
    assert built.output_shape[-1] == 2


def test_class_weights_upweight_the_smaller_class():
    labels = np.array([HUMAN, HUMAN, NONHUMAN, NONHUMAN, NONHUMAN, NONHUMAN])
    weights = class_weights(labels)
    assert weights[HUMAN] == 1.5
    assert weights[NONHUMAN] == 0.75


def test_resize_accepts_gray_and_scales_to_unit_interval():
    gray = np.full((20, 30), 255, np.uint8)
    batch = resize_rgb([gray], size=16)
    assert batch.shape == (1, 16, 16, 3)
    assert 0.9 <= batch.max() <= 1.0
