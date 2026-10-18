"""W1 bounded transient frame; no optical calculation or archive format.

Preamble ``<8sII`` contains magic, unpadded UTF-8 header length, reserved zero.
Zero padding aligns the payload to eight bytes. Intensity sections and metre
axes are contiguous C-order little-endian binary64, with exact descriptors.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import math
import struct

import numpy as np

from ohlab.optics.wave_field import WaveFieldResult, section_plan

from .protocol import experiment_digest, validate_request_id

MAGIC = b"OHLABWF\0"
PROTOCOL_VERSION = 1
MESSAGE_TYPE = "w1_wave_field"
MAX_AXIS = 128
MAX_SECTIONS = 25
MAX_INTERIORS = 19
MAX_BODY_BYTES = 32_768
MAX_HEADER_BYTES = 65_536
MAX_RESPONSE_BYTES = 3_344_400
PREAMBLE = struct.Struct("<8sII")


def strict_json_loads(data: bytes) -> object:
    """Parse bounded strict UTF-8 JSON, rejecting duplicates and underflow."""
    if type(data) is not bytes:
        raise TypeError("JSON body: expected bytes")
    if len(data) > MAX_BODY_BYTES:
        raise ValueError("JSON body exceeds 32768 bytes")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON object key")
            result[key] = value
        return result

    def constant(token):
        raise ValueError("nonfinite JSON constant")

    def real(token):
        value = float(token)
        coefficient = token.lower().split("e", 1)[0]
        if not math.isfinite(value) or (value == 0 and any(c in "123456789" for c in coefficient)):
            raise ValueError("JSON number is not usable finite binary64")
        return value

    def integer(token):
        value = int(token)
        if not math.isfinite(float(value)):
            raise ValueError("JSON integer exceeds finite binary64")
        return value

    try:
        return json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                          parse_constant=constant, parse_float=real, parse_int=integer)
    except (UnicodeError, json.JSONDecodeError, RecursionError, OverflowError) as exc:
        raise ValueError("expected bounded strict UTF-8 JSON") from exc


def _real(value: object, name: str, *, nonnegative: bool = False) -> float:
    if type(value) not in (int, float):
        raise TypeError(f"{name}: expected finite real excluding bool")
    value = float(value)
    if not math.isfinite(value) or (nonnegative and value < 0):
        raise ValueError(f"{name}: expected finite {'nonnegative ' if nonnegative else ''}value")
    return value


def _stage_dict(stage) -> dict[str, object]:
    return {"selector": stage.selector, "z_m": stage.z_m, "norm": stage.norm,
            "previous_norm": stage.previous_norm, "delta_norm": stage.delta_norm,
            "transmission_ratio": stage.transmission_ratio}


def encode_result(request_id: str, result: WaveFieldResult) -> bytes:
    """Encode exact section samples, geometry and canonical V0 diagnostics.

