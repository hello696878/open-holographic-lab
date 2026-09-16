r"""Reproduce the bounded Milestone 3 numerical, timing and memory evidence.

    .\.venv\Scripts\python.exe -B scripts\probe_m3_evidence.py
    .\.venv\Scripts\python.exe -B scripts\probe_m3_evidence.py --section numerics
    .\.venv\Scripts\python.exe -B scripts\probe_m3_evidence.py --section performance
    .\.venv\Scripts\python.exe -B scripts\probe_m3_evidence.py --section memory

JSON lines go to stdout for exact capture in the handoff. Temporary PNG inputs
are removed automatically. This is bounded evidence code, outside the core;
it is not an alternative solver API, production diagnostic or artifact system.
Planning fixture definitions and seeds are preserved; measurements here use
the shipped solver and are not the historical planning measurements.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
import gc
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import tracemalloc

import numpy as np
import scipy
from PIL import Image, __version__ as pillow_version

from ohlab import ComplexField, SamplingGrid
from ohlab.algorithms import GerchbergSaxtonResult, gerchberg_saxton
from ohlab.io.images import load_target_intensity
from ohlab.propagation import angular_spectrum_transfer_function, propagate_angular_spectrum
from ohlab.targets import grayscale8_to_intensity, intensity_to_amplitude

SEEDS = (0, 1, 2, 3)
ITERATIONS = 50
WAVELENGTH_M = 633e-9
DISTANCE_M = 5e-3
RTOL = 1e-12
ATOL = 1e-14
# name, ny, nx, dy [m], dx [m], design. Preserved from the planning probe.
CASES = (
    ("smooth_spot_64", 64, 64, 8e-6, 8e-6, "spot"),
    ("two_features_64", 64, 64, 8e-6, 8e-6, "two"),
    ("two_features_rect", 48, 64, 10e-6, 8e-6, "two"),
)


@dataclass(frozen=True, eq=False)
class Fixture:
    """One fixed planning case; grid lengths are metres, amplitudes are a.u."""
    name: str
    grid: SamplingGrid
    continuous_intensity: np.ndarray
    codes: np.ndarray
    intensity: np.ndarray
    target: np.ndarray
    source: np.ndarray


def planning_fixture(index: int) -> Fixture:
    """Recover the exact predeclared design, quantization and source formula."""
    name, ny, nx, dy, dx, kind = CASES[index]
    grid = SamplingGrid(ny=ny, nx=nx, dy=dy, dx=dx)
    x, y = grid.meshgrid()
    if kind == "spot":
        design = np.exp(-0.5 * ((x / 60e-6)**2 + (y / 60e-6)**2))
    else:
        design = (
            0.65 * np.exp(-0.5 * (((x + 80e-6) / 32e-6)**2 + ((y + 48e-6) / 40e-6)**2))
            + 0.35 * np.exp(-0.5 * (((x - 72e-6) / 40e-6)**2 + ((y - 64e-6) / 28e-6)**2))
        )
    codes = np.rint(255.0 * design).astype(np.uint8)
    intensity = grayscale8_to_intensity(codes, grid=grid)
    target = intensity_to_amplitude(intensity, grid=grid)
    # Preserve the planning expression, including evaluation order.
    source = np.full(grid.shape, np.sqrt(np.mean(intensity)), dtype=np.float64)
    return Fixture(name, grid, design, codes, intensity, target, source)


def decode_fixture_png(fixture: Fixture) -> tuple[np.ndarray, np.ndarray]:
    """Encode uint8 codes to PNG, decode publicly, and return real target arrays."""
    with TemporaryDirectory(prefix="ohlab-m3-evidence-") as directory:
        path = Path(directory) / "target.png"
        with Image.fromarray(fixture.codes) as image:
            image.save(path, format="PNG")
        intensity = load_target_intensity(path, grid=fixture.grid)
    target = intensity_to_amplitude(intensity, grid=fixture.grid)
    return intensity, target


def solve_fixture(
    fixture: Fixture, seed: int, *, target: np.ndarray | None = None,
    source: np.ndarray | None = None,
) -> GerchbergSaxtonResult:
    """Run the shipped solver at 633 nm, +5 mm and 50 complete cycles."""
    return gerchberg_saxton(
        target_amplitude=fixture.target if target is None else target,
        source_amplitude=fixture.source if source is None else source,
        grid=fixture.grid, wavelength_m=WAVELENGTH_M, distance_m=DISTANCE_M,
        iterations=ITERATIONS, seed=seed,
    )


def emit(record: str, **values: object) -> None:
    """Print one unrounded JSON evidence record, preserving raw histories."""
    print(json.dumps({"record": record, **values}, allow_nan=False), flush=True)


def geometry_record(fixture: Fixture) -> dict[str, object]:
    """Measure analytic Theta=kz*z increments, not unwrap(angle(H)), in radians."""
    grid = fixture.grid
    # Centered axes are physically sorted ascending. Axis 1 is fx; axis 0 is fy.
    fx_axis, fy_axis = grid.fx_centered, grid.fy_centered
    assert np.all(np.diff(fx_axis) > 0.0) and np.all(np.diff(fy_axis) > 0.0)
    fx, fy = np.meshgrid(fx_axis, fy_axis, indexing="xy")
    radial = (1.0 / WAVELENGTH_M)**2 - fx**2 - fy**2
    assert np.all(radial >= 0.0)
    # Analytic diagnostic only. Solver physics always comes from the public H.
    kz = 2.0 * np.pi * np.sqrt(radial)
    theta = kz * DISTANCE_M
    derivative_x = 2.0 * np.pi * DISTANCE_M * np.abs(fx) / np.sqrt(radial) / grid.extent_x
    derivative_y = 2.0 * np.pi * DISTANCE_M * np.abs(fy) / np.sqrt(radial) / grid.extent_y
    source_energy, target_energy = float(np.sum(fixture.source**2)), float(np.sum(fixture.target**2))
    return {
        "case": fixture.name, "shape": grid.shape, "dx_m": grid.dx, "dy_m": grid.dy,
        "wavelength_m": WAVELENGTH_M, "distance_m": DISTANCE_M,
        "frequency_order": "ascending physical cycles/m; fx axis 1, fy axis 0",
        "phase_calculation": "Theta=(2*pi*sqrt(1/lambda**2-fx**2-fy**2))*z; diff on adjacent sorted samples, never unwrap(angle(H))",
        "fx_range_cycles_per_m": [float(fx_axis[0]), float(fx_axis[-1])],
        "fy_range_cycles_per_m": [float(fy_axis[0]), float(fy_axis[-1])],
        "dfx_cycles_per_m": 1.0 / grid.extent_x, "dfy_cycles_per_m": 1.0 / grid.extent_y,
        "evanescent_samples": int(np.count_nonzero(radial < 0.0)),
        "max_adjacent_theta_step_x_rad": float(np.max(np.abs(np.diff(theta, axis=1)))),
        "max_adjacent_theta_step_y_rad": float(np.max(np.abs(np.diff(theta, axis=0)))),
        "max_derivative_bin_phase_x_rad": float(np.max(derivative_x)),
        "max_derivative_bin_phase_y_rad": float(np.max(derivative_y)),
        "source_amplitude": float(fixture.source[0, 0]),
        "target_power_au_m2": target_energy * grid.pixel_area,
        "source_power_au_m2": source_energy * grid.pixel_area,
        "relative_power_mismatch": abs(source_energy - target_energy) / max(source_energy, target_energy),
        "target_intensity_range": [float(fixture.intensity.min()), float(fixture.intensity.max())],
        "limitation": "Evidence for these periodic discrete configurations, not a general sampling or isolated-aperture guarantee.",
    }


def numerical_evidence() -> None:
    """Verify all 12 predeclared cases and separate real PNG/quantization evidence."""
    for index in range(len(CASES)):
        fixture = planning_fixture(index)
        emit("geometry", **geometry_record(fixture))
        results = []
        for seed in SEEDS:
            started = time.perf_counter()
            result = solve_fixture(fixture, seed)
            elapsed = time.perf_counter() - started
            results.append(result)
            rebuilt = ComplexField.from_amplitude_phase(
                amplitude=fixture.source, phase=result.phase, grid=fixture.grid,
                wavelength_m=WAVELENGTH_M,
            )
            independently_propagated = propagate_angular_spectrum(
                rebuilt, distance_m=DISTANCE_M, pad_factor=1,
            )
            recomputed = float(
                np.sum((independently_propagated.amplitude - fixture.target)**2)
                / np.sum(fixture.target**2)
            )
            np.testing.assert_allclose(
                independently_propagated.data, result.reconstruction.data, rtol=RTOL, atol=ATOL,
            )
            np.testing.assert_allclose(recomputed, result.residual_history[-1], rtol=RTOL, atol=ATOL)
            history = result.residual_history
            assert history.shape == (ITERATIONS + 1,)
            assert history[-1] < 0.05 and history[-1] < 0.1 * history[0]
            source_power = float(np.sum(fixture.source**2) * fixture.grid.pixel_area)
            np.testing.assert_allclose(
                result.source_field.amplitude, fixture.source, rtol=5e-15, atol=0.0,
            )
            np.testing.assert_allclose(result.reconstruction.power, source_power, rtol=5e-15, atol=0.0)
            emit(
                "shipped_solve", case=fixture.name, seed=seed, iterations=ITERATIONS,
                elapsed_s=elapsed, residual_initial=float(history[0]),
                residual_30=float(history[30]), residual_final=float(history[-1]),
                residual_min=float(history.min()), residual_max=float(history.max()),
                residual_final_over_initial=float(history[-1] / history[0]),
                positive_steps_above_1e_minus_14=int(np.count_nonzero(np.diff(history) > 1e-14)),
                raw_residual_history=history.tolist(),
                independent_final_residual=recomputed,
                max_source_amplitude_error=float(np.max(np.abs(result.source_field.amplitude-fixture.source))),
                max_relative_source_amplitude_error=float(np.max(
                    np.abs(result.source_field.amplitude-fixture.source) / fixture.source)),
                relative_reconstruction_power_error=abs(result.reconstruction.power-source_power) / source_power,
                reforward_phase_max_complex_error=float(np.max(np.abs(
                    independently_propagated.data-result.reconstruction.data))),
                reconstruction_intensity_range=[float(result.reconstruction.intensity.min()),
                                                float(result.reconstruction.intensity.max())],
                acceptance="rho50 < 0.05 and rho50 < 0.1*rho0; only these declared fixtures/seeds",
            )
        decoded_intensity, decoded_target = decode_fixture_png(fixture)
        png_result = solve_fixture(fixture, SEEDS[0], target=decoded_target)
        # EXACTNESS IS THE PROPERTY UNDER TEST: lossless PNG decodes the same
        # codes, and deterministic identical arrays produce identical results.
        for actual, expected in (
            (decoded_intensity, fixture.intensity), (decoded_target, fixture.target),
            (png_result.source_field.data, results[0].source_field.data),
            (png_result.reconstruction.data, results[0].reconstruction.data),
            (png_result.residual_history, results[0].residual_history),
        ):
            np.testing.assert_array_equal(actual, expected)
        continuous_target = intensity_to_amplitude(fixture.continuous_intensity, grid=fixture.grid)
        continuous_source = np.full(
            fixture.grid.shape, np.sqrt(np.mean(fixture.continuous_intensity)), dtype=np.float64,
        )
        continuous_result = solve_fixture(
            fixture, SEEDS[0], target=continuous_target, source=continuous_source,
        )
        demo_amplitude = float(np.sqrt(np.sum(decoded_target**2) / decoded_target.size))
        amplitude_delta = demo_amplitude - float(fixture.source[0, 0])
        emit(
            "png_and_quantization", case=fixture.name, seed=SEEDS[0],
            png_vs_array_intensity_max_error=float(np.max(np.abs(decoded_intensity-fixture.intensity))),
            png_vs_array_source_max_error=float(np.max(np.abs(png_result.source_field.data-results[0].source_field.data))),
            png_vs_array_history_max_error=float(np.max(np.abs(png_result.residual_history-results[0].residual_history))),
            continuous_vs_decoded_intensity_max_error=float(np.max(np.abs(fixture.continuous_intensity-decoded_intensity))),
            continuous_vs_decoded_amplitude_max_error=float(np.max(np.abs(continuous_target-decoded_target))),
            continuous_power_au_m2=float(np.sum(continuous_target**2) * fixture.grid.pixel_area),
            decoded_power_au_m2=float(np.sum(decoded_target**2) * fixture.grid.pixel_area),
            continuous_final_residual=float(continuous_result.residual_history[-1]),
            decoded_final_residual=float(png_result.residual_history[-1]),
            continuous_vs_decoded_final_intensity_max_difference=float(np.max(np.abs(
                continuous_result.reconstruction.intensity-png_result.reconstruction.intensity))),
            planning_source_amplitude=float(fixture.source[0, 0]), demo_source_amplitude=demo_amplitude,
            demo_minus_planning_amplitude=amplitude_delta,
            demo_minus_planning_amplitude_ulps=amplitude_delta / float(np.spacing(fixture.source[0, 0])),
            interpretation="PNG matches uint8-array route exactly. Continuous design is a different target; its solve is separate evidence, not a replacement acceptance fixture.",
        )


def _phase_with_zero_tie(data: np.ndarray) -> np.ndarray:
    phase = np.angle(data)
    phase[phase == -np.pi] = np.pi
    phase[data == 0.0] = 0.0
    return phase


def _benchmark_loop(
    fixture: Fixture, *, hoist_transfer: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Paired probe kernels differing only in public-H reuse; not a second physics model."""
    def transfer(distance: float) -> np.ndarray:
        return angular_spectrum_transfer_function(
            fixture.grid, wavelength_m=WAVELENGTH_M, distance_m=distance,
        )
    if hoist_transfer:
        forward, backward = transfer(DISTANCE_M), transfer(-DISTANCE_M)

    def propagate(data: np.ndarray, distance: float) -> np.ndarray:
        h = (forward if distance > 0.0 else backward) if hoist_transfer else transfer(distance)
        return np.fft.ifft2(np.fft.fft2(data, norm="backward") * h, norm="backward")

    phase = np.random.default_rng(SEEDS[0]).uniform(-np.pi, np.pi, size=fixture.grid.shape)
    source = fixture.source * np.exp(1j * phase)
    history = np.empty(ITERATIONS + 1, dtype=np.float64)
    energy = float(np.sum(fixture.target**2))
    for k in range(ITERATIONS + 1):
        reconstruction = propagate(source, DISTANCE_M)
        history[k] = float(np.sum((np.abs(reconstruction)-fixture.target)**2) / energy)
        if k == ITERATIONS:
            break
        target_projected = fixture.target * np.exp(1j * _phase_with_zero_tie(reconstruction))
        returned = propagate(target_projected, -DISTANCE_M)
        source = fixture.source * np.exp(1j * _phase_with_zero_tie(returned))
    return source, reconstruction, history


