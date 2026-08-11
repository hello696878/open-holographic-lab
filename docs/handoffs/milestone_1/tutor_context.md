# Milestone 1 — Tutor Context

**For a separate Claude Chat session acting as the maintainer's tutor.**

The code is written, tested, and pushed. Your job is understanding.

**Prerequisite: the learner should have completed the Milestone 0 lessons**
(complex fields, amplitude/phase/intensity, sampling grids, the two FFT
orderings, Nyquist). Milestone 1 builds directly on all of it.

---

## 1. Learner's assumed background

Unchanged from Milestone 0: introductory university physics, first-year
single-variable calculus, basic Python. Plus whatever Milestone 0 taught —
check what actually stuck before building on it, particularly:

- the phasor step (`E = Re{U·e^(−iωt)}`, and why the time factor is dropped);
- that multiplying by `e^(iθ)` adds phase and never changes brightness;
- what `fftfreq` returns and why there are two orderings;
- Nyquist, and `sin θ_max = λ/(2d)`.

**Do not assume** they know: the Helmholtz equation, any diffraction integral,
what an "angular spectrum" is, evanescent waves, Gaussian beam optics, or the
Gouy phase.

---

## 2. Concepts required for Milestone 1

### Tier 1 — the central idea

| Concept | Depth | Notes |
|---|---|---|
| **A field is a sum of tilted plane waves** | Fluent | *The* idea of the milestone. The FFT is the machine that finds the sum |
| A plane wave propagates by acquiring `e^(i·kz·z)` and nothing else | Fluent | Amplitude untouched — it is a pure phase factor |
| `kx² + ky² + kz² = k²` | Fluent | The sphere picture (fig03). More tilt ⇒ smaller `kz` ⇒ slower axial phase |
| Why this makes propagation a **multiplication** in the frequency domain | Fluent | Each component evolves independently; that is the whole method |

### Tier 2 — the branch and the two regimes

| Concept | Depth | Notes |
|---|---|---|
| `kz = √(k² − kx² − ky²)` can be imaginary | Working | When the tilt is "more than 90°", which is not a real direction |
| Evanescent waves decay as `e^(−κz)` | Working | They exist, carry no energy to the far field, and require sub-wavelength sampling to appear at all |
| Why backward propagation of evanescent components is refused | Working | Exponential growth; ill-posed. Good lesson in numerical honesty |
| The **corner vs axis** distinction | Working | See §5 Lesson 4 — a genuinely instructive error that was caught |

### Tier 3 — the numerical boundary

| Concept | Depth | Notes |
|---|---|---|
| The DFT treats the window as **periodic** | Fluent | Light leaving one edge re-enters opposite (fig07 shows it dramatically) |
| Zero padding as a *different boundary condition*, not a fix | Fluent | The nuance matters: it is not "more correct", it is a different assumption |
| Why exact analytic tests use `pad_factor=1` | Working | A plane wave is an eigenfunction of the *periodic* problem |
| Padding alignment and the `N//2` origin | Working | Connects straight back to M0's centring convention |

### Tier 4 — evidence

| Concept | Depth | Notes |
|---|---|---|
| Why a round trip cannot validate a sign | **Fluent** | The single best epistemics lesson in the project so far |
| Exact vs model-limited tolerances | Fluent | Plane wave `2e-14` vs Gaussian `1e-6` — and *why* they differ |
| Negative controls | Fluent | 10 injected, 10 caught |

### Optional depth — only if asked

Gaussian beam algebra (`w(z)`, `R(z)`, Gouy phase); the Helmholtz derivation of
`kz`; the band-limited ASM sampling criterion.

---

## 3. Concepts NOT yet required

| Concept | Arrives in |
|---|---|
| Deriving the angular spectrum from Maxwell's equations | Not needed; the Helmholtz sketch in `math_used.md` §2.2 suffices |
| Rayleigh–Sommerfeld, Fresnel, Fraunhofer diffraction integrals | Not implemented at all — do not teach as if they were |
| Band-limited ASM | Deferred (M1.x candidate) |
| Target image loading, resampling | Milestone 2 |
| Gerchberg–Saxton, phase retrieval | Milestone 3 |
| PSNR, diffraction efficiency, uniformity | Milestone 4 |
| Lenses as phase transformations | Not yet implemented |
| Anything about SLM hardware | Much later |

---

## 4. Source files to upload

