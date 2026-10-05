"""Bounded V1 transient transport, not an experiment archive.

The preamble is ``<8sII``: magic, unpadded UTF-8 header byte length, reserved
zero. The header is padded with zeros to an eight-byte boundary. Descriptor
offsets start at the following payload. All three arrays are little-endian
binary64 in C order: intensity (amplitude_unit^2), x_m and y_m (metres).
"""

from __future__ import annotations

import hashlib
import json
import struct
import uuid

import numpy as np

from ohlab.optics import SequentialExperiment, SequentialResult

MAGIC = b"OHLABV1\0"
PROTOCOL_VERSION = 1
MAX_AXIS = 512
MAX_COMPONENTS = 8
MAX_BODY_BYTES = 32_768
MAX_HEADER_BYTES = 16_384
MAX_RESPONSE_BYTES = 2_359_296
PREAMBLE = struct.Struct("<8sII")


def validate_request_id(value: object) -> str:
    """Require a canonical lowercase UUIDv4 string; no scientific units."""
    if not isinstance(value, str):
        raise TypeError("request_id: expected canonical UUIDv4 string")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ValueError("request_id: expected canonical UUIDv4 string") from exc
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError("request_id: expected canonical lowercase UUIDv4 string")
    return value


def experiment_digest(experiment: SequentialExperiment) -> str:
    """Hash canonical server serialization of the complete SI specification.

This is a transport identity. It is not an M5 qualification or persistence
contract, and clients must not assume JavaScript serializes floats identically.
"""
    if not isinstance(experiment, SequentialExperiment):
        raise TypeError("experiment: expected SequentialExperiment")
    encoded = json.dumps(experiment.to_dict(), sort_keys=True,
                         separators=(",", ":"), ensure_ascii=True,
                         allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def encode_result(request_id: str, result: SequentialResult) -> bytes:
    """Encode actual terminal intensity and coordinates with original V0 stages.

Intensity is amplitude_unit^2; coordinates and stage z are metres. Stage norms
retain V0 amplitude_unit^2 m^2 values, including signed differences and null
undefined ratios. No normalization, intermediate fields, phase, or float32
scientific values are introduced.
"""
    validate_request_id(request_id)
    if not isinstance(result, SequentialResult):
        raise TypeError("result: expected SequentialResult")
    grid = result.experiment.grid
    if not (1 <= grid.ny <= MAX_AXIS and 1 <= grid.nx <= MAX_AXIS):
        raise ValueError("result grid exceeds V1 limits")
    if len(result.experiment.components) > MAX_COMPONENTS:
        raise ValueError("result components exceed V1 limits")
    try:
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            intensity = result.observation.intensity
    except FloatingPointError as exc:
        raise ValueError("terminal intensity is not usable binary64") from exc
    arrays = (("intensity", intensity, (grid.ny, grid.nx), "amplitude_unit^2"),
              ("x_m", grid.x, (grid.nx,), "m"),
              ("y_m", grid.y, (grid.ny,), "m"))
    descriptors: list[dict[str, object]] = []
    payload_parts: list[bytes] = []
    offset = 0
    for name, values, shape, units in arrays:
        if values.shape != shape or values.dtype != np.dtype("float64"):
            raise ValueError(f"{name}: expected finite float64 shape {shape}")
        if not np.isfinite(values).all():
            raise ValueError(f"{name}: expected finite float64 values")
        if name == "intensity" and np.any(values < 0):
            raise ValueError("intensity: expected nonnegative values")
        part = np.ascontiguousarray(values, dtype="<f8").tobytes(order="C")
        descriptors.append({"name": name, "dtype": "float64-le", "order": "C",
                            "shape": list(shape), "offset_bytes": offset,
                            "nbytes": len(part), "units": units})
        payload_parts.append(part)
        offset += len(part)
    header = {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "experiment_sha256": experiment_digest(result.experiment),
        "experiment": result.experiment.to_dict(),
        "stages": [{"selector": stage.selector, "z_m": stage.z_m,
                    "norm": stage.norm, "previous_norm": stage.previous_norm,
                    "delta_norm": stage.delta_norm,
                    "transmission_ratio": stage.transmission_ratio}
                   for stage in result.stages],
        "arrays": descriptors,
        "intensity_max": float(np.max(intensity)),
    }
    encoded_header = json.dumps(header, separators=(",", ":"), ensure_ascii=True,
                                allow_nan=False).encode("utf-8")
    if len(encoded_header) > MAX_HEADER_BYTES:
        raise ValueError("result header exceeds V1 byte limit")
    padding = b"\0" * (-len(encoded_header) % 8)
    size = PREAMBLE.size + len(encoded_header) + len(padding) + offset
    if size > MAX_RESPONSE_BYTES:
        raise ValueError("result frame exceeds V1 byte limit")
    return b"".join((PREAMBLE.pack(MAGIC, len(encoded_header), 0),
                     encoded_header, padding, *payload_parts))
