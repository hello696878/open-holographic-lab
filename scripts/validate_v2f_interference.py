"""Independent finite references and measured V2f runner acceptance.

Expected tiny fields use literal port/Jones coefficients, independently built
physical coordinates, signed frequency bins and finite complex sums. They use
no production FFT, mesh, propagation, mixer or element helpers. References are
bounded to 64 spatial samples. Evidence is regenerable validation, not a saved
experiment/result contract or a qualified replay claim.
"""
from __future__ import annotations

import argparse
import cmath
import ctypes
from dataclasses import asdict
from decimal import Decimal, localcontext
import hashlib
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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ohlab import ComplexField, SamplingGrid
from ohlab.optics import polarized_interference as core
from ohlab.optics.interference import TwoArmSpec, run_two_arm
from ohlab.optics.polarization import JonesField, apply_linear_polarizer, transmission_ratio
from ohlab.optics.polarized_interference import (
    PolarizerAction, RetarderAction, PolarizationArm, PolarizedTwoArmSpec,
    mix_balanced_jones, run_polarized_two_arm,
)

WAVELENGTH = 633e-9
DX, DY = 3.7e-6, 4.1e-6
PHASES = tuple(k * math.pi / 8 for k in range(17))
EXTRA_PHASES = (.37, -.83, 2.41)
NEAR_PHASES = (-1e-4, 1e-4, -1e-7, 1e-7, -1e-9, 1e-9,
               math.pi - 1e-4, math.pi + 1e-4, math.pi - 1e-7,
               math.pi + 1e-7, math.pi - 1e-9, math.pi + 1e-9)
TOLERANCES = {
    "complex": {"rtol": 2e-14, "atol_Ain": 2e-14},
    "norm": {"rtol": 2e-13, "atol_Nin": 2e-13},
    "direct_sum": {"rtol": 1e-11, "atol_Ain": 1e-11},
    "fraction": {"rtol": 2e-13, "atol": 2e-13},
    "selected_near_dark_fraction": {"rtol": 2e-13, "atol": 1e-40},
}


