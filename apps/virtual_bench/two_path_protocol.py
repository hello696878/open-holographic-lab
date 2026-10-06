"""Bounded V2b transient dual-output transport; no scientific archive format.

``OHLAB2P\0`` uses a little-endian ``<8sII`` preamble and zero padding to
eight-byte alignment. Payloads contain only two actual float64 intensities
and their common metre axes. V1 framing and limits are unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import struct

import numpy as np

from ohlab.optics.interference import TwoArmResult

from .protocol import validate_request_id

MAGIC = b"OHLAB2P\0"
PROTOCOL_VERSION = 1
MAX_AXIS = 512
MAX_SWEEP_AXIS = 128
MAX_BODY_BYTES = 32_768
MAX_HEADER_BYTES = 16_384
# 16-byte preamble + maximum aligned header + 2 intensities/shared axes at 512².
MAX_RESPONSE_BYTES = 4_218_896
MAX_SWEEP_RESPONSE_BYTES = 65_536
PREAMBLE = struct.Struct("<8sII")
PHASES_RAD = (
    0.0, 0.39269908169872414, 0.7853981633974483, 1.1780972450961724,
    1.5707963267948966, 1.9634954084936207, 2.356194490192345,
    2.748893571891069, 3.141592653589793, 3.5342917352885173,
    3.9269908169872414, 4.319689898685965, 4.71238898038469,
    5.105088062083414, 5.497787143782138, 5.890486225480862,
    6.283185307179586,
)


def _json(value: object, *, canonical: bool = False) -> bytes:
    return json.dumps(value, sort_keys=canonical, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def experiment_digest(experiment: dict[str, object]) -> str:
    """Hash the complete server-canonical SI transport specification."""
    if not isinstance(experiment, dict):
        raise TypeError("experiment: expected dictionary")
    return hashlib.sha256(_json(experiment, canonical=True)).hexdigest()


def sweep_digest(fixed_experiment: dict[str, object], phases_rad: tuple[float, ...]) -> str:
    """Hash fixed SI inputs and the exact requested phase grid together."""
    return hashlib.sha256(_json({"fixed_experiment": fixed_experiment,
                                "phases_rad": phases_rad}, canonical=True)).hexdigest()


def norm_records(result: TwoArmResult) -> dict[str, object]:
    """Copy all ten authoritative returned sampled norms (amplitude-unit² m²)."""
    return {name: list(getattr(result.norms, name)) for name in
            ("inputs", "split", "propagated", "combiner", "outputs")}


def diagnostics(result: TwoArmResult) -> dict[str, object]:
    """Read public V2a properties; never integrate image buffers or renormalize."""
    names = ("inputs_total", "split_total", "propagated_total", "combiner_total",
             "outputs_total", "split_delta", "propagation_delta", "phase_delta",
             "recombination_delta", "total_delta", "output_fractions",
             "total_output_ratio")
    return {name: getattr(result.norms, name) for name in names}


def encode_result(request_id: str, experiment: dict[str, object],
                  result: TwoArmResult) -> bytes:
    """Encode both actual ordered intensities and public scalar diagnostics.

    Intensities use amplitude-unit², axes metres. No complex intermediate,
    normalization, dark clamp, reflected frame or precision conversion is added.
    """
    validate_request_id(request_id)
    if not isinstance(result, TwoArmResult):
        raise TypeError("result: expected TwoArmResult")
    grid = result.outputs[0].grid
    if not (1 <= grid.ny <= MAX_AXIS and 1 <= grid.nx <= MAX_AXIS):
        raise ValueError("result grid exceeds V2b limits")
    if result.outputs[1].grid != grid:
        raise ValueError("output grids must match exactly")
    try:
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            intensities = tuple(output.intensity for output in result.outputs)
    except FloatingPointError as exc:
        raise ValueError("output intensity is not usable binary64") from exc
    arrays = (("intensity_port_0", "intensity", "port_0", intensities[0],
               (grid.ny, grid.nx), "amplitude_unit^2"),
              ("intensity_port_1", "intensity", "port_1", intensities[1],
               (grid.ny, grid.nx), "amplitude_unit^2"),
              ("x_m", "coordinate", None, grid.x, (grid.nx,), "m"),
              ("y_m", "coordinate", None, grid.y, (grid.ny,), "m"))
    descriptors = []
    parts = []
    offset = 0
    for name, role, port_id, values, shape, units in arrays:
        if values.shape != shape or values.dtype != np.dtype("float64"):
            raise ValueError(f"{name}: expected finite float64 shape {shape}")
        if not np.isfinite(values).all() or (role == "intensity" and np.any(values < 0)):
            raise ValueError(f"{name}: expected finite {'nonnegative ' if role == 'intensity' else ''}values")
        part = np.ascontiguousarray(values, dtype="<f8").tobytes(order="C")
        descriptors.append({"name": name, "role": role, "port_id": port_id,
                            "dtype": "float64-le", "order": "C", "shape": list(shape),
                            "offset_bytes": offset, "nbytes": len(part), "units": units})
        parts.append(part)
        offset += len(part)
    header = {"protocol_version": PROTOCOL_VERSION, "message_type": "two_path_result",
              "request_id": request_id, "experiment_sha256": experiment_digest(experiment),
              "experiment": experiment, "ports": ["port_0", "port_1"],
              "norms": norm_records(result), "diagnostics": diagnostics(result),
              "arrays": descriptors,
              "intensity_max": [float(np.max(values)) for values in intensities]}
    encoded = _json(header)
    if len(encoded) > MAX_HEADER_BYTES:
        raise ValueError("result header exceeds V2b byte limit")
    padding = b"\0" * (-len(encoded) % 8)
    if PREAMBLE.size + len(encoded) + len(padding) + offset > MAX_RESPONSE_BYTES:
        raise ValueError("result frame exceeds V2b byte limit")
    return b"".join((PREAMBLE.pack(MAGIC, len(encoded), 0), encoded, padding, *parts))


def row_from_result(index: int, phase_rad: float, result: TwoArmResult) -> dict[str, object]:
    """Extract one actual sweep measurement, without retaining output arrays."""
    norms = result.norms
    return {"index": index, "phase_rad": phase_rad, "input_norm": norms.inputs_total,
            "output_norms": list(norms.outputs), "output_fractions": list(norms.output_fractions),
            "total_output_ratio": norms.total_output_ratio,
            "split_delta": norms.split_delta, "propagation_delta": norms.propagation_delta,
            "phase_delta": norms.phase_delta, "recombination_delta": norms.recombination_delta,
            "total_delta": norms.total_delta}


@dataclass(frozen=True, kw_only=True)
class SweepReply:
    """Already encoded bounded scalar reply; gate includes encoding lifetime."""

    status_code: int
    body: bytes


def encode_sweep_reply(request_id: str, fixed_experiment: dict[str, object],
                       phases_rad: tuple[float, ...], rows: list[dict[str, object]], *,
                       failed_index: int | None = None,
                       error: dict[str, str] | None = None,
                       status_code: int = 200) -> SweepReply:
    """Encode complete rows or an explicitly failed genuine contiguous prefix."""
    validate_request_id(request_id)
    failed = failed_index is not None
    if len(phases_rad) != 17 or len(rows) > 17:
        raise ValueError("sweep: expected exactly 17 requested phases and at most 17 rows")
    if failed:
        if (type(failed_index) is not int or failed_index != len(rows) or
                not 0 <= failed_index < 17 or status_code not in (422, 500) or
                error is None or set(error) != {"code", "message"}):
            raise ValueError("failed sweep: inconsistent prefix, error or status")
        if (not isinstance(error["code"], str) or not 1 <= len(error["code"]) <= 64 or
                not isinstance(error["message"], str) or not 1 <= len(error["message"]) <= 300):
            raise ValueError("failed sweep: bounded code/message required")
    elif len(rows) != 17 or error is not None or status_code != 200:
        raise ValueError("complete sweep: all 17 genuine rows required")
    for index, row in enumerate(rows):
        if row.get("index") != index or row.get("phase_rad") != phases_rad[index]:
            raise ValueError("sweep rows: expected contiguous requested phases")
    value = {"protocol_version": PROTOCOL_VERSION, "message_type": "two_path_sweep_result",
             "request_id": request_id,
             "fixed_experiment_sha256": sweep_digest(fixed_experiment, phases_rad),
             "fixed_experiment": fixed_experiment, "phases_rad": list(phases_rad),
             "status": "failed" if failed else "complete", "requested_count": 17,
             "completed_count": len(rows), "failed_index": failed_index,
             "rows": rows, "error": error}
    encoded = _json(value)
    if len(encoded) > MAX_SWEEP_RESPONSE_BYTES:
        raise ValueError("sweep response exceeds V2b byte limit")
    return SweepReply(status_code=status_code, body=encoded)
