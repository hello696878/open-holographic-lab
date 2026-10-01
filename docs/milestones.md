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
| 4 | Reconstruction quality metrics | **complete** (2026-09-20) | [`milestone_4/`](handoffs/milestone_4/) |
| 5 | Configuration and run artifacts | **complete** (2026-09-23) | [`milestone_5/`](handoffs/milestone_5/) |
| 6 | Minimal application layer | **complete** (2026-09-29; closeout recorded 2026-09-30) | [`milestone_6/`](handoffs/milestone_6/) |
| 7 | Editable 2D target designer | **complete** (2026-09-30; closeout recorded 2026-10-01) | [`milestone_7/`](handoffs/milestone_7/) |
| V0 | Aligned sequential virtual optics foundation | implementation acceptance complete; publication checks follow (2026-10-01) | [`v0/`](handoffs/v0/) |

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

**Status: complete** (2026-09-20). **904 tests passing**: all 668 accepted
baseline cases plus 236 new metric contract/reference/integration cases.

**Scope.** Five keyword-only pure-array functions in `ohlab.metrics`:
intensity MSE, target-squared-norm intensity NMSE, explicit-range intensity
PSNR, signal-region power fraction and regional population CV. These precise
names and definitions replace the earlier provisional efficiency/uniformity
labels. Normative contract: `math_conventions.md` §3.14, version 0.7; §2.1
clarifies raw MSE scale dependence without changing field normalization.

**Acceptance criteria — all met.**

- [x] Plain native-float64 nonempty 2-D finite nonnegative intensities; exact
      comparison/mask shapes; values above one, read-only and strided inputs;
      built-in float outputs and no mutation/retention
- [x] Complete validation before exact shortcuts; numerical signed-zero
      equality for PSNR; required explicit positive range; no approximate
      equality, clipping, normalization, inferred masks or epsilon denominators
- [x] Defined zero results separated from undefined ratios; positive-constant
      CV exactly zero, empty signal selection valid with usable positive total,
      negative PSNR and CV above one preserved
- [x] Strict local arithmetic failure handling, unsupported extreme scales
      documented, and caller NumPy error settings restored on success/failure
- [x] Hand-array identities and independent Decimal references; scaling,
      brightness, population-CV, leakage and explicit-range behavior verified
- [x] Actual M3 reconstruction evaluated; returned phase independently rebuilt
      through public ASM; M3 amplitude residual remains separately labeled;
      target/mask/field/history bytes preserved
- [x] Seven isolated mutations each produced the independent expected assertion
      failure, with no collection/setup/teardown or other-call failures; all 29
      source/test file hashes unchanged; full suite passed afterward
- [x] Separate fixed seed-0 64x64 example passed headlessly; explicit radius-15
      signal disk and separate intended-flat fixtures; shared display/error
      scales preserve brightness errors and reconstruction overshoot
- [x] Two figures visually inspected and regenerated twice with identical hashes
- [x] Six handoff documents completed in
      [`handoffs/milestone_4/`](handoffs/milestone_4/); all 85 protected
      pre-existing tracked files remain byte-identical

The actual smooth-spot reconstruction has intensity MSE
`4.81562267041563932e-04`, NMSE `1.11723641621580324e-02`, PSNR
`3.31734754969381669e+01` dB with data_range=1, and regional fraction
`8.38568123674199528e-01`. Its separate M3 amplitude residual remains
`1.71252990524567231e-02`. These are shipped-function measurements, not
replacement historical planning numbers or new GS convergence thresholds.

**Recorded limitations.** Metrics assume corresponding pixels on one declared
scale. NMSE uses a squared intensity norm, not optical power. PSNR's reference
range is explicit and exact equality returns infinity. Regional power fraction
does not establish brightness fidelity or calibrated efficiency. CV describes
population variation only where its selected region is meaningfully interpreted;
it can exceed one. Extreme finite inputs can have unsupported arithmetic and
raise instead of being rescaled. Validation covers finite fixtures and the stated
Windows environment, not every platform, dependency version or physical model.
Interactive GUI operation was not separately automated. Exact commands, output,
tolerances, negative-control code and limitations are in the
[M4 evidence](handoffs/milestone_4/tests_and_evidence.md) and
[limitations](handoffs/milestone_4/known_limitations.md).

Only the approved fifteen paths are included. Existing numerical implementations,
tests, root exports, dependencies, engineering instructions and M0-M3 evidence,
examples and figures are unchanged. M5, M6 and deferred enhancements are not
started; no teaching completion is inferred.

