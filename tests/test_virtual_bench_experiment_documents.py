"""Independent settings/schema/bit identity checks; no optical execution."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import math
import struct

import pytest

from apps.virtual_bench import adapter, experiment_documents as documents
from apps.virtual_bench import polarization_adapter, two_path_adapter

REQUEST_ID = "12345678-1234-4234-8234-123456789abc"
MODES = ("sequential", "two_path", "polarization")
CONTRACTS = {"sequential": "v0_aligned_scalar_forward_v1",
             "two_path": "v2b_unfolded_scalar_two_path_v1",
             "polarization": "v2d_ideal_jones_same_plane_v1"}


def document(mode="sequential", *, gaussian=True):
    source = {"kind": "uniform", "amplitude": 1.17, "phase_rad": 8.71}
    if gaussian:
        source.update(kind="gaussian", waist_radius_m=23.7e-6,
                      center_x_m=2.31e-6, center_y_m=-1.91e-6)
        if mode != "polarization": source["waist_z_m"] = -0.00073
    experiment = {"wavelength_m": 633.0000000000001e-9,
                  "grid": {"ny": 5, "nx": 8, "dy": 4.31e-6, "dx": 3.79e-6},
                  "source": source}
    if mode == "sequential":
        experiment.update(schema_version=1, model_contract=CONTRACTS[mode], components=[
            {"id": "iris_Z", "kind": "circular_aperture", "z_m": 0.001, "radius_m": 13.7e-6},
            {"id": "lens_A", "kind": "thin_lens", "z_m": 0.001, "focal_length_m": -0.020000000000000004},
            {"id": "slit_M", "kind": "rectangular_aperture", "z_m": 0.0013,
             "width_m": 17.1e-6, "height_m": 23.3e-6}], observation={"id": "screen", "z_m": 0.0023})
    elif mode == "two_path":
        experiment["two_arm_spec"] = {"arm_0_distance_m": 0.0011, "arm_1_distance_m": 0.0017,
                                      "relative_phase_rad": 8.570796326794897}
    else:
        experiment.update(schema_version=1, model_contract=CONTRACTS[mode],
            coefficients={"x": {"re": .83, "im": -.27}, "y": {"re": -.19, "im": .61}},
            elements=[{"id": "plate_Z", "kind": "linear_retarder", "axis_angle_rad": -.31,
                       "retardance_rad": 7.913981633974483},
                      {"id": "analyzer_A", "kind": "linear_polarizer", "axis_angle_rad": math.pi/2 + 1e-12}],
            readout={"row": 1, "column": 6})
    return {"document_format": "ohlab_virtual_experiment", "document_version": 1,
            "mode": mode, "model_contract": CONTRACTS[mode], "experiment": experiment,
            "metadata": {"title": "實驗 e\u0301 😀", "notes": "  保留空白\n\t<script>text only</script>  "}}


def raw(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")


def ordinary_submission(value):
    mode, experiment = value["mode"], value["experiment"]
    if mode == "sequential": return adapter.validate_submission({"request_id": REQUEST_ID, "experiment": experiment})
    if mode == "two_path":
        return two_path_adapter.validate_submission({"protocol_version": 1, "message_type": "two_path_submission",
            "request_id": REQUEST_ID, "experiment": experiment})
    return polarization_adapter.validate_submission({"protocol_version": 1, "message_type": "polarization_submission",
        "request_id": REQUEST_ID, "experiment_sha256": None, "experiment": experiment})


def bits(value):
    return struct.pack(">d", float(value))


def assert_leaves(actual, expected):
    if isinstance(expected, dict):
        assert set(actual) == set(expected), "DOCUMENT_NUMERIC_BITS_DETECTED"
        for key in expected: assert_leaves(actual[key], expected[key])
    elif isinstance(expected, list):
        assert len(actual) == len(expected), "DOCUMENT_ORDER_IDS_DETECTED"
        for left, right in zip(actual, expected): assert_leaves(left, right)
    elif type(expected) in (float, int) and not isinstance(expected, bool):
        if type(expected) is int:
            assert type(actual) is int, "DOCUMENT_NUMERIC_BITS_DETECTED"
        assert bits(actual) == bits(expected), "DOCUMENT_NUMERIC_BITS_DETECTED"
    else:
        assert actual == expected, "DOCUMENT_ORDER_IDS_DETECTED"


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("gaussian", [False, True])
def test_canonical_bytes_complete_numeric_order_and_existing_digest(mode, gaussian):
    value = document(mode, gaussian=gaussian)
    normal = ordinary_submission(deepcopy(value))
    validated = documents.document_from_json(raw(value))
    expected = {**value, "experiment": normal.experiment.to_dict()}
    encoded = (json.dumps(expected, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    assert validated.canonical_bytes == encoded, "DOCUMENT_NUMERIC_BITS_DETECTED"
    assert validated.experiment_sha256 == normal.experiment_sha256, "DOCUMENT_DIGEST_CONTRACT_DETECTED"
    assert_leaves(validated.to_dict(), value)
    assert documents.document_from_json(encoded).canonical_bytes == encoded
    assert not encoded.startswith(b"\xef\xbb\xbf") and encoded.endswith(b"\n")


@pytest.mark.parametrize("mode", MODES)
def test_metadata_has_no_scientific_digest_coverage_and_data_are_owned(mode):
    value = document(mode)
    validated = documents.validate_document(value)
    original = validated.canonical_bytes
    value["metadata"]["title"] = "changed"
    value["experiment"]["source"]["amplitude"] = 9.0
    copied = validated.to_dict(); copied["experiment"]["grid"]["nx"] = 123
    assert validated.canonical_bytes == original and validated.to_dict()["experiment"]["grid"]["nx"] == 8
    metadata_only = validated.to_dict(); metadata_only["metadata"] = {"title": "別名", "notes": "內容"}
    other = documents.validate_document(metadata_only)
    assert other.canonical_bytes != original
    assert other.experiment_sha256 == validated.experiment_sha256, "DOCUMENT_DIGEST_CONTRACT_DETECTED"
    with pytest.raises(FrozenInstanceError): validated.experiment_sha256 = "x"


@pytest.mark.parametrize("mode", MODES)
def test_document_operations_execute_zero_scientific_calls(mode, monkeypatch):
    def forbidden(*args, **kwargs): pytest.fail("DOCUMENT_ZERO_COMPUTE_DETECTED")
    for module, names in ((adapter, ("run_experiment", "simulate_submission")),
        (two_path_adapter, ("sample_source", "run_two_arm", "simulate_submission", "sweep_submission")),
        (polarization_adapter, ("sample_source", "apply_linear_polarizer", "apply_linear_retarder",
                               "transmission_ratio", "simulate_submission", "sweep_submission"))):
        for name in names: monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(polarization_adapter.JonesField, "from_scalar", forbidden)
    value = documents.document_from_json(raw(document(mode)))
    assert documents.validate_document(value.to_dict()).canonical_bytes == value.canonical_bytes


@pytest.mark.parametrize("mode", MODES)
def test_empty_and_maximum_train_and_mode_caps(mode):
    value = document(mode, gaussian=False)
    scientific = value["experiment"]
    cap = 128 if mode == "polarization" else 512
    scientific["grid"].update(ny=cap, nx=cap)
    if mode == "sequential":
        scientific["components"] = []
        documents.validate_document(value)
        scientific["components"] = [{"id": f"lens{i}", "kind": "thin_lens", "z_m": 0., "focal_length_m": -.02} for i in range(8)]
    elif mode == "polarization":
        scientific["elements"] = []
        documents.validate_document(value)
        scientific["elements"] = [{"id": f"p{i}", "kind": "linear_polarizer", "axis_angle_rad": i*.13} for i in range(8)]
    documents.validate_document(value)
    scientific["grid"]["nx"] = cap + 1
    with pytest.raises(documents.DocumentError, match=str(cap)) as caught: documents.validate_document(value)
    assert caught.value.code == "invalid_experiment"


@pytest.mark.parametrize("mode", ["sequential", "polarization"])
def test_order_ids_coefficients_readout_and_excess_elements(mode):
    value = document(mode)
    canonical = documents.validate_document(value).to_dict()["experiment"]
    name = "components" if mode == "sequential" else "elements"
    assert canonical[name] == value["experiment"][name], "DOCUMENT_ORDER_IDS_DETECTED"
    if mode == "polarization":
        assert canonical["coefficients"] == value["experiment"]["coefficients"], "DOCUMENT_COEFFICIENT_BITS_DETECTED"
        assert_leaves(canonical["coefficients"], value["experiment"]["coefficients"])
        assert canonical["readout"] == {"row": 1, "column": 6}, "DOCUMENT_ORDER_IDS_DETECTED"
    value["experiment"][name] = [value["experiment"][name][0]] * 9
    with pytest.raises(documents.DocumentError): documents.validate_document(value)


@pytest.mark.parametrize("mode", MODES)
def test_raw_and_browser_prepared_signed_zeros_have_normal_digest(mode):
    value = document(mode)
    value["experiment"]["source"].update(amplitude=-0.0, phase_rad=-0.0, center_x_m=-0.0, center_y_m=-0.0)
    if mode != "polarization": value["experiment"]["source"]["waist_z_m"] = -0.0
    if mode == "two_path": value["experiment"]["two_arm_spec"].update(arm_0_distance_m=-0.0, relative_phase_rad=-0.0)
    first = documents.document_from_json(raw(value))
    assert first.experiment_sha256 == ordinary_submission(first.to_dict()).experiment_sha256, "DOCUMENT_DIGEST_CONTRACT_DETECTED"
    # Test-only representation of ordinary JSON.stringify's numeric-zero wire policy.
    def browser_wire(item):
        if isinstance(item, dict): return {k: browser_wire(v) for k, v in item.items()}
        if isinstance(item, list): return [browser_wire(v) for v in item]
        return 0 if type(item) in (int, float) and item == 0 else item
    final = documents.document_from_json(raw(browser_wire(first.to_dict())))
    assert final.experiment_sha256 == ordinary_submission(final.to_dict()).experiment_sha256, "DOCUMENT_DIGEST_CONTRACT_DETECTED"
    assert documents.document_from_json(raw(final.to_dict())).canonical_bytes == final.canonical_bytes
    if mode != "polarization": assert first.experiment_sha256 != final.experiment_sha256


@pytest.mark.parametrize("token,expected", [("5e-324", 5e-324), ("-5e-324", -5e-324),
    ("9007199254740993", 9007199254740992.), ("9007199254740992", 9007199254740992.),
    ("18014398509481984", 18014398509481984.), ("0e-999", 0.), ("-0.0", -0.)])
def test_supported_binary64_scalar_rounding_and_subnormal_tokens(token, expected):
    value = document(gaussian=False)
    encoded = raw(value).replace(b'"phase_rad": 8.71', b'"phase_rad": ' + token.encode())
    phase = documents.document_from_json(encoded).to_dict()["experiment"]["source"]["phase_rad"]
    assert bits(phase) == bits(expected), "DOCUMENT_NUMERIC_BITS_DETECTED"


@pytest.mark.parametrize("token", ["1e-999", "-1e-999", "1.01e-999", "0.0001e-999"])
def test_nonzero_decimal_underflow_is_rejected_without_tightening_old_parser(token):
    encoded = ('{"number":' + token + '}').encode()
    assert adapter.strict_json_loads(encoded)["number"] == 0
    try:
        documents.strict_document_loads(encoded)
    except ValueError:
        pass
    else:
        pytest.fail("DOCUMENT_NONZERO_UNDERFLOW_DETECTED")


def test_overflow_integer_token_is_raw_document_error_and_legacy_parser_unchanged():
    encoded = b'{"number":' + b'1' + b'0'*400 + b'}'
    assert type(adapter.strict_json_loads(encoded)["number"]) is int
    with pytest.raises(ValueError, match="integer exceeds finite binary64"):
        documents.strict_document_loads(encoded)


@pytest.mark.parametrize("encoded", [b'{"x":1,"x":2}', b'{"x":{"k":1,"\\u006b":2}}',
    b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":1e999}', b'{"x":-1e999}',
    b'\xff', b'\xef\xbb\xbf{}', b'{"x":', b'['*3000, b' '*32769, b'{"x":'+b'9'*5000+b'}'],
    ids=["duplicate", "escaped_duplicate", "nan", "infinity", "negative_infinity", "overflow",
         "negative_overflow", "invalid_utf8", "bom", "truncated", "recursion", "oversize", "unusable_integer"])
def test_malformed_raw_json_rejected_before_decoded_validation(encoded):
    try:
        documents.strict_document_loads(encoded)
    except (ValueError, TypeError):
        pass
    else:
        pytest.fail("RAW_DUPLICATE_KEYS_DETECTED")


@pytest.mark.parametrize("field,value,code", [
    ("document_format", "other", "invalid_document"),
    ("document_version", 2, "unsupported_document_version"),
    ("document_version", True, "unsupported_document_version"),
    ("mode", "other", "unsupported_document_mode"), ("mode", [], "unsupported_document_mode"),
    ("model_contract", "unknown", "unsupported_model_contract"),
    ("metadata", {"title": "x"}, "invalid_metadata"), ("metadata", [], "invalid_metadata")])
def test_closed_wrapper_rejects_unsupported_or_missing_contracts(field, value, code):
    data = document(); data[field] = value
    try:
        documents.validate_document(data)
    except documents.DocumentError as exc:
        assert exc.code == code, "DOCUMENT_MODE_CONTRACT_DETECTED"
    else:
        pytest.fail("DOCUMENT_MODE_CONTRACT_DETECTED")


@pytest.mark.parametrize("field", ["document_format", "document_version", "mode", "model_contract", "experiment", "metadata"])
def test_missing_root_field_rejected(field):
    value = document(); del value[field]
    with pytest.raises(documents.DocumentError) as caught: documents.validate_document(value)
    assert caught.value.code == "invalid_document"


@pytest.mark.parametrize("field", ["status", "results", "request_id", "experiment_sha256", "arrays", "camera", "__proto__", "constructor"])
def test_no_imported_success_result_or_unknown_fields(field):
    value = document(); value[field] = "complete"
    try:
        documents.validate_document(value)
    except documents.DocumentError as exc:
        assert exc.code == "invalid_document", "IMPORTED_SUCCESS_STATE_DETECTED"
    else:
        pytest.fail("IMPORTED_SUCCESS_STATE_DETECTED")


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("mutation", [lambda d: d["grid"].update(nx=True),
    lambda d: d["grid"].update(dx=0), lambda d: d["source"].update(amplitude=-1),
    lambda d: d["source"].update(phase_rad=True), lambda d: d.update(extra=1),
    lambda d: d["source"].update(extra=1)])
def test_existing_scientific_domains_and_unknown_fields_are_authoritative(mode, mutation):
    value = document(mode); mutation(value["experiment"])
    with pytest.raises(documents.DocumentError) as caught: documents.validate_document(value)
    assert caught.value.code == "invalid_experiment"


@pytest.mark.parametrize("mode", ["sequential", "polarization"])
def test_wrapper_inner_model_mismatch_and_missing_inner_field(mode):
    value = document(mode); value["experiment"]["model_contract"] = "wrong"
    with pytest.raises(documents.DocumentError) as caught: documents.validate_document(value)
    assert caught.value.code == "invalid_experiment", "DOCUMENT_MODE_CONTRACT_DETECTED"
    value = document(mode); del value["experiment"]["schema_version"]
    with pytest.raises(documents.DocumentError): documents.validate_document(value)


@pytest.mark.parametrize("name,limit", [("title", 120), ("notes", 2000)])
def test_unicode_scalar_lengths_supplementary_combining_chinese_and_exact_text(name, limit):
    value = document(); value["metadata"][name] = "😀" * limit
    assert documents.validate_document(value).to_dict()["metadata"][name] == "😀" * limit, "DOCUMENT_UNICODE_SCALARS_DETECTED"
    value["metadata"][name] += "中"
    try:
        documents.validate_document(value)
    except documents.DocumentError as exc:
        assert exc.code == "invalid_metadata", "DOCUMENT_UNICODE_SCALARS_DETECTED"
    else:
        pytest.fail("DOCUMENT_UNICODE_SCALARS_DETECTED")
    value["metadata"][name] = " e\u0301中文 "
    assert documents.validate_document(value).to_dict()["metadata"][name] == " e\u0301中文 "


@pytest.mark.parametrize("character", ["\0", "\r", "\x1f", "\x7f", "\x85", "\x9f", "\ud800", "\udfff"])
@pytest.mark.parametrize("name", ["title", "notes"])
def test_lone_surrogates_and_forbidden_controls_reject(character, name):
    value = document(); value["metadata"][name] = character
    encoded = json.dumps(value, ensure_ascii=True).encode()
    with pytest.raises(documents.DocumentError) as caught: documents.document_from_json(encoded)
    assert caught.value.code == "invalid_metadata"


def test_notes_only_allow_tab_lf_and_escaped_surrogate_pair_is_one_scalar():
    value = document(); value["metadata"]["notes"] = "\t\n"
    assert documents.validate_document(value).to_dict()["metadata"]["notes"] == "\t\n"
    value["metadata"]["title"] = "\t"
    with pytest.raises(documents.DocumentError): documents.validate_document(value)
    assert documents.strict_document_loads(b'{"title":"\\ud83d\\ude00"}')["title"] == "😀"


@pytest.mark.parametrize("kind", ["depth", "nodes", "string", "key", "surrogate_key", "control_key"])
def test_structure_and_all_text_fail_before_mode_construction(kind, monkeypatch):
    value = document()
    if kind == "depth":
        value["extra"] = []; current = value["extra"]
        for _ in range(12): current.append([]); current = current[0]
    elif kind == "nodes": value["extra"] = [None] * 2048
    elif kind == "string": value["extra"] = "x" * 8193
    elif kind == "key": value["x" * 8193] = 0
    elif kind == "surrogate_key": value["\ud800"] = 0
    else: value["\t"] = 0
    def forbidden(*args, **kwargs): pytest.fail("DOCUMENT_STRUCTURE_LIMIT_DETECTED: mode constructor reached")
    monkeypatch.setattr(documents, "validate_sequential", forbidden)
    with pytest.raises(documents.DocumentError) as caught: documents.validate_document(value)
    expected = "invalid_document" if kind.endswith("_key") else "document_structure_limit"
    assert caught.value.code == expected, "DOCUMENT_STRUCTURE_LIMIT_DETECTED"


def test_structure_limit_counting_boundaries_and_canonical_cap(monkeypatch):
    # Direct structural boundary probes: keys are strings but not value nodes.
    documents._structure({"x": [None] * 2046})
    with pytest.raises(documents.DocumentError): documents._structure({"x": [None] * 2047})
    value = {}; current = value
    for _ in range(12): current["x"] = {}; current = current["x"]
    documents._structure(value)
    current["x"] = {}
    with pytest.raises(documents.DocumentError): documents._structure(value)
    documents._structure({"x" * 8192: "x" * 8192})
    value = document(); expected = documents.validate_document(value).canonical_bytes
    monkeypatch.setattr(documents, "MAX_DOCUMENT_BYTES", len(expected))
    assert documents.validate_document(value).canonical_bytes == expected
    monkeypatch.setattr(documents, "MAX_DOCUMENT_BYTES", len(expected) - 1)
    with pytest.raises(documents.DocumentError) as caught: documents.validate_document(value)
    assert caught.value.code == "canonical_document_too_large"
