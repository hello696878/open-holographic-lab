"""M7 discrete geometry: exact membership and exact assigned intensity bits.

Expected masks are hand enumerations or independent rational arithmetic;
neither reference calls the production rasterizer's membership helper.
"""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from fractions import Fraction
from types import MappingProxyType

import numpy as np
import pytest

from ohlab.target_design import TargetDesign2D, rasterize_target_design


def obj(kind="disk", *, intensity=0.3, identifier=1, **parameters):
    defaults = {
        "disk": {"cx_px": 0.0, "cy_px": 0.0, "radius_px": 2.0},
        "rectangle": {"cx_px": 0.0, "cy_px": 0.0, "width_px": 2.0, "height_px": 2.0},
        "segment": {"x0_px": -1.0, "y0_px": 0.0, "x1_px": 1.0, "y1_px": 0.0, "width_px": 2.0},
    }
    return {"id": f"{identifier:032x}", "type": kind,
            "parameters": defaults[kind] | parameters, "intensity": intensity}


def spec(*objects, ny=5, nx=7, background=0.0):
    return {"schema_version": 1, "rasterizer_version": "center_sample_overwrite_v1",
            "coordinate_system": "centered_pixels_y_down_v1", "canvas": {"ny": ny, "nx": nx},
            "background_intensity": background, "objects": list(objects)}


def exact(actual, expected):
    """These are exact assigned values/masks, not approximate floating results."""
    expected = np.array(expected, dtype=np.float64, order="C")
    assert actual.dtype == expected.dtype and actual.shape == expected.shape
    assert actual.tobytes(order="C") == expected.tobytes(order="C")


def test_hand_computable_disk_mask_and_fractional_intensity():
    actual = rasterize_target_design(TargetDesign2D(spec(obj())))
    # x=-3..3, y=-2..2; integer points satisfying x*x+y*y <= 4.
    mask = np.array([[0, 0, 0, 1, 0, 0, 0],
                     [0, 0, 1, 1, 1, 0, 0],
                     [0, 1, 1, 1, 1, 1, 0],
                     [0, 0, 1, 1, 1, 0, 0],
                     [0, 0, 0, 1, 0, 0, 0]], dtype=bool)
    expected = np.zeros((5, 7), dtype=np.float64)
    expected[mask] = 0.3
    exact(actual, expected)
    assert actual.max().hex() == float(0.3).hex()  # no sqrt or peak normalization


@pytest.mark.parametrize("shape,item,rows", [
    ((4, 5), obj(cx_px=1.0, cy_px=-1.0, radius_px=1.0), ["00010", "00111", "00010", "00000"]),
    ((4, 5), obj("rectangle", cx_px=-0.5, cy_px=0.0, width_px=1.0, height_px=2.0),
     ["00000", "01100", "01100", "01100"]),
    ((5, 4), obj("rectangle", cx_px=0.5, cy_px=-1.0, width_px=1.0, height_px=2.0),
     ["0011", "0011", "0011", "0000", "0000"]),
])
def test_supplied_hand_masks(shape, item, rows):
    expected = np.array([[0.3 if digit == "1" else 0.0 for digit in row] for row in rows])
    exact(rasterize_target_design(TargetDesign2D(spec(item, ny=shape[0], nx=shape[1]))), expected)