---

## Milestone 5 — Configuration and run artifacts

**Status: complete** (2026-09-23). **1291 tests passing, 1 skipped**: all
904 accepted baseline cases plus 248 configuration and 139 artifact cases
passing. One additional real-file-symlink case requires Windows privileges
unavailable to this account; the separate real junction test passes.

**Scope.** Immutable `ohlab.io.config.RunConfig` and four functions in
`ohlab.io.artifacts`: save a computed run, verify, load and replay. Schema v1
captures normalized M2 design intensity, explicit source illumination,
unchanged M3 initialization and requested M4 metrics. It stores actual complex
source/reconstruction fields alongside inputs, derived outputs and history.
Normative contract: `math_conventions.md` §3.15, version 0.8.

**Acceptance evidence.**

- [x] Existing numerical implementations, tests, architecture guards, package
      initializers, dependencies and historical evidence remain unchanged
- [x] Owned C-order input snapshots preserve dtype and element bits; nested
      configuration ownership, caller nonmutation and single-solve capture tested
- [x] Strict deterministic JSON, explicit PSNR infinity, NPY 1.0 header/payload
      checks, conditional inventory and hashes-before-decoding validated
- [x] Artifact integrity, independent source/environment qualification and
      actual numerical comparison reported separately; no tolerance fallback
- [x] Twelve cases cover both initialization modes, N=0/5 and signed/zero
      distance; explicit metric ranges, distinct masks and complex signed zeros
- [x] Rehashed wrong metrics, changed settings and changed complex outputs
      demonstrate that integrity or matching metadata does not imply replay
- [x] Exclusive sibling staging, manifest-last publication, owned-only cleanup,
      write/fsync/manifest/rename failures and appearing destinations tested
- [x] Seven in-memory negative controls detected by 23 intended assertions;
      no collection/setup failures counted; 33 source/test files hash-identical
      afterward and the complete suite passed after process-local restoration
- [x] Fresh-process relocation retained all 12 bundle-file hashes and passed
      14 comparisons after original PNG/bundle paths became unavailable
- [x] Headless default example verified with dirty precommit provenance;
      two explanatory figures visually inspected and regenerated identically
- [x] Six handoff documents completed in
      [`handoffs/milestone_5/`](handoffs/milestone_5/)

Precommit example and relocation comparisons pass in explicit diagnostic mode
while qualification correctly remains unqualified. Synthetic caller-source
metadata in policy tests is not executing-code attestation. The approved
publication workflow separately requires a fresh qualified example after the
single clean M5 commit and before push; its actual SHA/output belongs in ignored
run artifacts and the completion report, avoiding self-referential commits.

Candidate validation intermittently encountered Windows directory-rename
error 5, including outside the sandbox; a 100-save probe did not reproduce it.
The cause is unconfirmed. Publication now retries only that error while the
destination remains absent: at most four attempts and 10/30/100 ms waits.
Eight direct cases verify retry success, exhaustion, destination appearance,
later nonretryable errors and other errors/platforms. Final full-suite output
and all observed failures remain distinguished in the
[tests and evidence](handoffs/milestone_5/tests_and_evidence.md).

**Recorded limitations.** Hashes are relative to an unsigned manifest, not
authorship. Qualification is a metadata policy, not universal cross-platform
determinism. Unqualified default replay reports `not_run`; explicit diagnostic
comparison never upgrades qualification. Loading is bounded-format validation,
not a general hostile-input resource framework. Publication has no locking,
overwrite, cross-filesystem fallback or power-loss durability guarantee;
Windows retry is bounded and can still fail. Existing optical and metric
limitations remain. See the complete
[API/schema](handoffs/milestone_5/implementation_summary.md) and
[limitations](handoffs/milestone_5/known_limitations.md).

Only the approved seventeen paths are included; all 97 protected pre-existing
tracked files remain byte-identical. Generated bundles remain ignored. M6 and
deferred enhancements are not started; teaching completion is not inferred.

**Publication resumed — 2026-09-29.** Automatic approval review previously
could not complete staging because of an account usage limit; no commit or
push occurred then. On resumption, main/HEAD/live remote still matched the
accepted M4 baseline, the 33 source/test file hashes matched the validated
candidate, and all 97 protected files remained unchanged. A fresh full suite
returned **1291 passed, 1 skipped in 16.11s**. This separately dated rerun
preserves the original September 22–23 evidence. Clean-commit replay and
three-way publication verification are recorded in the completion report.

