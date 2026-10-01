# Mathematical and Numerical Conventions

**Status:** normative. Code must match this document. If they disagree, that is
a bug. Changing a convention requires updating this file, the affected code,
the affected tests, and adding a Change Log entry at the bottom — in the same
change.

**Version:** 0.10 — 2026-10-01

---

## 1. Physical model and scope

Everything in this repository assumes:

| Assumption | Meaning | Consequence if violated |
|---|---|---|
| **Scalar** | Light is one complex number per point; polarization ignored | Wrong for high-NA systems and polarizing elements |
| **Monochromatic** | Exactly one wavelength; fully coherent | No white light, no partial coherence, no RGB |
| **Homogeneous medium** | Refractive index `n = 1` everywhere, constant | No lenses-as-media, no aberrating materials |
| **Parallel planes** | Fields live on flat planes perpendicular to the optical axis `z` | No tilted planes, no curved surfaces |
| **Same sampling on both planes** | Source and destination share `(Ny, Nx, dy, dx)` | Required by the Angular Spectrum Method; not required by Fresnel/Fraunhofer |
| **Linear, time-invariant** | Fields superpose | No nonlinear optics |

The refractive index is fixed at `n = 1` in version 0.1. It is **not** a free
parameter and does not appear in any function signature. Introducing it later
is a convention change requiring a Change Log entry.

---

## 2. Units

**All quantities stored, passed, or returned by the numerical core are in SI
base units.** No micrometres, no nanometres, no millimetres anywhere in the
core.

| Quantity | Symbol | Unit | Typical value |
|---|---|---|---|
| Wavelength (in vacuum) | `λ` | metre, m | `633e-9` |
| Pixel pitch | `dx`, `dy` | metre, m | `3.74e-6` |
| Propagation distance | `z` | metre, m | `0.20` |
| Transverse coordinate | `x`, `y` | metre, m | — |
| Spatial frequency | `fx`, `fy` | cycles per metre, m⁻¹ | — |
| Angular spatial frequency | `kx`, `ky` | radian per metre, rad·m⁻¹ | — |
| Wavenumber | `k = 2π/λ` | radian per metre, rad·m⁻¹ | `9.93e6` |
| Phase | `φ` | radian (dimensionless) | — |
| Amplitude | `A` | arbitrary units (a.u.) | — |
| Intensity | `I` | arbitrary units (a.u.) | — |
| Optical power | `P` | a.u.·m² | — |

Human-facing layers (CLI, config files, UI) **may** accept other units, but
**must** convert to SI at the boundary. `ohlab.units` provides multipliers
(`NM`, `UM`, `MM`, `CM`, `DEG`) for readability, e.g.
`wavelength_m = 633 * NM`.

### 2.1 Intensity normalization (explicit)

Physically, irradiance is `I_phys = ½·ε₀·c·n·|U|²` in W/m². **We drop the
constant `½ε₀cn` and define**

    I ≡ |U|²

*Justification:* a shared arbitrary intensity scale suffices for these
simulations. Ratios such as intensity NMSE, regional power fraction and CV
cancel a common positive intensity factor. PSNR is invariant only when its
explicit `data_range` is scaled by that same factor. Raw intensity MSE has
squared-intensity units and changes by the square of the factor; optical
power and displayed intensity values also retain their declared scale.
This clarification adds M4's raw MSE without changing field normalization.

*Consequence:* intensities are comparable **within** a run, and between runs
using the same normalization, but are **not** absolute radiometric quantities.
Do not report them in W/m².

Optical power over the window is the area integral, discretized as

    P = Σ_ij I[i,j] · dx · dy        [a.u.·m²]

---

## 3. Conventions

### 3.1 Time convention and the sign of the exponent

The physical real field is recovered as

    E(x, y, t) = Re{ U(x, y) · exp(−i·ω·t) }

**We use the `exp(−iωt)` time convention.**

**External verification (v0.3).** This convention, together with the
forward-propagation sign of §3.9, was independently checked against
Konijnenberg, Adam & Urbach, *BSc Optics* (TU Delft), §6.3 "Angular Spectrum
Method", which states that its time dependence is `e^(−iωt)` with `ω > 0`,
gives the propagator as `e^(+i·k_z·z)`, defines
`k_z = √((2π/λ)² − k_x² − k_y²)`, and selects the `+` branch of the square
root. All four items match this document exactly.

Goodman's *Introduction to Fourier Optics* is the usual citation for this
convention and is believed to agree, but **it has not been checked directly**
and is recorded here as a secondary, unverified attribution.

Note on terminology: `exp(−iωt)` is commonly called the *physicists'*
convention and `exp(+iωt)` the *engineering* convention. Version 0.1 of this
document labelled ours "engineering", which was wrong; the label is corrected
here. The mathematics is unchanged.

Direct consequences, all of which follow from this one choice:

- A plane wave travelling in the **+z** direction is `exp(+i·k·z)`.
- **Forward propagation multiplies the angular spectrum by `exp(+i·kz·Δz)`.**
- A converging lens applies `exp(−i·k·r²/(2f))` for focal length `f > 0`.
- A greater optical path length means a **more positive** phase.
- Evanescent waves **decay** as `exp(−|kz|·Δz)` for `Δz > 0`. Any
  implementation producing exponential *growth* has a sign error.

The opposite convention (`exp(+iωt)`, common in electrical engineering) flips
the sign of every phase in the codebase. **Do not mix them.** A field computed
under one convention is the complex conjugate of the same field under the
other.

**On NumPy's role.** `numpy.fft` fixes only the *discrete Fourier transform
kernel* used by `fft2` (§3.6). It does **not** fix the time-harmonic
convention — that is a physical modelling choice made here. What matters is
that the three choices form a mutually consistent set:

| Choice | Value | Where |
|---|---|---|
| Time dependence | `exp(−iωt)` | §3.1 |
| Forward Fourier kernel | `exp(−i2π(f·r))` | §3.6 |
| Forward propagation | `exp(+i·kz·z)` | §3.9 |

These are the project's selected conventions; they remain unchanged. The time
convention fixes which longitudinal phase describes forward travel. The sign
of the Fourier **analysis/synthesis pair** is a separate representational
choice, provided the inverse kernel and transverse-wavevector interpretation
are consistent (§3.6). It need not flip when the time convention changes.
NumPy does not impose a time convention. `test_c04` pins the selected Fourier
kernel; `test_a02`/`test_a05`/`test_a06` independently check propagation signs.

### 3.2 Complex field

    U(x, y) = A(x, y) · exp( i·φ(x, y) )

| Quantity | Definition | NumPy | Range |
|---|---|---|---|
| Amplitude | `A = \|U\|` | `np.abs(U)` | `[0, ∞)` |
| Phase | `φ = arg(U)` | `np.angle(U)`, then replace exactly `−π` by `+π` | `(−π, +π]` |
| Intensity | `I = \|U\|² = U·conj(U)` | `np.abs(U)**2` | `[0, ∞)` |

**Phase wrapping.** Phase is only ever defined modulo 2π. The canonical branch
in this repository is the half-open interval **`(−π, +π]`**. Any function
returning a phase **must** return it on this branch unless its name says
otherwise (e.g. a future `unwrapped_phase`). Raw `np.angle` can return `−π`
for a negative-real value with a negative signed-zero imaginary component.
`ComplexField.phase` therefore computes `np.angle(U)` and changes only outputs
**exactly equal to `−π`** into `+π`. Nearby representable angles are unchanged;
there is no tolerance-based remapping, broad modulo operation, or unwrapping.
The returned array remains `float64` with the field's shape; the stored
`complex128` array, including its signed-zero bits, is never mutated.

**Phase of zero amplitude is undefined.** Ordinary `0+0j` still yields `0.0`.
Other signed-zero combinations follow NumPy, subject to the same exact endpoint
rule: for example, `complex(-0.0, -0.0)` has raw angle `−π` and canonical output
`+π`. That representation change has no physical phase meaning. Code must not
attach meaning to the phase where the amplitude is zero (or within machine
epsilon of zero).

### 3.3 Array layout

    field.data.shape == (Ny, Nx)
    field.data.dtype == np.complex128      (always; real input is promoted)

    axis 0 = row index i → y direction
    axis 1 = col index j → x direction

    field.data[i, j] is U at spatial position (x[j], y[i])

`Ny` precedes `Nx` in every shape tuple, matching `(rows, columns)` and image
conventions. Grid parameters are nevertheless always *named* explicitly
(`ny=`, `nx=`, `dy=`, `dx=`) and never passed positionally as a bare tuple.

