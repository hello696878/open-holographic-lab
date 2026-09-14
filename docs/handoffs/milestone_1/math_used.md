# Milestone 1 — Mathematics Used

Every equation implemented or assumed in Milestone 1. Technically precise, not
a beginner tutorial. Normative source: `docs/math_conventions.md` v0.3.

**Correction notes added 2026-09-14.** Original equations and measurements are
preserved below. Notes in §2.1 and §2.4 correct spectrum notation and the
domain of the conjugacy identity. The current normative source is v0.4; see
the [consolidated correction record](../../corrections/m0_m1_contract_and_evidence.md).

Milestone 0's symbol table (`U`, `A`, `φ`, `I`, `P`, `λ`, `k`, `fx`, `kx`, …)
still applies; only additions are listed here.

---

## 1. Additional symbols

| Symbol | Meaning | Unit | Python name |
|---|---|---|---|
| `z` | signed propagation distance | m | `distance_m` |
| `kz` | axial wavevector component | rad/m | `kz` (local) |
| `H` | angular-spectrum transfer function | dimensionless | `angular_spectrum_transfer_function(...)` |
| `A(fx,fy;z)` | angular spectrum at plane `z` | a.u.·m² | *(never named; an intermediate)* |
| `w₀` | Gaussian beam waist radius | m | `waist_m` |
| `w(z)` | Gaussian beam radius at `z` | m | `w_z` |
| `z_R` | Rayleigh range | m | `rayleigh` |
| `R(z)` | wavefront radius of curvature | m | `radius_z` |
| `ψ(z)` | Gouy phase | rad | `gouy` |
| `p` | zero-padding factor | — | `pad_factor` |

---

## 2. The Angular Spectrum Method

### 2.1 The three steps

```
A(fx, fy; 0) = FFT2{ U(x, y, 0) }                                       (1)
A(fx, fy; z) = A(fx, fy; 0) · H(fx, fy; z)                              (2)
U(x, y, z)   = IFFT2{ A(fx, fy; z) }                                    (3)
```

**Python:** `np.fft.ifft2(np.fft.fft2(source) * transfer)`.

The `dx·dy` factor relating the DFT to the continuous spectrum (§3.7 eq. 19)
is not applied: the forward and inverse transforms contribute reciprocal
factors that cancel exactly, and nothing here reports a physical spectral
amplitude.

**Correction (2026-09-14).** The `A` in the original FFT pipeline (1)–(3)
denotes raw index-based DFT coefficients, not the physical spectrum with units
a.u.·m² listed in §1. For the latter, define `a = dx·dy` and
`C[l,m] = exp(−i·2π·(fx[m]·x0 + fy[l]·y0))`, where
`x0 = −(Nx//2)·dx`, `y0 = −(Ny//2)·dy`. Then

```
A_d(0) = a·C·FFT2(U_0)
A_d(z) = H·A_d(0)
U_z = IFFT2{ A_d(z)/(a·C) } = IFFT2{ H·FFT2(U_0) }
```

Factoring the constant origin term from the physical-coordinate Fourier sum
gives the first line; the inverse uses the opposite kernel and frequency-cell
area `1/(Ny·Nx·a)`. The origin phases cancel along with the areas on the
**same grid**. No shifts are inserted into propagation. See normative §3.7,
M0 equation (19-c), and independent direct-sum tests C-09–C-11.

### 2.2 The transfer function — one expression

```
H(fx, fy; z) = exp( +i · kz · z )                                       (4)

kz = 2π · √( 1/λ² − fx² − fy² )      principal branch, Im{kz} ≥ 0       (5)
```

Equivalently, in angular variables, `kz = √(k² − kx² − ky²)`.

**This one expression covers everything**: propagating samples, evanescent
samples, and both signs of `z`. It is deliberately *not* written as a
piecewise definition, and there is deliberately no second formula for backward
propagation — see §2.4.

**Python:**
```python
radial = (1.0 / lam) ** 2 - fx**2 - fy**2
kz = 2.0 * np.pi * np.sqrt(radial.astype(np.complex128))
return np.exp(1j * kz * distance)
```

The cast to `complex128` before `np.sqrt` is what selects the branch: NumPy's
principal square root returns `+i·√|·|` for a negative real argument, which is
exactly `Im{kz} ≥ 0`. No `np.where`, no sign logic, no branch.

**Derivation sketch.** Each plane-wave component `exp(i(kx·x + ky·y))` of the
source must satisfy the Helmholtz equation `∇²U + k²U = 0` in the source-free
half-space `z > 0`. Substituting `U = A·exp(i(kx·x + ky·y + kz·z))` gives
`kx² + ky² + kz² = k²`, hence (5). The branch is fixed by requiring that no
component grow without bound as `z → +∞`.

