# Milestone 0 — Code Map

A guide to reading the implementation. Written for someone who will read the
source, not a tutorial on the physics (see `math_used.md` and
`tutor_context.md` for that).

---

## Recommended reading order

Read in this order; each file depends only on the ones above it.

| # | File | Why here | Approx. time |
|---|---|---|---|
| 1 | `docs/math_conventions.md` §2, §3.2–§3.8 | **Read first.** Normative. The code is an implementation of this document, and every design choice below traces back to a numbered section. | 25 min |
| 2 | `src/ohlab/units.py` | Trivial, 40 lines. Establishes the SI-only rule. | 2 min |
| 3 | `src/ohlab/validation.py` | No project concepts, only argument checking. Read the module docstring for the `TypeError` vs `ValueError` policy and the deliberate bool asymmetry. | 15 min |
| 4 | `src/ohlab/grid.py` | The core geometric object. Read the module docstring first — it explains the reciprocal-multiply requirement, which is the subtlest thing in the milestone. | 30 min |
| 5 | `src/ohlab/field.py` | Builds on the grid. Read `__post_init__`, then the three physical properties, then the constructors, then the derived-field operations. | 35 min |
| 6 | `tests/test_fft_conventions.py` | The most valuable test module. `test_c01_*` is the single decisive convention test. | 25 min |
| 7 | `tests/test_plane_wave.py` | Analytic validation. The neighbour-ratio identity is the cleanest piece of physics in the milestone. | 20 min |
| 8 | `tests/test_grid.py`, `tests/test_field.py` | Exhaustive but repetitive; skim, then read the tests whose docstrings say "EXACTNESS IS THE PROPERTY UNDER TEST". | 30 min |
| 9 | `scripts/make_m0_figures.py` | Optional. Shows the API in use. | 10 min |

---

## Module responsibilities

### `src/ohlab/units.py`
SI multipliers so call sites read physically (`633 * NM`). Contains **no
logic**. Deliberately has no conversion functions: a `to_micrometres()` helper
would invite a non-SI quantity to be stored or passed onward, which
`math_conventions.md` §2 forbids.

### `src/ohlab/validation.py`
Every public entry point in the package routes its arguments through here
before any numerical work.

Two policies worth knowing:

- **`TypeError` = wrong kind, `ValueError` = unusable value.** A string where a
  number is required is a `TypeError`; a negative pixel pitch is a `ValueError`.
- **`bool` is rejected by scalar validators but accepted by array validators.**
  For a scalar count, `SamplingGrid(nx=True)` silently meaning `nx=1` is a
  semantic mistake. For an array, a boolean mask is a legitimate binary
  aperture. The asymmetry is intentional and documented.

`as_float64_array` / `as_complex128_array` always return a **fresh copy**
(`astype(..., copy=True)`). That is what gives `ComplexField` its
defensive-copy guarantee without a separate copy step.

### `src/ohlab/grid.py`
`SamplingGrid` stores exactly four numbers and derives everything else. Nothing
is cached.

The single subtle point is `_centered_frequency_axis`, which evaluates
`(m − n//2) * (1.0/(n*d))` rather than `(m − n//2)/(n*d)`. See the module
docstring and `math_conventions.md` §3.8.1.

### `src/ohlab/field.py`
`ComplexField` holds `data` (complex128, read-only), a `grid`, and a
`wavelength_m`. The wavelength lives on the field because a monochromatic field
*has* a wavelength, which lets every future two-field operation assert
agreement for free.

`with_amplitude` and `with_phase` are named as they are because they are
exactly the two Gerchberg–Saxton projection steps; Milestone 3 will read like
the algorithm.

### `scripts/make_m0_figures.py`
Outside the numerical core. The only file importing matplotlib. Enforced by
`test_c06_numerical_core_imports_no_ui_or_io_library` (AST scan) and by the
runtime dependency set in `pyproject.toml`.

---

## Public API

### `ohlab.units`

```
NM, UM, MM, CM, DEG : float
```

### `ohlab.validation`