Intensity is amplitude_unit^2, positions metres and norms amplitude_unit^2 m^2.
Canonical stage norms are retained; they are not replaced by image reductions.
No complex stack, optical operation, normalization or resampling is introduced.
"""
    validate_request_id(request_id)
    if not isinstance(result, WaveFieldResult):
        raise TypeError("result: expected WaveFieldResult")
    grid = result.experiment.grid
    if not (1 <= grid.ny <= MAX_AXIS and 1 <= grid.nx <= MAX_AXIS):
        raise ValueError("W1 result grid exceeds 128-axis limit")
    if result.canonical.experiment != result.experiment:
        raise ValueError("canonical experiment does not match W1 result")
    layout = section_plan(result.experiment, interior_z_m=result.interior_z_m)
    if not 6 <= len(result.planes) <= MAX_SECTIONS or len(result.planes) != len(layout):
        raise ValueError("planes: expected complete bounded section plan")
    canonical = result.canonical.stages
    expected_stages = [("source", 0.0)]
    for component in result.experiment.components:
        expected_stages.extend(((f"before:{component.id}", component.z_m),
                                (f"after:{component.id}", component.z_m)))
    expected_stages.append(("observation", result.experiment.observation.z_m))
    if [(stage.selector, stage.z_m) for stage in canonical] != expected_stages:
        raise ValueError("canonical stages: wrong complete ordered identities")
    by_stage = {stage.selector: _stage_dict(stage) for stage in canonical}
    previous = None
    for stage in canonical:
        _real(stage.norm, "stage.norm", nonnegative=True)
        if stage.previous_norm != previous:
            raise ValueError("canonical stage norm chain disagrees")
        previous = stage.norm
    arrays = (("intensities", result.intensities, (len(layout), grid.ny, grid.nx), "amplitude_unit^2"),
              ("x_m", result.x_m, (grid.nx,), "m"),
              ("y_m", result.y_m, (grid.ny,), "m"))
    descriptors, parts, offset = [], [], 0
    for name, values, shape, units in arrays:
        if (not isinstance(values, np.ndarray) or values.shape != shape or
                values.dtype != np.dtype("float64")):
            raise ValueError(f"{name}: expected float64 shape {shape}")
        if not np.isfinite(values).all() or (name == "intensities" and np.any(values < 0)):
            raise ValueError(f"{name}: expected finite {'nonnegative ' if name == 'intensities' else ''}values")
        if name in {"x_m", "y_m"} and not np.array_equal(values, grid.x if name == "x_m" else grid.y):
            raise ValueError(f"{name}: coordinates disagree with original grid")
        part = np.ascontiguousarray(values, dtype="<f8").tobytes(order="C")
        descriptors.append({"name": name, "dtype": "float64-le", "order": "C", "shape": list(shape),
                            "offset_bytes": offset, "nbytes": len(part), "units": units})
        parts.append(part)
        offset += len(part)
    planes = []
    for index, (plane, position) in enumerate(zip(result.planes, layout)):
        record = asdict(plane)
        if any(record.get(key) != value for key, value in asdict(position).items()):
            raise ValueError("plane: incorrect section identity, order, position or upstream provenance")
        norm = _real(plane.norm, "plane.norm", nonnegative=True)
        _real(plane.on_axis_intensity, "plane.on_axis_intensity", nonnegative=True)
        _real(plane.max_intensity, "plane.max_intensity", nonnegative=True)
        values = result.intensities[index]
        if plane.on_axis_intensity != float(values[grid.ny // 2, grid.nx // 2]) or plane.max_intensity != float(np.max(values)):
            raise ValueError("plane: raw intensity diagnostics disagree with samples")
        if plane.stage != "interior":
            stage = by_stage[plane.stage]
            if plane.comparison != "previous_stage" or any(record[key] != stage[key] for key in
                    ("norm", "previous_norm", "delta_norm", "transmission_ratio")):
                raise ValueError("plane: canonical signed diagnostics disagree")
        else:
            upstream = by_stage[plane.anchor_selector]["norm"]
            if plane.comparison != "upstream_anchor" or plane.previous_norm != upstream:
                raise ValueError("interior: expected upstream-anchor norm comparison")
            if plane.delta_norm != norm - upstream:
                raise ValueError("interior: signed delta disagrees")
            if plane.transmission_ratio != (None if upstream == 0 else norm / upstream):
                raise ValueError("interior: ratio disagrees")
        planes.append(record)
    with np.errstate(over="raise", invalid="raise", under="ignore"):
        terminal_intensity = result.canonical.observation.intensity
    if result.intensities[-1].tobytes() != terminal_intensity.tobytes():
        raise ValueError("terminal intensity must retain canonical V0 samples byte-for-byte")
    header = {"protocol_version": PROTOCOL_VERSION, "message_type": MESSAGE_TYPE,
              "request_id": request_id, "experiment_sha256": experiment_digest(result.experiment),
              "experiment": result.experiment.to_dict(),
              "sampling": {"interior_z_m": list(result.interior_z_m)},
              "ordered_section_ids": [plane.id for plane in result.planes],
              "planes": planes, "stages": [_stage_dict(stage) for stage in canonical],
              "arrays": descriptors}
    encoded = json.dumps(header, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_HEADER_BYTES:
        raise ValueError("W1 result header exceeds 65536 bytes")
    padding = b"\0" * (-len(encoded) % 8)
    if PREAMBLE.size + len(encoded) + len(padding) + offset > MAX_RESPONSE_BYTES:
        raise ValueError("W1 result exceeds 3344400 bytes")
    return b"".join((PREAMBLE.pack(MAGIC, len(encoded), 0), encoded, padding, *parts))