### 3.4 Spatial coordinate grid

    x[j] = (j − Nx//2) · dx        j = 0 … Nx−1
    y[i] = (i − Ny//2) · dy        i = 0 … Ny−1

(`//` is floor division.) Therefore `x[Nx//2] == 0.0` and `y[Ny//2] == 0.0`
**exactly**, for both even and odd `N`. Index `N//2` is "the centre" in every
array in this project, in both the space and the frequency domain.

For even `N` the grid is asymmetric by one sample: it spans
`[−(N/2)·dx, +(N/2 − 1)·dx]`. This is accepted deliberately, in exchange for
exact index alignment with `np.fft.fftshift(np.fft.fftfreq(...))` (§3.8).

**Extent:** `Lx = Nx·dx`, `Ly = Ny·dy`. Note that
`Lx = x[-1] − x[0] + dx` — the extent counts each sample's full cell, not just
the distance between the first and last sample centres.

**2D grids:** `X, Y = np.meshgrid(x, y, indexing='xy')`, giving
`X.shape == Y.shape == (Ny, Nx)`, with `X` varying along axis 1 and `Y` along
axis 0.

**Return order of `SamplingGrid.meshgrid()`.** The method returns
`(x_grid, y_grid)` — matching `numpy.meshgrid`'s own convention, **not** axis
order. Likewise `freq_meshgrid()` returns `(fx_grid, fy_grid)`. Array *shapes*
are `(Ny, Nx)` (rows first, §3.3); the *return tuple* is x-then-y. These two
orders are different things and both are deliberate.

### 3.5 Vertical axis direction

`y` **increases with row index `i`**. When displayed with
`plt.imshow(img, origin='upper')` — the matplotlib default — array row 0 is at
the top of the screen, so **the +y axis points downward on screen**.

This makes the displayed `(x, y)` pair left-handed relative to textbook axes.
It is chosen so that the array, the coordinate grid, and the displayed image
all agree with no flipping anywhere.

*Impact:* none on any quantity depending only on `kx² + ky²` — this includes
the Angular Spectrum transfer function and all Milestone 0–3 work. It **does**
flip the sign of any signed vertical quantity: a tilt/prism phase ramp, an
off-axis carrier, or the topological charge of an optical vortex. Any such
feature must state its sign convention against this definition and be tested
for it.

### 3.6 Fourier transform convention

Continuous forward (analysis) and inverse (synthesis) transforms:

    A(fx, fy) = ∬ U(x, y) · exp( −i·2π·(fx·x + fy·y) ) dx dy
    U(x, y)   = ∬ A(fx, fy) · exp( +i·2π·(fx·x + fy·y) ) dfx dfy

Note the **`−i` in the forward transform**, which matches the kernel of
`numpy.fft.fft2`. This pairing is deliberate: it means each component of the
inverse transform is a plane wave `exp(+i·(kx·x + ky·y))`, which combined with
the `exp(+i·kz·z)` of §3.1 gives a physically forward-travelling plane wave
`exp(i·(kx·x + ky·y + kz·z))`.

**The selected signs are consistent, but the Fourier pair is not forced by
the time convention.** More generally, for an analysis-kernel sign
`s ∈ {−1, +1}`:

    A_s(f) = ∬ U(r) · exp(s·i·2π·f·r) dr
    U(r)   = ∬ A_s(f) · exp(−s·i·2π·f·r) df

The synthesis wave then has transverse wavevector `k_perp = −s·2π·f` when
written as `exp(+i·k_perp·r)`. Both transform pairs describe the same field;
the opposite analysis sign relabels the spectrum by `f → −f`. This does not
change the time dependence or force a longitudinal propagation-sign change.
The project keeps `s = −1`, hence `kx = 2πfx`, `ky = 2πfy`, and all production
FFT calls unchanged. C-09/C-10 check both sign pairs against independent sums;
they do not introduce an alternate production convention.

`fx` and `fy` are in **cycles per metre**. The angular versions are
`kx = 2π·fx` and `ky = 2π·fy`, in rad/m. Names must make clear which is meant:
`fx_*` for cycles/m, `kx_*` for rad/m. Never use `k` for a cyclic frequency.

### 3.7 Discrete transform, normalization, and Parseval

We use `numpy.fft` with its **default `norm="backward"`**: the forward
transform `np.fft.fft2` applies no scale factor, and `np.fft.ifft2` applies the
full `1/(Ny·Nx)`.

Consequence — Parseval's theorem in the form that actually holds for this
normalization:

    Σ_ij |u[i,j]|²  =  (1 / (Ny·Nx)) · Σ_lm |np.fft.fft2(u)[l,m]|²

Any energy-conservation test must use this exact form.

**Physical spectrum vs. DFT output.** The array's first sample is at
`x0 = −(Nx//2)·dx`, `y0 = −(Ny//2)·dy`, not at `(0,0)`. At FFT-ordered
frequencies define the physical-coordinate rectangular sum `A_d`:

    A(fx[m], fy[l]) ≈ A_d[l,m]
    A_d[l,m] = dx·dy · Σ_ij U[i,j] · exp(−i·2π·(fx[m]·x[j] + fy[l]·y[i]))

Insert `x[j] = x0 + j·dx`, `y[i] = y0 + i·dy`. The origin-dependent part is
constant within each sum, and the remaining kernel is NumPy's index-based DFT:

    D = np.fft.fft2(U)
    C[l,m] = exp(−i·2π·(fx[m]·x0 + fy[l]·y0))
    A_d = dx·dy · C · D

Thus both **sample area and origin phase** are required. Equivalently,
`A_d = dx·dy·fft2(ifftshift(U))`, with the result in FFT frequency order.
This equivalence holds at both parities under the §3.4 origin rule. `A_d` has
units a.u.·m²; `D` contains raw DFT coefficients. The sum is exactly defined;
its approximation to a continuous integral still depends on sampling and the
finite window. C-09 uses independent physical-coordinate sums and a center
impulse to check the formula, without deriving its reference from an FFT.

The inverse sum uses `Δfx·Δfy = 1/(Nx·Ny·dx·dy)` and the opposite kernel:

    U[i,j] = Δfx·Δfy · Σ_lm A_d[l,m] · exp(+i·2π·(fx[m]·x[j] + fy[l]·y[i]))
           = IFFT2{ A_d / (dx·dy·C) }[i,j]

For **same-grid** ASM, multiplication by `H` is pointwise on this same
frequency mesh, so the factors cancel algebraically:

    U_z = IFFT2{ (H · dx·dy·C·FFT2(U_0)) / (dx·dy·C) }
        = IFFT2{ H · FFT2(U_0) }

This is why production propagation needs neither new shifts nor explicit area
or origin factors. C-11 compares it with direct physical-coordinate analysis
and synthesis for the same sampled `H`; it isolates this cancellation, not
the physical accuracy of `H`. Any future physical-spectrum export must include
the area and origin factors and state its frequency ordering.

### 3.8 Frequency grids and array ordering

Two orderings are used. **Mixing them is the most common failure mode in this
kind of code, so the ordering is always part of the name.**

| Ordering | Value at index 0 | Zero frequency at | Produced by | Used for |
|---|---|---|---|---|
| `*_fft` | `0` | index `0` | `np.fft.fftfreq(n, d)` | propagation math |
| `*_centered` | most negative | index `n//2` | `fftshift(fftfreq(n, d))` | display, tests |

Definitions (centered form; the `_fft` form is the `ifftshift` of it):

    fx_centered[m] = (m − Nx//2) · (1 / (Nx · dx))        [cycles/m]
    fy_centered[l] = (l − Ny//2) · (1 / (Ny · dy))        [cycles/m]

#### 3.8.1 Required evaluation order (v0.2)

**The expression above must be evaluated as written: compute the reciprocal
`1 / (N·d)` once, then multiply by the integer offset. Do not write it as the
division `(m − N//2) / (N·d)`.**

The two forms are mathematically identical. They are *not* numerically
identical. `numpy.fft.fftfreq` computes `val = 1.0 / (n * d)` once and then
multiplies an integer array by `val`; writing a division instead reassociates
the floating-point operations and differs by roughly one unit in the last
place.

This project guarantees bit-for-bit agreement between `SamplingGrid.fx_fft`
and `numpy.fft.fftfreq`, so the reciprocal-multiply form is mandatory.

Measured discrepancy of the division form against `fftshift(fftfreq(...))`
(NumPy 2.4.6):

| `n` | `d` | bit-identical? | max abs diff | max rel diff |
|---|---|---|---|---|
| 8 | 1.0 | yes | — | — |
| 7 | 3.74e-6 | yes | — | — |
| 1024 | 6.4e-6 | yes | — | — |
| **512** | **3.74e-6** | **no** | `2.910e-11` | `2.177e-16` |
| **480** | **8e-6** | **no** | `7.276e-12` | `1.164e-16` |

Note that the discrepancy vanishes at `d = 1.0` and at some size/pitch
combinations. Any test of this property must therefore be parametrized over a
**realistic** pitch; a round-number-only test passes under the wrong
implementation. Verified by
`tests/test_grid.py::test_g10_fft_ordered_axis_matches_numpy_bit_for_bit`,
which was confirmed against a deliberately mutated implementation.

This subsection specifies floating-point evaluation order only. **No
mathematical convention is changed by v0.2.**

**Nyquist frequency:** `f_nyq_x = 1/(2·dx)`. For even `Nx`, `fx_centered[0]`
equals exactly `−f_nyq_x`, and the maximum value is `+f_nyq_x − 1/(Nx·dx)`.
The positive Nyquist frequency itself is not a sample.

**Maximum representable diffraction angle:**

    sin(θ_max) = λ · f_nyq = λ / (2·dx)

Spatial frequencies beyond this alias. This is a hard limit of the sampling,
not of any algorithm.

**Implicit periodicity.** The DFT treats the field as periodic with period
`(Ly, Lx)`. Light diffracting past the window edge **wraps around** to the
opposite edge instead of leaving. Zero-padding is implemented in Milestone 1
and is specified in §3.9.4; band-limiting is deferred.

### 3.9 Angular Spectrum Method — transfer function

*Implemented in Milestone 1 as `ohlab.propagation`.*

Propagation by distance `z` through a homogeneous medium (`n = 1`):

    1.  A      = FFT2{ U_source }
    2.  A'     = A · H(fx, fy; z)
    3.  U_dest = IFFT2{ A' }

#### 3.9.1 One expression for all distances

**The transfer function is written once, and only once:**

    H(fx, fy; z) = exp( +i · kz · z )        kz = 2π·√( 1/λ² − fx² − fy² )

with the **principal complex square root**, i.e. the branch satisfying
**`Im{kz} ≥ 0`**. Equivalently `kz = √(k² − kx² − ky²)` with `k = 2π/λ`.

This single mathematical expression covers propagating and evanescent samples
and **both signs of `z`**. For **real `kz`**, including the grazing value zero,
`H(−z) = conj(H(z))`. This identity does not hold for evanescent samples:
if `kz = i·κ`, `κ > 0`, and `z > 0`, then `H(z) = exp(−κz)` while
`H(−z) = exp(+κz)`, not `conj(H(z))`. The formula describes growth in that
inverse direction; the public API refuses backward propagation whenever the
computational mesh contains evanescent samples (§3.9.3). The existing forward
decay and backward-rejection policies are unchanged.

**Do not write a separate expression for negative `z`.** A second formula such
as `exp(−i·|kz|·z)` is easy to misread and easy to sign incorrectly, and there
is no need for it. Versions 0.1–0.2 presented `H` as a two-branch piecewise
definition; that presentation is **withdrawn** in favour of the single
expression above, which is what the code implements. The mathematics is
identical — the piecewise form is reproduced below only to show the
correspondence:

                   ┌ exp( +i·2π·z·√( 1/λ² − fx² − fy² ) )   if fx² + fy² <  1/λ²   (propagating)
    H(fx,fy;z) =  ─┤
                   └ exp( −2π·z·√( fx² + fy² − 1/λ² ) )     if fx² + fy² ≥ 1/λ²   (evanescent)

In code the single expression is one line with no branch logic: casting the
radicand to `complex128` before `np.sqrt` selects the required branch
automatically.

| Regime | Condition | `kz` | `\|H\|` for `z > 0` |
|---|---|---|---|
| Propagating | `fx² + fy² < 1/λ²` | real, `> 0` | 1 |
| Grazing | `fx² + fy² = 1/λ²` | 0 | 1 |
| Evanescent | `fx² + fy² > 1/λ²` | purely imaginary, `Im > 0` | `< 1`, decaying |

**Sign check:** for `z > 0`, `|H| ≤ 1` everywhere. `|H| > 1` anywhere means the
square-root branch is wrong.

**`|H| = 1` is a mathematical statement, not a bitwise one.** The measured
worst-case deviation of `abs(exp(i·θ))` from 1 is `2.220e-16` — exactly one
float64 epsilon. Tests must use an explicit machine-precision tolerance, never
an exact comparison.

`H` is evaluated on the **`_fft`-ordered** frequency grids, so no `fftshift` of
a full-size array is needed in the propagation hot path.

#### 3.9.2 Determining whether a grid carries evanescent samples

**Use the actual discrete frequency mesh. There is no valid scalar pitch
threshold.**

    evanescent(grid) := any( fx_fft² + fy_fft² > 1/λ² )   over the 2-D mesh

The tempting shortcut `d < λ/2` is **wrong**: that is the condition for the
frequency *axis* to reach the cutoff. The extreme sample of a square grid is
the **corner** of the Nyquist square, at radius `√2/(2d)`, so evanescent
samples first appear at

    d < λ/√2      (≈ 447.6 nm at λ = 633 nm)

not at `d < λ/2` (≈ 316.5 nm). **Between those two pitches the evanescent
region is populated only near the four corners of the mesh** — 97 samples of
4096 at `d = 400 nm`, with neither axis reaching the cutoff. For an anisotropic
grid there is no single `d` and no scalar threshold exists at all.

Pinned by `test_m08_evanescent_detection_uses_the_discrete_mesh_not_a_pitch_rule`.

#### 3.9.3 Evanescent policy

| Case | Behaviour |
|---|---|
| `z > 0`, evanescent samples present | Computed normally; they decay, underflowing silently to `0.0` |
| `z = 0` | `H ≡ 1 + 0j` exactly |
| `z < 0`, **no** evanescent samples on the mesh | Allowed. This is every realistic configuration |
| `z < 0`, evanescent samples present | **`ValueError`** |

Backward propagation of evanescent components is an ill-posed inverse problem:
it amplifies arbitrarily small numerical noise, reaching `4×10⁸` after one
micrometre and overflowing to `inf` within a hundred on a sub-wavelength grid.
Zeroing those samples would misreport what was computed; clamping would invent
a number with no physical meaning. The request is refused instead.

#### 3.9.4 Boundary conditions: the periodic window and zero padding

The DFT treats the field as periodic with period `(Ly, Lx)`, so light
diffracting past an edge **re-enters from the opposite edge**. Two boundary
conditions are available, and neither is universally correct:

| `pad_factor` | Boundary condition |
|---|---|
| `1` | The original **periodic** DFT window. Circular wrap-around occurs |
| `> 1` | The field is embedded in a larger **zero-valued** window, then the result is cropped back |

Padding **reduces** circular wrap-around; it is **not** a guarantee of physical
correctness. Once light reaches the edge of the padded window it wraps again,
and embedding a field that fills its window imposes a hard aperture that the
periodic problem did not have. Measured against an analytic Gaussian at
`z = 100 mm`: `pad_factor=1` gives relative error `4.98e-01`, `pad_factor=2`
gives `3.04e-04`.

**Consequence for exact tests:** a plane wave or a uniform field is an
eigenfunction of the *periodic* problem, not of the zero-embedded one. Tests
asserting an exact analytic identity must use `pad_factor=1`.

**Padding alignment.** Padding must preserve the §3.4 origin convention. For
each axis:

    pad_before = N_padded//2 − N//2
    pad_after  = N_padded − N − pad_before

so that original index `N//2` maps to padded index `N_padded//2`, and every
physical coordinate is preserved **bit-exactly** at both parities. Cropping is
the exact inverse. `numpy.pad`'s default placement is deliberately **not**
used: it would define the physical alignment implicitly and disagrees with this
rule for odd sizes.

#### 3.9.5 Deferred: band-limited ASM

The transfer function itself becomes undersampled at long range, which motivates
the band-limited ASM of Matsushima & Shimobaba (*Opt. Express* **17**, 19662,
2009). It is **not implemented**; see
`docs/handoffs/milestone_1/known_limitations.md` for the measured evidence
behind that decision.

### 3.10 Determinism

Any function using randomness **must** accept an explicit `seed: int` or an
`np.random.Generator`, and **must** construct its generator via
`np.random.default_rng(seed)`. **The legacy global `np.random.*` API is
forbidden in `src/`.** Replay must specify its captured inputs, execution
environment and comparison criterion. M5 distinguishes exact saved-file
integrity, source/environment qualification and measured numerical replay
(§3.15). Same-version metadata is necessary under that qualification policy,
not a universal guarantee across machines, library builds or FFT backends.
The shipped replay criterion is bit identity with no tolerance fallback.

### 3.11 Floating-point precision

The core computes in `complex128` / `float64`. Exported image files may be
lower precision, but that conversion happens only in `ohlab.io`, is lossy, and
must be documented at the point of export. Never round-trip a phase map
through `uint8` inside the core.

---

### 3.12 Design target intensity and amplitude

A target grayscale code `g` is an intensity specification, with the fixed
mapping

    I_target[i,j] = float64(g[i,j]) / 255
    A_target[i,j] = sqrt(I_target[i,j])

These normalized design values lie in `[0, 1]`. They use the same amplitude-
squared intensity relation as §2.1, but do not supply a physical radiometric
calibration or a phase. In particular, code 128 means intensity
`128/255 ≈ 0.501961` and amplitude `≈ 0.708492`; it does not mean amplitude
`128/255`. A target amplitude alone is neither a `ComplexField` nor an SLM
phase pattern. No target phase is inferred or assigned.

`ohlab.targets.grayscale8_to_intensity(grayscale, *, grid)` accepts only a
plain two-dimensional `uint8` ndarray. `intensity_to_amplitude(intensity, *,
grid)` accepts only a plain native `float64` ndarray with finite values in
`[0, 1]`. Array subclasses, masked arrays, array-like objects, implicit dtype
conversions and non-native float storage are rejected. Both require
`shape == grid.shape == (ny, nx)` and return fresh, writable, C-contiguous
native `float64` arrays. They preserve input storage and grid parameters.
Invalid type/dtype raises `TypeError`; invalid dimensions, shape, finiteness
or range raises `ValueError`.

Pixel `[i, j]` remains at `(grid.x[j], grid.y[i])` under §3.4, with `+y`
downward. There is no resize, interpolation, crop, pad, axis transpose,
orientation correction or pitch inference from image metadata. There is no
gamma/profile conversion, threshold, clipping, contrast stretch, per-image
peak normalization or power normalization. Equal codes retain equal
intensities across different images. All-zero targets are valid and remain
zero; a later algorithm must separately define any nonzero-power requirement.

The optional boundary `ohlab.io.images.load_target_intensity(path, *, grid)`
accepts actual PNG content independently of extension, with source bit depth
8, grayscale color type 0, decoded mode `L`, no transparency and no APNG
metadata (including single-frame APNG). It checks the fixed IHDR dimensions
against the grid before full pixel decoding or target allocation, verifies
integrity, reopens for decoding, and rechecks decoded shape. Pillow's size
and malformed/truncated-image protections remain enabled. Metadata such as
gamma, ICC, DPI and EXIF never changes the returned raster or its grid.
This strict boundary is not an exhaustive validator for all malformed PNGs.

M2 validation uses independent 80-digit Decimal references for all 256 codes:
`rtol=2e-15, atol=0` for intensity/amplitude and `rtol=5e-15, atol=0` for
`A_target**2 == I_target`. Zero endpoints are exact; nonzero encoded intensity
is at least `1/255`. Measured errors and the scope of these bounds are in the
[M2 evidence](handoffs/milestone_2/tests_and_evidence.md). Existing propagation,
sampling and boundary-condition limitations in §3.9 are unchanged.

---

### 3.13 Single-plane phase-only Gerchberg–Saxton synthesis

M3 uses one complete fixed grid and constrains every source and target pixel.
There is no embedding, cropping, or free exterior region. The forward operator
is the existing ASM expression with `pad_factor=1`:

    P_z(U) = IFFT2(FFT2(U) * H_z),  H_z = exp(+i*kz*z).

The entire discrete frequency mesh must have real `kz`, including grazing
zero. A mesh with any evanescent samples is rejected even for `z=0` or zero
iterations. Existing M1 implementation, signs and default padding are unchanged.
This is a **discrete periodic synthesis model**, not a validation of arbitrary
isolated finite-aperture optics or a general sampling-adequacy guarantee.

#### 3.13.1 Inverse, adjoint and power

On this lossless complete grid, `|H_z|=1` mathematically, so

    P_z^(-1) = P_z^* = P_(-z).

The adjoint is with respect to `sum(conj(u)*v)*dx*dy`; the common pixel area
does not change the adjoint. Forward propagation `P_z` is generally neither
its own adjoint nor its own inverse. For the embedded/cropped operator
`E^* P_z E`, distance reversal can give the adjoint but is generally not the
inverse: cropping discards information. That operator is not the M3 model.

For prescribed real amplitudes `A_s` and `A_t`, define

    S_s = sum(A_s**2),  S_t = sum(A_t**2),  P = S*dx*dy.
    abs(S_s - S_t) <= 1e-12 * max(S_s, S_t).

This symmetric power-compatibility test has **absolute tolerance zero**.
Energies and physical powers must be positive, finite and numerically usable
in float64. Zero power, overflow, underflow that makes the derived arithmetic
unusable, and nonfinite propagation/residual arithmetic raise informative
errors. There is no silent rescaling or clipping. Equal power is necessary,
not sufficient, for exact synthesis. M2's blank-image acceptance is unchanged.

M3 also checks that the public transfer formula's sequential float64 radicand
`(1/lambda)**2 - fx**2 - fy**2` is nonnegative. At the cutoff, rounding can
make it negative even when the summed-frequency domain comparison passes.
Such a geometry cannot represent the chosen lossless model and is rejected,
including identity requests; it is not clamped to grazing zero. This is domain
validation only, with no second production kz or transfer-function calculation.
NumPy-reported underflow is treated as unusable arithmetic, including
precision-losing tiny/subnormal intermediates even if a total remains positive.

#### 3.13.2 Inputs and initialization

Both amplitudes are plain native `float64` ndarrays, exactly `grid.shape`,
finite and nonnegative; there is no upper bound of one. Supplied phase is a
plain native `float64` array of the same shape and finite radians on any
branch. Read-only and noncontiguous arrays are accepted via owned copies;
input bytes and the grid are preserved. Array-like objects, subclasses,
implicit dtype conversion and non-native storage are rejected.

Wavelength is finite positive metres; distance is finite signed metres.
Iterations is an integer at least zero; seed is an integer at least zero;
booleans are rejected. Exactly one of seed or initial phase is required.
Seeded initialization uses `default_rng(seed).uniform(-pi, pi, grid.shape)`.
The initial field is `U_0=A_s*exp(i*phi_0)`.

Wrong types/dtypes raise `TypeError`; invalid shapes, domains, initialization
choices, incompatible power and unusable derived arithmetic raise `ValueError`.

#### 3.13.3 Projection cycle and returned iterate

Define `theta(w)` as the canonical phase in `(-pi,+pi]`, with **zero radians at
exact complex zero**. Only the exact `-pi` endpoint is mapped to `+pi`; there
is no near-zero cutoff. This tie rule is local to M3 and does not change the
existing `ComplexField.phase` signed-zero contract.

For `k=0,...,N-1`:

    V_k = P_z(U_k)
    rho_k = sum((abs(V_k)-A_t)**2) / S_t
    V'_k = A_t * exp(i*theta(V_k))
    W_k = P_(-z)(V'_k)
    U_(k+1) = A_s * exp(i*theta(W_k))

Finally evaluate `V_N=P_z(U_N)` and `rho_N`. Residuals are evaluated **before**
target-amplitude replacement. Return the **last** `U_N`, its actual unmodified
`V_N`, and all `N+1` residuals indexed zero through `N`. There are `N+1`
forward and `N` inverse applications, with both public transfer functions
computed once per solve. Local FFT application keeps §3.7 normalization.
No best-iterate substitution, early stopping, or generic convergence flag
is provided. Finite fixture improvement does not promise arbitrary convergence.

At `N=0`, return initialization and its actual reconstruction. At `z=0`,
propagation is exact identity without FFT, while the requested projection
cycles still run. In particular, a zero target pixel can reset source phase
to zero on the first cycle even if its prescribed source amplitude is positive.

`rho` is a dimensionless normalized **squared amplitude residual**, not an
intensity MSE, a fraction of pixels, diffraction efficiency or percent accuracy.
With exactly equal powers and exact arithmetic, `0 <= rho <= 2`; stored
histories are not clipped to that theoretical bound.

`GerchbergSaxtonResult` is frozen with `eq=False`. It stores `source_field`,
`reconstruction` and an owned read-only native-float64 `residual_history`.
Its `iterations` property derives `len(history)-1`; `phase` derives a fresh
writable canonical array from `source_field`, with zero on zero source support.
There is no separately stored phase that can disagree with the returned field.

---

### 3.14 Reconstruction intensity metrics

`ohlab.metrics` evaluates supplied intensity arrays. It neither changes M3's
algorithm nor replaces its normalized squared **amplitude** residual (§3.13).
In integration, use the actual `result.reconstruction.intensity` associated
with the returned source phase, before any target-amplitude replacement.

#### 3.14.1 Definitions and interpretation

Let `T` be target intensity, `R` reconstruction intensity, `N` the total pixel
count, and `M` a caller-supplied Boolean region. Both comparison inputs must
use the same declared scale and corresponding pixel locations.

    MSE_I = sum((R - T)**2) / N
    NMSE_I = sum((R - T)**2) / sum(T**2)
    PSNR_I = 20*log10(data_range) - 10*log10(MSE_I)
    signal_region_power_fraction = sum(R[M]) / sum(R)
    regional_intensity_cv = std(R[M], ddof=0) / mean(R[M])

MSE has squared-intensity units. NMSE is dimensionless squared relative
intensity error, neither NRMSE nor the M3 residual. Its target squared norm
`sum(T**2)` is **not** optical power `sum(T)*dx*dy`; the normalization is an
explicit project convention, not a universal definition of NMSE. PSNR is in
dB and uses a caller-declared finite positive intensity `data_range`. This is
not inferred from observed maxima and is not a bound on either array. The M4
example declares one for M2-normalized design intensities; reconstruction
values above one remain valid.

Common scaling `T,R -> c*T,c*R`, for positive `c`, multiplies MSE by `c**2`
and preserves NMSE. PSNR is preserved only if `data_range -> c*data_range`;
at fixed range it changes by `-20*log10(c)`. Power fraction and CV are
invariant under common positive scaling within usable float64 arithmetic.
Equal power fraction therefore does not imply correct target brightness.

The fraction denominator covers the **full supplied reconstruction window**.
Uniform pixel area cancels from numerator and denominator. A source-normalized
simulated efficiency would instead equal this fraction times
`P_destination_window/P_source`. Complete-window power conservation makes the
two equal; M3 supplies a discrete periodic lossless model, not hardware
efficiency. Measured hardware efficiency additionally needs defined incident
and collected powers, radiometric calibration, device losses and collection
apertures. M4 does not implement either additional efficiency metric.

CV uses population variance (division by selected count, `ddof=0`), not a
sample estimate. It can exceed one. Lower means less regional intensity
variation, which is a uniformity diagnostic only where flat brightness is
intended. A desired Gaussian falloff is not evidence of speckle or poor
uniformity. CV and `1-CV` are not universal quality or accuracy scores.

#### 3.14.2 Inputs, ownership and undefined cases

The five public functions are keyword-only and return built-in Python floats.
Intensities must be plain native `float64` ndarrays, nonempty and 2-D, finite
and nonnegative, with no upper-one bound. Comparison shapes must match exactly.
Masks must be plain Boolean ndarrays with exactly the intensity shape. All
intensity pixels are validated, including those outside a selected region.
Read-only and noncontiguous inputs are accepted without mutation or retention.
No array-like/subclass conversion, clipping, alignment, resizing, normalization,
mask inference, thresholding or epsilon denominator is performed.

Wrong types/dtypes raise `TypeError`; invalid shapes, values, undefined
ratios and unusable derived arithmetic raise contextual `ValueError`.
`data_range` accepts real Python/NumPy numeric scalars, excluding booleans,
and must convert to a finite positive float64-scale value.

- Zero-target MSE is valid. A zero target squared norm makes NMSE undefined,
  including zero against zero. NMSE requires a usable positive denominator
  even when the two images match.
- After validating both arrays and `data_range`, exact numerical equality
  gives PSNR `+inf`. Signed zeros compare numerically equal; raw bit identity
  is not required. No approximate-match threshold is used. Negative PSNR is
  returned unchanged. Nonidentical inputs require usable positive MSE.
- The fraction requires usable positive full-window power. Empty selection
  or a selection containing only zeros then gives zero; an all-window mask
  gives one. Zero full-window power raises even for an empty selection.
- CV requires a nonempty region and positive mean. A validated region whose
  values are all exactly equal and positive returns exact zero before any
  mean/variance reduction, including one pixel. A constant zero region raises.
  No approximate equality, clipping or variance floor is used.

#### 3.14.3 Floating-point scope

Required arithmetic uses local float64 error handling and explicit result
checks. Overflow, division errors, invalid results and NumPy-reported underflow
raise `ValueError`; caller error settings are restored on success and failure.
In particular, underflow of a nonzero squared error never becomes a perfect
match. The log-domain PSNR formula avoids forming `data_range**2` or its
ratio to MSE, but it still requires usable MSE for nonidentical inputs.

Finite input alone does not guarantee support: squares, sums, variance or
ratios can be unusable even when the mathematical metric is defined. No
rescaling or arbitrary-precision fallback is added. Exact-match PSNR and
positive-constant CV bypass unnecessary arithmetic only after validation.
Independent finite-case errors, explicit relative/absolute tolerances and
deliberate negative controls are recorded in the M4 handoff; they are not
universal numerical bounds or proof of physical reconstruction accuracy.

---

### 3.15 Configuration, artifact integrity and numerical replay

M5 is an I/O orchestration boundary over the unchanged M2, M3 and M4 APIs.
Schema v1 accepts normalized M2 target intensity in `[0,1]`, explicitly
supplied source amplitude, one M3 initialization mode, and a requested subset
of the five named M4 metrics. It does not cover arbitrary target-amplitude
scales, other algorithms, device encoding or an application interface.

#### 3.15.1 Captured scientific identity

Grid shape and SI pitches, wavelength, signed distance, exact cycle count,
the `m3_periodic_lossless_asm_v1` contract, initialization and metric parameters
are explicit. The solver contract fixes the existing complete periodic grid,
lossless ASM domain, FFT convention, zero tie, final-iterate selection and
pre-projection amplitude-residual history (§3.13). M5 changes none of them.

Validate plain native arrays, then take owned C-contiguous snapshots before
computation. Preserve dtype and logical element bits, including signed zero;
do not preserve caller strides, cast, scale or normalize. Reduction order can
depend on memory layout. Compute M4 values from the same C-order reconstruction
intensity snapshot that is persisted, making capture layout reproducible.

Store target intensity and its actual M2 square-root amplitude separately;
squaring rounded amplitude need not recover intensity bits. Store the actual
final complex source field and actual complex reconstruction, both complex128,
plus float64 phase, reconstruction intensity and the complete `N+1` residual
history. Phase/intensity are checked derived outputs. Amplitude and extracted
phase cannot generally reconstruct the exact original complex bits.

Seed initialization records the exact integer seed and environment and calls
M3 with that seed on replay. Explicit initialization stores the raw finite
radian array, with its original phase branch and bits. Do not duplicate M3's
RNG or replace seeded initialization with phase recovered from an N=0 solve.

Metric configuration preserves exact function names, explicit PSNR range and
separate Boolean fraction/CV masks when requested. Values belong to M4's
existing arithmetic contract, including an unmodified finite fraction that
rounds slightly above one; the artifact layer does not clamp it. An empty
metric request is explicit and valid. A requested undefined metric fails the
save instead of being omitted or replaced by a generic quality score.

#### 3.15.2 Serialization and integrity

Strict version-1 JSON uses UTF-8, sorted keys, fixed indentation, LF and a final
newline. Finite binary64 scalars use JSON numbers and must round-trip with
identical bits. Booleans are not numeric parameters. PSNR positive infinity
uses only the string `"+inf"` in its named value field. Reject duplicate,
missing, unknown and unsupported-version fields, nonstandard JSON constants,
nonfinite parsed numbers and undeclared nonfinite representations. RunConfig
retains immutable canonical bytes; exporting settings returns a defensive copy.

Typed arrays use NPY 1.0: C-order float64, complex128 or Boolean according to
their fixed logical roles. Check the bounded header, exact expected shape,
dtype/byte order, order and total payload length independently of manifest
claims, then load verified bytes with `allow_pickle=False`. Reject object and
structured dtypes, NPZ, unsupported versions, truncation and trailing bytes.
Loading returns owned arrays marked read-only, without hidden byte-order casts.

SHA-256 covers complete file bytes, including NPY headers, config and metrics
JSON. The manifest lists sorted, unique fixed relative filenames, byte lengths
and digests plus array metadata. It does not hash itself. Reject changed,
missing, extra or conditionally inconsistent artifacts, unsafe paths,
directories, symlinks and Windows reparse points. Verify all file hashes before
interpreting numerical artifact contents; decode those same snapshots.
Integrity is relative to the unsigned manifest, not authorship or authenticity.

An optional original PNG is copied byte-for-byte, hashed and checked against
the captured target through the strict M2 loader before publication. It is
provenance; replay uses the numerical arrays. No external original path or
original bundle directory is necessary. PNG previews are not authoritative.

#### 3.15.3 Qualification and comparisons

Record package version plus source `{revision, state, method}`. A clean exact
Git SHA matters because the development version alone is not unique. The
reusable I/O API accepts caller-supplied metadata and never invokes Git. The
example optionally detects Git from the checkout providing imported `ohlab`.
A supplied SHA is a declaration, not attestation of executing source bytes.

Required environment fields are Python implementation/full version, NumPy and
SciPy versions, conditional Pillow version when PNG decoding occurred,
platform, machine, processor, byte order, pointer width and `numpy.fft`
identifier. Package version and clean matching source revisions are required
as well. Python executable location, logical CPU count and provenance method
are informational; the last remains visible so supplied and detected claims
are distinguishable. No universal determinism follows from metadata equality.

Collect current environment independently and require separately supplied or
detected current provenance. Never copy "current" values from the saved bundle.
Dirty, unavailable or mismatched required information yields `unqualified`.
Default replay then reports numerical comparison `not_run`. Explicit
diagnostic replay may compare, but remains unqualified even if outputs match.
Foreign-endian arrays remain inspectable; the native-array core is not run
or silently fed converted arrays. Even diagnostic replay then reports
comparison `not_run`, with the failed native-byte-order gate visible.

Replay uses saved actual amplitude inputs and the original initialization
mode. Compare source field, phase, reconstruction field, reconstruction
intensity and history individually by dtype, shape and C-order bytes. Check
stored amplitude/phase/intensity derivations, recompute metrics from saved
data, and separately recompute them from the new reconstruction. Finite
metric scalars compare binary64 bits; positive-infinite PSNR is handled
separately. There is no `allclose`, automatic tolerance relaxation, substituted
seed or environment repair. Changed numerical outputs fail comparison even
when qualification fields match. Exactness is the tested property, not a
zero-roundoff assertion about the underlying optics.

#### 3.15.4 Publication and limitations

Write to an exclusively created temporary sibling. Create files exclusively,
register cleanup ownership only after creation, flush/fsync/close files, write
manifest last, validate staged contents and rename on the same filesystem.
Public readers reject reserved `.ohlab-partial-` directories; private staged
validation shares the same content checks. Refuse existing destinations.
Windows rename also rejects a destination appearing during publication; this
is not a cross-platform concurrent-writer guarantee. Preserve unrelated files
and original exceptions, and report leftover staging paths if cleanup fails.

On the tested Windows host, ordinary directory rename intermittently returned
error 5 after application handles had closed; its external cause was not
established. Retry only that error while the destination remains absent, at
most four rename attempts with 10, 30 and 100 ms waits (140 ms total explicit
waiting). Recheck destination absence after each wait. Exhaustion preserves
the first error; other errors propagate immediately. This adds no overwrite,
locking or cross-filesystem fallback, and cannot guarantee eventual success.

File fsync and rename are not a power-loss durability guarantee. Hard termination
can leave a visibly partial directory. M5 provides no signing, locks, schema
migrations, hostile concurrent-filesystem protection or universal cross-CPU/
cross-version replay. Run UUIDs identify directories, not scientific differences.
Measured evidence and remaining limits are in the M5 handoff; M0–M4 scientific
contracts and their historical measurements remain unchanged.

---

### 3.16 Editable 2D designs and deterministic rasterization

Milestone 7 adds desired-intensity authoring, not a new optical model.
`TargetDesign2D` describes dimensionless pixel/sample coordinates. Optical
lengths supplied to existing field, grid, solver and artifact APIs remain SI.
An editable drawing is neither a complex field nor an arrangement of coherent
sources, optical components or calibrated hardware.

#### 3.16.1 Versioned design and validation

The immutable model has exactly these top-level fields:

| Field | Contract |
|---|---|
| `schema_version` | Built-in integer `1` |
| `rasterizer_version` | `"center_sample_overwrite_v1"` |
| `coordinate_system` | `"centered_pixels_y_down_v1"` |
| `canvas` | Exactly `ny`, `nx`, built-in integers in `[1,512]` |
| `background_intensity` | Finite binary64 intensity in `[0,1]` |
| `objects` | Ordered list of at most 64 supported objects |

Each object contains exactly `id`, `type`, `parameters` and `intensity`.
IDs are unique 32-character lowercase hexadecimal strings. Supported parameter
sets are disk `{cx_px,cy_px,radius_px}`, rectangle
`{cx_px,cy_px,width_px,height_px}`, and segment
`{x0_px,y0_px,x1_px,y1_px,width_px}`. Object intensity has the same contract as
background intensity. Coordinates lie in `[-4096,4096]`; radii, widths and
heights are positive and no greater than 8192 pixels. Real scalar settings
accept built-in integers/floats, excluding booleans, and must be representable
as finite binary64. Validation preserves represented scalar bits, including
signed zero. Unknown/missing fields, duplicate IDs, unsupported kinds/versions,
nonfinite values and invalid limits fail explicitly. Wrong types raise
`TypeError`; invalid values/domains raise `ValueError`.

`TargetDesign2D(spec)` takes an owned validated snapshot. `to_dict()` returns
fresh nested containers; changing the caller's original or returned dictionary
does not change the model. Object ordering and stored endpoint orientation are
part of that editable record. Selection is UI state and is not design content.

#### 3.16.2 Pixel centers, canvas and physical interpretation

For canvas `(ny,nx)`, evaluate each pixel at

```text
x_px[j] = j - nx//2       j = 0,...,nx-1
y_px[i] = i - ny//2       i = 0,...,ny-1
```

The origin is index `[ny//2,nx//2]`, for odd and even sizes; `+x` follows
columns rightward and `+y` follows rows downward. An even length `N` covers
`-N/2,...,N/2-1`; odd lengths have symmetric center coordinates. Shapes remain
in their stated coordinates when partly or wholly off-canvas. Evaluate only
the declared canvas's centers, without wrapping or moving geometry.

The design canvas is authoritative for the submitted grid shape. Resizing
changes the centered-coordinate window but does not rescale/reposition/delete
objects. Positive grid pitches assign physical coordinates
`x_m = x_px * dx_m`, `y_m = y_px * dy_m`, with extents `nx*dx_m`, `ny*dy_m`.
Changing either pitch does not change the raster. A disk in pixel coordinates
can be physically elliptical when `dx_m != dy_m`.

#### 3.16.3 Membership and ordered overwrite

Membership includes the boundary. For a disk centered at `(cx,cy)` with radius
`r`, include a center `(x,y)` when

```text
(x-cx)**2 + (y-cy)**2 <= r**2
```

For an axis-aligned rectangle of width `w` and height `h`, include it when

```text
abs(x-cx) <= w/2 and abs(y-cy) <= h/2
```

These are geometric dimensions, not promised counts of covered centers.
For example, a centered width-2 rectangle can include `x=-1,0,1`.

A segment has round end caps and total width `w`. Treat its endpoints as
undirected geometry. Before projection, order endpoint pairs lexicographically
by `(x,y)` using their exact finite values; this internal evaluation order does
not rewrite the user's stored endpoint fields. Let the ordered endpoints be
`A=(ax,ay)`, `B=(bx,by)`, `D=B-A`, and `P=(x,y)`. For distinct endpoints:

```text
length_squared = Dx*Dx + Dy*Dy
t_raw = ((x-ax)*Dx + (y-ay)*Dy) / length_squared
t = min(1, max(0, t_raw))
qx = ax + t*Dx
qy = ay + t*Dy
distance_squared = (x-qx)**2 + (y-qy)**2
included = distance_squared <= (w/2)**2
```

Clamping `t` selects the closest point on a finite segment; it is not an
intensity correction. Exactly coincident endpoints use disk semantics with
radius `w/2`. Distinct endpoints whose required binary64 arithmetic is unusable
raise; they must not silently become coincident. No approximate endpoint
equality, snapping, epsilon boundary expansion or alternate reversal path is
allowed. Reversed stored endpoints therefore use the same evaluation order
and must give the same raster under this rasterizer and tested environment.
Required overflow, invalid/division errors and NumPy-reported underflow raise
`ValueError` identifying the object. A local error-state context restores the
caller's NumPy settings; a valid document can still fail rasterization when
required geometry arithmetic is unusable.

Membership arithmetic is binary64, not exact real arithmetic. A center at or
adjacent to a mathematically described boundary can depend on its represented
parameters and specified operation order. The boundary-sensitive regression
`A=(-1.3,-0.2), B=(2.7,1.3), P=(0,0)` measures this effect in the current
environment; planning values are not universal bit-identity claims. Independent
membership references must not call the production membership/rasterizer.

Initialize every output sample to `background_intensity`. Traverse objects
in stored list order, assigning that object's intensity to all included
centers. A later object overwrites earlier values, including assignment of
zero intensity. Never sum, blend, normalize by a peak or clip brightness.
There is no antialiasing, gamma mapping or conversion to/from 8-bit PNG.
Assigned binary64 intensity bits are retained exactly. The result is a fresh,
writable, C-contiguous plain native-float64 ndarray of shape `(ny,nx)`.
Rasterization neither mutates the model nor aliases caller storage.

#### 3.16.4 Editable persistence and numerical runs

Design I/O is separate from numerical computation and M5 bundles. Strict UTF-8
JSON is bounded to 256 KiB and rejects duplicate keys, nonstandard constants,
unknown fields and unsupported versions. Canonical output sorts object keys,
uses two-space indentation, LF and a final newline; array/list order retains
the object's explicit layering. Supported finite binary64 scalars round-trip
without 8-bit quantization. Zero/empty designs are valid editable documents.

Write only to exclusive new destinations using owned temporary files and
closed resources; cleanup must not remove unrelated data. Editable copies live
under `runs/designs/`; submitted snapshots use
`runs/designs/submissions/<run-uuid>.json`. These are external to completed
M5 bundles. Do not insert design metadata into the fixed manifest inventory or
change schema v1. Browser filenames never determine server destinations.
The standalone file API requires an existing parent, rejects links/reparse
paths and reserved partial filenames, and uses write/fsync/close plus an
absence recheck before same-filesystem rename. It adds no directory creation,
retry, overwrite or locking. Cleanup failure reports the owned leftover path
while preserving the primary error. Windows destination refusal does not imply
concurrent POSIX no-clobber or power-loss durability guarantees.

An explicit generation first consumes its operation nonce, captures immutable
design/scientific settings, validates and rasterizes the design, then persists
the editable snapshot. Only successful snapshot persistence permits the one
M5 run. The numerical path uses existing M2 amplitude conversion and explicit
per-target uniform illumination. The prescribed amplitude is
`sqrt(sum(A_target**2)/A_target.size)`, outside the solver. The actual float64
intensity enters M5 with `input_png=None`, without a PNG quantization step.
A zero target may preview/save/export; M3's positive-power requirement still
rejects synthesis. No substitute target is allowed.

A snapshot failure prevents generation. A subsequent M5 failure leaves the
reported editable snapshot intact. M5 success is recorded before presentation;
display failure neither deletes the completed run nor triggers another solve.
Preview edits can rasterize only, without implicit persistence, artifact
verification, synthesis or replay.

An explicitly requested associated-design load verifies the numerical bundle
through M5, validates/rasterizes the external design, then compares target
shape, dtype and C-order element bytes. A matching UUID name alone proves
nothing. Missing, malformed or raster-mismatched designs do not replace the
editor or invalidate otherwise valid numerical bundles. A raster match is not
authenticated authorship and does not identify a unique original drawing.
Completed-run replay continues to use saved actual arrays, independently of
the designer or external JSON; existing qualification/diagnostic rules remain.

No M0–M6 optical model, physical sign, normalization, numerical threshold,
artifact schema or historical evidence is changed by this section. M7
membership and target-byte checks state exact discrete claims; they do not
guarantee GS convergence or a quality threshold for arbitrary hard-edged
targets. Evidence and limitations are in the [M7 handoff](handoffs/milestone_7/).

---

### 3.17 V0 aligned sequential optics — API and schema contract

The V0 contract is `v0_aligned_scalar_forward_v1`, schema version integer 1.
It describes a single scalar monochromatic forward train in air on one complete
fixed grid, distinct from M3 synthesis, M5 RunConfig and M7 TargetDesign2D.
All positions, pitches, wavelengths and dimensions below are metres; phase is
radians and amplitude is arbitrary field units. No disk persistence is included.

**Exact schema keys (no optional/defaulted scientific parameters):**

| Object / tag | Required keys |
|---|---|
| Experiment | `schema_version`, `model_contract`, `wavelength_m`, `grid`, `source`, `components`, `observation` |
| Grid | `ny`, `nx`, `dy`, `dx` |
| Source `kind="uniform"` | `kind`, `amplitude`, `phase_rad` |
| Source `kind="gaussian"` | `kind`, `amplitude`, `phase_rad`, `waist_radius_m`, `waist_z_m`, `center_x_m`, `center_y_m` |
| Component `kind="circular_aperture"` | `id`, `kind`, `z_m`, `radius_m` |
| Component `kind="rectangular_aperture"` | `id`, `kind`, `z_m`, `width_m`, `height_m` |
| Component `kind="thin_lens"` | `id`, `kind`, `z_m`, `focal_length_m` |
| Observation | `id`, `z_m` |

`SequentialExperiment.from_dict(mapping)` accepts a Mapping with these exact
keys and a list/tuple of component mappings. Missing/unknown keys or unsupported
tags/versions raise ValueError; incorrect kinds/types raise TypeError.
Real scalars accept Python int/float and NumPy integer/floating scalars, excluding
both Python and NumPy booleans, complex values, strings and arrays. Counts and
schema version accept integers only, excluding booleans. All real scalars must
convert to finite binary64. Dimensions/pitches/wavelength are positive; amplitude
is nonnegative; focal length is nonzero; waist position/centers/phase may be signed.
IDs are ASCII `[A-Za-z][A-Za-z0-9_-]{0,63}`, with component and observation IDs
unique and `source` reserved. The source plane is z=0. Component z positions
must be nonnegative and nondecreasing in stored order; observation must be at
or beyond the last component. Never sort. Colocated list entries act in order.
At most 2048 samples per axis and 16 components are accepted; derived arithmetic
must be usable in binary64. These resource bounds do not guarantee sampling.

The constructor is `SequentialExperiment(*, wavelength_m, grid, source,
components, observation, schema_version=1,
model_contract="v0_aligned_scalar_forward_v1")`. Frozen source/component/plane
records use keyword-only parameters named exactly as their schema keys (the
fixed kind tag is derived). Parsed nested mappings become immutable records;
`to_dict()` exports fresh independent nested Python dictionaries/lists.

Exact public record constructors (all keyword-only, no defaults):

```python
UniformSource(*, amplitude, phase_rad)
GaussianSource(*, amplitude, phase_rad, waist_radius_m, waist_z_m,
               center_x_m, center_y_m)
CircularAperture(*, id, z_m, radius_m)
RectangularAperture(*, id, z_m, width_m, height_m)
ThinLens(*, id, z_m, focal_length_m)
ObservationPlane(*, id, z_m)
StageRecord(*, selector, z_m, norm, previous_norm)
StageField(*, selector, field)
SequentialResult(*, experiment, observation, stages, recorded_fields)
```

`Component` is the union of the three supported element records. Scientific
classes/functions are imported from `ohlab.optics`; root exports are unchanged.

Public functions (type hints use these immutable records and existing fields):

```python
sample_source(experiment: SequentialExperiment) -> ComplexField
apply_component(field: ComplexField, component: Component) -> ComplexField
run_experiment(experiment: SequentialExperiment, *,
               record_fields: tuple[str, ...] = ()) -> SequentialResult
```

`apply_component` applies only transmission on the supplied plane; `component.z_m`
never causes propagation. The runner derives each separation once and calls the
existing public M1 propagator with pad_factor=1, including the terminal interval.
No intermediate crop, embedding, normalization or second production kz/FFT path.
Forward evanescent decay is retained. Source/element/grid metadata are unchanged.

Stage selectors are `source`, `before:<component-id>`, `after:<component-id>`
and `observation`. Every stage has its own identity even at equal z. All stages
receive scalar StageRecord entries; `record_fields` must be a tuple of at most
four distinct source/before/after selector strings. Unknown, duplicate and
`observation` recording requests raise ValueError (the terminal field is always
available). SequentialResult stores the experiment, actual `observation` field,
`stages` tuple and `recorded_fields` tuple of StageField(selector, field).
`field_at(selector)` retrieves the terminal or explicitly recorded field and
raises ValueError otherwise. StageRecord has selector, z_m, norm,
previous_norm, delta_norm and transmission_ratio. The source has None for the
last three. Each later record compares with the immediately preceding stage;
delta_norm is after minus previous, signed and never clamped. A ratio is None
when the previous norm is zero; it is not calibrated efficiency. Fields have
owned read-only complex128 storage, and derived intensity uses existing field
semantics. No large unrequested stage field is retained.

Source Gaussian: let s=-waist_z_m at the source, zR=pi*w0**2/lambda,
b=1+i*s/zR and r2=(x-cx)**2+(y-cy)**2. Then
`U=(A0/b)*exp(-r2/(w0**2*b))*exp(i*(k*s+phase_rad))`, where A0 is the
waist peak field amplitude and w0 the 1/e amplitude / 1/e^2 intensity radius.
Uniform source is `A0*exp(i*phase_rad)` over the complete periodic window.
No image-design Gaussian width or unit-power normalization is used. The
sign-matched paraxial Gaussian parameter is q=s-i*zR.

**Independent Gaussian/lens reference.** A centered Gaussian at a lens plane
can be written `C*exp(-a*r2)`, including its actual complex on-axis prefactor C.
The lens leaves C unchanged and updates `a -> a+i*k/(2*f)`. After a distance d,
define `B=1+2*i*d*a/k`; the complete paraxial field is
`C*exp(i*k*d)/B * exp(-a*r2/B)`. The amplitude prefactor and its complex phase
continuity must be retained; no fitted amplitude or global-phase alignment.
For a waist at the lens, `a=1/w0**2+i*k/(2*f)` and
`w(d)=w0*sqrt((1-d/f)**2+(d/zR)**2)`. Its minimum for positive f is at
`d=f/(1+(f/zR)**2)`, not necessarily f. Exact ASM and this paraxial reference
have a model-dependent agreement floor.

Verified primary references (accessed 2026-10-01): Konijnenberg, Adam and
Urbach, [Angular Spectrum Method §6.3, displayed Eqs. (6)–(7)](https://phys.libretexts.org/Bookshelves/Optics/BSc_Optics_%28Konijnenberg_Adam_and_Urbach%29/06%3A_Scalar_diffraction_optics/6.04%3A_Angular_Spectrum_Method)
fixes the negative time exponent and positive forward exponent;
[Fourier Optics §6.8.1, displayed Eqs. (3)–(7)](https://phys.libretexts.org/Bookshelves/Optics/BSc_Optics_%28Konijnenberg_Adam_and_Urbach%29/06%3A_Scalar_diffraction_optics/6.09%3A_Fourier_Optics)
derives the negative quadratic lens phase in the small-aperture limit.
MIT [Gaussian Beams and Resonators, printed pp. 104–106, Eqs. (2.259)–(2.263)](https://ocw.mit.edu/courses/6-974-fundamentals-of-photonics-quantum-electronics-spring-2006/e9852c138493233bc2813f683da5b199_gaussian_bem_res.pdf)
gives ABCD evolution and `1/q_after=1/q_before-1/f`; its field uses the
opposite phase convention and positive imaginary waist q, so the field/q
are conjugated for the present convention. These verified sources do not
upgrade the earlier unverified Goodman attribution.

Circular transmission is `x*x+y*y <= radius_m**2`; rectangular transmission
is `abs(x)<=width_m/2 and abs(y)<=height_m/2`, inclusive center-sampled 0/1
field-amplitude masks using physical coordinates on both axes. Lens transmission
is `exp(-i*k*(x*x+y*y)/(2*f))`, f finite nonzero signed, no implicit aperture
or constant phase correction. It changes phase immediately; focusing requires
propagation. Thin lenses and Gaussian sources are ideal paraxial models.

The ideal observation records U and |U|**2, without camera integration, exposure,
noise, saturation, calibrated irradiance or watts. Sampled norm is
`sum(abs(U)**2)*dx*dy` in amplitude-unit^2*m^2; no target metric is required.
Dark sources/blocked fields are valid. Validate all parameters and usable derived
geometry before exact-zero shortcuts. Overflow/invalid arithmetic and unusable
geometry raise ValueError. Only decaying Gaussian exponential tails, products
of finite fields with bounded unit-modulus/zero-one transmission, squared
magnitudes in norm reduction, and existing forward evanescent decay may
underflow to zero. Norm must reject a nonzero field whose complete sampled norm
underflows to zero. Error handling is local; caller settings remain unchanged,
and no blanket all-errors-raise policy is applied around M1 propagation.

Full-window periodic norm changes are distinct from physical aperture loss and
selected observation-region norm. Do not assign escaped power or call tiny lens
roundoff absorption. Adequate isolated-optics accuracy needs separately reported
window and pitch convergence. No universal sampling or paraxial-validity badge.

**Bounded aperture reference acceptance.** For unit incident amplitude and zero
phase through a continuous centered rectangle of width 80e-6 and height 120e-6 m,
use lambda=633e-9 m and d=5e-3 m. For each axis v and full width D, set
`t_plus=sqrt(2/(lambda*d))*(D/2-v)` and
`t_minus=sqrt(2/(lambda*d))*(-D/2-v)`. With F=C+i*S (standard Fresnel integrals),
the reference is `exp(i*k*d)/(2*i) * (F(tx_plus)-F(tx_minus)) *
(F(ty_plus)-F(ty_minus))`. This follows the sign-matched
[Fresnel kernel, page 6.6, subsection 6.5.1, displayed diffraction integral](https://phys.libretexts.org/Bookshelves/Optics/BSc_Optics_%28Konijnenberg_Adam_and_Urbach%29/06%3A_Scalar_diffraction_optics/6.07%3A_Fresnel_and_Fraunhofer_Approximations)
and the separable C/S definitions in
[UT Austin, Eqs. (10.119)–(10.124)](https://farside.ph.utexas.edu/teaching/315/Waveshtml/node101.html).
The exact ROI selects sample centers with `abs(x)<=100e-6` and
`abs(y)<=100e-6`, inclusive, on each grid. Compare
`sqrt(sum_ROI(abs(U_numeric-U_reference)**2)/sum_ROI(abs(U_reference)**2))`
without alignment, fitted scaling, peak normalization or reference-aperture
enlargement. Finest acceptance is 2048² at 1e-6 m pitch with error <=0.035;
also retain 512²/4e-6, 1024²/4e-6, 1024²/2e-6 and 2048²/2e-6 cases.
It is a regional complex-field L2 criterion, not intensity error, worst-pixel
bound or percent accuracy. Sampled-area bias and omitted Fresnel terms are
separate; no sub-percent claim is made for this hard-edged fixture.

## 4. Symbol reference

| Symbol | Code name | Meaning | Unit |
|---|---|---|---|
| `U` | `field.data` | complex field | a.u. |
| `A` | `field.amplitude` | amplitude, `\|U\|` | a.u. |
| `φ` | `field.phase` | phase, `arg(U)` | rad, `(−π, π]` |
| `I` | `field.intensity` | intensity, `\|U\|²` | a.u. |
| `P` | `field.power` | `Σ I · dx · dy` | a.u.·m² |
| `λ` | `wavelength_m` | vacuum wavelength | m |
| `k` | `wavenumber` | `2π/λ` | rad/m |
| `Nx, Ny` | `nx`, `ny` | sample counts | — |
| `dx, dy` | `dx`, `dy` | pixel pitch | m |
| `Lx, Ly` | `extent_x`, `extent_y` | window size, `N·d` | m |
| `fx, fy` | `fx_fft`, `fx_centered` | spatial frequency | cycles/m |
| `kx, ky` | `kx_fft`, `kx_centered` | angular spatial frequency | rad/m |
| `kz` | `kz` | axial wavevector component | rad/m |
| `z` | `distance_m` | propagation distance | m |
| `n` | — | refractive index (fixed at 1) | — |

---

## 5. Explicitly out of scope in v0.1

Not assumed, not implemented, and not to be added without an explicit decision:

polarization; partial coherence; multiple wavelengths or RGB; 3D scenes;
refractive index ≠ 1; tilted or non-parallel planes; different sampling on source
and destination planes; production Fresnel or Fraunhofer propagators;
SLM non-idealities (phase quantization,
fill factor, inter-pixel crosstalk, nonlinear phase response); any hardware
model.

V0 (§3.17) adds sequential observations on parallel planes using unchanged ASM,
with explicitly paraxial ideal Gaussian/lens models and independent Fresnel
validation references. It does not add M3 multi-plane synthesis or a 3D scene.

---

## Change Log

| Version | Date | Change | Reason |
|---|---|---|---|
| 0.10 | 2026-10-01 | **§3.17 added** — exact SI sequential-experiment schema/API, immutable stage identities, source/element actions, complete-window forward ASM reuse, dark/norm arithmetic and bounded independent reference criteria. **§5 clarified** — V0's explicit ideal paraxial elements/reference formulas are distinct from an unimplemented alternate propagator or 3D scene. | Approved V0 implementation. Existing M0–M7 numerical implementations, selected signs, sampling, GS and M5 bundle contracts remain unchanged; original evidence and the earlier unverified Goodman attribution are preserved. |
| 0.9 | 2026-09-30 | **§3.16 added** — versioned pixel-coordinate designs, inclusive center-sampled geometry, internally ordered undirected segments, ordered intensity overwrite, bounded editable JSON and external design/run association. | Approved Milestone 7. Pixel coordinates are dimensionless authoring/sample coordinates; existing SI optical calls, M2–M5 scientific/serialization contracts, old mathematical sections and historical evidence remain unchanged. |
| 0.8 | 2026-09-23 | **§3.10 refined; §3.15 added** — separate artifact integrity, provenance qualification and exact replay; define schema-v1 capture/serialization, metric persistence and transactional I/O. | Approved Milestone 5. M0–M4 algorithms, physical conventions, normalization, RNG and historical evidence remain unchanged. |
| 0.7 | 2026-09-20 | **§3.14 added** — five intensity metrics, explicit target/range/region semantics, population CV, validated exact cases and float64 failure policies. **§2.1 clarified** — raw MSE retains squared intensity scale; PSNR cancels common scale only with coordinated data range. | Approved Milestone 4. Field normalization, units, propagation, M3 solver/residual history and historical evidence remain unchanged. |
| 0.6 | 2026-09-16 | **§3.13 added** — complete periodic lossless ASM GS, explicit power/initialization/zero contracts, inverse versus adjoint, fixed cycle count, last-iterate reconstruction and pre-projection residual history. | Approved Milestone 3. M0/M1/M2 implementations and conventions remain unchanged; no hidden normalization, physical-device calibration, or general convergence claim. |
| 0.5 | 2026-09-16 | **§3.12 added** — fixed grayscale-to-intensity `/255` and amplitude square-root contracts, strict array ownership/dtypes, size/orientation rules and static 8-bit grayscale PNG boundary. | Approved Milestone 2. No hidden radiometric or spatial conversion; no phase assignment. Existing optical signs, grid/FFT conventions, field/propagation behavior and precision remain unchanged. |
| 0.4 | 2026-09-14 | **§3.1/§3.6** — distinguish the selected Fourier pair from the physical time/propagation convention; remove the claim that all three signs must flip together. **§3.2** — specify exact `−π` to `+π` endpoint normalization after `np.angle`, including signed-zero handling without changing stored data. **§3.7** — derive the centered-coordinate physical spectrum, its inverse, and same-grid ASM cancellation of area and origin factors. **§3.9.1** — restrict conjugacy under distance reversal to real `kz` and explain the evanescent exception. | Approved M0/M1 corrective maintenance. Existing selected signs, grid/FFT ordering, precision, normalization, propagation implementation, and evanescent policy are retained; phase output is corrected to the existing canonical-interval contract. Historical evidence and dated errata are recorded in `docs/corrections/m0_m1_contract_and_evidence.md`. |
| 0.3 | 2026-08-11 | **§3.1** — records the external verification of the time convention and propagation sign against Konijnenberg/Adam/Urbach; downgrades the Goodman citation to an unverified secondary attribution; corrects the mislabelling of `exp(−iωt)` as the "engineering" convention (it is the *physicists'* convention); states that NumPy fixes the DFT kernel only, not the time convention, and that the three sign choices form a mutually verified set. **§3.9 rewritten** — §3.9.1 mandates the single expression `H = exp(+i·kz·z)` with `Im{kz} ≥ 0` and withdraws the piecewise presentation; §3.9.2 requires evanescence to be determined from the discrete mesh and corrects the threshold from `d < λ/2` to the corner condition `d < λ/√2`; §3.9.3 states the evanescent policy; §3.9.4 specifies the padding/cropping alignment rule and the boundary-condition semantics; §3.9.5 defers band-limited ASM. **§3.8** — periodicity note updated. No mathematical convention changed. | Milestone 1. The `d < λ/2` threshold in the M1 plan was an error (axis-only reasoning); the corner of the 2-D Nyquist square reaches the cutoff first. Raised and corrected before implementation. |
| 0.2 | 2026-08-08 | **§3.8.1 added** — mandates the reciprocal-multiply evaluation order for frequency axes, with measured ULP-level evidence. **§3.4** — documents that `meshgrid()` returns `(x_grid, y_grid)`, matching `numpy.meshgrid` order rather than axis order. Both are clarifications; no mathematical convention changed. | Milestone 0. The literal division form in v0.1 §3.8 was inconsistent with the bit-for-bit agreement with `numpy.fft.fftfreq` required by `milestones.md`; the conflict was raised and approved before implementation. |
| 0.1 | 2026-08-08 | Initial version. Establishes §1–§5: scalar monochromatic model at `n = 1`; SI units with `I ≡ \|U\|²`; `exp(−iωt)` time convention with forward propagation `exp(+i·kz·z)`; `(Ny, Nx)` array layout with `+y` downward; `N//2`-centred space and frequency grids; `numpy.fft` `norm="backward"`; `*_fft` / `*_centered` ordering discipline; Angular Spectrum transfer function; determinism and precision rules. | Scaffolding, prior to Milestone 0. |
