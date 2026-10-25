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
| V0 | Aligned sequential virtual optics foundation | **complete** (2026-10-01; closeout recorded 2026-10-05) | [`v0/`](handoffs/v0/) |
| V1 | Interactive 3D virtual optical bench | **complete** (2026-10-05; dated publication closeout below) | [`v1/`](handoffs/v1/) |
| V2a | Coherent two-path interference foundation | **complete** (accepted; dated publication closeout below, 2026-10-06) | [`v2a/`](handoffs/v2a/) |
| V2b | Interactive two-path interference and dual-output display | precommit acceptance complete; clean-postcommit build/browser/publication gates follow (2026-10-06) | [`v2b/`](handoffs/v2b/) |

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

### V0 publication closeout — recorded 2026-10-05

The preceding V0 section remains its original precommit snapshot. The user
accepted V0 within its reported validation scope. Read-back of the existing
ignored `runs/v0_acceptance_20261001/publication_verification.json` records
commit `ce4fe39eee2213dec993e09b25492e01f9d16497`, clean postcommit source/demo
checks, normal push and local/live remote/GitHub API agreement. That same SHA
was freshly verified as clean synchronized V1 starting state. These are dated
publication records, not replacement measurements of the historical optics
evidence. The V0 handoff, numerical source and tests remain unchanged.

---

## V1 — Interactive 3D virtual optical bench

**Status: precommit acceptance complete; clean-build/publication gate follows
(2026-10-05).** Accepted starting revision is V0
`ce4fe39eee2213dec993e09b25492e01f9d16497`. Exactly 44 paths are approved:
five existing documentation/configuration changes and 39 new application,
frontend, test, validation and handoff/screenshot files.

Plain TypeScript/Three.js/WebGL2/Vite supplies the schematic bench. Existing
Starlette/Uvicorn serves owned production assets/API only on 127.0.0.1:8510.
Authoritative public V0 validates the SI specification and computes once per
accepted intentional simulation with `record_fields=()`. No new optics,
JavaScript solver, physical component model, persistence or replay badge exists.
The existing Streamlit application and M0–V0 scientific code/contracts remain
unchanged. The port-8501 service is not task-owned and stays untouched.

Numeric editing and constrained z-only ghost dragging preserve component IDs,
order and colocated stages. Camera/selection/color/viewport state changes no
scientific parameter or solver request. Optical edits detach the editable bench
texture immediately; old results retain their original submitted specification.
Complete bounded little-endian float64 frame validation precedes publication.
Display products never replace numerical values; shared 0–10 color limits preserve
loss, with raw maximum, saturation notice and undefined ratios retained as null.

The computation gate follows the actual private worker lifetime across client
disconnect, success, numerical/encoding failure and submission/cancellation
paths. HTTP abort does not cancel running Python work. Body/grid/component,
header/response/connection and drawing-buffer caps are application limits,
not guarantees of sufficient physical sampling or hardware performance.

The fresh retained baseline was 1702 passed, 1 skipped in 160.62s. V1 adds 100 Python
tests, 65 frontend unit tests, real HTTP/direct-V0 comparison, actual production
Chrome/WebGL acceptance, nine isolated detecting faults and three genuine
screenshots. Exact final outputs, controlled cancellation scope, resource
measurements, prior failed attempts and limitations are in the
[V1 evidence](handoffs/v1/tests_and_evidence.md). The existing Windows file-symlink
skip remains unchanged. No privileges are elevated to remove it.

All 167 protected tracked files and 52 Python distribution records, including
editable PKG-INFO, remain unchanged. The reviewed npm tree adds only owned V1
frontend tools; install scripts stay disabled. The full 44-path inventory and
unchanged lock/source checks precede the one approved milestone commit. Fresh
dist recreation, source/served-asset and genuine browser/direct-V0 smoke checks
must pass from the clean commit before normal push. Publication outcomes remain
in ignored evidence and the completion report rather than being predicted here.

V2/V3, hardware and later enhancements remain unstarted. Teaching is separate;
no learning completion is inferred.

---

### V1 publication closeout — recorded 2026-10-05

The preceding V1 section remains its original precommit snapshot. The user
accepted V1 within its reported validation scope. Read-back of the existing
ignored `runs/v1_acceptance_20261005/publication_verification.json`,
`postcommit_build_verification.json` and
`postcommit_browser/postcommit_browser_smoke.json` records commit
`303a312fcbddfc9abefcef8c1424ae374ef872fe`, recreation of owned production
assets from the clean commit, source/served-asset checks, genuine Chrome/WebGL
direct-V0 smoke, a normal push and matching local/live remote/GitHub API SHAs.
That revision was freshly verified as clean synchronized V2a starting state.
These are dated read-backs of separately executed publication checks, not a
new frontend build or browser run. The historical 10-pass/1-skip browser batch
and separately passed controlled-disconnect check retain their original scope.
No historical V1 handoff or measurement has been rewritten.

---

## V2a — Coherent two-path interference foundation

**Status: precommit numerical acceptance complete; clean-postcommit source/demo
and publication gates follow (2026-10-05).** Accepted starting revision:
`303a312fcbddfc9abefcef8c1424ae374ef872fe`. Exactly 22 paths are approved:
four existing documentation updates and eighteen new numerical, test, script,
example, handoff and figure paths.