@pytest.mark.parametrize("shape", [(4, 7), (5, 8), (4, 8), (5, 7)])
def test_mixed_parity_asymmetric_xy_and_origin(shape):
    ny, nx = shape
    design = TargetDesign2D(spec(obj("rectangle", cx_px=2.0, cy_px=-1.0,
                                     width_px=0.5, height_px=0.5), ny=ny, nx=nx))
    expected = np.zeros(shape, dtype=np.float64)
    expected[ny // 2 - 1, nx // 2 + 2] = 0.3
    exact(rasterize_target_design(design), expected)
    center = TargetDesign2D(spec(obj(radius_px=0.1), ny=ny, nx=nx))
    expected.fill(0)
    expected[ny // 2, nx // 2] = 0.3
    exact(rasterize_target_design(center), expected)


@pytest.mark.parametrize("kind,key,boundary", [("disk", "radius_px", 1.0),
                                                ("rectangle", "width_px", 2.0),
                                                ("segment", "width_px", 2.0)])
def test_inclusive_edges_and_adjacent_representable_sizes(kind, key, boundary):
    other = {"height_px": 0.25} if kind == "rectangle" else {}
    if kind == "segment":
        other = {"x0_px": 0.0, "y0_px": -1.0, "x1_px": 0.0, "y1_px": 1.0}
    for value, included in [(np.nextafter(boundary, 0.0), False),
                            (boundary, True), (np.nextafter(boundary, np.inf), True)]:
        model = TargetDesign2D(spec(obj(kind, **other, **{key: float(value)})))
        actual = rasterize_target_design(model)
        assert bool(actual[2, 4] == 0.3) == included


def test_geometric_rectangle_width_two_covers_three_centers():
    actual = rasterize_target_design(TargetDesign2D(spec(obj("rectangle", height_px=0.25))))
    expected = np.zeros((5, 7), dtype=np.float64)
    expected[2, 2:5] = 0.3
    exact(actual, expected)


def test_segment_round_caps_hand_mask():
    actual = rasterize_target_design(TargetDesign2D(spec(obj("segment"))))
    expected = np.zeros((5, 7), dtype=np.float64)
    expected[1, 2:5] = 0.3
    expected[2, 1:6] = 0.3
    expected[3, 2:5] = 0.3
    exact(actual, expected)


def test_coincident_segment_is_disk_without_approximate_endpoint_equality():
    point = obj("segment", x0_px=1.0, x1_px=1.0, y0_px=-1.0, y1_px=-1.0, width_px=2.0)
    actual = rasterize_target_design(TargetDesign2D(spec(point)))
    expected = np.zeros((5, 7), dtype=np.float64)
    expected[0, 4] = expected[1, 3] = expected[1, 4] = expected[1, 5] = expected[2, 4] = 0.3
    exact(actual, expected)
    tiny = obj("segment", x0_px=0.0, x1_px=1e-200, y0_px=0.0, y1_px=0.0)
    with pytest.raises(ValueError, match="unusable float64 geometry"):
        rasterize_target_design(TargetDesign2D(spec(tiny)))


def _direct_projection_distance2(a, b):
    """Independent scalar reference with the specified, deliberately directed order."""
    ax, ay = map(np.float64, a)
    bx, by = map(np.float64, b)
    dx, dy = bx - ax, by - ay
    t = ((0.0 - ax) * dx + (0.0 - ay) * dy) / (dx * dx + dy * dy)
    t = min(1.0, max(0.0, t))
    return (0.0 - (ax + t * dx))**2 + (0.0 - (ay + t * dy))**2


def test_boundary_sensitive_segment_reversal_preserves_document():
    a, b = (-1.3, -0.2), (2.7, 1.3)
    forward, reverse = _direct_projection_distance2(a, b), _direct_projection_distance2(b, a)
    # This fixture deliberately straddles a represented threshold on the tested
    # environment. Do not replace with allclose or expand the closed boundary.
    width = 0.5383892771022006
    threshold = (np.float64(width) / 2.0)**2
    assert forward <= threshold < reverse, (forward, threshold, reverse)
    first = obj("segment", x0_px=a[0], y0_px=a[1], x1_px=b[0], y1_px=b[1], width_px=width)
    second = obj("segment", x0_px=b[0], y0_px=b[1], x1_px=a[0], y1_px=a[1], width_px=width)
    original, reversed_model = TargetDesign2D(spec(first)), TargetDesign2D(spec(second))
    direct = rasterize_target_design(original)
    reversed_raster = rasterize_target_design(reversed_model)
    assert direct[2, 3] == 0.3
    exact(reversed_raster, direct)
    assert original.to_dict()["objects"][0]["parameters"] == first["parameters"]
    assert reversed_model.to_dict()["objects"][0]["parameters"] == second["parameters"]


def _rational_member(item, x, y):
    """Exact-real reference for safely separated binary rational fixtures."""
    p = {key: Fraction(value) for key, value in item["parameters"].items()}
    x, y = Fraction(x), Fraction(y)
    if item["type"] == "disk":
        return (x-p["cx_px"])**2 + (y-p["cy_px"])**2 <= p["radius_px"]**2
    if item["type"] == "rectangle":
        return abs(x-p["cx_px"]) <= p["width_px"]/2 and abs(y-p["cy_px"]) <= p["height_px"]/2
    ax, ay, bx, by = (p[key] for key in ("x0_px", "y0_px", "x1_px", "y1_px"))
    dx, dy = bx-ax, by-ay
    t = Fraction(0) if dx == dy == 0 else min(Fraction(1), max(Fraction(0),
        ((x-ax)*dx + (y-ay)*dy)/(dx*dx + dy*dy)))
    return (x-(ax+t*dx))**2 + (y-(ay+t*dy))**2 <= (p["width_px"]/2)**2


@pytest.mark.parametrize("item", [
    obj(cx_px=0.25, cy_px=-0.5, radius_px=1.75),
    obj("rectangle", cx_px=1.25, cy_px=-0.5, width_px=2.5, height_px=1.5),
    obj("segment", x0_px=-2.25, y0_px=0.5, x1_px=1.5, y1_px=-1.25, width_px=1.25),
])
def test_independent_fraction_membership_reference(item):
    expected = np.zeros((6, 9), dtype=np.float64)
    for i in range(6):
        for j in range(9):
            if _rational_member(item, j-4, i-3):
                expected[i, j] = item["intensity"]
    exact(rasterize_target_design(TargetDesign2D(spec(item, ny=6, nx=9))), expected)


@pytest.mark.parametrize("a,b,width", [
    ((-2.0, -1.0), (2.0, 1.0), 0.75),
    ((-2.0, 1.0), (2.0, -1.0), 1.5),
    ((-1.0, -2.0), (1.0, 2.0), 1.25),
    ((-1.0, 2.0), (1.0, -2.0), 0.5),
    ((-3.0, -2.0), (0.0, 1.0), 1.0),
    ((0.0, -1.0), (3.0, 2.0), 1.0),
    ((-1.5, -0.5), (2.5, 0.5), 2.0),
    ((-2.5, 1.5), (0.5, -1.5), 1.5),
    ((-2.0, -1.0), (1.0, -1.0), 2.0),
    ((1.0, -2.0), (1.0, 1.0), 2.0),
])
def test_ten_segments_against_independent_rational_membership(a, b, width):
    item = obj("segment", x0_px=a[0], y0_px=a[1], x1_px=b[0], y1_px=b[1], width_px=width)
    expected = np.zeros((6, 9), dtype=np.float64)
    for i in range(6):
        for j in range(9):
            if _rational_member(item, j-4, i-3):
                expected[i, j] = 0.3
    actual = rasterize_target_design(TargetDesign2D(spec(item, ny=6, nx=9)))
    exact(actual, expected)
    reversed_item = obj("segment", x0_px=b[0], y0_px=b[1], x1_px=a[0], y1_px=a[1], width_px=width)
    exact(rasterize_target_design(TargetDesign2D(spec(reversed_item, ny=6, nx=9))), actual)


def test_later_object_overwrites_including_exact_signed_zero():
    first = obj("rectangle", width_px=4.0, height_px=2.0, intensity=0.3)
    last = obj(radius_px=1.0, intensity=-0.0, identifier=2)
    actual = rasterize_target_design(TargetDesign2D(spec(first, last, background=0.1)))
    expected = np.full((5, 7), 0.1, dtype=np.float64)
    expected[1:4, 1:6] = 0.3
    expected[1, 3] = expected[2, 2] = expected[2, 3] = expected[2, 4] = expected[3, 3] = -0.0
    exact(actual, expected)
    reversed_result = rasterize_target_design(TargetDesign2D(spec(last, first, background=0.1)))
    assert reversed_result[2, 3].hex() == (0.3).hex()


def test_off_canvas_partial_empty_and_resize_preserve_coordinates():
    item = obj("rectangle", cx_px=3.0, cy_px=0.0, width_px=2.0, height_px=0.25)
    original = TargetDesign2D(spec(item))
    expected = np.zeros((5, 7))
    expected[2, 5:7] = 0.3
    exact(rasterize_target_design(original), expected)
    resized = original.to_dict()
    resized["canvas"] = {"ny": 3, "nx": 3}
    changed = TargetDesign2D(resized)
    assert changed.to_dict()["objects"] == original.to_dict()["objects"]
    exact(rasterize_target_design(changed), np.zeros((3, 3)))
    exact(rasterize_target_design(TargetDesign2D(spec(background=-0.0))), np.full((5, 7), -0.0))


def test_immutable_owned_model_and_writable_independent_outputs():
    supplied = spec(obj())
    before = deepcopy(supplied)
    design = TargetDesign2D(MappingProxyType(supplied))
    first = rasterize_target_design(design)
    assert supplied == before
    supplied["objects"][0]["parameters"]["radius_px"] = 99.0
    supplied["objects"].clear()
    exported = design.to_dict()
    exported["objects"][0]["intensity"] = 1.0
    exported["canvas"]["nx"] = 99
    assert design.to_dict() == before
    with pytest.raises(FrozenInstanceError):
        design._document = b"{}"
    assert not hasattr(design, "__dict__")
    assert type(first) is np.ndarray and first.dtype == np.dtype(np.float64)
    assert first.dtype.isnative and first.flags.c_contiguous and first.flags.owndata and first.flags.writeable
    second = rasterize_target_design(design)
    exact(second, first)
    assert not np.shares_memory(first, second)
    first.fill(1)
    assert second[2, 3] == 0.3


@pytest.mark.parametrize("path,value,error", [
    (("schema_version",), True, TypeError), (("schema_version",), 2, ValueError),
    (("rasterizer_version",), "unknown", ValueError), (("coordinate_system",), "y_up", ValueError),
    (("canvas", "ny"), 0, ValueError), (("canvas", "nx"), 513, ValueError),
    (("canvas", "ny"), 3.0, TypeError), (("canvas", "ny"), np.int64(3), TypeError),
    (("canvas", "ny"), False, TypeError), (("objects",), (), TypeError),
    (("background_intensity",), -0.01, ValueError), (("background_intensity",), 1.01, ValueError),
    (("background_intensity",), True, TypeError), (("background_intensity",), np.float64(0.3), TypeError),
    (("background_intensity",), float("nan"), ValueError),
    (("background_intensity",), float("inf"), ValueError),
    (("background_intensity",), 10**1000, ValueError),
    (("objects", 0, "id"), "f" * 31, ValueError), (("objects", 0, "id"), "A" * 32, ValueError),
    (("objects", 0, "id"), 1, TypeError), (("objects", 0, "type"), "triangle", ValueError),
    (("objects", 0, "intensity"), -1.0, ValueError), (("objects", 0, "intensity"), "0.3", TypeError),
    (("objects", 0, "parameters", "cx_px"), 4096.1, ValueError),
    (("objects", 0, "parameters", "cy_px"), -4096.1, ValueError),
    (("objects", 0, "parameters", "radius_px"), 8192.1, ValueError),
    (("objects", 0, "parameters", "radius_px"), 0.0, ValueError),
    (("objects", 0, "parameters", "radius_px"), -0.0, ValueError),
    (("objects", 0, "parameters", "cx_px"), float("inf"), ValueError),
])
def test_schema_scalar_validation(path, value, error):
    document = spec(obj())
    current = document
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = value
    with pytest.raises(error):
        TargetDesign2D(document)


@pytest.mark.parametrize("path", [(), ("canvas",), ("objects", 0), ("objects", 0, "parameters")])
@pytest.mark.parametrize("operation", ["extra", "missing", "non_string_key", "wrong_type"])
def test_exact_fields_at_every_schema_level(path, operation):
    document = spec(obj())
    current = document
    for key in path:
        current = current[key]
    if operation == "wrong_type":
        if not path:
            document = []
        else:
            parent = document
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = []
    elif operation == "missing":
        del current[next(iter(current))]
    else:
        current["unexpected" if operation == "extra" else 7] = 1
    with pytest.raises(TypeError if operation in ("wrong_type", "non_string_key") else ValueError):
        TargetDesign2D(document)


def test_inclusive_limits_unique_ids_and_object_count():
    items = [obj(identifier=i, cx_px=-4096, cy_px=4096, radius_px=8192, intensity=1) for i in range(64)]
    document = spec(*items, ny=512, nx=1, background=1)
    design = TargetDesign2D(document)
    assert rasterize_target_design(design).shape == (512, 1)
    duplicate = deepcopy(document)
    duplicate["objects"][1]["id"] = duplicate["objects"][0]["id"]
    with pytest.raises(ValueError, match="duplicate"):
        TargetDesign2D(duplicate)
    document["objects"].append(obj(identifier=65))
    with pytest.raises(ValueError, match="at most 64"):
        TargetDesign2D(document)


@pytest.mark.parametrize("kind,parameters", [
    ("disk", {"radius_px": 1e-200}),
    ("rectangle", {"width_px": float(np.nextafter(0.0, 1.0))}),
    ("segment", {"width_px": 1e-200}),
    ("segment", {"x0_px": 0.0, "x1_px": 1e-200}),
])
def test_unusable_required_arithmetic_raises_and_restores_error_state(kind, parameters):
    design = TargetDesign2D(spec(obj(kind, **parameters)))
    with np.errstate(over="ignore", invalid="warn", under="ignore", divide="warn"):
        before = np.geterr()
        with pytest.raises(ValueError, match="unusable float64 geometry"):
            rasterize_target_design(design)
        assert np.geterr() == before
        rasterize_target_design(TargetDesign2D(spec(obj())))
        assert np.geterr() == before


def test_rasterizer_requires_validated_design():
    with pytest.raises(TypeError, match="TargetDesign2D"):
        rasterize_target_design(spec())