def direct_propagate(data: np.ndarray, *, dy: float, dx: float,
                     wavelength: float, distance: float) -> np.ndarray:
    """Independent physical-coordinate finite DFT; all lengths in metres."""
    if type(data) is not np.ndarray or data.ndim != 2 or not data.size:
        raise ValueError("direct reference requires a nonempty plain 2-D array")
    ny, nx = data.shape
    if ny * nx > 64:
        raise ValueError(f"direct reference is bounded to 64 samples, got {data.size}")
    positions = [((c - nx // 2) * dx, (r - ny // 2) * dy)
                 for r in range(ny) for c in range(nx)]
    bx = [k if k < (nx + 1) // 2 else k - nx for k in range(nx)]
    by = [k if k < (ny + 1) // 2 else k - ny for k in range(ny)]
    frequencies = [(kx / (nx * dx), ky / (ny * dy)) for ky in by for kx in bx]
    coefficients = []
    for fx, fy in frequencies:
        analyzed = sum(complex(v) * cmath.exp(-2j * math.pi * (fx * x + fy * y))
                       for v, (x, y) in zip(data.ravel(), positions)) * dx * dy
        kz = 2 * math.pi * cmath.sqrt(complex((1 / wavelength) ** 2 - fx ** 2 - fy ** 2))
        coefficients.append(analyzed * cmath.exp(1j * kz * distance))
    result = [sum(v * cmath.exp(2j * math.pi * (fx * x + fy * y))
                  for v, (fx, fy) in zip(coefficients, frequencies)) /
              ((nx * dx) * (ny * dy)) for x, y in positions]
    return np.asarray(result, dtype=np.complex128).reshape(ny, nx)


def literal_action(operation: tuple) -> np.ndarray:
    """Expanded ideal Jones coefficients; selected-axis phase zero."""
    kind, theta, *rest = operation
    c, s = math.cos(theta), math.sin(theta)
    if kind == "polarizer":
        return np.asarray([[c * c, c * s], [c * s, s * s]], dtype=np.complex128)
    if kind != "retarder" or len(rest) != 1:
        raise ValueError(f"unknown literal action {operation!r}")
    q = cmath.exp(1j * rest[0])
    return np.asarray([[c * c + q * s * s, (1 - q) * c * s],
                       [(1 - q) * c * s, s * s + q * c * c]], dtype=np.complex128)


def literal_block() -> np.ndarray:
    """B in fixed order (port0.x, port0.y, port1.x, port1.y)."""
    return np.asarray([[1, 0, 1j, 0], [0, 1, 0, 1j],
                       [1j, 0, 1, 0], [0, 1j, 0, 1]], dtype=np.complex128) / math.sqrt(2)


def direct_path(incident: np.ndarray, distance_0: float, distance_1: float,
                actions_0: tuple, actions_1: tuple, phase: float, *,
                dy: float, dx: float, wavelength: float) -> tuple[np.ndarray, np.ndarray]:
    """Complete independent path; input/output shapes (2,ny,nx), no phase fit."""
    if incident.ndim != 3 or incident.shape[0] != 2:
        raise ValueError("reference incident must have shape (2,ny,nx)")
    block = literal_block()
    split = np.einsum("ab,bij->aij", block,
                      np.concatenate((incident, np.zeros_like(incident)), axis=0))
    ends = []
    for arm_index, distance, operations in ((0, distance_0, actions_0), (1, distance_1, actions_1)):
        arm = np.stack([direct_propagate(split[2 * arm_index + component], dy=dy, dx=dx,
                                        wavelength=wavelength, distance=distance) for component in (0, 1)])
        for operation in operations:
            arm = np.einsum("ab,bij->aij", literal_action(operation), arm)
        ends.append(arm)
    before = np.concatenate((ends[0], cmath.exp(1j * phase) * ends[1]), axis=0)
    outputs = np.einsum("ab,bij->aij", block.conj().T, before)
    return outputs[:2], outputs[2:]


def decimal_sincos(angle: float) -> tuple[Decimal, Decimal]:
    """80-digit sine/cosine at the actual supplied binary64 angle."""
    with localcontext() as context:
        context.prec = 80
        value = Decimal.from_float(angle)
        sine, st, cosine, ct = value, value, Decimal(1), Decimal(1)
        for n in range(1, 120):
            st *= -value * value / Decimal((2 * n) * (2 * n + 1))
            ct *= -value * value / Decimal((2 * n - 1) * (2 * n))
            sine += st
            cosine += ct
            if abs(st) < Decimal("1e-78") and abs(ct) < Decimal("1e-78"):
                return +sine, +cosine
        raise AssertionError("bounded Decimal series did not converge")


def independent_norm(data: np.ndarray, *, dx: float = DX, dy: float = DY) -> float:
    """Jones combined reduction, amplitude-unit²*m²; data shape (2,ny,nx)."""
    return float(np.sum(np.abs(data[0]) ** 2 + np.abs(data[1]) ** 2,
                        dtype=np.float64) * dx * dy)


def arrays(value: JonesField) -> np.ndarray:
    """Expose both actual transverse arrays for ordered comparisons."""
    return np.stack((value.x.data, value.y.data))


def make_jones(x: object, y: object, *, grid: SamplingGrid | None = None) -> JonesField:
    """Construct valid actual public fields; x/y amplitude arrays or scalars."""
    grid = grid or SamplingGrid(ny=2, nx=3, dy=DY, dx=DX)
    def component(value: object) -> ComplexField:
        data = np.asarray(value, dtype=np.complex128)
        if data.ndim == 0:
            data = np.full(grid.shape, data, dtype=np.complex128)
        return ComplexField(data=data, grid=grid, wavelength_m=WAVELENGTH)
    return JonesField(x=component(x), y=component(y))


def actions(operations: tuple) -> tuple:
    """Convert independent fixture descriptions to public request records."""
    return tuple(PolarizerAction(axis_angle_rad=op[1]) if op[0] == "polarizer" else
                 RetarderAction(axis_angle_rad=op[1], retardance_rad=op[2]) for op in operations)


def spec(z0: float = 0.0, z1: float = 0.0, a0: tuple = (), a1: tuple = (), phase: float = .37) -> PolarizedTwoArmSpec:
    """Actual fixed-topology request, distances m and phase rad."""
    return PolarizedTwoArmSpec(arm_0=PolarizationArm(distance_m=z0, actions=actions(a0)),
                              arm_1=PolarizationArm(distance_m=z1, actions=actions(a1)),
                              relative_phase_rad=phase)


def norms_to_dict(value: object) -> dict[str, object]:
    """Measured six checkpoints/action histories and all declared diagnostics."""
    result = asdict(value)
    for name in ("inputs_total", "split_total", "propagated_total", "elements_total", "combiner_total", "outputs_total",
                 "split_delta", "propagation_delta", "elements_delta", "phase_delta", "recombination_delta", "total_delta",
                 "propagation_deltas", "element_deltas", "phase_deltas", "arm_action_deltas", "output_fractions", "total_output_ratio"):
        result[name] = getattr(value, name)
    return result


def check_pair(actual: tuple, expected: tuple, ain: float, *, tolerance: float = 2e-14) -> dict[str, object]:
    """Absolute and input-scaled max complex errors; no fitted alignment."""
    errors = []
    for observed, reference in zip(actual, expected, strict=True):
        observed = arrays(observed) if isinstance(observed, JonesField) else observed
        # Hand Jones states are spatially uniform. Explicitly replicate that
        # declared uniform reference; assert_allclose itself forbids differing
        # array shapes even when their ordinary arithmetic broadcasts.
        if reference.shape == (2, 1, 1) and observed.ndim == 3 and observed.shape[0] == 2:
            reference = np.broadcast_to(reference, observed.shape)
        elif reference.shape != observed.shape:
            raise AssertionError(f"complete reference shape {reference.shape} differs from actual {observed.shape}")
        np.testing.assert_allclose(observed, reference, rtol=tolerance, atol=tolerance * ain)
        errors.append(float(np.max(np.abs(observed - reference))))
    return {"max_absolute_by_port": errors, "max_absolute_over_Ain": max(errors) / ain if ain else 0.0}


def overlap(j0: np.ndarray, j1: np.ndarray) -> complex:
    """Independent Hermitian overlap; complex first arm matters."""
    return complex(np.sum(np.conj(j0) * j1))


def near_dark_checks() -> list[dict[str, object]]:
    source = make_jones(1, 0)
    nin = independent_norm(arrays(source))
    rows = []
    for phase in NEAR_PHASES:
        result = run_polarized_two_arm(source, spec=spec(phase=phase))
        port = 1 if abs(phase) < 1e-3 else 0
        sine, cosine = decimal_sincos(phase)
        with localcontext() as context:
            context.prec = 80
            reference = float(((1 - cosine) ** 2 + sine * sine) / 4 if port == 1 else
                              ((1 + cosine) ** 2 + sine * sine) / 4)
            component = (complex(float(-sine / 2), float((cosine - 1) / 2)) if port == 1 else
                         complex(float((1 + cosine) / 2), float(sine / 2)))
        measured = result.norms.output_fractions[port]
        assert measured is not None and measured > 0 and np.any(arrays(result.outputs[port]) != 0)
        np.testing.assert_allclose(measured, reference, rtol=2e-13, atol=1e-40)
        np.testing.assert_allclose(result.norms.outputs[port], reference * nin, rtol=2e-13, atol=1e-40 * nin)
        actual_component = complex(result.outputs[port].x.data[0, 0])
        np.testing.assert_allclose(actual_component, component, rtol=2e-14, atol=2e-14)
        rows.append({"phase_rad": phase, "dark_port": port, "actual_fraction": measured,
                     "decimal_fraction_at_actual_binary64_phase": reference,
                     "absolute_error": abs(measured - reference), "relative_error": abs(measured - reference) / reference,
                     "actual_component": [actual_component.real, actual_component.imag],
                     "decimal_component": [component.real, component.imag],
                     "component_absolute_error": abs(actual_component - component),
                     "nonzero_signal_retained": True,
                     "smaller_quadrature_rounded_to_zero": bool((component.real != 0 and actual_component.real == 0) or
                                                                 (component.imag != 0 and actual_component.imag == 0))})
    return rows


def run_validation() -> dict[str, object]:
    """Exercise shipped functions with independent complete-field acceptance."""
    caller_settings = np.geterr().copy()
    block = literal_block()
    unitarity = float(np.max(np.abs(block.conj().T @ block - np.eye(4))))
    np.testing.assert_allclose(block.conj().T @ block, np.eye(4), rtol=0, atol=2e-15)
    p0, p1 = make_jones(1 + 2j, -.4 + .6j), make_jones(.3 - .7j, 2.1 + .2j)
    inputs = np.concatenate((arrays(p0), arrays(p1)), axis=0)
    mixing = []
    for name, matrix in (("B", block), ("B_dagger", block.conj().T)):
        actual = mix_balanced_jones(p0, p1, matrix=name)
        expected = np.einsum("ab,bij->aij", matrix, inputs)
        mixing.append({"matrix": name, **check_pair(actual, (expected[:2], expected[2:]), float(np.max(np.abs(inputs))))})
    source = make_jones(1, 0)
    nin = independent_norm(arrays(source))
    cases = {
        "A_identical": ((), (), np.array([1, 0]), np.array([1, 0])),
        "B_orthogonal_linear": ((), (("retarder", math.pi / 4, math.pi),), np.array([1, 0]), np.array([0, 1])),
        "D_complex_overlap": ((), (("retarder", math.pi / 4, math.pi / 2),), np.array([1, 0]), np.array([(1 + 1j) / 2, (1 - 1j) / 2])),
        "D_complex_first_arm": ((("retarder", math.pi / 8, math.pi), ("retarder", 0.0, math.pi / 2)),
                                (("retarder", math.pi / 8, math.pi),), np.array([1, 1j]) / math.sqrt(2), np.array([1, 1]) / math.sqrt(2)),
        "common_retarder_phase": ((), (("retarder", math.pi / 2, math.pi),), np.array([1, 0]), np.array([-1, 0])),
    }
    rows = []
    for name, (a0, a1, j0, j1) in cases.items():
        gamma = overlap(j0, j1)
        for phase in PHASES + EXTRA_PHASES:
            result = run_polarized_two_arm(source, spec=spec(a0=a0, a1=a1, phase=phase))
            factor = cmath.exp(1j * phase)
            expected = ((j0 + factor * j1)[:, None, None] / 2,
                        1j * (factor * j1 - j0)[:, None, None] / 2)
            discrepancy = check_pair(result.outputs, expected, 1.0)
            fractions = ((1 + (factor * gamma).real) / 2, (1 - (factor * gamma).real) / 2)
            np.testing.assert_allclose(result.norms.output_fractions, fractions, rtol=2e-13, atol=2e-13)
            np.testing.assert_allclose(result.norms.outputs, np.array(fractions) * nin, rtol=2e-13, atol=2e-13 * nin)
            before = tuple(arrays(f).tobytes() for f in result.outputs)
            analyzed = tuple(apply_linear_polarizer(f, axis_angle_rad=math.pi / 4) for f in result.outputs)
            analyzed_fractions = tuple(transmission_ratio(source, f) for f in analyzed)
            removed = tuple(raw.sampled_norm - out.sampled_norm for raw, out in zip(result.outputs, analyzed))
            assert before == tuple(arrays(f).tobytes() for f in result.outputs)
            row = {"case": name, "phase_rad": phase, "gamma": [gamma.real, gamma.imag],
                   "actual_fractions": result.norms.output_fractions, "analytic_fractions": fractions,
                   "fraction_max_absolute_error": max(abs(a - b) for a, b in zip(result.norms.output_fractions, fractions)),
                   "complex": discrepancy, "norms": norms_to_dict(result.norms),
                   "analyzed_fractions_original_input": analyzed_fractions,
                   "analyzed_fractions_downstream_input": tuple(transmission_ratio(raw, out) for raw, out in zip(result.outputs, analyzed)),
                   "analyzer_removed_norms": removed,
                   "raw_sample": [[[complex(v).real, complex(v).imag] for v in arrays(f)[:, 0, 0]] for f in result.outputs],
                   "expected_sample": [[[complex(v).real, complex(v).imag] for v in f[:, 0, 0]] for f in expected]}
            if name == "B_orthogonal_linear":
                predicted = ((1 + math.cos(phase)) / 4, (1 - math.cos(phase)) / 4)
                np.testing.assert_allclose(analyzed_fractions, predicted, rtol=2e-13, atol=2e-13)
                np.testing.assert_allclose(sum(analyzed_fractions), .5, rtol=2e-13, atol=2e-13)
                row["analyzed_analytic_fractions"] = predicted
                row["analyzed_max_absolute_error"] = max(abs(a - b) for a, b in zip(analyzed_fractions, predicted))
            rows.append(row)
    anchor = next(row for row in rows if row["case"] == "D_complex_first_arm" and row["phase_rad"] == math.pi / 2)
    np.testing.assert_allclose(anchor["actual_fractions"], (.75, .25), rtol=2e-13, atol=2e-13)
    np.testing.assert_allclose(anchor["gamma"], (.5, -.5), rtol=0, atol=2e-15)
    circular = make_jones(1 / math.sqrt(2), 1 / math.sqrt(2))
    circular_ain = float(np.max(np.abs(arrays(circular))))
    circular_rows = []
    for phase in PHASES:
        result = run_polarized_two_arm(circular, spec=spec(a0=(("retarder", 0., math.pi / 2),),
                                                        a1=(("retarder", 0., -math.pi / 2),), phase=phase))
        states = (np.array([1, 1j]) / math.sqrt(2), np.array([1, -1j]) / math.sqrt(2))
        factor = cmath.exp(1j * phase)
        check = check_pair(result.outputs, ((states[0] + factor * states[1])[:, None, None] / 2,
                                            1j * (factor * states[1] - states[0])[:, None, None] / 2), circular_ain)
        np.testing.assert_allclose(result.norms.output_fractions, (.5, .5), rtol=2e-13, atol=2e-13)
        circular_rows.append({"phase_rad": phase, "Ain": circular_ain, "actual_fractions": result.norms.output_fractions, "complex": check})
    lossy = []
    for phase in PHASES:
        result = run_polarized_two_arm(source, spec=spec(a1=(("polarizer", math.pi / 3),), phase=phase))
        j0, j1 = np.array([1, 0]), np.array([.25, math.sqrt(3) / 4])
        factor = cmath.exp(1j * phase)
        complex_check = check_pair(result.outputs, ((j0 + factor * j1)[:, None, None] / 2,
                                                   1j * (factor * j1 - j0)[:, None, None] / 2), 1.)
        expected = (5 / 16 + math.cos(phase) / 8, 5 / 16 - math.cos(phase) / 8)
        np.testing.assert_allclose(result.norms.output_fractions, expected, rtol=2e-13, atol=2e-13)
        np.testing.assert_allclose(result.norms.outputs_total / nin, 5 / 8, rtol=2e-13, atol=2e-13)
        lossy.append({"phase_rad": phase, "actual_fractions": result.norms.output_fractions,
                      "analytic_fractions": expected, "retained_original_input": result.norms.outputs_total / nin,
                      "removed_original_input": (nin - result.norms.outputs_total) / nin,
                      "complex": complex_check, "norms": norms_to_dict(result.norms)})
    dense = []
    a0, a1 = (("polarizer", .23), ("retarder", -.41, .71)), (("retarder", .61, -.83), ("polarizer", -.37))
    for ny, nx in ((3, 4), (5, 6), (6, 5)):
        grid = SamplingGrid(ny=ny, nx=nx, dy=DY, dx=DX)
        r, c = np.indices(grid.shape)
        x = (1 + .07 * r + .13 * c) * np.exp(1j * (.21 + .31 * r - .27 * c + .03 * r * c))
        y = (.19 + .03 * r + .05 * c) * np.exp(1j * (-.73 + .17 * r + .11 * c))
        incident = make_jones(x, y, grid=grid)
        original = arrays(incident).tobytes()
        result = run_polarized_two_arm(incident, spec=spec(.002731, .004123, a0, a1, .37))
        started = time.perf_counter()
        expected = direct_path(arrays(incident), .002731, .004123, a0, a1, .37, dy=DY, dx=DX, wavelength=WAVELENGTH)
        reference_seconds = time.perf_counter() - started
        ain = float(np.max(np.abs(arrays(incident))))
        input_norm = independent_norm(arrays(incident))
        check = check_pair(result.outputs, expected, ain, tolerance=1e-11)
        expected_norms = tuple(independent_norm(f) for f in expected)
        np.testing.assert_allclose(result.norms.outputs, expected_norms, rtol=2e-13, atol=2e-13 * input_norm)
        components = tuple(component.data for out in result.outputs for component in (out.x, out.y))
        assert all(not v.flags.writeable for v in components)
        assert all(not np.shares_memory(a, b) for i, a in enumerate(components) for b in components[i + 1:])
        assert all(not np.shares_memory(a, b) for a in components for b in (incident.x.data, incident.y.data))
        assert arrays(incident).tobytes() == original
        dense.append({"shape": [ny, nx], "reference_seconds": reference_seconds, "Ain": ain, "Nin": input_norm,
                      "complex": check, "norm_max_absolute_over_Nin": max(abs(a - b) for a, b in zip(result.norms.outputs, expected_norms)) / input_norm,
                      "norms": norms_to_dict(result.norms), "all_four_outputs_independently_owned": True})
    axis_rows = []
    incident = make_jones(np.asarray([[1 + 2j, -.3 + .7j, 0, 2j], [4 - .2j, -2 - 1j, .2, .7], [.3j, .6, .9j, 1 - .1j]]), 0,
                          grid=SamplingGrid(ny=3, nx=4, dy=DY, dx=DX))
    scalar = incident.x
    old = run_two_arm(scalar, spec=TwoArmSpec(arm_0_distance_m=.002731, arm_1_distance_m=.004123, relative_phase_rad=.37))
    for axis in ("x", "y"):
        value = JonesField.from_scalar(scalar, x_coefficient=int(axis == "x"), y_coefficient=int(axis == "y"))
        result = run_polarized_two_arm(value, spec=spec(.002731, .004123))
        errors = [float(np.max(np.abs(getattr(out, axis).data - reference.data))) for out, reference in zip(result.outputs, old.outputs)]
        for out, reference in zip(result.outputs, old.outputs):
            np.testing.assert_allclose(getattr(out, axis).data, reference.data, rtol=2e-14, atol=2e-14 * float(np.max(np.abs(scalar.data))))
        np.testing.assert_allclose(result.norms.output_fractions, old.norms.output_fractions, rtol=2e-13, atol=2e-13)
        axis_rows.append({"axis": axis, "complex_max_absolute": max(errors),
                          "fraction_max_absolute": max(abs(a - b) for a, b in zip(result.norms.output_fractions, old.norms.output_fractions))})
    z0, z1 = WAVELENGTH / 7, WAVELENGTH / 7 + WAVELENGTH / 6
    result = run_polarized_two_arm(source, spec=spec(z0, z1, phase=0.))
    h0, h1 = cmath.exp(2j * math.pi * z0 / WAVELENGTH), cmath.exp(2j * math.pi * z1 / WAVELENGTH)
    carrier = {"actual_fractions": result.norms.output_fractions,
               "complex": check_pair(result.outputs, (np.array([(h0 + h1) / 2, 0])[:, None, None],
                                                        np.array([1j * (h1 - h0) / 2, 0])[:, None, None]), 1.)}
    np.testing.assert_allclose(result.norms.output_fractions, (.75, .25), rtol=2e-13, atol=2e-13)
    exceptions = []
    for name, value, request in (("original_tiny_component", make_jones(1, 1e-200), spec()),
                                 ("derived_arm0_terminal_tiny", source, spec(a0=(("polarizer", 1e-200),))),
                                 ("derived_arm1_phase_tiny", source, spec(a1=(("polarizer", 1e-200),)))):
        try:
            run_polarized_two_arm(value, spec=request)
        except ValueError as exc:
            exceptions.append({"case": name, "exception": type(exc).__name__, "message": str(exc),
                               "classification": "ordinary documented exception contract; not fault mutation"})
        else:
            raise AssertionError(f"unsupported tiny component silently accepted: {name}")
    valid_jones_only = run_polarized_two_arm(source, spec=spec(a0=(("polarizer", 1e-200), ("polarizer", 0.))))
    assert len(valid_jones_only.norms.arm_action_norms[0]) == 2
    dark = run_polarized_two_arm(make_jones(0, 0), spec=spec())
    assert dark.norms.output_fractions == (None, None)
    near = near_dark_checks()
    assert np.geterr() == caller_settings, "caller NumPy settings changed"
    return {"acceptance_passed": True, "environment": environment_record(), "tolerances": TOLERANCES,
            "Ain_definition": "maximum absolute incident component sample, across applicable input ports",
            "Nin_definition": "independent combined Jones input reduction sum(abs(x)^2+abs(y)^2,float64)*dx*dy; never adjusted",
            "error_metrics": "max_absolute=max(abs(actual-reference)); input-scaled=max_absolute/Ain or norm_error/Nin; relative weak error=abs(actual-reference)/reference",
            "reference_independence": "literal 4x4 block, expanded Jones coefficients, independently constructed coordinates/bins/principal kz/finite sums; no FFT or production numerical helper in expected fields",
            "phase_markers_rad": PHASES, "additional_phases_rad": EXTRA_PHASES,
            "block_unitarity_max_absolute": unitarity, "literal_four_component_mixing": mixing,
            "lossless_sweep": rows, "complex_first_arm_anchor": anchor, "orthogonal_circular": circular_rows,
            "lossy_arm": lossy, "complete_direct_sums": dense, "pure_axis_scalar_reductions": axis_rows,
            "carrier_once": carrier, "selected_near_dark": near, "exception_contracts": exceptions,
            "jones_only_tiny_intermediate_then_removed_supported": True, "numpy_settings_preserved": True,
            "maxima": {"ordinary_complex_over_Ain": max(r["complex"]["max_absolute_over_Ain"] for r in rows),
                       "fraction_absolute_error": max(r["fraction_max_absolute_error"] for r in rows),
                       "analyzer_fraction_absolute_error": max(r.get("analyzed_max_absolute_error", 0.) for r in rows),
                       "direct_complex_over_Ain": max(r["complex"]["max_absolute_over_Ain"] for r in dense),
                       "direct_norm_over_Nin": max(r["norm_max_absolute_over_Nin"] for r in dense),
                       "selected_near_dark_relative_error": max(r["relative_error"] for r in near)},
            "limitations": ["finite discrete model checks, not continuum/vector electromagnetic calibration",
                            "no universal relative-accuracy guarantee for smaller complex quadratures; recorded nonzero quadrature may round to zero",
                            "17 sampled markers are not exact continuous visibility; 0 and 2*pi evaluated independently"]}


def environment_record() -> dict[str, object]:
    """Actual interpreter and source provenance, without environment secrets."""
    paths = (Path(core.__file__), Path(__file__))
    return {"interpreter": sys.executable, "python": sys.version, "platform": platform.platform(),
            "numpy": np.__version__, "sources": {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}


def process_memory() -> dict[str, int] | None:
    """Whole-process Windows snapshot and nonresettable lifetime working-set peak."""
    if os.name != "nt":
        return None
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t), ("PrivateUsage", ctypes.c_size_t)]
    kernel, psapi = ctypes.WinDLL("kernel32", use_last_error=True), ctypes.WinDLL("psapi", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {"working_set_bytes": int(counters.WorkingSetSize), "private_bytes": int(counters.PrivateUsage),
            "process_lifetime_peak_working_set_bytes": int(counters.PeakWorkingSetSize)}


def measure_resources(*, iterations: int = 20) -> list[dict[str, object]]:
    """Measure actual runner at 32/64/128; wall and traced intervals separate."""
    records = []
    for n in (32, 64, 128):
        grid = SamplingGrid(ny=n, nx=n, dy=DY, dx=DX)
        x = (np.arange(n) - n // 2) * DX
        y = (np.arange(n) - n // 2) * DY
        envelope = np.exp(-(y[:, None] ** 2 + x[None, :] ** 2) / (35e-6) ** 2) * np.exp(1j * (.2 * x[None, :] / 35e-6 - .1 * y[:, None] / 35e-6))
        source = make_jones((1 + .3j) * envelope, (.2 - .4j) * envelope, grid=grid)
        request = spec(.002, .0031, (("polarizer", .37), ("retarder", .61, .83)),
                       (("retarder", -.27, 1.1), ("polarizer", .41)), .43)
        before = process_memory()
        started = time.perf_counter()
        for _ in range(iterations):
            result = run_polarized_two_arm(source, spec=request)
        wall = time.perf_counter() - started
        after_wall = process_memory()
        del result
        tracemalloc.start()
        for _ in range(iterations):
            result = run_polarized_two_arm(source, spec=request)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        after_trace = process_memory()
        records.append({"shape": [n, n], "iterations_per_separate_interval": iterations,
                        "wall_seconds_without_tracing": wall, "wall_seconds_per_runner_without_tracing": wall / iterations,
                        "traced_current_bytes": current, "traced_peak_bytes": peak,
                        "process_before": before, "process_after_wall": after_wall, "process_after_trace": after_trace,
                        "output_four_component_bytes": sum(c.data.nbytes for f in result.outputs for c in (f.x, f.y)),
                        "norms": norms_to_dict(result.norms),
                        "interpretation": "actual shipped runner; tracing excludes input construction and reference/serialization; process snapshots/lifetime peaks are whole process, not isolated native peaks; observations are not guarantees"})
    return records


def fresh_output(path: Path) -> Path:
    """Require a new ignored evidence child of this checkout's runs directory."""
    output, runs = path.resolve(), (ROOT / "runs").resolve()
    if not output.is_relative_to(runs) or output == runs:
        raise ValueError(f"fresh evidence must be below {runs}")
    output.mkdir(parents=True, exist_ok=False)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "runs" / f"v2f-validation-{uuid.uuid4().hex}")
    parser.add_argument("--resources", action="store_true")
    args = parser.parse_args()
    output = fresh_output(args.output_dir)
    report = run_validation()
    if args.resources:
        report["actual_runner_resources"] = measure_resources()
    (output / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"acceptance_passed": report["acceptance_passed"], "output": str(output / "validation.json"),
                      "fixed_phase_markers": len(PHASES), "direct_cases": len(report["complete_direct_sums"]),
                      "near_dark_cases": len(report["selected_near_dark"]), "maxima": report["maxima"],
                      "resources": report.get("actual_runner_resources")}, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