Direct `ohlab.optics.interference` supplies ideal B/B_dagger ordered coherent
mixing, uniform phase, fixed frozen two-arm records and the runner. Existing
public ASM is called once per arm at pad1, preserving carrier/decay and zero
distance. Extra signed phase applies only on arm 1; both actual complex outputs
remain. Public constructors preserve independent complex128 read-only ndarray
ownership without storage hardening. Ten sampled norms, signed differences and
original-input fractions derive without clamping or hidden normalization.
Equal-arm fractions include propagation survival tau; mixer algebra is not
calibrated evanescent electromagnetic energy transport.

The fresh unchanged baseline was 1802 passed, 1 skipped in 126.67 s. First retained/new
suite was 2006 passed, 1 skipped in 223.75 s. Final after all twelve isolated scientific
fault detections/restoration: **2006 passed, 1 skipped in 254.93s (0:04:14)**. The original Windows
file-symlink privilege skip remains; junction behavior is tested separately.
All eight declared phases plus four near-dark sides, asymmetric independent
physical-coordinate DFT, simultaneous coherent inputs, unequal carrier,
common/relative phase, forward evanescence and blocked quarter/quarter/half
budget passed unchanged bounds. Worst complete asymmetric input-scaled complex
DFT error was 1.1562283221955914e-15. Equal 100 nm mixed-spectrum tau was
0.9275310453988844; unequal 80/130 nm ratio 0.9278073476242655. Exact current
measurements, probe provenance and the preserved new-fixture message failure
are in the [V2a evidence](handoffs/v2a/tests_and_evidence.md).

Both modest 64²/128² demos and bounded 512² runtime/memory probes ran on shipped
functions. All three actual numerical figures were inspected and regenerated
byte-identically. No browser/frontend/server acceptance was run or required.
Historical V1 results remain historical. All 207 protected pre-existing tracked
files and installed distribution versions, metadata hashes and source locations
remain unchanged. Existing code/tests/guards/exports, M5 contracts, apps/frontend,
dependencies, settings, instructions and historical handoffs were not modified.

One commit and normal push are explicitly approved after acceptance. A clean
postcommit import/source-location and 64² demo smoke precede pushing; local/live
remote/GitHub API matching and final clean status are recorded afterward in
ignored evidence/completion report, not predicted here. No new replay gate,
persistence schema, general topology, physical mirror model or UI is added.

V2a numerical foundation -> separately approved V2b dual-output 3D integration
-> later reflection geometry, polarization and instruments. V2b/later stages
remain unstarted; teaching and historical learning records remain separate.

---

### V2a publication closeout — recorded 2026-10-06

The preceding V2a section remains its dated precommit evidence. The user
accepted V2a within its reported validation scope. Read-back of the existing
ignored `runs/v2a_acceptance_20261005/publication_verification.json` records
commit `a215da74cb0f85e8727bbbdffb6408da4d3df3d4`, clean-postcommit public source
imports and a 64² demo, normal push, matching local/live remote/GitHub API
SHAs and a clean synchronized main. These are separately recorded publication
checks, not new numerical measurements or rewritten historical evidence.
That exact revision was freshly verified as the clean V2b starting state.

---

## V2b — Interactive two-path interference and dual-output display

**Status: implementation and precommit acceptance complete; clean-postcommit
build/browser and publication gates follow (2026-10-06).** Accepted starting
revision: `a215da74cb0f85e8727bbbdffb6408da4d3df3d4`. Exactly 36 paths were
approved: 12 modifications and 24 creations, recorded in the
[V2b implementation handoff](handoffs/v2b/implementation_summary.md).

Sequential optics remains the default. Separate two-path scientific drafts
use public V0 source-plane sampling and unchanged public V2a computation;
one explicit single run calls run_two_arm once. Both actual immediate
B_dagger outputs share coordinates and color limits, retain original float64
readouts/maxima, ten sampled norms and signed original-input diagnostics.
The fixed unfolded schematic adds no travel, flip, conjugation or mirror law.
Browser-authored negative-zero phase canonicalizes to positive zero before
identity; nonzero signed radians are not reduced or altered.

OHLAB2P and the typed /api/v2b routes are separate from unchanged legacy V1
framing and limits. Whole-frame validation precedes preparation of both
textures/canvases and readout state, then one immutable publication. A failed
second preparation disposes partial resources and retains the old submission
separately, without numerical replay. Scientific edits detach both outputs;
mode switches invalidate late attachment even after an away/back sequence.

The separate scalar-only sweep freezes source/grid/distances and performs
exactly 17 genuine calls, including distinct 0 and 2*pi calls. Failed numerical
sweeps return 422, unexpected internal failures 500, with only a genuine
contiguous prefix and explicit failed/partial labels. All three compute routes
share one gate tied to actual worker and encoding completion, including after
HTTP disconnect. Single axes cap 512; sweep axes cap 128. App-owned persistent
16 MiB/transient 32 MiB budgets explicitly exclude whole heap/process/GPU
memory and renderer caches; repeated replacement/disposal is tested.