```
require_positive_int(value, name)            -> int
require_finite_float(value, name)            -> float
require_positive_finite_float(value, name)   -> float
as_float64_array(value, name)                -> np.ndarray   (fresh copy)
as_complex128_array(value, name)             -> np.ndarray   (fresh copy)
require_ndim(a, ndim, name)                  -> np.ndarray
require_shape(a, expected, name)             -> np.ndarray
require_all_finite(a, name)                  -> np.ndarray
```

### `ohlab.SamplingGrid`

Frozen, keyword-only, hashable, value-equality.

| Member | Kind | Returns | Units |
|---|---|---|---|
| `ny, nx` | field | `int` | — |
| `dy, dx` | field | `float` | m |
| `shape` | property | `(ny, nx)` | — |
| `extent_y`, `extent_x` | property | `float` | m |
| `pixel_area` | property | `float` | m² |
| `y`, `x` | property | `(n,)` float64 | m |
| `meshgrid()` | method | `(x_grid, y_grid)`, each `(ny,nx)` | m |
| `fy_centered`, `fx_centered` | property | `(n,)` float64 | cycles/m |
| `fy_fft`, `fx_fft` | property | `(n,)` float64 | cycles/m |
| `ky_centered`, `kx_centered` | property | `(n,)` float64 | rad/m |
| `ky_fft`, `kx_fft` | property | `(n,)` float64 | rad/m |
| `freq_meshgrid(*, order)` | method | `(fx_grid, fy_grid)` | cycles/m |
| `nyquist_fy`, `nyquist_fx` | property | `float` | cycles/m |
| `max_diffraction_angle_rad(λ, *, axis)` | method | `float` | rad |
| `to_dict()` / `from_dict(d)` | method / classmethod | JSON-safe dict / grid | — |
| `square(*, n, pitch)` | classmethod | grid | — |

### `ohlab.ComplexField`

Frozen, keyword-only, **identity equality** (`eq=False`).

| Member | Kind | Returns | Units |
|---|---|---|---|
| `data` | field | `(ny,nx)` complex128, read-only | a.u. |
| `grid` | field | `SamplingGrid` | — |
| `wavelength_m` | field | `float` | m |
| `shape` | property | `(ny, nx)` | — |
| `amplitude` | property | `(ny,nx)` float64 ≥ 0 | a.u. |
| `phase` | property | `(ny,nx)` float64 ∈ (−π, π] | rad |
| `intensity` | property | `(ny,nx)` float64 ≥ 0 | a.u. |
| `power` | property | `float` | a.u.·m² |
| `wavenumber` | property | `float` | rad/m |
| `from_amplitude_phase(*, amplitude, phase, grid, wavelength_m)` | classmethod | field | — |
| `from_intensity_phase(*, intensity, phase, grid, wavelength_m)` | classmethod | field | — |
| `uniform(*, grid, wavelength_m, amplitude=1.0)` | classmethod | field | — |
| `plane_wave(*, grid, wavelength_m, theta_x_rad, theta_y_rad, amplitude)` | classmethod | field | — |
| `random_phase(*, grid, wavelength_m, seed, amplitude=1.0)` | classmethod | field | — |
| `with_data(data)` | method | new field | — |
| `with_amplitude(amplitude)` | method | new field | — |
| `with_phase(phase)` | method | new field | — |
| `scaled(factor)` | method | new field | — |
| `normalized_power(target=1.0)` | method | new field | — |
| `conjugate()` | method | new field | — |
| `allclose(other, *, rtol, atol)` | method | `bool` | — |

---

## Data flow