### 2.3 Propagating and evanescent regimes

| Regime | Condition | `kz` | `\|H\|` for `z > 0` |
|---|---|---|---|
| Propagating | `fx² + fy² < 1/λ²` | real, `> 0` | 1 |
| Grazing | `fx² + fy² = 1/λ²` | 0 | 1 |
| Evanescent | `fx² + fy² > 1/λ²` | purely imaginary, `Im > 0` | `< 1`, decaying |

For an evanescent sample, writing `kz = i·κ` with `κ = 2π√(fx²+fy² − 1/λ²) > 0`:

```
H = exp(i · (i·κ) · z) = exp(−κ·z)                                      (6)
```

which decays for `z > 0` and **grows** for `z < 0`. Same expression; the
physics falls out of the sign of `z`.

**Measured:** worst-case `| |H| − 1 |` on the propagating branch across grids
and distances is `2.220e-16`, exactly one float64 epsilon. `|H| = 1` is a
mathematical identity, not a bitwise one, and tests must use a
machine-precision tolerance.

### 2.4 Why there is no separate backward expression

From (4), for any real `kz` or any `kz` on the chosen branch:

```
H(−z) = exp(−i·kz·z) = conj( exp(+i·kz·z) ) = conj( H(z) )              (7)
```

so reversing the distance conjugates the propagator automatically. Writing a
second formula such as `exp(−i·|kz|·z)` would be redundant, would need its own
branch handling for the evanescent case, and is easy to sign incorrectly.
Pinned by `test_m04`.

**Correction (2026-09-14) to equation (7).** The historical wording "any
`kz` on the chosen branch" is incorrect. Conjugacy holds for **real `kz`**
only (including zero). For `kz=i·κ`, `κ>0`, and `z>0`:

```
H(z) = exp(−κz),    H(−z) = exp(+κz) != conj(H(z))                 (7-c)
```

The public functions refuse the backward request on an evanescent mesh; they
still compute forward decay with the same single expression. M-04 uses an
all-propagating mesh; M-11/M-12 test decay and backward rejection separately.
The original equation remains above for historical traceability and must be
read with this restriction. Composition (8) remains valid for the exponential,
but neither composition nor a forward/backward round trip alone establishes
the physical propagation sign.

Composition follows from the same exponential:

```
H(z₁) · H(z₂) = H(z₁ + z₂)                                              (8)
```

Pinned by `test_m05` (transfer function) and `test_m29` (fields).

---

## 3. Determining whether a grid carries evanescent samples

**The criterion is evaluated on the actual discrete mesh:**

```
evanescent(grid) := any over the 2-D FFT-ordered mesh of
                    ( fx² + fy² > 1/λ² )                                (9)
```

**Python:** `(fx**2 + fy**2) > (1.0 / wavelength_m) ** 2` on
`grid.freq_meshgrid(order="fft")`.

### 3.1 Why no scalar pitch threshold works

The frequency-axis limit is `f_nyq = 1/(2d)`, so requiring the *axis* to reach
the cutoff gives `1/(2d) > 1/λ`, i.e.

```
d < λ/2                    AXIS-ONLY -- NOT the correct criterion       (10)
```

But the extreme sample of a square mesh is the **corner** of the Nyquist
square, at radius

```
|f|_corner = √( f_nyq,x² + f_nyq,y² ) = √2 / (2d)      (square grid)     (11)
```

so evanescent samples first appear at

```
d < λ/√2                   CORNER condition, square grid                (12)
```

At `λ = 633 nm`: `λ/2 = 316.50 nm` but `λ/√2 = 447.60 nm`. **Between those two
pitches the evanescent region is populated only near the four corners.**

Measured (64×64 grid, λ = 633 nm):

| pitch | axis reaches cutoff? | mesh has evanescent? | count of 4096 |
|---|---|---|---|
| 450 nm | no | no | 0 |
| 440 nm | no | **yes** | 5 |
| 420 nm | no | **yes** | 29 |
| **400 nm** | **no** | **yes** | **97** |
| 350 nm | no | **yes** | 433 |
| 316 nm | yes | yes | 899 |
| 250 nm | yes | yes | 2087 |

For an **anisotropic** grid, (11) becomes `√(1/(2dy)² + 1/(2dx)²)` and there is
no single `d` at all — no scalar threshold exists even in principle.

Regression test: `test_m08_evanescent_detection_uses_the_discrete_mesh_not_a_pitch_rule`
uses `d = 400 nm` and asserts that the axis condition says "no", the mesh says
"yes", and no evanescent sample lies on either axis.

