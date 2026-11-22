import cv2
import numpy as np

from scripts.face_pipeline import crop_quality
from scripts.frame_quality import COPIED_LAPLACIAN, floors_from_rows, quality_flags


def _stripes(size=64, period=4):
    grey = np.zeros((size, size), np.uint8)
    grey[:, ::period] = 255
    return grey


def test_blur_lowers_laplacian_and_copied_threshold_is_not_the_floor():
    sharp = crop_quality(_stripes())
    soft = crop_quality(np.full((64, 64), 80, np.uint8))
    assert sharp["laplacian_var"] > soft["laplacian_var"]
    dark = crop_quality(np.full((40, 40), 5, np.uint8))
    assert dark["dark_fraction"] == 1
    bright = crop_quality(np.full((40, 40), 250, np.uint8))
    assert bright["bright_fraction"] == 1
    copied = floors_from_rows([sharp, soft])
    assert copied["copied_laplacian"] == COPIED_LAPLACIAN
    assert copied["below_copied_laplacian"] == 1
    assert copied["laplacian_var"] != COPIED_LAPLACIAN
    floors = floors_from_rows([sharp, sharp, sharp])
    assert floors["below_copied_laplacian"] == 0
    assert "blur" in quality_flags(soft, floors)
    assert quality_flags(sharp, floors) == []
    tiny = dict(sharp)
    tiny["width_px"] = tiny["height_px"] = 8
    assert "small_box" in quality_flags(tiny, floors)
    assert "small_box" not in quality_flags(tiny, floors, check_size=False)
