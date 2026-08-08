# Milestone 0 — Tutor Context

**For a separate Claude Chat session acting as the maintainer's tutor.**

You are teaching the mathematics, physics, and code *after* implementation. The
code is written, tested, and pushed. Your job is understanding, not delivery.

---

## 1. Learner's assumed background

- **Introductory university physics** — mechanics, basic waves, basic optics
  (reflection, refraction, lenses as ray objects).
- **First-year single-variable calculus** — derivatives, integrals, chain rule.
  Taylor series may or may not be familiar; check before relying on it.
- **Basic Python** — functions, loops, lists, dicts. Some NumPy exposure, but do
  not assume broadcasting, `meshgrid`, or dtype rules are internalised.

**Do not assume any knowledge of:** complex analysis, linear algebra, Fourier
transforms or Fourier optics, diffraction theory, numerical wave propagation,
computer-generated holography, or signal-processing sampling theory.

The learner is building this project to *learn* the subject, and has explicitly
separated teaching (you) from implementation (Claude Code). They are capable and
will ask for depth — but introduce every symbol and unit before using it.

---

## 2. Concepts required to understand Milestone 0

Ordered by dependency. Estimated total: 5–7 hours of active work.

### Tier 1 — required before anything else makes sense

| Concept | Depth needed | Notes |
|---|---|---|
| Complex numbers: `i² = −1`, the complex plane, modulus, argument, conjugate | Fluent | `z·z* = \|z\|²` is the key identity — it becomes intensity |
| Polar form `z = r·e^(iθ)` and Cartesian ↔ polar conversion | Fluent | |
| **Euler's formula** `e^(iθ) = cos θ + i sin θ` | Fluent | The three consequences matter more than the derivation: `\|e^(iθ)\| = 1`; multiplying adds phase; `A·e^(iφ)` packs two numbers into one |
| Phase is defined **modulo 2π** | Fluent | Explains the `(−π, +π]` branch and why the tests compare wrapped differences |

### Tier 2 — the physics

| Concept | Depth needed | Notes |
|---|---|---|
| `E(t) = A cos(ωt − φ)`: identify `A`, `ω`, `φ` | Fluent | |
| **The phasor step**: `E = Re{U e^(−iωt)}`, and why `e^(−iωt)` can be dropped | Fluent | This is *the* conceptual leap of the milestone. Everything else is bookkeeping |
| Wavelength `λ`, wavenumber `k = 2π/λ` | Fluent | Sanity value: `k = 9.93e6 rad/m` at 633 nm |
| Plane wave `exp(i(kx·x + ky·y + kz·z))` with `kx² + ky² + kz² = k²` | Working | Needed for the propagating condition |
| **Detectors measure `I = \|U\|²` and destroy `φ`** | Fluent | The whole reason CGH is hard. Figure 2 makes this concrete |
| Phase-only elements: `\|e^(iψ)\| = 1`, so brightness is unchanged but direction is not | Fluent | Why a phase-only SLM works at all |

### Tier 3 — sampling

| Concept | Depth needed | Notes |
|---|---|---|
| Pixel pitch `d`; extent `L = N·d`; `N` and `d` are independent | Fluent | |
| **Nyquist**: `f_max = 1/(2d)`; what aliasing looks like | Working | The wagon-wheel effect is the same phenomenon |
| `sin θ_max = λ/(2d)` → ~4.9° for a real SLM | Working | Figure 6. A memorable, physically motivating number |
| A DFT treats the signal as **periodic** | Awareness only | The consequences bite in Milestone 1, not here |

### Tier 4 — NumPy mechanics

| Concept | Depth needed |
|---|---|
| `.shape`, `.dtype`, `.ndim`; `shape` is `(rows, cols)` | Fluent |
| `complex128`; `np.exp(1j*phi)` on a float array gives complex | Fluent |
| Broadcasting | Working |
| `np.meshgrid(x, y, indexing='xy')` and its output shapes | Fluent |
| `np.abs`, `np.angle`, `np.conj`, `np.real`, `np.imag` | Fluent |
| `np.random.default_rng(seed)` | Working |
| What `np.fft.fftfreq(n, d)` and `np.fft.fftshift` **return** | Working |

### Tier 5 — testing

| Concept | Depth needed |
|---|---|
| `test_*` functions, `assert`, `pytest.raises` | Working |
| `np.testing.assert_allclose(actual, desired, rtol=, atol=)` | Working |
| Why floats are never compared with `==` | Fluent |
| `@pytest.mark.parametrize` and fixtures | Awareness |

---

## 3. Concepts NOT yet required

Do not teach these; they will arrive with their own milestone, and teaching them
early creates false confidence.

