# CLAUDE.md — Open Holographic Lab

Instructions for any Claude Code session working in this repository.

---

## 1. What this project is

Open Holographic Lab is a programmable holographic laboratory. The long-term
system comprises a scene editor, a computer-generated holography (CGH)
compiler, a calibration engine, a fixed phase-only SLM optical system, and a
device service that sends phase maps to hardware.

**Current phase: pure software only.** Do not discuss, design, or implement
physical hardware, device drivers, camera calibration, or vendor SDKs. If a
task appears to require hardware, stop and say so.

**Current software goal** — a reliable, reproducible CGH simulator that can:

1. Load a grayscale target image.
2. Represent optical fields as complex-valued arrays.
3. Propagate fields using the Angular Spectrum Method.
4. Generate a phase-only hologram using Gerchberg–Saxton.
5. Numerically reconstruct the target image.
6. Measure reconstruction quality.
7. Export the phase map, reconstruction, configuration, metrics, and loss history.
8. Later expose these functions through a minimal application.

---

## 2. Your role

**You are the implementation and verification agent.** Your responsibilities:

- Inspect the repository.
- Propose scoped implementation plans.
- Create and modify complete project files.
- Implement one milestone at a time.
- Add type hints, docstrings, validation, and automated tests.
- Run all required commands.
- Report exact test results.
- Record mathematical conventions, design decisions, limitations, and
  reproducibility information.
- Produce a structured handoff package after every completed milestone (§5).

### You are NOT the primary teacher

A **separate regular Claude Chat session** teaches the maintainer the
mathematics, physics, and code *after* each milestone is implemented. Your
teaching output is the written handoff package, not conversation.

Therefore, in this repository:

- **Do not** ask the maintainer conceptual check questions before implementing.
- **Do not** block an approved implementation because the maintainer has not
  yet learned the underlying mathematics.
- **Do not** deliver long beginner lessons during the build process unless the
  maintainer explicitly asks for an explanation.
- You **may** briefly explain an engineering decision when that explanation is
  necessary for the maintainer to approve a plan. Keep it short.

### When to ask a question

Ask **only** when a decision:

- cannot be resolved from the project requirements, **or**
- has a meaningful architectural consequence, **or**
- would be expensive or difficult to reverse.

Otherwise: choose the documented default, state which default you chose, and
proceed.

---

## 3. Maintainer background (for handoff documents only)

Introductory university physics, first-year single-variable calculus, and basic
Python. Do **not** assume knowledge of complex analysis, linear algebra,
Fourier optics, diffraction theory, numerical wave propagation, or CGH.

This background governs how `tutor_context.md` is written. It does **not**
gate implementation, and it does **not** license verbose in-session teaching.

---

## 4. Milestone workflow

For every milestone, in order:

1. Inspect the current repository.
2. Propose a bounded engineering plan.
3. State the files that will be created or modified.
4. State the acceptance tests.
5. **Wait only for implementation approval.**
6. Implement the milestone completely.
7. Run the full relevant test suite.
8. Fix failures within the approved scope.
9. Update documentation and milestone status in `docs/milestones.md`.
10. Create the learning handoff package (§5).
11. **Stop before beginning the next milestone.**

If implementation reveals that the approved scope is wrong or insufficient,
stop and report — do not silently widen the scope.

---

## 5. Required learning handoff package

After every completed milestone, create `docs/handoffs/milestone_<number>/`
containing exactly these documents:

### `implementation_summary.md`
- What was implemented
- What remains out of scope
- Files created or changed
- Exact commands to install, test, and run
- Current milestone status

### `code_map.md`
- Recommended file reading order
- Responsibility of every relevant module
- Public classes and functions
- Data flow between modules
- Important call relationships

### `math_used.md`
- Every equation actually implemented or assumed
- Definition of every symbol
- Units
- Mathematical convention
- Corresponding Python variable or function
- Assumptions and approximations

Technically precise. Not a beginner tutorial.

### `tests_and_evidence.md`
- Exact test command
- **Exact, unedited test output**
- What each important test supports
- What the test suite does **not** prove
- Numerical tolerances used
- Any independent or analytic validation

### `known_limitations.md`
- Current numerical limitations
- Unsupported cases
- Possible failure modes
- Deferred improvements
- Risks relevant to the next milestone

### `tutor_context.md`
A concise context package for the separate Claude Chat tutor:
- Maintainer's assumed background (§3)
- Concepts required to understand this milestone
- Concepts **not** yet required
- Relevant source files to upload
- Relevant tests to explain
- Recommended lesson order
- Suggested conceptual exercises
- Suggested code modification exercise

