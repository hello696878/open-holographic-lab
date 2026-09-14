# Milestone 1 — Implementation Summary

**Status: complete.** 291 tests passing (188 from Milestone 0, 103 new).
Verified on Python 3.11.9, NumPy 2.4.6, SciPy 1.17.1, pytest 9.1.1
(Windows 11).

**Correction note — 2026-09-14.** The status and measurements below are the
original milestone record. The original file-count split of 71 mechanics /
32 analytic tests is inaccurate: baseline `1b2e755` contains **72 / 31**,
still 103 M1 cases and 291 total. Conjugacy in the design discussion applies
only to real `kz`; backward evanescent propagation remains refused. See the
[maintenance evidence and tutor errata](../../corrections/m0_m1_contract_and_evidence.md)
for current corrections and the new suite count. Original transcripts and
historical count claims below are retained with this clarification.

---

## What was implemented

Free-space propagation of a `ComplexField` by the Angular Spectrum Method:

```
U(x,y,0) --FFT2--> A(fx,fy;0) --xH--> A(fx,fy;z) --IFFT2--> U(x,y,z)
```

A single module, `src/ohlab/propagation.py`, exposing **two functions and no
class**. A propagation is a pure function of `(field, distance)`; there is no
state to carry, so a class would only add ceremony.

| Function | Responsibility |
|---|---|
| `propagate_angular_spectrum(field, *, distance_m, pad_factor=2)` | Propagate a field by a signed distance in metres |
| `angular_spectrum_transfer_function(grid, *, wavelength_m, distance_m)` | The transfer function `H` on the FFT-ordered frequency mesh |

### Key design decisions

1. **One transfer-function expression for every distance.**
   `H = exp(+i·kz·z)` with `Im{kz} ≥ 0`, full stop. There is deliberately no
   separate formula for `z < 0`: the same expression already yields the
   conjugate propagator, and a second formula is an invitation to a sign
   error. Casting the radicand to `complex128` before `np.sqrt` selects the
   required branch with no conditional logic at all.

2. **Evanescence is determined from the discrete frequency mesh.** Not from a
   pitch threshold. The plan for this milestone originally claimed evanescent
   samples require `d < λ/2`; that is the *axis-only* condition and it is
   wrong. The extreme sample of a square grid is the **corner** of the Nyquist
   square, so the true condition is `d < λ/√2`. Between 316.5 nm and 447.6 nm
   (at 633 nm) the evanescent region is populated *only near the four
   corners* — 97 samples of 4096 at `d = 400 nm`. A regression test pins
   exactly that case.

3. **Backward propagation is refused when evanescent samples exist.**
   Reversing evanescent decay is ill-posed: measured `|H|` reaches `4.3×10⁸`
   after one micrometre and `inf` within a hundred. Zeroing would misreport
   what was computed; clamping would invent a number. On every realistic grid
   this error cannot fire.

4. **Zero distance returns the input object itself.** `ComplexField` is
   immutable, so `result is field` is safe, and it makes the identity exact
   rather than accurate to ~`1.6e-15` through an FFT round trip. The contract
   is documented and asserted with `is`.

5. **Padding preserves the Milestone 0 origin convention exactly.**
   `pad_before = N_pad//2 − N//2`, so original index `N//2` lands on padded
   index `N_pad//2` and every physical coordinate is preserved bit-exactly at
   both parities. `numpy.pad`'s default placement is not used — it would define
   the physical alignment implicitly and disagrees for odd sizes.

6. **Padding is presented as a boundary-condition choice, not an improvement.**
   `pad_factor=1` solves the periodic problem; `pad_factor>1` solves a
   zero-embedded one. Padding reduces wrap-around but is not a guarantee of
   physical correctness, and the documentation says so in those words.

### Normative-document changes

`docs/math_conventions.md` raised to **v0.3**:

