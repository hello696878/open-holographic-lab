"""Open Holographic Lab (``ohlab``).

A reproducible computer-generated holography (CGH) simulator.

This package provides an exactly-specified, exactly-tested representation
of a sampled complex optical field
(:class:`~ohlab.field.ComplexField`) and its coordinate and frequency grids
(:class:`~ohlab.grid.SamplingGrid`), and free-space propagation by the Angular
Spectrum Method (:func:`~ohlab.propagation.propagate_angular_spectrum`). Target
intensity and amplitude preparation lives in :mod:`ohlab.targets`; optional
strict grayscale PNG loading lives in :mod:`ohlab.io.images`. These modules
are imported explicitly rather than re-exported here. Single-plane phase-only
synthesis on a complete periodic grid lives in :mod:`ohlab.algorithms`.
Plotting and file I/O remain outside the numerical core.

Normative references
--------------------
``docs/math_conventions.md``
    Units, sign conventions, array layout, coordinate and frequency grid
    definitions, FFT normalization. Code must match that document.
``docs/milestones.md``
    Milestone scope, status, and recorded limitations.

Quick start
-----------
>>> from ohlab import ComplexField, SamplingGrid
>>> from ohlab.units import NM, UM
>>> grid = SamplingGrid(ny=256, nx=256, dy=3.74 * UM, dx=3.74 * UM)
>>> field = ComplexField.random_phase(grid=grid, wavelength_m=633 * NM, seed=0)
>>> field.shape
(256, 256)

Notes
-----
``__version__`` is assigned as a plain string literal and must stay that way:
``pyproject.toml`` resolves the distribution version from it via
``[tool.setuptools.dynamic]``, which relies on static analysis of this file.
"""

from __future__ import annotations

#: Package version. Single source of truth for the version string; read by
#: ``pyproject.toml`` via ``[tool.setuptools.dynamic]``. Keep as a literal.
__version__: str = "0.1.0.dev0"

from . import units
from .field import ComplexField
from .grid import SamplingGrid
from .propagation import (
    angular_spectrum_transfer_function,
    propagate_angular_spectrum,
)

__all__ = [
    "ComplexField",
    "SamplingGrid",
    "angular_spectrum_transfer_function",
    "propagate_angular_spectrum",
    "units",
    "__version__",
]
