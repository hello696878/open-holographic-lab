# Milestone 0 — Mathematics Used

Every equation actually implemented or assumed in Milestone 0, with symbols,
units, conventions, and the corresponding Python name.

Technically precise, not a beginner tutorial. Normative source:
`docs/math_conventions.md` v0.2.

**Correction notes added 2026-09-14.** This is the historical M0 mathematics
record. Original equations and claims below are preserved; labeled notes in
§3.2, §5.1, and §5.5 supply the current corrections. The current normative
source is v0.4; see also the
[consolidated correction record](../../corrections/m0_m1_contract_and_evidence.md).

---

## 1. Symbol table

| Symbol | Meaning | Unit | Python name | Type |
|---|---|---|---|---|
| `U` | complex field (complex amplitude / phasor) | a.u. | `ComplexField.data` | `(ny,nx)` complex128 |
| `A` | amplitude, `\|U\|` | a.u. | `ComplexField.amplitude` | `(ny,nx)` float64 |
| `φ` | phase, `arg(U)` | rad | `ComplexField.phase` | `(ny,nx)` float64 |
| `I` | intensity, `\|U\|²` | a.u. | `ComplexField.intensity` | `(ny,nx)` float64 |
| `P` | optical power | a.u.·m² | `ComplexField.power` | `float` |
| `λ` | vacuum wavelength | m | `wavelength_m` | `float` |
| `k` | wavenumber | rad/m | `ComplexField.wavenumber` | `float` |
| `ω` | angular temporal frequency | rad/s | *(never stored)* | — |
| `t` | time | s | *(never stored)* | — |
| `Nx, Ny` | sample counts | — | `nx`, `ny` | `int` |
| `dx, dy` | pixel pitch | m | `dx`, `dy` | `float` |
| `Lx, Ly` | window extent | m | `extent_x`, `extent_y` | `float` |
| `x, y` | transverse coordinates | m | `grid.x`, `grid.y` | `(n,)` float64 |
| `fx, fy` | spatial frequency (cyclic) | cycles/m | `fx_fft`, `fx_centered` | `(n,)` float64 |
| `kx, ky` | spatial frequency (angular) | rad/m | `kx_fft`, `kx_centered` | `(n,)` float64 |
| `f_nyq` | Nyquist frequency | cycles/m | `nyquist_fx`, `nyquist_fy` | `float` |
| `θx, θy` | tilt angles | rad | `theta_x_rad`, `theta_y_rad` | `float` |
| `i, j` | row, column index | — | — | `int` |
| `n` | refractive index | — | *fixed at 1, not a parameter* | — |

`a.u.` = arbitrary units (see §3).

---

## 2. The complex field and the time convention

### 2.1 Phasor representation

The physical, real, time-varying scalar field is

```
E(x, y, t) = A(x, y) · cos(ω·t − φ(x, y))
           = Re{ U(x, y) · exp(−i·ω·t) }
```

with

```
U(x, y) = A(x, y) · exp( i·φ(x, y) )                                    (1)
```

**Convention:** `exp(−iωt)` time dependence (`math_conventions.md` §3.1,
Goodman). The factor `exp(−iωt)` is identical at every point and unchanged by
every linear optical element, so it is never stored. Only `U` is stored.

**Implemented in:** `ComplexField.data`, and
`ComplexField.from_amplitude_phase`, which computes `a * np.exp(1j * p)`.

**Assumptions:** scalar (polarization ignored), monochromatic, fully coherent,
linear and time-invariant medium.

### 2.2 Consequences of the sign convention

Not implemented in Milestone 0, but locked in and carried forward:

```
plane wave travelling in +z            exp(+i·k·z)
forward propagation of the spectrum    exp(+i·kz·Δz)
converging lens, focal length f > 0    exp(−i·k·r²/(2f))
evanescent decay for Δz > 0            exp(−|kz|·Δz)
```

The opposite (`exp(+iωt)`) convention conjugates every field in the codebase.
**These may not be mixed.**

---

## 3. Amplitude, phase, intensity, power