The fresh unchanged baseline was **2006 passed, 1 skipped in 110.00s (0:01:50)**.
The final restored full suite was **2079 passed, 1 skipped in 256.93s (0:04:16)**.
The original Windows file-symlink privilege skip remains; junctions are tested
separately. Frontend baseline: 65 tests in four files. Final: **129 tests in
seven files**, typecheck exit 0 and production build exit 0, with its retained
large-chunk warning. Final genuine Chrome/WebGL production batch: **18 passed,
3 skipped** (the separate controlled cases). Controlled partial failure and
sequential/dual/sweep disconnect checks each passed separately. All legacy V1
API fixtures and all ten ordinary V1 browser tests were rerun unchanged.

Independent actual HTTP acceptance matched all arrays/axes/scalars exactly
against public V2a on 18 captured fixtures and three actual 17-call sweeps.
Known-phase, near-dark, common-phase, carrier and lossy cases passed explicit
analytic bounds. Worst periodic fraction closure was 4.440892098500626e-16
with rtol=atol=2e-13, retaining independent endpoints. The controlled fourth-call
failure returned three genuine rows, failed_index 3 and HTTP 422. All 14
isolated fault variants across the eleven requested categories plus atomic
second-texture failure triggered intended assertions and passed restoration;
production was never mutated by that harness. The new camera-fixture failures
and setup failures remain separately recorded, not counted as detections.

Three genuine UI screenshots and the six-document handoff are in
[`docs/handoffs/v2b/`](handoffs/v2b/). Exact commands, unedited output,
provenance, scope and limitations are in
[tests and evidence](handoffs/v2b/tests_and_evidence.md). All 217 protected
pre-existing tracked files remain unchanged, including V0/V2a numerical
source/scientific tests, normative conventions, exports, M5 schemas, Streamlit
apps, dependencies/lockfile and historical handoffs/figures. Installed Python
distribution versions/metadata/source locations and installed Node versions
match the captured baseline. No install or global configuration change occurred.

One commit and normal origin/main push are explicitly approved. Clean-postcommit
rebuilt assets, imported source/served-asset ownership, fresh sequential/dual
browser smoke and one genuine 17-point sweep precede pushing. Actual SHAs and
final clean state are recorded afterward in ignored evidence and the completion
report; this precommit section does not predict publication success. Reflection
geometry, polarization, instruments, persistence, deployment, hardware and later
stages remain unstarted. Teaching and historical learning records stay separate.

---

### V2b publication closeout — recorded 2026-10-06

The preceding V2b section remains its dated precommit evidence. The user
accepted V2b within its reported validation scope. Read-back of existing
ignored `runs/v2b_acceptance_20261006/publication_verification.json` records
commit `886cdac549dcd4373be7d24f9f2211af03659371`, clean-postcommit source/served-
asset checks, rebuilt owned production assets, genuine Chrome/WebGL smoke
(3 passed; 18 deliberately unselected) and an actual 17-point sweep, a normal
push, matching local/live remote/GitHub API SHAs, and clean synchronized main.
That exact revision was freshly verified as the V2c starting state.

This is a dated read-back, not a new frontend build or browser run. Historical
Python 2079-pass/1-skip, frontend 129-test, typecheck/build and retained chunk
warning evidence keep their original scope. Ordinary browser 18-pass/3-skip
results and separately passed partial-failure and sequential/dual/sweep
disconnect checks remain distinct. No historical handoff or measurement was
rewritten; V2c does not launch/manage the existing servers or browser sessions.

---

## V2c — Ideal Jones polarization at one common reference plane

**Status: implementation and precommit numerical acceptance complete;
clean-postcommit source/demo and publication checks follow (2026-10-06).**
Accepted starting revision: `886cdac549dcd4373be7d24f9f2211af03659371`.
Exactly 22 paths are approved: four documentation modifications and eighteen
new source/test/script/example/handoff/figure paths.

Direct `ohlab.optics.polarization` supplies frozen keyword-only `JonesField`,
arbitrary-coefficient `from_scalar`, ideal linear polarizer/retarder actions
and a compatible-field norm ratio. Each component snapshots through unchanged
public `ComplexField`, with native complex128, independently owned read-only
arrays and fresh outputs, including identity/dark cases. Canonical equal grids,
shape and wavelength stipulate a common transverse plane/basis; they do not
establish physical alignment. No initializer/export, scalar propagation,
port/schema, UI/protocol or persistence contract changes.

The unchanged exp(-i*omega*t) convention uses e=(cos(theta),sin(theta)),
p=(-sin(theta),cos(theta)); P=e*e.T and W=e*e.T+exp(i*delta)*p*p.T.
Element coordinates use R.T and conversion back R. Axis phase is zero,
perpendicular phase +delta; QWP/HWP delta=pi/2/pi. Returned complex common phase
is preserved. Positive algebraic angle appears clockwise in y-down display.
Total intensity sums orthogonal component squares without a scalar cross term;
norm evaluates sum(I,dtype=float64)*dx*dy left-to-right. Ratios do not certify
causality: an independent doubled-amplitude output correctly gives four.
No polarizer-loss normalization, epsilon denominator, snapping or clipping.

Fresh unchanged baseline: **2079 passed, 1 skipped in 257.50s (0:04:17)**.
Focused new tests: **277 passed in 1.08s**. Final full restored suite:
**2356 passed, 1 skipped in 113.31s (0:01:53)**. The original skip remains:
`tests/test_run_artifacts.py:1101` — this Windows account lacks symlink
privilege; junction is tested separately. No test or privilege change removed it.

