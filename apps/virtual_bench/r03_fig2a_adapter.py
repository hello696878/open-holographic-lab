"""Single public ideal-ensemble call and owned settings for research workspace A.

No experimental arrays, PAX transforms, I/O, propagation, sweep, or replacement
statistical equations belong in this application adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import platform

from numpy import __version__ as numpy_version

from ohlab.optics.r03_fig2a import (IdealPolarizationResult, IdealPolarizationSpec,
                                   run_ideal_polarization)

from .adapter import NumericalError
from .r03_fig2a_protocol import (MODEL_CONTRACT, STAGE_IDS, UNITS, encode_result,
                                 experiment_digest, validate_request_id)

_EXPERIMENT_KEYS = {"schema_version", "model_contract", "source_amplitude", "mean_phase_rad",
                    "phase_std_rad", "qwp_angle_rad", "hwp_angle_rad", "seed"}


def _keys(value: object, expected: set[str], name: str) -> dict:
    if type(value) is not dict:
        raise TypeError(f"{name}: expected plain JSON object")
    if set(value) != expected:
        raise ValueError(f"{name}: expected exactly {sorted(expected)}")
    return value


def experiment_dict(spec: IdealPolarizationSpec) -> dict[str, object]:
    """Return fresh complete settings with canonical real binary64 values."""
    if type(spec) is not IdealPolarizationSpec:
        raise TypeError("spec: expected IdealPolarizationSpec")
    values = {"source_amplitude": spec.amplitude, "mean_phase_rad": spec.mean_phase_rad,
              "phase_std_rad": spec.phase_std_rad, "qwp_angle_rad": spec.qwp_angle_rad,
              "hwp_angle_rad": spec.hwp_angle_rad}
    canonical = {name: 0.0 if value == 0 else float(value) for name, value in values.items()}
    return {"schema_version": 1, "model_contract": MODEL_CONTRACT, **canonical, "seed": spec.seed}


def validate_experiment(value: object) -> IdealPolarizationSpec:
    """Validate scalar settings without generating samples or running a worker."""
    record = _keys(value, _EXPERIMENT_KEYS, "experiment")
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        raise ValueError("schema_version: expected integer 1")
    if record["model_contract"] != MODEL_CONTRACT:
        raise ValueError(f"model_contract: expected {MODEL_CONTRACT}")
    return IdealPolarizationSpec(amplitude=record["source_amplitude"],
        mean_phase_rad=record["mean_phase_rad"], phase_std_rad=record["phase_std_rad"],
        qwp_angle_rad=record["qwp_angle_rad"], hwp_angle_rad=record["hwp_angle_rad"], seed=record["seed"])


@dataclass(frozen=True, kw_only=True)
class ValidatedIdealSubmission:
    """Immutable complete settings/seed identity; no numerical allocation."""

    request_id: str
    spec: IdealPolarizationSpec
    experiment_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        validate_request_id(self.request_id)
        if type(self.spec) is not IdealPolarizationSpec:
            raise TypeError("spec: expected IdealPolarizationSpec")
        owned = validate_experiment(experiment_dict(self.spec))
        object.__setattr__(self, "spec", owned)
        object.__setattr__(self, "experiment_sha256", experiment_digest(experiment_dict(owned)))

    def experiment_dict(self) -> dict[str, object]:
        """Export independent scalar settings without exposing owned state."""
        return experiment_dict(self.spec)


def validate_submission(payload: object, *, require_digest: bool = True) -> ValidatedIdealSubmission:
    """Require the exact independent contract, UUID and complete settings digest."""
    value = _keys(payload, {"protocol_version", "message_type", "request_id", "experiment",
                            "experiment_sha256"}, "submission")
    if type(value["protocol_version"]) is not int or value["protocol_version"] != 1:
        raise ValueError("protocol_version: expected integer 1")
    if value["message_type"] != "r03_ideal_submission":
        raise ValueError("message_type: expected r03_ideal_submission")
    submission = ValidatedIdealSubmission(request_id=value["request_id"],
                                           spec=validate_experiment(value["experiment"]))
    digest = value["experiment_sha256"]
    if require_digest:
        if type(digest) is not str or digest != submission.experiment_sha256:
            raise ValueError("digest: compute requires matching complete validated settings SHA")
    elif digest is not None:
        raise ValueError("digest: noncomputing validation requires null")
    return submission


def _measurement_record(measurement, stage_id: str) -> dict[str, object]:
    return {"id": stage_id,
        "coherency": [[{"re": float(value.real), "im": float(value.imag)} for value in row]
                       for row in measurement.coherency],
        "stokes": list(measurement.stokes),
        "normalized_stokes": None if measurement.normalized_stokes is None else list(measurement.normalized_stokes),
        "polarized_direction": None if measurement.polarized_direction is None else list(measurement.polarized_direction),
        "degree_of_polarization": measurement.degree_of_polarization,
        "eigenvalues": list(measurement.eigenvalues), "roundoff_limited": measurement.roundoff_limited}


def simulate_submission(submission: ValidatedIdealSubmission) -> bytes:
    """Run one public finite ensemble and encode its actual mask and measurements."""
    if type(submission) is not ValidatedIdealSubmission:
        raise TypeError("submission: expected ValidatedIdealSubmission")
    try:
        result = run_ideal_polarization(submission.spec)
        if type(result) is not IdealPolarizationResult or result.spec != submission.spec:
            raise ValueError("public result: immutable submitted settings mismatch")
        if (result.model_contract != MODEL_CONTRACT or result.rng_algorithm != "PCG64"
                or result.sample_order != "C" or result.sample_shape != (16, 16) or result.sample_count != 256):
            raise ValueError("public result: frozen model/sample identity mismatch")
    except (ValueError, FloatingPointError, OverflowError) as exc:
        raise NumericalError(f"ideal statistical polarization: {exc}") from exc
    phase = {"shape": [16, 16], "order": "C",
             "unwrapped_rad": result.phase_unwrapped_rad.reshape(-1, order="C").tolist(),
             "wrapped_rad": result.phase_wrapped_rad.reshape(-1, order="C").tolist()}
    stages = [_measurement_record(measurement, name) for measurement, name in zip(
        (result.source, result.after_slm, result.after_qwp, result.output), STAGE_IDS)]
    provenance = {"model_contract": MODEL_CONTRACT,
        "identity": "Ideal statistical polarization — independent theoretical model",
        "rng_algorithm": result.rng_algorithm, "rng_normal_sampler": "Generator.standard_normal",
        "rng_draw_shape": [16, 16], "sample_order": result.sample_order,
        "sample_count": result.sample_count, "probability_weight": 1 / 256,
        "measurement": "probability_mean_uncentered_second_moment", "source": "amplitude*(1,1)/sqrt(2)",
        "element_order": ["SLM", "QWP", "HWP"], "units": UNITS.copy(),
        "python_version": platform.python_version(), "numpy_version": numpy_version}
    return encode_result(submission.request_id, submission.experiment_dict(), phase=phase,
        stages=stages, population_dop=result.population_dop, provenance=provenance)