---

## Milestone 6 — Minimal application layer

**Status: implementation and precommit acceptance complete** (2026-09-29).
**1396 tests passing, 1 skipped**: the unchanged 1292-case M5 baseline plus
105 new M6 cases (68 controller/presentation, 20 installed Streamlit AppTest,
17 architecture/configuration). The existing Windows file-symlink privilege
skip and its explanation remain unchanged.

**Scope.** One local Streamlit workbench over the existing M2–M5 public APIs,
with Traditional Chinese explanations and English scientific terms. It creates
UUID-named bundles, displays saved arrays/settings/metrics, and explicitly
loads, refreshes or replays completed runs. It adds no numerical model or
bundle-schema change.

**Precommit acceptance evidence.**

- [x] Constrained wheel-only installation added Streamlit 1.64.0 and 31
      necessary missing dependencies; all 20 pre-existing distributions retain
      their versions, metadata hashes and locations. Pip check, imports and
      installed uploader/AppTest API probes passed.
- [x] Original index-disabled dry-run preserved; separately recorded retry
      used PyPI and a copied child environment with `PIP_NO_INDEX="0"` only.
      Parent/persistent settings, proxy/certificate configuration and existing
      packages were not changed.
- [x] Unchanged pre/post-install suites each passed 1291 cases with one skip;
      the final full candidate suite passed 1396 cases with that same skip.
- [x] Immutable submissions, byte-based upload identity, consumed operation
      tokens, app resource/path limits and separation of persistence from
      presentation failure validated through real controller/API tests.
- [x] Installed Streamlit AppTest covers explicit action wiring, stale draft
      labels, upload replacement, statuses, error recovery and post-save
      presentation failure; numerical core/controller imports exclude Streamlit.
- [x] Five process-local negative controls each caused the intended detecting
      assertion, with no setup/collection failure counted. Restoration hashes
      and the later full suite are recorded separately.
- [x] Actual Chrome file-picker uploads, same-name/same-size replacement,
      invalid RGB rejection and recovery, existing M5 loading, strict/explicit
      diagnostic replay, reload and fresh-session reopening all performed.
- [x] Real rapid clicks plus an old-button event received while busy produced
      one accepted submission and one published bundle. A documented
      process-local callback pause exposed the queued-event window; no browser
      events or successful results were fabricated.
- [x] Loopback-only launch resolves app imports without a PYTHONPATH change;
      CORS/XSRF stay enabled, telemetry/file watching/run-on-save/fast reruns
      stay disabled. Two genuine UI screenshots and six handoffs are in
      [`handoffs/milestone_6/`](handoffs/milestone_6/).

Candidate source is honestly dirty/unqualified. Strict candidate replay reports
integrity `passed`, qualification `unqualified`, comparison `not_run`; explicit
diagnostic replay compares successfully without upgrading qualification.
After the single clean milestone commit, the approved publication gate requires
a fresh real-UI run and strict `passed / qualified / passed` replay before push.
The actual clean revision, run and three-way Git verification belong in ignored
captures and the completion report, avoiding self-referential commits.

**Recorded limitations.** Submission protection is bounded to a tested active
session, not durable exactly-once behavior across reloads/crashes/sessions.
App limits are not sampling guarantees; the strict PNG, periodic optical,
float64, unsigned-manifest and provenance limitations of M2–M5 remain. Saved
status is a snapshot, not continuous filesystem monitoring. There is no public
server, hardware output, archive import, job queue, overwrite or repair flow.
See [exact evidence](handoffs/milestone_6/tests_and_evidence.md) and
[limitations](handoffs/milestone_6/known_limitations.md).

Only the approved twenty paths change. All 111 protected pre-existing tracked
files, including numerical source, existing tests/guards and historical evidence,
remain byte-identical. Later milestones and deferred enhancements are not
started; teaching completion is not inferred.

---

### M6 publication closeout — recorded 2026-09-30

The preceding M6 section is the unchanged **2026-09-29 precommit snapshot**.
The accepted publication gate subsequently completed on that date. The local
`runs/m6_acceptance_20260929/postcommit_completion.md`,
`postcommit_ui_verification.json` and `publication_verification.json` record:

- Commit `cc93c949da23de4a6f98acc0c4954c3c2d7f6849`,
  `feat(m6): add local holographic workbench`, was the single approved
  twenty-path milestone commit. The 111 protected baseline files remained
  byte-identical. The candidate suite was **1396 passed, 1 skipped in 57.91s**;
  the existing Windows file-symlink privilege skip was retained.