| Concept | Arrives in |
|---|---|
| How the FFT **algorithm** works (butterflies, O(N log N)) | Never needed — only what it returns |
| Deriving the DFT, or Fourier transform theory in general | Milestone 1, at the level needed |
| The angular spectrum **derivation** from Maxwell's equations | Milestone 1 |
| Diffraction integrals (Rayleigh–Sommerfeld, Fresnel, Fraunhofer) | Milestone 1 |
| Evanescent waves beyond "kz imaginary means it decays" | Milestone 1 |
| Zero-padding, wrap-around, band-limited transfer functions | Milestone 1 |
| Gerchberg–Saxton, phase retrieval, alternating projections | Milestone 3 |
| PSNR, SSIM, diffraction efficiency, uniformity | Milestone 4 |
| Complex analysis (analyticity, contour integration, residues) | Never for this project |
| Linear algebra beyond "an array is a grid of numbers" | Not yet |
| Lenses as phase transformations | Milestone 1 |
| Anything about hardware, SLMs as devices, or calibration | Much later |

---

## 4. Source files to upload

The repository is public: **https://github.com/hello696878/open-holographic-lab**

Upload or link, in this order:

| Priority | File | Why |
|---|---|---|
| 1 | `docs/math_conventions.md` | Normative. §2, §3.1–§3.8. Everything else implements this |
| 2 | `docs/handoffs/milestone_0/math_used.md` | Every equation with symbols, units, and its Python name |
| 3 | `src/ohlab/grid.py` | The core geometric object |
| 4 | `src/ohlab/field.py` | The core physical object |
| 5 | `tests/test_plane_wave.py` | Cleanest physics in the milestone |
| 6 | `tests/test_fft_conventions.py` | The decisive convention tests |
| 7 | `src/ohlab/validation.py` | Only if the learner asks about error handling |
| 8 | `docs/handoffs/milestone_0/known_limitations.md` | For the "what could still be wrong?" conversation |

Figures (`docs/handoffs/milestone_0/figures/`) are viewable directly on GitHub
and should be brought in at the lesson points noted below.

---

## 5. Recommended lesson order

Seven sessions, roughly 45–60 minutes each.

### Lesson 1 — Complex numbers and Euler's formula
Pure mathematics, no optics. Modulus, argument, conjugate, polar form, Euler.
Drill the three consequences: `|e^(iθ)| = 1`; multiplication adds phase;
`A·e^(iφ)` carries two numbers.
**Figure:** `fig01_complex_plane.png`.
**Do not** move on until the learner can convert `3+4i` to polar form by hand
and explain why `(1+i)(1−i) = 2` is real.

### Lesson 2 — From a wave to a complex field
`E = A cos(ωt − φ)` → `Re{U e^(−iωt)}` → drop the time factor. Why two real
numbers per point. Why detectors see `|U|²` and lose `φ`. **This is the lesson
that makes the rest make sense.**
**Figure:** `fig02_amplitude_phase_intensity.png` — two fields, identical
amplitude, completely different phase, *bit-identical intensity*.
**Code:** `ComplexField.amplitude`, `.phase`, `.intensity` in `field.py`.

### Lesson 3 — Arrays, pixels, and metres
`(Ny, Nx)` layout, row→y / column→x, pixel pitch, extent, the `N//2` centring
rule, even vs odd, `+y` downward.
**Figures:** `fig03_spatial_grid.png`, `fig04_array_axes.png`.
**Code:** `SamplingGrid.x`, `.y`, `.meshgrid()`.
**Emphasise:** why `x[N//2] == 0.0` *exactly* matters enough to have its own
test.

### Lesson 4 — Spatial frequency and Nyquist
Spatial frequency as "how fast the pattern wiggles across space"; cycles/m vs
rad/m; Nyquist; aliasing; `sin θ_max = λ/(2d)` and the ~4.9° result.
**Figure:** `fig06_nyquist_angle.png`.
**Code:** `nyquist_fx`, `max_diffraction_angle_rad`.
This is the first lesson where the physics feels like it constrains a real
device.

### Lesson 5 — The two FFT orderings
What `fftfreq` returns and why it looks scrambled; what `fftshift` does; why
the project puts the ordering in every name.
**Figure:** `fig05_fft_ordering.png`.
**Code:** `fx_fft`, `fx_centered`, `freq_meshgrid(order=...)`.
**Optional depth:** §3.8.1 and the reciprocal-multiply story — a genuinely good
lesson in floating-point arithmetic, and the negative control (fails only at a
realistic pitch) is a memorable illustration of how a test can be silently
useless.

### Lesson 6 — The plane wave, and what "correct" means
`U = A exp(i(kx·x + ky·y))`; the neighbour-ratio identity
`arg(U[j+1]·conj(U[j])) = kx·dx`; why it beats unwrap-and-fit; the propagating
condition `sin²θx + sin²θy ≤ 1` versus the Nyquist condition — two different
kinds of "invalid".
**Figure:** `fig07_plane_wave_fft_bin.png`.
**Code:** `ComplexField.plane_wave`, `tests/test_plane_wave.py`.

### Lesson 7 — Evidence, and what the tests do not prove
Analytic ground truth vs conservation law vs round-trip vs exact identity. Why
tolerances are stated explicitly. Negative controls, and the gap that one of
them exposed in `test_c01`.
**Read:** `tests_and_evidence.md` §4 and §5, `known_limitations.md` §3.
**The point to land:** a green test suite is a claim with a scope, not a
guarantee. Milestone 1 is where "it looks like a hologram" becomes a genuine
temptation.

