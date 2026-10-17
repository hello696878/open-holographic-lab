"""Focused deliberate faults in new in-memory functions/state, then restoration.

Production source is never edited. Every control must pass its independent
baseline assertion, fail that assertion (not import/domain setup), restore the
exact original function object in finally, and pass again. Only new modules
are patched; old Jones operations/files and global RNG settings are untouched.
Use existing Python -B and a fresh ignored --output-dir under runs/.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import traceback

import numpy as np

from ohlab.optics import polarization_statistics as statistics
from ohlab.optics import r03_fig2a as runner

ROOT=Path(__file__).resolve().parents[1]


def hashes() -> dict[str,str]:
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (
        "src/ohlab/optics/polarization_statistics.py","src/ohlab/optics/r03_fig2a.py",
        "scripts/r03_fig2a_negative_controls.py",
    )}


def fixture_spec():
    return runner.IdealPolarizationSpec(amplitude=1.,mean_phase_rad=.7,phase_std_rad=1.2,qwp_angle_rad=.37,hwp_angle_rad=-.61,seed=20261017)


def equal_mixture_assertion():
    result=statistics.coherency_from_samples(np.array([[1,0],[0,1]],dtype=np.complex128),probabilities=np.array([.5,.5]))
    np.testing.assert_allclose(result.coherency,np.diag([.5,.5]),rtol=0,atol=0)


def constant_assertion():
    result=statistics.coherency_from_samples(np.ones((2,2),dtype=np.complex128),probabilities=np.array([.5,.5]))
    np.testing.assert_allclose(result.coherency,np.ones((2,2)),rtol=0,atol=0)


def unequal_power_assertion():
    result=statistics.coherency_from_samples(np.array([[2,0],[0,2]],dtype=np.complex128),probabilities=np.array([.75,.25]))
    np.testing.assert_allclose(result.coherency,np.diag([3.,1.]),rtol=0,atol=0)


def signed_stokes_assertion():
    result=statistics.measure_coherency(np.array([[.5,-.5j],[.5j,.5]],dtype=np.complex128))
    np.testing.assert_allclose(result.stokes,[1,0,0,1],rtol=0,atol=0)


def raw_roundoff_assertion():
    result=statistics.measure_coherency(np.diag([1.,-np.finfo(float).eps]).astype(np.complex128))
    assert result.degree_of_polarization>1.,"raw DoP must not be silently clamped"
    assert result.eigenvalues[0]<0.,"raw eigenvalue must not be silently clipped"


def finite_assertion():
    result=runner.run_ideal_polarization(fixture_spec())
    finite=abs(sum(complex(math.cos(float(p)),math.sin(float(p))) for p in result.phase_wrapped_rad.ravel())/256)
    np.testing.assert_allclose(result.output.degree_of_polarization,finite,rtol=2e-13,atol=2e-13)


def phase_assertion():
    result=runner.run_ideal_polarization(fixture_spec())
    normal=np.random.Generator(np.random.PCG64(20261017)).standard_normal((16,16))
    np.testing.assert_array_equal(result.phase_unwrapped_rad,.7+1.2*normal)


def retarder_assertion():
    result=runner.run_ideal_polarization(fixture_spec())
    # Independent expanded scalar operation, no production matrix helper.
    rows=[(complex(math.cos(float(p)),math.sin(float(p)))/math.sqrt(2),1/math.sqrt(2)+0j) for p in result.phase_wrapped_rad.ravel()]
    for theta,delta in ((.37,math.pi/2),(-.61,math.pi)):
        c,s=math.cos(theta),math.sin(theta)
        q=complex(math.cos(delta),math.sin(delta))
        rows=[((c*c+q*s*s)*x+(1-q)*c*s*y,(1-q)*c*s*x+(s*s+q*c*c)*y) for x,y in rows]
    expected=np.array([[sum(e[a]*e[b].conjugate() for e in rows)/256 for b in (0,1)] for a in (0,1)],dtype=np.complex128)
    np.testing.assert_allclose(result.output.coherency,expected,rtol=2e-14,atol=2e-14)


def controls():
    original_samples=statistics.coherency_from_samples
    original_measure=statistics.measure_coherency
    original_run=runner.run_ideal_polarization
    original_retarder=runner._retarder
    def mean_field(samples,*,probabilities):
        mean=np.sum(probabilities[:,None]*samples,axis=0)
        return original_measure(np.outer(mean,mean.conj()))
    def centered(samples,*,probabilities):
        mean=np.sum(probabilities[:,None]*samples,axis=0)
        centered=samples-mean
        return original_samples(centered,probabilities=probabilities)
    def unbiased(samples,*,probabilities):
        result=original_samples(samples,probabilities=probabilities)
        return original_measure(result.coherency*(len(samples)/(len(samples)-1)))
    def normalize_fields(samples,*,probabilities):
        normalized=samples/np.sqrt(np.sum(np.abs(samples)**2,axis=1))[:,None]
        return original_samples(normalized,probabilities=probabilities)
    def wrong_sign(matrix):
        result=original_measure(matrix)
        s0,s1,s2,s3=result.stokes
        object.__setattr__(result,"stokes",(s0,s1,s2,-s3))
        return result
    def clamp(matrix):
        result=original_measure(matrix)
        object.__setattr__(result,"degree_of_polarization",min(1.,result.degree_of_polarization))
        object.__setattr__(result,"eigenvalues",tuple(max(0.,v) for v in result.eigenvalues))
        return result
    def replace_finite(spec):
        result=original_run(spec)
        object.__setattr__(result.output,"degree_of_polarization",result.population_dop)
        return result
    def different_seed(spec):
        altered=runner.IdealPolarizationSpec(amplitude=spec.amplitude,mean_phase_rad=spec.mean_phase_rad,phase_std_rad=spec.phase_std_rad,qwp_angle_rad=spec.qwp_angle_rad,hwp_angle_rad=spec.hwp_angle_rad,seed=spec.seed+1)
        return original_run(altered)
    def conjugate_retarder(samples,theta,delta):
        return original_retarder(samples,theta,-delta)
    return (
        ("coherent_mean_for_second_moment",statistics,"coherency_from_samples",mean_field,equal_mixture_assertion),
        ("centered_covariance_erases_constant_power",statistics,"coherency_from_samples",centered,constant_assertion),
        ("M_minus_one_normalization",statistics,"coherency_from_samples",unbiased,unequal_power_assertion),
        ("normalize_each_field_erases_amplitude",statistics,"coherency_from_samples",normalize_fields,unequal_power_assertion),
        ("reverse_Stokes_S3",statistics,"measure_coherency",wrong_sign,signed_stokes_assertion),
        ("silently_clip_raw_roundoff",statistics,"measure_coherency",clamp,raw_roundoff_assertion),
        ("population_replaces_actual_finite",runner,"run_ideal_polarization",replace_finite,finite_assertion),
        ("different_seed_mask",runner,"run_ideal_polarization",different_seed,phase_assertion),
        ("conjugate_retarder_phase",runner,"_retarder",conjugate_retarder,retarder_assertion),
    )


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",required=True)
    args=parser.parse_args()
    output=Path(args.output_dir).resolve()
    runs=(ROOT/"runs").resolve()
    if output==runs or not output.is_relative_to(runs) or output.exists() or not output.parent.is_dir():
        raise ValueError("output must be fresh with existing parent strictly inside runs/")
    if subprocess.run(["git","check-ignore","--quiet",str(output)],cwd=ROOT,capture_output=True).returncode!=0:
        raise ValueError("output must be ignored by existing repository rules")
    output.mkdir()
    before=hashes()
    result={"schema":"r03-ideal-focused-negative-controls/1","created_utc":datetime.now(timezone.utc).isoformat(),"argv":[sys.executable,*sys.orig_argv[1:]],"source_before":before,"controls":[],"production_mutations":False,"legacy_mutations":False}
    success=True
    for name,module,attribute,fault,assertion in controls():
        original=getattr(module,attribute)
        record={"name":name,"target":module.__name__+"."+attribute,"independent_assertion":assertion.__name__}
        try:
            assertion()
            record["baseline"]="PASS"
            setattr(module,attribute,fault)
            try:
                assertion()
            except AssertionError as exc:
                record["fault"]="DETECTED_BY_SCIENTIFIC_ASSERTION"
                record["assertion_message"]=str(exc)
            except Exception as exc:
                record["fault"]="SETUP_OR_DOMAIN_ERROR_NOT_DETECTION"
                record["error"]=type(exc).__name__+": "+str(exc)
                success=False
            else:
                record["fault"]="NOT_DETECTED"
                success=False
        except Exception as exc:
            record["baseline"]="FAIL"
            record["error"]=type(exc).__name__+": "+str(exc)
            success=False
        finally:
            setattr(module,attribute,original)
            record["exact_original_function_restored"]=getattr(module,attribute) is original
            try:
                assertion()
                record["restored"]="PASS"
            except Exception as exc:
                record["restored"]="FAIL"
                record["restoration_error"]=traceback.format_exc()
                success=False
        result["controls"].append(record)
        print(name,record.get("baseline"),record.get("fault"),record.get("restored"))
    result["source_after"]=hashes()
    result["source_unchanged"]=before==result["source_after"]
    success=success and result["source_unchanged"] and all(x["exact_original_function_restored"] for x in result["controls"])
    result["status"]="PASS_DETECTION_AND_RESTORATION" if success else "FAIL"
    with (output/"negative_controls.json").open("x",encoding="utf-8") as stream:
        json.dump(result,stream,indent=2,allow_nan=False)
        stream.write("\n")
    print(result["status"])
    print("SOURCE_UNCHANGED",result["source_unchanged"])
    print("EVIDENCE",output/"negative_controls.json")
    return 0 if success else 1


if __name__=="__main__":
    raise SystemExit(main())