### 3.1 Amplitude

```
A = |U| = sqrt( Re(U)² + Im(U)² )                                       (2)
```

**Python:** `np.abs(self.data)` (uses `hypot`, which avoids intermediate
overflow). Range `[0, ∞)`.

### 3.2 Phase

```
φ = arg(U) = atan2( Im(U), Re(U) )                                      (3)
```

**Python:** `np.angle(self.data)`.

**Correction (2026-09-14).** The original implementation statement above
omits the now-required canonical-endpoint step. `ComplexField.phase` evaluates
`np.angle(self.data)` and maps outputs exactly equal to `−π` to `+π`.
NumPy alone can return `−π` for negative-real values with negative signed-zero
imaginary parts. Nearby negative angles and stored field bits are unchanged.
The original zero-amplitude discussion below applies to ordinary `0+0j`;
signed-zero combinations can yield other raw angles, with `−π` subject to the
same endpoint rule. Phase is physically undefined for every zero-amplitude
combination. These corrections do not change equation (3)'s modulo-`2π`
mathematical meaning.

**Convention:** the canonical branch is the half-open interval **`(−π, +π]`**.
Note `np.angle(-1.0) = +π`, not `−π`.

**Undefined where `A = 0`.** NumPy returns `0.0` there as its own convention;
that value carries no physical meaning and every test that compares phases
masks those pixels out (`_helpers.assert_phase_allclose`).

**Comparison rule.** Because phase is defined only modulo `2π` and `np.angle`
has a branch cut, two phase maps are compared through the wrapped difference

```
Δφ = arg( exp( i·(φ_actual − φ_expected) ) )                            (4)
```

which returns `0` for physically identical phases regardless of branch.
**Python:** `_helpers.wrapped_phase_difference`.

### 3.3 Intensity

```
I = |U|² = U · conj(U) = Re(U)² + Im(U)²                                (5)
```

**Python:** `self.data.real**2 + self.data.imag**2`.

**Approximation / convention.** Physically, irradiance is
`I_phys = ½·ε₀·c·n·|U|²` in W/m². **The constant `½ε₀cn` is dropped** — every
quantity this project reports is a ratio, a normalized error, or a displayed
image, none of which depends on it. Intensities are therefore relative, **not**
radiometric, and must not be reported in W/m².

**Implementation note.** `Re² + Im²` is used rather than `np.abs(U)**2` so that
the test `intensity == amplitude**2` compares two independent code paths. The
cost is that no `hypot`-style rescaling protects against overflow for
amplitudes beyond ~`1e154`.

### 3.4 Optical power

The area integral of intensity over the window, discretised as a
rectangular-rule sum:

```
P = ∫∫ I(x,y) dx dy  ≈  Σ_ij I[i,j] · dx · dy                           (6)
```

**Python:** `float(np.sum(self.intensity) * self.grid.pixel_area)`.

**Approximation:** rectangular rule (each sample represents one full cell of
area `dx·dy`). Exact for band-limited fields sampled above Nyquist; first-order
accurate otherwise. Units a.u.·m².

### 3.5 Wavenumber

```
k = 2π / λ                                                              (7)
```

**Python:** `2.0 * math.pi / self.wavelength_m`. For `λ = 633 nm`,
`k = 9.9260e6 rad/m`.

### 3.6 Invariance of a phase-only element

For any real `ψ(x,y)`, since `|exp(iψ)| = 1` exactly:

```
|U · exp(iψ)|² = |U|²        and therefore      P unchanged             (8)
```

This is the defining property of a phase-only modulator and the reason a
phase-only SLM can redistribute light without absorbing it. Verified by
`test_f10`.

---

## 4. Sampling geometry

### 4.1 Array layout

```
data.shape = (Ny, Nx)
data[i, j] = U at (x[j], y[i])
axis 0 = row index i -> y
axis 1 = col index j -> x
```

