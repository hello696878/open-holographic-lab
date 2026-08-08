# Milestone 0 — Tests and Evidence

---

## 1. Exact test command and output

### Command

```
.\.venv\Scripts\python.exe -m pytest -q
```

Run from `C:\holographiclab` with the project installed via
`pip install -e ".[dev]"`.

### Output — exact and unedited

```
........................................................................ [ 38%]
........................................................................ [ 76%]
............................................                             [100%]
188 passed in 0.46s
```

Exit code `0`.

### Environment

| Component | Version |
|---|---|
| OS | Windows 11 Home 10.0.26100 |
| Python | 3.11.9 (tags/v3.11.9:de54cf5, Apr 2 2024) [MSC v.1938 64 bit (AMD64)] |
| NumPy | 2.4.6 |
| SciPy | 1.17.1 |
| pytest | 9.1.1 |
| ohlab | 0.1.0.dev0 (editable) |

pytest is configured with `filterwarnings = ["error"]`, so **any** warning —
including a NumPy `RuntimeWarning` for divide-by-zero, overflow, or
`invalid value encountered` — fails the run. A green suite therefore also
means no numerical warnings were emitted anywhere.

### Test count by module

| Module | Tests | Focus |
|---|---|---|
| `tests/test_packaging.py` | 3 | Toolchain smoke tests (pre-existing) |
| `tests/test_units.py` | 4 | SI multipliers |
| `tests/test_validation.py` | 34 | Argument validation |
| `tests/test_grid.py` | 68 | Geometry, centring, frequency axes, Nyquist |
| `tests/test_field.py` | 44 | Field construction, quantities, invariances |
| `tests/test_fft_conventions.py` | 13 | Grid ↔ `numpy.fft` agreement, static guards |
| `tests/test_plane_wave.py` | 22 | Analytic plane-wave validation |
| **Total** | **188** | |

---

## 2. What the important tests support

### The decisive convention tests

| Test | What it establishes | Evidence class |
|---|---|---|
| `test_c01_on_grid_plane_wave_lands_in_the_predicted_bin` | The spatial grid, the frequency grid, and NumPy's FFT kernel agree on centring, ordering, and sign. The destination bin is computed in closed form *before* the FFT, across all four `(±fx₀, ±fy₀)` quadrants on an anisotropic grid. The peak's complex value additionally pins `meshgrid`↔axis consistency and the `Ny·Nx` DC scale factor. | Analytic ground truth |
| `test_g10_fft_ordered_axis_matches_numpy_bit_for_bit` | `fx_fft` equals `np.fft.fftfreq(nx, dx)` **bit for bit**, at both parities and at a realistic pitch. The axis is built independently from the documented formula, so this is a real comparison rather than a tautology. | NumPy reference |
| `test_c02_parseval_holds_in_the_backward_norm_form` | Energy is conserved under the DFT in the exact form that holds for `norm="backward"`. A symmetric-norm mistake would be off by `Ny·Nx`. | Conservation law |
| `test_c04_shift_theorem_sign` | The forward kernel is `−i`, not `+i`. Expressed in physical frequencies from `freq_meshgrid`, so it also exercises the FFT-ordered grids. | Analytic ground truth |
| `test_p02_neighbour_ratio_phase_equals_kx_dx_and_ky_dy` | `arg(U[j+1]·conj(U[j])) = kx·dx` pointwise. Validates the coordinate grid, the wavenumber, and the phase convention together, with no unwrapping and no fitting. | Analytic ground truth |
| `test_g07_origin_sits_exactly_on_index_n_over_2` | `x[n//2] == 0.0` exactly, both parities. This is what actually pins the absolute origin convention. | Exact identity |
| `test_g17_meshgrid_orientation` | The anti-transposition test. Only meaningful because `ny ≠ nx`. | Exact identity |
| `test_f10_phase_only_multiplication_preserves_intensity_and_power` | A phase-only element conserves intensity and power exactly — the property that makes a phase-only SLM useful. | Symmetry / conservation |
| `test_f22_random_phase_is_reproducible_from_its_seed` | Bit-for-bit reproducibility from a seed, as §3.10 requires. | Bit-for-bit reproducibility |
| `test_c06` / `test_c07` | AST scan proving no module in `src/ohlab/` imports a plotting/image library or touches the legacy global RNG. Static, so it cannot be fooled by an untaken code path. | Static analysis |
| `test_p06` / `test_p07` | The joint propagating condition `sin²θx + sin²θy ≤ 1` is enforced *and* is not over-enforced. | Analytic ground truth |

### Evidence class by behaviour

