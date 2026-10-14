"""Explicit v2/new-only documents and frozen pre-edit legacy canonical identities."""

from copy import deepcopy
import hashlib
import json
import math
import struct

import pytest

from apps.virtual_bench import experiment_documents as documents
from apps.virtual_bench import polarized_two_path_adapter as adapter
from apps.virtual_bench import polarized_two_path_protocol as protocol
from test_virtual_bench_experiment_documents import document as legacy_document, assert_leaves
from test_virtual_bench_polarized_two_path_adapter import envelope, polarizer, retarder

# Captured before any implementation edit on accepted 431346c; independent of
# this changed encoder. Exact bytes remain in ignored legacy_v1_before evidence.
LEGACY_CANONICAL_SHA256={
    ("sequential",False):"b386c454288e57b896e3670b248cdf591e40eff270556b41552fff4b6ffc304d",
    ("sequential",True):"07dd0b8009cf0e26fd5384c3bc0220c0d9475aaadc91760b83151a36c3da65bb",
    ("two_path",False):"f7668d53e74f2dcd326c339f882cc16f5ca9e206f22975ca7dd52ac1f6939e6e",
    ("two_path",True):"6bdfb95524bbc985f7313bace78b0ca0775ff718fe058b8288a56c3e1f457d54",
    ("polarization",False):"94bcf56c617493cd490226cb11290b578182df21682d630aaca52f8b2727e3b1",
    ("polarization",True):"f941414ae13d947bcd155a3bcab84666d33b40cfc439ceddc9390d95b3cc7427",
}


def document(*,enabled=True,gaussian=True):
    scientific=envelope(gaussian=gaussian,enabled=enabled,angle=-7.123456789123456,phase=8.570796326794897,
        actions_0=[retarder("plate_Z",-.31,7.913981633974483),polarizer("loss_A",.43)],
        actions_1=[polarizer("loss_B",-.27),retarder("plate_M",.19,-1.23)])["experiment"]
    return {"document_format":"ohlab_virtual_experiment","document_version":2,"mode":"polarized_two_path",
        "model_contract":protocol.MODEL_CONTRACT,"experiment":scientific,
        "metadata":{"title":"實驗 e\u0301 😀","notes":"  保留空白\n\t<script>text only</script>  "}}


@pytest.mark.parametrize("mode",["sequential","two_path","polarization"])
@pytest.mark.parametrize("gaussian",[False,True])
def test_old_v1_bytes_match_pre_edit_frozen_canonical_hashes(mode,gaussian):
    result=documents.validate_document(legacy_document(mode,gaussian=gaussian))
    assert hashlib.sha256(result.canonical_bytes).hexdigest()==LEGACY_CANONICAL_SHA256[mode,gaussian],"V2G_LEGACY_CANONICAL_DETECTED"
    assert result.to_dict()["document_version"]==1,"V2G_LEGACY_VERSION_DETECTED"
    assert documents.DOCUMENT_VERSION==1 and set(documents.MODEL_CONTRACTS)=={"sequential","two_path","polarization"}


@pytest.mark.parametrize("enabled",[False,True])
@pytest.mark.parametrize("gaussian",[False,True])
def test_v2_complete_roundtrip_bits_order_ids_disabled_angle_and_canonical_fixed_point(enabled,gaussian):
    value=document(enabled=enabled,gaussian=gaussian)
    raw=json.dumps(value,ensure_ascii=False,allow_nan=False).encode("utf-8")
    result=documents.document_from_json(raw)
    owned=result.to_dict()
    assert set(owned)=={"document_format","document_version","mode","model_contract","experiment","metadata"}
    assert_leaves(owned,value)
    assert owned["experiment"]["analyzer"]==value["experiment"]["analyzer"],"V2G_DISABLED_ANGLE_DOCUMENT_DETECTED"
    assert owned["experiment"]["coefficients"]==value["experiment"]["coefficients"],"V2G_DOCUMENT_FIELDS_DETECTED"
    for name in ("arm_0","arm_1"):
        assert [a["id"] for a in owned["experiment"][name]["actions"]]==[a["id"] for a in value["experiment"][name]["actions"]],"V2G_DOCUMENT_FIELDS_DETECTED"
    assert documents.document_from_json(result.canonical_bytes).canonical_bytes==result.canonical_bytes
    assert result.experiment_sha256==protocol.experiment_digest(adapter.validate_experiment(value["experiment"]).to_dict())
    assert result.canonical_bytes.endswith(b"\n") and not result.canonical_bytes.startswith(b"\xef\xbb\xbf")
    changed=deepcopy(owned);changed["metadata"]["title"]="renamed"
    assert documents.validate_document(changed).experiment_sha256==result.experiment_sha256
    if gaussian:assert owned["experiment"]["source"]["waist_z_m"]==-.00073


