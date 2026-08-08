# Milestone 0 — Implementation Summary

**Status: complete.** 188 tests passing. Verified on Python 3.11.9, NumPy
2.4.6, SciPy 1.17.1, pytest 9.1.1 (Windows 11).

---

## What was implemented

An exactly-specified, exactly-tested representation of a sampled complex
optical field and its coordinate and frequency grids. No physics beyond
definitions — Milestone 0 is bookkeeping, and it exists so that the sign,
centring, and ordering conventions are nailed down and independently tested
*before* any propagation code can build on them.

| Module | Responsibility |
|---|---|
| `src/ohlab/units.py` | SI multipliers `NM`, `UM`, `MM`, `CM`, `DEG`. Multipliers only — no conversion functions, which would invite a non-SI value to be stored. |
| `src/ohlab/validation.py` | Shared validators for scalars and arrays. `TypeError` for wrong kind, `ValueError` for unusable value; every message names the parameter, the offending value, and the expectation. |
| `src/ohlab/grid.py` | `SamplingGrid` — frozen, keyword-only. Stores four numbers (`ny`, `nx`, `dy`, `dx`) and derives everything else, so no two stored quantities can disagree. |
| `src/ohlab/field.py` | `ComplexField` — frozen, keyword-only. A sampled monochromatic scalar field bound to a grid and a wavelength. |
| `scripts/make_m0_figures.py` | Generates the seven handoff figures. The only file in the repository that imports matplotlib. |

### Key design decisions

1. **`kw_only=True` on both dataclasses.** `SamplingGrid(8, 8, 1e-6, 1e-6)` is
   a `TypeError`. This makes the classic `(nx, ny)` transposition impossible to
   *write*, not merely discouraged. Enforces `math_conventions.md` §3.3 at the
   language level.

2. **Frozen, with a defensive copy of `data` marked non-writeable.** Every
   operation returns a new `ComplexField`. Gerchberg–Saxton (Milestone 3) is a
   loop that repeatedly swaps amplitudes and phases; aliasing bugs there
   produce plausible-looking wrong output and are very hard to find.

3. **`eq=False` plus explicit `allclose(rtol=, atol=)`.** A dataclass-generated
   `__eq__` would compare ndarray fields with `==` and raise
   `ValueError: truth value of an array is ambiguous`. Rather than papering
   over that with `np.array_equal`, value comparison is exposed as a method
   that *requires* explicit tolerances.

4. **`intensity` computed as `Re² + Im²`, not `np.abs(U)**2`.** This makes the
   test `intensity == amplitude**2` a genuine cross-check between two
   independent code paths instead of a tautology.

5. **Frequency axes built from the documented formula, then tested against
   NumPy.** Delegating to `np.fft.fftfreq` would have made the bit-identity
   acceptance criterion unfalsifiable.

6. **Nothing is cached.** Derived arrays are recomputed on each access and
   returned writeable, so a caller mutating one cannot corrupt grid or field
   state. Caching is deferred to Milestone 1, where a hot path exists to
   profile.

### Normative-document change

`docs/math_conventions.md` was raised to **v0.2**, adding §3.8.1: the
frequency axis must be evaluated as `(m − N//2) · (1/(N·d))`
(reciprocal-multiply), not as a division. The two are mathematically identical
but differ by ~1 ULP, and the division form breaks the required bit-for-bit
agreement with `numpy.fft.fftfreq` at realistic pixel pitches. §3.4 also gained
an explicit note that `meshgrid()` returns `(x_grid, y_grid)`.

**No mathematical convention was changed.** The conflict was raised and
approved before any code was written, and the Change Log records it.

---

## What remains out of scope

Not implemented, and not to be added without an explicit decision:

- **Propagation of any kind** — Angular Spectrum, Fresnel, Fraunhofer.
  `math_conventions.md` §3.9 *specifies* the ASM transfer function so that the
  grid conventions are already correct for it, but no code implements it.
- Target-image loading; anything that touches disk.
- Gerchberg–Saxton or any phase-retrieval algorithm.
- Reconstruction quality metrics.
- CLI, Streamlit, or any UI.
- Lenses, apertures, or any optical element.
- Configuration files and run artifacts.
- Hardware interfaces, PyTorch, CUDA, neural networks, multiple depth planes,
  RGB holography, refractive index ≠ 1.
- `SamplingGrid.radius` — deferred until lens phases need it in Milestone 1.

---

## Files created

| Path | Lines* | Purpose |
|---|---|---|
| `src/ohlab/units.py` | 40 | SI multipliers |
| `src/ohlab/validation.py` | 258 | Shared validators |
| `src/ohlab/grid.py` | 415 | `SamplingGrid` |
| `src/ohlab/field.py` | 560 | `ComplexField` |
| `scripts/make_m0_figures.py` | 430 | Figure generation (outside the core) |
| `tests/conftest.py` | 78 | Shared fixtures |
| `tests/_helpers.py` | 88 | Phase-comparison and bit-identity helpers |
| `tests/test_units.py` | 60 | 4 tests |
| `tests/test_validation.py` | 216 | 34 tests |
| `tests/test_grid.py` | 425 | 68 tests |
| `tests/test_field.py` | 480 | 44 tests |
| `tests/test_fft_conventions.py` | 300 | 13 tests |
| `tests/test_plane_wave.py` | 280 | 22 tests |
| `docs/handoffs/milestone_0/*.md` | — | This package (6 documents) |
| `docs/handoffs/milestone_0/figures/*.png` | — | 7 figures, ~815 KB total |

\* approximate, including docstrings and comments.

## Files modified

| Path | Change |
|---|---|
| `src/ohlab/__init__.py` | Re-exports `SamplingGrid`, `ComplexField`, `units`. `__version__` kept as a plain string literal so setuptools' static `attr:` resolution keeps working. |
| `docs/math_conventions.md` | Raised to v0.2 (§3.8.1, §3.4 note, Change Log row). |
| `docs/milestones.md` | Milestone 0 marked complete; limitations recorded; decision D-4 resolved. |
| `README.md` | Status updated; usage snippet added. |

## Files deliberately untouched

`.gitignore`, `pyproject.toml`, `src/ohlab/py.typed`, `tests/test_packaging.py`,
`CLAUDE.md`.

---

## Exact commands

### Install (once)

```
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --use-feature=truststore --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

The `--use-feature=truststore` flag is needed only on machines where a
corporate proxy or antivirus performs TLS inspection; see the Troubleshooting
section of `README.md`. It is not a verification bypass.

### Test

```
.\.venv\Scripts\python.exe -m pytest -q
```

One file, verbosely:

```
.\.venv\Scripts\python.exe -m pytest tests\test_grid.py -v
```

### Regenerate the figures

```
.\.venv\Scripts\python.exe scripts\make_m0_figures.py
```

### Verify the package imports the Milestone 0 API

```
.\.venv\Scripts\python.exe -c "from ohlab import ComplexField, SamplingGrid; print(SamplingGrid.square(n=8, pitch=3.74e-6).x)"
```

---

## Current milestone status

| # | Milestone | Status |
|---|---|---|
| — | Scaffolding + normative documentation | complete |
| **0** | **Field and grid representation** | **complete — 188 tests passing** |
| 1 | Angular Spectrum propagation | not started |
| 2 | Target image loading | not started |
| 3 | Gerchberg–Saxton phase retrieval | not started |
| 4 | Reconstruction quality metrics | not started |
| 5 | Configuration and run artifacts | not started |
| 6 | Minimal application layer | not started |

Milestone 1 has **not** been started.
