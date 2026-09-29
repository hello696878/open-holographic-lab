"""M5 scientific schema, defensive ownership and exact JSON evidence."""

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import math
import struct
import sys
from types import MappingProxyType

import numpy as np
import pytest

from ohlab.io.config import RunConfig, _json_bytes, _parse_json


def _settings():
    return {
        "schema_version": 1,
        "grid": {"ny": 3, "nx": 5, "dy_m": 10e-6, "dx_m": 8e-6},
        "optics": {"wavelength_m": 633e-9, "distance_m": 2e-4},
        "solver": {
            "algorithm": "gerchberg_saxton",
            "contract": "m3_periodic_lossless_asm_v1",
            "iterations": 5,
            "initialization": {"mode": "seed", "seed": 7},
        },
        "metrics": {
            "intensity_mse": {},
            "intensity_nmse": {},
            "intensity_psnr": {"data_range": 1.0},
            "signal_region_power_fraction": {"mask": "signal_mask.npy"},
            "regional_intensity_cv": {"mask": "cv_mask.npy"},
        },
    }


def _parent(settings, path):
    keys = path.split(".")
    node = settings
    for key in keys[:-1]:
        node = node[key]
    return node, keys[-1]


def _set(settings, path, value):
    parent, key = _parent(settings, path)
    parent[key] = value


def _node(settings, path):
    if not path:
        return settings
    parent, key = _parent(settings, path)
    return parent[key]


def _bits(value):
    return struct.pack(">d", value)


def test_valid_seed_configuration_preserves_full_scientific_specification():
    original = _settings()
    config = RunConfig(original)
    assert config.to_dict() == original
    assert RunConfig(config.to_dict()) == config
    assert hash(RunConfig(config.to_dict())) == hash(config)


def test_explicit_phase_configuration_has_only_its_actual_artifact():
    settings = _settings()
    settings["solver"]["initialization"] = {
        "mode": "explicit_phase", "artifact": "initial_phase.npy",
    }
    result = RunConfig(settings).to_dict()
    assert result["solver"]["initialization"] == settings["solver"]["initialization"]
    assert "seed" not in result["solver"]["initialization"]


@pytest.mark.parametrize("names", [[], ["intensity_mse"], ["intensity_psnr"],
                                  ["signal_region_power_fraction", "regional_intensity_cv"]])
def test_metric_selection_is_an_explicit_subset_including_empty(names):
    settings = _settings()
    settings["metrics"] = {name: settings["metrics"][name] for name in names}
    assert RunConfig(settings).to_dict()["metrics"] == settings["metrics"]


def test_nested_mappings_are_supported_without_exposing_mutable_storage():
    def freeze(value):
        return MappingProxyType({key: freeze(item) if isinstance(item, Mapping) else item
                                 for key, item in value.items()})
    expected = _settings()
    config = RunConfig(freeze(expected))
    assert config.to_dict() == expected
    assert type(config._document) is bytes
    assert not hasattr(config, "__dict__")
    assert not hasattr(config, "settings")
    with pytest.raises(FrozenInstanceError):
        config._document = b"{}"
    with pytest.raises(FrozenInstanceError):
        del config._document
    with pytest.raises(TypeError):
        config._document[0] = 0


def test_mutating_caller_mappings_at_every_nested_level_cannot_change_configuration():
    settings = _settings()
    expected = deepcopy(settings)
    config = RunConfig(settings)
    settings["schema_version"] = 2
    settings["grid"]["ny"] = 0
    settings["optics"]["distance_m"] = math.inf
    settings["solver"]["iterations"] = -1
    settings["solver"]["initialization"]["seed"] = False
    settings["metrics"]["intensity_mse"]["unexpected"] = 1
    settings["metrics"]["intensity_psnr"]["data_range"] = 0.0
    settings["metrics"]["signal_region_power_fraction"]["mask"] = "../outside.npy"
    settings["metrics"]["regional_intensity_cv"].clear()
    settings.clear()
    assert config.to_dict() == expected


def test_mutating_exported_nested_dictionaries_cannot_bypass_validation():
    config = RunConfig(_settings())
    exported = config.to_dict()
    exported["solver"]["initialization"]["seed"] = -1
    exported["metrics"]["intensity_psnr"]["data_range"] = math.nan
    exported["grid"]["dx_m"] = 0.0
    assert config.to_dict() == _settings()
    with pytest.raises(ValueError, match="grid.dx_m"):
        RunConfig(exported)
    fresh = config.to_dict()
    for path in ("", "grid", "optics", "solver", "solver.initialization", "metrics",
                 "metrics.intensity_psnr"):
        assert _node(fresh, path) is not _node(exported, path)


_OBJECT_PATHS = ["", "grid", "optics", "solver", "solver.initialization", "metrics",
                 "metrics.intensity_mse", "metrics.intensity_nmse", "metrics.intensity_psnr",
                 "metrics.signal_region_power_fraction", "metrics.regional_intensity_cv"]


