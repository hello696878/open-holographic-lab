"""Closed A settings, one real core call, and complete mask/readout identity."""

import copy
import json
import math

import numpy as np
import pytest

from apps.virtual_bench import r03_fig2a_adapter as adapter
from apps.virtual_bench import r03_fig2a_protocol as protocol
from ohlab.optics.r03_fig2a import run_ideal_polarization

REQUEST_ID = "d6287710-887b-4fa0-8de2-1f6c174a912d"


def experiment(**changes):
    return {"schema_version": 1, "model_contract": protocol.MODEL_CONTRACT,
        "source_amplitude": 1.0, "mean_phase_rad": math.pi, "phase_std_rad": 1.2,
        "qwp_angle_rad": 0.0, "hwp_angle_rad": 0.0, "seed": 20261017, **changes}


def envelope(*, digested=False, **changes):
    value = {"protocol_version": 1, "message_type": "r03_ideal_submission", "request_id": REQUEST_ID,
             "experiment": experiment(**changes), "experiment_sha256": None}
    if digested:
        value["experiment_sha256"] = adapter.validate_submission(value, require_digest=False).experiment_sha256
    return value


def result(**changes):
    return json.loads(adapter.simulate_submission(adapter.validate_submission(envelope(digested=True, **changes))))


def test_validation_allocates_no_randomness_or_computation_and_owns_complete_settings(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("noncomputing validation performed numerical work")
    monkeypatch.setattr(adapter, "run_ideal_polarization", forbidden)
    monkeypatch.setattr(np.random, "default_rng", forbidden)
    value = envelope(source_amplitude=2, mean_phase_rad=-0.0)
    validated = adapter.validate_submission(value, require_digest=False)
    assert validated.experiment_dict()["mean_phase_rad"] == 0.0
    assert math.copysign(1, validated.experiment_dict()["mean_phase_rad"]) == 1
    assert type(validated.experiment_dict()["source_amplitude"]) is float
    value["experiment"]["source_amplitude"] = 99
    exported = validated.experiment_dict()
    exported["seed"] = 0
    assert validated.spec.amplitude == 2 and validated.spec.seed == 20261017
    assert validated.experiment_sha256 == protocol.experiment_digest(validated.experiment_dict())


def test_one_public_run_encodes_exact_phase_and_all_four_actual_measurements(monkeypatch):
    original = adapter.run_ideal_polarization
    calls = []
    def run(spec):
        calls.append(spec)
        return original(spec)
    monkeypatch.setattr(adapter, "run_ideal_polarization", run)
    submission = adapter.validate_submission(envelope(digested=True, source_amplitude=2.5,
        mean_phase_rad=-1.1, phase_std_rad=2.1, qwp_angle_rad=.34, hwp_angle_rad=-.12, seed=17))
    body = adapter.simulate_submission(submission)
    assert len(calls) == 1, "R03_ONE_REALIZATION_DETECTED"
    actual, direct = json.loads(body), run_ideal_polarization(submission.spec)
    assert set(actual) == {"protocol_version", "message_type", "request_id", "experiment_sha256",
        "experiment", "phase", "stages", "population", "provenance", "limitations"}
    assert actual["experiment"] == submission.experiment_dict()
    assert actual["experiment_sha256"] == submission.experiment_sha256
    assert actual["request_id"] == submission.request_id
    np.testing.assert_array_equal(actual["phase"]["unwrapped_rad"], direct.phase_unwrapped_rad.ravel(order="C"))
    np.testing.assert_array_equal(actual["phase"]["wrapped_rad"], direct.phase_wrapped_rad.ravel(order="C"))
    for record, measured in zip(actual["stages"], (direct.source, direct.after_slm, direct.after_qwp, direct.output)):
        matrix = np.array([[complex(pair["re"], pair["im"]) for pair in row] for row in record["coherency"]])
        np.testing.assert_array_equal(matrix, measured.coherency)
        assert record["stokes"] == list(measured.stokes)
        assert record["degree_of_polarization"] == measured.degree_of_polarization
        assert record["roundoff_limited"] == measured.roundoff_limited
    assert actual["population"]["infinite_gaussian_degree_of_polarization"] == direct.population_dop
    assert len(body) <= protocol.MAX_RESPONSE_BYTES
    assert actual["provenance"]["units"] == protocol.UNITS
    assert actual["provenance"]["rng_algorithm"] == "PCG64"
    assert "independent theoretical model" in actual["provenance"]["identity"]


def test_dark_source_keeps_actual_phase_but_null_optical_normalization():
    actual = result(source_amplitude=0.0)
    assert len(actual["phase"]["wrapped_rad"]) == 256
    assert actual["population"]["infinite_gaussian_degree_of_polarization"] is None
    for record in actual["stages"]:
        assert record["stokes"] == [0.0] * 4
        assert record["degree_of_polarization"] is None
        assert record["normalized_stokes"] is None and record["polarized_direction"] is None


@pytest.mark.parametrize("name,value", [
    ("source_amplitude", -1), ("source_amplitude", 1e6 + 1), ("source_amplitude", True),
    ("mean_phase_rad", 2 * math.pi + .001), ("phase_std_rad", -.1), ("phase_std_rad", math.pi + .001),
    ("qwp_angle_rad", float("nan")), ("hwp_angle_rad", "0"), ("seed", True),
    ("seed", -1), ("seed", 2**32), ("seed", 1.0), ("schema_version", True),
    ("model_contract", "v2d_ideal_jones_same_plane_v1"),
])
def test_closed_invalid_scalar_domains_before_worker(name, value):
    with pytest.raises((TypeError, ValueError, OverflowError)):
        adapter.validate_submission(envelope(**{name: value}), require_digest=False)


def test_digest_uuid_versions_and_cross_mode_envelopes_are_closed():
    initial = envelope()
    with pytest.raises(ValueError):
        adapter.validate_submission(initial)
    validated = envelope(digested=True)
    with pytest.raises(ValueError):
        adapter.validate_submission(validated, require_digest=False)
    for key, value in (("protocol_version", True), ("request_id", REQUEST_ID.upper()),
                       ("message_type", "polarization_submission"), ("unknown", 1)):
        bad = copy.deepcopy(initial); bad[key] = value
        with pytest.raises((TypeError, ValueError)):
            adapter.validate_submission(bad, require_digest=False)
    bad = envelope(digested=True)
    bad["experiment"]["seed"] += 1
    with pytest.raises(ValueError, match="digest"):
        adapter.validate_submission(bad)
    bad = envelope(); bad["experiment"]["distribution"] = "uniform"
    with pytest.raises(ValueError):
        adapter.validate_submission(bad, require_digest=False)


def test_numerical_failure_and_encoding_failure_are_distinct(monkeypatch):
    submission = adapter.validate_submission(envelope(digested=True))
    def numerical(*args):
        raise ValueError("controlled core arithmetic")
    with monkeypatch.context() as patch:
        patch.setattr(adapter, "run_ideal_polarization", numerical)
        with pytest.raises(adapter.NumericalError, match="controlled core arithmetic"):
            adapter.simulate_submission(submission)
    def encoding(*args, **kwargs):
        raise ValueError("controlled serializer")
    monkeypatch.setattr(adapter, "encode_result", encoding)
    with pytest.raises(ValueError, match="controlled serializer"):
        adapter.simulate_submission(submission)