---

## 4. Zero-padding and cropping

### 4.1 Alignment rule

For each axis, with `N` original samples and `N_pad = p·N`:

```
pad_before = N_pad//2 − N//2                                            (13)
pad_after  = N_pad − N − pad_before
```

**Property guaranteed:** original index `N//2` maps to padded index
`N_pad//2`, therefore

```
x_padded[ j + pad_before ] == x[ j ]      bit-exactly, for every j       (14)
```

because both are `(index − N//2)·dx` with the same integer offset (§3.4). The
pitch is unchanged, so the Nyquist limit is unchanged; only the frequency
*spacing* becomes finer.

**Why not `numpy.pad`'s default.** `np.pad` with a symmetric width places
`(N_pad − N)//2` samples before, which for odd `N` differs from (13). Example:
`N = 7`, `p = 2` gives `N_pad = 14`; (13) yields `pad_before = 7 − 3 = 4`,
while `(14 − 7)//2 = 3`. The latter shifts every physical coordinate by one
pixel. Pinned by `test_m17`, `test_m18`, `test_m19`, and negative control NC-10.

### 4.2 Boundary-condition semantics

| `pad_factor` | Problem actually solved |
|---|---|
| `1` | The original **periodic** DFT window |
| `> 1` | The field embedded in a larger **zero-valued** window, result cropped |

These are **different boundary conditions**, not a worse and a better one.
Padding reduces circular wrap-around but does not guarantee physical
correctness: once light reaches the padded edge it wraps again, and embedding
a window-filling field imposes a hard aperture the periodic problem lacked.

Measured against the analytic Gaussian (`w₀ = 40 µm`, 256², 3.74 µm pitch):

| `z` | `w(z)` | `pad_factor=1` | `pad_factor=2` | improvement |
|---|---|---|---|---|
| 5 mm | 47.3 µm | `5.72e-06` | `5.72e-06` | 1.0× |
| 20 mm | 108.4 µm | `8.12e-06` | `8.12e-06` | 1.0× |
| 50 mm | 255.0 µm | `2.95e-02` | `2.14e-05` | 1381× |
| 100 mm | 505.3 µm | `4.98e-01` | `3.04e-04` | 1634× |

**Consequence for exact tests.** A plane wave or uniform field is an
eigenfunction of the *periodic* problem. Zero-padding it introduces an
aperture edge, so the exact analytic identity legitimately stops holding. All
exact analytic tests therefore use `pad_factor=1`.

---

## 5. Power

For a mesh carrying no evanescent samples, `|H| = 1` for every sample, so by
Parseval (§3.7 eq. 18) the total power over the **periodic computational
window** is invariant:

```
P(z) = P(0)      exactly, for pad_factor = 1, all-propagating mesh      (15)
```

Measured: relative change `≤ 3.5e-16` at `z` from 1 mm to 500 mm and at
`z = −20 mm`.

With padding and cropping, power in the **cropped window** can only decrease,
because light that moved into the pad region is no longer counted:

```
P_cropped(z) ≤ P(0)                                                     (16)
```

Measured (`w₀ = 40 µm`): ratio `1.000000` at `z = 5` and `25 mm`, falling to
`0.887108` at `z = 100 mm`. This is physically correct and must **not** be
described as conservation. Pinned by `test_m26` (equality) and `test_m27`
(inequality).

---

## 6. Analytic references used in validation

### 6.1 On-grid plane wave — exact, non-paraxial

For `U(x,y,0) = A·exp(i(kx·x + ky·y))` with `(fx, fy)` landing exactly on grid
samples:

```
U(x, y, z) = A · exp(i(kx·x + ky·y)) · exp(i·kz·z)                      (17)
```

with `kz` from (5). No approximation of any kind. The amplitude is unchanged
because `|exp(i·kz·z)| = 1`.

**Measured:** worst relative error `1.93e-14` over five `(fx, fy)` sign
combinations and `z ∈ {1, 50, 200} mm`.

For a superposition, each component receives its own `kz`:

```
U(x,y,z) = Σₙ Aₙ · exp(i(kxₙ·x + kyₙ·y)) · exp(i·kzₙ·z)                 (18)
```

**Measured:** `5.21e-15` for three components of unequal amplitude at
`z = 50 mm`.

### 6.2 Uniform field

The `kx = ky = 0` case of (17), where `kz = k`:

```
U(x, y, z) = U₀ · exp(i·k·z)                                            (19)
```

**Measured** error against `k·z·ε`, the float64 rounding floor of the angle
itself:

