r"""Bounded classical Jones demonstration; no server, browser or persistence API.

From the repository root, use the existing interpreter::

    .\.venv\Scripts\python.exe -B -X utf8 examples\jones_polarization.py --output-dir runs\v2c-demo64-NEW
    .\.venv\Scripts\python.exe -B -X utf8 examples\jones_polarization.py --n 32 --output-dir runs\v2c-demo32-NEW

The default 64x64 and alternate 32x32 grids use dx=3.7 um, dy=4.1 um and
wavelength 633 nm. Actual arrays for every declared sweep point are retained.
The three-polarizer example has already x-polarized incident light. Ellipses
come from one explicitly identified nonzero sample, with unscaled components
and dimensionless optical phase tau; they are not slowed real-time dynamics.
"""

from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import tracemalloc
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ohlab import SamplingGrid
from ohlab.optics.polarization import apply_linear_polarizer, apply_linear_retarder
from scripts.validate_v2c_polarization import (
    DX_M, DY_M, MALUS_DEGREES, NEAR_OFFSETS, WAVELENGTH_M,
    make_field, run_validation, sample_components,
)


@dataclass(frozen=True, kw_only=True, eq=False)
class DemoData:
    """Actual finite-case report and bounded numerical arrays; no load schema."""

    report: dict[str, object]
    arrays: dict[str, np.ndarray]


def process_memory() -> dict[str, int] | None:
    """Windows whole-process snapshots and lifetime peak, not isolated core peak."""
    if os.name != "nt":
        return None
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                    ("PrivateUsage", ctypes.c_size_t)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {"working_set_bytes": int(counters.WorkingSetSize),
            "private_bytes": int(counters.PrivateUsage),
            "process_lifetime_peak_working_set_bytes": int(counters.PeakWorkingSetSize)}


def measure_resources(*, n: int) -> dict[str, object]:
    """Twenty independent shipped two-element applications, not scratch timing.

    Input construction and reference/JSON work are outside the interval.
    Each iteration starts from the same incident field, applies a polarizer
    then a retarder and retains the final pair. Traced allocations may include
    NumPy-tracked data, but are not total native/process memory. Whole-process
    before/after observations and lifetime peaks have different scopes.
    """
    if tracemalloc.is_tracing():
        raise RuntimeError("resource probe requires no pre-existing allocation tracer")
    grid = SamplingGrid(ny=n, nx=n, dy=DY_M, dx=DX_M)
    incident = make_field(1 + 2j, .3 - .7j, grid=grid)
    before = process_memory()
    tracemalloc.start()
    try:
        started = time.perf_counter()
        for _ in range(20):
            result = apply_linear_retarder(
                apply_linear_polarizer(incident, axis_angle_rad=.37),
                axis_angle_rad=.61, retardance_rad=.83,
            )
        elapsed = time.perf_counter() - started
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    after = process_memory()
    return {"shape": [n, n], "iterations": 20, "element_applications": 40,
            "polarizer_axis_rad": .37, "retarder_axis_rad": .61, "retardance_rad": .83,
            "wall_seconds": elapsed, "wall_seconds_per_two_element_application": elapsed / 20,
            "traced_current_bytes": current, "traced_peak_bytes": peak,
            "process_before": before, "process_after": after,
            "input_component_array_bytes": incident.x.data.nbytes + incident.y.data.nbytes,
            "final_component_array_bytes": result.x.data.nbytes + result.y.data.nbytes,
            "final_sampled_norm": result.sampled_norm,
            "measurement_scope": "single observation of shipped public operations, input/reference/serialization excluded; traced allocations, instantaneous whole-process values and lifetime peaks are distinct, not portable guarantees"}


