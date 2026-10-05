"""Independent V2a references and measured acceptance, outside the numerical core.

The dense physical-coordinate DFT below constructs its own positions, signed
frequency integers, propagation factors and two-port coefficients. It never
uses a production FFT, grid-array helper, mixer, phase helper or ASM for the
expected fields. Dense work is restricted to at most 256 samples. Evidence is
transient numerical validation, not a persistence/replay format.
"""

from __future__ import annotations

import argparse
import cmath
import ctypes
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
import tracemalloc
import uuid

import numpy as np

from ohlab import ComplexField, SamplingGrid
from ohlab.optics import interference
from ohlab.optics.interference import (
    TwoArmSpec, apply_uniform_phase, mix_balanced, run_two_arm,
)
from ohlab.propagation import propagate_angular_spectrum

ROOT = Path(__file__).resolve().parents[1]
WAVELENGTH_M = 633e-9
PHASES = (0.0, math.pi / 2, math.pi, 3 * math.pi / 2, 2 * math.pi,
          0.37, -0.83, 2.41)
NEAR_DARK_PHASES = (-1e-4, 1e-4, math.pi - 1e-4, math.pi + 1e-4)
TOLERANCES = {
    "unitarity": {"rtol": 0.0, "atol": 2e-15},
    "complex": {"rtol": 2e-14, "atol_input_amplitude_multiplier": 2e-14},
    "direct_dft": {"rtol": 1e-11, "atol_input_amplitude_multiplier": 1e-11},
    "norm": {"rtol": 2e-13, "atol_input_norm_multiplier": 2e-13},
}


def sampled_norm(data: np.ndarray, *, dx_m: float, dy_m: float) -> float:
    """Independent sampled norm in amplitude-unit²·m²; no output normalization."""
    return float(np.sum(np.abs(data) ** 2, dtype=np.float64) * dx_m * dy_m)


def asymmetric_fixture(ny: int = 3, nx: int = 4) -> np.ndarray:
    """Deterministic asymmetric complex amplitudes, with no RNG state."""
    row, col = np.indices((ny, nx))
    return ((1 + .07 * row + .13 * col)
            * np.exp(1j * (.21 + .31 * row - .27 * col + .03 * row * col))).astype(np.complex128)