def _timed(call: Callable[[], object]) -> float:
    started = time.perf_counter()
    call()
    return time.perf_counter() - started


def performance_evidence() -> None:
    """Measure current solver and isolate H reuse with alternating paired runs."""
    for index in range(len(CASES)):
        fixture = planning_fixture(index)
        shipped = solve_fixture(fixture, SEEDS[0])
        hoisted = _benchmark_loop(fixture, hoist_transfer=True)
        unhoisted = _benchmark_loop(fixture, hoist_transfer=False)
        for a, b in zip(hoisted, unhoisted, strict=True):
            # EXACTNESS IS THE PROPERTY UNDER TEST: identical loop operations
            # with deterministic repeated H versus deterministic stored H.
            np.testing.assert_array_equal(a, b)
        for a, b in zip(
            hoisted, (shipped.source_field.data, shipped.reconstruction.data, shipped.residual_history),
            strict=True,
        ):
            np.testing.assert_allclose(a, b, rtol=RTOL, atol=ATOL)
        times: dict[str, list[float]] = {"shipped": [], "hoisted_probe": [], "unhoisted_probe": []}
        calls = {
            "shipped": lambda: solve_fixture(fixture, SEEDS[0]),
            "hoisted_probe": lambda: _benchmark_loop(fixture, hoist_transfer=True),
            "unhoisted_probe": lambda: _benchmark_loop(fixture, hoist_transfer=False),
        }
        for call in calls.values():
            call()  # One additional warmup after output verification.
        for repeat in range(5):
            order = tuple(calls) if repeat % 2 == 0 else tuple(reversed(calls))
            for name in order:
                times[name].append(_timed(calls[name]))
        medians = {name: statistics.median(values) for name, values in times.items()}
        emit(
            "performance", case=fixture.name, shape=fixture.grid.shape, seed=SEEDS[0],
            iterations=ITERATIONS, repetitions=5, wall_seconds=times, median_seconds=medians,
            hoisted_probe_H_calls=2, unhoisted_probe_H_calls=2 * ITERATIONS + 1,
            unhoisted_over_hoisted_probe_median_ratio=medians["unhoisted_probe"] / medians["hoisted_probe"],
            hoisted_vs_unhoisted_max_source_error=float(np.max(np.abs(hoisted[0]-unhoisted[0]))),
            hoisted_vs_shipped_max_source_error=float(np.max(np.abs(hoisted[0]-shipped.source_field.data))),
            hoisted_vs_shipped_max_history_error=float(np.max(np.abs(hoisted[2]-shipped.residual_history))),
            method="perf_counter, same interpreter, alternating order, warmed. Paired probe kernels differ only in repeated public-H construction. Shipped solver timed separately with its validation/result construction.",
        )