@pytest.mark.parametrize("path", _OBJECT_PATHS)
@pytest.mark.parametrize("bad", [None, [], 1, "{}"])
def test_each_schema_object_requires_a_mapping(path, bad):
    settings = _settings()
    if path:
        _set(settings, path, bad)
    else:
        settings = bad
    with pytest.raises(TypeError, match="mapping"):
        RunConfig(settings)


@pytest.mark.parametrize("path", _OBJECT_PATHS)
def test_unknown_keys_are_rejected_at_every_object_level(path):
    settings = _settings()
    _node(settings, path)["unexpected"] = 1
    with pytest.raises(ValueError, match="unknown|unsupported"):
        RunConfig(settings)


@pytest.mark.parametrize("path", _OBJECT_PATHS)
def test_nonstring_keys_are_rejected_before_sorting_or_serialization(path):
    settings = _settings()
    _node(settings, path)[0] = "unexpected"
    with pytest.raises(TypeError, match="keys must be strings"):
        RunConfig(settings)


_REQUIRED_PATHS = [
    "schema_version", "grid", "optics", "solver", "metrics",
    "grid.ny", "grid.nx", "grid.dy_m", "grid.dx_m",
    "optics.wavelength_m", "optics.distance_m",
    "solver.algorithm", "solver.contract", "solver.iterations", "solver.initialization",
    "solver.initialization.mode", "solver.initialization.seed",
    "metrics.intensity_psnr.data_range", "metrics.signal_region_power_fraction.mask",
    "metrics.regional_intensity_cv.mask",
]


@pytest.mark.parametrize("path", _REQUIRED_PATHS)
def test_missing_required_keys_are_rejected(path):
    settings = _settings()
    parent, key = _parent(settings, path)
    del parent[key]
    with pytest.raises(ValueError, match="missing"):
        RunConfig(settings)


_INTEGER_PATHS = ["schema_version", "grid.ny", "grid.nx", "solver.iterations",
                  "solver.initialization.seed"]


@pytest.mark.parametrize("path", _INTEGER_PATHS)
@pytest.mark.parametrize("bad", [True, False, 1.0, "1", None, np.int64(1)])
def test_integer_fields_require_builtin_int_and_never_accept_bool(path, bad):
    settings = _settings()
    _set(settings, path, bad)
    with pytest.raises(TypeError, match=path):
        RunConfig(settings)


@pytest.mark.parametrize("path,bad", [
    ("schema_version", 0), ("schema_version", 2), ("schema_version", -1),
    ("grid.ny", 0), ("grid.nx", -1), ("grid.ny", sys.maxsize + 1),
    ("grid.nx", sys.maxsize + 1), ("solver.iterations", -1),
    ("solver.iterations", sys.maxsize), ("solver.initialization.seed", -1),
])
def test_integer_domains_and_supported_version_are_checked(path, bad):
    settings = _settings()
    _set(settings, path, bad)
    with pytest.raises(ValueError, match=path):
        RunConfig(settings)


def test_indexable_boundary_counts_and_large_seed_do_not_allocate_or_truncate():
    settings = _settings()
    settings["grid"].update(ny=sys.maxsize, nx=1)
    settings["solver"]["iterations"] = sys.maxsize - 1
    settings["solver"]["initialization"]["seed"] = 2**128 + 1
    assert RunConfig(settings).to_dict() == settings
    settings["solver"]["iterations"] = 0
    settings["solver"]["initialization"]["seed"] = 0
    assert RunConfig(settings).to_dict() == settings


_REAL_PATHS = ["grid.dy_m", "grid.dx_m", "optics.wavelength_m", "optics.distance_m",
               "metrics.intensity_psnr.data_range"]


@pytest.mark.parametrize("path", _REAL_PATHS)
@pytest.mark.parametrize("bad", [True, "1.0", None, 1j, np.float64(1.0), np.float32(1.0)])
def test_real_fields_reject_implicit_non_json_scalar_conversion(path, bad):
    settings = _settings()
    _set(settings, path, bad)
    with pytest.raises(TypeError, match=path):
        RunConfig(settings)


@pytest.mark.parametrize("path", _REAL_PATHS)
@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, 10**400])
def test_real_fields_reject_nonfinite_and_unrepresentable_values(path, bad):
    settings = _settings()
    _set(settings, path, bad)
    with pytest.raises(ValueError, match=path):
        RunConfig(settings)


@pytest.mark.parametrize("path", [path for path in _REAL_PATHS if path != "optics.distance_m"])
@pytest.mark.parametrize("bad", [0.0, -0.0, -1.0])
def test_positive_real_fields_reject_zero_and_negative_values(path, bad):
    settings = _settings()
    _set(settings, path, bad)
    with pytest.raises(ValueError, match=path):
        RunConfig(settings)


@pytest.mark.parametrize("path", _REAL_PATHS)
def test_builtin_integer_real_parameters_are_stored_as_binary64(path):
    settings = _settings()
    _set(settings, path, 1)
    parent, key = _parent(RunConfig(settings).to_dict(), path)
    assert type(parent[key]) is float
    assert _bits(parent[key]) == _bits(1.0)


