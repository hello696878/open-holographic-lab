r"""Run the modest V2a classical unfolded two-path demonstration.

From the repository root::

    .\.venv\Scripts\python.exe -B -X utf8 examples\two_path_interference.py
    .\.venv\Scripts\python.exe -B -X utf8 examples\two_path_interference.py --n 128

The default uniform 64-by-64 field uses 4 micrometre pitch, wavelength 633 nm
and two 2 mm arms. Every predeclared phase is retained. Output fractions use
the original incident sampled norm; they do not conceal blocked-arm removal.
The independent dense DFT is restricted to one 3-by-4 asymmetric reference.
The resulting JSON/NPZ files are regenerable evidence, not a persistence,
replay or calibrated radiometry contract. No server or GUI is started.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
import json
import math
from pathlib import Path
import platform
import sys
import time
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ohlab import ComplexField, SamplingGrid, propagate_angular_spectrum
from ohlab.optics.interference import (
    TwoArmSpec,
    apply_uniform_phase,
    mix_balanced,
    run_two_arm,
)
from scripts.validate_v2a_interference import (
    PHASES,
    asymmetric_fixture,
    independent_dft_reference,
    norms_to_dict,
    sampled_norm,
)

WAVELENGTH_M = 633e-9
PITCH_M = 4e-6
ARM_DISTANCE_M = 2e-3
ILLUSTRATION_PHASE_RAD = 0.37


@dataclass(frozen=True, kw_only=True, eq=False)
class DemoData:
    """Actual measured rows and the few retained demonstration/reference arrays."""

    report: dict[str, object]
    arrays: dict[str, np.ndarray]


def compute_demo(*, n: int = 64) -> DemoData:
    """Run all eight prescribed phases on the shipped functions, in SI units.

    Only ``n=64`` and ``n=128`` are demonstration options. The phase sweep is
    streamed; only the phi=0.37 field pair is retained for plotting. Reference
    values use independent literal mixing and a physical-coordinate dense DFT
    in the validation script, never a fitted output phase or normalization.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(f"n must be Python int 64 or 128, got {n!r}")
    if n not in (64, 128):
        raise ValueError(f"n must be 64 or 128 for this modest demo, got {n}")
    started = time.perf_counter()
    grid = SamplingGrid(ny=n, nx=n, dy=PITCH_M, dx=PITCH_M)
    incident = ComplexField.uniform(
        grid=grid, wavelength_m=WAVELENGTH_M, amplitude=1.0,
    )
    # Equal-arm algebra is defined against W=P(L)U. This separate public call
    # tests coherent mixing without confusing long-carrier grouping roundoff
    # with the declared 2e-14 mixing bound. The small dense DFT below tests the
    # complete propagation pipeline independently at its own fixed bound.
    equal_arm_w = propagate_angular_spectrum(
        incident, distance_m=ARM_DISTANCE_M, pad_factor=1,
    ).data
    arrays = {"demo_incident": incident.data.copy()}
    sweep = []
    for phase in PHASES:
        spec = TwoArmSpec(
            arm_0_distance_m=ARM_DISTANCE_M,
            arm_1_distance_m=ARM_DISTANCE_M,
            relative_phase_rad=phase,
        )
        run_started = time.perf_counter()
        result = run_two_arm(incident, spec=spec)
        run_seconds = time.perf_counter() - run_started
        phase_factor = complex(math.cos(phase), math.sin(phase))
        expected = (
            (1.0 + phase_factor) * equal_arm_w / 2.0,
            1j * (phase_factor - 1.0) * equal_arm_w / 2.0,
        )
        errors = [
            float(np.max(np.abs(output.data - reference)))
            for output, reference in zip(result.outputs, expected, strict=True)
        ]
        for output, reference in zip(result.outputs, expected, strict=True):
            np.testing.assert_allclose(
                output.data, reference, rtol=2e-14, atol=2e-14,
                err_msg="uniform complete complex-field analytic expression",
            )
        fractions = (math.cos(phase / 2.0) ** 2, math.sin(phase / 2.0) ** 2)
        np.testing.assert_allclose(
            result.norms.output_fractions, fractions,
            rtol=2e-13, atol=2e-13,
            err_msg="lossless output fractions use original incident norm",
        )
        sweep.append({
            "phase_rad": phase,
            "norms": norms_to_dict(result.norms),
            "analytic_fractions_original_input": list(fractions),
            "absolute_max_complex_errors": errors,
            "input_scaled_max_complex_errors": errors,
            "output_intensity_maxima": [
                float(np.max(field.intensity)) for field in result.outputs
            ],
            "shipped_runner_wall_seconds": run_seconds,
        })
        if phase == ILLUSTRATION_PHASE_RAD:
            for index, output in enumerate(result.outputs):
                arrays[f"demo_output_{index}"] = output.data.copy()

    # This is an intentional boundary control, not an additional runner option.
    dark = ComplexField.uniform(
        grid=grid, wavelength_m=WAVELENGTH_M, amplitude=0.0,
    )
    split_0, split_1 = mix_balanced(incident, dark, matrix="B")
    survived = propagate_angular_spectrum(
        split_0, distance_m=ARM_DISTANCE_M, pad_factor=1,
    )
    removed = propagate_angular_spectrum(
        split_1, distance_m=ARM_DISTANCE_M, pad_factor=1,
    )
    incident_norm = sampled_norm(incident.data, dx_m=PITCH_M, dy_m=PITCH_M)
    survivor_norm = sampled_norm(survived.data, dx_m=PITCH_M, dy_m=PITCH_M)
    removed_norm = sampled_norm(removed.data, dx_m=PITCH_M, dy_m=PITCH_M)
    base_outputs = mix_balanced(survived, dark, matrix="B_dagger")
    base_intensities = tuple(field.intensity for field in base_outputs)
    surviving_phase_rows = []
    for phase in PHASES:
        rotated = apply_uniform_phase(survived, phase_rad=phase)
        outputs = mix_balanced(rotated, dark, matrix="B_dagger")
        output_norms = [
            sampled_norm(field.data, dx_m=PITCH_M, dy_m=PITCH_M)
            for field in outputs
        ]
        fractions = [value / incident_norm for value in output_norms]
        np.testing.assert_allclose(
            fractions, [0.25, 0.25], rtol=2e-13, atol=2e-13,
            err_msg="blocked-arm fractions retain the original incident denominator",
        )
        intensity_errors = [
            float(np.max(np.abs(field.intensity - baseline)))
            for field, baseline in zip(outputs, base_intensities, strict=True)
        ]
        np.testing.assert_allclose(intensity_errors, [0.0, 0.0], rtol=0, atol=2e-14)
        surviving_phase_rows.append({
            "phase_on_surviving_arm_0_rad": phase,
            "output_norms": output_norms,
            "output_fractions_original_input": fractions,
            "intensity_max_abs_difference_from_zero_phase": intensity_errors,
        })
    np.testing.assert_allclose(
        [removed_norm / incident_norm, survivor_norm / incident_norm],
        [0.5, 0.5], rtol=2e-13, atol=2e-13,
    )
    blocked = {
        "boundary_operation": "replace propagated arm 1 by a zero field before recombination",
        "incident_norm": incident_norm,
        "removed_norm": removed_norm,
        "survivor_norm": survivor_norm,
        "removed_fraction_original_input": removed_norm / incident_norm,
        "survivor_fraction_original_input": survivor_norm / incident_norm,
        "outputs_norms": surviving_phase_rows[0]["output_norms"],
        "output_fractions_original_input": surviving_phase_rows[0]["output_fractions_original_input"],
        "surviving_phase_rows": surviving_phase_rows,
        "phase_operation_scope": "uniform phase on sole surviving arm 0; not a change to TwoArmSpec",
    }

    reference_parameters = {
        "dy_m": 4.1e-6, "dx_m": 3.7e-6,
        "wavelength_m": WAVELENGTH_M,
        "arm_0_distance_m": 2e-3, "arm_1_distance_m": 3e-3,
        "relative_phase_rad": ILLUSTRATION_PHASE_RAD,
    }
    reference_incident = asymmetric_fixture(ny=3, nx=4)
    reference_grid = SamplingGrid(ny=3, nx=4, dy=4.1e-6, dx=3.7e-6)
    reference_result = run_two_arm(
        ComplexField(
            data=reference_incident, grid=reference_grid, wavelength_m=WAVELENGTH_M,
        ),
        spec=TwoArmSpec(
            arm_0_distance_m=2e-3, arm_1_distance_m=3e-3,
            relative_phase_rad=ILLUSTRATION_PHASE_RAD,
        ),
    )
    independent = independent_dft_reference(reference_incident, **reference_parameters)
    amplitude_scale = float(np.max(np.abs(reference_incident)))
    reference_errors = []
    arrays["reference_incident"] = reference_incident.copy()
    for index, (output, expected) in enumerate(zip(reference_result.outputs, independent, strict=True)):
        difference = output.data - expected
        np.testing.assert_allclose(
            output.data, expected, rtol=1e-11, atol=1e-11 * amplitude_scale,
            err_msg="complete independent physical-coordinate DFT reference",
        )
        reference_errors.append(float(np.max(np.abs(difference))))
        arrays[f"reference_output_{index}"] = output.data.copy()
        arrays[f"independent_reference_{index}"] = expected.copy()
        arrays[f"reference_discrepancy_{index}"] = difference.copy()
    reference_record = {
        "case_id": "asymmetric_3x4",
        "shape": [3, 4],
        **reference_parameters,
        "norms": norms_to_dict(reference_result.norms),
        "absolute_max_complex_errors": reference_errors,
        "input_scaled_max_complex_errors": [value / amplitude_scale for value in reference_errors],
        "reference_scope": "independent coordinates/frequency bins/DFT/branch and literal complex mixers; no alignment or fitted scale",
    }
    report = {
        "kind": "V2a actual shipped-functions standalone demonstration evidence",
        "acceptance_passed": True,
        "environment": {
            "python": platform.python_version(), "interpreter": sys.executable,
            "numpy": np.__version__,
        },
        "scientific_inputs": {
            "ny": n, "nx": n, "dy_m": PITCH_M, "dx_m": PITCH_M,
            "wavelength_m": WAVELENGTH_M,
            "arm_0_distance_m": ARM_DISTANCE_M,
            "arm_1_distance_m": ARM_DISTANCE_M,
            "incident_amplitude": 1.0, "incident_phase_rad": 0.0,
            "phase_points_rad": list(PHASES),
        },
        "port_convention": "ordered (0,1): B=[[1,i],[i,1]]/sqrt(2), recombiner B_dagger=[[1,-i],[-i,1]]/sqrt(2)",
        "frame_model": "ideal scalar classical unfolded model, identical sample correspondence; schematic is not reflection geometry",
        "norm_units": "amplitude-unit^2 * m^2; not calibrated watts",
        "fraction_denominator": "sum(norms.inputs), the original incident norm",
        "residual_sign": "after minus before; signed roundoff is not physical absorption",
        "equal_arm_analytic_reference": "complex algebra against W=P(L)U from one separate existing public ASM call; complete independent propagation tested in the small direct-DFT case",
        "phase_sweep": sweep,
        "blocked_arm": blocked,
        "independent_reference": reference_record,
        "retained_arrays": sorted(arrays),
        "display_policy": "shared raw 0..1 intensity scale; no per-output normalization; uniform equal modes redistribute brightness without invented stripes",
        "computation_wall_seconds": time.perf_counter() - started,
        "timing_scope": "single demo run including streamed sweep, blocked control and small independent DFT, excluding imports and evidence I/O; not a performance guarantee",
    }
    return DemoData(report=report, arrays=arrays)


