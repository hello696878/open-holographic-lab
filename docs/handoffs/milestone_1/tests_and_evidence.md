# Milestone 1 — Tests and Evidence

---

## 1. Exact test command and output

### Command

```
.\.venv\Scripts\python.exe -m pytest -q
```

### Output — exact and unedited

```
........................................................................ [ 24%]
........................................................................ [ 49%]
........................................................................ [ 74%]
........................................................................ [ 98%]
...                                                                      [100%]
291 passed in 4.14s
```

Exit code `0`.

### Environment

| Component | Version |
|---|---|
| OS | Windows 11 Home 10.0.26100 |
| Python | 3.11.9 |
| NumPy | 2.4.6 |
| SciPy | 1.17.1 |
| pytest | 9.1.1 |

`filterwarnings = ["error"]` is active, so a green run also proves no NumPy
`RuntimeWarning` (overflow, underflow-to-invalid, divide-by-zero) was emitted
anywhere. This matters for Milestone 1: a naive transfer function emits
`overflow encountered in exp` on an evanescent grid at negative distance.

### Test count by module

| Module | Tests | Milestone |
|---|---|---|
| `test_packaging.py` | 3 | 0 |
| `test_units.py` | 4 | 0 |
| `test_validation.py` | 34 | 0 |
| `test_grid.py` | 68 | 0 |
| `test_field.py` | 44 | 0 |
| `test_fft_conventions.py` | 13 | 0 |
| `test_plane_wave.py` | 22 | 0 |
| **M0 subtotal** | **188** | |
| `test_propagation.py` | 72 | 1 |
| `test_propagation_analytic.py` | 31 | 1 |
| **M1 subtotal** | **103** | |
| **Total** | **291** | |

---

## 2. Headline analytic results

### 2.1 On-grid plane wave — the decisive test

`U(z) = U(0)·exp(i·kz·z)`, exact and non-paraxial. Grid 48×64,
`dy = 5.00 µm`, `dx = 3.74 µm`, `λ = 633 nm`, `pad_factor=1`.

```
  (dcol,drow)   z (mm)     rel err   max|dphase| rad
       (0, 0)      1.0   2.776e-17         0.000e+00
       (0, 0)     50.0   0.000e+00         0.000e+00
       (0, 0)    200.0   1.388e-17         0.000e+00
       (7, 5)      1.0   6.695e-15         6.661e-15
       (7, 5)     50.0   7.011e-15         6.942e-15
       (7, 5)    200.0   7.328e-15         7.327e-15
    (-11, -3)      1.0   1.001e-14         9.992e-15
    (-11, -3)     50.0   1.068e-14         1.066e-14
    (-11, -3)    200.0   1.118e-14         1.110e-14
      (9, -6)      1.0   1.265e-14         1.221e-14
      (9, -6)     50.0   1.357e-14         1.177e-14
      (9, -6)    200.0   1.080e-14         1.055e-14
     (-13, 8)      1.0   1.926e-14         1.926e-14
     (-13, 8)     50.0   1.525e-14         1.465e-14
     (-13, 8)    200.0   1.644e-14         1.643e-14
  WORST relative error over all cases: 1.926e-14
```

**Three-component superposition** (unequal amplitudes, `z = 50 mm`):
`rel err = 5.206e-15`.

### 2.2 Uniform field — the tolerance mechanism confirmed

```
  z=   0.10 mm  k*z= 9.9260e+02 rad  err=1.137e-13  k*z*eps=2.204e-13  ratio=0.52
  z=   1.00 mm  k*z= 9.9260e+03 rad  err=1.819e-12  k*z*eps=2.204e-12  ratio=0.83
  z=  10.00 mm  k*z= 9.9260e+04 rad  err=1.455e-11  k*z*eps=2.204e-11  ratio=0.66
  z= 100.00 mm  k*z= 9.9260e+05 rad  err=1.164e-10  k*z*eps=2.204e-10  ratio=0.53
```

The error tracks `k·z·ε` to within a factor of two at every distance,
confirming the limit is the float64 representation of the *angle*, not the
propagator. Test tolerances scale as `100·k·z·ε` accordingly.

### 2.3 Gaussian beam vs analytic

```
  w0=100um  zR=49.63mm  w0/lambda=158.0  paraxial est. (lambda/pi/w0)^2 = 4.06e-06
    z/zR    z (mm)   w(z) um   complex rel err
     0.5     24.82    111.80         8.120e-07
     1.0     49.63    141.42         1.015e-06
     2.0     99.26    223.61         1.012e-06

  Gouy phase check at z = zR (expect pi/4 = 0.785398):
    measured on-axis lag = 0.785398 rad   error = 4.037e-11
```

**The `~1e-6` floor is the paraxial approximation of the reference, not our
numerical error** — consistent with the `4.06e-06` estimate, and eight orders
of magnitude above the plane-wave floor. The Gouy phase, by contrast, agrees
to `4.0e-11` because it is a *phase* quantity that the paraxial error barely
perturbs.

