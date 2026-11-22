import numpy as np

from scripts.hybrid_hog import FEATURE_COUNT, GEO_COUNT, HYBRID_COUNT, fuse, geometry_vector


def test_geometry_is_scale_invariant_and_unit():
    box = (10, 20, 50, 80)
    points = np.array([[18., 30.], [28., 31.], [24., 40.], [20., 50.], [30., 51.]])
    small = geometry_vector(points, *box)
    wide = geometry_vector(points * 2, 20, 40, 100, 160)
    assert small.shape == (GEO_COUNT,)
    assert np.isclose(np.linalg.norm(small), 1)
    assert np.allclose(small, wide, atol=1e-5)


def test_fuse_keeps_equal_energy_from_geo_and_hog():
    geo = np.zeros(GEO_COUNT, np.float32)
    geo[0] = 1
    hog = np.zeros(FEATURE_COUNT, np.float32)
    hog[0] = 1
    fused = fuse(geo, hog)
    assert fused.shape == (HYBRID_COUNT,)
    assert np.isclose(np.linalg.norm(fused), 1)
    assert np.isclose(np.sum(fused[:GEO_COUNT] ** 2), np.sum(fused[GEO_COUNT:] ** 2))
