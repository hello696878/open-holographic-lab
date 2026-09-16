"""Agreement between ``ohlab`` grids and ``numpy.fft`` (IDs C-01 .. C-11).

These tests pin the selected Fourier kernel, frequency labels, normalization,
and coordinate origin (``docs/math_conventions.md`` sections 3.6--3.8).
NumPy's Fourier kernel does not select the physical time convention. Propagation
signs have separate analytic tests in ``test_propagation_analytic.py``.
C-09--C-11 were added in the 2026-09-14 corrective maintenance: independent
direct sums check the physical spectrum and both Fourier sign pairs without
changing the production transform pair.

It also contains the static-analysis guards that keep the numerical core free
of UI/plotting dependencies and of the legacy global RNG.
"""

from __future__ import annotations

import ast
import cmath
from importlib.util import resolve_name
import math
from pathlib import Path

import numpy as np
import pytest

from _helpers import assert_bit_identical
from ohlab import ComplexField, propagate_angular_spectrum
from ohlab.grid import SamplingGrid

# Forbidden throughout src/ohlab/, except PIL in exactly io/images.py.
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


def _assert_import_boundaries(source: str, relative_path: Path) -> None:
    """Check ordinary imports, including aliases and function-local imports.

    ``relative_path`` is relative to the ``ohlab`` package directory. Resolve
    relative imports from that file's package; this applies equally to module
    files and ``__init__.py``. This bounded AST check does not resolve dynamic
    imports or attribute access through arbitrary runtime objects.
    """
    tree = ast.parse(source, filename=str(relative_path))
    package = ".".join(("ohlab", *relative_path.parent.parts))
    in_io = relative_path.parts[0] == "io"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                module = resolve_name("." * node.level + module, package)
            imported_names = [module]
            imported_names.extend(f"{module}.{alias.name}" for alias in node.names)
        else:
            continue

        for name in imported_names:
            root = name.split(".")[0]
            permitted_pil = (
                root == "PIL" and relative_path.as_posix() == "io/images.py"
            )
            assert root not in FORBIDDEN_IMPORT_ROOTS or permitted_pil, (
                f"{relative_path} imports forbidden module {name!r}"
            )
            imports_io = name == "ohlab.io" or name.startswith("ohlab.io.")
            assert in_io or not imports_io, (
                f"{relative_path} imports I/O module {name!r} into the numerical core"
            )


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

        # Pins meshgrid/axis consistency and DFT scale, not the absolute origin.
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
    """C-06: image decoding is confined to ``ohlab/io/images.py``.

    Evidence class: static analysis of the AST, not a runtime probe -- a
    runtime check would only catch imports on the paths that happen to run.

    AGENTS.md keeps the numerical core independent of I/O. The M2 exception
    permits PIL only in the designated decoder module. Every source file is
    scanned, including package initializers; core modules cannot import
    ``ohlab.io`` directly or through ordinary relative/aliased imports.
    All other plotting, image, UI and accelerator prohibitions remain in force.
    """
    import ohlab

    package_dir = Path(ohlab.__file__).resolve().parent
    sources = _package_source_files()
    assert sources, "no ohlab source files found; the scan would be vacuous"

    for path in sources:
        _assert_import_boundaries(
            path.read_text(encoding="utf-8"), path.relative_to(package_dir)
        )


@pytest.mark.parametrize(
    ("relative_path", "source"),
    [
        ("io/images.py", "from PIL import Image"),
        ("io/images.py", "import PIL.Image as decoder"),
        ("io/images.py", "def load():\n    from PIL import Image as decoder"),
        ("io/__init__.py", "from .images import load_target_intensity"),
        ("targets.py", "import io\nfrom .grid import SamplingGrid"),
        ("__init__.py", "from . import units"),
        ("algorithms/__init__.py", "from .. import targets"),
        ("targets.py", "import ohlab.iota as unrelated"),
        ("targets.py", "# import PIL\ntext = 'from ohlab import io'"),
    ],
)
def test_c06_import_guard_accepts_only_the_designated_exception(
    relative_path: str, source: str
) -> None:
    """Positive controls distinguish the I/O subtree from similarly named imports."""
    _assert_import_boundaries(source, Path(relative_path))