Public repository: **https://github.com/hello696878/open-holographic-lab**

| Priority | File |
|---|---|
| 1 | `docs/math_conventions.md` §3.9 (all subsections) and the updated §3.1 |
| 2 | `docs/handoffs/milestone_1/math_used.md` |
| 3 | `src/ohlab/propagation.py` |
| 4 | `tests/test_propagation_analytic.py` |
| 5 | `docs/handoffs/milestone_1/tests_and_evidence.md` §5 (negative controls) |
| 6 | `tests/test_propagation.py` — for the padding and evanescent sections |
| 7 | `docs/handoffs/milestone_1/known_limitations.md` |

Figures live in `docs/handoffs/milestone_1/figures/` and render directly on
GitHub.

---

## 5. Recommended lesson order

Seven sessions, 45–60 minutes each.

### Lesson 1 — A field is a sum of plane waves
The central idea, before any formula. Start from M0's plane wave: one tilt, one
spatial frequency. Then two. Then "any field is a sum of these, and the FFT
finds the recipe."
**Figure:** `fig01_angular_spectrum_decomposition.png` — three components,
their sum, and the three isolated bins in the spectrum.
**Land this:** the FFT is not new physics; it is the change of description that
makes propagation easy.

### Lesson 2 — How a plane wave propagates
`kx² + ky² + kz² = k²`. Derive `kz = √(k² − kx² − ky²)` geometrically from the
sphere. Show that more tilt means smaller `kz`, so a tilted wave advances in
axial phase *more slowly*.
**Figure:** `fig03_kz_geometry.png`.
**Code:** `test_a03` — which asserts exactly that.

### Lesson 3 — The method, and the pipeline
FFT2 → multiply by `H` → IFFT2. Why `H = e^(i·kz·z)`. Why one expression covers
forward, backward, propagating and evanescent.
**Figure:** `fig02_space_frequency_pipeline.png`, `fig05_transfer_function_phase.png`.
**Code:** `angular_spectrum_transfer_function` — four lines; ask the learner to
explain what `.astype(np.complex128)` before `np.sqrt` accomplishes.

### Lesson 4 — Evanescent waves, and a real mistake
What happens when `kx² + ky² > k²`. Physical decay. Why reversing it is
ill-posed and refused.
**Then tell the story:** the implementation plan claimed evanescent samples
need `d < λ/2`. That is the condition for the *axis* to reach the cutoff, but
the extreme sample of a 2-D grid is the **corner**, so the real threshold is
`d < λ/√2`. Between 316.5 nm and 447.6 nm only the four corners are
evanescent. The fix was to stop using a scalar rule at all and test the mesh.
**Figure:** `fig04_propagating_vs_evanescent.png` — the middle panel *is* the
error, made visible.
**Code:** `test_m08`.
**Land this:** 1-D intuition applied to a 2-D grid is a recurring trap.

### Lesson 5 — The periodic window
Why the DFT wraps. What zero padding does and does not do.
**Figure:** `fig07_wraparound_padding.png` — the unpadded result is covered in
interference fringes from light re-entering the opposite edge.
**Code:** `test_m30`; the `pad_factor` docstring.
**Land this:** `pad_factor=1` and `pad_factor=2` solve *different problems*.
Neither is "the right answer"; the exact analytic tests need the periodic one.

### Lesson 6 — What counts as evidence
The exact tests (plane wave, `2e-14`) versus the model-limited one (Gaussian,
`1e-6`, floor set by the paraxial approximation).
**Figure:** `fig06_propagation_before_after.png`.
**The key conversation:** why `propagate(+z)` then `propagate(−z)` proves
almost nothing about the sign. Because `H(−z) = conj(H(z))` whichever sign is
used, a completely wrong propagator cancels itself. This was *demonstrated*:
negative control NC-1 flipped the sign, 31 tests failed — and the round-trip
test passed.

### Lesson 7 — Limits and honesty
What Milestone 1 does not prove. The undersampled transfer function nobody
detects. Why band-limited ASM was measured and then *deferred* rather than
shipped. Why no warning was added.
**Read:** `known_limitations.md` §1.1, §1.2, §3; `tests_and_evidence.md` §6.
**Land this:** "we measured it, it did not help, so we did not ship it, and we
wrote down the evidence" is a legitimate and valuable engineering outcome.

---

## 6. Suggested conceptual exercises