| `z` | `k·z` (rad) | error | `k·z·ε` | ratio |
|---|---|---|---|---|
| 0.1 mm | `9.926e+02` | `1.14e-13` | `2.20e-13` | 0.52 |
| 1 mm | `9.926e+03` | `1.82e-12` | `2.20e-12` | 0.83 |
| 10 mm | `9.926e+04` | `1.46e-11` | `2.20e-11` | 0.66 |
| 100 mm | `9.926e+05` | `1.16e-10` | `2.20e-10` | 0.53 |

The error tracks `k·z·ε` to within a factor of 2 at every distance, confirming
that the limit is the representation of the *angle*, not the propagator. Test
tolerances therefore scale as `100·k·z·ε`.

### 6.3 Gaussian beam — independent, but paraxial

Used as the one independent analytic reference with genuine transverse
structure. With `r² = x² + y²`:

```
z_R  = π·w₀² / λ                              Rayleigh range         [m]  (20)
w(z) = w₀·√( 1 + (z/z_R)² )                   beam radius            [m]  (21)
R(z) = z·( 1 + (z_R/z)² )                     wavefront curvature    [m]  (22)
ψ(z) = arctan( z / z_R )                      Gouy phase           [rad]  (23)

U(r,z) = (w₀/w(z)) · exp( −r²/w(z)² )
         · exp( +i·[ k·z + k·r²/(2·R(z)) − ψ(z) ] )                       (24)
```

**Sign choices under our `exp(−iωt)` convention** (§3.1) — all three flip
under the opposite convention, giving the complex conjugate of (24):

| Term | Sign | Meaning |
|---|---|---|
| `+k·z` | positive | The longitudinal carrier **advances** with distance, matching the plane-wave factor `exp(+i·k·z)` of (19) |
| `+k·r²/(2R)` | positive | A diverging beam (`R > 0` for `z > 0`) has a wavefront that lags on axis relative to the edge |
| `−ψ(z)` | **negative** | The Gouy phase is **subtracted** — the beam is retarded relative to a plane wave, by a total of `π` across the focus |

**This comparison's floor is the paraxial approximation, not float64.** The
Angular Spectrum Method is exact and non-paraxial; (24) is a paraxial solution
of the same problem. They differ by `O((λ/(π·w₀))²)`, which for `w₀ = 100 µm`
at `λ = 633 nm` is `4.06e-06`.

**Measured** (`w₀ = 100 µm`, 512², 4 µm pitch, `pad_factor=2`):

| `z / z_R` | `z` | `w(z)` | complex relative error |
|---|---|---|---|
| 0.5 | 24.82 mm | 111.80 µm | `8.12e-07` |
| 1.0 | 49.63 mm | 141.42 µm | `1.02e-06` |
| 2.0 | 99.26 mm | 223.61 µm | `1.01e-06` |

Consistent with the `4.06e-06` estimate and about eight orders of magnitude
above the float64 floor of the plane-wave tests. **The `rtol=1e-4` used in
`test_a09` must not be tightened toward machine precision** — that would be
fitting the test to the wrong physical model.

Two sharper consequences of (24) are tested separately:

- **Gouy phase.** The on-axis phase is `k·z − ψ(z)`, so at `z = z_R` the beam
  lags a plane wave by exactly `π/4`. **Measured: `0.785398` rad, error
  `4.0e-11`.** This is a sign-sensitive test of a subtle effect no plane wave
  can reach.
- **Peak intensity.** `I(0,z)/I(0,0) = (w₀/w(z))²`, energy conservation
  expressed pointwise.

---

## 7. Assumptions and approximations

Milestone 0's list (A1–A10) still holds. Additions:

| # | Assumption | Where | Consequence if violated |
|---|---|---|---|
| A11 | Source and destination planes are parallel and share the same grid | (1)–(3) | ASM requires it; a different pitch or size at the destination is not representable |
| A12 | The medium is source-free and homogeneous for `0 < z' < z` | (5) | No propagation through a scattering or graded medium |
| A13 | Only forward-travelling components are retained | branch of (5) | Back-scattering is not modelled |
| A14 | Field periodicity (`p=1`) or zero-embedding (`p>1`) as the boundary condition | §4.2 | Wrap-around, or an artificial aperture |
| A15 | Transfer function assumed adequately sampled | — | Undersampled `H` at long range is not detected |
| A16 | Gaussian reference is paraxial | (24) | Sets the ~`4e-6` comparison floor |

**Not assumed anywhere:** any Fresnel or Fraunhofer approximation, any
small-angle approximation, any thin-element approximation. Equations (4), (5)
and (17) are exact.