`+y` increases with row index, so with `imshow(origin='upper')` the `+y` axis
points **downward** on screen. This makes the displayed `(x, y)` pair
left-handed. It affects nothing that depends only on `kx² + ky²` (which is all
of Milestones 0–3) but will flip the sign of any signed vertical quantity —
tilt ramps, off-axis carriers, vortex charge.

### 4.2 Spatial coordinates

```
x[j] = (j − Nx//2) · dx        j = 0 … Nx−1                             (9)
y[i] = (i − Ny//2) · dy        i = 0 … Ny−1
```

`//` is floor division. Consequently `x[Nx//2] == 0.0` **exactly**, for both
parities, because `(Nx//2 − Nx//2)·dx` is exactly `0.0` in IEEE-754.

For even `N` the span is `[−(N/2)·dx, +(N/2 − 1)·dx]` — asymmetric by one
sample. Accepted deliberately in exchange for exact index alignment with
`fftshift(fftfreq(...))`.

**Python:** `(np.arange(self.nx) - (self.nx // 2)) * self.dx`.

### 4.3 Extent

```
Lx = Nx · dx        (= x[-1] − x[0] + dx)                              (10)
```

The extent counts each sample's full cell, not merely the distance between the
first and last sample centres.

### 4.4 2-D grids

```
x_grid, y_grid = np.meshgrid(x, y, indexing='xy')     both (Ny, Nx)
```

`x_grid` varies along axis 1, `y_grid` along axis 0. **Return order is
`(x, y)`**, matching `numpy.meshgrid` — not axis order.

---

## 5. Spatial frequency

### 5.1 Fourier transform convention

```
A(fx, fy) = ∬ U(x,y) · exp( −i·2π·(fx·x + fy·y) ) dx dy               (11)
U(x,y)    = ∬ A(fx,fy) · exp( +i·2π·(fx·x + fy·y) ) dfx dfy           (12)
```

The `−i` in the forward transform matches `numpy.fft.fft2`'s kernel. Each
component of the inverse transform is then a plane wave
`exp(+i(kx·x + ky·y))`, which combined with `exp(+i·kz·z)` from §2.2 gives a
forward-travelling wave. **The three sign choices are mutually consistent and
cannot be changed independently.** Verified by `test_c04` (shift theorem).

**Correction (2026-09-14).** The preceding sign-coupling claim is overstated.
The chosen signs are consistent, but the Fourier analysis/inverse pair can be
chosen independently of the time convention, with a consistent transverse
wavevector interpretation. An analysis kernel `exp(s·i·2πf·r)` has inverse
kernel `exp(−s·i·2πf·r)` and synthesis wavevector `k_perp = −s·2πf`.
The project continues to use `s = −1`; no production sign changes.
`test_c04` checks the chosen Fourier kernel, not the temporal convention.
Current C-09/C-10 independently check both transform pairs.

### 5.2 Frequency axes

```
fx_centered[m] = (m − Nx//2) · (1 / (Nx · dx))     [cycles/m]         (13)
fx_fft         = ifftshift(fx_centered)                               (14)
kx             = 2π · fx                            [rad/m]           (15)
```

**Required evaluation order (v0.2, §3.8.1).** Equation (13) must be evaluated
as a *reciprocal-multiply*, not as the division `(m − Nx//2)/(Nx·dx)`. The two
are mathematically identical but differ by ~1 ULP; `np.fft.fftfreq` computes
`val = 1.0/(n*d)` once and multiplies, and this project guarantees bit-for-bit
agreement with it.

Measured (NumPy 2.4.6): the division form is bit-identical at `n=8, d=1.0` but
differs at `n=512, d=3.74e-6` by `2.910e-11` absolute / `2.177e-16` relative.

**Python:**
```python
val = 1.0 / (n * d)
return (np.arange(n) - (n // 2)) * val
```

### 5.3 Ordering

| Ordering | Value at index 0 | Zero frequency at | Python |
|---|---|---|---|
| FFT | `0` | index `0` | `fx_fft` |
| centred | most negative | index `n//2` | `fx_centered` |

Mixing them is the dominant failure mode in this kind of code, so the ordering
is part of every name and `freq_meshgrid(*, order=...)` has no default.

