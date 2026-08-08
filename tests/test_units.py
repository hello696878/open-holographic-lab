"""Tests for :mod:`ohlab.units` (Milestone 0, IDs U-01 .. U-04).

These constants are the only place a non-SI number is allowed to appear in
user code, so their values are asserted exactly.
"""

from __future__ import annotations

import math

import pytest

from ohlab import units


def test_u01_length_multipliers_are_exact() -> None:
    """U-01: metric length prefixes have their exact defined values.

    Exact comparison is correct here: these are definitions, not computed
    quantities, and each is exactly representable relative to 1 metre only in
    the sense of being the nearest double to the decimal value -- which is
    what the literal produces on both sides.
    """
    assert units.NM == 1e-9
    assert units.UM == 1e-6
    assert units.MM == 1e-3
    assert units.CM == 1e-2


def test_u02_degree_is_pi_over_180() -> None:
    """U-02: ``DEG`` equals ``math.pi / 180`` exactly."""
    assert units.DEG == math.pi / 180.0


def test_u03_wavelength_expression_round_trips(
) -> None:
    """U-03: ``633 * NM`` recovers 633 to float64 relative precision.

    Tolerance ``rtol=1e-15`` is about 4.5 machine epsilon, covering the two
    rounding steps (multiply then divide) without being loose enough to hide a
    wrong constant, which would be off by a factor of 1000 or more.
    """
    assert (633 * units.NM) / units.NM == pytest.approx(633.0, rel=1e-15)
    assert (3.74 * units.UM) / units.UM == pytest.approx(3.74, rel=1e-15)


def test_u04_module_exports_only_multipliers() -> None:
    """U-04: the module exposes multipliers only, no conversion functions.

    A conversion helper would invite a non-SI value to be stored or passed
    onward, which ``docs/math_conventions.md`` section 2 forbids.
    """
    assert set(units.__all__) == {"NM", "UM", "MM", "CM", "DEG"}
    for name in units.__all__:
        assert isinstance(getattr(units, name), float)