- An ordinary loopback server launched from that clean checkout. One real
  Chrome UI action created `runs/m6/b3e4eacb6b5a41d9aac451a804ec9603`, using the
  built-in 64×64 target, 8 µm pitches, 633 nm wavelength, 5 mm distance,
  seed 0 and **two iterations**. The strict replay action with diagnostics
  unchecked reported **passed / qualified / passed** at
  `2026-09-29T15:48:02.622063+00:00` (23:48 Taipei).
- Independent read-only verification checked saved settings/source, target and
  display values, the three history samples, exact new-run membership and
  unchanged bundle-file hashes. That verifier did not itself generate/replay.
- Normal push succeeded. Local HEAD, live remote `main` and GitHub API `main`
  SHA all matched the commit above; the checkout was clean and synchronized.
  Only task-owned browser/server processes were closed, with no remaining
  listener on port 8501.

Server05 retained two Windows Proactor connection-close `WinError 10054`
traces with unconfirmed cause; successful UI generation and strict replay do
not erase that observation. Original precommit evidence, screenshots,
limitations and the ignored completion records are preserved. This closeout
corrects the stale summary row; it does not rerun or expand the M6 audit.

---

## Milestone 7 — Editable 2D target designer

**Status: precommit acceptance complete; clean-postcommit publication gate
pending** (2026-09-30). The starting
revision is accepted M6 `cc93c949da23de4a6f98acc0c4954c3c2d7f6849`.
The fresh baseline passed **1396 tests, 1 skipped in 79.07s (0:01:19)**.
The same Windows file-symlink privilege skip remains. The final full candidate
suite passed **1570 tests, 1 skipped in 111.67s (0:01:51)**, retaining the 1397
baseline cases and adding 174 (117 model/I/O, 28 controller, 18 AppTest and 11
architecture). Six isolated in-memory faults caused nine intended assertion
failures; all 49 source/test Python hashes were unchanged before/after and
matched the final tested state. Exact outputs, the preserved initial discovery
failure and limitations are in [tests and evidence](handoffs/milestone_7/tests_and_evidence.md).

The asymmetric 48×64 example retained exact design/raster/saved-target bytes
and reported actual metrics, with strict candidate replay correctly unqualified
and explicit diagnostic comparison passed. The measured boundary-sensitive
segment probe confirms the specified internal endpoint order on the tested
environment, not universally identical boundary arithmetic. Recorded browser
checks confirm one actual 8×10/N=2 run, rejection of a received duplicate event,
saved target-byte identity, stale-draft labels, external-association failures
and recovery, strict/diagnostic statuses, and explicit reopen without rerun.
Two genuine viewport captures are present. The final real-browser import
sequence verified equal-size/equal-basename changed content, upload-only
preservation, invalid-JSON preservation and explicit valid-import recovery.
Earlier permission-dismissal attempts performed no import and remain separate
from those completed checks. All 24 candidate paths are within scope; 125
protected files and 53 distributions are unchanged. The later clean-postcommit
publication gate remains separate and pending.

**Approved scope.** A strict immutable `TargetDesign2D`, deterministic
center-sampled overwrite rasterization, bounded versioned design JSON, an
ordered numeric editor, exact float64 target integration and separate external
submitted-design snapshots. Built-in/PNG modes and M2–M5 scientific contracts
remain intact. Twenty-four paths are approved; six existing files may change.

The design canvas owns submitted dimensions. Edits may preview but never
implicitly solve/save/replay. One accepted action captures one immutable
design, persists it separately and calls M5 once. Completed numerical bundles
remain usable without their external editable design; explicit association
requires verified target-byte agreement, not merely a matching UUID.

Completed precommit acceptance includes pure/I/O and controller/API tests,
installed Streamlit AppTest, real browser interactions, six detecting negative
controls, the asymmetric example, two real screenshots, six handoffs and exact
scope/protected-file checks. No arbitrary hard-edged target inherits the old
Gaussian quality threshold. Candidate provenance remains dirty/unqualified.
After one clean milestone commit, a fresh real-UI Designer run must retain
exact submitted target bytes and strict `passed / qualified / passed` replay
with diagnostics off, including independence from external design storage.
Postcommit evidence stays in ignored captures and the completion report.