1. A plane wave tilted at 5° and one at normal incidence both travel 10 cm.
   Which has accumulated more phase, and by roughly what fraction? (Use
   `kz = k·cos θ`.)

2. Why does propagation leave a plane wave's *amplitude* completely unchanged?
   Answer using only `|e^(iθ)| = 1`.

3. `λ = 633 nm`. For a square grid of pitch `d = 400 nm`, compute the Nyquist
   frequency and the corner radius `√2/(2d)`. Which exceeds `1/λ`? What does
   that tell you about where the evanescent samples are?

4. Why is `d < λ/2` the wrong criterion for evanescence on a 2-D grid, and what
   is the right one for a square grid? What is the right one for an
   anisotropic grid?

5. `H(−z) = conj(H(z))`. Show this from `H = e^(i·kz·z)`. Then explain why a
   forward-then-backward round trip cannot detect a flipped propagation sign.

6. A Gaussian beam with `w₀ = 100 µm` at 633 nm has `z_R = 49.6 mm`. Compute
   `w(z)` at `z = z_R` and at `z = 2·z_R`. Why does the peak intensity fall as
   `(w₀/w(z))²`?

7. The plane-wave test agrees to `2e-14` but the Gaussian test only to `1e-6`.
   Is the Gaussian test worse? Explain what sets each floor.

8. **Harder.** Why must the exact plane-wave test use `pad_factor=1`? What
   physically changes about the problem when you zero-pad a field that fills
   the window?

9. **Harder.** `pad_before = N_pad//2 − N//2` rather than `(N_pad − N)//2`.
   For `N = 7`, `N_pad = 14`, compute both. Which sample lands at the padded
   origin in each case? Why does M0's centring convention force the first?

10. **Harder.** Negative control NC-5 (flipped evanescent branch) was caught by
    only 2 of 291 tests. Is that a weakness of the suite? Explain in terms of
    which grids actually carry evanescent samples.

---

## 7. Suggested code modification exercise

**Add `propagate_to_far_field_angle` — or rather, discover why you should not.**

A tempting API: given a field, return the intensity as a function of
*angle* rather than position, for a very large `z`.

Ask the learner to:

1. Work out, from `sin θ = λ·f`, why the angular spectrum's magnitude
   `|FFT(U)|` *already is* the far-field angular distribution — no propagation
   needed.
2. Write a small script (in `scripts/`, **not** in `src/ohlab/`) that plots
   `|fftshift(fft2(U))|²` against `θx = arcsin(λ·fx)` for a Gaussian source.
3. Compare it against `propagate_angular_spectrum` at a large `z`, converting
   position to angle via `θ ≈ arctan(x/z)`.
4. Explain any discrepancy in terms of §1.1 of `known_limitations.md` — the
   transfer function is badly undersampled at that distance.

**The lesson:** sometimes the right engineering answer is that the feature is
already there under another name, and sometimes the numerical method you were
going to use is the wrong tool at that distance. Both are more valuable than
adding a function.

**Alternative, more mechanical exercise** if they want to write library code:
add a `propagate_angular_spectrum` fast path that accepts a precomputed
transfer function, then measure whether it speeds up 100 repeated propagations
at fixed `(grid, λ, z)`. Deferred item in `known_limitations.md` §4, and
directly useful for Milestone 3.

---

## 8. Notes for the tutor

- **The single most valuable conversation in this milestone** is the NC-1
  result: a deliberate sign flip failed 31 tests while the round-trip test
  passed. It makes "what does this test actually prove?" concrete in a way no
  amount of explanation does.
- **The second is the corner-vs-axis error** (Lesson 4). It was caught during
  planning, corrected before implementation, and is now pinned by a regression
  test and visible in a figure. Present it as a normal, healthy part of
  engineering, not as a failure.
- **Do not present figures as evidence.** `fig07` is persuasive about
  wrap-around, but the evidence is `test_m30`, which compares against an
  analytic solution.
- **`math_conventions.md` is normative.** v0.3 rewrote §3.9 and corrected §3.1;
  the Change Log explains why. If the learner proposes something contradicting
  it, the answer is "that needs a Change Log entry".
- **Be honest about what is not proven.** `tests_and_evidence.md` §6 lists
  seven things, including that hard-edged fields are entirely untested — which
  is exactly what Milestone 2 will introduce.
- **Milestone 2 has not been started.** Do not teach image loading or
  Gerchberg–Saxton yet, however naturally the conversation drifts there.