def _new_evidence_directory(path: Path | None) -> Path:
    """Create one fresh owned directory under ignored runs; refuse reuse."""
    target = path if path is not None else ROOT / "runs" / f"v2a_demo_{uuid.uuid4().hex}"
    target = target.resolve()
    runs_root = (ROOT / "runs").resolve()
    if target == runs_root or not target.is_relative_to(runs_root):
        raise ValueError(f"demo evidence must be a fresh child of {runs_root}, got {target}")
    target.mkdir(parents=True, exist_ok=False)
    return target


def main(argv: Sequence[str] | None = None) -> int:
    """Print raw measurements and retain actual fields in a fresh ignored folder."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", "--size", dest="n", type=int, choices=(64, 128), default=64)
    parser.add_argument("--output", "--output-dir", dest="output", type=Path,
                        help="fresh owned directory below repository runs; must not exist")
    args = parser.parse_args(argv)
    directory = _new_evidence_directory(args.output)
    data = compute_demo(n=args.n)
    encoded = json.dumps(data.report, indent=2, allow_nan=False) + "\n"
    (directory / "demo.json").write_text(encoded, encoding="utf-8")
    np.savez_compressed(directory / "arrays.npz", **data.arrays)
    print(encoded, end="")
    print(f"Evidence directory: {directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
