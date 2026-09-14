# Milestone Ledger

Authoritative status for Open Holographic Lab. Updated at the end of every
milestone according to the workflow in [`AGENTS.md`](../AGENTS.md).

**Rule:** do not begin a milestone before the previous one is implemented,
tested, its limitations recorded here, and its handoff package written to
`docs/handoffs/milestone_<n>/`.

---

## Status summary

| # | Milestone | Status | Handoff package |
|---|---|---|---|
| — | Scaffolding + normative documentation | **complete** (2026-08-08) | n/a |
| 0 | Field and grid representation | **complete** (2026-08-08) | [`milestone_0/`](handoffs/milestone_0/) |
| 1.x | *Candidate:* band-limited ASM (deferred from M1) | not started | — |
| 1 | Angular Spectrum propagation | **complete** (2026-08-11) | [`milestone_1/`](handoffs/milestone_1/) |
| 2 | Target image loading | not started | — |
| 3 | Gerchberg–Saxton phase retrieval | not started | — |
| 4 | Reconstruction quality metrics | not started | — |
| 5 | Configuration and run artifacts | not started | — |
| 6 | Minimal application layer | not started | — |

---

## Scaffolding (complete)

**Scope.** Git initialization on `main`; project configuration; the two
normative documents. No numerical source code.

**Delivered.**

| File | Purpose |
|---|---|
| `.gitignore` | Excludes venv, caches, build output, `runs/`, raw arrays |
| `pyproject.toml` | setuptools + `src/` layout; runtime deps NumPy/SciPy only; dev extra; pytest config |
| `README.md` | Orientation, install, test commands |
| `CLAUDE.md` | Working model, engineering rules, milestone workflow, handoff package spec |
| `docs/math_conventions.md` | **Normative** conventions, v0.1 |
| `docs/milestones.md` | This file |
| `src/ohlab/__init__.py` | Package marker; single source of the version string |
| `src/ohlab/py.typed` | PEP 561 inline-types marker |
| `tests/test_packaging.py` | Toolchain smoke tests (no physics) |

**Verified.** Editable install on Python 3.11.9; `import ohlab` from outside
the repository; `pytest` green; runtime dependency set is NumPy + SciPy only.

**Deliberately deferred.** `examples/`, `scripts/`, `runs/`,
`docs/handoffs/`, licence choice, `authors` metadata, CI.

---

## Milestone 0 — Field and grid representation

**Status: complete** (2026-08-08). **188 tests passing.**

**Scope.** An exactly-specified, exactly-tested representation of a sampled
complex optical field and its coordinate and frequency grids. No physics
beyond definitions.

| Module | Contents |
|---|---|
| `src/ohlab/units.py` | SI multipliers `NM`, `UM`, `MM`, `CM`, `DEG` |
| `src/ohlab/validation.py` | Shared argument validators (shape, dtype, finiteness, positivity) |
| `src/ohlab/grid.py` | `SamplingGrid` — frozen; spatial and frequency grids, Nyquist limits, serialization |
| `src/ohlab/field.py` | `ComplexField` — frozen; amplitude / phase / intensity / power, constructors, derived-field operations |

**Acceptance criteria — all met.**

- [x] `pytest` fully green; exact output recorded in the handoff package
- [x] `x[nx//2] == 0.0` exactly, for even and odd `nx`
- [x] `fx_fft` equals `np.fft.fftfreq(nx, dx)` bit-for-bit
- [x] `ifftshift(fx_centered) == fx_fft` exactly
- [x] An on-grid plane wave lands in the single predicted FFT bin, with the
      predicted sign, for all four `(±fx₀, ±fy₀)` quadrants
- [x] Parseval holds in the `norm="backward"` form of `math_conventions.md` §3.7
- [x] Multiplying by `exp(iψ)` leaves `intensity` and `power` unchanged
- [x] Every public function carries a full type hint and a docstring naming units
- [x] No import of matplotlib, PIL, or any I/O library anywhere in `src/ohlab/`
- [x] Each of `math_conventions.md` §3.2–§3.8 maps to at least one named test

**Explicitly out of scope.** Propagation; FFT of a field outside the
convention tests; image loading; plotting; lenses, apertures, or any optical
element; configuration files; CLI.