All 13 declared Malus points and five actual-binary64 near-extinction angles
passed independent components/intensity/norm/ratio checks. Decimal80 references
retain the selected ~1e-18 signals rather than relying only on generic atol.
Worst input-scaled complex discrepancy was 2.479436791899844e-16; Malus absolute
error 2.220446049250313e-16; public-basis unitarity error 4.440892098500626e-16;
selected weak relative error 2.0194839179460514e-16. Crossed ratio is
3.749399456654644e-33, three-polarizer ratio 0.25000000000000006 for already
x-polarized input. Noncommuting order and selected rotated-QWP common phase
passed literal complex references without fitting or normalization.

All 15 actual isolated fault variants triggered intended scientific
AssertionErrors on valid records; originals/restored assertions passed,
copied source was restored exactly, and production hashes were unchanged.
Both 64²/32² demos ran shipped functions; runtime, traced allocations and
whole-process observations are separately reported. All three numerical
figures were visually inspected, their title layout corrected within scope,
and regenerated byte-identically. Exact commands/output, measured bounds,
negative controls and limitations are in the six-document
[V2c handoff](handoffs/v2c/implementation_summary.md).

One commit and normal origin/main push are explicitly approved after acceptance.
Clean-postcommit import/source-location and fresh 64² demo smoke precede pushing;
actual local/live remote/GitHub API SHAs and final clean state are recorded
afterward in ignored evidence and the completion report, not predicted here.
No new qualified-replay gate or environment/dependency change is introduced.

V2c numerical Jones foundation -> separately approved V2d 3D polarization mode
-> later polarized interference, reflection/frame geometry and instruments.
Virtual-experiment save/load remains a separate product gap. V2d and later
work remain unstarted; teaching and learning records stay separate.

---

## V2c publication closeout — recorded 2026-10-12

The user accepted V2c within its reported validation scope. Read-back of
existing `runs/v2c_acceptance_20261006_01/publication_verification.json`
records published commit `ff669ab683bcf7b07b4a8ff9073c8557dc6ad1b8`, matching
local/live remote/GitHub API SHAs, a normal push, and clean synchronized main.
Its clean-postcommit import/source-location checks and fresh 64² demo passed.
Exactly 22 paths were committed; 249 protected tracked files and all 53
installed-distribution entries retained their recorded hashes/metadata.

This is a dated read-back, not a new V2c numerical run, frontend build or
browser run. The preceding precommit record, historical tolerances, 2356-pass/
1-skip result, 15 intended fault detections and three numerical figures retain
their original provenance. V2c performed no new frontend/server/browser work.
That exact published revision was verified as the V2d starting baseline.
Historical handoffs and learning records remain unchanged.

---

## V2d — Interactive ideal Jones polarization experiments

**Status: implementation and precommit acceptance complete (2026-10-12);
clean-postcommit rebuild, source/assets ownership and all-three-mode production
smoke must pass before publication.** Accepted starting revision:
`ff669ab683bcf7b07b4a8ff9073c8557dc6ad1b8` on clean synchronized main.

The third bench mode reuses public V0 source-plane parsing/sampling and V2c
Jones actions. Sequential remains default and both older workflows retain
their protocols/assertions. Arbitrary finite complex coefficients are not
normalized. Stable ordered polarizer/retarder IDs, numeric QWP/HWP values,
explicit simulation, actual incident/final float64 intensities and one submitted
complex sample per input/element stage preserve complete request identity.
All actions are ideal at one common plane; no propagation or physical z.

Shared-phase trajectories use only Re([Ux,Uy]*exp(-i*tau)), with equal component
scales and +y down. The common phase remains visible at fixed tau. Exact-dark
classification uses all four returned complex parts; tiny nonzero samples with
rounded-zero intensity disclose display limitations. Intensity picking cannot
relabel the submitted complex sample. Optical edits detach old attachments;
late replies, later-resource failures and context loss cannot publish a mixed
result or trigger automatic resubmission. One owned callback uses the existing
bench loop and detaches without stopping the shared renderer.

The actual thirteen-angle sweep retains both endpoints, restarts the original
incident Jones field and applies the full ordered train at each point (104
public element calls for eight). It returns only genuine scalar rows, with
distinct HTTP422 numerical and HTTP500 unexpected failures and contiguous completed
prefixes. OHLABPL uses bounded little-endian float64 framing. All five compute
kinds share the actual-worker-lifetime gate through encoding/disconnect;
concurrent work fails with HTTP409 while health/validation remain responsive.

Fresh baseline: **2356 passed, 1 skipped in 176.00s (0:02:55)**. Final full suite:
**2523 passed, 1 skipped in 240.61s (0:04:00)**. The existing Windows file-symlink
skip at tests/test_run_artifacts.py:1101 is unchanged; junction coverage is
separate. Installed frontend baseline 129 tests; final 186 tests/typecheck/build
passed. The build's >500 kB chunk warning is retained, not suppressed.

Current production APIs passed 10 sequential cases, 18 two-path cases/3 sweeps,
and 28 polarization cases/3 sweeps with direct-public and unchanged independent
analytic/Decimal references. Full Chrome acceptance passed 28 scenarios with
five explicit controlled-service skips. Separate controlled children passed
all six polarization index 0/3/12 numerical/unexpected failures, legacy partial
sweep and all five disconnect holders. Browser-only transport/resource fault
fixtures remain supplementary. An initial sweep-click interception failure
and an encoder boolean-zero reproducer are preserved with their scoped fixes.
All 26 isolated fault variants in 21 categories triggered intended assertions;
originals/restored assertions passed and production hashes remained unchanged.