The [roadmap](roadmap.md) orders existing M0–M6, M7 content design, then
separately approved V0–V3 virtual-laboratory stages. Text, richer editing,
hardware and all V-stages remain unstarted. No teaching progress is inferred.

---

### M7 publication closeout — recorded 2026-10-01

The preceding section remains the original 2026-09-30 precommit snapshot.
The user accepted M7 within its reported validation scope. Existing ignored
`runs/m7_acceptance_20260930/postcommit_ui_verification.json` and
`publication_verification.json`, read back during V0, record publication at
`3b94a2262ae11f7d2316ac4fc5d168fa4881c859` with one actual 4×5/N=2 Designer
submission, one new editable snapshot and one new numerical bundle. The saved
target bytes matched the submitted raster; source state was clean. Strict UI
replay reported `passed / qualified / passed` with diagnostics off, including
while external design storage was absent. The snapshot was restored exactly
and numerical bundle hashes stayed unchanged. Normal push and local/live
remote/GitHub API SHA agreement were recorded, with a clean final tree.
These are dated M7 records, not a new browser/replay run during V0. Original
precommit counts, screenshots, limitations and handoff documents are unchanged.

---

## V0 — Aligned sequential virtual optics foundation

**Status: implementation acceptance complete (2026-10-01).**
Accepted baseline is M7 `3b94a2262ae11f7d2316ac4fc5d168fa4881c859`.
One scalar monochromatic forward train in air uses one complete SamplingGrid,
Gaussian/uniform sources, inclusive physical circular/rectangular apertures,
signed ideal thin lenses and a terminal ideal observation plane. Absolute
positions and list order are authoritative; colocated stages remain distinct.
Existing public M1 ASM uses pad_factor=1 per interval, with no intermediate
crop or power matching. Dark fields and forward evanescent decay remain valid.

The exact schema/API, narrow arithmetic policy and bounded independent
reference criteria are normative in §3.17 of [math conventions](math_conventions.md).
The [V0 handoff](handoffs/v0/implementation_summary.md) records actual test,
optical/convergence, negative-control, demonstration and figure evidence.
Exactly 27 paths are approved. Old numerical modules/tests/guards, applications,
M5 contracts, dependencies, settings and historical handoffs remain protected.
The baseline suite passed 1570 tests with one retained Windows symlink skip;
the final suite passed **1702 tests, 1 skipped in 184.06s (0:03:04)**. Independent
mixed-parity direct-DFT train errors were below 4.2e-12. Full optical validation
actually ran the required 2048²/1-µm rectangular-aperture case: fixed-ROI complex
L2 error **0.027085064479543036 <= 0.035**. All five coarser/finest measurements,
signed Gaussian lens comparisons, minimum-plane neighbors and clipped-Gaussian
window/pitch studies are retained without fitting or normalization. Nine
isolated deliberate faults failed their independent assertions; production
files were never mutated. The default 512² demonstration ran, and all three
numerical figures were inspected and regenerated with identical bytes.

All 145 pre-existing tracked files outside the four allowed documentation
modifications have unchanged hashes. The 52 installed-distribution inventory
records match the starting versions, METADATA hashes and source locations;
the initial inventory did not hash editable ohlab's separate PKG-INFO bytes.
No dependencies, settings, instructions, old source/tests or historical
handoffs were modified. Commit and normal push are explicitly approved after
acceptance. A clean postcommit import/demo smoke check precedes pushing;
three-way publication verification follows. Those postcommit outcomes stay
in ignored evidence and the completion report, not predicted in this record.
There is no V0 bundle/replay schema and no new qualified-replay gate.

V1/V2/V3, hardware, target-editor extensions and teaching progress are outside
this milestone. The port-8501 server is not task-owned and remains untouched.

---

## Open project decisions

Deferred, non-blocking. Each needs a decision before the corresponding event.

| # | Decision | Needed before |
|---|---|---|
| D-1 | Software licence (`license` field in `pyproject.toml`) | Making the repository public |
| D-2 | `authors` metadata — what name/email, if any, appears in published package metadata | Making the repository public |
| D-3 | Continuous integration (GitHub Actions?) | Any external contribution |
| ~~D-4~~ | ~~Whether `figures/` PNGs are committed or regenerated on demand~~ | **Resolved 2026-08-08: committed.** The tutoring session reads this repository through its public URL and cannot execute code, so the figures must be present as files. They are small PNGs (~815 KB total) and are regenerable at any time via `scripts/make_m0_figures.py`. |
