r"""Independent finite-case Jones validation, outside the numerical core.

Run with the existing project interpreter, for example::

    .\.venv\Scripts\python.exe -B -X utf8 scripts\validate_v2c_polarization.py --output-dir runs\v2c-validation-NEW

Literal complex fixtures and expanded scalar coefficients never call a
production matrix/application helper for expectations. The selected weak
fixtures additionally use bounded stdlib Decimal Taylor sums at the *actual*
binary64 input angle. No phase fitting, signal normalization or new package
is used. JSON is regenerable evidence, not an experiment persistence format.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import sys
import uuid

import numpy as np

from ohlab import ComplexField, SamplingGrid
from ohlab.optics import polarization
from ohlab.optics.polarization import (
    JonesField, apply_linear_polarizer, apply_linear_retarder, transmission_ratio,
)

ROOT = Path(__file__).resolve().parents[1]
WAVELENGTH_M = 633e-9
DX_M = 3.7e-6
DY_M = 4.1e-6
MALUS_DEGREES = (-90, -75, -60, -45, -30, -15, 0, 15, 30, 45, 60, 75, 90)
NEAR_OFFSETS = (-1e-6, -1e-9, 0.0, 1e-9, 1e-6)
AXIS_ANGLES = (0.0, math.pi / 12, math.pi / 8, math.pi / 4, math.pi / 2, -.37, .61)
RETARDANCES = (0.0, math.pi / 2, math.pi, -.83, 2.41)
TOLERANCES = {
    "complex": {"rtol": 2e-14, "atol_input_amplitude_multiplier": 2e-14},
    "intensity": {"rtol": 2e-13, "atol_input_amplitude_squared_multiplier": 2e-13},
    "norm": {"rtol": 2e-13, "atol_input_norm_multiplier": 2e-13},
    "ratio": {"rtol": 2e-13, "atol": 2e-13},
    "unitarity": {"rtol": 0.0, "atol": 2e-15},
    "selected_weak_components_intensity_ratio": {"rtol": 2e-14, "atol": 1e-48},
    "selected_weak_norm": {"rtol": 2e-14, "atol_input_norm_multiplier": 1e-48},
}


def scalar_reference(
    x: np.ndarray, y: np.ndarray, theta: float, delta: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Expanded component reference, angles/retardance in radians.

    Production acts through axis projections. This reference expands each
    coefficient independently; fixed literal fixtures constrain its sign and
    common phase. It does not construct/call the production element matrices.
    """
    c, s = math.cos(theta), math.sin(theta)
    if delta is None:
        return c * c * x + c * s * y, c * s * x + s * s * y
    q = complex(math.cos(delta), math.sin(delta))
    return ((c * c + q * s * s) * x + (1 - q) * c * s * y,
            (1 - q) * c * s * x + (s * s + q * c * c) * y)