def independent_dft_propagation(
    data: np.ndarray, *, dy_m: float, dx_m: float,
    wavelength_m: float, distance_m: float,
) -> np.ndarray:
    """Finite direct physical-coordinate propagation, pitches/distances in metres.

    Positions are centered at integer index N//2. FFT-ordered integer bins are
    constructed directly, including the negative even-N Nyquist bin. Explicit
    analysis carries dx*dy; synthesis carries 1/(Lx*Ly). No production helper
    participates. The principal scalar square root preserves forward decay.
    """
    if type(data) is not np.ndarray or data.ndim != 2 or not data.size:
        raise ValueError("direct reference requires a nonempty plain 2-D array")
    ny, nx = data.shape
    if nx * ny > 256:
        raise ValueError(f"dense direct reference is bounded to 256 samples, got {data.size}")
    points = [((col - nx // 2) * dx_m, (row - ny // 2) * dy_m)
              for row in range(ny) for col in range(nx)]
    bins_x = [index if index < (nx + 1) // 2 else index - nx for index in range(nx)]
    bins_y = [index if index < (ny + 1) // 2 else index - ny for index in range(ny)]
    frequencies = [(bx / (nx * dx_m), by / (ny * dy_m))
                   for by in bins_y for bx in bins_x]
    area = dx_m * dy_m
    spectrum = []
    flat = data.ravel()
    for fx, fy in frequencies:
        coefficient = sum(value * cmath.exp(-2j * math.pi * (fx * x + fy * y))
                          for value, (x, y) in zip(flat, points)) * area
        radial = (1 / wavelength_m) ** 2 - fx ** 2 - fy ** 2
        kz = 2 * math.pi * cmath.sqrt(complex(radial))
        spectrum.append(coefficient * cmath.exp(1j * kz * distance_m))
    scale = (nx * dx_m) * (ny * dy_m)
    result = [sum(coefficient * cmath.exp(2j * math.pi * (fx * x + fy * y))
                  for coefficient, (fx, fy) in zip(spectrum, frequencies)) / scale
              for x, y in points]
    return np.asarray(result, dtype=np.complex128).reshape(ny, nx)


def independent_dft_reference(
    data: np.ndarray, *, dy_m: float, dx_m: float, wavelength_m: float,
    arm_0_distance_m: float, arm_1_distance_m: float, relative_phase_rad: float,
    second_input: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Complete independent B -> two travels -> arm-1 phase -> B† reference.

    Optional second input permits simultaneous coherent-input integration
    controls without extending the single-input public runner specification.
    """
    other = np.zeros_like(data) if second_input is None else second_input
    if other.shape != data.shape:
        raise ValueError("direct reference port shapes must match")
    root_two = math.sqrt(2)
    split_0 = (data + 1j * other) / root_two
    split_1 = (1j * data + other) / root_two
    arm_0 = independent_dft_propagation(
        split_0, dy_m=dy_m, dx_m=dx_m, wavelength_m=wavelength_m,
        distance_m=arm_0_distance_m)
    arm_1 = independent_dft_propagation(
        split_1, dy_m=dy_m, dx_m=dx_m, wavelength_m=wavelength_m,
        distance_m=arm_1_distance_m) * cmath.exp(1j * relative_phase_rad)
    return ((arm_0 - 1j * arm_1) / root_two,
            (-1j * arm_0 + arm_1) / root_two)


def norms_to_dict(norms: object) -> dict[str, object]:
    """Serialize the ten measured stage norms and derived declared diagnostics."""
    values = asdict(norms)
    for name in ("inputs_total", "split_total", "propagated_total", "combiner_total",
                 "outputs_total", "split_delta", "propagation_delta", "phase_delta",
                 "recombination_delta", "total_delta", "output_fractions", "total_output_ratio"):
        values[name] = getattr(norms, name)
    return values


def assert_complex_pair(
    actual: tuple[np.ndarray, np.ndarray], expected: tuple[np.ndarray, np.ndarray],
    amplitude: float, *, tolerance: float,
) -> tuple[list[float], list[float]]:
    """Check ordered complex fields without fitting phase or replacing amplitudes."""
    absolute = [float(np.max(np.abs(a - b))) for a, b in zip(actual, expected)]
    for a, b in zip(actual, expected):
        np.testing.assert_allclose(a, b, rtol=tolerance, atol=tolerance * amplitude)
    return absolute, [value / amplitude for value in absolute]


def _process_memory() -> dict[str, int] | None:
    """Instantaneous Windows working set/private bytes and process lifetime peak.

    These are observed whole-process values, not isolated runner/native FFT
    peaks. The lifetime peak cannot be reset per case and is labelled as such.
    """
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
    counter = Counters()
    counter.cb = ctypes.sizeof(counter)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counter), counter.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {"working_set_bytes": int(counter.WorkingSetSize),
            "private_bytes": int(counter.PrivateUsage),
            "process_lifetime_peak_working_set_bytes": int(counter.PeakWorkingSetSize)}


def measure_resources() -> list[dict[str, object]]:
    """Measure shipped runner, separately from planning and before all result release."""
    records = []
    for size, phases in ((64, PHASES), (128, PHASES), (512, (.37,))):
        grid = SamplingGrid(ny=size, nx=size, dy=4e-6, dx=4e-6)
        incident = ComplexField.uniform(grid=grid, wavelength_m=WAVELENGTH_M)
        before = _process_memory()
        tracemalloc.start()
        started = time.perf_counter()
        points = []
        for phase in phases:
            result = run_two_arm(incident, spec=TwoArmSpec(
                arm_0_distance_m=.002, arm_1_distance_m=.002, relative_phase_rad=phase))
            points.append({"phase_rad": phase, "norms": norms_to_dict(result.norms)})
        elapsed = time.perf_counter() - started
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        after = _process_memory()
        records.append({"shape": [size, size], "phase_count": len(phases),
                        "wall_seconds": elapsed, "python_traced_current_bytes": current,
                        "python_traced_peak_bytes": peak, "process_before": before, "process_after": after,
                        "one_complex128_field_bytes": incident.data.nbytes,
                        "final_output_fields_bytes": sum(field.data.nbytes for field in result.outputs),
                        "points": points,
                        "measurement_scope": "single sequential shipped-runner observation; traced allocations are not total process/native memory; process peaks are lifetime values; not a benchmark or sampling guarantee"})
        del result, incident
    return records


def _field(data: np.ndarray, grid: SamplingGrid) -> ComplexField:
    return ComplexField(data=data, grid=grid, wavelength_m=WAVELENGTH_M)


def validate(output: Path) -> dict[str, object]:
    """Execute all declared finite scientific cases, retaining every phase point."""
    report: dict[str, object] = {"acceptance_passed": False, "phases_rad": PHASES,
        "near_dark_phases_rad": NEAR_DARK_PHASES, "tolerances": TOLERANCES,
        "scope": "classical scalar unfolded coherent numerical validation; not calibrated electromagnetic evanescent energy transport, UI or replay",
        "environment": {"interpreter": sys.executable, "python": platform.python_version(),
            "numpy": np.__version__, "scipy": importlib.metadata.version("scipy"),
            "platform": platform.platform(), "interference_source": str(Path(interference.__file__).resolve()),
            "source_sha256": hashlib.sha256(Path(interference.__file__).read_bytes()).hexdigest(),
            "reference_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}
    b = np.asarray([[1, 1j], [1j, 1]], dtype=np.complex128) / math.sqrt(2)
    error = float(np.max(np.abs(b.conj().T @ b - np.eye(2))))
    np.testing.assert_allclose(b.conj().T @ b, np.eye(2), rtol=0, atol=2e-15)
    report["literal_matrix_unitarity_max_abs_error"] = error
    basis_grid = SamplingGrid(ny=1, nx=1, dy=4e-6, dx=4e-6)
    one = _field(np.ones((1, 1), dtype=np.complex128), basis_grid)
    zero_basis = _field(np.zeros((1, 1), dtype=np.complex128), basis_grid)
    actual_b = np.column_stack([[f.data[0, 0] for f in mix_balanced(one, zero_basis, matrix="B")],
                                [f.data[0, 0] for f in mix_balanced(zero_basis, one, matrix="B")]])
    actual_dagger = np.column_stack([[f.data[0, 0] for f in mix_balanced(one, zero_basis, matrix="B_dagger")],
                                     [f.data[0, 0] for f in mix_balanced(zero_basis, one, matrix="B_dagger")]])
    np.testing.assert_allclose(actual_b, b, rtol=0, atol=2e-15)
    np.testing.assert_allclose(actual_dagger @ actual_b, np.eye(2), rtol=0, atol=2e-15)
    # MIT's +iwt field convention conjugates its ideal S. The explicit input/
    # internal/output phase gauges translate its ports to the present B/B†.
    # R=diag(1,-1); Q=[[0,i],[-i,0]]. These are translations, not new optics.
    r = np.diag([1., -1.]).astype(np.complex128)
    q = np.array([[0., 1j], [-1j, 0.]], dtype=np.complex128)
    first_translation = r @ b.conj() @ r
    second_translation = q @ b.conj() @ r
    np.testing.assert_allclose(first_translation, actual_b, rtol=0, atol=2e-15)
    np.testing.assert_allclose(second_translation, actual_dagger, rtol=0, atol=2e-15)
    report["shipped_matrix_and_MIT_translation"] = {
        "B_coefficients_max_abs_error": float(np.max(np.abs(actual_b - b))),
        "B_dagger_B_max_abs_error": float(np.max(np.abs(actual_dagger @ actual_b - np.eye(2)))),
        "R_S_conjugate_R_minus_B_max_abs_error": float(np.max(np.abs(first_translation - actual_b))),
        "Q_S_conjugate_R_minus_B_dagger_max_abs_error": float(np.max(np.abs(second_translation - actual_dagger))),
        "reference": "MIT mirror/interferometer notes, conjugated +iwt convention; explicit R and Q port-phase gauges; inverse mixer is a chosen ideal logical convention"}
    hand_rows = []
    for left, right in ((1 + 2j, .3 - .7j), (1 + 0j, 1j)):
        a = _field(np.full((1, 1), left, dtype=np.complex128), basis_grid)
        v = _field(np.full((1, 1), right, dtype=np.complex128), basis_grid)
        for tag, crossed in (("B", 1j), ("B_dagger", -1j)):
            outputs = mix_balanced(a, v, matrix=tag)
            refs = (np.array([[(left + crossed * right) / math.sqrt(2)]]),
                    np.array([[(crossed * left + right) / math.sqrt(2)]]))
            absolute, scaled = assert_complex_pair(tuple(f.data for f in outputs), refs,
                max(abs(left), abs(right)), tolerance=2e-14)
            before = sampled_norm(a.data, dx_m=basis_grid.dx, dy_m=basis_grid.dy) + sampled_norm(v.data, dx_m=basis_grid.dx, dy_m=basis_grid.dy)
            after = sum(sampled_norm(f.data, dx_m=basis_grid.dx, dy_m=basis_grid.dy) for f in outputs)
            np.testing.assert_allclose(after, before, rtol=2e-13, atol=2e-13 * before)
            hand_rows.append({"inputs": [[left.real, left.imag], [right.real, right.imag]],
                "matrix": tag, "absolute_complex_errors": absolute,
                "input_scaled_max_complex_errors": scaled, "input_norm": before,
                "combined_output_norm": after, "signed_norm_delta": after - before})
    report["hand_coherent_inputs"] = hand_rows
    grid = SamplingGrid(ny=64, nx=64, dy=4e-6, dx=4e-6)
    incident = ComplexField.uniform(grid=grid, wavelength_m=WAVELENGTH_M)
    travelled = propagate_angular_spectrum(incident, distance_m=.002, pad_factor=1).data
    sweep = []
    for phase in PHASES + NEAR_DARK_PHASES:
        result = run_two_arm(incident, spec=TwoArmSpec(
            arm_0_distance_m=.002, arm_1_distance_m=.002, relative_phase_rad=phase))
        factor = cmath.exp(1j * phase)
        refs = ((1 + factor) * travelled / 2, 1j * (factor - 1) * travelled / 2)
        absolute, scaled = assert_complex_pair(tuple(f.data for f in result.outputs), refs, 1., tolerance=2e-14)
        analytic = [math.cos(phase / 2) ** 2, math.sin(phase / 2) ** 2]
        np.testing.assert_allclose(result.norms.output_fractions, analytic, rtol=2e-13, atol=2e-13)
        np.testing.assert_allclose(result.norms.outputs_total, result.norms.inputs_total,
                                   rtol=2e-13, atol=2e-13 * result.norms.inputs_total)
        row = {"phase_rad": phase, "norms": norms_to_dict(result.norms),
               "analytic_fractions": analytic, "absolute_complex_errors": absolute,
               "input_scaled_max_complex_errors": scaled,
               "output_maxima": [float(np.max(f.intensity)) for f in result.outputs]}
        if phase in NEAR_DARK_PHASES:
            dark_port = 1 if abs(phase) < .001 else 0
            signal = float(np.max(np.abs(result.outputs[dark_port].data)))
            assert signal > 1e-5
            assert analytic[dark_port] > 1e-10
            row.update({"near_dark_port": dark_port,
                        "near_dark_max_amplitude": signal,
                        "near_dark_signal_to_absolute_complex_bound": signal / 2e-14})
        sweep.append(row)
        if phase == .37:
            np.savez(output / "demo_phi037.npz", incident=incident.data,
                     output_0=result.outputs[0].data, output_1=result.outputs[1].data)
    report["phase_sweep"] = sweep[:len(PHASES)]
    report["near_dark"] = sweep[len(PHASES):]
    report["equal_arm_complex_reference_scope"] = "independent literal coherent coefficients use W=P(L)U from unchanged public ASM; complete direct-DFT cases below independently verify propagation"
    independent = []
    for ny, nx, z0, z1 in ((3, 4, .002, .003), (5, 6, .002731, .004123), (6, 5, .002731, .004123)):
        case_grid = SamplingGrid(ny=ny, nx=nx, dy=4.1e-6, dx=3.7e-6)
        data = asymmetric_fixture(ny, nx)
        spec = TwoArmSpec(arm_0_distance_m=z0, arm_1_distance_m=z1, relative_phase_rad=.37)
        result = run_two_arm(_field(data, case_grid), spec=spec)
        refs = independent_dft_reference(data, dy_m=case_grid.dy, dx_m=case_grid.dx,
            wavelength_m=WAVELENGTH_M, **asdict(spec))
        absolute, scaled = assert_complex_pair(tuple(f.data for f in result.outputs), refs,
                                                float(np.max(np.abs(data))), tolerance=1e-11)
        case_id = f"asymmetric_{ny}x{nx}"
        filename = case_id + ".npz"
        np.savez(output / filename, incident=data, output_0=result.outputs[0].data,
                 output_1=result.outputs[1].data, reference_0=refs[0], reference_1=refs[1],
                 discrepancy_0=result.outputs[0].data - refs[0], discrepancy_1=result.outputs[1].data - refs[1])
        independent.append({"case_id": case_id, "shape": [ny, nx], "dy_m": case_grid.dy,
            "dx_m": case_grid.dx, "wavelength_m": WAVELENGTH_M, "spec": asdict(spec),
            "absolute_complex_errors": absolute, "input_scaled_max_complex_errors": scaled,
            "norms": norms_to_dict(result.norms), "arrays_file": filename})
    report["independent_cases"] = independent
    # Coherent two-input primitive/integration evidence is separate from fixed runner.
    grid_pair = SamplingGrid(ny=3, nx=4, dy=4.1e-6, dx=3.7e-6)
    a = asymmetric_fixture(3, 4)
    other = (.2 + .4j) * asymmetric_fixture(3, 4)[::-1, ::-1]
    split = mix_balanced(_field(a, grid_pair), _field(other, grid_pair), matrix="B")
    p0 = propagate_angular_spectrum(split[0], distance_m=.002, pad_factor=1)
    p1 = propagate_angular_spectrum(split[1], distance_m=.003, pad_factor=1)
    outputs = mix_balanced(p0, apply_uniform_phase(p1, phase_rad=.37), matrix="B_dagger")
    refs = independent_dft_reference(a, second_input=other, dy_m=grid_pair.dy,
        dx_m=grid_pair.dx, wavelength_m=WAVELENGTH_M, arm_0_distance_m=.002,
        arm_1_distance_m=.003, relative_phase_rad=.37)
    abs_err, scaled_err = assert_complex_pair(tuple(f.data for f in outputs), refs,
        max(float(np.max(np.abs(a))), float(np.max(np.abs(other)))), tolerance=1e-11)
    report["simultaneous_coherent_inputs"] = {"absolute_complex_errors": abs_err,
        "input_scaled_max_complex_errors": scaled_err,
        "input_norms": [sampled_norm(v, dx_m=grid_pair.dx, dy_m=grid_pair.dy) for v in (a, other)],
        "output_norms": [sampled_norm(f.data, dx_m=grid_pair.dx, dy_m=grid_pair.dy) for f in outputs]}
    original = _field(a, grid_pair)
    zero = _field(np.zeros_like(a), grid_pair)
    split = mix_balanced(original, zero, matrix="B")
    input_norm = sampled_norm(a, dx_m=grid_pair.dx, dy_m=grid_pair.dy)
    survivor_norm = sampled_norm(split[0].data, dx_m=grid_pair.dx, dy_m=grid_pair.dy)
    removed_norm = sampled_norm(split[1].data, dx_m=grid_pair.dx, dy_m=grid_pair.dy)
    np.testing.assert_allclose([survivor_norm, removed_norm], [input_norm / 2] * 2,
                               rtol=2e-13, atol=2e-13 * input_norm)
    blocked_rows = []
    for phase in PHASES:
        pair = mix_balanced(apply_uniform_phase(split[0], phase_rad=phase), zero, matrix="B_dagger")
        values = [sampled_norm(f.data, dx_m=grid_pair.dx, dy_m=grid_pair.dy) for f in pair]
        np.testing.assert_allclose(values, [input_norm / 4] * 2, rtol=2e-13, atol=2e-13 * input_norm)
        np.testing.assert_allclose(sum(values), input_norm - removed_norm,
                                   rtol=2e-13, atol=2e-13 * input_norm)
        for actual in pair:
            np.testing.assert_allclose(actual.intensity, np.abs(a) ** 2 / 4,
                                       rtol=2e-13, atol=2e-13 * float(np.max(np.abs(a))) ** 2)
        blocked_rows.append({"surviving_phase_rad": phase, "output_norms": values,
            "output_fractions_original_input": [v / input_norm for v in values]})
    report["blocked_arm"] = {"incident_norm": input_norm, "removed_norm": removed_norm,
        "survivor_norm": survivor_norm, "analytic_removed_norm": input_norm / 2,
        "analytic_survivor_norm": input_norm / 2,
        "outputs_norms": blocked_rows[0]["output_norms"],
        "output_fractions_original_input": blocked_rows[0]["output_fractions_original_input"],
        "surviving_phase_rows": blocked_rows, "removed_stage": "external blocking between splitter and combiner; not the phase stage"}
    carrier = []
    for mode, phase in (("DC", 0.), ("DC", .37), ("off_axis", .37)):
        g = SamplingGrid(ny=5, nx=6, dy=4.1e-6, dx=3.7e-6)
        row, col = np.indices(g.shape)
        u = np.ones(g.shape, dtype=np.complex128)
        fx, fy = 0., 0.
        if mode == "off_axis":
            fx, fy = 1 / (g.nx * g.dx), -1 / (g.ny * g.dy)
            u = np.exp(2j * math.pi * ((col - g.nx // 2) / g.nx - (row - g.ny // 2) / g.ny))
        z0, z1 = WAVELENGTH_M / 7, WAVELENGTH_M / 7 + WAVELENGTH_M / 6
        spec = TwoArmSpec(arm_0_distance_m=z0, arm_1_distance_m=z1, relative_phase_rad=phase)
        result = run_two_arm(_field(u, g), spec=spec)
        kz = 2 * math.pi * math.sqrt((1 / WAVELENGTH_M) ** 2 - fx ** 2 - fy ** 2)
        h0, h1 = cmath.exp(1j * kz * z0), cmath.exp(1j * (kz * z1 + phase))
        refs = ((h0 + h1) * u / 2, 1j * (h1 - h0) * u / 2)
        absolute, scaled = assert_complex_pair(tuple(f.data for f in result.outputs), refs, 1., tolerance=2e-14)
        carrier.append({"mode": mode, "spec": asdict(spec), "norms": norms_to_dict(result.norms),
            "absolute_complex_errors": absolute, "input_scaled_max_complex_errors": scaled,
            "analytic_fractions": [math.cos((kz * (z1 - z0) + phase) / 2) ** 2,
                                    math.sin((kz * (z1 - z0) + phase) / 2) ** 2]})
    report["unequal_length_plane_waves"] = carrier
    ev_grid = SamplingGrid(ny=4, nx=5, dy=.22e-6, dx=.2e-6)
    row, col = np.indices(ev_grid.shape)
    ev = (1 + .3 * np.exp(2j * math.pi * (2 * col / 5 + row / 4))).astype(np.complex128)
    ev_input = _field(ev, ev_grid)
    ev_norm = sampled_norm(ev, dx_m=ev_grid.dx, dy_m=ev_grid.dy)
    ev_refs = independent_dft_reference(ev, dy_m=ev_grid.dy, dx_m=ev_grid.dx,
        wavelength_m=WAVELENGTH_M, arm_0_distance_m=80e-9, arm_1_distance_m=130e-9, relative_phase_rad=.37)
    ev_result = run_two_arm(ev_input, spec=TwoArmSpec(
        arm_0_distance_m=80e-9, arm_1_distance_m=130e-9, relative_phase_rad=.37))
    absolute, scaled = assert_complex_pair(tuple(f.data for f in ev_result.outputs), ev_refs,
                                           float(np.max(np.abs(ev))), tolerance=1e-11)
    assert ev_result.norms.total_output_ratio < .99
    equal_w = independent_dft_propagation(ev, dy_m=ev_grid.dy, dx_m=ev_grid.dx,
        wavelength_m=WAVELENGTH_M, distance_m=100e-9)
    tau = sampled_norm(equal_w, dx_m=ev_grid.dx, dy_m=ev_grid.dy) / ev_norm
    ev_sweep = []
    for phase in PHASES:
        result = run_two_arm(ev_input, spec=TwoArmSpec(
            arm_0_distance_m=100e-9, arm_1_distance_m=100e-9, relative_phase_rad=phase))
        expected = [tau * math.cos(phase / 2) ** 2, tau * math.sin(phase / 2) ** 2]
        np.testing.assert_allclose(result.norms.output_fractions, expected, rtol=2e-13, atol=2e-13)
        ev_sweep.append({"phase_rad": phase, "norms": norms_to_dict(result.norms),
                         "input_normalized_analytic_fractions": expected})
    report["evanescent"] = {"shape": list(ev_grid.shape), "dy_m": ev_grid.dy, "dx_m": ev_grid.dx,
        "unequal_norms": norms_to_dict(ev_result.norms), "absolute_complex_errors": absolute,
        "input_scaled_max_complex_errors": scaled, "equal_arm_distance_m": 100e-9,
        "equal_arm_tau": tau, "equal_arm_sweep": ev_sweep,
        "interpretation": "sampled scalar norm loss from supported forward evanescent decay; not calibrated electromagnetic energy transport"}
    global_factor = cmath.exp(.67j)
    spec = TwoArmSpec(arm_0_distance_m=.002, arm_1_distance_m=.003, relative_phase_rad=.37)
    base = run_two_arm(original, spec=spec)
    rotated = run_two_arm(_field(a * global_factor, grid_pair), spec=spec)
    abs_err, scaled_err = assert_complex_pair(tuple(f.data for f in rotated.outputs),
        tuple(f.data * global_factor for f in base.outputs), float(np.max(np.abs(a))), tolerance=2e-14)
    changed = run_two_arm(original, spec=TwoArmSpec(
        arm_0_distance_m=.002, arm_1_distance_m=.003, relative_phase_rad=.81))
    intensity_difference = max(float(np.max(np.abs(f.intensity - g.intensity)))
                               for f, g in zip(base.outputs, rotated.outputs))
    relative_difference = max(float(np.max(np.abs(f.intensity - g.intensity)))
                              for f, g in zip(base.outputs, changed.outputs))
    assert relative_difference > .01
    report["common_global_phase"] = {"phase_rad": .67, "absolute_complex_errors": abs_err,
        "input_scaled_max_complex_errors": scaled_err, "intensity_max_abs_error": intensity_difference,
        "relative_arm_phase_intensity_change": relative_difference}
    dark = run_two_arm(zero, spec=spec)
    assert all(np.count_nonzero(f.data) == 0 for f in dark.outputs)
    assert dark.norms.output_fractions == (None, None) and dark.norms.total_output_ratio is None
    report["exact_dark_input"] = norms_to_dict(dark.norms)
    report["resources"] = measure_resources()
    report["measured_error_summary"] = {
        "equal_arm_max_input_scaled_complex_error": max(max(row["input_scaled_max_complex_errors"]) for row in sweep),
        "direct_dft_max_input_scaled_complex_error": max(max(row["input_scaled_max_complex_errors"]) for row in independent),
        "coherent_two_input_DFT_max_input_scaled_complex_error": max(report["simultaneous_coherent_inputs"]["input_scaled_max_complex_errors"]),
        "equal_lossless_sweep_max_input_scaled_total_signed_norm_abs": max(abs(row["norms"]["total_delta"]) / row["norms"]["inputs_total"] for row in sweep),
        "equal_lossless_sweep_max_fraction_abs_error": max(max(abs(a - b) for a, b in zip(row["norms"]["output_fractions"], row["analytic_fractions"])) for row in sweep),
        "bounds_unchanged_from_approval": True}
    report["acceptance_passed"] = True
    return report


def fresh_evidence_directory(value: str | None) -> Path:
    """Exclusively create an owned ignored run destination; never replace evidence."""
    path = Path(value) if value else ROOT / "runs" / ("v2a-validation-" + str(uuid.uuid4()))
    path = path.resolve()
    runs = (ROOT / "runs").resolve()
    if not path.is_relative_to(runs) or path == runs:
        raise ValueError(f"evidence must be a fresh directory below {runs}, got {path}")
    if not path.parent.is_dir():
        raise ValueError(f"existing evidence parent required, got {path.parent}")
    path.mkdir(exist_ok=False)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    args = parser.parse_args()
    output = fresh_evidence_directory(args.output)
    try:
        report = validate(output)
    except Exception as exc:
        (output / "failure.json").write_text(json.dumps({"acceptance_passed": False,
            "error_type": type(exc).__name__, "error": str(exc)}, indent=2) + "\n", encoding="utf-8")
        raise
    (output / "evidence.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, allow_nan=False))
    print(f"V2A_INDEPENDENT_VALIDATION_PASSED: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
