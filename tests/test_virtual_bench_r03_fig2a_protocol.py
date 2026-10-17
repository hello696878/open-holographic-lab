"""Independent A transport has bounded structure and lossless binary64 JSON."""

import copy
import json

import pytest

from apps.virtual_bench import r03_fig2a_protocol as protocol
from test_virtual_bench_r03_fig2a_adapter import REQUEST_ID, result


def encode(value):
    return protocol.encode_result(value["request_id"], value["experiment"], phase=value["phase"],
        stages=value["stages"], population_dop=value["population"]["infinite_gaussian_degree_of_polarization"],
        provenance=value["provenance"])


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}',
    b'{"a":1e999}', b'{"a":1e-999}', b'\xff', b'\xef\xbb\xbf{}', b'[' * 2000 + b']' * 2000,
    b' ' * 32769], ids=["duplicate", "nan", "infinity", "overflow", "underflow", "utf8",
                       "bom", "deep", "oversized"])
def test_strict_json_rejects_ambiguous_nonfinite_underflow_and_excessive_inputs(raw):
    with pytest.raises((ValueError, TypeError)):
        protocol.strict_json_loads(raw)


def test_canonical_digest_order_and_lossless_float_encoding():
    first = {"b": [1.0000000000000002, 5e-324, -0.0], "a": 1}
    second = {"a": 1, "b": first["b"].copy()}
    assert protocol.experiment_digest(first) == protocol.experiment_digest(second)
    assert protocol.strict_json_loads(protocol.json_bytes(first)) == first
    assert protocol.validate_request_id(REQUEST_ID) == REQUEST_ID
    assert protocol.strict_json_loads(b'{"zero":0e-999}') == {"zero": 0.0}


def test_full_record_roundtrip_is_bounded_and_preserves_small_values_without_reformatting():
    value = result()
    encoded = encode(value)
    assert json.loads(encoded) == value
    assert len(encoded) < protocol.MAX_RESPONSE_BYTES
    assert [record["id"] for record in value["stages"]] == list(protocol.STAGE_IDS)
    assert value["phase"]["shape"] == [16, 16] and value["phase"]["order"] == "C"
    assert value["provenance"]["units"]["stokes"] == "amplitude_unit^2"
    assert value["population"]["assumption"] == protocol.POPULATION_ASSUMPTION
    assert value["limitations"] == list(protocol.LIMITATIONS)


@pytest.mark.parametrize("alter", [
    lambda v: v["phase"].update(shape=[256]),
    lambda v: v["phase"].update(order="F"),
    lambda v: v["phase"]["wrapped_rad"].pop(),
    lambda v: v["phase"]["unwrapped_rad"].append(0.0),
    lambda v: v["phase"]["wrapped_rad"].__setitem__(0, float("nan")),
    lambda v: v["stages"].reverse(),
    lambda v: v["stages"][0]["coherency"][0].pop(),
    lambda v: v["stages"][0].update(roundoff_limited=1),
    lambda v: v["stages"][0].update(stokes=[0.0] * 4),
    lambda v: v["provenance"].update(sample_count=512),
    lambda v: v["provenance"].update(measurement="coherent_mean_field"),
    lambda v: v["provenance"]["units"].update(stokes="W"),
    lambda v: v["provenance"].update(python_version="x" * 65),
])
def test_encoder_rejects_shape_order_nonfinite_identity_and_false_unit_metadata(alter):
    value = copy.deepcopy(result())
    alter(value)
    with pytest.raises((TypeError, ValueError)):
        encode(value)
