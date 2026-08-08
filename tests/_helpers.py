"""Shared assertion helpers for the Milestone 0 test suite.

Not a test module (the filename does not match ``test_*.py``), so pytest does
not collect it. It is importable from the test modules because pytest's
default ``prepend`` import mode puts the ``tests/`` directory on ``sys.path``.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "wrapped_phase_difference",
    "assert_phase_allclose",
    "assert_bit_identical",
]


def wrapped_phase_difference(
    actual: np.ndarray | float, expected: np.ndarray | float
) -> np.ndarray:
    """Return ``actual - expected`` wrapped into the canonical branch.

    Phase is only ever defined modulo ``2*pi``, so a naive subtraction can
    report a difference of nearly ``2*pi`` for two phases that are physically
    identical -- for instance ``+pi`` versus ``-pi``, or a value that has
    crossed the branch cut of ``np.angle``.

    Wrapping through the unit circle,
    ``angle(exp(i * (actual - expected)))``, maps any such difference back
    into ``(-pi, +pi]`` and returns ``0`` for physically equal phases
    regardless of branch.

    Returns
    -------
    ndarray
        The wrapped difference, in radians, in ``(-pi, +pi]``.
    """
    return np.angle(np.exp(1j * (np.asarray(actual) - np.asarray(expected))))


def assert_phase_allclose(
    actual: np.ndarray,
    expected: np.ndarray | float,
    *,
    atol: float,
    amplitude: np.ndarray | None = None,
    amplitude_floor: float = 0.0,
) -> None:
    """Assert two phase maps agree modulo ``2*pi``, ignoring undefined pixels.

    Parameters
    ----------
    actual, expected:
        Phase maps in radians. Any branch is acceptable; the comparison is
        performed on the wrapped difference.
    atol:
        Absolute tolerance on the wrapped difference, in radians. Mandatory
        and keyword-only -- this project never uses a default tolerance.
    amplitude:
        Optional amplitude map. Where the amplitude does not exceed
        ``amplitude_floor`` the phase is physically undefined (section 3.2)
        and those pixels are excluded from the comparison.
    amplitude_floor:
        Threshold below which amplitude counts as zero.
    """
    difference = wrapped_phase_difference(actual, expected)
    if amplitude is not None:
        defined = np.asarray(amplitude) > amplitude_floor
        difference = difference[defined]
        assert difference.size > 0, (
            "no pixels had defined phase; the test would be vacuous"
        )
    np.testing.assert_allclose(
        difference, np.zeros_like(difference), rtol=0.0, atol=atol
    )


def assert_bit_identical(actual: np.ndarray, desired: np.ndarray) -> None:
    """Assert two float arrays are identical bit for bit.

    Used only where exactness is the property under test -- agreement with
    ``numpy.fft.fftfreq``, coordinate centring, and immutability. Every such
    call site carries a comment saying why exactness is required.
    """
    np.testing.assert_array_equal(actual, desired)
    assert actual.dtype == desired.dtype, (
        f"dtype mismatch: {actual.dtype} vs {desired.dtype}"
    )