**Recorded limitations.** Full detail in
[`handoffs/milestone_0/known_limitations.md`](handoffs/milestone_0/known_limitations.md).
Summary:

1. **Verified against NumPy 2.4.6 only.** The bit-for-bit frequency-axis tests
   depend on `numpy.fft.fftfreq`'s internal evaluation order, which is not a
   documented API guarantee. A future NumPy could break G-10/G-11 without
   being wrong. NumPy is deliberately left unpinned; the tests will fail
   loudly if this happens.
2. **Milestone 0 is bookkeeping, not physics.** Nothing here can be
   "physically correct" — there is no propagation to be right or wrong about.
3. **No sampling-adequacy check.** `SamplingGrid` will build a grid far too
   coarse for a given problem without complaint. Adequacy criteria are
   Milestone 1.
4. **`intensity` uses `Re² + Im²`**, which overflows for amplitudes beyond
   about `1e154`. Chosen deliberately so that `intensity == amplitude**2` is a
   genuine cross-check between two code paths rather than a tautology.
5. **No caching.** Every derived array is recomputed on access. Safe, but a
   propagation loop should hoist grid arrays out. Deferred to Milestone 1
   where there is a hot path to profile.
6. **Conventions are internally consistent, not externally verified.** The
   claim that these match Goodman is a citation, not a test.

**Negative controls performed.** Three deliberate mutations of the
implementation were injected and confirmed to fail the suite: the division
form of the frequency axis (fails G-10/G-11, *only* at realistic pitch), a
one-pixel spatial origin shift (fails G-07/G-08/G-09), and a flipped FFT
kernel sign (fails C-04). Recorded in `tests_and_evidence.md`.

---

## Milestone 1 — Angular Spectrum propagation

**Status: complete** (2026-08-11). **291 tests passing** (188 from M0, 103 new).

**Scope.** `src/ohlab/propagation.py` implementing `math_conventions.md` §3.9,
validated against analytic ground truth.

**Public API.** Two functions, no class — a propagation is a pure function of
`(field, distance)` with no state to carry.

| Function | Purpose |
|---|---|
| `propagate_angular_spectrum(field, *, distance_m, pad_factor=2)` | Propagate a `ComplexField` by a signed distance |
| `angular_spectrum_transfer_function(grid, *, wavelength_m, distance_m)` | The transfer function `H` on the FFT-ordered mesh |

**Acceptance criteria — all met.**

- [x] All 188 M0 tests still green
- [x] Zero distance returns the input object itself (documented contract)
- [x] On-grid plane wave acquires exactly `exp(i·kz·z)` — worst relative error `1.93e-14`
- [x] Three-component superposition — `5.21e-15`
- [x] Uniform field acquires `exp(i·k·z)`, error `0.52–0.83 ×` the `k·z·ε` floor
- [x] Power conserved exactly on the periodic window — `≤ 3.5e-16`
- [x] `|H| = 1` on the propagating branch to `2.22e-16`; evanescent decay tested separately
- [x] Evanescent detection from the discrete mesh, with a corner-only regression test
- [x] Backward propagation refused when evanescent samples exist
- [x] Padding/crop alignment bit-exact at all parities
- [x] Wrap-around characterised; padding improves agreement `1381×`–`1634×`
- [x] Gaussian beam vs analytic — `8.1e-7` to `1.0e-6`, floor set by the paraxial model
- [x] Gouy phase at `z = z_R` measured as `0.785398` rad (`π/4`), error `4.0e-11`
- [x] **10 of 10 negative controls caught; 0 test gaps**
- [x] Sign convention externally verified (§3.1)
- [x] No UI/plotting/I-O import in `src/ohlab/`

**Explicitly out of scope, and not implemented.** Fresnel or Fraunhofer
propagation; band-limited ASM; target image loading; Gerchberg–Saxton; metrics;
CLI; hardware.

**Recorded limitations.** Full detail in
[`handoffs/milestone_1/known_limitations.md`](handoffs/milestone_1/known_limitations.md).
Summary:

1. **Band-limited ASM is not implemented.** Probes showed zero-padding
   dominates it for every case tested, and that band-limiting can *worsen*
   agreement when combined with padding by truncating genuine signal. Recorded
   as a candidate M1.x enhancement with the evidence preserved.