@pytest.mark.parametrize(
    "relative_path",
    [
        "field.py",
        "targets.py",
        "__init__.py",
        "io/__init__.py",
        "io/other.py",
        "io/sub/images.py",
        "io/Images.py",
    ],
)
def test_c06_pil_exception_requires_the_exact_decoder_path(relative_path: str) -> None:
    with pytest.raises(AssertionError, match="forbidden module 'PIL'"):
        _assert_import_boundaries("from PIL import Image", Path(relative_path))


@pytest.mark.parametrize("root", sorted(FORBIDDEN_IMPORT_ROOTS - {"PIL"}))
def test_c06_other_forbidden_dependencies_stay_forbidden_in_io(root: str) -> None:
    with pytest.raises(AssertionError, match="forbidden module"):
        _assert_import_boundaries(f"import {root} as library", Path("io/images.py"))


@pytest.mark.parametrize(
    ("relative_path", "source"),
    [
        ("targets.py", "import ohlab.io"),
        ("targets.py", "import ohlab.io.images as images"),
        ("targets.py", "from ohlab.io.images import load_target_intensity as load"),
        ("targets.py", "from ohlab import io as files"),
        ("targets.py", "from . import io as files"),
        ("targets.py", "from .io import images"),
        ("targets.py", "from .io.images import load_target_intensity"),
        ("targets.py", "def prepare():\n    from . import io"),
        ("__init__.py", "from . import io"),
        ("__init__.py", "from ohlab.io import images"),
        ("algorithms/prepare.py", "from .. import io as files"),
        ("algorithms/prepare.py", "from ..io.images import load_target_intensity"),
        ("algorithms/__init__.py", "from ..io import images"),
        ("algorithms/__init__.py", "def prepare():\n    import ohlab.io as files"),
    ],
)
def test_c06_import_guard_rejects_core_to_io_dependencies(
    relative_path: str, source: str
) -> None:
    with pytest.raises(AssertionError, match="imports I/O module"):
        _assert_import_boundaries(source, Path(relative_path))


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


