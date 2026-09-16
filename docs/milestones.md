# Milestone Ledger

Authoritative status for Open Holographic Lab. Updated at the end of every
milestone according to the workflow in [`AGENTS.md`](../AGENTS.md).

The status summary and each milestone's dated entry show current acceptance.
Older milestone and corrective-maintenance sections remain historical
snapshots; their counts and deferred-work statements describe their own dates.

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
| 2 | Target image loading | **complete** (2026-09-16) | [`milestone_2/`](handoffs/milestone_2/) |
| 3 | Gerchberg–Saxton phase retrieval | **complete** (2026-09-16) | [`milestone_3/`](handoffs/milestone_3/) |
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

**Status: complete** (2026-09-16). **491 tests passing**: all 323 accepted
baseline cases plus 168 new cases (70 target-array, 47 image-boundary,
51 architecture/RNG guard cases). Existing numerical regressions are retained.

**Scope.** Pure `ohlab.targets` conversions and the optional
`ohlab.io.images.load_target_intensity` PNG boundary. The approved strict-size
policy preserves `(ny, nx)` orientation and caller-supplied SI pitches.
`I_target = g / 255`, `A_target = sqrt(I_target)`; all-zero targets are valid.
Normative contract: `math_conventions.md` §3.12, version 0.5.

**Acceptance criteria — all met.**

- [x] Source 8-bit grayscale PNG, color type 0, decoded mode L; content-based
      identification independent of filename extension
- [x] Transparency, low/high bit depths, unsupported color modes, non-PNG,
      single-frame APNG and multiframe APNG rejected
- [x] Declared IHDR dimensions checked before payload reading/full decoding;
      final decoded shape checked independently
- [x] Integrity verification and pixel decoding use separate reopened image
      objects; CRC-valid malformed compressed pixels exercise decoding failure
- [x] Filesystem exception types preserved; identified decoder failures carry
      path/stage and chained cause; file/stream/image resources closed
- [x] Independent 80-digit Decimal references cover all 256 codes; maximum
      amplitude absolute error and amplitude-squared residual each `1.11e-16`
- [x] Cross-image brightness, blank/low inputs, rectangular mixed-parity
      orientation, invalid arrays, fresh ownership and nonmutation validated
- [x] Lazy optional Pillow import; base/dev requirements and root exports
      unchanged; only the decoder module receives the narrow PIL permission
- [x] Five targeted mutations detected, with source/test hash restoration
      checks and a passing full suite afterward; this is finite test evidence
- [x] Standalone default and explicit-path demo verified headlessly; three
      figures visually reviewed and regenerated with identical SHA-256 hashes
- [x] Six handoff documents completed in
      [`handoffs/milestone_2/`](handoffs/milestone_2/)

Exact commands/output, tolerance measurements, dependency versions and
negative-control transcripts are in
[`tests_and_evidence.md`](handoffs/milestone_2/tests_and_evidence.md).
The final suite used the existing interpreter and a fresh repository-local
pytest `--basetemp` after Windows denied access to its default temp root.
No package was installed, upgraded or rebuilt.

**Recorded limitations.** No resize/pad/crop, gamma/profile conversion,
thresholding or normalization beyond fixed `/255`. Targets are design
intensity/amplitude, not calibrated irradiance, a complex field or an SLM
phase pattern. Encoded files are buffered after header validation; this is
not a streaming or exhaustive malformed-PNG validator. Pillow 12.3.0 was
tested; the declared `pillow>=10.0` range has not been exhaustively tested.
Existing propagation/sampling limitations remain unchanged. See the full
[limitations](handoffs/milestone_2/known_limitations.md).

Category C's narrow I/O boundary is now implemented. Historical M0/M1
handoffs, correction evidence, numerical source, AGENTS.md, CLAUDE.md and
existing figures remain unchanged. Milestone 3 and all later work remain
not started; there is no phase assignment or hologram computation.

---

## Milestone 3 — Gerchberg–Saxton phase retrieval

