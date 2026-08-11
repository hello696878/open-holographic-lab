# Milestone 1 — Code Map

Milestone 1 adds exactly one module to the numerical core. Everything else in
`src/ohlab/` is unchanged from Milestone 0.

---

## Recommended reading order

| # | File | Why here | Time |
|---|---|---|---|
| 1 | `docs/math_conventions.md` §3.9 (all five subsections) | **Read first.** Normative. `propagation.py` is a direct implementation of it | 20 min |
| 2 | `docs/handoffs/milestone_1/math_used.md` | Every equation, with the measured numbers beside it | 25 min |
| 3 | `src/ohlab/propagation.py` — module docstring | Explains the single-expression rule and the corner-vs-axis evanescent correction before any code | 10 min |
| 4 | `src/ohlab/propagation.py` — `angular_spectrum_transfer_function` | Four lines of arithmetic; all the subtlety is in the branch and the docstring | 15 min |
| 5 | `src/ohlab/propagation.py` — `_pad_offset`, `_zero_pad`, `_crop` | The alignment rule that keeps the M0 origin convention intact | 15 min |
| 6 | `src/ohlab/propagation.py` — `propagate_angular_spectrum` | Assembles the above; note the zero-distance early return | 10 min |
| 7 | `tests/test_propagation_analytic.py` | The evidence. `test_a02` is the decisive test | 30 min |
| 8 | `tests/test_propagation.py` | Mechanics, policy, padding. Skim, then read the docstrings marked "EXACTNESS IS THE PROPERTY UNDER TEST" | 25 min |
| 9 | `scripts/make_m1_figures.py` | Optional. The API in use | 10 min |

---

## Module responsibility

### `src/ohlab/propagation.py`

The only new module. Imports `numpy`, `math`, and three names from
`ohlab.validation`, plus `ComplexField` and `SamplingGrid`. It imports no
plotting, image, or I/O library — enforced by the AST scan in
`tests/test_fft_conventions.py::test_c06`.

**Public**

```python
angular_spectrum_transfer_function(grid, *, wavelength_m, distance_m) -> np.ndarray
propagate_angular_spectrum(field, *, distance_m, pad_factor=2) -> ComplexField
```

**Private**

```python
_evanescent_mask(grid, wavelength_m) -> np.ndarray   # bool, (ny, nx)
_padded_grid(grid, pad_factor)       -> SamplingGrid
_pad_offset(n, n_padded)             -> int
_zero_pad(data, grid, padded)        -> np.ndarray
_crop(data, grid, padded)            -> np.ndarray
_reject_backward_evanescent(grid, wavelength_m, distance_m) -> None
```

The private helpers are imported directly by `tests/test_propagation.py`.
That is deliberate: the padding alignment rule is the kind of thing that must
be tested at the unit level, not only through its effect on a propagated field.

---

## Data flow

```
  propagate_angular_spectrum(field, distance_m=z, pad_factor=p)
      |
      |-- isinstance(field, ComplexField)            -> TypeError
      |-- require_finite_float(distance_m)           -> ValueError
      |-- require_positive_int(pad_factor)           -> ValueError / TypeError
      |
      |-- if distance == 0.0:  return field          <-- SAME OBJECT, exact identity
      |
      |-- padded = _padded_grid(grid, p)             pitch unchanged, size x p
      |
      |-- _reject_backward_evanescent(padded, lambda, z)
      |        evaluated on the PADDED grid: padding samples the frequency
      |        plane more finely, so it can expose evanescent samples the
      |        unpadded mesh misses
      |
      |-- source = _zero_pad(field.data, grid, padded)
      |        pad_before = N_pad//2 - N//2  ->  origin index preserved
      |
      |-- transfer = angular_spectrum_transfer_function(padded, ...)
      |        |
      |        |-- fx, fy = padded.freq_meshgrid(order="fft")
      |        |-- radial = 1/lambda^2 - fx^2 - fy^2          float64
      |        |-- kz = 2*pi*sqrt(radial.astype(complex128))  Im(kz) >= 0
      |        +-- H  = exp(1j * kz * distance)               ONE expression
      |
      |-- propagated = ifft2( fft2(source) * transfer )
      |
      |-- cropped = _crop(propagated, grid, padded)   exact inverse of the pad
      |
      +-- return field.with_data(cropped)             full ComplexField validation
```

Two properties worth noting:

1. **The result re-enters `ComplexField.__post_init__` via `with_data`.** There
   is no path that produces a propagated field bypassing shape, dtype and
   finiteness validation, so a NaN introduced by propagation cannot survive
   silently.
2. **The grid object is shared, not rebuilt.** `with_data` reuses
   `field.grid`, so the output is guaranteed to compare equal on grid and
   wavelength — which is what lets `allclose` refuse mismatched operands.

---

## Important call relationships

| Caller | Callee | Why it matters |
|---|---|---|
| `angular_spectrum_transfer_function` | `np.sqrt` on a **complex** array | This single cast is the entire branch selection. Removing `.astype(np.complex128)` would produce `NaN` for evanescent samples instead of decay |
| `propagate_angular_spectrum` | `_reject_backward_evanescent(padded, ...)` | Deliberately the **padded** grid, not the source grid |
| `propagate_angular_spectrum` | `field.with_data(...)` | Re-validates; also fixes grid and wavelength on the output |
| `_zero_pad` / `_crop` | `_pad_offset` | Both use the same offset, which is what makes cropping an exact inverse |
| `_padded_grid` | `SamplingGrid(...)` | Constructs with the **same pitch**, so the Nyquist limit is unchanged and only the frequency spacing refines |
| `tests/test_propagation.py` | `_pad_offset`, `_zero_pad`, `_crop` | Unit-level testing of alignment, at every parity |

---

## What changed elsewhere

| File | Change |
|---|---|
| `src/ohlab/__init__.py` | Re-exports the two public functions; `__version__` still a plain literal for setuptools |
| `tests/test_fft_conventions.py` | `test_c08` only — the exact-set assertion on `ohlab.__all__` now lists the M0 and M1 API sets |

Nothing else in `src/ohlab/` or `tests/` was touched.

---

## Where the Milestone 1 conventions are pinned

| Convention | `math_conventions.md` | Test |
|---|---|---|
| Single expression `H = exp(+i·kz·z)` | §3.9.1 | `test_m04`, `test_m05` |
| Branch `Im{kz} ≥ 0` | §3.9.1 | `test_m11` (decay), NC-5 |
| `\|H\| = 1` to machine precision | §3.9.1 | `test_m03` |
| Mesh-based evanescence, corner condition | §3.9.2 | `test_m08`, `test_m10` |
| Evanescent policy | §3.9.3 | `test_m11`, `test_m12`, `test_m13`, `test_m14` |
| Zero-distance identity contract | API docstring | `test_m15`, `test_m16`, `test_a01` |
| Padding alignment | §3.9.4 | `test_m17`, `test_m18`, `test_m19`, NC-10 |
| Periodic vs zero-embedded boundary | §3.9.4 | `test_m26`, `test_m27`, `test_m30` |
| Propagation sign | §3.1, §3.9.1 | `test_a02`, `test_a05`, `test_a06`, NC-1 |
| Per-component `kz` | §3.9.1 | `test_a04` |
| FFT ordering in the hot path | §3.8, §3.9.1 | `test_m01`, NC-3 |