### 5.4 Nyquist limit and diffraction angle

```
f_nyq = 1 / (2·d)                                   [cycles/m]        (16)
sin(θ_max) = λ · f_nyq = λ / (2·d)                                    (17)
```

For even `N`, `fx_centered[0] == −f_nyq` exactly, and the maximum sampled value
is `+f_nyq − 1/(N·d)` — the positive Nyquist frequency is **not** a sample.

Worked value: `λ = 633 nm`, `d = 3.74 µm` → `sin θ = 0.084626`,
`θ = 4.855°`. This is why phase-only SLM holograms have a narrow field of view.

**Python:** `nyquist_fx`, `max_diffraction_angle_rad(λ, axis=...)`. The method
raises `ValueError` when `λ/(2d) > 1` rather than returning `NaN`.

### 5.5 Discrete transform and normalization

`numpy.fft` default `norm="backward"`: `fft2` applies no scale factor, `ifft2`
applies `1/(Ny·Nx)`. Parseval therefore holds in the form

```
Σ_ij |u[i,j]|²  =  (1/(Ny·Nx)) · Σ_lm |fft2(u)[l,m]|²                 (18)
```

Verified by `test_c02`; measured relative error ≤ `2.4e-16`.

The DFT approximates the continuous spectrum only up to the sample area:

```
A(fx[m], fy[l]) ≈ dx · dy · fft2(U)[l, m]                             (19)
```

Milestone 0 never applies the `dx·dy` factor (nothing here reports a physical
spectral amplitude). Propagation will not apply it either, because forward and
inverse transforms contribute reciprocal factors that cancel.

**Correction (2026-09-14) to equation (19).** The physical-coordinate
spectrum requires the origin phase as well as sample area. With
`x0 = −(Nx//2)·dx`, `y0 = −(Ny//2)·dy`, and FFT-ordered frequencies:

```
C[l,m] = exp(−i·2π·(fx[m]·x0 + fy[l]·y0))
A_d[l,m] = dx·dy · Σ_ij U[i,j] exp(−i·2π·(fx[m]·x[j] + fy[l]·y[i]))
         = dx·dy · C[l,m] · FFT2(U)[l,m]                            (19-c)
U = IFFT2{ A_d / (dx·dy·C) }
```

`A_d` is the rectangular-sum approximation to the continuous `A`, in a.u.·m².
Factoring `x[j] = x0+j·dx`, `y[i] = y0+i·dy` gives (19-c); the remaining sum
is the index-based DFT. Equivalently, `A_d = dx·dy·FFT2(ifftshift(U))` in
FFT frequency order, at both parities. In same-grid propagation the pointwise
`C` and area factors cancel through `H`, leaving the existing
`IFFT2{H·FFT2(U)}` unchanged. C-09 compares with independent coordinate sums
and a center impulse; C-11 checks that cancellation. The original equation
(19) and historical measurements remain above as the record being corrected.

---

## 6. The plane wave

### 6.1 Definition

```
U(x, y) = A · exp( i·(kx·x + ky·y) )                                  (20)
kx = k·sin(θx),   ky = k·sin(θy),   k = 2π/λ                          (21)
```

**Python:** `ComplexField.plane_wave`.

### 6.2 Physical validity — the propagating condition

A homogeneous plane wave in a medium with `n = 1` satisfies
`kx² + ky² + kz² = k²`. For `kz` to be real (a propagating, not evanescent,
wave):

```
kx² + ky² ≤ k²        ⟺        sin²(θx) + sin²(θy) ≤ 1                (22)
```

**This is a joint condition on the two angles.** Each of `θx = θy = 50°` is
individually reasonable, but together `sin²+sin² = 1.174 > 1`, requiring an
imaginary `kz`. That combination is rejected.

**Implementation note.** The check is coded as `sin²(θx) + sin²(θy) > 1.0`
rather than `kx² + ky² > k²`. The forms are equivalent (divide by `k²`) but the
sine form avoids constructing `k² ≈ 1e14` and losing precision. The boundary
case is subject to the rounding of `math.sin`; grazing incidence (`kz = 0`) is
degenerate anyway.