```
    user code
       |
       |  SamplingGrid(ny=, nx=, dy=, dx=)          [keyword-only]
       v
  +---------------------------------------------+
  |  SamplingGrid.__post_init__                  |
  |    require_positive_int   x2                 |----> validation.py
  |    require_positive_finite_float x2          |
  +---------------------------------------------+
       |
       |  four validated scalars, frozen
       v
  +---------------------------------------------+
  |  derived, recomputed on every access:        |
  |    x, y            = (i - n//2) * d          |
  |    f*_centered     = (m - n//2) * (1/(n*d))  |
  |    f*_fft          = ifftshift(f*_centered)  |----> numpy.fft (permutation only)
  |    k*              = 2*pi * f*               |
  |    nyquist_f*      = 1/(2*d)                 |
  +---------------------------------------------+
       |
       |  grid passed by reference into a field
       v
  +---------------------------------------------+
  |  ComplexField.__post_init__                  |
  |    isinstance(grid, SamplingGrid)            |
  |    require_positive_finite_float(wavelength) |----> validation.py
  |    as_complex128_array   -> FRESH COPY       |
  |    require_ndim / require_shape(grid.shape)  |
  |    require_all_finite                        |
  |    data.flags.writeable = False              |
  +---------------------------------------------+
       |
       +--> amplitude   = np.abs(data)                    float64, fresh
       +--> phase       = np.angle(data)                  float64, fresh, (-pi, pi]
       +--> intensity   = data.real**2 + data.imag**2     float64, fresh
       +--> power       = sum(intensity) * grid.pixel_area
       |
       +--> with_amplitude / with_phase / scaled / conjugate / normalized_power
                |
                +--> with_data(...) --> new ComplexField (full re-validation)
```

Two properties of this flow are worth noting:

1. **Every derived field re-enters `__post_init__` through `with_data`.** There
   is no path that produces a `ComplexField` bypassing validation, so an
   operation cannot introduce a NaN and have it survive silently.
2. **The grid is shared by reference, never copied.** It is immutable and
   hashable, so sharing is safe, and `allclose` can compare grids with `==`.

---

## Important call relationships

| Caller | Callee | Why it matters |
|---|---|---|
| `SamplingGrid.fx_fft` | `SamplingGrid.fx_centered` → `np.fft.ifftshift` | FFT order is *derived* from centred order, so the two can never disagree. `test_g12` asserts the round trip is exact. |
| `ComplexField.__post_init__` | `validation.as_complex128_array` | The `astype(copy=True)` inside is the defensive copy. Removing it would silently break immutability. |
| `ComplexField.with_amplitude` | `self.phase` → `np.angle` | Recomputes the phase, hence tests compare with tolerance, not bit-identity. |
| `ComplexField.normalized_power` | `self.power` → `self.intensity` → `grid.pixel_area` | Power depends on the grid, so normalisation is grid-dependent. Two fields with identical `data` on different grids have different powers. |
| `ComplexField.plane_wave` | `grid.meshgrid()`, `grid.nyquist_fx/fy` | Both the physical (propagating) and sampling (Nyquist) checks live here; nothing downstream re-checks them. |
| `tests/test_fft_conventions.py` | `ohlab.__file__` → AST scan | The architectural guard operates on the *installed* package, so it cannot be fooled by a stale source tree. |

---

## Where the conventions are pinned

If you need to know which test enforces a given convention:

| Convention | `math_conventions.md` | Test |
|---|---|---|
| `(ny, nx)` shape | §3.3 | `test_g01`, `test_f02` |
| Keyword-only construction | §3.3 | `test_g03`, `test_f04b` |
| `x[n//2] == 0` exactly | §3.4 | `test_g07` |
| Even-`n` asymmetric span | §3.4 | `test_g08` |
| `meshgrid` orientation | §3.4 | `test_g17` |
| `+y` downward | §3.5 | documented; visualised in `fig04` |
| FFT sign convention | §3.6 | `test_c04` |
| cyclic vs angular | §3.6 | `test_g14` |
| Parseval / `norm="backward"` | §3.7 | `test_c02` |
| `fftfreq` bit-identity | §3.8, §3.8.1 | `test_g10`, `test_g11` |
| Ordering round trip | §3.8 | `test_g12`, `test_c05` |
| Nyquist | §3.8 | `test_g15`, `test_g16`, `test_p08` |
| Phase branch `(−π, π]` | §3.2 | `test_f06` |
| `I = \|U\|²` | §2.1 | `test_f07` |
| `P = ΣI·dx·dy` | §2.1 | `test_f09` |
| Deterministic RNG | §3.10 | `test_f22`, `test_c07` |
| `complex128` / `float64` | §3.11 | `test_f01`, `test_f07` |
