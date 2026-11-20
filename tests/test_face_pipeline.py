from pathlib import Path

import cv2
import numpy as np
import pytest

from scripts.face_pipeline import (explore, load_models, private_path,
                                   process_image, validate_embedding)


FACE = np.array([[5, 5, 40, 40, 15, 15, 35, 15, 25, 25, 15, 35, 35, 35, .99]], np.float32)


class Detector:
    def __init__(self, faces):
        self.faces = faces

    def setInputSize(self, size):
        self.size = size

    def detect(self, image):
        return None, self.faces


class Extractor:
    def alignCrop(self, image, face):
        return np.zeros((112, 112, 3), np.uint8)

    def feature(self, aligned):
        return np.ones((1, 128), np.float32)


@pytest.mark.parametrize("faces,status", [(None, "no_face"),
    (np.concatenate([FACE, FACE]), "multiple_faces"), (FACE, "ok")])
def test_detection_outcomes_and_preservation(faces, status):
    image = np.zeros((64, 64, 3), np.uint8)
    before = image.copy()
    result, aligned, vector = process_image(image, Detector(faces), Extractor())
    assert result["status"] == status
    np.testing.assert_array_equal(image, before)
    if status == "ok":
        assert aligned.shape == (112, 112, 3)
        assert vector.shape == (128,)
    else:
        assert aligned is None and vector is None


@pytest.mark.parametrize("image", [None, np.zeros((3, 3), np.uint8), np.zeros((3, 3, 3), np.float32)])
def test_invalid_image(image):
    assert process_image(image, Detector(FACE), Extractor())[0]["status"] == "invalid_image"


@pytest.mark.parametrize("vector", [np.zeros(128, np.float32), np.ones(127, np.float32),
    np.full(128, np.nan, np.float32), np.full(128, np.inf, np.float32), np.ones(128, np.float64)])
def test_rejects_bad_embeddings(vector):
    with pytest.raises(ValueError):
        validate_embedding(vector)


def test_bad_landmarks_and_detector_exception():
    face = FACE.copy()
    face[0, 4] = -5
    assert process_image(np.zeros((64, 64, 3), np.uint8), Detector(face), Extractor())[0]["status"] == "invalid_geometry"
    class BrokenDetector(Detector):
        def detect(self, image):
            raise cv2.error("injected")
    assert process_image(np.zeros((64, 64, 3), np.uint8), BrokenDetector(None), Extractor())[0]["status"] == "processing_error"


def test_refuses_missing_and_modified_models(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_models(tmp_path)
    from scripts.download_face_models import MODELS
    (tmp_path / MODELS["yunet"][1]).write_bytes(b"not weights")
    with pytest.raises(ValueError):
        load_models(tmp_path)


def test_outputs_must_stay_under_private_root(tmp_path):
    assert private_path(tmp_path / "private/results", tmp_path / "private").name == "results"
    with pytest.raises(ValueError):
        private_path(tmp_path / "private/../public", tmp_path / "private")
    with pytest.raises(ValueError):
        private_path(tmp_path / "private", tmp_path / "private")


def test_cosine_pairs_exclude_diagonal_and_are_not_classification():
    vectors = np.array([[1, 0], [1, 0], [0, 1], [0, 1]], np.float32)
    summary, matrix = explore(vectors, ["A", "A", "B", "B"], ["1", "2", "3", "4"])
    assert summary["intra"]["n"] == 2
    assert summary["inter"]["n"] == 4
    assert summary["intra"]["median"] == 1
    assert summary["inter"]["median"] == 0