def _working_set() -> dict[str, int]:
    """Read Windows process working set and absolute lifetime peak, in bytes."""
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
        ]
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.argtypes = []
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {
        "working_set_bytes": counters.WorkingSetSize,
        "absolute_process_peak_working_set_bytes": counters.PeakWorkingSetSize,
    }


def memory_child(index: int, kind: str) -> None:
    """Measure one fresh-process solve, tracing separately from OS lifetime peak."""
    fixture = planning_fixture(index)
    gc.collect()
    if kind == "traced":
        tracemalloc.start()
        baseline, _ = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        result = solve_fixture(fixture, SEEDS[0])
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        details = {
            "tracemalloc_baseline_bytes": baseline, "tracemalloc_current_bytes": current,
            "tracemalloc_additional_peak_bytes": peak - baseline,
            "method": "Fresh process, inputs built before tracing. Additional tracked peak includes allocations/lazy initialization during solve; not total process memory.",
        }
    else:
        before = _working_set()
        result = solve_fixture(fixture, SEEDS[0])
        after = _working_set()
        details = {
            "before_solve": before, "after_solve": after,
            "method": "Fresh process without tracemalloc. Windows absolute lifetime peak includes interpreter, imports, inputs, and solve; it is not an incremental solver allocation peak.",
        }
    emit("memory", case=fixture.name, shape=fixture.grid.shape, kind=kind, seed=SEEDS[0],
         iterations=ITERATIONS, final_residual=float(result.residual_history[-1]), **details)