**Status: complete** (2026-09-16). **668 tests passing**: all 491 accepted
baseline cases plus 177 new cases (160 contract/operator/fixture/PNG cases,
17 independent direct-reference/fixed-point/analytic cases).

**Scope.** `ohlab.algorithms.gerchberg_saxton` and frozen
`GerchbergSaxtonResult`: single-plane phase-only synthesis on one complete
periodic lossless ASM grid, equivalent to explicit `pad_factor=1`. No crop,
padding or evanescent samples. The approved fixed-cycle/last-iterate policy
replaces the earlier provisional convergence-stopping scope. Local projections
implement the M3 exact-zero phase tie without changing `ComplexField.phase`.
Normative contract: `math_conventions.md` §3.13, version 0.6.

**Acceptance criteria — all met.**

- [x] All existing tests retained unchanged; root executable exports/version,
      existing numerical implementations, loader and dependencies preserved
- [x] Strict plain native-float64 shape/domain/ownership validation, positive
      usable powers, symmetric power compatibility (`rtol=1e-12`, absolute
      tolerance zero), and no hidden normalization or target scaling
- [x] Explicit seed or phase, nonuniform prescribed source amplitude,
      canonical phase with local exact-zero tie, zero iterations, zero distance,
      sparse zeros, signed distance and evanescent rejection verified
- [x] Last source and actual forward reconstruction returned; all N+1 residuals
      measured before target replacement; returned phase independently rebuilt
      and propagated through public ASM
- [x] Public transfer functions constructed once per direction; both local
      operator directions checked against public propagation, with inverse and
      adjoint identities on the lossless grid
- [x] Scalar physical-coordinate direct-DFT complete iterations on (3,5) and
      (5,8), signed 0.2 mm, N=0/1/3; source/reconstruction discrepancies below
      2.31e-15 of input peak; constructed fixed points and analytic plane wave
- [x] All three original quantized planning fixtures and seeds 0/1/2/3 retain
      50 cycles and satisfy rho50 < 0.05 and rho50 < 0.1*rho0; no seed selection
- [x] Seven in-memory mutations across six categories detected; 52 assertion
      failures, no collection/setup/teardown failures; source/test hashes
      unchanged and complete suite passed afterward
- [x] Actual synthetic-PNG-to-M2-to-M3 path verified; continuous designs and
      decoded targets reported separately; analytic unwrapped transfer-phase
      differences measured on physically sorted adjacent frequencies
- [x] Default and explicit-path headless demos verified; three useful figures
      visually reviewed and regenerated with identical SHA-256 values
- [x] Shipped runtime/memory measured separately from planning probes; paired
      otherwise-identical kernels measured the benefit of reusing public H
- [x] Six handoff documents complete in
      [`handoffs/milestone_3/`](handoffs/milestone_3/)

Review found a rounded-cutoff geometry whose summed-frequency test passes
while the public H radicand becomes slightly negative. M3 rejects that
unrepresentable lossless domain, including zero-distance/iteration requests,
without clamping or changing M1. Exact-grazing acceptance is tested separately.

**Recorded limitations.** This is a discrete periodic synthesis model, not
arbitrary isolated-aperture optical validation. Power compatibility is necessary
but insufficient for exact synthesis; there is no unique-phase or arbitrary
convergence promise. The residual is normalized squared amplitude error, not
percent accuracy, intensity MSE or efficiency. Tiny/subnormal intermediate
arithmetic reported unusable by NumPy is rejected rather than rescaled.
The ideal phase figures are not calibrated SLM drive images. Demonstration
illumination is explicitly configured separately for each target. Headless
rendering and the stated Windows environment were tested; interactive GUI and
cross-platform bit identity were not. Full details and exact commands/output
are in [tests and evidence](handoffs/milestone_3/tests_and_evidence.md) and
[known limitations](handoffs/milestone_3/known_limitations.md).

Only the approved twenty paths are included. M0/M1/M2 historical evidence,
AGENTS.md, CLAUDE.md, existing tests and old figures remain unchanged.
Milestone 4 and deferred enhancements are not started.

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