2. **Padding is not a correctness guarantee.** It exchanges a periodic
   boundary for a zero-embedded one. Light reaching the padded edge wraps
   again.
3. **No sampling-adequacy check is enforced.** The transfer function can be
   undersampled at long range with no diagnostic raised.
4. **The Gaussian comparison floor is the paraxial model**, ~`4e-6`, not
   float64. Its tolerance must not be tightened.
5. **Peak Python-visible allocation is 4.5× (unpadded) or 22× (2× padded) a
   single *source* field array** — equivalently 4.5×–5.5× a single array of the
   *computational* grid. At 1024² with `pad_factor=2` that is 352 MB of NumPy
   allocation and a 364 MB process working-set peak, for a 1.2 s call. Relevant
   to M3.
6. Verified on NumPy 2.4.6 / Windows only.

**Negative controls performed.** Ten deliberate mutations injected and all ten
caught: propagation sign flip, `fy` dropped, centred-vs-FFT ordering, wrong
`kz` sign, evanescent branch flip, omitted inverse FFT, distance unit error,
crop misalignment, `pad_factor` ignored, and `numpy.pad`-style centring.
Recorded verbatim in `tests_and_evidence.md`.

---

## Corrective maintenance — 2026-09-14

Approved M0/M1 categories A and B; this is not a new milestone. M0 and M1
remain complete, and their acceptance counts and historical evidence above
remain preserved. The current suite is **323 passing tests** (291 baseline
plus 32 regressions); the historical M1 file split is 72 mechanics / 31
analytic cases, correcting the original 71/32 prose attribution.

Production changes are limited to the exact `-pi` to `+pi` phase endpoint
representation and corrected diffraction-angle diagnostic text. Propagation
has no executable change. Explicit tolerances, literal byte-identity tests,
independent physical-coordinate Fourier sums, dated mathematical errata,
and recovered Gaussian-reference provenance are recorded in the
[consolidated correction and tutor errata](corrections/m0_m1_contract_and_evidence.md).
Original measurements and transcripts remain intact; historical sign and
"0 test gaps" claims above must be read with that dated clarification.

Category C remains deferred to the future M2 I/O design. Milestone 2 and all
later work remain not started.

---

## Milestone 2 — Target image loading

**Status:** not started.

**Scope.** `src/ohlab/io/` — grayscale image to normalized target amplitude.
Defines the amplitude-vs-intensity convention for targets, resizing policy,
and normalization. First code permitted to touch disk; stays out of the
numerical core.

---

## Milestone 3 — Gerchberg–Saxton phase retrieval

**Status:** not started.

**Scope.** `src/ohlab/algorithms/gerchberg_saxton.py`. Deterministic seeded
initial phase; per-iteration loss history; explicit convergence and stopping
criteria; the amplitude/phase projection steps expressed via
`ComplexField.with_amplitude` / `.with_phase`.

---

## Milestone 4 — Reconstruction quality metrics

**Status:** not started.

**Scope.** `src/ohlab/metrics.py`. Normalized MSE, PSNR, diffraction
efficiency, uniformity, and the normalization convention each assumes.

---

## Milestone 5 — Configuration and run artifacts

**Status:** not started.

**Scope.** `src/ohlab/io/config.py` and `artifacts.py`. A run must be
reproducible bit-for-bit from its saved configuration. Exports phase map,
reconstruction, configuration, metrics, and loss history to `runs/`.

---

## Milestone 6 — Minimal application layer

**Status:** not started.

**Scope.** A thin CLI or minimal UI over the existing library. No physics.

---

## Open project decisions

Deferred, non-blocking. Each needs a decision before the corresponding event.

| # | Decision | Needed before |
|---|---|---|
| D-1 | Software licence (`license` field in `pyproject.toml`) | Making the repository public |
| D-2 | `authors` metadata — what name/email, if any, appears in published package metadata | Making the repository public |
| D-3 | Continuous integration (GitHub Actions?) | Any external contribution |
| ~~D-4~~ | ~~Whether `figures/` PNGs are committed or regenerated on demand~~ | **Resolved 2026-08-08: committed.** The tutoring session reads this repository through its public URL and cannot execute code, so the figures must be present as files. They are small PNGs (~815 KB total) and are regenerable at any time via `scripts/make_m0_figures.py`. |