| Behaviour | Evidence |
|---|---|
| Grid centring | Exact identity (IEEE-754) |
| Frequency axes | NumPy reference, bit-for-bit |
| FFT ordering | Round-trip identity |
| Nyquist limit, diffraction angle | Analytic ground truth + independent hand calculation (4.855° at 633 nm / 3.74 µm) |
| meshgrid orientation | Exact identity on a deliberately non-square grid |
| Parseval | Conservation law |
| Phase-only invariance | Symmetry / conservation |
| Plane-wave structure | Analytic ground truth (two independent methods) |
| FFT bin placement | Analytic ground truth, four sign quadrants |
| amplitude / phase / intensity | Exact algebraic identity, cross-checked between two code paths |
| Power normalisation | Round-trip identity |
| Conjugation | Symmetry |
| Determinism | Bit-for-bit reproducibility |
| Immutability | Behavioural |
| Validation | Behavioural (`pytest.raises` + message-content assertions) |
| Dependency isolation | Static analysis (AST) |

**No test uses visual plausibility.** The seven figures are generated *from*
verified code for the tutoring session and are never an input to a pass/fail
decision; `scripts/` is outside `testpaths` and is never collected.

---

## 3. Numerical tolerances

Every numerical comparison passes explicit `rtol`/`atol`. Tolerances were set
from **measured** error magnitudes, not guessed.

| Test | Tolerance | Measured error | Margin | Justification |
|---|---|---|---|---|
| `test_g10`, `test_g11`, `test_g12` | **exact** | — | — | Bit-identity with `numpy.fft.fftfreq` is the property under test |
| `test_g07` | **exact** | — | — | `(n//2 − n//2)·d ≡ 0.0` in IEEE-754 |
| `test_g17`, `test_c05`, `test_f19`, `test_f22` | **exact** | — | — | Value copying / permutation / defensive copy — exactness is the claim |
| `test_c01` peak index | **exact** | — | — | Integer index |
| `test_c01` off-peak | `≤ 1e-10 × peak` | `0.0` | ∞ | A convention error relocates O(1) energy |
| `test_c01` peak value | `rtol=1e-10` | `6e-16` | ~1.7e5 | Closed-form DFT sum |
| `test_c02` Parseval | `rtol=1e-12` | `2.4e-16` | ~4000× | Normalization errors are O(`Ny·Nx`) |
| `test_c04` shift theorem | `rtol=1e-10`, `atol=1e-10×peak` | — | — | Individual bins can be near zero for random data, so relative-only would be meaningless |
| `test_g06` axis spacing | `rtol=1e-12` | — | ~1e4 × eps | `np.diff` of large coordinates loses ~1 ULP |
| `test_g14` `k = 2πf` | `rtol=1e-15` | — | ~4 × eps | One multiplication; a cyclic/angular confusion is a factor of 2π |
| `test_g22` diffraction angle | `abs=0.01°` | — | — | Set by the precision of the hand calculation, not by float64 |
| `test_f05` amplitude | `rtol=1e-12` | `2.9e-16` | ~4000× | |
| `test_f05` phase | `atol=1e-12` rad | `2.2e-16` | ~4500× | On the **wrapped** difference |
| `test_f07` intensity | `rtol=1e-12` | `7.5e-16` | ~1300× | Two independent code paths |
| `test_f10` invariance | `rtol=1e-12` | `1.0e-15` intensity, `0.0` power | ~1000× | |
| `test_f15` conjugate amplitude | `rtol=1e-15` | — | — | `hypot` is sign-symmetric |
| `test_p02` neighbour ratio | `atol=1e-10` rad | — | ~2500× | `\|kx·x\| ≈ 16 rad`, so its own rounding is ~`3.5e-15`; the product roughly doubles that |
| `test_p03` phase gradient | `rtol=1e-10`, `atol=1e-10·k` | `4.4e-16` | ~1e6 | `atol` handles the zero-tilt case where relative tolerance is meaningless |

**Policy.** Exact comparison is used only where exactness is the property under
test, and every such call site carries a comment saying so. Float tolerances
are ≥10³× the measured error — loose enough to absorb libm and FFT-backend
variation across platforms, and far tighter than any genuine defect, which
produces O(1) rather than O(10⁻¹²) discrepancies.

---

## 4. Independent and analytic validation

### 4.1 Analytic ground truth

| Quantity | Closed form | Verified in |
|---|---|---|
| FFT bin of an on-grid plane wave | `fftshift(fft2(U))[l₀,m₀] = Ny·Nx·exp(2πi(fx₀x[0] + fy₀y[0]))` | `test_c01`, `test_p05` |
| Neighbour ratio | `arg(U[j+1]conj(U[j])) = kx·dx` | `test_p02`, `test_p07` |
| Phase gradient | `dφ/dx = kx = k·sin θx` | `test_p03` |
| Shift theorem | `exp(−2πi(fx·Δx + fy·Δy))` | `test_c04` |
| Max diffraction angle | `sin θ = λ/(2d)` | `test_g21` |
| Parseval | `Σ\|u\|² = Σ\|û\|²/(NyNx)` | `test_c02` |
| Wavelength scaling | `kx ∝ 1/λ` at fixed tilt | `test_p11` |

