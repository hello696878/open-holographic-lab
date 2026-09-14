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

**Historical provenance correction — 2026-09-14.** The heading above does
not describe every row of the original table below. Recovered planning-probe
source and output show that its 5 mm and 20 mm values match comparison
against a **4×-padded, band-limited numerical reference**, not an analytic
Gaussian. A later analytic probe gives the approximately `1e-6` values in
`tests_and_evidence.md` §2.4. At 100 mm the padded value instead agrees with
the later analytic result, so this table cannot be treated as one consistent
analytic benchmark. The original numbers remain untouched. Exact assembly
and rounding of every cell are not fully recorded. See the
[recovered provenance and separate current probe](../../corrections/m0_m1_contract_and_evidence.md).
No band-limited implementation has been added or rerun by this maintenance.

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

Measured on the complete shipped propagation path (`_zero_pad`, `fft2`, `H`,
multiply, `ifft2`, `_crop`, `with_data`), each configuration in a **fresh
process**, after one warm-up call.

**Two different quantities are reported, and they must not be conflated:**

- **Peak Python-visible allocation** — `tracemalloc` high-water mark for the
  call. This is the sum of NumPy arrays and temporaries allocated through
  Python. It does *not* include allocations made inside NumPy's C code.
- **Process working set** — the operating system's view (`WorkingSetSize` /
  `PeakWorkingSetSize` via `K32GetProcessMemoryInfo`). This includes the
  interpreter, NumPy itself, and any C-level FFT workspace.

| `N` | `pad_factor` | source array | computational array | peak Python alloc | ÷ source | ÷ computational | proc. WS delta | proc. WS peak | ms/call |
|---|---|---|---|---|---|---|---|---|---|
| 128 | 1 | 0.25 MB | 0.25 MB | 1.13 MB | 4.5× | 4.5× | 1.48 MB | 29.81 MB | 2.4 |
| 128 | 2 | 0.25 MB | 1.00 MB | 5.50 MB | 22.0× | 5.5× | 4.95 MB | 33.62 MB | 11.2 |
| 256 | 1 | 1.00 MB | 1.00 MB | 4.50 MB | 4.5× | 4.5× | 4.61 MB | 33.73 MB | 10.5 |
| 256 | 2 | 1.00 MB | 4.00 MB | 22.00 MB | 22.0× | 5.5× | 20.04 MB | 49.42 MB | 60.4 |
| 512 | 1 | 4.00 MB | 4.00 MB | 18.00 MB | 4.5× | 4.5× | 18.04 MB | 50.53 MB | 56.0 |
| 512 | 2 | 4.00 MB | 16.00 MB | 88.00 MB | 22.0× | 5.5× | 80.04 MB | 112.64 MB | 211.3 |
| 1024 | 1 | 16.00 MB | 16.00 MB | 72.00 MB | 4.5× | 4.5× | 72.04 MB | 116.39 MB | 223.0 |
| **1024** | **2** | **16.00 MB** | **64.00 MB** | **352.00 MB** | **22.0×** | **5.5×** | **320.05 MB** | **364.55 MB** | **1209.7** |

Notes on reading the table:

- **`source array`** is one `complex128` array of the caller's grid,
  `N²·16` bytes. **`computational array`** is one `complex128` array of the
  padded grid actually transformed, `(p·N)²·16` bytes. The `22×` and `5.5×`
  columns are the *same measurement* against these two different denominators —
  `22 = 5.5 × p²` with `p = 2`. Quoting a ratio without naming its denominator
  is meaningless, which is why both are shown.
- **The process working-set delta is slightly below the Python-visible peak**
  (e.g. 320 MB vs 352 MB at 1024²/2) because the warm-up call had already
  faulted those pages in, so they were resident at the baseline.
- **The process working-set peak includes a ~28–29 MB floor** for the
  interpreter plus NumPy, independent of problem size.

**Where the peak comes from.** Not one padded array. With `pad_factor=2` the
path holds, simultaneously, the padded source, the transfer function,
`fft2(source)`, the product, and the `ifft2` output — five arrays of the
computational grid — plus the cropped output copy. That is 5 computational
units ≈ 5.5× measured, or 22× a source array.

The ordering matters and was measured: `angular_spectrum_transfer_function` is
called **before** `fft2`, so its internal temporaries (`fx`, `fy`, `radial`,
`kz`) are freed on return while only the padded source is alive. Computing the
transfer function *after* the forward FFT — as a throwaway planning probe did —
keeps one extra computational unit live and raises the peak to 26× a source
array. The shipped ordering is the leaner of the two.

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
