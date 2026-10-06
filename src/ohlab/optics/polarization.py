"""Ideal coherent Jones polarization on one common transverse reference plane.

Components use the fixed algebraic x/y basis and ``exp(-i*omega*t)``. Positive
axis angles turn from +x toward +y, appearing clockwise in the repository's
y-down display. Polarization components are not the optical ports of V2a.
Metadata compatibility stipulates a common plane/basis; it cannot establish
physical alignment. No propagation, frame transformation or material model is
implemented here. Normative reference: ``docs/math_conventions.md`` section 3.19.

Scalar inputs are converted to binary64. Angles accept Python int/float and
NumPy integer/floating scalars; coefficients additionally accept Python complex
and NumPy complexfloating scalars. Booleans, temporal scalars, arrays and strings
are rejected. A nonzero angle that rounds to zero on conversion is rejected;
coefficient conversion/products may lose negligible tails. This is not an
arbitrary-dynamic-range accuracy guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from ..field import ComplexField
from ..grid import SamplingGrid

__all__ = [
    "JonesField",
    "apply_linear_polarizer",
    "apply_linear_retarder",
    "transmission_ratio",
]


def _real_angle(value: object, name: str) -> float:
    """Finite real binary64 radians, without wrapping or snapping."""
    if isinstance(value, (bool, np.bool_, np.timedelta64)) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        raise TypeError(
            f"{name}: expected int/float or NumPy integer/floating scalar "
            f"excluding bool and temporal scalars, got {type(value).__name__}"
        )
    try:
        result = float(value)
    except (OverflowError, ValueError, TypeError) as exc:
        raise ValueError(f"{name}: expected representable finite binary64 radians") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name}: expected finite binary64 radians, got {result!r}")
    if result == 0.0 and value != 0:
        raise ValueError(f"{name}: nonzero angle underflowed to zero during binary64 conversion")
    return result


def _coefficient(value: object, name: str) -> complex:
    """Finite binary64 real/imaginary parts, with no normalization."""
    if isinstance(value, (bool, np.bool_, np.timedelta64)) or not isinstance(
        value, (int, float, complex, np.integer, np.floating, np.complexfloating)
    ):
        raise TypeError(
            f"{name}: expected Python int/float/complex or NumPy "
            f"integer/floating/complexfloating scalar excluding bool and "
            f"temporal scalars, got {type(value).__name__}"
        )
    try:
        result = complex(value)
    except (OverflowError, ValueError, TypeError) as exc:
        raise ValueError(f"{name}: expected representable finite binary64 components") from exc
    if not (math.isfinite(result.real) and math.isfinite(result.imag)):
        raise ValueError(f"{name}: expected finite binary64 components, got {result!r}")
    return result


def _geometry(grid: SamplingGrid, wavelength_m: float, name: str) -> None:
    """Check common-plane geometry, without propagation-frequency limits."""
    if type(grid) is not SamplingGrid:
        raise TypeError(
            f"{name}.grid: expected canonical SamplingGrid, got {type(grid).__name__}"
        )
    for key in ("ny", "nx"):
        count = getattr(grid, key)
        if isinstance(count, (bool, np.bool_, np.timedelta64)) or not isinstance(
            count, (int, np.integer)
        ):
            raise TypeError(f"{name}.grid.{key}: expected positive integer, got {type(count).__name__}")
        if count < 1:
            raise ValueError(f"{name}.grid.{key}: expected integer >= 1, got {count!r}")
    pitches = []
    for key in ("dx", "dy"):
        value = getattr(grid, key)
        if isinstance(value, (bool, np.bool_, np.timedelta64)) or not isinstance(
            value, (int, float, np.integer, np.floating)
        ):
            raise TypeError(f"{name}.grid.{key}: expected positive finite real metres, got {type(value).__name__}")
        try:
            pitch = float(value)
        except (OverflowError, ValueError, TypeError) as exc:
            raise ValueError(f"{name}.grid.{key}: expected finite binary64 metres") from exc
        if not math.isfinite(pitch) or pitch <= 0.0:
            raise ValueError(f"{name}.grid.{key}: expected positive finite metres, got {pitch!r}")
        pitches.append(pitch)
    area = pitches[0] * pitches[1]
    if not math.isfinite(area) or area <= 0.0:
        raise ValueError(f"{name}.grid pixel area: expected usable positive dx*dy, got {area!r} m^2")
    if isinstance(wavelength_m, (bool, np.bool_, np.timedelta64)) or not isinstance(
        wavelength_m, (int, float, np.integer, np.floating)
    ):
        raise TypeError(f"{name}.wavelength_m: expected positive finite real metres, got {type(wavelength_m).__name__}")
    try:
        wavelength = float(wavelength_m)
    except (OverflowError, ValueError, TypeError) as exc:
        raise ValueError(f"{name}.wavelength_m: expected finite binary64 metres") from exc
    if not math.isfinite(wavelength) or wavelength <= 0.0:
        raise ValueError(f"{name}.wavelength_m: expected positive finite metres, got {wavelength!r}")


def _component(value: ComplexField, name: str) -> None:
    """Validate existing public-field storage without replacing its data."""
    if not isinstance(value, ComplexField):
        raise TypeError(f"{name}: expected ComplexField, got {type(value).__name__}")
    _geometry(value.grid, value.wavelength_m, name)
    if type(value.data) is not np.ndarray or value.data.dtype != np.dtype(np.complex128):
        raise TypeError(
            f"{name}.data: expected plain native complex128 ndarray, got "
            f"{type(value.data).__name__} with dtype {getattr(value.data, 'dtype', None)!r}"
        )
    if value.data.shape != value.grid.shape:
        raise ValueError(f"{name}.data: expected shape {value.grid.shape}, got {value.data.shape}")
    if not bool(np.all(np.isfinite(value.data))):
        raise ValueError(f"{name}.data: expected finite complex values, got NaN or infinity")


def _compatible(first: ComplexField, second: ComplexField, name: str) -> None:
    """Require exact scalar metadata; do not infer alignment."""
    first_grid = (first.grid.ny, first.grid.nx, first.grid.dy, first.grid.dx)
    second_grid = (second.grid.ny, second.grid.nx, second.grid.dy, second.grid.dx)
    if first_grid != second_grid:
        raise ValueError(
            f"{name}: grids must match exactly in ny/nx/dy/dx: expected "
            f"{first.grid!r}, got {second.grid!r}; shape alone is insufficient"
        )
    if first.wavelength_m != second.wavelength_m:
        raise ValueError(
            f"{name}: wavelengths must match exactly: expected "
            f"{first.wavelength_m!r} m, got {second.wavelength_m!r} m"
        )


def _pair(x: ComplexField, y: ComplexField, name: str) -> None:
    _component(x, f"{name}.x")
    _component(y, f"{name}.y")
    _compatible(x, y, name)


def _diagnostics(x: ComplexField, y: ComplexField, name: str) -> tuple[np.ndarray, float]:
    """Fresh total intensity and left-to-right sampled norm, with local errors."""
    x_data, y_data = x.data, y.data
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            intensity = np.abs(x_data) ** 2 + np.abs(y_data) ** 2
            norm = float(np.sum(intensity, dtype=np.float64) * x.grid.dx * x.grid.dy)
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError(f"{name}: intensity or sampled norm overflow/invalid arithmetic") from exc
    if not math.isfinite(norm):
        raise ValueError(f"{name}: sampled norm must be finite, got {norm!r}")
    if norm == 0.0 and (bool(np.any(x_data != 0.0)) or bool(np.any(y_data != 0.0))):
        raise ValueError(f"{name}: sampled norm underflowed to zero for a represented nonzero combined field")
    return intensity, norm


def _jones(value: JonesField, name: str) -> None:
    if not isinstance(value, JonesField):
        raise TypeError(f"{name}: expected JonesField, got {type(value).__name__}")
    _pair(value.x, value.y, name)
    _diagnostics(value.x, value.y, name)


def _from_data(x_data: np.ndarray, y_data: np.ndarray, template: ComplexField) -> JonesField:
    """All storage passes through supported public ComplexField construction."""
    return JonesField(
        x=ComplexField(data=x_data, grid=template.grid, wavelength_m=template.wavelength_m),
        y=ComplexField(data=y_data, grid=template.grid, wavelength_m=template.wavelength_m),
    )


@dataclass(frozen=True, kw_only=True, eq=False)
class JonesField:
    """Coherent monochromatic x/y components on a stipulated common plane/basis.

    ``x`` and ``y`` are actual :class:`ComplexField` components, in amplitude
    units, on exactly equal canonical grids and at equal wavelengths in metres.
    Shape alone does not establish compatibility; metadata does not establish
    physical alignment. Common and relative complex phase are retained.

    Each component is independently snapshot through the public ComplexField
    constructor, including when both arguments are the same object. Stored
    native complex128 arrays are read-only and share no numerical storage with
    callers or each other. This is the existing ndarray ownership contract, not
    irreversible write protection. Equality is identity comparison.

    Construction and numerical operations require usable total intensity/norm.
    Exact zero fields are valid. Tiny individual tails may underflow, but a
    represented nonzero combined field whose entire norm rounds to zero raises
    ValueError. Overflow and invalid arithmetic raise contextual ValueError;
    caller NumPy error settings are preserved. No output is normalized.
    """

    x: ComplexField
    y: ComplexField

    def __post_init__(self) -> None:
        _pair(self.x, self.y, "JonesField")
        owned_x = ComplexField(data=self.x.data, grid=self.x.grid, wavelength_m=self.x.wavelength_m)
        owned_y = ComplexField(data=self.y.data, grid=self.y.grid, wavelength_m=self.y.wavelength_m)
        _diagnostics(owned_x, owned_y, "JonesField")
        object.__setattr__(self, "x", owned_x)
        object.__setattr__(self, "y", owned_y)

    @classmethod
    def from_scalar(
        cls,
        scalar: ComplexField,
        *,
        x_coefficient: complex,
        y_coefficient: complex,
    ) -> JonesField:
        """Return ``(cx*U, cy*U)`` using arbitrary finite complex coefficients.

        Coefficients accept Python int/float/complex and NumPy integer,
        floating and complexfloating scalars, excluding booleans/temporal
        scalars, arrays and strings. Finite binary64 conversion is required.
        Intensity changes by ``abs(cx)**2 + abs(cy)**2`` mathematically; no
        clipping, coefficient normalization or phase reset is performed.
        Coefficient/product tails may underflow within the bounded arithmetic
        policy. Validate both coefficients and scalar metadata/data even for
        dark input or two zero coefficients. A usable scalar norm is not needed
        when the resulting combined Jones field is exact zero.
        """
        _component(scalar, "scalar")
        cx = _coefficient(x_coefficient, "x_coefficient")
        cy = _coefficient(y_coefficient, "y_coefficient")
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
                x_data = cx * scalar.data
                y_data = cy * scalar.data
        except (FloatingPointError, OverflowError) as exc:
            raise ValueError("from_scalar: overflow or invalid coefficient/field arithmetic") from exc
        return cls(
            x=ComplexField(data=x_data, grid=scalar.grid, wavelength_m=scalar.wavelength_m),
            y=ComplexField(data=y_data, grid=scalar.grid, wavelength_m=scalar.wavelength_m),
        )

    @property
    def grid(self) -> SamplingGrid:
        """Common immutable sampling grid; pitches are in metres."""
        return self.x.grid

    @property
    def wavelength_m(self) -> float:
        """Common vacuum wavelength in metres."""
        return self.x.wavelength_m

    @property
    def shape(self) -> tuple[int, int]:
        """Common array shape ``(ny, nx)``, not component/port ordering."""
        return self.x.shape

    @property
    def intensity(self) -> np.ndarray:
        """Fresh writable float64 ``abs(Ux)**2 + abs(Uy)**2``, amplitude-unit^2.

        There is no scalar cross term between orthogonal components. Both
        complete intensity and sampled norm must be numerically usable.
        """
        _pair(self.x, self.y, "JonesField.intensity")
        return _diagnostics(self.x, self.y, "JonesField.intensity")[0]

    @property
    def sampled_norm(self) -> float:
        """``sum(I, dtype=float64)*dx*dy``, amplitude-unit^2*m^2, not watts.

        Evaluate that expression left-to-right. Finite inputs may still have
        unusable squares, reductions or intermediate products; no rescaling
        or arbitrary-precision fallback is applied.
        """
        _pair(self.x, self.y, "JonesField.sampled_norm")
        return _diagnostics(self.x, self.y, "JonesField.sampled_norm")[1]


def apply_linear_polarizer(field: JonesField, *, axis_angle_rad: float) -> JonesField:
    """Apply ideal ``e_theta e_theta.T`` in complex amplitude; axis in radians.

    ``e_theta=(cos(theta), sin(theta))``. Angles accept Python int/float and
    NumPy integer/floating scalars excluding booleans/temporal scalars. They
    must convert to finite binary64; nonzero conversion to zero is rejected.
    Evaluate nonzero angles as supplied, without wrapping/snapping. Float
    pi/2 retains its represented extinction residual. Polarizer loss is
    preserved; no cos-squared field factor or normalization is introduced.
    Return fresh independently owned components, including dark outputs.
    """
    theta = _real_angle(axis_angle_rad, "axis_angle_rad")
    _jones(field, "polarizer input")
    c, s = math.cos(theta), math.sin(theta)
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            projected = c * field.x.data + s * field.y.data
            x_data = c * projected
            y_data = s * projected
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError("linear polarizer: overflow or invalid field arithmetic") from exc
    return _from_data(x_data, y_data, field.x)


def apply_linear_retarder(
    field: JonesField, *, axis_angle_rad: float, retardance_rad: float
) -> JonesField:
    """Apply ideal linear retardance on this plane; axis/delta in radians.

    ``W=e_theta e_theta.T + exp(i*delta) e_perp e_perp.T``, where
    ``e_perp=(-sin(theta), cos(theta))``. Element coordinates use R.T and
    conversion back uses R. The axis has reference phase zero; perpendicular
    gets +delta. QWP uses pi/2, HWP pi. The selected complex common phase is
    retained, without multiplication by exp(-i*delta/2) or phase alignment.
    This supplied ideal retardance does not predict material thickness,
    dispersion or absolute optical-path phase.

    Both parameters use the real scalar policy of apply_linear_polarizer.
    No wrapping/snapping occurs; float pi retains its phase residual. Exact
    +/-0 delta returns fresh component copies only after full validation.
    Caller settings, amplitudes and relative phase are not normalized.
    """
    theta = _real_angle(axis_angle_rad, "axis_angle_rad")
    delta = _real_angle(retardance_rad, "retardance_rad")
    _jones(field, "retarder input")
    if delta == 0.0:
        return JonesField(x=field.x, y=field.y)
    c, s = math.cos(theta), math.sin(theta)
    phase = complex(math.cos(delta), math.sin(delta))
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            axis = c * field.x.data + s * field.y.data
            perpendicular = -s * field.x.data + c * field.y.data
            x_data = c * axis - s * phase * perpendicular
            y_data = s * axis + c * phase * perpendicular
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError("linear retarder: overflow or invalid field arithmetic") from exc
    return _from_data(x_data, y_data, field.x)


def transmission_ratio(incident: JonesField, transmitted: JonesField) -> float | None:
    """Dimensionless ``N_transmitted/N_incident``; None for zero incident norm.

    Validate both Jones fields and exact metadata compatibility before the
    zero-denominator shortcut. This diagnostic does not infer/certify a causal
    optical transformation. Compatible independently supplied amplitudes can
    give a finite ratio above one; retain it without clamping or rejection.
    No epsilon denominator is used. NumPy-reported division underflow raises
    ValueError, including an inexact positive subnormal result; a strictly
    positive ratio rounding to zero is also rejected. This is a bounded
    binary64 diagnostic, not arbitrary-dynamic-range support. Caller NumPy
    settings are restored.
    """
    _jones(incident, "incident")
    _jones(transmitted, "transmitted")
    _compatible(incident.x, transmitted.x, "transmission_ratio")
    denominator = incident.sampled_norm
    numerator = transmitted.sampled_norm
    if denominator == 0.0:
        return None
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="raise"):
            ratio = float(np.float64(numerator) / np.float64(denominator))
    except (FloatingPointError, OverflowError) as exc:
        raise ValueError("transmission_ratio: overflow, underflow or invalid ratio arithmetic") from exc
    if not math.isfinite(ratio):
        raise ValueError(f"transmission_ratio: expected finite ratio, got {ratio!r}")
    if numerator > 0.0 and ratio == 0.0:
        raise ValueError("transmission_ratio: strictly positive ratio underflowed to zero")
    return ratio