### 2.4 Padding / wrap-around evidence

Against the analytic Gaussian, `w₀ = 40 µm`, 256², 3.74 µm, window 0.957 mm:

```
    z (mm)   w(z) um   pad_factor=1   pad_factor=2   improvement
       5.0      47.3      5.721e-06      5.721e-06          1.0x
      20.0     108.4      8.123e-06      8.123e-06          1.0x
      50.0     255.0      2.950e-02      2.136e-05       1381.0x
     100.0     505.3      4.976e-01      3.045e-04       1634.4x
```

Note that padding does nothing at short range (the boundary is never reached)
and becomes decisive once the beam approaches the window edge.

### 2.5 Power bookkeeping

```
  pad_factor=1  z=   +1.0mm  rel power change = 0.000e+00
  pad_factor=1  z=  +50.0mm  rel power change = 3.489e-16
  pad_factor=1  z= +500.0mm  rel power change = 2.326e-16
  pad_factor=1  z=  -20.0mm  rel power change = 0.000e+00
  pad_factor=2  z=   +5.0mm  cropped/source power = 1.000000
  pad_factor=2  z=  +25.0mm  cropped/source power = 1.000000
  pad_factor=2  z= +100.0mm  cropped/source power = 0.887108
```

Exact conservation on the periodic window; strict decrease once light leaves
the cropped window. The second is asserted as an **inequality**, never as
conservation.

---

## 3. What the important tests support

| Test | Establishes | Evidence class |
|---|---|---|
| `test_a02_on_grid_plane_wave_acquires_exactly_exp_i_kz_z` | The propagation SIGN, the magnitude of `kz`, and its dependence on `fx`/`fy` across all sign quadrants. Exact, non-paraxial | Analytic ground truth |
| `test_a04_superposition_gives_each_component_its_own_kz` | Linearity, and that each component receives its own `kz` — detects an `fx`/`fy` mix-up that a single plane wave cannot | Analytic + linearity |
| `test_a05` / `test_a06` | The on-axis carrier `exp(i·k·z)`; `a06` isolates the sign at `k·z < π/2` so wrapping cannot hide it | Analytic ground truth |
| `test_a09` / `test_a11` / `test_a12` | Agreement with an independent analytic solution having real transverse structure; the Gouy phase to `4e-11` | Independent analytic solution |
| `test_a10` | Beam width follows `w(z)` — an amplitude check completely insensitive to phase sign, so it corroborates `\|kz\|` independently | Analytic ground truth |
| `test_a07` / `test_a08` | Symmetry preserved for a symmetric source, and NOT manufactured for an asymmetric one | Symmetry + anti-vacuity |
| `test_m26` | Exact power conservation on the periodic window | Conservation law |
| `test_m27` | Cropped power can only decrease | Inequality, physically correct |
| `test_m08` | **Regression:** corner-only evanescent samples are detected by the mesh, not missed by a pitch rule | Analytic + regression |
| `test_m11` / `test_m12` | Evanescent decay for `z>0`; refusal for `z<0`; no warning emitted | Behavioural + policy |
| `test_m15` | The zero-distance contract, asserted with `is` | Exact identity |
| `test_m17`–`test_m19` | Padding preserves the origin convention and `crop(pad(U)) == U` bit-exactly at all parities | Exact identity |
| `test_m04` / `test_m05` | `H(−z) = conj(H(z))`, `H(z₁)H(z₂) = H(z₁+z₂)` | Algebraic identity |
| `test_m28` | Round trip — **secondary evidence only** (see §5) | Round-trip identity |
| `test_m30` | Padding reduces wrap-around by ≥100× against an analytic reference | Independent analytic |

---

## 4. Numerical tolerances

| Test | Tolerance | Measured | Justification |
|---|---|---|---|
| `test_m02` `H(0)` | **exact** | — | `exp(1j·kz·0.0)` is exactly `1+0j` |
| `test_m15` zero distance | **`is`** | — | Object identity is the contract |
| `test_m17`–`m19` padding | **exact** | — | Index arithmetic and data movement, no computation |
| `test_m03` `\|H\|=1` | `atol=1e-12` | `2.220e-16` | ~4500×. **Not** an exact `≤1`: bitwise `exp` behaviour is not guaranteed across platforms |
| `test_m01`, `m05` | `100·k·z·ε` | ratio 0.52–0.83 | The angle's own rounding; a fixed `atol` would fail at long range for no good reason |
| `test_a02` plane wave | `rtol=1e-11`, phase `atol=1e-10` | `1.93e-14`, `1.93e-14` | ~500× and ~5000× |
| `test_a04` superposition | `rtol=1e-11` | `5.21e-15` | ~2000× |
| `test_a05` uniform | `100·k·z·ε` | ratio ≤0.83 | distance-scaled |
| `test_m26` power | `rtol=1e-12` | `3.49e-16` | ~2900× |
| `test_m28` round trip | `rtol=1e-11` | `7.5e-16` | secondary evidence |
| `test_a07` symmetry | `rtol=1e-12` | `8.72e-16` | ~1100× |
| **`test_a09` Gaussian** | **`rtol=1e-4`** | `1.02e-06` | **Floor is the PARAXIAL MODEL (`4.06e-06`), not float64. Must NOT be tightened** |
| `test_a11` Gouy | `atol=2e-3` rad | `4.04e-11` | generous; the effect is `π/4 ≈ 0.785` |
| `test_a10` beam width | `rel=2e-3` | — | second-moment estimator on a truncated grid |

