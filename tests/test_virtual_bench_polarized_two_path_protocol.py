"""Exact conditional transport roles, framing bounds and malformed scalar rejection."""

from copy import deepcopy
import json
import struct

import numpy as np
import pytest

from apps.virtual_bench import polarized_two_path_adapter as adapter
from apps.virtual_bench import polarized_two_path_protocol as protocol
from test_virtual_bench_polarized_two_path_adapter import REQUEST_ID, envelope, output, sweep_envelope, unpack


def encode(header, arrays):
    return protocol.encode_result(REQUEST_ID, header["experiment"], header["norms"], header["diagnostics"], header["analysis"],
        raw_intensities=tuple(arrays[f"raw_port_{i}_intensity"] for i in range(2)),
        analyzed_intensities=tuple(arrays[f"analyzed_port_{i}_intensity"] for i in range(2))
            if header["experiment"]["analyzer"]["enabled"] else None, x_m=arrays["x_m"], y_m=arrays["y_m"])


@pytest.mark.parametrize("enabled", [False,True])
@pytest.mark.parametrize("shape", [(1,1),(3,4),(32,32),(64,64),(128,128)])
def test_exact_frame_conditional_inventory_order_endian_padding_and_derived_bounds(enabled, shape):
    header, arrays = output(envelope(ny=shape[0],nx=shape[1],enabled=enabled))
    frame = encode(header, arrays)
    magic, length, reserved = struct.unpack_from("<8sII",frame)
    assert magic == b"OHLABPT\0" and reserved == 0
    padding = -length % 8
    assert frame[16+length:16+length+padding] == b"\0"*padding
    assert length+padding <= 16_384
    k = 4 if enabled else 2
    payload_size = 8*(k*shape[0]*shape[1]+sum(shape))
    assert len(frame) == 16+length+padding+payload_size
    assert payload_size <= (526336 if enabled else 264192)
    assert len(frame) <= (542736 if enabled else 280592)
    names = ["raw_port_0_intensity","raw_port_1_intensity"]
    if enabled: names += ["analyzed_port_0_intensity","analyzed_port_1_intensity"]
    names += ["x_m","y_m"]
    position = 0
    for index,(item,name) in enumerate(zip(header["arrays"],names)):
        assert set(item) == {"name","role","port_id","state","dtype","order","shape","offset_bytes","nbytes","units"}
        assert item["name"] == name and item["offset_bytes"] == position, "V2G_WIRE_ROLES_DETECTED"
        assert item["dtype"] == "float64-le" and item["order"] == "C"
        assert item["shape"] == list(arrays[name].shape)
        if index < k:
            assert item["role"] == "intensity" and item["state"] == ("raw" if index < 2 else "analyzed")
            assert item["port_id"] == f"port_{index%2}" and item["units"] == "amplitude_unit^2", "V2G_WIRE_ROLES_DETECTED"
        else:
            assert item["role"] == "coordinate" and item["state"] is item["port_id"] is None and item["units"] == "m"
        start = 16+length+padding+position
        assert frame[start:start+item["nbytes"]] == arrays[name].astype("<f8").tobytes(order="C")
        position += item["nbytes"]
    assert position == payload_size
    assert header["intensity_max"] == [float(arrays[name].max()) for name in names[:k]]
    assert protocol.MAX_RAW_RESPONSE_BYTES == 16+16384+8*(2*128*128+2*128) == 280592
    assert protocol.MAX_RESPONSE_BYTES == 16+16384+8*(4*128*128+2*128) == 542736


def test_closed_result_header_and_original_float64_readout():
    header, arrays = output()
    assert set(header) == {"protocol_version","message_type","request_id","experiment_sha256","experiment",
                          "norms","diagnostics","analysis","arrays","intensity_max"}
    assert header["message_type"] == "polarized_two_path_result"
    assert set(header["norms"]) == {*protocol.NORM_PAIRS,"arm_action_norms"}
    assert set(header["diagnostics"]) == set(protocol.DIAGNOSTIC_KEYS)
    assert header["experiment_sha256"] == protocol.experiment_digest(header["experiment"])
    assert len({b"OHLABV1\0",b"OHLAB2P\0",b"OHLABPL\0",protocol.MAGIC}) == 4
    arrays = {name: values.copy() for name,values in arrays.items()}
    arrays["raw_port_0_intensity"][0,0] = np.nextafter(1.,2.)
    arrays["raw_port_1_intensity"][0,0] = 1e-300
    _, restored = unpack(encode(header,arrays))
    assert restored["raw_port_0_intensity"][0,0] == np.nextafter(1.,2.)
    assert restored["raw_port_1_intensity"][0,0] == 1e-300


