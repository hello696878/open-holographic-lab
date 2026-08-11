# Milestone 1 — Known Limitations

Every item here is a deliberate, recorded decision or a genuine gap. None is a
bug.

---

## 1. Numerical limitations

### 1.1 The transfer function can be undersampled, and nothing detects it

`H = exp(i·kz·z)` has phase fringes in the frequency plane whose local
frequency grows with `z`. Beyond a certain distance those fringes exceed one
cycle per frequency sample and `H` itself aliases. **No check for this is
implemented**, and the propagator will happily return a plausible-looking wrong
answer.

The classical criterion (Matsushima & Shimobaba) gives a limiting frequency

    u_limit = 1 / ( λ·√( (2·z/Lx)² + 1 ) )

where `Lx = nx·dx`. Sampling is adequate when `u_limit ≥ f_nyquist`. Measured:

| `n` | pitch | `z` | `u_limit / f_nyq` |
|---|---|---|---|
| 512 | 3.74 µm | 10 mm | 1.13 — ok |
| 512 | 3.74 µm | 100 mm | 0.11 — undersampled |
| 1024 | 3.74 µm | 100 mm | 0.23 — undersampled |
| 1024 | 8.0 µm | 100 mm | 1.03 — ok |
| 2048 | 8.0 µm | 500 mm | 0.41 — undersampled |

**Why no warning was shipped.** The criterion is a worst-case bound over the
whole band, and it proved to be a *poor predictor of actual error*. A probe at
`u_limit/f_nyq = 0.226` — nominally badly undersampled — agreed with the
analytic Gaussian to `4.3e-05`, because a smooth compact source simply has no
energy at the frequencies that alias. Emitting a warning on that basis would
train the user to ignore warnings, and would interact badly with
`filterwarnings = ["error"]`.

Deferred rather than guessed. See §2.

### 1.2 Band-limited ASM is not implemented

Approval C originally proposed a `band_limit` option. It was **deferred on
measured evidence**.

Judged against the analytic Gaussian (256², 3.74 µm, `w₀ = 40 µm`):

| `z` | plain | 2× padded | band-limited | BL + 2× padded |
|---|---|---|---|---|
| 5 mm | `9.1e-13` | `6.2e-13` | `9.1e-13` | `6.2e-13` |
| 20 mm | `3.4e-09` | `3.7e-12` | `3.4e-09` | `3.7e-12` |
| 100 mm | `4.98e-01` | `3.05e-04` | `3.51e-01` | `7.90e-03` |

And against a 4×-padded reference for a hard-edged circular aperture:

| `z` | plain | 2× padded | band-limited |
|---|---|---|---|
| 5 mm | `3.79e-04` | `6.12e-05` | `3.79e-04` |
| 20 mm | `3.14e-03` | `3.50e-04` | `3.14e-03` |
| 100 mm | `5.27e-02` | `8.08e-04` | `3.22e-02` |

Two conclusions:

1. **Zero-padding dominates band-limiting in every case measured.**
2. **Band-limiting can make results worse.** At `z = 100 mm`, `BL + padding`
   (`7.9e-3`) is 26× worse than padding alone (`3.0e-4`), because `u_limit`
   scales with window size and the mask cuts genuine diffracted content that
   the padding existed to preserve.

**Status: candidate M1.x enhancement.** It addresses a real failure mode
(§1.1) that padding does not touch, and it should be revisited if a concrete
validation case emerges where transfer-function aliasing demonstrably
dominates and padding cannot fix it. Reference: Matsushima & Shimobaba,
*Band-Limited Angular Spectrum Method for Numerical Simulation of Free-Space
Propagation in Far and Near Fields*, Opt. Express **17**(22), 19662 (2009),
DOI `10.1364/OE.17.019662`. The probe evidence above is preserved in this
document deliberately, so that the decision can be re-examined rather than
re-derived.

### 1.3 Padding is a boundary condition, not a correctness guarantee

`pad_factor=1` solves the periodic problem; `pad_factor>1` solves a
zero-embedded one. Neither is universally right.

- Once light reaches the edge of the **padded** window it wraps again.
- Embedding a field that *fills* its window imposes a hard aperture the
  periodic problem did not have — which is exactly why every exact analytic
  test uses `pad_factor=1`.
- The default `pad_factor=2` is a judgement call, not a derived value.

### 1.4 Accumulated phase limits long-distance accuracy

Comparing two `exp(i·kz·z)` values is limited by the rounding of the angle:
`k·z` reaches `9.9e5` rad at `z = 100 mm`, so absolute agreement cannot beat
`k·z·ε ≈ 2.2e-10`. This is a hard float64 limit, not an implementation defect.
It scales linearly with distance and inversely with wavelength.

### 1.5 Hard-edged fields are untested

Nothing in the suite propagates a discontinuous field. A sharp aperture has
unbounded bandwidth, so it aliases regardless of the transfer function, and the
resulting error is neither measured nor bounded here. Milestone 2 will
introduce exactly such fields when it loads target images.

### 1.6 Performance and memory

Measured, complete propagation path (`fft2`, `H`, multiply, `ifft2`, crop):