Actual owned-buffer observations, resource replacement, pause/reset/context
loss and callback teardown remain bounded by 16 MiB persistent/32 MiB transient.
Conservative phase bounds do not measure whole heap, process or GPU memory.
The six [V2d handoffs](handoffs/v2d/implementation_summary.md) contain exact
schemas, commands, unedited outputs, tolerances, evidence distinctions and
three inspected genuine production UI screenshots. Scope is exactly 35 paths:
nine modifications and 26 creations; 262 protected tracked files and all 53
installed-distribution metadata/location/version records remain unchanged.

One approved commit uses `feat(v2d): add interactive Jones polarization experiments`.
Postcommit rebuilt ownership/smoke and actual publication SHAs belong in fresh
ignored evidence and the completion report; they are not predicted here.
No qualified replay, persistence, polarized interference, hardware, deployment
or later milestone is introduced. Teaching and learning records stay separate.

---

## V2d publication closeout — recorded 2026-10-12

Read-back of `runs/v2d_acceptance_20261012_01/publication_verification.json`
and `final_closeout.json`: V2d was published as
`9791db07ad182902fb027ab4e3caf9d2faccc966`. Local HEAD, live origin/main and
GitHub API main matched, main was clean and synchronized (0/0), and the
task-owned service was closed. The clean-postcommit production rebuild and
source/served-asset checks passed; the existing three-mode smoke passed
**5 tests in 17.4s, no skips**. This is a dated evidence read-back, not a new
V2d scientific run. Its preceding precommit record, counts, tolerances,
screenshots and handoffs retain their original provenance.

## V2e — Portable virtual-experiment settings documents

**Status: implementation and precommit acceptance complete (2026-10-12);
clean-postcommit portability, three-mode smoke and publication remain separate
gates recorded in fresh ignored evidence.**

Approved priority after V2d: settings-only export/import for sequential,
two-path and ideal Jones modes. Accepted starting revision:
`9791db07ad182902fb027ab4e3caf9d2faccc966`, verified on clean synchronized main.
The [V2e handoff](handoffs/v2e/implementation_summary.md) defines the six-key
version-1 schema, stateless `POST /api/v2e/documents/validate`, strict bounded
raw parsing, two-stage exact scientific correspondence and explicit Apply.
Export captures the current valid draft; import previews before replacement.
Restoration has no result or success badge and performs no computation.
Ordinary explicit simulation remains necessary. M5 bundles, existing numerical
models/wire contracts and all historical handoffs remain unchanged.

Baseline Python: **2523 passed, 1 skipped in 216.06s (0:03:36)**. Final restored
Python: **2700 passed, 1 skipped in 302.95s (0:05:02)**. The Windows file-symlink
privilege skip remains unchanged. Installed frontend baseline 186/final 222
tests, typecheck and production build passed; the existing chunk-size warning
is retained. Ordinary legacy browsers passed 28 with 5 controlled-only skips;
document browsers passed 5 with 1 held-worker-only skip. Separate controlled
children passed 17 browser cases with 0 skips and 7 partial-prefix API checks.
All 24 isolated fault variants across 19 categories triggered intended assertions,
original/restored copies passed and production hashes stayed unchanged.
Three-mode actual download/closed-context/renamed-file import and explicit
recomputation matched complete original/direct arrays, scalars and samples
exactly. All 286 protected tracked files and 53 Python package records are unchanged.

Precommit acceptance and publication gates are recorded in the
[new evidence handoff](handoffs/v2e/tests_and_evidence.md). Fresh-session
portability is a tested same-platform identical-input property, not qualified
replay or a cross-version guarantee. Saved results, sweep recipes, libraries,
migration, additional optics, sharing and deployment remain deferred.

---

## V2e publication closeout — recorded 2026-10-13

The preceding V2e section remains its dated precommit evidence. The user
accepted V2e within its reported validation scope. Read-back of existing
`runs/v2e_acceptance_20261012_01/final_closeout01.json`, GitHub/API/live-remote
captures and final closeout report records published commit
`1dde19c4c1d5419714523828c338bc0c948ea82c`, normal push, matching local/live
remote/GitHub API SHAs and clean synchronized main. Clean-postcommit owned
source/assets, fresh-session portability3passed and legacy smoke5passed are
recorded there. These are historical read-back, not newly executed browser,
frontend or V2e validation checks. No historical handoff is rewritten.
That exact revision was verified as clean synchronized main before V2f work.

---

## V2f — Ideal polarization-sensitive two-path interference

Approved numerical scope recorded2026-10-13; accepted starting revision
`1dde19c4c1d5419714523828c338bc0c948ea82c`. Exactly22 paths: four documentation
modifications and eighteen new numerical/test/example/script/handoff/figure
paths. The exact eight-name API and domain/checkpoint/exception contract were
completed in normative3.20 and the new handoff before executable implementation.

