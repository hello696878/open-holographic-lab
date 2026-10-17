"""Independent ideal-model evidence; no paper-data comparison or fitting.

Use the existing project interpreter with -B and --output-dir pointing to a
fresh ignored directory under runs/. Output is exclusive, never overwritten.
References use hand fixtures, scalar complex sums, direct analyzers and the
existing public deterministic Jones operations on a genuine test-only plane.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np

from ohlab import ComplexField, SamplingGrid
from ohlab.optics.polarization import JonesField, apply_linear_polarizer, apply_linear_retarder
from ohlab.optics.polarization_statistics import analyzer_intensity, coherency_from_samples, measure_coherency
from ohlab.optics.r03_fig2a import IdealPolarizationSpec, run_ideal_polarization

ROOT = Path(__file__).resolve().parents[1]
TOLERANCES = {
    "matrix": {"rtol": 2e-14, "atol_multiplier_mean_S0": 2e-14},
    "observables": {"rtol": 2e-13, "atol_multiplier_mean_S0": 2e-13},
    "dimensionless": {"rtol": 2e-13, "atol": 2e-13},
    "uniform_test_only": {"realizations": 512, "M": 16, "seed": 1742026, "standard_error_multiplier": 6},
    "gaussian_test_only": {"realizations": 512, "M": 16, "seed": 1742027, "std_rad": 1.2, "standard_error_multiplier": 6},
}


def source_hashes() -> dict[str, str]:
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in (
        "src/ohlab/optics/polarization_statistics.py", "src/ohlab/optics/r03_fig2a.py",
        "scripts/validate_r03_fig2a.py",
    )}


def fresh_output(value: str) -> Path:
    output = Path(value).resolve()
    runs = (ROOT/"runs").resolve()
    if not output.is_relative_to(runs) or output == runs or output.exists():
        raise ValueError("--output-dir must be a fresh directory strictly inside this repository's runs/")
    if not output.parent.is_dir():
        raise ValueError("--output-dir parent must already exist")
    ignored = subprocess.run(["git", "check-ignore", "--quiet", str(output)], cwd=ROOT, capture_output=True, check=False)
    if ignored.returncode != 0:
        raise ValueError("--output-dir must be ignored by the existing repository configuration")
    output.mkdir()
    return output


def independent_C(rows: list[tuple[complex, complex]], weights: list[float]) -> np.ndarray:
    return np.array([[sum(p*e[a]*e[b].conjugate() for p,e in zip(weights, rows)) for b in (0,1)] for a in (0,1)], dtype=np.complex128)


def pairs(array: np.ndarray) -> list:
    return [[[float(v.real),float(v.imag)] for v in row] for row in array]


def compare_matrix(actual: np.ndarray, expected: np.ndarray, scale: float) -> float:
    np.testing.assert_allclose(actual,expected,rtol=2e-14,atol=2e-14*scale)
    return float(np.max(np.abs(actual-expected)))/scale if scale else 0.0


def validate() -> dict:
    measurements=[]
    maximum_matrix_error=0.0
    maximum_intensity_error=0.0
    maximum_dop_error=0.0
    hand_cases=(
        ("constant_H",[(1+0j,0j)]*2,[.5,.5],[[1,0],[0,0]],(1,1,0,0),1.),
        ("positive_S3",[(1/math.sqrt(2),1j/math.sqrt(2))],[1.],[[.5,-.5j],[.5j,.5]],(1,0,0,1),1.),
        ("equal_orthogonal",[(1+0j,0j),(0j,1+0j)],[.5,.5],[[.5,0],[0,.5]],(1,0,0,0),0.),
        ("unequal_amplitude_mixture",[(2+0j,0j),(0j,2+0j)],[.75,.25],[[3,0],[0,1]],(4,2,0,0),.5),
        ("constant_D_not_centered",[(1+0j,1+0j)]*2,[.5,.5],[[1,1],[1,1]],(2,0,2,0),1.),
    )
    for name,rows,weights,c,stokes,dop in hand_cases:
        actual=coherency_from_samples(np.array(rows,dtype=np.complex128),probabilities=np.array(weights))
        expected=np.array(c,dtype=np.complex128)
        error=compare_matrix(actual.coherency,expected,stokes[0])
        maximum_matrix_error=max(maximum_matrix_error,error)
        np.testing.assert_allclose(actual.stokes,stokes,rtol=2e-13,atol=2e-13*stokes[0])
        np.testing.assert_allclose(actual.degree_of_polarization,dop,rtol=2e-13,atol=2e-13)
        for theta in (0.,.37,math.pi/4,math.pi/2):
            direct=sum(p*abs(math.cos(theta)*e[0]+math.sin(theta)*e[1])**2 for p,e in zip(weights,rows))
            analyzed=analyzer_intensity(actual,axis_angle_rad=theta)
            np.testing.assert_allclose(analyzed,direct,rtol=2e-13,atol=2e-13*stokes[0])
            maximum_intensity_error=max(maximum_intensity_error,abs(analyzed-direct)/stokes[0])
        measurements.append({"case":name,"actual_C_re_im":pairs(actual.coherency),"actual_stokes":actual.stokes,"DoP":actual.degree_of_polarization,"matrix_absolute_error_over_S0":error})

    model_cases=[]
    # These fixed acceptance fixtures are not a UI sweep or parameter search.
    settings=(
        (1.,0.,0.,0.,0.,0),
        (1.,math.pi,1.2,0.,0.,20261017),
        (2.3,-.7,math.pi,.37,-.61,1),
        (1000.,2*math.pi,.4,-2*math.pi,2*math.pi,2**32-1),
        (0.,.4,1.2,.2,.3,7),
    )
    for amplitude,mean,std,qangle,hangle,seed in settings:
        specification=IdealPolarizationSpec(amplitude=amplitude,mean_phase_rad=mean,phase_std_rad=std,qwp_angle_rad=qangle,hwp_angle_rad=hangle,seed=seed)
        started=time.perf_counter()
        actual=run_ideal_polarization(specification)
        elapsed=time.perf_counter()-started
        # Explicit modern PCG64 is permitted in this validation script. The
        # product uses public default_rng(seed) plus an algorithm identity guard
        # to satisfy the unchanged legacy architecture guard, never an alias.
        normal=np.random.Generator(np.random.PCG64(seed)).standard_normal((16,16))
        expected_unwrapped=mean+std*normal
        np.testing.assert_array_equal(actual.phase_unwrapped_rad,expected_unwrapped)
        np.testing.assert_array_equal(actual.phase_wrapped_rad,np.mod(expected_unwrapped,2*math.pi))
        rows=[(amplitude*complex(math.cos(float(p)),math.sin(float(p)))/math.sqrt(2),amplitude/math.sqrt(2)+0j) for p in actual.phase_wrapped_rad.ravel(order="C")]
        reference=independent_C(rows,[1/256]*256)
        scale=amplitude**2
        stage_errors={"after_slm":compare_matrix(actual.after_slm.coherency,reference,scale)}
        maximum_matrix_error=max(maximum_matrix_error,stage_errors["after_slm"])
        # Existing public Jones operations are an independent runtime reference
        # on this explicitly test-only physical plane; no production fake grid.
        grid=SamplingGrid(ny=16,nx=16,dy=4e-6,dx=3e-6)
        field=JonesField(x=ComplexField(data=np.array([r[0] for r in rows]).reshape(16,16),grid=grid,wavelength_m=633e-9),y=ComplexField(data=np.array([r[1] for r in rows]).reshape(16,16),grid=grid,wavelength_m=633e-9))
        qfield=apply_linear_retarder(field,axis_angle_rad=qangle,retardance_rad=math.pi/2)
        hfield=apply_linear_retarder(qfield,axis_angle_rad=hangle,retardance_rad=math.pi)
        for name,measured,plane in (("after_qwp",actual.after_qwp,qfield),("output",actual.output,hfield)):
            directrows=[(complex(x),complex(y)) for x,y in zip(plane.x.data.ravel(),plane.y.data.ravel())]
            expected=independent_C(directrows,[1/256]*256)
            error=compare_matrix(measured.coherency,expected,scale)
            maximum_matrix_error=max(maximum_matrix_error,error)
            stage_errors[name]=error
        if amplitude:
            finite=abs(sum(complex(math.cos(float(p)),math.sin(float(p))) for p in actual.phase_wrapped_rad.ravel())/256)
            for measured in (actual.after_slm,actual.after_qwp,actual.output):
                np.testing.assert_allclose(measured.degree_of_polarization,finite,rtol=2e-13,atol=2e-13)
                np.testing.assert_allclose(measured.stokes[0],actual.source.stokes[0],rtol=2e-13,atol=2e-13*scale)
                maximum_dop_error=max(maximum_dop_error,abs(measured.degree_of_polarization-finite))
                maximum_intensity_error=max(maximum_intensity_error,abs(measured.stokes[0]-actual.source.stokes[0])/scale)
            projected=apply_linear_polarizer(hfield,axis_angle_rad=.41)
            direct=sum(abs(complex(x))**2+abs(complex(y))**2 for x,y in zip(projected.x.data.ravel(),projected.y.data.ravel()))/256
            np.testing.assert_allclose(analyzer_intensity(actual.output,axis_angle_rad=.41),direct,rtol=2e-13,atol=2e-13*scale)
            maximum_intensity_error=max(maximum_intensity_error,abs(analyzer_intensity(actual.output,axis_angle_rad=.41)-direct)/scale)
        else:
            assert actual.population_dop is None
            assert all(x.degree_of_polarization is None for x in (actual.source,actual.after_slm,actual.after_qwp,actual.output))
        repeated=run_ideal_polarization(specification)
        np.testing.assert_array_equal(repeated.phase_unwrapped_rad,actual.phase_unwrapped_rad)
        np.testing.assert_array_equal(repeated.output.coherency,actual.output.coherency)
        model_cases.append({"settings":asdict(specification),"finite_DoP":actual.output.degree_of_polarization,"population_DoP":actual.population_dop,"stage_matrix_absolute_error_over_amplitude_squared":stage_errors,"runtime_seconds_one_observed_call":elapsed,"phase_arrays_owned_bytes":actual.phase_unwrapped_rad.nbytes+actual.phase_wrapped_rad.nbytes,"four_C_arrays_owned_bytes":sum(x.coherency.nbytes for x in (actual.source,actual.after_slm,actual.after_qwp,actual.output)),"phase_unwrapped_sha256":hashlib.sha256(actual.phase_unwrapped_rad.tobytes()).hexdigest(),"phase_wrapped_sha256":hashlib.sha256(actual.phase_wrapped_rad.tobytes()).hexdigest(),"exact_explicit_PCG64_realization_match":True,"reference_rng":"Generator(PCG64(seed)).standard_normal((16,16)); independent of product default_rng(seed)+PCG64 check"})

    populations=[]
    n,m=512,16
    for distribution,seed,std in (("uniform_test_only",1742026,None),("gaussian_test_only",1742027,1.2)):
        rng=np.random.Generator(np.random.PCG64(seed))
        values=[]
        for _ in range(n):
            phase=rng.uniform(0,2*math.pi,m) if std is None else .4+std*rng.standard_normal(m)
            fields=np.column_stack((np.ones(m),np.exp(1j*phase)))/math.sqrt(2)
            measured=coherency_from_samples(fields,probabilities=np.full(m,1/m))
            values.append(measured.degree_of_polarization**2)
        mu_squared=0. if std is None else math.exp(-std**2)
        expected=mu_squared+(1-mu_squared)/m
        if std is None:
            variance=(m-1)/m**3
        else:
            # Exact fourth moment from index partitions of |sum z_m|^4.
            # E[z]=e^(i*.4-std²/2), E[z²]=e^(2i*.4-2std²).
            fourth=(m+m*(m-1)*(2+math.exp(-4*std**2)+4*mu_squared)+m*(m-1)*(m-2)*(4*mu_squared+2*math.exp(-3*std**2))+m*(m-1)*(m-2)*(m-3)*mu_squared**2)/m**4
            variance=fourth-expected**2
        bound=6*math.sqrt(variance/n)
        observed=float(np.mean(values))
        assert abs(observed-expected)<=bound
        populations.append({"distribution":distribution,"product_distribution":False,"seed":seed,"realizations":n,"M":m,"std_rad":std,"observed_mean_DoP_squared":observed,"predicted_mean_DoP_squared":expected,"single_realization_variance_DoP_squared":variance,"predeclared_6_standard_error_bound":bound,"observed_absolute_discrepancy":abs(observed-expected),"scope":"Bounded fixed test sample, no retry/seed tuning and no per-seed equality or experimental confidence interval."})

    dark=measure_coherency(np.zeros((2,2),dtype=np.complex128))
    assert dark.degree_of_polarization is None
    near=measure_coherency(np.diag([1.,-np.finfo(float).eps]).astype(np.complex128))
    assert near.eigenvalues[0]<0 and near.degree_of_polarization>1 and near.roundoff_limited
    return {"hand_cases":measurements,"fixed_model_cases":model_cases,"test_only_population_checks":populations,"measured_maxima":{"matrix_absolute_error_over_S0_scale":maximum_matrix_error,"intensity_absolute_error_over_S0_scale":maximum_intensity_error,"DoP_absolute_error":maximum_dop_error},"roundoff_policy_probe":{"input_minimum_eigenvalue":near.eigenvalues[0],"retained_raw_DoP":near.degree_of_polarization,"roundoff_limited":near.roundoff_limited,"dark_DoP":dark.degree_of_polarization},"no_experimental_accuracy_claim":True}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",required=True)
    args=parser.parse_args()
    output=fresh_output(args.output_dir)
    before=source_hashes()
    record={"schema":"r03-ideal-independent-validation/1","created_utc":datetime.now(timezone.utc).isoformat(),"argv":[sys.executable,*sys.orig_argv[1:]],"python":sys.version,"numpy":np.__version__,"platform":platform.platform(),"tolerances_predeclared":TOLERANCES,"source_before":before}
    status=0
    try:
        record["validation"]=validate()
        record["status"]="PASS_WITHIN_DECLARED_IDEAL_MODEL"
    except Exception as exc:
        record["status"]="FAIL"
        record["error"]={"type":type(exc).__name__,"message":str(exc)}
        status=1
    finally:
        record["source_after"]=source_hashes()
        record["source_unchanged"]=before==record["source_after"]
        if not record["source_unchanged"]:
            status=1
    with (output/"independent_validation.json").open("x",encoding="utf-8") as stream:
        json.dump(record,stream,indent=2,allow_nan=False)
        stream.write("\n")
    print(record["status"])
    if status:
        print(record.get("error",{}))
    else:
        print(json.dumps(record["validation"]["measured_maxima"],sort_keys=True))
        for item in record["validation"]["test_only_population_checks"]:
            print(item["distribution"],"observed",item["observed_mean_DoP_squared"],"expected",item["predicted_mean_DoP_squared"],"predeclared_bound",item["predeclared_6_standard_error_bound"])
    print("SOURCE_UNCHANGED",record["source_unchanged"])
    print("EVIDENCE",output/"independent_validation.json")
    return status


if __name__=="__main__":
    raise SystemExit(main())
