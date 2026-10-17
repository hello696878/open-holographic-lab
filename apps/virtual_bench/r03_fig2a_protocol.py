"""Closed bounded JSON transport for the independent ideal ensemble workspace.

This module validates transport structure; it performs no optical calculation,
array generation, data import, or conversion of experimental measurements.
"""

from __future__ import annotations

import hashlib
import json
import math
import uuid

PROTOCOL_VERSION = 1
MODEL_CONTRACT = "r03_ideal_statistical_polarization_v1"
MAX_BODY_BYTES = 32_768
MAX_RESPONSE_BYTES = 131_072
STAGE_IDS = ("source", "after_slm", "after_qwp", "output")
UNITS = {
    "phase": "rad", "coherency": "amplitude_unit^2", "stokes": "amplitude_unit^2",
    "normalized_stokes": "dimensionless", "polarized_direction": "dimensionless",
    "degree_of_polarization": "dimensionless", "eigenvalues": "amplitude_unit^2",
}
POPULATION_ASSUMPTION = (
    "Infinite iid Gaussian phases under the declared probability-mean second-moment model."
)
LIMITATIONS = (
    "Independent theoretical model; no Figure 2a experimental agreement is established.",
    "Functional apparatus schematic; no physical propagation, finite-aperture collection or PAX response is calculated.",
    "Finite realization and infinite-ensemble expectation are distinct; no experimental uncertainty estimate is supplied.",
    "RNG traceability is limited to the tested platform and library versions.",
)


def validate_request_id(value: object) -> str:
    """Require a canonical lowercase UUIDv4 temporary operation identity."""
    if type(value) is not str:
        raise TypeError("request_id: expected canonical UUIDv4 string")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ValueError("request_id: expected canonical UUIDv4 string") from exc
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError("request_id: expected canonical lowercase UUIDv4 string")
    return value