def compute_demo(*, n: int = 64, measure: bool = True) -> DemoData:
    """Run actual declared cases on n=32 or64; retain amplitudes/common phase."""
    if type(n) is not int or n not in (32, 64):
        raise ValueError("demo n must be Python int 32 or 64")
    started = time.perf_counter()
    validation = run_validation(n=n)
    grid = SamplingGrid(ny=n, nx=n, dy=DY_M, dx=DX_M)
    x_input = make_field(1.0, 0.0, grid=grid)
    root_two = math.sqrt(2)
    linear_45 = make_field(1 / root_two, 1 / root_two, grid=grid)
    fields = {
        "linear_x": x_input,
        "linear45": linear_45,
        "QWP0_linear45": apply_linear_retarder(linear_45, axis_angle_rad=0.0, retardance_rad=math.pi / 2),
        "QWP45_x": apply_linear_retarder(x_input, axis_angle_rad=math.pi / 4, retardance_rad=math.pi / 2),
        "HWP_pi8_x": apply_linear_retarder(x_input, axis_angle_rad=math.pi / 8, retardance_rad=math.pi),
        "crossed": apply_linear_polarizer(apply_linear_polarizer(x_input, axis_angle_rad=0.0), axis_angle_rad=math.pi / 2),
        "three_polarizers": apply_linear_polarizer(apply_linear_polarizer(apply_linear_polarizer(x_input, axis_angle_rad=0.0), axis_angle_rad=math.pi / 4), axis_angle_rad=math.pi / 2),
    }
    arrays: dict[str, np.ndarray] = {}
    for name, field in fields.items():
        arrays[f"{name}_x"] = field.x.data.copy()
        arrays[f"{name}_y"] = field.y.data.copy()
        arrays[f"{name}_intensity"] = field.intensity
    for index, degree in enumerate(MALUS_DEGREES):
        field = apply_linear_polarizer(x_input, axis_angle_rad=math.radians(degree))
        arrays[f"malus_{index:02d}_x"] = field.x.data.copy()
        arrays[f"malus_{index:02d}_y"] = field.y.data.copy()
        arrays[f"malus_{index:02d}_intensity"] = field.intensity
        # Repeated shipped operation equality is a provenance check; the
        # independent scientific bounds remain in run_validation.
        np.testing.assert_array_equal(sample_components(field, (n // 2, n // 2)),
                                      validation["malus"][index]["actual_components"])
    for index, offset in enumerate(NEAR_OFFSETS):
        field = apply_linear_polarizer(x_input, axis_angle_rad=math.pi / 2 + offset)
        arrays[f"weak_{index:02d}_x"] = field.x.data.copy()
        arrays[f"weak_{index:02d}_y"] = field.y.data.copy()
        arrays[f"weak_{index:02d}_intensity"] = field.intensity
        np.testing.assert_array_equal(sample_components(field, (n // 2, n // 2)),
                                      validation["near_extinction"][index]["actual_components"])
    tau = np.linspace(0.0, 2 * math.pi, 257, dtype=np.float64)
    sample = (n // 2, n // 2)
    ellipses = []
    for name in ("linear_x", "linear45", "QWP0_linear45", "QWP45_x", "HWP_pi8_x"):
        field = fields[name]
        components = np.asarray([field.x.data[sample], field.y.data[sample]], dtype=np.complex128)
        assert np.any(components != 0), "ellipse sample must be a named nonzero sample"
        points = np.real(components[:, None] * np.exp(-1j * tau)[None, :]).T
        arrays[f"ellipse_{name}_points"] = points.copy()
        ellipses.append({"case_id": name, "sample_row_col": list(sample),
                         "sample_x_m": 0.0, "sample_y_m": 0.0,
                         "actual_components": sample_components(field, sample),
                         "actual_intensity": float(field.intensity[sample]),
                         "points": points.tolist()})
    arrays["ellipse_tau"] = tau
    report = {"acceptance_passed": True, "shape": [n, n],
              "validation": validation,
              "scope": "actual classical deterministic Jones demonstration, not unpolarized illumination, hardware, V2d imagery or an archive/load schema",
              "ellipse_definition": "Re([Ux,Uy]*exp(-i*tau)) at center sample; tau dimensionless optical phase, not a real-time animation",
              "ellipse_display": "+y downward, equal component-axis scaling, no fitted ellipse or amplitude normalization",
              "ellipse_tau": tau.tolist(), "ellipses": ellipses,
              "case_norms": {name: field.sampled_norm for name, field in fields.items()},
              "demo_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scientific_demo_wall_seconds_excluding_resource_probe_and_serialization": time.perf_counter() - started}
    if measure:
        report["resources"] = measure_resources(n=n)
    return DemoData(report=report, arrays=arrays)


def main() -> int:
    """Save actual JSON rows and complete bounded arrays to a fresh directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, choices=(32, 64), default=64)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "runs" / f"v2c-demo-{uuid.uuid4().hex}")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError(f"fresh empty evidence directory required, got {output}")
    data = compute_demo(n=args.n)
    np.savez(output / "demo_arrays.npz", **data.arrays)
    data.report["demo_arrays_sha256"] = hashlib.sha256((output / "demo_arrays.npz").read_bytes()).hexdigest()
    (output / "demo.json").write_text(json.dumps(data.report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"acceptance_passed": True, "output": str(output), "shape": data.report["shape"],
                      "malus_points": len(MALUS_DEGREES), "weak_points": len(NEAR_OFFSETS),
                      "crossed_ratio": data.report["validation"]["crossed"]["ratio"],
                      "three_polarizers_ratio": data.report["validation"]["three_polarizers"]["ratio"],
                      "maxima": data.report["validation"]["maxima"],
                      "resources": data.report["resources"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