The fixed ideal unfolded runner mixes corresponding polarization components
across ports, uses four public scalar ASM calls at explicit pad1, applies each
arm's zero-to-two ordered terminal Jones actions, adds the same common phase
to both arm1 components and recombines with B_dagger. Both raw Jones outputs,
six measured combined-norm checkpoint pairs and short action histories remain.
Analyzers are separate downstream measurements; no loss or phase is normalized
away. The runner-only128-axis cap and scalar/Jones complete-pipeline supported
intersection are explicit. Derived unusable components fail contextually rather
than being silently deleted. This is an aligned low-angle envelope composition,
not a vector Maxwell, reflection/coating, material or calibrated-energy model.

Actual baseline/final tests, independent A–F/full-complex/weak/direct-sum
measurements, classified fault controls/restoration, shipped-runner resources,
both numerical demonstrations and inspected/regenerated figures are recorded
in the [V2f evidence handoff](handoffs/v2f/tests_and_evidence.md). Precommit and
postcommit/publication gates are distinguished there and in fresh ignored
evidence. Precommit acceptance passed: baseline 2700 passed/1 skipped and
restored final 2942 passed/1 skipped, including 242 new cases. The retained skip
is the Windows file-symlink privilege case. All 20 classified controls detected
their intended assertions and restored exactly; independent references, both
demos, shipped-runner resource probes and three inspected byte-identically
regenerated figures passed. Commit and publication remain separate later gates
recorded in the ignored closeout captures and completion report.

Every other existing numerical module/test/guard, initializer/export, app,
wire/document/bundle contract, dependency/lockfile, instruction and historical
handoff remains protected. Frontend/browser results remain historical. No npm,
build, browser/server launch or service management belongs to V2f.

V2f numerical integration precedes separately approved V2g interactive
integration. V2g must explicitly plan new-mode document compatibility; V2e
remains closed to sequential/two_path/polarization. No new document mode,
saved numerical-result feature, reflection geometry, material model, hardware
or deployment is introduced. Teaching and learning records remain separate.

---

## V2f publication closeout — recorded 2026-10-14

The preceding V2f section remains its dated precommit evidence. The user
accepted V2f within its reported validation scope. Read-back of the existing
`runs/v2f_acceptance_20261013_01/final_closeout01.json` records commit
`431346c16e7275f2a4d6798c6efbf689b0056e91`, normal push exit0, matching local
HEAD/live origin/main/GitHub API main, clean synchronized main, one22-path
commit,317 protected pre-existing files unchanged and53 installed distribution
version/location/metadata records unchanged. Clean-postcommit imported-source
and fresh demonstration checks passed. This is a dated publication closeout,
not a rerun or replacement of its numerical measurements or handoffs. That
exact published commit was reverified as clean synchronized main before V2g.

## V2g — Interactive polarized two-path experiments

Approved2026-10-14 from accepted V2f revision
`431346c16e7275f2a4d6798c6efbf689b0056e91`. Frozen exact46-path scope:
16 modifications and30 creations at opening. A later explicit user amendment
adds only `frontend/bench/src/experiment_document_files.ts` to permit the new
download filename: final47 paths,17 modifications/30 creations,322 protected
pre-existing tracked files. The original planning inventory remains unchanged.
The complete application/schema/transport/state/document contract was written
in the [new handoff](handoffs/v2g/implementation_summary.md) before executable
implementation. The numerical core and mathematical conventions are unchanged.

The fourth mode samples the full public source and constructs incident Jones
once per deliberate operation. A single solve calls V2f once, with zero or two
separate public output analyzers. The real17-point sweep calls V2f17times and
enabled analyzers34times, preserving independently calculated endpoints and
genuine failure prefixes. Raw/analyzed roles share one display scale; scientific
analyzer edits invalidate attachments while view switches compute nothing.

`OHLABPT` transports only ordered float64 intensity images and shared axes,
complete scalar histories and immutable full-request identity. Analyzer-off
settings preserve their angle while analyzed data is absent. An analyzer
failure fails the entire requested measurement; later display-preparation
failure is reported separately. All seven computations share actual backend
worker lifetime through encoding and disconnect.

Version1 portable settings remain limited to sequential/two_path/polarization;
version2 accepts only polarized_two_path. Import/export and transactional Apply
perform no optics or gate operation. Apply restores a not-yet-simulated state.
Explicit all-mode result release preserves drafts, invalid edits, stable IDs,
metadata, useful documents and camera. Fixed16/32MiB app-owned budgets do not
automatically evict or retry. The [evidence handoff](handoffs/v2g/tests_and_evidence.md)
records current checks, classified controls, screenshots and limitations;
publication is a separate postcommit gate.

Actual precommit closeout: fresh baseline 2942 passed / 1 skipped; restored final
3242 passed / 1 skipped in 331.13s, with the same Windows file-symlink privilege
skip. Installed frontend typecheck passed and 304 unit tests in 18 files passed.
Production build passed with its unchanged large-chunk warning. Current old
browser assertions passed 33 cases with 6 controlled-only skips; current new
ordinary browser passed 10 cases with 2 controlled-only skips. Separate new
controlled browser runs passed 8 selected cases, including both actual disconnected
workers/all-seven contenders and six genuine failure prefixes. Eight controlled
HTTP cases passed. 26 unit-copy and 3 actual production-main browser-copy fault
variants each detected their intended assertion and restored exactly. 36 complete
new browser frames matched independent direct-public arrays/scalars. The three
genuine screenshots were inspected. 322 protected files and all 53 Python / 7 frontend
package records remain unchanged. Exact commands, unedited streams, measured
limits/tolerances, actual corrections and remaining model limitations are in
the evidence handoff; these counts do not merge separate suites or skips.