- **§3.1** — records the external verification of the time convention and
  propagation sign; downgrades the Goodman citation to an unverified secondary
  attribution; corrects the v0.1 mislabelling of `exp(−iωt)` as the
  "engineering" convention (it is the *physicists'* convention); states
  explicitly that NumPy fixes the DFT kernel only, **not** the time convention,
  and that the three sign choices form a mutually verified set.
- **§3.9 rewritten** into five subsections: the single expression (§3.9.1),
  mesh-based evanescence detection with the corrected threshold (§3.9.2), the
  evanescent policy (§3.9.3), boundary conditions and padding alignment
  (§3.9.4), and deferred band-limited ASM (§3.9.5).

**No mathematical convention was changed.**

---

## What remains out of scope

Not implemented, and not to be added without an explicit decision:

- **Band-limited ASM** — deferred; see `known_limitations.md` §2 for the
  measured evidence. Recorded as a candidate M1.x enhancement.
- **Fresnel and Fraunhofer propagation** — neither approximation is used
  anywhere; the implemented method is exact and non-paraxial.
- Target image loading, Gerchberg–Saxton, phase retrieval, reconstruction
  metrics, CLI, Streamlit, hardware interfaces, SLM models, PyTorch, GPU, RGB,
  multi-plane holography.
- Any sampling-adequacy warning or heuristic. A candidate diagnostic
  (`u_limit / f_nyquist`) was probed and found to be a **poor predictor of
  actual error**, so it was not shipped.

---

## Files created

| Path | Purpose |
|---|---|
| `src/ohlab/propagation.py` | The propagator (~330 lines with docstrings) |
| `tests/test_propagation.py` | 71 tests: transfer function, validation, zero-distance contract, evanescent policy, padding alignment, power, round trip, wrap-around |
| `tests/test_propagation_analytic.py` | 32 tests: plane wave, superposition, uniform field, symmetry, Gaussian beam |
| `scripts/make_m1_figures.py` | 7 figures. Outside the numerical core |
| `docs/handoffs/milestone_1/` | This package + `figures/` |

## Files modified

| Path | Change |
|---|---|
| `src/ohlab/__init__.py` | Exports the two propagation functions |
| `docs/math_conventions.md` | → v0.3 (§3.1, §3.8, §3.9) |
| `docs/milestones.md` | M1 complete, limitations, M1.x candidate row |
| `README.md` | Status, propagation usage snippet |
| `tests/test_fft_conventions.py` | **`test_c08` only** — the public-API assertion now includes the two new names. See "Deviations" below |

## Files deliberately untouched

`src/ohlab/grid.py`, `field.py`, `units.py`, `validation.py`, `py.typed`;
`tests/test_grid.py`, `test_field.py`, `test_plane_wave.py`,
`test_validation.py`, `test_units.py`, `test_packaging.py`, `conftest.py`,
`_helpers.py`; `scripts/make_m0_figures.py`; the entire `milestone_0/` handoff;
`pyproject.toml`, `.gitignore`, `CLAUDE.md`.

### Deviation from the plan

The plan stated all Milestone 0 test files would be untouched. One was:
`tests/test_fft_conventions.py::test_c08` asserts the exact contents of
`ohlab.__all__`, so adding two public names necessarily fails it. The
assertion was updated to list the M0 and M1 API sets explicitly, and
deliberately kept as an exact-set comparison rather than weakened to a subset
check, so that a future addition to `__all__` remains a conscious act. No
other M0 test was modified.

---

## Exact commands

### Install (once)

```
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --use-feature=truststore --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### Test

```
.\.venv\Scripts\python.exe -m pytest -q
```

Propagation only:

```
.\.venv\Scripts\python.exe -m pytest tests\test_propagation.py tests\test_propagation_analytic.py -v
```

### Regenerate the figures

```
.\.venv\Scripts\python.exe scripts\make_m1_figures.py
```

### Minimal run

```
.\.venv\Scripts\python.exe -c "from ohlab import *; from ohlab.units import *; g=SamplingGrid.square(n=256,pitch=4*UM); f=ComplexField.uniform(grid=g,wavelength_m=633*NM); print(propagate_angular_spectrum(f,distance_m=50*MM).power)"
```

---

## Current milestone status

| # | Milestone | Status |
|---|---|---|
| — | Scaffolding + normative documentation | complete |
| 0 | Field and grid representation | complete — 188 tests |
| **1** | **Angular Spectrum propagation** | **complete — 291 tests total** |
| 1.x | *Candidate:* band-limited ASM | not started |
| 2 | Target image loading | **not started** |
| 3 | Gerchberg–Saxton phase retrieval | not started |
| 4 | Reconstruction quality metrics | not started |
| 5 | Configuration and run artifacts | not started |
| 6 | Minimal application layer | not started |

**Milestone 2 has not been started.**
