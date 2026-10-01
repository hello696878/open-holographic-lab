"""Nine isolated scientific negative controls for the new V0 optics modules.

Only the four new optics files are copied. Existing ohlab numerical modules
remain imported from the installed source checkout. Each isolated original
first passes its independent assertion, then an explicit appended mutation
must fail that assertion. Import/setup/validation exceptions never count as
scientific detection. Production hashes must remain unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

REPOSITORY = Path(__file__).resolve().parents[1]
NEW_MODULES = ("__init__.py", "model.py", "elements.py", "simulation.py")

MUTATIONS: dict[str, tuple[str, str, str]] = {
    "wrong_lens_sign": ("elements.py", "signed_lens_complex_phase", '''
# Deliberate isolated fault: reverse the signed focal length.
from dataclasses import replace as _nc_replace
_nc_original_apply = apply_component
def apply_component(field, component):
    if isinstance(component, ThinLens):
        component = _nc_replace(component, focal_length_m=-component.focal_length_m)
    return _nc_original_apply(field, component)
'''),
    "dx_used_for_both_axes": ("elements.py", "hand_listed_anisotropic_circle", '''
# Deliberate isolated fault: compute transmissions with dy=dx.
_nc_original_apply = apply_component
def apply_component(field, component):
    wrong_grid = SamplingGrid(ny=field.grid.ny, nx=field.grid.nx,
                              dy=field.grid.dx, dx=field.grid.dx)
    wrong_field = ComplexField(data=field.data, grid=wrong_grid,
                               wavelength_m=field.wavelength_m)
    output = _nc_original_apply(wrong_field, component)
    return _owned_field(output.data, field.grid, field.wavelength_m)
'''),
    "incorrect_si_units": ("elements.py", "signed_lens_complex_phase", '''
# Deliberate isolated fault: interpret focal length in millimetres as metres.
from dataclasses import replace as _nc_replace
_nc_original_apply = apply_component
def apply_component(field, component):
    if isinstance(component, ThinLens):
        component = _nc_replace(component, focal_length_m=component.focal_length_m*1000)
    return _nc_original_apply(field, component)
'''),
    "omitted_aperture": ("elements.py", "absolute_aperture_transmitted_norm", '''
# Deliberate isolated fault: omit every aperture action.
_nc_original_apply = apply_component
def apply_component(field, component):
    if isinstance(component, (CircularAperture, RectangularAperture)):
        return _owned_field(field.data, field.grid, field.wavelength_m)
    return _nc_original_apply(field, component)
'''),
    "source_amplitude_as_intensity": ("elements.py", "amplitude_two_produces_intensity_four", '''
# Deliberate isolated fault: sqrt the prescribed field amplitude.
from dataclasses import replace as _nc_replace
_nc_original_source = sample_source
def sample_source(experiment):
    wrong_source = _nc_replace(experiment.source, amplitude=math.sqrt(experiment.source.amplitude))
    return _nc_original_source(_nc_replace(experiment, source=wrong_source))
'''),
    "renormalization_after_aperture": ("elements.py", "absolute_aperture_transmitted_norm", '''
# Deliberate isolated fault: restore incident sampled norm after aperture loss.
_nc_original_apply = apply_component
def apply_component(field, component):
    output = _nc_original_apply(field, component)
    if isinstance(component, (CircularAperture, RectangularAperture)):
        before = float(np.sum(np.abs(field.data)**2))
        after = float(np.sum(np.abs(output.data)**2))
        if after:
            output = _owned_field(output.data*math.sqrt(before/after), field.grid, field.wavelength_m)
    return output
'''),
    "wrong_separated_component_order": ("simulation.py", "independent_separated_train_complex_field", '''
# Deliberate isolated fault: exchange separated lens/aperture actions, retaining z order.
_nc_original_run = run_experiment
def run_experiment(experiment, *, record_fields=()):
    spec = experiment.to_dict()
    components = spec['components']
    if len(components) >= 2:
        first, second = components[0].copy(), components[1].copy()
        first_z, second_z = first['z_m'], second['z_m']
        second['z_m'], first['z_m'] = first_z, second_z
        components[0], components[1] = second, first
    wrong = SequentialExperiment.from_dict(spec)
    return _nc_original_run(wrong, record_fields=record_fields)
'''),
    "intermediate_cropping": ("simulation.py", "independent_separated_train_complex_field", '''
# Deliberate isolated fault: discard exterior field after each interval.
_nc_original_propagate = propagate_angular_spectrum
def propagate_angular_spectrum(field, *, distance_m, pad_factor=1):
    output = _nc_original_propagate(field, distance_m=distance_m, pad_factor=pad_factor)
    cropped = output.data.copy()
    ny, nx = cropped.shape
    keep = np.zeros(cropped.shape, dtype=bool)
    keep[max(0,ny//2-1):ny//2+2, max(0,nx//2-1):nx//2+2] = True
    cropped[~keep] = 0
    return _owned_field(cropped, field.grid, field.wavelength_m)
'''),
    "earlier_field_as_observation": ("simulation.py", "independent_terminal_complex_field", '''
# Deliberate isolated fault: coherently relabel source as terminal field.
# Update the scalar terminal norm too, so constructor consistency is not detection.
from dataclasses import replace as _nc_replace
_nc_original_run = run_experiment
def run_experiment(experiment, *, record_fields=()):
    actual = _nc_original_run(experiment, record_fields=record_fields)
    earlier = sample_source(experiment)
    terminal = _nc_replace(actual.stages[-1], norm=_sampled_norm(earlier))
    return _nc_replace(actual, observation=earlier, stages=actual.stages[:-1]+(terminal,))
'''),
}


def production_hashes() -> dict[str, str]:
    return {name: hashlib.sha256((REPOSITORY/"src"/"ohlab"/"optics"/name).read_bytes()).hexdigest()
            for name in NEW_MODULES}


def detecting_assertion(control: str) -> None:
    """Independent expected values, no mutated production helper as oracle."""
    import math
    import numpy as np
    from ohlab.optics import SequentialExperiment, apply_component, run_experiment, sample_source
    from scripts.validate_v0_optics import (WAVELENGTH_M, asymmetric_train_spec,
                                          direct_dft_train, experiment_spec, sampled_norm)
    if control in ("wrong_lens_sign", "incorrect_si_units"):
        spec = experiment_spec(n=7, observation_z_m=0, focal_length_m=.02)
        spec["grid"] = dict(ny=5, nx=7, dy=20e-6, dx=10e-6)
        spec["source"] = dict(kind="uniform", amplitude=2., phase_rad=.31)
        experiment = SequentialExperiment.from_dict(spec)
        output = apply_component(sample_source(experiment), experiment.components[0])
        expected = np.exp(-1j*(2*math.pi/WAVELENGTH_M)*((20e-6)**2+(-20e-6)**2)/(.04))
        np.testing.assert_allclose(output.data[1, 5]/output.data[2, 3], expected,
                                   rtol=2e-14, atol=2e-14)
    elif control == "dx_used_for_both_axes":
        spec = experiment_spec(n=7, observation_z_m=0, aperture_radius_m=20e-6)
        spec["grid"] = dict(ny=5, nx=7, dy=20e-6, dx=10e-6)
        spec["source"] = dict(kind="uniform", amplitude=2., phase_rad=.31)
        experiment = SequentialExperiment.from_dict(spec)
        output = apply_component(sample_source(experiment), experiment.components[0])
        expected = np.zeros((5, 7), dtype=bool)
        expected[1, 3] = expected[3, 3] = True
        expected[2, 1:6] = True
        np.testing.assert_array_equal(output.data != 0, expected)
    elif control in ("omitted_aperture", "renormalization_after_aperture"):
        spec = experiment_spec(n=7, observation_z_m=0, aperture_radius_m=20e-6)
        spec["grid"] = dict(ny=5, nx=7, dy=20e-6, dx=10e-6)
        spec["source"] = dict(kind="uniform", amplitude=2., phase_rad=.31)
        experiment = SequentialExperiment.from_dict(spec)
        output = apply_component(sample_source(experiment), experiment.components[0])
        np.testing.assert_allclose(sampled_norm(output.data, experiment.grid), 7*4*2e-10,
                                   rtol=2e-14, atol=0)
    elif control == "source_amplitude_as_intensity":
        spec = experiment_spec(n=7, observation_z_m=0)
        spec["source"] = dict(kind="uniform", amplitude=2., phase_rad=.31)
        experiment = SequentialExperiment.from_dict(spec)
        output = sample_source(experiment)
        np.testing.assert_allclose(np.abs(output.data)**2, np.full((7, 7), 4.),
                                   rtol=2e-14, atol=2e-14*4)
    else:
        experiment = SequentialExperiment.from_dict(asymmetric_train_spec())
        reference = direct_dft_train(experiment)
        actual = run_experiment(experiment).observation.data
        np.testing.assert_allclose(actual, reference, rtol=1e-10,
                                   atol=1e-10*np.max(np.abs(reference)))


def worker(scratch: Path, control: str) -> int:
    """Overlay only isolated optics; special status 10 means AssertionError."""
    sys.path.insert(0, str(REPOSITORY))
    import ohlab
    ohlab.__path__.insert(0, str(scratch/"ohlab"))
    try:
        import ohlab.optics.elements as elements
        import ohlab.optics.simulation as simulation
        for module in (elements, simulation):
            if not Path(module.__file__).resolve().is_relative_to(scratch.resolve()):
                raise RuntimeError("isolated optics overlay was not used")
        detecting_assertion(control)
    except AssertionError as exc:
        print(json.dumps(dict(status="scientific_assertion_failed", control=control,
                              assertion=MUTATIONS[control][1], detail=str(exc))), flush=True)
        return 10
    except Exception:
        traceback.print_exc()
        return 20
    print(json.dumps(dict(status="independent_assertion_passed", control=control,
                          assertion=MUTATIONS[control][1])), flush=True)
    return 0


def run_controls(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    before = production_hashes()
    records = []
    for control, (module, assertion, mutation) in MUTATIONS.items():
        owned = output/control
        package = owned/"ohlab"/"optics"
        package.mkdir(parents=True, exist_ok=False)
        for name in NEW_MODULES:
            shutil.copyfile(REPOSITORY/"src"/"ohlab"/"optics"/name, package/name)
        command = [sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()),
                   "--worker", str(owned.resolve()), control]
        baseline = subprocess.run(command, capture_output=True, cwd=REPOSITORY)
        (owned/"baseline_stdout.txt").write_bytes(baseline.stdout)
        (owned/"baseline_stderr.txt").write_bytes(baseline.stderr)
        original = (package/module).read_text(encoding="utf-8")
        (package/module).write_text(original+"\n"+mutation, encoding="utf-8")
        mutant = subprocess.run(command, capture_output=True, cwd=REPOSITORY)
        (owned/"mutated_stdout.txt").write_bytes(mutant.stdout)
        (owned/"mutated_stderr.txt").write_bytes(mutant.stderr)
        detected = baseline.returncode == 0 and mutant.returncode == 10
        records.append(dict(control=control, mutated_module=module, actual_mutation=mutation.strip(),
                            independently_detecting_assertion=assertion,
                            command=command, baseline_exit_code=baseline.returncode,
                            mutation_exit_code=mutant.returncode, scientific_detection=detected,
                            baseline_stdout=baseline.stdout.decode("utf-8"),
                            mutated_stdout=mutant.stdout.decode("utf-8"),
                            setup_or_exception_failure=baseline.returncode not in (0, 10) or mutant.returncode not in (0, 10)))
        print(f"{control}: baseline={baseline.returncode}, mutation={mutant.returncode}, detected={detected}", flush=True)
    after = production_hashes()
    report = dict(controls=records, production_hashes_before=before, production_hashes_after=after,
                  production_unchanged=before == after,
                  acceptance_passed=before == after and all(r["scientific_detection"] for r in records),
                  restoration="Production was never mutated; only owned isolated copies retain deliberate faults.",
                  limitations="Nine demonstrated faults; no assertion that all possible scientific defects are detectable.")
    (output/"negative_control_report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    return report


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        return worker(Path(sys.argv[2]), sys.argv[3])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="Fresh exclusively owned ignored scratch directory.")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((REPOSITORY/"runs").resolve()):
        parser.error("negative controls must use an owned directory beneath repository runs/")
    report = run_controls(output)
    print(json.dumps(report, indent=2, allow_nan=False), flush=True)
    return 0 if report["acceptance_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