@pytest.mark.parametrize("mode",["sequential","two_path","polarization","polarized_two_path"])
@pytest.mark.parametrize("version",[1,2,3,True,1.0,"2"])
def test_exact_version_mode_acceptance_matrix_and_error_codes(mode,version):
    value=document() if mode=="polarized_two_path" else legacy_document(mode)
    value["document_version"]=version
    if type(version) is int and ((version==1 and mode!="polarized_two_path") or (version==2 and mode=="polarized_two_path")):
        assert documents.validate_document(value).to_dict()["document_version"]==version
        return
    try:
        documents.validate_document(value)
    except documents.DocumentError as error:
        actual_code=error.code
    else:
        pytest.fail("V2G_DOCUMENT_VERSION_DETECTED: unsupported version/mode was accepted")
    expected="unsupported_document_mode" if type(version) is int and version==1 and mode=="polarized_two_path" else "unsupported_document_version"
    assert actual_code==expected,"V2G_DOCUMENT_VERSION_DETECTED"


@pytest.mark.parametrize("mutation,code",[
    (lambda v:v.update(mode="unknown"),"unsupported_document_mode"),
    (lambda v:v.update(model_contract="v2d_ideal_jones_same_plane_v1"),"unsupported_model_contract"),
    (lambda v:v["experiment"].update(model_contract="wrong"),"invalid_experiment"),
    (lambda v:v["experiment"].update(schema_version=2),"invalid_experiment"),
    (lambda v:v["experiment"]["analyzer"].pop("axis_angle_rad"),"invalid_experiment"),
    (lambda v:v["experiment"].update(outputs=[]),"invalid_experiment"),
    (lambda v:v.update(request_id="x"),"invalid_document"),
    (lambda v:v["metadata"].update(title="x"*121),"invalid_metadata"),
    (lambda v:v["metadata"].update(notes="x"*2001),"invalid_metadata"),
])
def test_new_documents_closed_schema_no_results_or_implicit_migration(mutation,code):
    value=document(enabled=False);mutation(value)
    with pytest.raises(documents.DocumentError) as caught:documents.validate_document(value)
    assert caught.value.code==code


def test_new_document_validation_import_export_zero_science_and_gate_access(monkeypatch):
    def forbidden(*a,**k):pytest.fail("V2G_DOCUMENT_ZERO_SCIENCE_DETECTED")
    for name in ("sample_source","run_polarized_two_arm","apply_linear_polarizer","transmission_ratio",
                 "simulate_submission","sweep_submission"):
        monkeypatch.setattr(adapter,name,forbidden)
    monkeypatch.setattr(adapter.JonesField,"from_scalar",forbidden)
    value=document(enabled=False)
    validated=documents.validate_document(value)
    assert documents.document_from_json(validated.canonical_bytes).canonical_bytes==validated.canonical_bytes
    assert validated.to_dict()["experiment"]["analyzer"]["axis_angle_rad"]==-7.123456789123456


@pytest.mark.parametrize("token",["1e-999","-1e-999","1e999","NaN","Infinity"])
def test_original_new_document_bytes_reject_nonfinite_or_underflow_before_reserialization(token):
    raw=json.dumps(document(enabled=False)).replace('"axis_angle_rad": -7.123456789123456',f'"axis_angle_rad": {token}').encode()
    with pytest.raises(ValueError):documents.document_from_json(raw)


def test_new_mode_signed_zero_only_canonicalization_and_nonzero_tiny_bits():
    value=document(enabled=False,gaussian=False)
    value["experiment"]["analyzer"]["axis_angle_rad"]=-0.
    value["experiment"]["relative_phase_rad"]=-1e-200
    result=documents.validate_document(value).to_dict()["experiment"]
    assert struct.pack(">d",result["analyzer"]["axis_angle_rad"])==struct.pack(">d",0.)
    assert struct.pack(">d",result["relative_phase_rad"])==struct.pack(">d",-1e-200)
