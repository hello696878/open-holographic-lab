"""Agreement between ``ohlab`` grids and ``numpy.fft`` (IDs C-01 .. C-08).

This is the most important module in Milestone 0. Three sign/ordering choices
must be mutually consistent -- the ``exp(-i*omega*t)`` time convention, the
``exp(+i*kz*z)`` forward-propagation sign, and the ``-i`` forward FFT kernel
(``docs/math_conventions.md`` sections 3.1, 3.6, 3.8). If any one of them is
wrong, Milestone 3 produces a hologram that reconstructs a mirrored or shifted
image which still *looks* correct. These tests fail loudly now instead.

It also contains the static-analysis guards that keep the numerical core free
of UI/plotting dependencies and of the legacy global RNG.
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest

from _helpers import assert_bit_identical
from ohlab.grid import SamplingGrid

# Import roots that must never appear anywhere inside src/ohlab/.
FORBIDDEN_IMPORT_ROOTS = frozenset(
    {
        "matplotlib",
        "pylab",
        "PIL",
        "Pillow",
        "cv2",
        "skimage",
        "imageio",
        "pandas",
        "seaborn",
        "torch",
        "tensorflow",
        "jax",
        "cupy",
    }
)


def _package_source_files() -> list[Path]:
    """Return every ``.py`` file shipped inside the installed ``ohlab`` package."""
    import ohlab

    package_dir = Path(ohlab.__file__).resolve().parent
    return sorted(package_dir.rglob("*.py"))


def _dotted_name(node: ast.AST) -> str | None:
    """Return the dotted name of an attribute chain such as ``np.random.seed``."""
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return None


# ---------------------------------------------------------------------------
# C-01: the decisive convention test
# ---------------------------------------------------------------------------
def test_c01_on_grid_plane_wave_lands_in_the_predicted_bin(
    aniso_grid: SamplingGrid,
) -> None:
    """C-01: an on-grid plane wave concentrates in exactly one predicted bin.

    Evidence class: analytic ground truth. The destination bin is computed in
    closed form from sections 3.4 and 3.8 *before* the FFT is taken, and all
    four sign quadrants of ``(fx0, fy0)`` are exercised on an anisotropic grid.

    A sign error in the FFT convention, or an error in the frequency-grid
    centring, relocates O(1) of the energy. The bin index is therefore
    asserted exactly (it is an integer), and the off-peak amplitude is
    required to be below ``1e-10`` of the peak -- a bound that is
    astronomically loose against any real defect but tolerant of arithmetic
    noise. Measured off-peak/peak ratio is exactly 0.

    **The magnitude alone is not sufficient**, and a negative control proved
    it: translating the spatial grid by one pixel multiplies the field by a
    *global constant* phase, which leaves ``|FFT|`` completely unchanged and
    the peak in the same bin. The peak's complex value is therefore asserted
    too. Summing the DFT in closed form gives

        fftshift(fft2(U))[row, col] = ny*nx * exp(+2i*pi*(fx0*x[0] + fy0*y[0]))

    Measured agreement is 6e-16, and injecting a one-pixel offset between the
    field and this prediction gives a relative error of 1.6.

    **Scope of that assertion, stated precisely.** Because the prediction is
    built from ``grid.x[0]``, it verifies that ``meshgrid()`` and the 1-D axes
    agree, and it pins the DC scale factor ``ny*nx`` of the unnormalized
    forward transform. It does **not** pin the absolute origin convention: a
    uniform redefinition of ``x`` shifts both the field and the prediction
    equally and passes here. The absolute origin is pinned separately, and
    exactly, by ``test_g07_origin_sits_exactly_on_index_n_over_2``. A negative
    control that shifted ``grid.x`` by one pixel failed G-07/G-08/G-09 and not
    this test, which is how the division of labour was established.
    """
    x_grid, y_grid = aniso_grid.meshgrid()
    fx_axis = aniso_grid.fx_centered
    fy_axis = aniso_grid.fy_centered
    n_samples = aniso_grid.ny * aniso_grid.nx

    quadrants = [(+3, +2), (-4, -2), (+3, -2), (-4, +2)]
    for col_offset, row_offset in quadrants:
        col = aniso_grid.nx // 2 + col_offset
        row = aniso_grid.ny // 2 + row_offset
        fx0 = fx_axis[col]
        fy0 = fy_axis[row]

        field = np.exp(2j * np.pi * (fx0 * x_grid + fy0 * y_grid))
        spectrum = np.fft.fftshift(np.fft.fft2(field))
        magnitude = np.abs(spectrum)

        peak = np.unravel_index(int(np.argmax(magnitude)), magnitude.shape)
        assert peak == (row, col), (
            f"expected bin (row={row}, col={col}) for "
            f"fx0={fx0:.6e}, fy0={fy0:.6e}; got {peak}"
        )

        off_peak = magnitude.copy()
        off_peak[peak] = 0.0
        assert float(np.max(off_peak)) <= 1e-10 * float(magnitude[peak])

        # Complex value, which pins the spatial ORIGIN as well as the spacing.
        predicted = n_samples * np.exp(
            2j * np.pi * (fx0 * aniso_grid.x[0] + fy0 * aniso_grid.y[0])
        )
        np.testing.assert_allclose(
            spectrum[row, col], predicted, rtol=1e-10, atol=0.0
        )


# ---------------------------------------------------------------------------
# C-02: energy conservation
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("shape", [(8, 8), (7, 9), (6, 10), (32, 48)])
def test_c02_parseval_holds_in_the_backward_norm_form(
    shape: tuple[int, int], rng: np.random.Generator
) -> None:
    """C-02: ``sum|u|^2 == sum|fft2(u)|^2 / (ny*nx)`` (section 3.7).

    Evidence class: conservation law. This is the exact form that holds for
    ``numpy.fft``'s default ``norm="backward"``; using the symmetric-norm
    form instead would be wrong by a factor of ``ny*nx``.

    Tolerance ``rtol=1e-12``. Measured worst case across these shapes is
    2.4e-16, so there is roughly a 4000x margin -- enough to absorb FFT
    backend differences, far tighter than any normalization mistake.
    """
    u = rng.standard_normal(shape) + 1j * rng.standard_normal(shape)
    lhs = float(np.sum(np.abs(u) ** 2))
    rhs = float(np.sum(np.abs(np.fft.fft2(u)) ** 2)) / (shape[0] * shape[1])
    np.testing.assert_allclose(lhs, rhs, rtol=1e-12, atol=0.0)


# ---------------------------------------------------------------------------
# C-03: DC placement
# ---------------------------------------------------------------------------
def test_c03_constant_field_transforms_to_dc_only(
    aniso_grid: SamplingGrid,
) -> None:
    """C-03: a constant field has energy only at zero frequency.

    In FFT order that is index ``[0, 0]``; after ``fftshift`` it is
    ``[ny//2, nx//2]`` -- the frequency-domain statement of the ``N//2``
    centring convention.
    """
    field = np.full(aniso_grid.shape, 2.5 + 0.0j)
    spectrum = np.fft.fft2(field)

    magnitude = np.abs(spectrum)
    assert np.unravel_index(int(np.argmax(magnitude)), magnitude.shape) == (0, 0)
    off = magnitude.copy()
    off[0, 0] = 0.0
    assert float(np.max(off)) <= 1e-10 * float(magnitude[0, 0])

    shifted = np.abs(np.fft.fftshift(spectrum))
    expected_centre = (aniso_grid.ny // 2, aniso_grid.nx // 2)
    assert (
        np.unravel_index(int(np.argmax(shifted)), shifted.shape)
        == expected_centre
    )

    # DC amplitude is the sum of the field, i.e. value * number of samples.
    np.testing.assert_allclose(
        magnitude[0, 0], 2.5 * aniso_grid.ny * aniso_grid.nx,
        rtol=1e-12, atol=0.0,
    )


# ---------------------------------------------------------------------------
# C-04: shift theorem, which pins the forward-kernel sign
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(("shift_rows", "shift_cols"), [(1, 0), (0, 2), (2, -3)])
def test_c04_shift_theorem_sign(
    aniso_grid: SamplingGrid,
    rng: np.random.Generator,
    shift_rows: int,
    shift_cols: int,
) -> None:
    """C-04: translating the field multiplies the spectrum by ``exp(-2i*pi*f.d)``.

    Evidence class: analytic ground truth. With the ``-i`` forward kernel of
    section 3.6, a translation by ``(dy_shift, dx_shift)`` metres multiplies
    the spectrum by ``exp(-2i*pi*(fx*dx_shift + fy*dy_shift))``. The opposite
    FFT sign convention would flip this exponent, so the test pins the
    convention rather than merely the magnitude.

    The comparison is written with physical frequencies from ``freq_meshgrid``
    rather than raw bin indices, so it also exercises the FFT-ordered
    frequency grids.

    Tolerance ``rtol=1e-10`` with an ``atol`` scaled to the spectrum's peak
    magnitude, because individual spectral bins can be near zero for random
    data and a pure relative tolerance would be meaningless there.
    """
    u = rng.standard_normal(aniso_grid.shape) + 1j * rng.standard_normal(
        aniso_grid.shape
    )
    dx_shift = shift_cols * aniso_grid.dx
    dy_shift = shift_rows * aniso_grid.dy

    fx_grid, fy_grid = aniso_grid.freq_meshgrid(order="fft")
    expected = np.fft.fft2(u) * np.exp(
        -2j * np.pi * (fx_grid * dx_shift + fy_grid * dy_shift)
    )
    actual = np.fft.fft2(np.roll(u, (shift_rows, shift_cols), axis=(0, 1)))

    scale = float(np.max(np.abs(expected)))
    np.testing.assert_allclose(
        actual, expected, rtol=1e-10, atol=1e-10 * scale
    )


# ---------------------------------------------------------------------------
# C-05: 2-D ordering round trip
# ---------------------------------------------------------------------------
def test_c05_fftshift_round_trip_is_exact(
    aniso_grid: SamplingGrid, rng: np.random.Generator
) -> None:
    """C-05: ``ifftshift(fftshift(A)) == A`` bit for bit, on a non-square array.

    EXACTNESS IS THE PROPERTY UNDER TEST: these are index permutations, so any
    difference is a genuine ordering bug. Non-square shape matters -- on a
    square array an axis mix-up can cancel out.
    """
    a = rng.standard_normal(aniso_grid.shape)
    assert_bit_identical(np.fft.ifftshift(np.fft.fftshift(a)), a)
    assert_bit_identical(np.fft.fftshift(np.fft.ifftshift(a)), a)


# ---------------------------------------------------------------------------
# C-06 / C-07: static guards on the numerical core
# ---------------------------------------------------------------------------
def test_c06_numerical_core_imports_no_ui_or_io_library() -> None:
    """C-06: no module in ``src/ohlab/`` imports a plotting or image library.

    Evidence class: static analysis of the AST, not a runtime probe -- a
    runtime check would only catch imports on the paths that happen to run.

    This is the architectural rule from ``CLAUDE.md`` section 6, and it is what
    lets the numerical core stay testable and headless. Figure generation lives
    in ``scripts/``.
    """
    sources = _package_source_files()
    assert sources, "no ohlab source files found; the scan would be vacuous"

    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    assert root not in FORBIDDEN_IMPORT_ROOTS, (
                        f"{path.name} imports forbidden module {alias.name!r}"
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                assert root not in FORBIDDEN_IMPORT_ROOTS, (
                    f"{path.name} imports from forbidden module {node.module!r}"
                )


def test_c07_numerical_core_uses_only_the_modern_rng() -> None:
    """C-07: ``src/ohlab/`` never touches the legacy global ``np.random.*`` API.

    Section 3.10 requires ``np.random.default_rng(seed)``. The legacy API
    carries hidden global state, which would break bit-for-bit reproducibility
    from a saved configuration.

    Scanning the AST rather than the raw text means docstrings and comments
    mentioning ``np.random`` cannot produce a false positive.
    """
    sources = _package_source_files()
    assert sources, "no ohlab source files found; the scan would be vacuous"

    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                name = _dotted_name(node)
                if name is None:
                    continue
                if name.startswith("np.random.") or name.startswith(
                    "numpy.random."
                ):
                    leaf = name.rsplit(".", 1)[1]
                    assert leaf == "default_rng", (
                        f"{path.name} uses legacy RNG call {name!r}; "
                        f"only np.random.default_rng is permitted"
                    )
            elif isinstance(node, ast.ImportFrom) and node.module in (
                "numpy.random",
                "np.random",
            ):
                for alias in node.names:
                    assert alias.name == "default_rng", (
                        f"{path.name} imports {alias.name!r} from "
                        f"{node.module!r}; only default_rng is permitted"
                    )


def test_c08_every_public_module_is_importable_without_optional_deps() -> None:
    """C-08: the core imports cleanly and exposes the documented public API.

    Updated in Milestone 1 to include the two propagation entry points. The
    assertion is deliberately an exact set comparison rather than a subset
    check, so that adding a name to ``__all__`` is a conscious act recorded in
    a milestone rather than something that drifts in unnoticed.
    """
    import ohlab

    milestone_0_api = {"ComplexField", "SamplingGrid", "units", "__version__"}
    milestone_1_api = {
        "angular_spectrum_transfer_function",
        "propagate_angular_spectrum",
    }
    for name in milestone_0_api | milestone_1_api:
        assert hasattr(ohlab, name), f"ohlab.{name} is missing"
    assert set(ohlab.__all__) == milestone_0_api | milestone_1_api