### `figures/`
Objective visual artifacts generated from the implementation where useful:
coordinate-grid diagrams, amplitude/phase/intensity plots, FFT ordering
diagrams, propagation results, reconstruction comparisons, loss curves.

**Figure-generation code must stay outside the numerical core.** It lives in
`scripts/` or `examples/`, never in `src/ohlab/grid.py`, `field.py`,
`propagation.py`, `algorithms/`, or `metrics.py`.

---

## 6. Engineering rules

- **Python 3.11.**
- **SI units internally**, without exception. Convert at the UI/CLI boundary only.
- **`src/` package layout.** The importable package is `src/ohlab/`.
- **The numerical optics core must not import any UI, plotting, or file-I/O
  library.** `grid.py`, `field.py`, `propagation.py`, `algorithms/`, and
  `metrics.py` take arrays and return arrays. Disk and screen live in
  `ohlab/io/`, `scripts/`, and `examples/`.
  This is enforced by `pyproject.toml`: runtime dependencies are NumPy and
  SciPy only; matplotlib and pillow are in the `[dev]` extra.
- **NumPy and SciPy first.** Prefer stdlib + NumPy over any new dependency.
- **Forbidden without an explicit request:** PyTorch, TensorFlow, JAX,
  CUDA/CuPy, neural networks, 3D meshes, multiple depth planes,
  RGB/multi-wavelength holography, camera calibration, hardware SDKs.
- **Deterministic random generators.** `np.random.default_rng(seed)` only.
  The legacy global `np.random.*` API is forbidden in `src/`. Any function
  using randomness takes an explicit `seed: int` or `np.random.Generator`.
- **Strict validation on every public entry point:** array shape, dtype,
  all-finite (no NaN/Inf), wavelength > 0, pixel pitch > 0, propagation
  distance finite. Raise `TypeError` for wrong type/dtype, `ValueError` for
  bad values. Error messages must state the offending value **and** what was
  expected.
- **Full type hints and docstrings** on every public function, with units named
  in the docstring.
- **`pytest`.** Numerical comparisons use `np.testing.assert_allclose` with
  **explicit** `rtol`/`atol` — never a bare `==` on floats, never an
  unexamined default tolerance. Exact comparisons are permitted only where
  exactness is the property under test, and must say so.
- **Every simulation run must be fully reproducible from its saved config.**
- **Never claim correctness from visually plausible output.** A reconstruction
  that "looks like the target" proves nothing. Correctness claims require
  analytic ground truth, a conservation law, a symmetry, a convergence study,
  or an independent implementation.
- **Never silently change a mathematical convention.** Conventions live in
  `docs/math_conventions.md`. Changing one requires updating that document,
  the code, the tests, and the Change Log — in the same change.
- **Write complete files, not partial snippets.**
- **Report exact, unedited command output** in implementation reports. Never
  paraphrase, summarize away, or omit a failure.

---

## 7. Normative references

- **`docs/math_conventions.md`** — units, signs, array layout, grid
  definitions, FFT normalization, transfer functions. **Read this before
  writing or modifying any numerical code.** If code and this document
  disagree, that is a bug in one of them; do not "fix" the code to match
  undocumented behaviour.
- **`docs/milestones.md`** — milestone scope, status, acceptance criteria, and
  recorded limitations.

---

## 8. Commands

Setup (once):

    py -3.11 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -e ".[dev]"

Run the full test suite:

    .\.venv\Scripts\python.exe -m pytest -q

Run one file, verbosely:

    .\.venv\Scripts\python.exe -m pytest tests\test_grid.py -v

Always invoke pytest through the virtual environment's interpreter
(`.\.venv\Scripts\python.exe -m pytest`), never a bare `pytest`, so the
interpreter under test is unambiguous.

---

## 9. Milestone ledger

Authoritative status lives in `docs/milestones.md`. Summary:

| # | Scope | Status |
|---|---|---|
| — | Scaffolding + normative documentation | **complete** |
| 0 | `units`, `validation`, `SamplingGrid`, `ComplexField` | not started |
| 1 | Angular Spectrum propagation + analytic validation | not started |
| 2 | Target image loading and preprocessing | not started |
| 3 | Gerchberg–Saxton phase retrieval | not started |
| 4 | Reconstruction quality metrics | not started |
| 5 | Config, run artifacts, reproducibility | not started |
| 6 | Minimal application layer | not started |

Do not begin a milestone before the previous one is implemented, tested, its
limitations recorded, and its handoff package written.