@pytest.mark.parametrize("mutation", [
    lambda h:h["norms"]["outputs"].__setitem__(0,True),
    lambda h:h["norms"].update(extra=0), lambda h:h["norms"]["inputs"].__setitem__(1,1.),
    lambda h:h["diagnostics"].update(outputs_total=1.), lambda h:h["diagnostics"].update(total_delta=False),
    lambda h:h["diagnostics"].update(phase_deltas=[99,99]),
    lambda h:h["diagnostics"].update(output_fractions=[None,None]),
    lambda h:h["analysis"].update(enabled=False), lambda h:h["analysis"].update(axis_angle_rad=.2),
    lambda h:h["analysis"].update(ports=None), lambda h:h["analysis"]["ports"].reverse(),
    lambda h:h["analysis"]["ports"][0].update(removed_norm=99.),
    lambda h:h["analysis"]["ports"][0].update(raw_output_ratio=True),
    lambda h:h["analysis"].update(total_original_input_ratio=float("inf")),
    lambda h:h["analysis"]["ports"][1].update(extra=0),
])
def test_malformed_scalar_identity_or_analysis_rejects_whole_result(mutation):
    header,arrays = output(); mutation(header)
    with pytest.raises((ValueError,TypeError)): encode(header,arrays)


def test_disabled_analysis_cannot_supply_duplicate_raw_arrays_or_zero_substitutes():
    header,arrays = output(envelope(enabled=False,angle=1.23456789123456))
    assert header["analysis"] == {"enabled":False,"axis_angle_rad":1.23456789123456,"ports":None,
                                  "total_norm":None,"total_removed_norm":None,"total_original_input_ratio":None}
    with pytest.raises(ValueError,match="absent"):
        protocol.encode_result(REQUEST_ID,header["experiment"],header["norms"],header["diagnostics"],header["analysis"],
            raw_intensities=(arrays["raw_port_0_intensity"],arrays["raw_port_1_intensity"]),
            analyzed_intensities=(arrays["raw_port_0_intensity"],arrays["raw_port_1_intensity"]),x_m=arrays["x_m"],y_m=arrays["y_m"])
    header["analysis"]["total_norm"] = 0
    with pytest.raises(ValueError,match="null"): encode(header,arrays)


def test_exact_zero_numerator_requires_zero_public_ratio_without_reassociation():
    value=envelope(phase=0,distances=(0,0),enabled=True,
        coefficients={"x":{"re":1.,"im":0.},"y":{"re":0.,"im":0.}})
    value["experiment"]["source"]["phase_rad"]=0.
    header,arrays=output(value)
    assert header["norms"]["outputs"][1]==0 and header["diagnostics"]["output_fractions"][1]==0
    changed=deepcopy(header);changed["diagnostics"]["output_fractions"][1]=.1
    with pytest.raises(ValueError,match="zero numerator"):encode(changed,arrays)
    changed=deepcopy(header);changed["analysis"]["ports"][1]["original_input_ratio"]=.1
    with pytest.raises(ValueError,match="zero numerator"):encode(changed,arrays)


@pytest.mark.parametrize("mutation", [
    lambda a:a.update(raw_port_0_intensity=a["raw_port_0_intensity"].astype(np.float32)),
    lambda a:a.update(analyzed_port_1_intensity=a["analyzed_port_1_intensity"][:,:-1]),
    lambda a:a["raw_port_1_intensity"].__setitem__((0,0),-1.),
    lambda a:a["analyzed_port_0_intensity"].__setitem__((0,0),float("nan")),
    lambda a:a["x_m"].__setitem__(0,float("inf")),
])
def test_unusable_array_prevents_frame_publication(mutation):
    header,arrays = output(); arrays={name:values.copy() for name,values in arrays.items()}; mutation(arrays)
    with pytest.raises(ValueError): encode(header,arrays)


