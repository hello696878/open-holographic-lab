"""V0 strict schema, SI domains, ordered positions and immutable ownership."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from types import MappingProxyType

import numpy as np
import pytest

from ohlab import SamplingGrid
from ohlab.optics import (CircularAperture, GaussianSource, ObservationPlane,
                         RectangularAperture, SequentialExperiment, ThinLens,
                         UniformSource)


def spec():
    return {"schema_version": 1, "model_contract": "v0_aligned_scalar_forward_v1",
            "wavelength_m": 633e-9, "grid": {"ny": 5, "nx": 7, "dy": 20e-6, "dx": 10e-6},
            "source": {"kind": "gaussian", "amplitude": 2.0, "phase_rad": 0.4,
                       "waist_radius_m": 100e-6, "waist_z_m": -0.003,
                       "center_x_m": 7e-6, "center_y_m": -9e-6},
            "components": [{"kind": "circular_aperture", "id": "stop", "z_m": 0.001,
                            "radius_m": 20e-6},
                           {"kind": "thin_lens", "id": "lens", "z_m": 0.001,
                            "focal_length_m": -0.02}],
            "observation": {"id": "detector", "z_m": 0.004}}


def test_exact_schema_roundtrip_owned_export_and_frozen_nested_records():
    original = spec()
    expected = deepcopy(original)
    experiment = SequentialExperiment.from_dict(MappingProxyType(original))
    assert experiment.to_dict() == expected
    assert isinstance(experiment.components, tuple)
    original["source"]["amplitude"] = 42
    original["components"][0]["radius_m"] = 99
    original["grid"]["nx"] = 1
    exported = experiment.to_dict()
    exported["components"].clear()
    exported["source"]["phase_rad"] = 99
    assert experiment.to_dict() == expected
    assert SequentialExperiment.from_dict(experiment.to_dict()) == experiment
    for record, attribute in [(experiment, "source"), (experiment.source, "amplitude"),
                              (experiment.components[0], "radius_m"),
                              (experiment.observation, "z_m")]:
        with pytest.raises(FrozenInstanceError):
            setattr(record, attribute, 0)


def test_constructor_owns_component_list_and_normalizes_numpy_scalars():
    components = [CircularAperture(id="a", z_m=np.float64(0), radius_m=np.float32(1e-5))]
    experiment = SequentialExperiment(wavelength_m=np.float64(633e-9),
                                     grid=SamplingGrid(ny=3, nx=4, dy=2e-6, dx=3e-6),
                                     source=UniformSource(amplitude=np.int64(2), phase_rad=np.float32(0.2)),
                                     components=components, observation=ObservationPlane(id="o", z_m=np.int64(0)),
                                     schema_version=np.int32(1))
    components.clear()
    assert len(experiment.components) == 1
    assert type(experiment.source.amplitude) is float
    assert type(experiment.schema_version) is int
    assert type(experiment.to_dict()["components"][0]["radius_m"]) is float


@pytest.mark.parametrize("section", [None, "grid", "source", "observation", "component"])
@pytest.mark.parametrize("change", ["missing", "unknown"])
def test_unknown_and_missing_keys_rejected(section, change):
    value = spec()
    mapping = value if section is None else value["components"][0] if section == "component" else value[section]
    if change == "unknown":
        mapping["unexpected"] = 0
    else:
        del mapping[next(iter(mapping))]
    with pytest.raises(ValueError, match="missing|unknown|tag"):
        SequentialExperiment.from_dict(value)


@pytest.mark.parametrize("value", [True, np.bool_(False), 1+0j, "2", np.array(2), None])
def test_real_scalar_kind_errors(value):
    with pytest.raises(TypeError, match="amplitude"):
        UniformSource(amplitude=value, phase_rad=0)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), 10**1000])
def test_nonfinite_or_unrepresentable_real_rejected(value):
    with pytest.raises(ValueError, match="amplitude"):
        UniformSource(amplitude=value, phase_rad=0)


@pytest.mark.parametrize("key,value,error", [("schema_version", True, TypeError),
                                           ("schema_version", np.bool_(True), TypeError),
                                           ("schema_version", 1.0, TypeError),
                                           ("schema_version", 2, ValueError),
                                           ("model_contract", 1, TypeError),
                                           ("model_contract", "future", ValueError),
                                           ("wavelength_m", 0, ValueError),
                                           ("wavelength_m", -633e-9, ValueError)])
def test_root_version_and_physical_domain(key, value, error):
    definition = spec()
    definition[key] = value
    with pytest.raises(error, match=key):
        SequentialExperiment.from_dict(definition)


@pytest.mark.parametrize("count,error", [(True, TypeError), (np.bool_(True), TypeError),
                                       (4.0, TypeError), (0, ValueError), (-1, ValueError),
                                       (2049, ValueError)])
def test_grid_count_type_domain_and_limit(count, error):
    definition = spec()
    definition["grid"]["nx"] = count
    with pytest.raises(error, match="nx"):
        SequentialExperiment.from_dict(definition)


@pytest.mark.parametrize("identifier,error", [("source", ValueError), ("", ValueError),
                                            ("1first", ValueError), ("a b", ValueError),
                                            ("光", ValueError), ("a"*65, ValueError),
                                            (1, TypeError)])
def test_identity_errors(identifier, error):
    with pytest.raises(error, match="id"):
        ObservationPlane(id=identifier, z_m=0)


def test_identity_bounds_and_unique_components_observation():
    assert ObservationPlane(id="A" + "_"*63, z_m=0).id.endswith("_")
    value = spec()
    value["components"][1]["id"] = value["components"][0]["id"]
    with pytest.raises(ValueError, match="duplicate"):
        SequentialExperiment.from_dict(value)
    value = spec()
    value["observation"]["id"] = value["components"][0]["id"]
    with pytest.raises(ValueError, match="duplicate"):
        SequentialExperiment.from_dict(value)


def test_order_is_not_sorted_and_colocated_list_order_retained():
    definition = spec()
    experiment = SequentialExperiment.from_dict(definition)
    assert [item.id for item in experiment.components] == ["stop", "lens"]
    definition["components"][1]["z_m"] = 0
    with pytest.raises(ValueError, match="previous"):
        SequentialExperiment.from_dict(definition)
    definition = spec()
    definition["observation"]["z_m"] = 0
    with pytest.raises(ValueError, match="last component"):
        SequentialExperiment.from_dict(definition)


@pytest.mark.parametrize("section,kind,error", [("source", "image_gaussian", ValueError),
                                              ("source", 1, TypeError),
                                              ("component", "mirror", ValueError),
                                              ("component", False, TypeError)])
def test_unsupported_tags(section, kind, error):
    definition = spec()
    mapping = definition["source"] if section == "source" else definition["components"][0]
    mapping["kind"] = kind
    with pytest.raises(error, match="kind"):
        SequentialExperiment.from_dict(definition)


@pytest.mark.parametrize("value", [None, "components", {}, iter([])])
def test_components_container_kind(value):
    definition = spec()
    definition["components"] = value
    with pytest.raises(TypeError, match="components"):
        SequentialExperiment.from_dict(definition)


def test_component_count_limit_and_exact_maximum():
    definition = spec()
    definition["components"] = [{"kind": "thin_lens", "id": f"l{i}", "z_m": 0,
                                 "focal_length_m": 0.02} for i in range(16)]
    assert len(SequentialExperiment.from_dict(definition).components) == 16
    definition["components"].append({"kind": "thin_lens", "id": "last", "z_m": 0,
                                     "focal_length_m": 0.02})
    with pytest.raises(ValueError, match="at most 16"):
        SequentialExperiment.from_dict(definition)


def test_component_limit_rejected_before_parsing_contents():
    definition = spec()
    definition["components"] = [None]*17
    with pytest.raises(ValueError, match="at most 16"):
        SequentialExperiment.from_dict(definition)


def test_geometry_underflow_is_not_suppressed_for_a_dark_gaussian():
    definition = spec()
    definition["source"].update(amplitude=0, waist_z_m=5e-324)
    with pytest.raises(ValueError, match="derived geometry"):
        SequentialExperiment.from_dict(definition)


@pytest.mark.parametrize("factory,parameters", [
    (UniformSource, {"amplitude": -1, "phase_rad": 0}),
    (GaussianSource, {"amplitude": 0, "phase_rad": 0, "waist_radius_m": 0,
                      "waist_z_m": 0, "center_x_m": 0, "center_y_m": 0}),
    (CircularAperture, {"id": "a", "z_m": 0, "radius_m": 0}),
    (RectangularAperture, {"id": "a", "z_m": 0, "width_m": 1e-5, "height_m": 0}),
    (ThinLens, {"id": "a", "z_m": 0, "focal_length_m": 0}),
    (ObservationPlane, {"id": "o", "z_m": -1}),
])
def test_record_physical_domains(factory, parameters):
    with pytest.raises(ValueError):
        factory(**parameters)


@pytest.mark.parametrize("changes", [
    {"source": {"waist_radius_m": 1e-300}},
    {"source": {"center_x_m": 1e300}},
    {"source": {"waist_z_m": 1e308}},
    {"grid": {"dx": 1e300}},
    {"grid": {"dx": 1e-300}},
    {"wavelength_m": 1e-300},
    {"observation": {"z_m": 1e308}},
])
def test_unusable_derived_geometry_rejected_even_with_zero_amplitude(changes):
    definition = spec()
    definition["source"]["amplitude"] = 0
    for key, value in changes.items():
        if isinstance(value, dict):
            definition[key].update(value)
        else:
            definition[key] = value
    with pytest.raises(ValueError, match="derived geometry"):
        SequentialExperiment.from_dict(definition)


def test_signed_focal_lengths_and_signed_source_positions_allowed():
    for focal in (-0.02, 0.02):
        assert ThinLens(id="l", z_m=0, focal_length_m=focal).focal_length_m == focal
    for waist_z in (-0.01, 0, 0.01):
        source = GaussianSource(amplitude=0, phase_rad=-0.7, waist_radius_m=100e-6,
                                waist_z_m=waist_z, center_x_m=-1e-5, center_y_m=2e-5)
        assert source.waist_z_m == waist_z


def test_nonmapping_and_nonstring_keys_fail_informatively():
    with pytest.raises(TypeError, match="Mapping"):
        SequentialExperiment.from_dict([])
    value = spec()
    value[1] = "bad"
    with pytest.raises(TypeError, match="string keys"):
        SequentialExperiment.from_dict(value)


def test_cyclic_cutoff_squared_must_not_underflow_even_if_k_squared_nonzero():
    value = spec()
    value["wavelength_m"] = 1e162
    value["source"] = {"kind": "uniform", "amplitude": 0, "phase_rad": 0}
    assert (2*np.pi/1e162)**2 > 0 and (1/1e162)**2 == 0
    with pytest.raises(ValueError, match="cutoff squared"):
        SequentialExperiment.from_dict(value)