Verified by `test_p06` (rejected) and `test_p07` (accepted at 30°/30°).

### 6.3 Sampling validity — the Nyquist condition

```
|sin(θx)| / λ ≤ 1/(2·dx)        and likewise for y                    (23)
```

Checked per axis, independently of (22). Verified by `test_p08` (rejected) and
`test_p09` (accepted exactly at the limit — the bound is inclusive).

### 6.4 Analytic structure — the neighbour-ratio identity

The primary analytic validation of the whole coordinate/wavenumber/phase chain.
From (20), for adjacent columns:

```
U[i, j+1] · conj(U[i, j]) = A² · exp( i·kx·dx )                       (24)
```

so

```
arg( U[i,j+1] · conj(U[i,j]) ) = kx · dx      (mod 2π)                (25)
```

and likewise `arg(U[i+1,j]·conj(U[i,j])) = ky·dy` along rows.

This is a **pointwise identity** requiring no phase unwrapping, no polynomial
fitting, and no reference to the absolute phase origin. Test angles are chosen
so that `|kx·dx| = π·(fraction of Nyquist)` stays well inside `(−π, +π]`, away
from the branch cut.

Verified by `test_p02`; measured agreement ≤ `1e-10` rad against an analytic
tolerance derived from `|kx·x| ≈ 16 rad` and float64 epsilon.

A secondary check (`test_p03`) fits the unwrapped phase along a row and
recovers `kx` as the gradient. It is retained as a cross-check but is not
relied on alone, since `np.unwrap` has its own failure modes near the branch
boundary.

### 6.5 On-grid plane wave and the DFT

For `fx0 = fx_centered[m0]` and `fy0 = fy_centered[l0]` exactly on grid, summing
the DFT in closed form gives all energy in a single bin, with a known complex
value:

```
fftshift(fft2(U))[l0, m0] = Ny·Nx · exp( +i·2π·(fx0·x[0] + fy0·y[0]) )  (26)
```

The magnitude pins the bin location; the phase factor pins the consistency
between `meshgrid()` and the 1-D axes, and pins the DC scale factor `Ny·Nx` of
the unnormalized forward transform.

Verified by `test_c01` and `test_p05`; measured agreement `6e-16` relative,
off-peak/peak amplitude ratio exactly `0`.

**Scope caveat.** (26) does *not* pin the absolute origin convention: a uniform
redefinition of `x` shifts both the field and the prediction equally. The
origin is pinned separately and exactly by `test_g07` (`x[n//2] == 0.0`). This
division of labour was established by an explicit negative control.

---

## 7. Assumptions and approximations, collected

| # | Assumption | Where it enters | Consequence if violated |
|---|---|---|---|
| A1 | Scalar field; polarization ignored | (1) | Wrong for high-NA or polarizing systems |
| A2 | Monochromatic, fully coherent | (1) | No white light, partial coherence, or RGB |
| A3 | `n = 1`, homogeneous | (7), (21), (22) | Wrong `k`, wrong propagating condition |
| A4 | Linear, time-invariant medium | (1) | No nonlinear optics |
| A5 | `exp(−iωt)` time convention | §2.1, §2.2, (11) | Every phase conjugated |
| A6 | `½ε₀cn` dropped from intensity | (5) | Intensities are relative, not radiometric |
| A7 | Rectangular-rule area integral | (6) | First-order error if undersampled |
| A8 | Band-limited to Nyquist | (16), (23) | Silent aliasing |
| A9 | `float64` / `complex128` throughout | all | ~1e-16 relative precision floor |
| A10 | `numpy.fft` `norm="backward"` | (18), (19) | Factor-of-`Ny·Nx` errors |

**Not assumed anywhere in Milestone 0:** any paraxial (Fresnel) or far-field
(Fraunhofer) approximation, any thin-element approximation, any small-angle
approximation. Equation (17) and condition (22) are exact.