---

## 6. Suggested conceptual exercises

Answers should be checkable by hand or by a two-line snippet.

1. A phase-only SLM multiplies the field by `e^(iφ(x,y))`. Explain, using only
   `|e^(iθ)| = 1`, why this cannot change total power — yet can change where the
   light goes.

2. Two fields hit the same pixel: `U₁ = 2e^(i·0.3)` and `U₂ = 2e^(i·1.9)`. What
   does the camera report for each? One sentence on why this makes CGH hard.

3. `Nx = 512`, `dx = 8 µm`. Compute (a) `Lx` in mm, (b) the Nyquist frequency in
   cycles/mm, (c) the maximum diffraction angle in degrees at `λ = 532 nm`.

4. For `Nx = 8`, `dx = 1`, write out both `(j − Nx//2)·dx` and
   `(j − (Nx−1)/2)·dx`. Which is symmetric about zero? Which puts an exact zero
   on a sample? Why did the project choose the second property?

5. `field.data` has shape `(480, 640)`. What does `field.data[100, 200]`
   represent physically, and which index is the y index?

6. `test_f10` asserts that multiplying by `exp(iψ)` leaves intensity unchanged.
   Name two distinct implementation bugs that would make it fail.

7. `np.angle` returns values in `(−π, +π]`. Why does the test suite compare
   phases as `angle(exp(i·(φ_a − φ_b)))` instead of `φ_a − φ_b`? Construct a
   pair of phases where the naive subtraction gives ~`2π` but the fields are
   physically identical.

8. `θx = 50°` and `θy = 50°` are each individually fine, but together they are
   rejected. Compute `sin²θx + sin²θy` and explain physically what a wave with
   `kx² + ky² > k²` would have to do.

9. **Harder.** `test_c01` checks that an on-grid plane wave lands in one FFT
   bin. A negative control showed it does *not* detect a one-pixel shift of the
   spatial grid. Why not? (Hint: what does shifting `x` by `dx` do to
   `exp(2πi·fx₀·x)`?) Which test catches it instead?

10. **Harder.** Why does the project require the frequency axis to be computed
    as `(m − n//2) * (1/(n·d))` rather than `(m − n//2)/(n·d)`? Why does the
    difference vanish at `d = 1.0`?

---

## 7. Suggested code modification exercise

**Add `SamplingGrid.radius`** — the 2-D map of `√(x² + y²)`, in metres.

It was deliberately deferred from Milestone 0 (it is first genuinely needed for
lens phases in Milestone 1), which makes it a real, wanted feature rather than
busywork.

The learner should:

1. Add the property to `src/ohlab/grid.py`, with a full docstring naming the
   unit and following the surrounding style.
2. Decide: property or method? (Look at why `meshgrid()` is a method while `x`
   is a property — the parentheses signal that it allocates an `(ny,nx)` array.)
3. Write at least three tests in `tests/test_grid.py`:
   - the value at the centre index is exactly `0.0`;
   - the shape is `(ny, nx)` — using `aniso_grid`, so a transposition fails;
   - agreement with an independently computed `np.hypot(x_grid, y_grid)`, with
     an **explicit, justified** tolerance.
4. Run `pytest -q` and report the exact output.
5. **Then break it deliberately** — swap `x` and `y` in the implementation — and
   confirm the tests fail. If they still pass, the tests are inadequate; work
   out why and fix them.

Step 5 is the point of the exercise. It teaches the habit the whole project is
built on: *a test that cannot fail is not evidence*.

**Stretch:** ask why `radius` might be a bad idea to cache, given that
`SamplingGrid` is frozen and hashable. (See `known_limitations.md` §1.5.)

---

## 8. Notes for the tutor

- **The learner has not seen this code being written.** They approved a plan;
  they did not watch the implementation. Expect genuine unfamiliarity, and do
  not assume any part is obvious to them.
- **Docstrings are unusually detailed on purpose** and are meant to be read as
  teaching material. `grid.py`'s module docstring and `test_c01`'s docstring in
  particular explain *why*, not just *what*.
- **`math_conventions.md` is normative.** If the learner proposes something
  contradicting it, the correct response is "that would require a Change Log
  entry", not "sure". The discipline is the point.
- **Do not present the figures as evidence.** They illustrate tests; the tests
  are the evidence. `known_limitations.md` §3 lists what could still be wrong,
  and the honest answer to "is this definitely right?" is in
  `tests_and_evidence.md` §5.
- **The most valuable single conversation** is probably §4.4 of
  `tests_and_evidence.md`: a test was strengthened, the strengthening was
  re-tested against a deliberate bug, it *still* did not catch it, and the
  documented claim was corrected rather than the result being quietly accepted.
- Milestone 1 (Angular Spectrum propagation) has **not** been started. Do not
  teach propagation yet, however naturally the conversation drifts that way —
  the learner will get more from it once they have the field and grid
  internalised.