def memory_evidence() -> None:
    """Run isolated tracing and OS measurements rather than infer memory from array size."""
    for index in range(len(CASES)):
        for kind in ("traced", "os"):
            child = subprocess.run(
                [sys.executable, "-B", str(Path(__file__).resolve()),
                 "--memory-child", kind, "--case-index", str(index)],
                capture_output=True, text=True, check=True,
            )
            print(child.stdout.rstrip(), flush=True)


def main() -> None:
    """Emit all evidence by default; sections allow focused reproducible reruns."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--section", choices=("all", "numerics", "performance", "memory"), default="all")
    parser.add_argument("--memory-child", choices=("traced", "os"), help=argparse.SUPPRESS)
    parser.add_argument("--case-index", type=int, choices=range(len(CASES)), default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.memory_child is not None:
        memory_child(args.case_index, args.memory_child)
        return
    emit(
        "environment", python=sys.version, executable=sys.executable, numpy=np.__version__,
        scipy=scipy.__version__, pillow=pillow_version, platform=platform.platform(),
        processor=platform.processor(), logical_cpu_count=os.cpu_count(),
        predeclared_seeds=SEEDS, iterations=ITERATIONS, cases=CASES,
        residual_definition="sum((abs(Pz(U_k))-A_target)**2)/sum(A_target**2), complete grid, k=0..N",
        comparison_tolerances={"rtol": RTOL, "atol": ATOL},
        measurements="Current shipped solver; historical planning measurements remain separately identified.",
    )
    if args.section in ("all", "numerics"):
        numerical_evidence()
    if args.section in ("all", "performance"):
        performance_evidence()
    if args.section in ("all", "memory"):
        memory_evidence()


if __name__ == "__main__":
    main()
