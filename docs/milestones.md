# Milestone Ledger

Authoritative status for Open Holographic Lab. Updated at the end of every
milestone (step 9 of the workflow in `CLAUDE.md` §4).

**Rule:** do not begin a milestone before the previous one is implemented,
tested, its limitations recorded here, and its handoff package written to
`docs/handoffs/milestone_<n>/`.

---

## Status summary

| # | Milestone | Status | Handoff package |
|---|---|---|---|
| — | Scaffolding + normative documentation | **complete** (2026-08-08) | n/a |
| 0 | Field and grid representation | not started | — |
| 1 | Angular Spectrum propagation | not started | — |
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

**Status:** not started.

**Scope.** An exactly-specified, exactly-tested representation of a sampled
complex optical field and its coordinate and frequency grids. No physics
beyond definitions.

| Module | Contents |
|---|---|
| `src/ohlab/units.py` | SI multipliers `NM`, `UM`, `MM`, `CM`, `DEG` |
| `src/ohlab/validation.py` | Shared argument validators (shape, dtype, finiteness, positivity) |
| `src/ohlab/grid.py` | `SamplingGrid` — frozen; spatial and frequency grids, Nyquist limits, serialization |
| `src/ohlab/field.py` | `ComplexField` — frozen; amplitude / phase / intensity / power, constructors, derived-field operations |

**Acceptance criteria.**

- [ ] `pytest` fully green; exact output recorded in the handoff package
- [ ] `x[nx//2] == 0.0` exactly, for even and odd `nx`
- [ ] `fx_fft` equals `np.fft.fftfreq(nx, dx)` bit-for-bit
- [ ] `ifftshift(fx_centered) == fx_fft` exactly
- [ ] An on-grid plane wave lands in the single predicted FFT bin, with the
      predicted sign, for all four `(±fx₀, ±fy₀)` quadrants
- [ ] Parseval holds in the `norm="backward"` form of `math_conventions.md` §3.7
- [ ] Multiplying by `exp(iψ)` leaves `intensity` and `power` unchanged
- [ ] Every public function carries a full type hint and a docstring naming units
- [ ] No import of matplotlib, PIL, or any I/O library anywhere in `src/ohlab/`
- [ ] Each of `math_conventions.md` §3.2–§3.8 maps to at least one named test

**Explicitly out of scope.** Propagation; FFT of a field outside the
convention tests; image loading; plotting; lenses, apertures, or any optical
element; configuration files; CLI.

**Recorded limitations.** *(to be filled at completion)*

---

## Milestone 1 — Angular Spectrum propagation

**Status:** not started.

**Scope.** `src/ohlab/propagation.py` implementing
`math_conventions.md` §3.9, plus validation against analytic ground truth.

**Planned acceptance criteria.**

- Zero-distance propagation is the identity to within a stated tolerance
- Round trip `z` then `−z` recovers the source field to a stated tolerance
- Energy is conserved for propagating components; evanescent components decay
- `|H| ≤ 1` everywhere for `z > 0`
- Agreement with an analytic case (e.g. Fresnel diffraction from a slit or a
  circular aperture) within a stated tolerance
- Sampling-adequacy guidance and/or an explicit warning for undersampled
  configurations
- Wrap-around behaviour characterized, and zero-padding or a band-limited
  transfer function specified

**Known risk carried in.** DFT implicit periodicity (§3.8). Must be addressed
here, not deferred.

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
| D-4 | Whether `figures/` PNGs are committed or regenerated on demand | Milestone 0 handoff |