@pytest.mark.parametrize("value", [0.0, -0.0, 0.1, -2e-4, 633e-9,
                                   math.nextafter(1.0, 0.0), math.nextafter(1.0, math.inf),
                                   sys.float_info.min, math.ulp(0.0), sys.float_info.max])
def test_finite_binary64_distance_bits_survive_config_json_roundtrip(value):
    settings = _settings()
    settings["optics"]["distance_m"] = value
    config = RunConfig(settings)
    parsed = _parse_json(_json_bytes(config.to_dict()), "config fixture")
    rebuilt = RunConfig(parsed)
    assert _bits(rebuilt.to_dict()["optics"]["distance_m"]) == _bits(value)


@pytest.mark.parametrize("path,bad", [
    ("solver.algorithm", "other"), ("solver.contract", "m3_periodic_lossless_asm_v2"),
    ("solver.initialization.mode", "random"),
    ("metrics.signal_region_power_fraction.mask", "cv_mask.npy"),
    ("metrics.regional_intensity_cv.mask", "signal_mask.npy"),
    ("metrics.signal_region_power_fraction.mask", "../signal_mask.npy"),
])
def test_named_contracts_and_metric_artifact_roles_are_exact(path, bad):
    settings = _settings()
    _set(settings, path, bad)
    with pytest.raises(ValueError, match=path):
        RunConfig(settings)


@pytest.mark.parametrize("path", ["solver.algorithm", "solver.contract", "solver.initialization.mode",
                                  "metrics.signal_region_power_fraction.mask", "metrics.regional_intensity_cv.mask"])
def test_named_schema_values_require_strings(path):
    settings = _settings()
    _set(settings, path, None)
    with pytest.raises(TypeError, match=path):
        RunConfig(settings)


@pytest.mark.parametrize("initialization", [
    {"mode": "seed", "seed": 7, "artifact": "initial_phase.npy"},
    {"mode": "explicit_phase", "artifact": "initial_phase.npy", "seed": 7},
    {"mode": "explicit_phase"},
    {"mode": "explicit_phase", "artifact": "../initial_phase.npy"},
])
def test_initialization_modes_are_exclusive_with_fixed_artifact_role(initialization):
    settings = _settings()
    settings["solver"]["initialization"] = initialization
    with pytest.raises(ValueError, match="solver.initialization"):
        RunConfig(settings)


def test_json_encoding_has_exact_utf8_sorted_format_lf_and_final_newline():
    value = {"z": "光", "a": {"x": -0.0, "b": 1}}
    expected = '{\n  "a": {\n    "b": 1,\n    "x": -0.0\n  },\n  "z": "光"\n}\n'.encode("utf-8")
    assert _json_bytes(value) == expected
    assert _json_bytes(dict(reversed(list(value.items())))) == expected
    assert b"\r" not in expected
    assert _parse_json(expected, "unicode fixture") == value


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_json_writer_never_emits_nonstandard_nonfinite_constants(value):
    with pytest.raises(ValueError):
        _json_bytes({"value": value})


@pytest.mark.parametrize("data", [
    b'{"a":1,"a":2}', b'{"outer":{"a":1,"a":2}}',
    b'{"a":1,"\\u0061":2}', b'[{"a":1,"a":2}]',
])
def test_json_reader_rejects_duplicate_keys_at_any_depth(data):
    with pytest.raises(ValueError, match="fixture.*duplicate key"):
        _parse_json(data, "fixture")


@pytest.mark.parametrize("token", [b"NaN", b"Infinity", b"-Infinity"])
def test_json_reader_rejects_nonstandard_constants(token):
    with pytest.raises(ValueError, match="fixture.*nonstandard constant"):
        _parse_json(b'{"value":' + token + b"}", "fixture")


@pytest.mark.parametrize("data", [b"\xff", b'{"x":}', b"{} trailing", b"\xef\xbb\xbf{}"])
def test_json_reader_reports_encoding_and_syntax_failures_with_context(data):
    with pytest.raises(ValueError, match="config.json.*invalid UTF-8 JSON"):
        _parse_json(data, "config.json")


@pytest.mark.parametrize("value", ["{}", bytearray(b"{}"), None])
def test_json_reader_requires_exact_byte_snapshot(value):
    with pytest.raises(TypeError, match="config.json.*bytes"):
        _parse_json(value, "config.json")


def test_standard_exponent_overflow_is_independently_rejected_by_schema():
    data = _json_bytes(_settings()).replace(b'"distance_m": 0.0002', b'"distance_m": 1e999')
    parsed = _parse_json(data, "config.json")
    assert math.isinf(parsed["optics"]["distance_m"])
    with pytest.raises(ValueError, match="optics.distance_m.*finite"):
        RunConfig(parsed)


def test_configuration_json_roundtrip_is_deterministic_without_retaining_inputs():
    settings = _settings()
    before = deepcopy(settings)
    config = RunConfig(settings)
    encoded = _json_bytes(config.to_dict())
    assert settings == before
    assert encoded == _json_bytes(RunConfig(json.loads(encoded)).to_dict())