@pytest.mark.parametrize(
    ("source", "permitted"),
    [
        ("rng = np.random.default_rng(0)", True),
        ("rng = numpy.random.default_rng(0)", True),
        ("from numpy.random import default_rng as make_rng", True),
        ("# np.random.seed(0)\ntext = 'numpy.random.rand()'", True),
        ("np.random.seed(0)", False),
        ("numpy.random.rand(2)", False),
        ("from numpy.random import seed as set_seed", False),
        ("from np.random import rand", False),
        ("def prepare():\n    np.random.normal()", False),
    ],
)
def test_c07_existing_rng_guard_supported_forms(
    source: str, permitted: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise the actual unchanged RNG guard without broadening its syntax scope."""
    probe = tmp_path / "rng_probe.py"
    probe.write_text(source, encoding="utf-8")
    monkeypatch.setitem(globals(), "_package_source_files", lambda: [probe])
    if permitted:
        test_c07_numerical_core_uses_only_the_modern_rng()
    else:
        with pytest.raises(AssertionError, match="only .*default_rng"):
            test_c07_numerical_core_uses_only_the_modern_rng()


def test_c08_documented_public_api_is_available() -> None:
    """C-08: the installed package exposes the documented public API.

    Updated in Milestone 1 to include the two propagation entry points. The
    assertion is deliberately an exact set comparison rather than a subset
    check, so that adding a name to ``__all__`` is a conscious act recorded in
    a milestone rather than something that drifts in unnoticed. This run has
    the development dependencies installed; it does not establish successful
    import in an environment without optional dependencies.
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


# ---------------------------------------------------------------------------
# C-09 .. C-11: centered-coordinate spectrum and independent direct sums
# ---------------------------------------------------------------------------
def _physical_spectrum_via_fft(
    data: np.ndarray, grid: SamplingGrid, kernel_sign: int
) -> np.ndarray:
    """Test subject for section 3.7, in a.u. * m^2; never used by production.

    ``kernel_sign=-1`` is the selected analysis kernel. ``+1`` exercises the
    alternative transform pair, using an unnormalized positive-kernel DFT.
    Keep the origin factor explicit so its omission can be a negative control.
    """
    fx, fy = grid.freq_meshgrid(order="fft")
    origin_phase = np.exp(
        kernel_sign * 2j * np.pi * (fx * grid.x[0] + fy * grid.y[0])
    )
    raw_spectrum = (
        np.fft.fft2(data)
        if kernel_sign == -1
        else np.fft.ifft2(data) * data.size
    )
    return grid.pixel_area * origin_phase * raw_spectrum


def _direct_physical_spectrum(
    data: np.ndarray, grid: SamplingGrid, kernel_sign: int
) -> np.ndarray:
    """Independent rectangular sum on physical coordinates, in a.u. * m^2.

    No FFT, shift, library coordinate/frequency accessor, or origin-correction
    helper is used. Signed bin integers and sample positions are built from
    counts and pitches, then the physical Fourier kernel is summed directly.
    """
    result = np.empty(grid.shape, dtype=np.complex128)
    for row in range(grid.ny):
        bin_y = row if row < (grid.ny + 1) // 2 else row - grid.ny
        fy = bin_y / (grid.ny * grid.dy)
        for col in range(grid.nx):
            bin_x = col if col < (grid.nx + 1) // 2 else col - grid.nx
            fx = bin_x / (grid.nx * grid.dx)
            total = 0j
            for i in range(grid.ny):
                y = (i - grid.ny // 2) * grid.dy
                for j in range(grid.nx):
                    x = (j - grid.nx // 2) * grid.dx
                    total += data[i, j] * cmath.exp(
                        kernel_sign * 2j * math.pi * (fx * x + fy * y)
                    )
            result[row, col] = grid.dx * grid.dy * total
    return result


def _direct_physical_synthesis(
    spectrum: np.ndarray, grid: SamplingGrid, kernel_sign: int
) -> np.ndarray:
    """Independent inverse sum, in a.u.; opposite kernel and frequency-cell area.

    Like the forward reference, this uses only scalar coordinates, signed bin
    integers, and complex exponentials. It calls no FFT or correction helper.
    """
    result = np.empty(grid.shape, dtype=np.complex128)
    for i in range(grid.ny):
        y = (i - grid.ny // 2) * grid.dy
        for j in range(grid.nx):
            x = (j - grid.nx // 2) * grid.dx
            total = 0j
            for row in range(grid.ny):
                bin_y = row if row < (grid.ny + 1) // 2 else row - grid.ny
                fy = bin_y / (grid.ny * grid.dy)
                for col in range(grid.nx):
                    bin_x = col if col < (grid.nx + 1) // 2 else col - grid.nx
                    fx = bin_x / (grid.nx * grid.dx)
                    total += spectrum[row, col] * cmath.exp(
                        -kernel_sign * 2j * math.pi * (fx * x + fy * y)
                    )
            result[i, j] = total / (grid.ny * grid.nx * grid.dy * grid.dx)
    return result


@pytest.mark.parametrize("shape", [(5, 8), (6, 7)])
@pytest.mark.parametrize("kernel_sign", [-1, +1])
@pytest.mark.parametrize("source_kind", ["center_impulse", "complex"])
def test_c09_physical_spectrum_matches_independent_coordinate_sum(
    shape: tuple[int, int], kernel_sign: int, source_kind: str
) -> None:
    """C-09: both Fourier kernels need the physical origin factor (section 3.7).

    The center impulse has a constant physical spectrum, independently of any
    transform formula. Nontrivial seeded complex data tests every kernel sum.
    Mixed parities and unequal pitches expose half-grid and axis mistakes.

    Before this test was added, the 2026-09-14 probe measured maximum absolute
    error / (pixel_area * sum(abs(data))) <= 1.41e-15. The tolerance is
    rtol=1e-12, atol=1e-12 times that triangle-inequality spectral bound: it
    allows near-zero bins without imposing a dimensionless floor on ~1e-11
    a.u.*m^2 spectra. Omitting the origin factor gives scaled errors 0.517--2.
    """
    grid = SamplingGrid(ny=shape[0], nx=shape[1], dy=5e-6, dx=3.74e-6)
    if source_kind == "center_impulse":
        data = np.zeros(shape, dtype=np.complex128)
        data[grid.ny // 2, grid.nx // 2] = 1.0
    else:
        rng = np.random.default_rng(20260914)
        data = rng.standard_normal(shape) + 1j * rng.standard_normal(shape)
    expected = _direct_physical_spectrum(data, grid, kernel_sign)
    actual = _physical_spectrum_via_fft(data, grid, kernel_sign)
    scale = grid.pixel_area * float(np.sum(np.abs(data)))
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12 * scale)
    if source_kind == "center_impulse":
        np.testing.assert_allclose(
            actual, np.full(shape, grid.pixel_area),
            rtol=1e-12, atol=1e-12 * grid.pixel_area,
        )


@pytest.mark.parametrize("shape", [(5, 8), (6, 7)])
@pytest.mark.parametrize("kernel_sign", [-1, +1])
def test_c10_each_fourier_sign_pair_inverts_an_independent_physical_spectrum(
    shape: tuple[int, int], kernel_sign: int
) -> None:
    """C-10: inverse origin factor and inverse kernel recover the sampled field.

    Input spectra come from the independent direct sum, not C-09's FFT helper;
    an incorrect forward factor therefore cannot cancel an incorrect inverse.
    Both sign pairs work without selecting a time-harmonic convention.
    Measured inverse error / max(abs(data)) <= 7.12e-16 (2026-09-14);
    rtol=1e-12 and a peak-scaled atol allow roundoff at small-amplitude pixels.
    """
    grid = SamplingGrid(ny=shape[0], nx=shape[1], dy=5e-6, dx=3.74e-6)
    rng = np.random.default_rng(20260914)
    data = rng.standard_normal(shape) + 1j * rng.standard_normal(shape)
    physical = _direct_physical_spectrum(data, grid, kernel_sign)
    fx, fy = grid.freq_meshgrid(order="fft")
    origin_phase = np.exp(
        kernel_sign * 2j * np.pi * (fx * grid.x[0] + fy * grid.y[0])
    )
    index_spectrum = physical / (grid.pixel_area * origin_phase)
    actual = (
        np.fft.ifft2(index_spectrum)
        if kernel_sign == -1
        else np.fft.fft2(index_spectrum) / data.size
    )
    scale = float(np.max(np.abs(data)))
    np.testing.assert_allclose(actual, data, rtol=1e-12, atol=1e-12 * scale)


@pytest.mark.parametrize("shape", [(5, 8), (6, 7)])
def test_c11_coordinate_factors_cancel_in_same_grid_asm(
    shape: tuple[int, int]
) -> None:
    """C-11: unchanged ASM equals physical-coordinate analysis/H/synthesis.

    Direct sums independently check the transform pair on the same sampled H;
    this isolates coordinate-factor cancellation, not transfer-function physics
    or sampling adequacy. Existing analytic propagation tests validate H.
    Measured max error / max(abs(reference)) <= 9.50e-16 (2026-09-14).
    rtol=1e-12 plus a peak-scaled atol handles cancellation near zero pixels.
    """
    grid = SamplingGrid(ny=shape[0], nx=shape[1], dy=5e-6, dx=3.74e-6)
    rng = np.random.default_rng(20260914)
    data = rng.standard_normal(shape) + 1j * rng.standard_normal(shape)
    wavelength, distance = 633e-9, 1e-3
    fx, fy = grid.freq_meshgrid(order="fft")
    transfer = np.exp(
        1j * 2 * np.pi
        * np.sqrt(((1 / wavelength) ** 2 - fx**2 - fy**2).astype(np.complex128))
        * distance
    )
    expected = _direct_physical_synthesis(
        _direct_physical_spectrum(data, grid, -1) * transfer, grid, -1
    )
    field = ComplexField(data=data, grid=grid, wavelength_m=wavelength)
    actual = propagate_angular_spectrum(
        field, distance_m=distance, pad_factor=1
    ).data
    scale = float(np.max(np.abs(expected)))
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12 * scale)