| `N` | `pad_factor` | one field array | **measured peak working set** | ratio | ms/call |
|---|---|---|---|---|---|
| 128 | 1 | 0.25 MB | 1.13 MB | 4.5× | 2.3 |
| 128 | 2 | 0.25 MB | 5.50 MB | 22× | 12.5 |
| 256 | 1 | 1.00 MB | 4.50 MB | 4.5× | 13.5 |
| 256 | 2 | 1.00 MB | 22.00 MB | 22× | 53.8 |
| 512 | 1 | 4.00 MB | 18.00 MB | 4.5× | 59.7 |
| 512 | 2 | 4.00 MB | 88.00 MB | 22× | 258.3 |
| 1024 | 1 | 16.00 MB | 72.00 MB | 4.5× | 237.2 |
| **1024** | **2** | **16.00 MB** | **352.00 MB** | **22×** | **1874.9** |

The peak is **not** one padded array: the path holds the padded field, its
spectrum, the transfer function, the product, and the inverse-FFT output
simultaneously, plus NumPy's internal FFT workspace. An earlier estimate in the
Approval C plan quoted a single padded array as "peak memory"; that was wrong
by roughly 5×.

Nothing is cached and nothing is optimised. `H` is recomputed on every call
even though it is constant for fixed `(grid, λ, z)`.

---

## 2. Unsupported cases

| Case | Status |
|---|---|
| Fresnel / Fraunhofer propagation | Absent by design |
| Band-limited ASM | Deferred (§1.2) |
| Backward propagation with evanescent samples on the mesh | **`ValueError`** |
| Non-finite `distance_m` | `ValueError` |
| `pad_factor < 1`, non-integer, or `bool` | `ValueError` / `TypeError` |
| Propagation between planes of different pitch or size | Not representable; ASM requires identical sampling |
| Tilted or non-parallel planes | Out of scope |
| Refractive index ≠ 1 | Not a parameter anywhere |
| Absorbing, scattering or graded media | Out of scope |
| Back-scattering | Only forward components are retained |
| Sampling-adequacy warning | Deliberately not implemented (§1.1) |

---

## 3. Possible failure modes

1. **A silently undersampled transfer function** (§1.1) is the most likely way
   to get a wrong answer that looks right. There is no diagnostic.

2. **A field that overruns the padded window** wraps around again, and the
   result degrades smoothly rather than failing. Only comparison against an
   independent reference reveals it.

3. **Mixing `pad_factor` between related calls.** Propagating forward with
   `pad_factor=2` and back with `pad_factor=1` is not an identity, because the
   two solve different boundary-value problems. `test_m28` uses `pad_factor=1`
   on both legs for exactly this reason.

4. **Assuming `z=0` returns a fresh object.** It returns the input itself.
   That is documented and asserted, but code that relies on getting a distinct
   object would be surprised. `ComplexField` is immutable, so this cannot cause
   aliasing damage.

5. **A flipped evanescent branch is undetectable on realistic grids.** NC-5 was
   caught by only 2 tests, both using deliberately sub-wavelength pitches. Any
   future refactor of the branch logic must keep those tests.

6. **The round trip cannot detect a sign error** — demonstrated by NC-1, where
   `test_m28` passed while 31 other tests failed. Anyone tempted to "simplify"
   the analytic tests down to a round trip would destroy the milestone's
   principal evidence.

7. **The Gaussian tolerance is model-limited.** If someone tightens
   `test_a09`'s `rtol=1e-4` toward machine precision it will fail, and the
   failure will be in the paraxial reference, not the implementation.

---

## 4. Deferred improvements

| Item | Trigger |
|---|---|
| Band-limited ASM (§1.2) | A validation case where TF aliasing dominates and padding cannot fix it |
| Sampling-adequacy diagnostic | A criterion that actually predicts error (the current one does not) |
| Caching `H` across calls | Milestone 3's Gerchberg–Saxton loop, where `(grid, λ, z)` is constant |
| In-place FFT / workspace reuse | If the 22× peak-memory ratio becomes binding |
| Non-paraxial structured-field validation (e.g. exact on-axis Rayleigh–Sommerfeld for a circular aperture) | When hard-edged fields arrive in Milestone 2 |
| `float32` / `complex64` mode | If memory becomes binding; would forfeit the `1e-11` tolerances |
| Propagation between differently-sampled planes | Would need a different algorithm (e.g. scaled/shifted ASM) |

---

## 5. Risks carried into Milestone 2

Milestone 2 loads grayscale target images and turns them into target
amplitudes. Specific risks inherited from here:

1. **Images have hard edges.** Every M1 validation used smooth fields
   (plane waves, Gaussians). A loaded image is discontinuous at the pixel
   level, with energy right up to Nyquist — precisely the regime §1.5 says is
   untested and §1.1 says is undetected. Milestone 2 should not assume M1's
   measured accuracy transfers.

2. **The target plane and the hologram plane must share a grid.** ASM requires
   identical `(ny, nx, dy, dx)`. Image loading must resample to the grid, not
   the other way round, and the resampling policy needs to be an explicit,
   documented decision.

3. **Amplitude versus intensity.** A grayscale image is conventionally an
   *intensity* map, but `ComplexField.from_amplitude_phase` takes amplitude.
   Getting this wrong applies a spurious square root — a plausible-looking
   error. `from_intensity_phase` already exists; the convention must be stated
   normatively.

4. **Nothing in M1 or M2 constrains the reconstruction distance.** The
   combination of image size, pitch and distance determines whether the
   propagation is adequately sampled at all, and there is still no check.
