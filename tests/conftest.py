"""Shared fixtures for the Milestone 0 test suite.

The grid fixtures deliberately cover the three cases where indexing and
centring bugs hide:

``even_grid``
    Even sample counts, where ``N//2`` centring makes the coordinate span
    asymmetric by one sample.
``odd_grid``
    Odd sample counts, where the span is symmetric and ``N//2`` differs from
    ``(N-1)/2`` arithmetic.
``aniso_grid``
    ``ny != nx`` and ``dy != dx``, so that any axis transposition becomes a
    shape error rather than a silent pass.

The pitches are chosen to be physically realistic (micrometre scale) rather
than convenient round numbers: at ``d = 1.0`` several floating-point
association differences vanish, which would mask exactly the class of bug the
frequency-grid tests exist to catch.
"""

from __future__ import annotations

import numpy as np
import pytest

from ohlab.grid import SamplingGrid
from ohlab.units import NM, UM

#: Red HeNe wavelength, the project's default test wavelength, in metres.
WAVELENGTH_M: float = 633 * NM

#: A representative phase-only SLM pixel pitch, in metres.
SLM_PITCH_M: float = 3.74 * UM


@pytest.fixture
def wavelength() -> float:
    """Vacuum wavelength in metres (633 nm)."""
    return WAVELENGTH_M


@pytest.fixture
def even_grid() -> SamplingGrid:
    """An 8 x 8 grid with a realistic isotropic pitch."""
    return SamplingGrid(ny=8, nx=8, dy=SLM_PITCH_M, dx=SLM_PITCH_M)


@pytest.fixture
def odd_grid() -> SamplingGrid:
    """A 7 x 7 grid with a realistic isotropic pitch."""
    return SamplingGrid(ny=7, nx=7, dy=SLM_PITCH_M, dx=SLM_PITCH_M)


@pytest.fixture
def aniso_grid() -> SamplingGrid:
    """A grid with ``ny != nx`` and ``dy != dx``.

    Any test that could pass under a transposition must use this fixture.
    """
    return SamplingGrid(ny=6, nx=10, dy=5.0 * UM, dx=3.74 * UM)


@pytest.fixture
def rng() -> np.random.Generator:
    """A seeded NumPy generator, for reproducible test data."""
    return np.random.default_rng(20260808)