def test_header_payload_complete_frame_and_sweep_caps_fail_closed(monkeypatch):
    header,arrays=output()
    for name,limit,message in (("MAX_HEADER_BYTES",16,"header"),("MAX_PAYLOAD_BYTES",1,"payload"),("MAX_RESPONSE_BYTES",16,"frame")):
        original=getattr(protocol,name); monkeypatch.setattr(protocol,name,limit)
        with pytest.raises(ValueError,match=message): encode(header,arrays)
        monkeypatch.setattr(protocol,name,original)
    monkeypatch.setattr(protocol,"MAX_SWEEP_RESPONSE_BYTES",2)
    with pytest.raises(ValueError,match="sweep response"):
        adapter.sweep_submission(adapter.validate_sweep_submission(sweep_envelope()))


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":Infinity}',b'{"a":1e999}',
    b'{"a":1e-999}',b'{"a":-1e-999}',b'\xef\xbb\xbf{}',b'\xff',b'"\x00"'])
def test_new_route_strict_parser_rejects_original_lossy_bytes(raw):
    with pytest.raises((ValueError,TypeError)): protocol.strict_json_loads(raw)


def test_new_parser_preserves_existing_old_route_policy_and_usable_small_values():
    from apps.virtual_bench.adapter import strict_json_loads as old_parser
    assert old_parser(b'{"a":1e-999}') == {"a":0.0}
    assert protocol.strict_json_loads(b'{"a":1e-200,"b":-0.0,"c":0e-999}') == {"a":1e-200,"b":-0.0,"c":0.0}
    with pytest.raises(ValueError): protocol.strict_json_loads(b" "*32769)


def test_sweep_exact_closed_fields_all_rows_prefix_and_scalar_inventory():
    submission=adapter.validate_sweep_submission(sweep_envelope())
    value=json.loads(adapter.sweep_submission(submission).body)
    assert set(value)=={"protocol_version","message_type","request_id","fixed_experiment_sha256","sweep_sha256",
        "fixed_experiment","phases_rad","status","requested_count","completed_count","failed_index","rows","error"}
    assert value["message_type"]=="polarized_two_path_sweep" and value["requested_count"]==value["completed_count"]==17
    assert value["failed_index"] is value["error"] is None
    assert "relative_phase_rad" not in value["fixed_experiment"]
    assert value["sweep_sha256"]==protocol.sweep_digest(submission.fixed_dict(),protocol.PHASES_RAD)
    rows=value["rows"]
    assert all(set(row)=={"index","phase_rad","norms","diagnostics","analysis"} for row in rows)
    for mutation in (lambda r:r[0].update(index=True),lambda r:r[8].update(phase_rad=False),
                     lambda r:r[-1].update(arrays=[]),lambda r:r[0]["analysis"]["ports"].reverse()):
        changed=deepcopy(rows); mutation(changed)
        with pytest.raises((ValueError,TypeError)):
            protocol.encode_sweep_reply(REQUEST_ID,submission.fixed_dict(),protocol.PHASES_RAD,changed)
    with pytest.raises(ValueError,match="complete"):
        protocol.encode_sweep_reply(REQUEST_ID,submission.fixed_dict(),protocol.PHASES_RAD,rows[:16])
    with pytest.raises(ValueError,match="prefix"):
        protocol.encode_sweep_reply(REQUEST_ID,submission.fixed_dict(),protocol.PHASES_RAD,rows[:3],failed_index=4,
                                   error={"code":"numerical_failure","message":"failed"},status_code=422)
    reply=protocol.encode_sweep_reply(REQUEST_ID,submission.fixed_dict(),protocol.PHASES_RAD,rows[:8],failed_index=8,
                                     error={"code":"numerical_failure","message":"😀"*300},status_code=422)
    assert len(reply.body)<=65536 and json.loads(reply.body)["completed_count"]==8
