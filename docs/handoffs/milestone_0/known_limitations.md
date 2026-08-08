# Milestone 0 — Known Limitations

Everything on this list is a deliberate, recorded decision or a genuine gap.
None of it is a bug.

---

## 1. Numerical limitations

### 1.1 Verified against NumPy 2.4.6 only

`test_g10` and `test_g11` assert **bit-for-bit** equality between
`SamplingGrid.fx_fft` and `numpy.fft.fftfreq`. That equality holds because our
implementation reproduces `fftfreq`'s *internal evaluation order*
(`val = 1.0/(n*d)` computed once, then multiplied). **This is not a documented
NumPy API guarantee.**

A future NumPy release could change the internal arithmetic without being
wrong, and these two tests would fail.

- **Decision:** NumPy is left unpinned (`numpy>=1.26`), by explicit approval.
- **Rationale:** the failure is loud, immediate, and diagnostic. Pinning would
  hide a real compatibility change.
- **If it happens:** relax `test_g10`/`test_g11` to a tight `rtol` (~`1e-15`)
  and record the change in `math_conventions.md` §3.8.1. Nothing physical
  depends on the last bit; the bit-identity requirement exists as a
  high-sensitivity tripwire, not as a physical necessity.
- Only NumPy 2.x semantics are exercised. The code avoids
  `np.array(copy=False)` (which raises in NumPy 2) and should work on 1.26,
  but that is **untested**.

### 1.2 `intensity` can overflow at extreme amplitudes

`intensity` is computed as `Re(U)² + Im(U)²` rather than `np.abs(U)**2`. This
is deliberate — it makes `test_f07` (`intensity == amplitude**2`) a genuine
cross-check between two independent code paths instead of a tautology.

The cost: no `hypot`-style rescaling, so amplitudes beyond about `1e154`
overflow to `inf`. With `filterwarnings = ["error"]` that would raise rather
than pass silently in tests, but in production code it would produce `inf`.

Far outside any regime this project operates in (normalized fields are O(1)).
Revisit only if a milestone introduces unnormalized physical units.

### 1.3 Float64 precision floor

The core computes in `complex128`/`float64`, giving ~`2.2e-16` relative
precision. Every tolerance in the suite sits ≥10³× above the measured error, so
there is ample headroom — but no operation can be more accurate than this.

### 1.4 Rectangular-rule power integral

`power = Σ I · dx · dy` is a rectangular-rule approximation to
`∫∫ I dx dy`. Exact for band-limited fields sampled above Nyquist,
first-order accurate otherwise. No quadrature refinement is offered.

### 1.5 Nothing is cached

Every derived array (`x`, `fx_fft`, `amplitude`, ...) is recomputed on each
access. This is a deliberate safety choice: a caller mutating a returned array
cannot corrupt grid or field state.

It is also a performance liability inside a loop. `SamplingGrid` properties
allocate a 1-D array per access; `ComplexField.intensity` allocates a full
`(ny,nx)` float64 array per access, and `power` calls `intensity`.

- **Impact today:** none. The suite runs in 0.46 s.
- **Impact in Milestone 3:** Gerchberg–Saxton will call these in a loop over
  hundreds of iterations on megapixel grids.
- **Mitigation when needed:** hoist grid arrays out of loops, or add an
  `lru_cache`d module-level axis factory returning read-only arrays.
  Deliberately deferred until there is a hot path to profile.

### 1.6 Memory

`complex128` is 16 bytes/pixel. A 1024×1024 field is 16 MB, and every operation
allocates a new one. A Gerchberg–Saxton iteration holding several fields plus
zero-padded copies at 4× area will need budgeting in Milestone 3.

---

## 2. Unsupported cases

Rejected with a clear error, or simply absent:

| Case | Status |
|---|---|
| Propagation of any kind (ASM, Fresnel, Fraunhofer) | Absent — Milestone 1 |
| Lenses, apertures, any optical element | Absent |
| Refractive index ≠ 1 | Not a parameter anywhere; fixed at 1 |
| Polarization / vector fields | Out of scope (scalar model) |
| Partial coherence, multiple wavelengths, RGB | Out of scope |
| Multiple depth planes, 3D scenes | Out of scope |
| Tilted or non-parallel planes | Out of scope |
| Different sampling on source and destination planes | Out of scope |
| Non-uniform / non-rectangular grids | Not representable by `SamplingGrid` |
| Complex input to a real parameter | `TypeError` |
| `bool` as a scalar count or pitch | `TypeError` (would silently mean 1) |
| Negative amplitude or intensity | `ValueError` (would be a hidden extra π of phase) |
| `NaN`/`Inf` anywhere | `ValueError` at construction |
| Non-propagating angle pair (`sin²θx + sin²θy > 1`) | `ValueError` |
| Tilt beyond Nyquist on either axis | `ValueError` |
| `λ/(2d) > 1` in `max_diffraction_angle_rad` | `ValueError`, not `NaN` |
| `SamplingGrid.radius` | Deferred to Milestone 1 (lens phases) |
| Serialization of `ComplexField` data | Deferred to Milestone 5 (`io/`) |

---

## 3. Possible failure modes

Ways this code could still mislead:

1. **The conventions could be internally consistent but externally wrong.**
   Every test verifies agreement with `math_conventions.md`; none verifies that
   `math_conventions.md` agrees with Goodman. If the `exp(−iωt)` attribution in
   §3.1 is mistaken, all 188 tests pass and every result is conjugated relative
   to the literature. **This is the single largest unverified assumption in the
   milestone.**

2. **`test_c01` does not pin the absolute spatial origin.** Established by an
   explicit negative control (see `tests_and_evidence.md` §4.4). The origin is
   pinned by `test_g07` instead. Anyone modifying `test_g07` should know it is
   load-bearing.

3. **Square grids hide transposition bugs.** A transposed implementation passes
   most tests on an `n × n` grid. Mitigated by using the `(6, 10)` anisotropic
   fixture throughout — but a *newly added* test that uses `even_grid` or
   `SamplingGrid.square` reintroduces the blind spot. **Any new test touching
   axis order must use `aniso_grid`.**

4. **Round-number pitches hide floating-point association bugs.** NC-1 failed
   only at `d=3.74e-6` and passed at `d=1.0`. Any new numerical test must be
   parametrized over a realistic pitch.

5. **Phase comparisons near the branch cut.** `np.angle` returns `(−π, +π]`, so
   naive subtraction of two phases can report ~`2π` for physically identical
   values. All phase comparisons in the suite go through
   `wrapped_phase_difference`. New tests must do the same, and must mask out
   zero-amplitude pixels where phase is undefined.

6. **Grazing incidence is a floating-point boundary.** `plane_wave` rejects on
   `sin²θx + sin²θy > 1.0` with no tolerance slack. An angle pair that is
   mathematically exactly on the boundary may be accepted or rejected depending
   on the rounding of `math.sin`. `kz = 0` is a degenerate case anyway, but the
   behaviour is not deterministic across libm implementations.

7. **Frequency-ordering mix-ups remain possible in *user* code.** The library
   names the ordering (`fx_fft` vs `fx_centered`) and requires an explicit
   `order=` argument, but nothing prevents a caller from passing a centred grid
   where an FFT-ordered one is expected. This will be the dominant risk in
   Milestone 1.

8. **`np.unwrap` in `test_p03`** can fail near the branch boundary. Mitigated by
   keeping test angles ≤0.45 of Nyquist and by treating `test_p02` (which needs
   no unwrapping) as the primary evidence.

---

## 4. Deferred improvements

| Item | Trigger |
|---|---|
| Cache grid axes (`lru_cache` returning read-only arrays) | A profiled hot path in Milestone 1/3 |
| `SamplingGrid.radius` | Lens phase in Milestone 1 |
| `ComplexField` serialization | Milestone 5 |
| Sampling-adequacy checks / warnings | Milestone 1 |
| `float32` / `complex64` mode for large grids | If memory becomes binding |
| CI on Linux + macOS, multiple NumPy versions | Decision D-3 |
| Property-based testing (Hypothesis) over grid parameters | Optional hardening |
| Benchmarks | Milestone 3 |
| Licence and `authors` metadata | Decisions D-1, D-2 — the repository is **public** with `README.md` currently stating "all rights reserved" |

---

## 5. Risks carried into Milestone 1

Milestone 1 implements the Angular Spectrum Method (`math_conventions.md` §3.9).
Specific risks inherited from here:

### 5.1 DFT implicit periodicity — the biggest one

The DFT treats the field as periodic with period `(Ly, Lx)`. Light diffracting
past the window edge **wraps around** to the opposite edge instead of leaving.
Nothing in Milestone 0 addresses this — `SamplingGrid` has no concept of a
guard band.

Milestone 1 **must** address it (zero-padding, or a band-limited transfer
function à la Matsushima–Shimobaba), not defer it. Wrap-around produces
reconstructions that still look like holograms.

### 5.2 The evanescent branch sign

§3.9 requires `|H| ≤ 1` everywhere for `z > 0`. The wrong branch of the square
root gives exponential **growth**, which will look like a dramatic bug — or
worse, be masked by normalization. Assert `|H| ≤ 1` directly.

### 5.3 Ordering discipline in the hot path

The transfer function must be evaluated on `*_fft` grids so no full-size array
is shifted. Using `*_centered` there produces a field that is fftshifted
relative to the truth — a *plausible-looking* result. Milestone 1's tests must
include a zero-distance identity check, which catches exactly this.

### 5.4 No sampling-adequacy criterion exists yet

ASM has its own sampling condition relating `z`, `λ`, `d`, and `N`. Milestone 0
supplies only the Nyquist limit on transverse frequency. A propagation distance
beyond the ASM validity range will produce quiet nonsense.

### 5.5 Same-sampling assumption

ASM requires source and destination planes to share `(ny, nx, dy, dx)`.
`ComplexField` carries its grid, so this is checkable — but nothing checks it
yet, because nothing yet propagates.

### 5.6 Analytic ground truth will be harder to obtain

Milestone 0 had exact closed forms for everything. Milestone 1 has fewer:
zero-distance identity, round-trip `z` then `−z`, energy conservation for
propagating components, and agreement with a Fresnel analytic case (slit or
circular aperture) within a stated tolerance. **A reconstruction that "looks
right" must not be accepted as evidence** — this is where that temptation first
becomes real.