---

## 5. Negative controls — 10 of 10 caught, 0 gaps

Every mutation was injected into `src/ohlab/propagation.py`, the full suite
run, and the source restored automatically.

```
      CAUGHT  NC-1  propagation sign flipped: exp(+i kz z) -> exp(-i kz z)
              31 failed, 260 passed in 4.01s  (31 test(s) failed)
      CAUGHT  NC-2  fy dropped (transverse axis mix-up): fy**2 -> fx**2
              24 failed, 267 passed in 2.94s  (24 test(s) failed)
      CAUGHT  NC-3  centered frequency order used with an unshifted FFT
              33 failed, 258 passed in 3.05s  (33 test(s) failed)
      CAUGHT  NC-4  wrong kz: sqrt(k^2 + kx^2 + ky^2) instead of minus
              21 failed, 270 passed in 3.93s  (21 test(s) failed)
      CAUGHT  NC-5  evanescent branch flipped: Im(kz) <= 0, i.e. growth not decay
              2 failed, 289 passed in 4.04s  (2 test(s) failed)
      CAUGHT  NC-6  inverse FFT omitted (spectrum returned as if it were a field)
              31 failed, 260 passed in 2.64s  (31 test(s) failed)
      CAUGHT  NC-7  distance unit error: metres treated as millimetres
              31 failed, 260 passed in 2.92s  (31 test(s) failed)
      CAUGHT  NC-8  crop misaligned by one row
              10 failed, 281 passed in 3.88s  (10 test(s) failed)
      CAUGHT  NC-9  pad_factor silently ignored
              2 failed, 289 passed in 1.67s  (2 test(s) failed)
      CAUGHT  NC-10 numpy.pad-style centring: (n_pad - n)//2 instead of n_pad//2 - n//2
              7 failed, 284 passed in 3.59s  (7 test(s) failed)

  test gaps: 0

SOURCE RESTORED EXACTLY: True
POST-RESTORE SUITE     : 291 passed in 3.43s
```

### Observations worth recording

- **NC-1 (sign flip) is caught by 31 tests but NOT by the round trip.**
  `test_m28` passes under a global sign flip, because `H(−z) = conj(H(z))`
  whichever sign is used — a wrong propagator cancels itself. This is the
  concrete demonstration of why the round trip is secondary evidence and the
  analytic plane-wave tests carry the weight.
- **NC-5 is caught by only 2 tests**, both evanescent-specific. That is
  correct and expected: on every realistic grid there are no evanescent
  samples, so a flipped evanescent branch is genuinely unobservable there. It
  is detected only because `test_m11` deliberately constructs sub-wavelength
  grids.
- **NC-10 confirms the `numpy.pad` concern was real**, not hypothetical: the
  default centring fails 7 tests, all at odd sizes.
- **NC-9 is caught by only 2 tests** — the wrap-around and cropped-power
  tests. Everything else uses `pad_factor=1` by design, so it is invisible to
  them.

---

## 6. What this test suite does NOT prove

1. **That the conventions match Goodman.** They were verified against
   Konijnenberg/Adam/Urbach (§3.1), which is a genuine independent source, but
   the Goodman attribution itself remains unchecked and is now labelled as such.
2. **That propagation is correct at long range on a coarse grid.** The transfer
   function becomes undersampled and nothing detects it. The Gaussian tests
   stay in the well-sampled regime by construction.
3. **Anything about hard-edged apertures.** No test propagates a discontinuous
   field. Aliasing from sharp edges is a real effect that is neither measured
   nor bounded here.
4. **That `pad_factor=2` is enough for any given problem.** It is a default,
   not a guarantee. A beam that overruns the padded window wraps again.
5. **Non-paraxial accuracy beyond the plane-wave tests.** The plane-wave tests
   are exact and non-paraxial but involve a single spatial frequency each; the
   only structured-field comparison (Gaussian) is paraxial. A genuinely
   non-paraxial structured comparison — for example the exact on-axis
   Rayleigh–Sommerfeld solution for a circular aperture — was considered and
   deferred, because a hard aperture's unbounded bandwidth would make the
   comparison measure sampling adequacy rather than the transfer function.
6. **Correctness on any NumPy other than 2.4.6**, or on any non-Windows
   platform.
7. **Performance adequacy for Milestone 3.** One 1024² propagation with
   `pad_factor=2` takes **1.2 s** and peaks at 352 MB of NumPy allocation; a
   200-iteration Gerchberg–Saxton loop would need roughly 8 minutes of
   propagation alone. See `known_limitations.md` §1.6 for the full table.
