"""Direct-public transport fidelity and independent bounded Jones regressions."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import math

import numpy as np
import pytest

from apps.virtual_bench import polarization_adapter as adapter
from apps.virtual_bench import polarization_protocol as protocol
from ohlab.optics import sample_source
from ohlab.optics.polarization import (JonesField, apply_linear_polarizer,
                                       apply_linear_retarder, transmission_ratio)
from scripts.validate_v2c_polarization import decimal_near_reference

REQUEST_ID = "cfdccf7d-d8ee-4ad4-b359-9d2d04106747"


def polarizer(identifier="analyzer", angle=.31):
    return {"id": identifier, "kind": "linear_polarizer", "axis_angle_rad": angle}


def retarder(identifier="plate", angle=.19, delta=math.pi / 2):
    return {"id": identifier, "kind": "linear_retarder", "axis_angle_rad": angle, "retardance_rad": delta}


def envelope(*, ny=3, nx=4, gaussian=False, elements=None, coefficients=None, amplitude=1., phase=.17):
    source = {"kind": "uniform", "amplitude": amplitude, "phase_rad": phase}
    if gaussian:
        source.update(kind="gaussian", waist_radius_m=11e-6, center_x_m=2e-6, center_y_m=-1e-6)
    return {"protocol_version": 1, "message_type": "polarization_submission", "request_id": REQUEST_ID,
            "experiment_sha256": None, "experiment": {
                "schema_version": 1, "model_contract": protocol.MODEL_CONTRACT, "wavelength_m": 633e-9,
                "grid": {"ny": ny, "nx": nx, "dy": 4.1e-6, "dx": 3.7e-6}, "source": source,
                "coefficients": coefficients or {"x": {"re": 1., "im": 0.}, "y": {"re": 0., "im": 0.}},
                "elements": [polarizer()] if elements is None else elements,
                "readout": {"row": ny // 2, "column": nx // 2}}}


def digested(value=None):
    value = deepcopy(envelope() if value is None else value)
    value["experiment_sha256"] = adapter.validate_submission(value).experiment_sha256
    return value


def sweep_envelope(value=None, selected="analyzer"):
    value = digested(value)
    value.update(message_type="polarization_sweep_submission", selected_element_id=selected,
                 angles_rad=list(protocol.ANGLES_RAD))
    return value


def unpack(frame):
    magic, length, reserved = protocol.PREAMBLE.unpack_from(frame)
    assert magic == protocol.MAGIC and reserved == 0
    header = json.loads(frame[16:16+length])
    offset = 16 + length + (-length % 8)
    arrays = {item["name"]: np.frombuffer(frame, dtype="<f8", count=item["nbytes"] // 8,
                                         offset=offset+item["offset_bytes"]).reshape(item["shape"])
              for item in header["arrays"]}
    return header, arrays


def output(value):
    return unpack(adapter.simulate_submission(adapter.validate_submission(digested(value), require_digest=True)))


def direct(experiment, angle=None, selected=None):
    incident = JonesField.from_scalar(sample_source(experiment.source_plane),
                      x_coefficient=experiment.coefficients[0], y_coefficient=experiment.coefficients[1])
    fields = [incident]
    for element in experiment.elements:
        axis = angle if element.id == selected else element.axis_angle_rad
        fields.append(apply_linear_polarizer(fields[-1], axis_angle_rad=axis)
                      if element.kind == "linear_polarizer" else
                      apply_linear_retarder(fields[-1], axis_angle_rad=axis, retardance_rad=element.retardance_rad))
    return fields


def sample(record):
    return tuple(complex(record["sample"][name]["re"], record["sample"][name]["im"]) for name in ("x", "y"))


def test_validation_runs_zero_numerical_calls(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("validation reached a numerical sampler/Jones/action/ratio")
    for name in ("sample_source", "apply_linear_polarizer", "apply_linear_retarder", "transmission_ratio"):
        monkeypatch.setattr(adapter, name, forbidden)
    monkeypatch.setattr(adapter.JonesField, "from_scalar", forbidden)
    value = envelope(elements=[polarizer(), retarder()])
    validated = adapter.validate_submission(value)
    assert validated.experiment.source_plane.components == ()
    assert validated.experiment.source_plane.observation.z_m == 0
    assert adapter.validate_sweep_submission(sweep_envelope(value)).angles_rad == protocol.ANGLES_RAD


@pytest.mark.parametrize("gaussian", [False, True])
@pytest.mark.parametrize("elements", [[], [polarizer(), retarder()], [retarder(), polarizer()]])
def test_transport_is_exact_direct_public_data_and_ordered_sample_identity(gaussian, elements):
    value = envelope(gaussian=gaussian, elements=elements,
                     coefficients={"x": {"re": .8, "im": .3}, "y": {"re": -.2, "im": .7}})
    experiment = adapter.validate_submission(value).experiment
    fields = direct(experiment)
    header, arrays = output(value)
    assert header["ordered_stage_ids"] == ["input", *(item["id"] for item in elements)]
    assert header["experiment"] == experiment.to_dict()
    for name, expected in (("incident_intensity", fields[0].intensity), ("final_intensity", fields[-1].intensity),
                           ("x_m", fields[0].grid.x), ("y_m", fields[0].grid.y)):
        np.testing.assert_array_equal(arrays[name], expected)
    assert header["readout"] == {"row": experiment.row, "column": experiment.column,
            "x_m": fields[0].grid.x[experiment.column], "y_m": fields[0].grid.y[experiment.row]}
    for index, (stage, field) in enumerate(zip(header["stages"], fields)):
        assert stage["norm"] == field.sampled_norm
        assert stage["incident_transmission_ratio"] == transmission_ratio(fields[0], field)
        assert sample(stage) == tuple(getattr(field, name).data[experiment.row, experiment.column] for name in ("x", "y"))
        if index:
            assert stage["adjacent_transmission_ratio"] == transmission_ratio(fields[index-1], field)
            assert stage["delta_norm"] == field.sampled_norm - fields[index-1].sampled_norm


def test_single_samples_and_constructs_once_then_exact_element_count(monkeypatch):
    counts = {"sample": 0, "Jones": 0, "elements": 0}
    original_sampler, original_jones = adapter.sample_source, adapter.JonesField.from_scalar
    original_p, original_w = adapter.apply_linear_polarizer, adapter.apply_linear_retarder
    def sampler(experiment):
        counts["sample"] += 1
        return original_sampler(experiment)
    def jones(cls, field, **kwargs):
        counts["Jones"] += 1
        return original_jones(field, **kwargs)
    def action(original):
        def call(field, **kwargs):
            counts["elements"] += 1
            return original(field, **kwargs)
        return call
    monkeypatch.setattr(adapter, "sample_source", sampler)
    monkeypatch.setattr(adapter.JonesField, "from_scalar", classmethod(jones))
    monkeypatch.setattr(adapter, "apply_linear_polarizer", action(original_p))
    monkeypatch.setattr(adapter, "apply_linear_retarder", action(original_w))
    output(envelope(elements=[polarizer("p0"), retarder("w1"), polarizer("p2")]))
    assert counts == {"sample": 1, "Jones": 1, "elements": 3}, "SINGLE_CALL_COUNT_DETECTED"


def test_sweep_104_public_calls_restarts_incident_and_rows_are_actual_full_train(monkeypatch):
    elements = [polarizer(f"p{i}", .13*i) if i % 2 == 0 else retarder(f"w{i}", -.11*i) for i in range(8)]
    submission = adapter.validate_sweep_submission(sweep_envelope(envelope(elements=elements), selected="p2"))
    counts, incidents = {"source": 0, "Jones": 0, "elements": 0}, []
    sampler, jones, run = adapter.sample_source, adapter.JonesField.from_scalar, adapter._run_train
    def source(exp):
        counts["source"] += 1
        return sampler(exp)
    def construct(cls, field, **kwargs):
        counts["Jones"] += 1
        return jones(field, **kwargs)
    def train(incident, experiment, **kwargs):
        incidents.append(incident)
        return run(incident, experiment, **kwargs)
    def wrap(original):
        def call(field, **kwargs):
            counts["elements"] += 1
            return original(field, **kwargs)
        return call
    monkeypatch.setattr(adapter, "sample_source", source)
    monkeypatch.setattr(adapter.JonesField, "from_scalar", classmethod(construct))
    monkeypatch.setattr(adapter, "_run_train", train)
    monkeypatch.setattr(adapter, "apply_linear_polarizer", wrap(adapter.apply_linear_polarizer))
    monkeypatch.setattr(adapter, "apply_linear_retarder", wrap(adapter.apply_linear_retarder))
    reply = adapter.sweep_submission(submission)
    body = json.loads(reply.body)
    assert counts == {"source": 1, "Jones": 1, "elements": 104}, "SWEEP_CALL_COUNT_DETECTED"
    assert len(incidents) == 13 and all(field is incidents[0] for field in incidents), "SWEEP_RESTART_INCIDENT_DETECTED"
    assert len(body["rows"]) == 13 and body["status"] == "complete"
    for index, row in enumerate(body["rows"]):
        fields = direct(submission.experiment, protocol.ANGLES_RAD[index], "p2")
        assert row["index"] == index and row["axis_angle_rad"] == protocol.ANGLES_RAD[index]
        assert row["final_norm"] == fields[-1].sampled_norm, "SWEEP_GENUINE_ROWS_DETECTED"
        assert row["incident_transmission_ratio"] == transmission_ratio(fields[0], fields[-1]), "SWEEP_GENUINE_ROWS_DETECTED"
        assert row["total_delta"] == fields[-1].sampled_norm - fields[0].sampled_norm
        assert all("sample" not in stage for stage in row["stages"])


@pytest.mark.parametrize("failed_index", [0, 3, 12])
@pytest.mark.parametrize("error_type,status", [(ValueError, 422), (RuntimeError, 500)])
def test_failed_sweep_retains_only_genuine_first_interior_last_prefix(monkeypatch, failed_index, error_type, status):
    original, calls = adapter._run_train, []
    def controlled(incident, experiment, **kwargs):
        calls.append(kwargs["axis_angle_rad"])
        if len(calls) == failed_index + 1:
            raise error_type("controlled failure; " + "x"*350)
        return original(incident, experiment, **kwargs)
    monkeypatch.setattr(adapter, "_run_train", controlled)
    reply = adapter.sweep_submission(adapter.validate_sweep_submission(sweep_envelope()))
    value = json.loads(reply.body)
    assert reply.status_code == status and value["status"] == "failed"
    assert value["completed_count"] == value["failed_index"] == failed_index
    assert len(value["rows"]) == failed_index and len(calls) == failed_index + 1, "SWEEP_GENUINE_ROWS_DETECTED"
    assert len(value["error"]["message"]) <= 300
    if status == 500:
        assert "controlled failure" not in value["error"]["message"]


def test_literal_qwp_hwp_order_and_preserved_complex_common_phase():
    a = 1/math.sqrt(2)
    diag = {"x": {"re": a, "im": 0.}, "y": {"re": a, "im": 0.}}
    qwp, arrays = output(envelope(phase=0., coefficients=diag, elements=[retarder(angle=0.)]))
    np.testing.assert_allclose(sample(qwp["stages"][-1]), (a, 1j*a), rtol=2e-14, atol=2e-14,
                               err_msg="COMPLEX_PHASE_DETECTED")
    np.testing.assert_allclose(arrays["incident_intensity"], arrays["final_intensity"], rtol=2e-13, atol=2e-13)
    hwp, _ = output(envelope(phase=0., elements=[retarder(angle=math.pi/8, delta=math.pi)]))
    np.testing.assert_allclose(sample(hwp["stages"][-1]), (a, a), rtol=2e-14, atol=2e-14)
    first, _ = output(envelope(phase=0., elements=[polarizer(angle=math.pi/4), retarder(angle=0.)]))
    reverse, _ = output(envelope(phase=0., elements=[retarder(angle=0.), polarizer(angle=math.pi/4)]))
    np.testing.assert_allclose(sample(first["stages"][-1]), (.5, .5j), rtol=2e-14, atol=2e-14,
                               err_msg="ELEMENT_ORDER_DETECTED")
    np.testing.assert_allclose(sample(reverse["stages"][-1]), (.5, .5), rtol=2e-14, atol=2e-14)
    shifted, _ = output(envelope(phase=math.pi/4, coefficients={"x": {"re": a, "im": 0},
                          "y": {"re": 0, "im": a}}, elements=[]))
    # Independently evaluated shared tau=0 marker: no per-stage phase fitting.
    np.testing.assert_allclose(np.real(sample(shifted["stages"][0])), (.5, -.5), rtol=0, atol=2e-15,
                               err_msg="COMMON_PHASE_RESET_DETECTED")


def test_arbitrary_coefficients_use_jones_denominator_and_actual_loss_and_angle_sign():
    header, _ = output(envelope(phase=0., coefficients={"x": {"re": 2, "im": 0}, "y": {"re": 0, "im": 0}},
                               elements=[polarizer(angle=math.pi/4)]))
    scalar_norm = sample_source(adapter.validate_submission(envelope()).experiment.source_plane).power
    np.testing.assert_allclose(header["stages"][0]["norm"], 4*scalar_norm, rtol=2e-13, atol=2e-13*scalar_norm)
    np.testing.assert_allclose(header["stages"][-1]["incident_transmission_ratio"], .5, rtol=2e-13, atol=2e-13,
                               err_msg="JONES_DENOMINATOR_DETECTED")
    assert header["stages"][-1]["delta_norm"] < 0, "POLARIZER_LOSS_DETECTED"
    positive, _ = output(envelope(phase=0., elements=[polarizer(angle=math.pi/6)]))
    np.testing.assert_allclose(sample(positive["stages"][-1]), (.75, math.sqrt(3)/4), rtol=2e-14, atol=2e-14,
                               err_msg="ANGLE_SIGN_DETECTED")
    triple, _ = output(envelope(phase=0., elements=[polarizer("p0", 0), polarizer("p45", math.pi/4), polarizer("p90", math.pi/2)]))
    np.testing.assert_allclose(triple["stages"][-1]["incident_transmission_ratio"], .25, rtol=2e-13, atol=2e-13)


@pytest.mark.parametrize("offset", [-1e-6, -1e-9, 0., 1e-9, 1e-6])
def test_transported_weak_signals_keep_unchanged_decimal_bounds(offset):
    angle = math.pi/2 + offset
    reference = decimal_near_reference(angle)
    header, arrays = output(envelope(phase=0., elements=[polarizer(angle=angle)]))
    stage = header["stages"][-1]
    np.testing.assert_allclose(sample(stage), (float(reference["x"]), float(reference["y"])), rtol=2e-14, atol=1e-48)
    expected = float(reference["intensity_fraction"])
    np.testing.assert_allclose(arrays["final_intensity"], expected, rtol=2e-14, atol=1e-48)
    np.testing.assert_allclose(stage["incident_transmission_ratio"], expected, rtol=2e-14, atol=1e-48)
    nin = header["stages"][0]["norm"]
    np.testing.assert_allclose(stage["norm"], expected*nin, rtol=2e-14, atol=1e-48*nin)
    assert stage["norm"] > 0 and stage["incident_transmission_ratio"] > 0


@pytest.mark.parametrize("dark", ["source", "coefficients"])
def test_dark_inputs_preserve_exact_zero_and_public_null_ratios(dark):
    value = envelope(elements=[retarder(), polarizer()])
    if dark == "source": value["experiment"]["source"]["amplitude"] = 0.
    else: value["experiment"]["coefficients"] = {name: {"re": 0., "im": 0.} for name in ("x", "y")}
    header, arrays = output(value)
    assert not np.any(arrays["incident_intensity"]) and not np.any(arrays["final_intensity"])
    assert all(stage["incident_transmission_ratio"] is None for stage in header["stages"])
    assert all(sample(stage) == (0j, 0j) for stage in header["stages"])


def test_owned_identity_rejects_wrong_digest_and_preserves_nonzero_angles():
    value = envelope(elements=[polarizer(angle=2*math.pi+.12345678901234567)])
    submission = adapter.validate_submission(value)
    owned = submission.experiment.to_dict()
    value["experiment"]["elements"][0]["axis_angle_rad"] = 17
    value["experiment"]["readout"]["row"] = 0
    assert submission.experiment.to_dict() == owned
    assert owned["elements"][0]["axis_angle_rad"] == 2*math.pi+.12345678901234567
    with pytest.raises(FrozenInstanceError): submission.request_id = "changed"
    with pytest.raises(ValueError, match="requires matching"): adapter.validate_submission(envelope(), require_digest=True)
    value = envelope(); value["experiment_sha256"] = "0"*64
    with pytest.raises(ValueError, match="mismatched"): adapter.validate_submission(value)


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(protocol_version=True), lambda d: d.update(message_type="two_path_submission"),
    lambda d: d.update(extra=0), lambda d: d["experiment"].update(extra=0),
    lambda d: d["experiment"].update(schema_version=True),
    lambda d: d["experiment"]["grid"].update(nx=129), lambda d: d["experiment"]["grid"].update(nx=True),
    lambda d: d["experiment"]["grid"].update(dx=0), lambda d: d["experiment"]["readout"].update(row=-1),
    lambda d: d["experiment"]["readout"].update(column=4), lambda d: d["experiment"]["readout"].update(row=True),
    lambda d: d["experiment"]["source"].update(waist_z_m=0), lambda d: d["experiment"]["source"].update(amplitude=-1),
    lambda d: d["experiment"]["coefficients"]["x"].update(re=True),
    lambda d: d["experiment"]["coefficients"]["y"].update(im=float("nan")),
    lambda d: d["experiment"]["elements"][0].update(axis_angle_rad=float("inf")),
    lambda d: d["experiment"]["elements"][0].update(id="input"),
    lambda d: d["experiment"]["elements"][0].update(id="bad id"),
    lambda d: d["experiment"]["elements"].append(dict(d["experiment"]["elements"][0])),
    lambda d: d["experiment"].update(elements=[polarizer(f"p{i}") for i in range(9)]),
])
def test_invalid_specs_fail_before_sampling(mutation, monkeypatch):
    value = envelope(); mutation(value)
    monkeypatch.setattr(adapter, "sample_source", lambda _: pytest.fail("sampler reached invalid spec"))
    with pytest.raises((ValueError, TypeError, OverflowError)):
        adapter.validate_submission(value)


@pytest.mark.parametrize("selection", ["missing", "plate", "input"])
def test_sweep_selection_requires_existing_polarizer(selection):
    with pytest.raises(ValueError, match="linear polarizer"):
        adapter.validate_sweep_submission(sweep_envelope(envelope(elements=[polarizer(), retarder()]), selected=selection))


def test_empty_identity_valid_but_empty_sweep_invalid():
    header, arrays = output(envelope(elements=[]))
    assert len(header["stages"]) == 1 and header["ordered_stage_ids"] == ["input"]
    np.testing.assert_array_equal(arrays["incident_intensity"], arrays["final_intensity"])
    with pytest.raises(ValueError, match="linear polarizer"):
        adapter.validate_sweep_submission(sweep_envelope(envelope(elements=[])))


def test_direct_record_construction_snapshots_mutable_containers_and_revalidates_domains():
    original = adapter.validate_submission(envelope()).experiment
    coefficients = [1+2j, .3j]
    elements = [adapter.PolarizationElement(id="direct", kind="linear_polarizer", axis_angle_rad=.123)]
    experiment = adapter.PolarizationExperiment(source_plane=original.source_plane,
                       coefficients=coefficients, elements=elements, row=1, column=2)
    submission = adapter.ValidatedPolarizationSubmission(request_id=REQUEST_ID, experiment=experiment)
    saved = submission.experiment.to_dict()
    coefficients[0] = 99j; elements.clear()
    assert submission.experiment.to_dict() == saved
    assert type(submission.experiment.coefficients) is type(submission.experiment.elements) is tuple
    assert submission.experiment.source_plane is not original.source_plane
    for kwargs in ({"coefficients": [True, 0]}, {"coefficients": [float("inf"), 0]},
                   {"elements": [object()]}, {"row": True}, {"column": 4}):
        values = {"source_plane": original.source_plane, "coefficients": [1, 0], "elements": [], "row": 1, "column": 2}
        values.update(kwargs)
        with pytest.raises((TypeError, ValueError)):
            adapter.PolarizationExperiment(**values)
    with pytest.raises(ValueError): adapter.PolarizationElement(id="input", kind="linear_polarizer", axis_angle_rad=0)
    with pytest.raises(TypeError): adapter.PolarizationElement(id="p", kind="linear_polarizer", axis_angle_rad=True)
    with pytest.raises(ValueError): adapter.PolarizationElement(id="p", kind="linear_polarizer", axis_angle_rad=0, retardance_rad=0)
    angles = list(protocol.ANGLES_RAD); angles[6] = False
    with pytest.raises(TypeError):
        adapter.ValidatedPolarizationSweepSubmission(request_id=REQUEST_ID, experiment=original,
                    selected_element_id="analyzer", angles_rad=tuple(angles))


@pytest.mark.parametrize("boundary", ["source", "Jones"])
def test_actual_public_source_or_jones_domain_failure_has_zero_completed_sweep_rows(boundary, monkeypatch):
    value = envelope(gaussian=boundary == "source", amplitude=1e200 if boundary == "Jones" else 1.)
    if boundary == "source":
        value["experiment"]["source"].update(center_x_m=1e-200, center_y_m=0.)
    submission = adapter.validate_submission(digested(value), require_digest=True)
    sweep = adapter.validate_sweep_submission(sweep_envelope(value))
    settings = np.geterr().copy()
    with pytest.raises(adapter.NumericalError): adapter.simulate_submission(submission)
    assert np.geterr() == settings
    counts = {"source": 0, "Jones": 0, "element": 0}
    sampler, construct, action = adapter.sample_source, adapter.JonesField.from_scalar, adapter.apply_linear_polarizer
    def source(experiment):
        counts["source"] += 1
        return sampler(experiment)
    def jones(cls, scalar, **kwargs):
        counts["Jones"] += 1
        return construct(scalar, **kwargs)
    def apply(field, **kwargs):
        counts["element"] += 1
        return action(field, **kwargs)
    monkeypatch.setattr(adapter, "sample_source", source)
    monkeypatch.setattr(adapter.JonesField, "from_scalar", classmethod(jones))
    monkeypatch.setattr(adapter, "apply_linear_polarizer", apply)
    reply = adapter.sweep_submission(sweep)
    failed = json.loads(reply.body)
    assert reply.status_code == 422 and failed["rows"] == []
    assert failed["failed_index"] == failed["completed_count"] == 0
    assert counts == {"source": 1, "Jones": int(boundary == "Jones"), "element": 0}
    assert np.geterr() == settings