### 4.2 Independent hand calculation

`λ = 633 nm`, `d = 3.74 µm`:
`sin θ = 633e-9 / 7.48e-6 = 0.084626` → `θ = 4.855°`. Computed by hand,
outside the implementation, and asserted in `test_g22` to `±0.01°`.

### 4.3 Negative controls

**A green suite is not evidence that the tests can fail.** Three deliberate
mutations were injected into the implementation and confirmed to be caught.

| # | Mutation | Result | Notes |
|---|---|---|---|
| NC-1 | Frequency axis computed as `(m − n//2)/(n·d)` (division) instead of reciprocal-multiply | **2 failed**, 10 passed | Failed `test_g10` and `test_g11` **only at `d=3.74e-06`**, passing at `d=1`. This is direct evidence that parametrizing over a realistic pitch was necessary; a round-number-only test suite would not have caught it. Reported mismatch: `-100267.37967914437` vs `-100267.37967914439`. |
| NC-2 | Spatial `x` origin shifted by one pixel (`+1` in the index offset) | **8 failed**, 180 passed | Failed `test_g07` (both parities, both pitches), `test_g08`, `test_g09`. |
| NC-3 | FFT shift-theorem exponent sign flipped (`+i` instead of `−i`) | detected | Verified out-of-band; the correct sign passes and the flipped sign fails the `test_c04` assertion. |

Two further probes checked that specific tests are *not* vacuous:

| Probe | Finding |
|---|---|
| Phase-only invariance with a `1e-9` gain added | Detected. The `rtol=1e-12` bound is tight enough to catch a part-per-billion amplitude error. |
| Neighbour ratio with `k` wrong by 1 part per million | Detected at `atol=1e-10` rad. |
| Transposed array on a **square** grid | **Accepted** — as expected, and precisely why every field test uses the anisotropic `(6, 10)` fixture. On the anisotropic grid the same input is rejected. |

### 4.4 A gap found and closed, and a claim corrected

NC-2 initially revealed that `test_c01` did **not** detect a one-pixel shift of
the spatial grid: such a shift multiplies the field by a *global constant*
phase, which leaves `|FFT|` and the peak bin completely unchanged.

The test was strengthened to assert the peak's **complex value** against the
closed form in §6.5 of `math_used.md`. Re-running the mutation then showed
something important: `test_c01` still passed, because the prediction is built
from `grid.x[0]`, which the mutation also shifts.

**The honest conclusion, now recorded in the test's own docstring:**
`test_c01`'s complex assertion verifies that `meshgrid()` and the 1-D axes are
consistent, and pins the `Ny·Nx` DC scale factor. It does **not** pin the
absolute origin convention. That is pinned separately, and exactly, by
`test_g07`. The suite as a whole catches the mutation (8 failures); a single
test does not do everything.

---

## 5. What this test suite does NOT prove

Stated explicitly, because a green suite invites over-reading.

1. **That the conventions match Goodman, or any other textbook.** These are
   internal-consistency tests. The citation in `math_conventions.md` §3.1 is an
   unverified external claim and is **the largest unverified assumption in
   Milestone 0.** Verifying it requires reading a source you trust.

2. **Anything physical.** No test involves propagation, diffraction, or
   Maxwell's equations. Milestone 0 is bookkeeping and cannot be physically
   correct or incorrect. A perfectly green Milestone 0 is entirely consistent
   with Milestone 1 producing physical nonsense.

3. **That a given sampling is adequate.** `SamplingGrid` will build a grid far
   too coarse for a given problem and report nothing. Adequacy criteria arrive
   in Milestone 1.

4. **Correctness on any NumPy other than 2.4.6.** The bit-identity tests
   (`test_g10`, `test_g11`) depend on `numpy.fft.fftfreq`'s *internal
   evaluation order*, which is not a documented API guarantee. NumPy is
   deliberately left unpinned so that a change surfaces loudly rather than
   silently.

5. **Correctness on other platforms.** Verified on Windows 11 / CPython 3.11.9
   / MSVC build only. `libm` differences could in principle move results, though
   all tolerances carry ≥10³× margin.

6. **Behaviour at numerical extremes.** Not tested: very large `N`
   (memory/precision), sub-nanometre pitch, amplitudes near underflow or
   beyond `1e154` (where `intensity`'s `Re²+Im²` overflows), or fields with
   content exactly at Nyquist.

7. **That the API is well designed.** Tests cannot report that an interface is
   awkward. Only Milestone 3, where Gerchberg–Saxton actually uses
   `with_amplitude`/`with_phase` in a loop, will show that.

8. **Performance.** Nothing is cached and nothing is benchmarked. The suite
   runs in 0.46 s on grids of at most 48×64.

9. **That the figures are correct.** They are illustrations generated from the
   verified API. They are documentation, not evidence.
