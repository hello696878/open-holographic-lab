"""Sampling and thin-element action on physical SI coordinates.

These operations do not propagate and never normalize amplitude or intensity.
Expected decaying exponential tails and finite field/transmission products may
underflow locally; derived geometry, overflow and invalid arithmetic may not.
"""

from __future__ import annotations

import math

import numpy as np

from ..field import ComplexField
from ..grid import SamplingGrid
from .model import (CircularAperture, Component, GaussianSource,
                    RectangularAperture, SequentialExperiment, ThinLens,
                    UniformSource, _validate_component_geometry, _validate_grid,
                    _validate_source_geometry)

__all__ = ["sample_source", "apply_component"]


def _owned_field(data: np.ndarray, grid: SamplingGrid,
                 wavelength_m: float) -> ComplexField:
    """Return existing ComplexField semantics with owned byte-backed storage."""
    field = ComplexField(data=data, grid=grid, wavelength_m=wavelength_m)
    immutable = np.frombuffer(field.data.tobytes(order="C"), dtype=np.complex128).reshape(grid.shape)
    object.__setattr__(field, "data", immutable)
    return field


def _validate_field(field: ComplexField) -> None:
    if not isinstance(field, ComplexField):
        raise TypeError(f"field: expected ComplexField, got {type(field).__name__}")
    _validate_grid(field.grid, field.wavelength_m)
    if field.data.dtype != np.dtype(np.complex128) or field.data.shape != field.grid.shape:
        raise ValueError("field: expected complex128 data on its complete grid")
    if not np.all(np.isfinite(field.data)):
        raise ValueError("field: expected finite complex data")


def sample_source(experiment: SequentialExperiment) -> ComplexField:
    """Sample the specified source at z=0; coordinates/wavelength are metres.

    Gaussian waist peak amplitude is in arbitrary field units. Gaussian tails
    reaching numerical zero are permitted only in the exponential and ensuing
    attenuated products. Caller NumPy error settings are restored on return.
    """
    if not isinstance(experiment, SequentialExperiment):
        raise TypeError(f"experiment: expected SequentialExperiment, got {type(experiment).__name__}")
    grid, lam, source = experiment.grid, experiment.wavelength_m, experiment.source
    _validate_grid(grid, lam)
    _validate_source_geometry(source, grid, lam)
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="raise"):
            if isinstance(source, UniformSource):
                phase = np.exp(1j * source.phase_rad)
                # Multiplication by finite unit-modulus transmission may underflow.
                with np.errstate(under="ignore"):
                    data = np.full(grid.shape, source.amplitude * phase, dtype=np.complex128)
            elif isinstance(source, GaussianSource):
                x, y = grid.meshgrid()
                r2 = (x - source.center_x_m)**2 + (y - source.center_y_m)**2
                waist2 = source.waist_radius_m**2
                rayleigh = math.pi * waist2 / lam
                s = -source.waist_z_m
                b = complex(1, s / rayleigh)
                exponent = -r2 / (waist2 * b)
                carrier = np.exp(1j * (2 * math.pi / lam * s + source.phase_rad))
                if source.amplitude == 0:
                    data = np.zeros(grid.shape, dtype=np.complex128)
                else:
                    with np.errstate(under="ignore"):
                        envelope = np.exp(exponent)
                        data = (source.amplitude / b) * envelope * carrier
            else:
                raise TypeError(f"source: unsupported {type(source).__name__}")
    except (FloatingPointError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError(f"source arithmetic is unusable in binary64: {exc}") from exc
    if not np.all(np.isfinite(data)):
        raise ValueError("source arithmetic produced nonfinite field values")
    return _owned_field(data, grid, lam)


def apply_component(field: ComplexField, component: Component) -> ComplexField:
    """Apply only the specified transmission at the supplied field's plane.

    All component dimensions/focal lengths are metres. component.z_m has no
    effect on this action; only the runner is responsible for propagation.
    Grid/wavelength and caller-owned field data are preserved. Masks are
    inclusive binary amplitude transmission, with no lens clear aperture.
    """
    _validate_field(field)
    grid, lam = field.grid, field.wavelength_m
    _validate_component_geometry(component, grid, lam)
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="raise"):
            x, y = grid.meshgrid()
            if isinstance(component, CircularAperture):
                transmission = x*x + y*y <= component.radius_m**2
            elif isinstance(component, RectangularAperture):
                transmission = ((np.abs(x) <= component.width_m / 2)
                                & (np.abs(y) <= component.height_m / 2))
            elif isinstance(component, ThinLens):
                phase = (-(2 * math.pi / lam) / (2 * component.focal_length_m)) * (x*x + y*y)
                transmission = np.exp(1j * phase)
            else:
                raise TypeError(f"component: unsupported {type(component).__name__}")
            with np.errstate(under="ignore"):
                data = field.data * transmission
    except (FloatingPointError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError(f"component {component.id!r} arithmetic is unusable in binary64: {exc}") from exc
    if not np.all(np.isfinite(data)):
        raise ValueError(f"component {component.id!r} produced nonfinite field values")
    return _owned_field(data, grid, lam)