def json_bytes(value: object, *, canonical: bool = False) -> bytes:
    """Encode strict compact ASCII JSON without lossy float formatting."""
    return json.dumps(value, sort_keys=canonical, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def experiment_digest(experiment: dict[str, object]) -> str:
    """Hash the complete validated settings, without sampling an ensemble."""
    if type(experiment) is not dict:
        raise TypeError("experiment: expected plain dictionary")
    return hashlib.sha256(json_bytes(experiment, canonical=True)).hexdigest()


def strict_json_loads(data: bytes) -> object:
    """Parse bounded UTF-8 JSON, rejecting duplicates and binary64 underflow."""
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


def _keys(value: object, names: set[str], label: str) -> dict:
    if type(value) is not dict:
        raise TypeError(f"{label}: expected plain object")
    if set(value) != names:
        raise ValueError(f"{label}: expected exactly {sorted(names)}")
    return value


def _real(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise TypeError(f"{label}: expected finite real excluding bool")
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{label}: expected finite binary64") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label}: expected finite binary64")
    return result


def _vector(value: object, size: int, label: str, *, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    if type(value) is not list or len(value) != size:
        raise ValueError(f"{label}: expected list with exactly {size} values")
    for index, item in enumerate(value):
        _real(item, f"{label}[{index}]")


def _measurement(value: object, stage_id: str) -> None:
    record = _keys(value, {"id", "coherency", "stokes", "normalized_stokes", "polarized_direction",
                          "degree_of_polarization", "eigenvalues", "roundoff_limited"}, "stage")
    if record["id"] != stage_id:
        raise ValueError("stages: expected all four ordered algebraic stage IDs")
    coherency = record["coherency"]
    if type(coherency) is not list or len(coherency) != 2:
        raise ValueError("coherency: expected two-by-two complex matrix")
    for row in coherency:
        if type(row) is not list or len(row) != 2:
            raise ValueError("coherency: expected two-by-two complex matrix")
        for element in row:
            pair = _keys(element, {"re", "im"}, "coherency element")
            _real(pair["re"], "coherency.re")
            _real(pair["im"], "coherency.im")
    _vector(record["stokes"], 4, "stokes")
    _vector(record["normalized_stokes"], 3, "normalized_stokes", nullable=True)
    _vector(record["polarized_direction"], 3, "polarized_direction", nullable=True)
    _vector(record["eigenvalues"], 2, "eigenvalues")
    if record["degree_of_polarization"] is not None:
        _real(record["degree_of_polarization"], "degree_of_polarization")
    if type(record["roundoff_limited"]) is not bool:
        raise TypeError("roundoff_limited: expected bool")
    if record["stokes"][0] == 0 and any(record[name] is not None for name in
            ("normalized_stokes", "polarized_direction", "degree_of_polarization")):
        raise ValueError("dark stage: undefined normalized values must be null")


def encode_result(request_id: str, experiment: dict[str, object], *, phase: dict,
                  stages: list[dict], population_dop: float | None,
                  provenance: dict[str, object]) -> bytes:
    """Encode one finite result and its separately labelled population value.

Matrix/Stokes/eigenvalue units are amplitude-unit squared; phase is radians.
Values come from the one public core result and are never recomputed here.
"""
    validate_request_id(request_id)
    _keys(phase, {"shape", "order", "unwrapped_rad", "wrapped_rad"}, "phase")
    if (type(phase["shape"]) is not list or phase["shape"] != [16, 16]
            or any(type(count) is not int for count in phase["shape"]) or phase["order"] != "C"):
        raise ValueError("phase: expected fixed 16-by-16 C-order sample identity")
    _vector(phase["unwrapped_rad"], 256, "phase.unwrapped_rad")
    _vector(phase["wrapped_rad"], 256, "phase.wrapped_rad")
    if type(stages) is not list or len(stages) != 4:
        raise ValueError("stages: expected exactly four finite measurements")
    for record, stage_id in zip(stages, STAGE_IDS):
        _measurement(record, stage_id)
    if population_dop is not None:
        _real(population_dop, "population_dop")
    _keys(provenance, {"model_contract", "identity", "rng_algorithm", "rng_normal_sampler",
          "rng_draw_shape", "sample_order", "sample_count", "probability_weight", "measurement",
          "source", "element_order", "units", "python_version", "numpy_version"}, "provenance")
    if (provenance["model_contract"] != MODEL_CONTRACT or provenance["rng_algorithm"] != "PCG64"
            or provenance["rng_normal_sampler"] != "Generator.standard_normal"
            or provenance["rng_draw_shape"] != [16, 16] or provenance["sample_order"] != "C"
            or type(provenance["sample_count"]) is not int or provenance["sample_count"] != 256
            or provenance["probability_weight"] != 1 / 256
            or provenance["measurement"] != "probability_mean_uncentered_second_moment"
            or provenance["source"] != "amplitude*(1,1)/sqrt(2)"
            or provenance["element_order"] != ["SLM", "QWP", "HWP"] or provenance["units"] != UNITS):
        raise ValueError("provenance: inconsistent frozen ideal model metadata")
    if provenance["identity"] != "Ideal statistical polarization — independent theoretical model":
        raise ValueError("provenance.identity: expected independent theoretical model identity")
    for name in ("python_version", "numpy_version"):
        if type(provenance[name]) is not str or not 1 <= len(provenance[name]) <= 64:
            raise ValueError(f"provenance.{name}: expected bounded version string")
    value = {"protocol_version": 1, "message_type": "r03_ideal_result", "request_id": request_id,
             "experiment_sha256": experiment_digest(experiment), "experiment": experiment,
             "phase": phase, "stages": stages,
             "population": {"infinite_gaussian_degree_of_polarization": population_dop,
                            "assumption": POPULATION_ASSUMPTION},
             "provenance": provenance, "limitations": list(LIMITATIONS)}
    encoded = json_bytes(value)
    if len(encoded) > MAX_RESPONSE_BYTES:
        raise ValueError("result exceeds 131072-byte ideal workspace response limit")
    return encoded
