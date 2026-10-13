r"""Run the bounded standalone V2f Jones-envelope two-path demonstration.

From the repository root, using the existing project interpreter::

    .\.venv\Scripts\python.exe -B -X utf8 examples\polarized_two_path_interference.py --n 64 --output-dir runs\v2f-demo64-NEW

The alternate demonstration size is 32. No GUI/server/browser is launched.
Raw outputs are retained separately from downstream analyzer outputs. All 17
fixed phase markers, including independently evaluated 0 and 2*pi, remain in
the report. Only selected illustration fields persist, not the entire sweep.
JSON/NPZ files are disposable evidence, not a public result-bundle contract.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ohlab import SamplingGrid
from ohlab.optics.polarization import apply_linear_polarizer, transmission_ratio
from ohlab.optics.polarized_interference import run_polarized_two_arm
from ohlab.propagation import propagate_angular_spectrum
from scripts.validate_v2f_interference import (
    DX, DY, PHASES, arrays, environment_record, fresh_output, make_jones,
    norms_to_dict, run_validation, spec,
)

ILLUSTRATION_PHASE = math.pi / 4


@dataclass(frozen=True, kw_only=True, eq=False)
class DemoData:
    """Actual scalar sweep rows and selected immutable-result field copies."""
    report: dict[str, object]
    arrays: dict[str, np.ndarray]


def compute_demo(*, n: int = 64, measure: bool = True) -> DemoData:
    """Compute real 32/64-grid raw/analyzed sweeps under the ideal fixed model."""
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(f"n must be Python int 32 or 64, got {n!r}")
    if n not in (32, 64):
        raise ValueError(f"n must be 32 or 64, got {n}")
    started = time.perf_counter()
    grid = SamplingGrid(ny=n, nx=n, dy=DY, dx=DX)
    x = (np.arange(n, dtype=np.float64) - n // 2) * DX
    y = (np.arange(n, dtype=np.float64) - n // 2) * DY
    envelope = np.exp(-(x[None, :] ** 2 + y[:, None] ** 2) / (35e-6) ** 2)
    envelope = envelope * np.exp(1j * (.2 * x[None, :] / 35e-6 - .1 * y[:, None] / 35e-6))
    incident = make_jones(envelope, 0, grid=grid)
    original = arrays(incident).tobytes()
    # This larger-grid comparison factors the common propagated envelope via
    # the existing public scalar API. It checks mixing/Jones algebra, not an
    # independent propagation kernel. The separate tiny complete direct sums
    # in validation provide independent complete-pipeline evidence.
    common_w = propagate_angular_spectrum(incident.x, distance_m=.002, pad_factor=1).data
    ain = float(np.max(np.abs(arrays(incident))))
    saved = {"incident_x": incident.x.data.copy(), "incident_y": incident.y.data.copy(),
             "incident_intensity": incident.intensity.copy()}
    rows = []
    for case, a1, j1 in (("identical", (), np.array([1, 0])),
                         ("orthogonal", (("retarder", math.pi / 4, math.pi),), np.array([0, 1]))):
        for phase in PHASES:
            run_started = time.perf_counter()
            result = run_polarized_two_arm(incident, spec=spec(.002, .002, a1=a1, phase=phase))
            run_seconds = time.perf_counter() - run_started
            phase_factor = complex(math.cos(phase), math.sin(phase))
            j0 = np.array([1, 0])
            expected = ((j0 + phase_factor * j1)[:, None, None] * common_w / 2,
                        1j * (phase_factor * j1 - j0)[:, None, None] * common_w / 2)
            errors = []
            for raw, reference in zip(result.outputs, expected):
                np.testing.assert_allclose(arrays(raw), reference, rtol=2e-14, atol=2e-14 * ain)
                errors.append(float(np.max(np.abs(arrays(raw) - reference))))
            raw_bytes = tuple(arrays(raw).tobytes() for raw in result.outputs)
            analyzed = tuple(apply_linear_polarizer(raw, axis_angle_rad=math.pi / 4) for raw in result.outputs)
            assert raw_bytes == tuple(arrays(raw).tobytes() for raw in result.outputs)
            raw_fractions = tuple(transmission_ratio(incident, raw) for raw in result.outputs)
            analyzed_fractions = tuple(transmission_ratio(incident, out) for out in analyzed)
            downstream_fractions = tuple(transmission_ratio(raw, out) for raw, out in zip(result.outputs, analyzed))
            removed = tuple(raw.sampled_norm - out.sampled_norm for raw, out in zip(result.outputs, analyzed))
            # Equal-arm propagation is norm preserving on this chosen discrete
            # propagating-only fixture. No production field is renormalized.
            raw_reference = ((1 + math.cos(phase)) / 2, (1 - math.cos(phase)) / 2) if case == "identical" else (.5, .5)
            analyzed_reference = tuple(value / 2 for value in raw_reference) if case == "identical" else (
                (1 + math.cos(phase)) / 4, (1 - math.cos(phase)) / 4)
            np.testing.assert_allclose(raw_fractions, raw_reference, rtol=2e-13, atol=2e-13)
            np.testing.assert_allclose(analyzed_fractions, analyzed_reference, rtol=2e-13, atol=2e-13)
            np.testing.assert_allclose(sum(analyzed_fractions), .5, rtol=2e-13, atol=2e-13)
            row = {"case": case, "phase_rad": phase, "norms": norms_to_dict(result.norms),
                   "raw_fractions_original_input": raw_fractions,
                   "analyzed_norms": tuple(out.sampled_norm for out in analyzed),
                   "analyzed_fractions_original_input": analyzed_fractions,
                   "analyzed_fractions_downstream_input": downstream_fractions,
                   "removed_norms_at_analyzers": removed,
                   "removed_fractions_original_input": tuple(v / incident.sampled_norm for v in removed),
                   "analytic_raw_fractions": raw_reference, "analytic_analyzed_fractions": analyzed_reference,
                   "complex_absolute_errors": errors, "complex_error_over_Ain": max(errors) / ain,
                   "run_wall_seconds": run_seconds if measure else None}
            rows.append(row)
            if phase == ILLUSTRATION_PHASE:
                for port, (raw, out) in enumerate(zip(result.outputs, analyzed)):
                    for label, field in (("raw", raw), ("analyzed", out)):
                        saved[f"{case}_{label}{port}_x"] = field.x.data.copy()
                        saved[f"{case}_{label}{port}_y"] = field.y.data.copy()
                        saved[f"{case}_{label}{port}_intensity"] = field.intensity.copy()
    assert arrays(incident).tobytes() == original
    validation = run_validation()
    elapsed = time.perf_counter() - started
    return DemoData(report={"acceptance_passed": True, "shape": [n, n], "environment": environment_record(),
                            "demo_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                            "grid": {"dy_m": DY, "dx_m": DX}, "wavelength_m": incident.wavelength_m,
                            "arm_distances_m": [.002, .002], "input_norm": incident.sampled_norm,
                            "phase_markers_rad": PHASES, "illustration_phase_rad": ILLUSTRATION_PHASE,
                            "topology": "incident Jones + zero port -> ideal B -> two forward arms -> terminal ordered Jones actions -> common arm1 phase -> B_dagger -> raw outputs; analyzers separate",
                            "model": "ideal unfolded aligned homogeneous low-angle transverse Jones envelopes; no reflected frame, longitudinal field, plate thickness or calibrated energy claim",
                            "sweep": rows, "validation": validation,
                            "wall_seconds_including_validation": elapsed if measure else None,
                            "large_grid_complex_reference": "public common propagated envelope factored with independent hand Jones/port coefficients; tiny direct sums independently validate complete propagation",
                            "array_retention": "incident and one selected phase per case, raw/analyzed separate; no full sweep/intermediate fields retained",
                            "limitations": "uniform relative phase changes matched-mode brightness; no invented spatial fringes; sampled extrema are not exact continuous visibility; evidence is not a results persistence contract"}, arrays=saved)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, choices=(32, 64), default=64)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "runs" / f"v2f-demo-{uuid.uuid4().hex}")
    args = parser.parse_args()
    output = fresh_output(args.output_dir)
    data = compute_demo(n=args.n)
    array_path = output / "demo_arrays.npz"
    np.savez_compressed(array_path, **data.arrays)
    data.report["demo_arrays_sha256"] = hashlib.sha256(array_path.read_bytes()).hexdigest()
    (output / "demo.json").write_text(json.dumps(data.report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"acceptance_passed": True, "shape": data.report["shape"], "output": str(output),
                      "phase_markers_per_case": len(PHASES), "sweep_rows": len(data.report["sweep"]),
                      "wall_seconds_including_validation": data.report["wall_seconds_including_validation"],
                      "maximum_demo_complex_error_over_Ain": max(r["complex_error_over_Ain"] for r in data.report["sweep"]),
                      "independent_maxima": data.report["validation"]["maxima"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
