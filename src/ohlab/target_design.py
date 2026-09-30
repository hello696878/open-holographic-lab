"""Immutable, bounded 2-D intensity designs with center-sampled geometry.

This module contains no image, plotting, filesystem, UI, or optical solver
dependency. Pixel coordinates are dimensionless: x points right, y down, and
array element [ny//2, nx//2] is the origin for both even and odd dimensions.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import math
import re

import numpy as np
from numpy.typing import NDArray

__all__ = ["TargetDesign2D", "rasterize_target_design"]

_ROOT_KEYS = {"schema_version", "rasterizer_version", "coordinate_system", "canvas",
              "background_intensity", "objects"}
_PARAMETERS = {
    "disk": {"cx_px", "cy_px", "radius_px"},
    "rectangle": {"cx_px", "cy_px", "width_px", "height_px"},
    "segment": {"x0_px", "y0_px", "x1_px", "y1_px", "width_px"},
}
_SIZE_KEYS = {"radius_px", "width_px", "height_px"}


def _keys(value: object, expected: set[str], name: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name}: expected a mapping, got {type(value).__name__}")
    if any(type(key) is not str for key in value):
        raise TypeError(f"{name}: expected string keys")
    actual = set(value)
    if actual != expected:
        raise ValueError(f"{name}: missing {sorted(expected - actual)}, unknown {sorted(actual - expected)}")
    return dict(value)


def _integer(value: object, name: str, low: int, high: int) -> int:
    if type(value) is not int:
        raise TypeError(f"{name}: expected int excluding bool, got {type(value).__name__}")
    if not low <= value <= high:
        raise ValueError(f"{name}: expected {low}..{high}, got {value}")
    return value


def _real(value: object, name: str, low: float, high: float, *, positive: bool = False) -> float:
    if type(value) not in (int, float):
        raise TypeError(f"{name}: expected built-in int or float excluding bool")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name}: value is not representable as finite binary64") from exc
    if not math.isfinite(number) or number < low or number > high or (positive and number <= 0):
        interval = f"(0,{high}]" if positive else f"[{low},{high}]"
        raise ValueError(f"{name}: expected finite value in {interval}, got {value!r}")
    return number


def _literal(value: object, expected: str, name: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{name}: expected str")
    if value != expected:
        raise ValueError(f"{name}: expected {expected!r}, got {value!r}")
    return value


def _validate(spec: Mapping[str, object]) -> dict[str, object]:
    root = _keys(spec, _ROOT_KEYS, "design")
    version = _integer(root["schema_version"], "schema_version", 1, 1)
    rasterizer = _literal(root["rasterizer_version"], "center_sample_overwrite_v1", "rasterizer_version")
    coordinates = _literal(root["coordinate_system"], "centered_pixels_y_down_v1", "coordinate_system")
    canvas = _keys(root["canvas"], {"ny", "nx"}, "canvas")
    canvas = {key: _integer(canvas[key], f"canvas.{key}", 1, 512) for key in ("ny", "nx")}
    background = _real(root["background_intensity"], "background_intensity", 0.0, 1.0)
    if type(root["objects"]) is not list:
        raise TypeError("objects: expected a list")
    if len(root["objects"]) > 64:
        raise ValueError(f"objects: expected at most 64, got {len(root['objects'])}")
    objects = []
    identifiers = set()
    for index, value in enumerate(root["objects"]):
        name = f"objects[{index}]"
        obj = _keys(value, {"id", "type", "parameters", "intensity"}, name)
        identifier = obj["id"]
        if type(identifier) is not str:
            raise TypeError(f"{name}.id: expected str")
        if re.fullmatch(r"[0-9a-f]{32}", identifier) is None:
            raise ValueError(f"{name}.id: expected 32 lowercase hexadecimal characters")
        if identifier in identifiers:
            raise ValueError(f"{name}.id: duplicate identifier {identifier!r}")
        identifiers.add(identifier)
        kind = obj["type"]
        if type(kind) is not str:
            raise TypeError(f"{name}.type: expected str")
        if kind not in _PARAMETERS:
            raise ValueError(f"{name}.type: unsupported object {kind!r}")
        params = _keys(obj["parameters"], _PARAMETERS[kind], f"{name}.parameters")
        validated = {}
        for key, value in params.items():
            size = key in _SIZE_KEYS
            validated[key] = _real(value, f"{name}.parameters.{key}",
                                   0.0 if size else -4096.0, 8192.0 if size else 4096.0, positive=size)
        objects.append({"id": identifier, "type": kind, "parameters": validated,
                        "intensity": _real(obj["intensity"], f"{name}.intensity", 0.0, 1.0)})
    return {"schema_version": version, "rasterizer_version": rasterizer,
            "coordinate_system": coordinates, "canvas": canvas,
            "background_intensity": background, "objects": objects}


@dataclass(frozen=True, slots=True, eq=False)
class TargetDesign2D:
    """Validated immutable design, preserving scalar bits and object order.

    ``spec`` has exactly schema/rasterizer/coordinate versions, canvas (ny,nx),
    background_intensity and an ordered object list. Coordinates are pixels,
    not metres. Dimensions are 1..512, at most 64 objects are accepted, positions
    are in [-4096,4096], and positive sizes are at most 8192 pixels. Intensity
    values are finite binary64 in [0,1], including signed zero. Numeric scalars
    use built-in int/float, excluding bool; counts require int. IDs are unique
    32-character lowercase hexadecimal strings. Unknown fields are rejected.

    Nested caller containers are never retained. Only immutable canonical JSON
    bytes are stored; ``to_dict`` returns a fresh defensive deep copy. A valid
    document can still fail rasterization if required float64 arithmetic is
    unusable. Resizing the canvas does not alter object parameters.
    """

    _document: bytes

    def __init__(self, spec: Mapping[str, object]) -> None:
        document = json.dumps(_validate(spec), sort_keys=True, ensure_ascii=False,
                              allow_nan=False, indent=2) + "\n"
        object.__setattr__(self, "_document", document.encode("utf-8"))

    def to_dict(self) -> dict[str, object]:
        """Return a new deep dictionary, preserving stored order and scalar bits."""
        return json.loads(self._document)


def _membership(obj: dict[str, object], x: NDArray[np.float64], y: NDArray[np.float64]) -> NDArray[np.bool_]:
    params = obj["parameters"]
    if obj["type"] == "disk":
        return (x - params["cx_px"])**2 + (y - params["cy_px"])**2 <= np.float64(params["radius_px"])**2
    if obj["type"] == "rectangle":
        return ((np.abs(x - params["cx_px"]) <= np.float64(params["width_px"]) / 2.0)
                & (np.abs(y - params["cy_px"]) <= np.float64(params["height_px"]) / 2.0))

    # Internal lexicographic ordering makes the undirected segment execute the
    # identical binary64 operations after endpoint reversal. Stored JSON stays
    # in the user's original endpoint order; no epsilon or snapping is used.
    first = (params["x0_px"], params["y0_px"])
    second = (params["x1_px"], params["y1_px"])
    (ax, ay), (bx, by) = sorted((first, second))
    radius2 = (np.float64(params["width_px"]) / 2.0)**2
    if first == second:
        return (x - ax)**2 + (y - ay)**2 <= radius2
    dx, dy = np.float64(bx) - np.float64(ax), np.float64(by) - np.float64(ay)
    length2 = dx * dx + dy * dy
    if not np.isfinite(length2) or length2 <= 0:
        raise ValueError("distinct segment endpoints require usable positive squared length")
    parameter = ((x - ax) * dx + (y - ay) * dy) / length2
    # This clamp is the specified nearest-point projection onto a finite
    # segment, not brightness clipping. It produces round endpoint caps.
    parameter = np.minimum(1.0, np.maximum(0.0, parameter))
    distance2 = (x - (ax + parameter * dx))**2 + (y - (ay + parameter * dy))**2
    return distance2 <= radius2


def rasterize_target_design(design: TargetDesign2D) -> NDArray[np.float64]:
    """Return a new desired-intensity raster, not amplitude or an optical field.

    Evaluate centers x=j-nx//2, y=i-ny//2. Closed disk/rectangle/capsule
    boundaries are included; later objects overwrite earlier objects, even
    with zero intensity. Off-canvas objects neither move nor wrap. There is no
    antialiasing, brightness clipping, blending or peak normalization. Assigned
    intensity bits are copied unchanged. Widths are geometric lengths, not
    covered-pixel counts: a centered width-2 rectangle covers x=-1,0,1.

    Segment projection uses lexicographically ordered endpoints, dx/dy, squared
    length, clamped dot/length parameter, then squared nearest-point distance.
    Exactly coincident endpoints have disk semantics. Required overflow,
    invalid/division errors or NumPy-reported underflow raise ValueError, also
    for distinct endpoints whose squared length is unusable. Caller NumPy error
    settings are restored. Boundary classification is the declared binary64
    evaluation, not a universal exact-real or cross-environment claim.

    The owned output is writable, plain native float64 and C-contiguous. Pixel
    pitch is not an input and cannot change this raster; unequal physical x/y
    pitches can make a pixel-space disk physically elliptical.
    """
    if not isinstance(design, TargetDesign2D):
        raise TypeError("design: expected TargetDesign2D")
    spec = design.to_dict()
    ny, nx = spec["canvas"]["ny"], spec["canvas"]["nx"]
    x, y = np.meshgrid(np.arange(nx, dtype=np.float64) - nx // 2,
                       np.arange(ny, dtype=np.float64) - ny // 2, indexing="xy")
    result = np.full((ny, nx), spec["background_intensity"], dtype=np.float64, order="C")
    for obj in spec["objects"]:
        try:
            with np.errstate(over="raise", under="raise", invalid="raise", divide="raise"):
                mask = _membership(obj, x, y)
        except (FloatingPointError, OverflowError, ValueError) as exc:
            raise ValueError(f"object {obj['id']} ({obj['type']}): unusable float64 geometry: {exc}") from exc
        result[mask] = obj["intensity"]
    return result