No saved numerical-result format, replay qualification, new optics, reflected
frames, materials, detector electronics, hardware or deployment is added.
No later stage or learning-record change is included.

---

## R03 A — Ideal statistical polarization workspace

Approved2026-10-17 from accepted revision
`2b3046682b0b5aefc4e712b901393209a9cede7e`. The unchanged readiness/semantics
split supplies the frozen41-path A inventory:10 modifications/31 creations.
Its source hash, exact Windows identities, baseline and preservation records
are under `runs/r03_ideal_polarization_impl_01/`. Earlier evidence and learning
records retain their historical state.

Identity: **Ideal statistical polarization — independent theoretical model**.
One explicit submission generates a fixed16×16 Gaussian phase realization using
local PCG64, applies an ideal phase-only SLM followed by uniform QWP/HWP, and
reports four finite uncentered probability-mean coherency measurements. Actual
phase samples, complete settings/seed, full Stokes, raw DoP/eigenvalues, units
and limitations share one immutable result identity. Dark normalized quantities
are null. The infinite Gaussian population expectation is separately labelled.
The appended mathematical contract is [section3.21](math_conventions.md#321-a-ideal-statistical-polarization-independently-declared-ensemble).

The dedicated research workspace reuses the existing service and renderer,
provides an original mounted functional schematic, actual submitted phase mask,
parameter inspector and adjacent readout. The four ordinary modes and v1/v2
documents stay closed and unchanged. A has no settings export, sweep, MAT import,
measurement overlay or fitting. Shared actual-worker/client operation gates and
global16/32MiB declared ownership budgets include A and transactional overlap.
See [the implementation handoff](handoffs/r03_fig2a/implementation_summary.md)
and [current evidence](handoffs/r03_fig2a/tests_and_evidence.md).

**B / Figure2a experimental reproduction remains unestablished and separately
gated.** A's ideal second-moment observation does not recover PAX measurement
semantics, historical geometry, observable/axis/estimator lineage or calibration.
No author correspondence, third-party research assets or later stage is included.
One commit and normal push are conditional on the required clean-postcommit
checks; failure preserves evidence and stops before push.

Current implementation/precommit evidence: unchanged baseline3242passed/1skip;
restored final3447passed/1skip, retaining the Windows symlink privilege skip.
Frontend typecheck and346unit tests/21files pass; production build retains its
large-chunk warning. Independent ideal references and9deliberate scientific
fault controls pass. Two actual A browser cases pass, including full submitted
phase/readout identity and manual display recovery. The four old modes have
current browser/HTTP evidence; a document-fixture precondition failure is retained
separately and the unchanged affected document suite passes with its existing
proper fixture generator. Controlled-child-only old browser skips are explicit.
Genuine application screenshots, interaction recording, numerical/resource
observations, exact41paths and protection/publication gates are in the new
evidence handoff. This paragraph does not claim an unperformed push or rewrite
the historical Chrome response-capture failure.

---

## W1 — Computed wave-field sections in the existing Sequential bench

**Status:** implemented and validated within the bounded scope below.
Publication is conditional on the separately recorded clean-postcommit gate.

The bounded vertical slice adds an optional Computed Sections view for a
Gaussian source → one circular/rectangular aperture → ideal thin lens →
observation plane. It retains the ordinary Sequential domain and its existing
limits. W1 rejects unsupported trains/grids without altering the draft.
At most 25 actual calculated sections use a maximum 128×128 grid, explicit
positions and distinct same-z element-event identities. One unchanged V0 run
provides three upstream anchors and the authoritative terminal field; interior
sections use the existing public pad1 ASM from the appropriate anchor.

Acceptance includes independent complex-field/DFT/Gaussian/coordinate/norm
checks, meaningful negative controls, complete transport validation, the same
actual-worker-lifetime gate, aggregate 16/32 MiB ownership admission and genuine
production-browser/visual evidence. Parameter edits detach stale results;
cursor, camera and shared-color changes do not propagate fields. Mounted
apparatus and labelled beam presentation do not claim ray tracing, realistic
side scattering or a volumetric electromagnetic calculation.

Current numerical acceptance records 3653 passed with the unchanged Windows
symlink-privilege skip. The production browser covers calculated sections,
all parameter fixtures, cached inspection, stale/context recovery, mixed
ownership/release, three desktop sizes and actual 200% zoom. The genuine
33.44-second recording shows inspection and a changed focal pattern. Retained
legacy checks pass, including 19 separate controlled executions. Exact outputs,
all earlier failures, sampling counterexamples and current frontend results
remain in the W1 handoff and task-owned evidence; no old measurements change.

The approved envelope is exactly 40 paths (8 modifications, 32 creations),
including the [W1 handoff](handoffs/w1/implementation_summary.md). One commit and
a normal push are authorized only after required precommit acceptance and the
clean-postcommit gate. A required postcommit failure stops before push without
history rewriting or automatic retry. Existing milestones, R03 A/B boundaries,
document/bundle contracts and historical evidence remain unchanged.

---

## W2 — Computed geometric optical routing

**Status:** implementation and reported validation completed; awaiting user
visual review. W2 is not accepted or published. Stop at the uncommitted
checkpoint. No stage, commit or push is authorized in this pass.

Accepted parent `721156cef44bc76425d7d437cc258b6481acf204`; the approved envelope
is exactly42 paths (9 modifications,33 creations). A separate Geometric Routing
workspace reuses the laboratory service, renderer and single actual-worker-
lifetime gate. One source ray encounters at most16 finite ideal mirror,
half-splitter, stop and receiver faces. Computed intersections, deterministic
branches, finite misses and terminal relative-weight accounting are distinct
from the unchanged wave and polarization models.

The [W2 handoff](handoffs/w2/implementation_summary.md) freezes poses, numeric
error propagation, exact transport and cap precedence before integration.
Independent high-precision geometry and complete32-stage enclosure checks,
focused faults, restored full suites, genuine browser regressions, ownership
controls, three desktop sizes, actual200% zoom and a normal-speed30–60second
recording are required. Current baseline is3653passed/1existing Windows
symlink skip and445frontend units; exact raw output is retained in the fresh
ignored implementation evidence. Final results must be recorded separately.

Dated implementation checkpoint, 2026-10-21: current Python 3910 passed with
the one unchanged symlink skip; 495 frontend units, typecheck and production
build passed. Final browser groups completed 113 passing invocations and eight
declared controlled-only exclusions across 101 unique IDs / 121 isolated
invocations; all 19 fresh legacy controlled scenarios passed. Genuine screenshots
and a 36-second computed interaction recording, independent 32-stage enclosure
evidence, focused negative controls and actual ownership qualifications are in
[tests and evidence](handoffs/w2/tests_and_evidence.md). Exactly 42 approved
paths remain unstaged/uncommitted; 429 protected tracked files and the frozen
planning/environment identities are unchanged. Required failures and their
scoped corrections remain recorded. No task-owned review service remains.

No refraction, coherent folded-wave coupling, calibrated radiometry, scene
persistence, hardware, Figure2a reconciliation or later milestone is included.
All earlier states, measurements, acceptance limitations and historical
evidence above retain their original meaning.

## W3 — Ideal refractive routing through closed bodies

**Status:** implemented and validated within the documented scope; awaiting
the user's visual review. The accepted starting commit remains
`828c7ff9080b174d5eae73b36f2c43608a4c94d7`. The exact46-path candidate
(13 modifications,33 creations) remains unstaged and uncommitted. No stage,
commit or push is authorized.

The existing English Geometric Routing workspace has separate W2/W3 drafts.
W3 adds one finite closed block/right triangular prism, explicit Trace,
certified refraction/internal TIR, medium-aware paths and event inspection.
Every finite side/end face is optical. Ideal route weights omit Fresnel losses;
W1 fields are not attached to folded geometric routes. W2's original numerical
implementation and published behavior/caps, all four prior bench modes, R03,
W1/W1.1, settingsv1/v2, M5 and historical evidence retain their boundaries.

The [W3 contract](handoffs/w3/implementation_summary.md) freezes exact
schema, API, medium, error and resource rules. Independent validation covers
14 reference cases including all five fixed finite receivers, exact stored
inputs versus ideal angles, reciprocity, finite side/end faces and uncertainty.
The original alternating-interface fixture first exceeds the unchanged width
bound at operation14; that is not a universal hard event cap or a promise of
support through32 events. Numerical failure is neither absorption nor ordinary
resource truncation.

Actual final checks: Python4202 passed/one unchanged Windows symlink-privilege
skip; frontend569 passed across35 files, typecheck and production build passed;
136 browser invocations/119 distinct IDs passed with zero skips/retries.
These include three desktop sizes, actual200% zoom, eleven-kind worker and
disconnect controls, presentation recovery, old modes/documents and normal-speed
recordings. The genuine W3 recording is42.56s. Ten screenshots and eight video
samples were visually inspected; prism labels can overlap. User visual acceptance
and publication have not occurred.

The clean baseline was3910 Python passes/one original skip and498 frontend
passes. Original startup, assertion, layout and certificate-validation failures
and their scoped corrections remain preserved. Exact commands, raw output,
measured bounds, resource scopes and qualifications are in
[tests and evidence](handoffs/w3/tests_and_evidence.md) and
[known limitations](handoffs/w3/known_limitations.md).

No Fresnel/polarization branching, dispersion, curved/nested bodies, persistence,
OPL or wave coupling, Figure2a comparison, hardware, deployment or teaching-state
work began. Earlier W2 dated checkpoint prose/evidence is preserved.

## Open project decisions

Deferred, non-blocking. Each needs a decision before the corresponding event.

| # | Decision | Needed before |
|---|---|---|
| D-1 | Software licence (`license` field in `pyproject.toml`) | Making the repository public |
| D-2 | `authors` metadata — what name/email, if any, appears in published package metadata | Making the repository public |
| D-3 | Continuous integration (GitHub Actions?) | Any external contribution |
| ~~D-4~~ | ~~Whether `figures/` PNGs are committed or regenerated on demand~~ | **Resolved 2026-08-08: committed.** The tutoring session reads this repository through its public URL and cannot execute code, so the figures must be present as files. They are small PNGs (~815 KB total) and are regenerable at any time via `scripts/make_m0_figures.py`. |