def independent_intensity(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Independent component squares in amplitude-unit²; no scalar cross term."""
    return x.real * x.real + x.imag * x.imag + y.real * y.real + y.imag * y.imag


def independent_norm(x: np.ndarray, y: np.ndarray, *, grid: SamplingGrid) -> float:
    """Independent norm, amplitude-unit²·m², with declared reduction order."""
    return float(np.sum(independent_intensity(x, y), dtype=np.float64) * grid.dx * grid.dy)


def decimal_near_reference(theta: float) -> dict[str, object]:
    """80-digit direct-angle reference for the five near-pi/2 binary64 inputs.

    Decimal.from_float preserves the exact supplied binary64 angle. Direct
    sin/cos Taylor sums avoid an approximate-pi subtraction; at most 100 terms
    are evaluated on |theta| <= 2. The final terms are below 1e-90, leaving
    ample guard digits for the roughly 1e-17 cosine cancellation. This is a
    bounded reference for these cases, not a general transcendental library.
    """
    if not isinstance(theta, float) or not math.isfinite(theta) or abs(theta) > 2:
        raise ValueError("Decimal reference requires finite Python float |theta| <= 2")
    with localcontext() as context:
        context.prec = 80
        angle = Decimal.from_float(theta)
        sine_term = angle
        cosine_term = Decimal(1)
        sine, cosine = sine_term, cosine_term
        cutoff = Decimal("1e-90")
        terms = 1
        for k in range(1, 101):
            sine_term *= -(angle * angle) / Decimal((2 * k) * (2 * k + 1))
            cosine_term *= -(angle * angle) / Decimal((2 * k - 1) * (2 * k))
            sine += sine_term
            cosine += cosine_term
            terms = k + 1
            if abs(sine_term) < cutoff and abs(cosine_term) < cutoff:
                break
        else:
            raise AssertionError("bounded Decimal reference failed to converge")
        x, y = cosine * cosine, cosine * sine
        intensity = x * x + y * y
        return {"angle_rad": theta, "angle_hex": theta.hex(),
                "exact_binary64_angle_decimal": str(angle), "precision_digits": 80,
                "terms": terms, "cos_decimal": str(cosine), "sin_decimal": str(sine),
                "x_decimal": str(x), "y_decimal": str(y),
                "intensity_fraction_decimal": str(intensity),
                "x": float(x), "y": float(y), "intensity_fraction": float(intensity)}


def make_field(x: object, y: object, *, grid: SamplingGrid) -> JonesField:
    """Create actual fields through public constructors, amplitudes in a.u."""
    def component(value: object) -> ComplexField:
        data = np.asarray(value, dtype=np.complex128)
        if data.ndim == 0:
            data = np.full(grid.shape, data.item(), dtype=np.complex128)
        return ComplexField(data=data, grid=grid, wavelength_m=WAVELENGTH_M)
    return JonesField(x=component(x), y=component(y))


def complex_pairs(values: np.ndarray) -> list[list[float]]:
    """Represent complex values without discarding real or imaginary parts."""
    return [[float(value.real), float(value.imag)] for value in np.ravel(values)]


def sample_components(field: JonesField, index: tuple[int, int]) -> list[list[float]]:
    """Actual x/y complex components at the declared row/column."""
    return complex_pairs(np.asarray([field.x.data[index], field.y.data[index]]))


def check_components(
    actual_x: np.ndarray, actual_y: np.ndarray,
    expected_x: np.ndarray, expected_y: np.ndarray, scale: float,
) -> float:
    """Assert selected complex outputs without phase alignment; return max error."""
    np.testing.assert_allclose(actual_x, expected_x, rtol=2e-14, atol=2e-14 * scale,
                               err_msg="selected complex x component")
    np.testing.assert_allclose(actual_y, expected_y, rtol=2e-14, atol=2e-14 * scale,
                               err_msg="selected complex y component")
    return max(float(np.max(np.abs(actual_x - expected_x))),
               float(np.max(np.abs(actual_y - expected_y))))


def check_output(
    field: JonesField, expected: tuple[np.ndarray, np.ndarray], incident: JonesField,
) -> dict[str, float]:
    """Check complex components and independent intensity/norm/ratio separately."""
    scale = max(float(np.max(np.abs(incident.x.data))),
                float(np.max(np.abs(incident.y.data))))
    error = check_components(field.x.data, field.y.data, *expected, scale)
    expected_i = independent_intensity(*expected)
    expected_n = independent_norm(*expected, grid=field.grid)
    input_n = independent_norm(incident.x.data, incident.y.data, grid=incident.grid)
    np.testing.assert_allclose(field.intensity, expected_i, rtol=2e-13, atol=2e-13 * scale ** 2,
                               err_msg="independent polarization-insensitive intensity")
    np.testing.assert_allclose(field.sampled_norm, expected_n, rtol=2e-13, atol=2e-13 * input_n,
                               err_msg="independent sampled norm")
    actual_ratio = transmission_ratio(incident, field)
    expected_ratio = expected_n / input_n
    np.testing.assert_allclose(actual_ratio, expected_ratio, rtol=2e-13, atol=2e-13,
                               err_msg="incident-normalized ratio")
    return {"max_complex_absolute_error": error,
            "max_complex_input_scaled_error": error / scale,
            "max_intensity_absolute_error": float(np.max(np.abs(field.intensity - expected_i))),
            "norm_absolute_error": abs(field.sampled_norm - expected_n),
            "actual_norm": field.sampled_norm, "expected_norm": expected_n,
            "actual_ratio": float(actual_ratio), "expected_ratio": expected_ratio,
            "ratio_absolute_error": abs(float(actual_ratio) - expected_ratio)}


def assert_weak_signal(
    field: JonesField, incident: JonesField, theta: float,
) -> dict[str, object]:
    """Selected uniform unit-x weak fixture; a zeroed diagnostic must fail.

    The ordinary input-scaled floor is intentionally insufficient here. Both
    represented component magnitudes and all four diagnostic forms must stay
    positive. Comparisons are relative to the independently computed weak
    signal, with tiny finite absolute floors; no universal dynamic-range
    relative-accuracy guarantee follows from five bounded fixtures.
    """
    reference = decimal_near_reference(theta)
    expected_x = float(reference["x"])
    expected_y = float(reference["y"])
    expected_i = float(reference["intensity_fraction"])
    input_n = independent_norm(incident.x.data, incident.y.data, grid=incident.grid)
    expected_n = expected_i * input_n
    actual_i = field.intensity
    actual_n = field.sampled_norm
    actual_ratio = transmission_ratio(incident, field)
    assert np.all(np.abs(field.x.data) > 0), "weak x component was truncated to zero"
    assert np.all(np.abs(field.y.data) > 0), "weak y component was truncated to zero"
    assert np.all(actual_i > 0), "weak intensity was truncated to zero"
    assert actual_n > 0, "weak norm was truncated to zero"
    assert actual_ratio is not None and actual_ratio > 0, "weak ratio was truncated to zero"
    np.testing.assert_allclose(field.x.data, expected_x, rtol=2e-14, atol=1e-48,
                               err_msg="selected weak complex x: actual binary64-angle Decimal reference")
    np.testing.assert_allclose(field.y.data, expected_y, rtol=2e-14, atol=1e-48,
                               err_msg="selected weak complex y: actual binary64-angle Decimal reference")
    np.testing.assert_allclose(actual_i, expected_i, rtol=2e-14, atol=1e-48,
                               err_msg="selected weak intensity")
    np.testing.assert_allclose(actual_n, expected_n, rtol=2e-14, atol=1e-48 * input_n,
                               err_msg="selected weak sampled norm")
    np.testing.assert_allclose(actual_ratio, expected_i, rtol=2e-14, atol=1e-48,
                               err_msg="selected weak transmission ratio")
    def relative_error(actual: object, expected: float) -> float:
        return float(np.max(np.abs(np.asarray(actual) - expected))) / abs(expected)
    return {"reference": reference,
            "actual_components": sample_components(field, (field.shape[0] // 2, field.shape[1] // 2)),
            "actual_intensity": float(actual_i[0, 0]), "expected_intensity": expected_i,
            "actual_norm": actual_n, "expected_norm": expected_n,
            "actual_ratio": float(actual_ratio), "expected_ratio": expected_i,
            "relative_errors": {"x": relative_error(field.x.data, expected_x),
                                "y": relative_error(field.y.data, expected_y),
                                "intensity": relative_error(actual_i, expected_i),
                                "norm": relative_error(actual_n, expected_n),
                                "ratio": relative_error(actual_ratio, expected_i)},
            "positive_components_and_diagnostics": True}


def asymmetric_fixture() -> tuple[np.ndarray, np.ndarray]:
    """Tiny asymmetric spatial components, including a represented dark sample."""
    x = np.array([[1 + 2j, -.3 + .7j, 0j, .17 - .4j],
                  [4 - .2j, -2 - 1j, 1e-7 + 3e-8j, -.9 + .1j],
                  [.2 + .3j, -.8 + 1.2j, 2.3 - .7j, .6 + .9j]], dtype=np.complex128)
    y = np.array([[.4 - .1j, 2 + 3j, 0j, -.2 + .6j],
                  [-.7 + 1j, .6 + .8j, -3e-8 + 4e-8j, .3 - 1.1j],
                  [1.7 - .2j, -.3 - .4j, .2 + .5j, -.7 + .8j]], dtype=np.complex128)
    return x, y


def environment_record() -> dict[str, object]:
    """Relevant source/runtime provenance, without dumping environment mappings."""
    source = Path(polarization.__file__).resolve()
    return {"interpreter": sys.executable, "python": platform.python_version(),
            "numpy": np.__version__, "scipy": importlib.metadata.version("scipy"),
            "platform": platform.platform(), "polarization_source": str(source),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "reference_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def run_validation(*, n: int = 32) -> dict[str, object]:
    """Validate shipped functions on all declared bounded cases; no files written."""
    if type(n) is not int or n not in (32, 64):
        raise ValueError("validation grid n must be Python int 32 or 64")
    caller_settings = np.geterr().copy()
    grid = SamplingGrid(ny=n, nx=n, dy=DY_M, dx=DX_M)
    index = (n // 2, n // 2)
    x_input = make_field(1.0, 0.0, grid=grid)
    same_phase = make_field(1.0, 1.0, grid=grid)
    np.testing.assert_allclose(same_phase.intensity, 2.0, rtol=0, atol=0,
                               err_msg="orthogonal components do not scalar-interfere")
    quadrature = make_field(1.0, 1j, grid=grid)
    np.testing.assert_allclose(quadrature.intensity, 2.0, rtol=0, atol=0)
    analyzer = apply_linear_polarizer(same_phase, axis_angle_rad=math.pi / 4)
    ones = np.ones(grid.shape, dtype=np.complex128)
    zeros = np.zeros(grid.shape, dtype=np.complex128)
    analyzer_check = check_output(analyzer, (ones, ones), same_phase)
    root_two = math.sqrt(2)
    linear_45 = make_field(1 / root_two, 1 / root_two, grid=grid)
    fixtures = []
    declared = (
        ("P0_11", same_phase, apply_linear_polarizer(same_phase, axis_angle_rad=0.0), (1 + 0j, 0j)),
        ("P90_11", same_phase, apply_linear_polarizer(same_phase, axis_angle_rad=math.pi / 2), (0j, 1 + 0j)),
        ("QWP0_linear45", linear_45, apply_linear_retarder(linear_45, axis_angle_rad=0.0, retardance_rad=math.pi / 2), (1 / root_two, 1j / root_two)),
        ("HWP_pi8_x", x_input, apply_linear_retarder(x_input, axis_angle_rad=math.pi / 8, retardance_rad=math.pi), (1 / root_two, 1 / root_two)),
        ("QWP45_x", x_input, apply_linear_retarder(x_input, axis_angle_rad=math.pi / 4, retardance_rad=math.pi / 2), ((1 + 1j) / 2, (1 - 1j) / 2)),
    )
    for name, incident, actual, expected in declared:
        reference = tuple(np.full(grid.shape, value, dtype=np.complex128) for value in expected)
        fixtures.append({"case_id": name, "actual_components": sample_components(actual, index),
                         "expected_components": complex_pairs(np.asarray(expected)),
                         **check_output(actual, reference, incident)})
    malus = []
    for degree in MALUS_DEGREES:
        theta = math.radians(degree)
        actual = apply_linear_polarizer(x_input, axis_angle_rad=theta)
        expected = scalar_reference(ones, zeros, theta)
        reference_ratio = math.cos(theta) ** 2
        check = check_output(actual, expected, x_input)
        np.testing.assert_allclose(transmission_ratio(x_input, actual), reference_ratio,
                                   rtol=2e-13, atol=2e-13, err_msg="Malus intensity, not amplitude cos-squared")
        malus.append({"degrees": degree, "radians": theta, "radians_hex": theta.hex(),
                      "actual_components": sample_components(actual, index),
                      "actual_intensity": float(actual.intensity[index]),
                      "analytic_ratio": reference_ratio, **check})
    near = []
    for offset in NEAR_OFFSETS:
        theta = math.pi / 2 + offset
        actual = apply_linear_polarizer(x_input, axis_angle_rad=theta)
        near.append({"offset_rad": offset, "theta_rad": theta,
                     **assert_weak_signal(actual, x_input, theta)})
    crossed = apply_linear_polarizer(apply_linear_polarizer(x_input, axis_angle_rad=0.0), axis_angle_rad=math.pi / 2)
    three = apply_linear_polarizer(apply_linear_polarizer(apply_linear_polarizer(x_input, axis_angle_rad=0.0), axis_angle_rad=math.pi / 4), axis_angle_rad=math.pi / 2)
    np.testing.assert_allclose(transmission_ratio(x_input, crossed), 0.0, rtol=0, atol=2e-13)
    np.testing.assert_allclose(transmission_ratio(x_input, three), .25, rtol=2e-13, atol=2e-13)
    # The actual ordered expression is deliberately explicit; the independent
    # literal fixture below stays fixed if an isolated control reverses it.
    ordered = apply_linear_retarder(apply_linear_polarizer(x_input, axis_angle_rad=0.0), axis_angle_rad=math.pi / 4, retardance_rad=math.pi / 2)
    reversed_order = apply_linear_polarizer(apply_linear_retarder(x_input, axis_angle_rad=math.pi / 4, retardance_rad=math.pi / 2), axis_angle_rad=0.0)
    ordered_check = check_output(ordered, (ones * ((1 + 1j) / 2), ones * ((1 - 1j) / 2)), x_input)
    reversed_check = check_output(reversed_order, (ones * ((1 + 1j) / 2), zeros), x_input)
    spatial_grid = SamplingGrid(ny=3, nx=4, dy=DY_M, dx=DX_M)
    x, y = asymmetric_fixture()
    spatial = make_field(x, y, grid=spatial_grid)
    spatial_i = independent_intensity(x, y)
    np.testing.assert_allclose(spatial.intensity, spatial_i, rtol=2e-13,
                               atol=2e-13 * max(float(np.max(np.abs(x))), float(np.max(np.abs(y)))) ** 2)
    spatial_checks, retarder_checks, covariance_checks, idempotence_checks = [], [], [], []
    phase = complex(math.cos(.67), math.sin(.67))
    shifted = make_field(phase * x, phase * y, grid=spatial_grid)
    amplitude_scale = max(float(np.max(np.abs(x))), float(np.max(np.abs(y))))
    norm_in = independent_norm(x, y, grid=spatial_grid)
    basis_x = make_field(1.0, 0.0, grid=spatial_grid)
    basis_y = make_field(0.0, 1.0, grid=spatial_grid)
    for theta in AXIS_ANGLES:
        polar = apply_linear_polarizer(spatial, axis_angle_rad=theta)
        spatial_checks.append({"theta_rad": theta, "kind": "polarizer",
                               **check_output(polar, scalar_reference(x, y, theta), spatial)})
        assert polar.sampled_norm <= norm_in + 2e-13 * norm_in, "passive polarizer contraction"
        repeated = apply_linear_polarizer(polar, axis_angle_rad=theta)
        idempotence_checks.append(check_components(repeated.x.data, repeated.y.data,
                                                  polar.x.data, polar.y.data, amplitude_scale) / amplitude_scale)
        shifted_polar = apply_linear_polarizer(shifted, axis_angle_rad=theta)
        covariance_checks.append(check_components(shifted_polar.x.data, shifted_polar.y.data,
                                                  phase * polar.x.data, phase * polar.y.data, amplitude_scale) / amplitude_scale)
        np.testing.assert_allclose(shifted_polar.intensity, polar.intensity, rtol=2e-13,
                                   atol=2e-13 * amplitude_scale ** 2)
        for delta in RETARDANCES:
            actual = apply_linear_retarder(spatial, axis_angle_rad=theta, retardance_rad=delta)
            check = check_output(actual, scalar_reference(x, y, theta, delta), spatial)
            inverse = apply_linear_retarder(actual, axis_angle_rad=theta, retardance_rad=-delta)
            inverse_error = check_components(inverse.x.data, inverse.y.data, x, y, amplitude_scale) / amplitude_scale
            np.testing.assert_allclose(actual.sampled_norm, norm_in, rtol=2e-13, atol=2e-13 * norm_in)
            shifted_actual = apply_linear_retarder(shifted, axis_angle_rad=theta, retardance_rad=delta)
            covariance_checks.append(check_components(shifted_actual.x.data, shifted_actual.y.data,
                                                      phase * actual.x.data, phase * actual.y.data, amplitude_scale) / amplitude_scale)
            np.testing.assert_allclose(shifted_actual.intensity, actual.intensity, rtol=2e-13,
                                       atol=2e-13 * amplitude_scale ** 2)
            # Matrix properties are observed only through public basis-field
            # actions. No new public matrix constructor is introduced.
            bx = apply_linear_retarder(basis_x, axis_angle_rad=theta, retardance_rad=delta)
            by = apply_linear_retarder(basis_y, axis_angle_rad=theta, retardance_rad=delta)
            matrix = np.asarray([[bx.x.data[0, 0], by.x.data[0, 0]],
                                 [bx.y.data[0, 0], by.y.data[0, 0]]])
            identity_error = float(np.max(np.abs(matrix.conj().T @ matrix - np.eye(2))))
            np.testing.assert_allclose(matrix.conj().T @ matrix, np.eye(2), rtol=0, atol=2e-15)
            retarder_checks.append({"theta_rad": theta, "delta_rad": delta,
                                    "unitarity_entry_error": identity_error,
                                    "inverse_input_scaled_error": inverse_error,
                                    "norm_relative_error": abs(actual.sampled_norm - norm_in) / norm_in,
                                    **check})
    scalar = ComplexField(data=x, grid=spatial_grid, wavelength_m=WAVELENGTH_M)
    cx, cy = 2 + .5j, -.7 + 1j
    coefficient_field = JonesField.from_scalar(scalar, x_coefficient=cx, y_coefficient=cy)
    coefficient_check = check_output(coefficient_field, (cx * x, cy * x), make_field(x, 0, grid=spatial_grid))
    expected_gain = abs(cx) ** 2 + abs(cy) ** 2
    np.testing.assert_allclose(coefficient_check["actual_ratio"], expected_gain, rtol=2e-13, atol=2e-13)
    reset_sensitive = JonesField.from_scalar(scalar, x_coefficient=phase, y_coefficient=1j * phase)
    reset_error = check_components(reset_sensitive.x.data, reset_sensitive.y.data,
                                   phase * x, 1j * phase * x, float(np.max(np.abs(x))))
    same_analyzer = apply_linear_polarizer(same_phase, axis_angle_rad=math.pi / 4)
    opposite = apply_linear_polarizer(make_field(1, -1, grid=grid), axis_angle_rad=math.pi / 4)
    np.testing.assert_allclose(same_analyzer.intensity, 2, rtol=2e-13, atol=2e-13)
    np.testing.assert_allclose(opposite.intensity, 0, rtol=0, atol=2e-13)
    doubled = make_field(2.0, 0.0, grid=grid)
    assert transmission_ratio(x_input, doubled) == 4.0, "ratio does not certify a causal passive operation"
    dark = make_field(0.0, 0.0, grid=grid)
    assert dark.sampled_norm == 0.0 and transmission_ratio(dark, dark) is None
    assert np.geterr() == caller_settings, "caller floating-point settings changed"
    all_checks = fixtures + spatial_checks + retarder_checks + malus
    return {"acceptance_passed": True,
            "scope": "classical deterministic fully coherent monochromatic Jones fields, common plane/basis; finite-case evidence, no propagation, calibrated watts, frontend or persistence",
            "shape": [n, n], "grid": {"ny": n, "nx": n, "dy_m": DY_M, "dx_m": DX_M},
            "wavelength_m": WAVELENGTH_M, "input_norm": x_input.sampled_norm,
            "tolerances": TOLERANCES, "environment": environment_record(),
            "basis": "e_theta=(cos(theta),sin(theta)); e_perp=(-sin(theta),cos(theta)); +y down in display",
            "time_convention": "exp(-i*omega*t)",
            "retarder_reference": "e_theta phase zero; e_perp phase +delta; no omitted-phase compensation",
            "malus": malus, "near_extinction": near, "literal_fixtures": fixtures,
            "same_phase_analyzer": analyzer_check,
            "crossed": {"ratio": transmission_ratio(x_input, crossed), "norm": crossed.sampled_norm,
                        "actual_components": sample_components(crossed, index)},
            "three_polarizers": {"ratio": transmission_ratio(x_input, three), "norm": three.sampled_norm,
                                  "actual_components": sample_components(three, index),
                                  "incident": "already x-polarized, unit component amplitude; not unpolarized"},
            "noncommuting_order": {"P_then_W": {"actual_components": sample_components(ordered, index), **ordered_check},
                                    "W_then_P": {"actual_components": sample_components(reversed_order, index), **reversed_check}},
            "asymmetric_spatial": {"shape": [3, 4], "input_x": complex_pairs(x), "input_y": complex_pairs(y),
                                   "input_norm": norm_in, "polarizers": spatial_checks},
            "retarders": retarder_checks,
            "arbitrary_coefficients": {"x_coefficient": complex_pairs(np.asarray(cx))[0],
                                       "y_coefficient": complex_pairs(np.asarray(cy))[0],
                                       "expected_gain": expected_gain, **coefficient_check},
            "phase_preserving_constructor_max_absolute_error": reset_error,
            "independently_constructed_amplitude_twice_ratio": transmission_ratio(x_input, doubled),
            "dark_input_ratio": transmission_ratio(dark, dark),
            "numpy_settings_preserved": True,
            "maxima": {"complex_input_scaled_error": max(row["max_complex_input_scaled_error"] for row in all_checks),
                       "malus_absolute_error": max(abs(row["actual_ratio"] - row["analytic_ratio"]) for row in malus),
                       "unitarity_entry_error": max(row["unitarity_entry_error"] for row in retarder_checks),
                       "inverse_input_scaled_error": max(row["inverse_input_scaled_error"] for row in retarder_checks),
                       "common_phase_covariance_input_scaled_error": max(covariance_checks),
                       "polarizer_idempotence_input_scaled_error": max(idempotence_checks),
                       "retarder_relative_norm_error": max(row["norm_relative_error"] for row in retarder_checks),
                       "selected_weak_relative_error": max(value for row in near for value in row["relative_errors"].values())}}


def main() -> int:
    """Run bounded validation and preserve exact scientific rows in fresh evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, choices=(32, 64), default=32)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "runs" / f"v2c-validation-{uuid.uuid4().hex}")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError(f"fresh empty evidence directory required, got {output}")
    report = run_validation(n=args.n)
    (output / "validation.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"acceptance_passed": True, "output": str(output / "validation.json"),
                      "shape": report["shape"], "malus_cases": len(report["malus"]),
                      "weak_cases": len(report["near_extinction"]), "maxima": report["maxima"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
