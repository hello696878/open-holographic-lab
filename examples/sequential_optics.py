r"""Run the modest, specification-driven V0 optics demonstration without a server.

From the repository root::

    .\.venv\Scripts\python.exe -B -X utf8 examples\sequential_optics.py

The default is a complete 512-by-512 periodic window with 4 micrometre pitch.
The printed JSON is measurement evidence, not a new experiment persistence or
M5 run-bundle format. ``--output`` writes an exclusively created evidence file.
No display normalization, crop, phase mask, or target-power matching enters the
numerical calculation. Analytical references live outside the numerical core.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import gc
import json
import math
from pathlib import Path
import sys
import time
import tracemalloc
from collections.abc import Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ohlab.optics import SequentialExperiment, SequentialResult, run_experiment
from scripts.validate_v0_optics import (
    complex_l2,
    gaussian_reference,
    lens_gaussian_reference,
    second_moment_radius,
)


@dataclass(frozen=True)
class DemoCase:
    """One actual experiment result and its optional independent paraxial field."""

    label: str
    result: SequentialResult
    reference: np.ndarray | None
    complex_relative_l2: float | None
    runtime_s: float


def demo_specs() -> tuple[tuple[str, SequentialExperiment], ...]:
    """Define the six small experiments in SI metres, without hidden parameters."""
    wavelength = 633e-9
    waist = 100e-6
    focal_length = 20e-3
    rayleigh = math.pi * waist**2 / wavelength
    waist_position = focal_length / (1.0 + (focal_length / rayleigh) ** 2)
    common = {
        "schema_version": 1,
        "model_contract": "v0_aligned_scalar_forward_v1",
        "wavelength_m": wavelength,
        "grid": {"ny": 512, "nx": 512, "dy": 4e-6, "dx": 4e-6},
        "source": {
            "kind": "gaussian", "amplitude": 1.0, "phase_rad": 0.0,
            "waist_radius_m": waist, "waist_z_m": 0.0,
            "center_x_m": 0.0, "center_y_m": 0.0,
        },
    }

    def make(components: list[dict[str, object]], z: float) -> SequentialExperiment:
        return SequentialExperiment.from_dict({
            **common, "components": components,
            "observation": {"id": "screen", "z_m": z},
        })

    lens = {"id": "lens", "kind": "thin_lens", "z_m": 0.0,
            "focal_length_m": focal_length}
    cases = [("free", make([], focal_length))]
    for label, z in (
        ("lens_before_waist", waist_position - 2e-3),
        ("lens_at_waist", waist_position),
        ("lens_after_waist", waist_position + 2e-3),
        ("lens_at_f", focal_length),
    ):
        cases.append((label, make([lens], z)))
    aperture = {"id": "aperture", "kind": "circular_aperture", "z_m": 0.0,
                "radius_m": 80e-6}
    cases.append(("aperture_lens", make([aperture, lens], focal_length)))
    return tuple(cases)


def compute_demo() -> tuple[DemoCase, ...]:
    """Execute the declared experiments; only selected modest fields are kept."""
    cases = []
    for label, spec in demo_specs():
        selectors = ("source", "after:aperture") if label == "aperture_lens" else ("source",)
        started = time.perf_counter()
        result = run_experiment(spec, record_fields=selectors)
        elapsed = time.perf_counter() - started
        source = spec.source
        parameters = {
            "wavelength_m": spec.wavelength_m,
            "z_m": spec.observation.z_m,
            "amplitude": source.amplitude,
            "waist_radius_m": source.waist_radius_m,
            "waist_z_m": source.waist_z_m,
            "phase_rad": source.phase_rad,
        }
        if not spec.components:
            reference = gaussian_reference(
                spec.grid, **parameters, center_x_m=source.center_x_m,
                center_y_m=source.center_y_m,
            )
        elif label != "aperture_lens":
            reference = lens_gaussian_reference(
                spec.grid, **parameters,
                focal_length_m=spec.components[0].focal_length_m,
            )
        else:
            # A clipped Gaussian is not the unbounded ABCD Gaussian reference.
            reference = None
        error = None if reference is None else complex_l2(result.observation.data, reference)
        cases.append(DemoCase(label, result, reference, error, elapsed))
    return tuple(cases)


def _process_memory() -> dict[str, int] | None:
    """Read Windows process snapshots in bytes with the existing stdlib only."""
    if sys.platform != "win32":
        return None

    class Counters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {
        "working_set_bytes": int(counters.WorkingSetSize),
        "private_commit_bytes": int(counters.PrivateUsage),
        "process_lifetime_peak_working_set_bytes": int(counters.PeakWorkingSetSize),
    }


def measure_resources() -> dict[str, object]:
    """Measure runtime separately from traced allocations for one shipped train.

    Imports and specification creation precede tracing. No source field exists
    at the tracing baseline. The measured train requests no intermediate fields.
    Windows values are process snapshots and lifetime peaks, not per-call peaks.
    """
    spec = demo_specs()[-1][1]
    gc.collect()
    started = time.perf_counter()
    result = run_experiment(spec)
    runtime = time.perf_counter() - started
    del result
    gc.collect()
    process_before = _process_memory()
    tracemalloc.start()
    baseline_current, baseline_peak = tracemalloc.get_traced_memory()
    result = run_experiment(spec)
    current, peak = tracemalloc.get_traced_memory()
    process_after = _process_memory()
    tracemalloc.stop()
    field_bytes = result.observation.data.nbytes
    del result
    return {
        "experiment": spec.to_dict(),
        "untraced_runtime_s": runtime,
        "single_complex128_field_bytes": field_bytes,
        "tracing_baseline": "imports/spec completed; no field or result retained; gc collected",
        "traced_baseline_current_bytes": baseline_current,
        "traced_baseline_peak_bytes": baseline_peak,
        "traced_current_bytes_with_terminal_result": current,
        "traced_peak_bytes": peak,
        "windows_process_before": process_before,
        "windows_process_after": process_after,
        "process_measurement_scope": "working set/private commit snapshots; peak is lifetime peak, not call-only peak",
        "extrapolated_traced_peak_bytes_1024": peak * 4,
        "extrapolated_traced_peak_bytes_2048": peak * 16,
        "extrapolation_scope": "n-squared estimate for this train, not measured memory or a reservation guarantee",
    }


def demo_report(cases: tuple[DemoCase, ...], resources: dict[str, object]) -> dict[str, object]:
    """Return evidence with actual specifications, unnormalized norms and errors."""
    rows = []
    for case in cases:
        result = case.result
        stages = [{
            "selector": stage.selector, "z_m": stage.z_m, "norm": stage.norm,
            "previous_norm": stage.previous_norm, "delta_norm": stage.delta_norm,
            "transmission_ratio": stage.transmission_ratio,
        } for stage in result.stages]
        rows.append({
            "label": case.label, "experiment": result.experiment.to_dict(),
            "runtime_s": case.runtime_s,
            "terminal_second_moment_radius_m": second_moment_radius(result.observation.data, result.experiment.grid),
            "independent_paraxial_complex_relative_l2": case.complex_relative_l2,
            "reference": "unbounded paraxial Gaussian; no fit/phase alignment" if case.reference is not None else "not supplied for clipped Gaussian; see separate window/pitch convergence validation",
            "stages": stages,
        })
    return {
        "model_contract": "v0_aligned_scalar_forward_v1", "cases": rows,
        "norm_units": "amplitude-unit^2 * m^2", "resources": resources,
        "display_policy": "authoritative arrays unnormalized; figure phase masking is display-only",
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Print the demonstration evidence; optionally create a separate report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="new evidence JSON path; parent must already exist")
    args = parser.parse_args(argv)
    resources = measure_resources()
    cases = compute_demo()
    report = demo_report(cases, resources)
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output is not None:
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
