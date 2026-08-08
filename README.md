# Open Holographic Lab

A reproducible **computer-generated holography (CGH)** simulator, built from
first principles with verifiable numerics.

The long-term system is a programmable holographic laboratory: a scene editor,
a CGH compiler, a calibration engine, a fixed phase-only SLM optical system,
and a device service. **This repository is currently pure software** — there is
no hardware component, and none is being designed yet.

---

## Current goal

A CGH simulator that can:

1. Load a grayscale target image.
2. Represent optical fields as complex-valued arrays.
3. Propagate fields using the **Angular Spectrum Method**.
4. Generate a phase-only hologram using **Gerchberg–Saxton**.
5. Numerically reconstruct the target image.
6. Measure reconstruction quality.
7. Export the phase map, reconstruction, configuration, metrics, and loss
   history — such that any run is reproducible from its saved configuration.
8. Expose these functions through a minimal application.

---

## Status

**Scaffolding complete. Milestone 0 not started.**

The package currently exposes only `ohlab.__version__`. See
[`docs/milestones.md`](docs/milestones.md) for the full ledger.

---

## Requirements

- Python **3.11**
- NumPy ≥ 1.26, SciPy ≥ 1.11 (installed automatically)

---

## Install

From the repository root, on Windows:

```
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

On Linux/macOS the interpreter path is `./.venv/bin/python` instead.

The `[dev]` extra adds `pytest`, `matplotlib`, and `pillow`. **The numerical
core does not depend on any of them** — see "Architecture" below.

### Troubleshooting: `CERTIFICATE_VERIFY_FAILED` on install

On machines where a corporate proxy or antivirus product performs TLS
inspection, the *first* command may fail with:

```
SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED]
certificate verify failed: self-signed certificate in certificate chain'))
```

The interceptor's root CA is in the **Windows certificate store**, but the pip
version bundled with `venv` (24.0) validates only against its own vendored
`certifi` bundle and never consults the OS store.

The fix is to upgrade pip while explicitly opting in to the OS trust store —
pip ≥ 24.2 then uses it by default, and the remaining commands work unchanged:

```
.\.venv\Scripts\python.exe -m pip install --use-feature=truststore --upgrade pip
```

Do **not** work around this with `--trusted-host` or by disabling certificate
verification. `--use-feature=truststore` still fully validates the certificate
chain; it simply uses the operating system's trust anchors, which is the
correct behaviour on Windows.

## Test

```
.\.venv\Scripts\python.exe -m pytest -q
```

A single file, verbosely:

```
.\.venv\Scripts\python.exe -m pytest tests\test_grid.py -v
```

Always invoke pytest through the virtual environment's interpreter
(`python -m pytest`), never a bare `pytest`, so the interpreter under test is
unambiguous.

---

## Layout

```
CLAUDE.md                   working model and engineering rules
README.md                   this file
pyproject.toml              packaging, dependencies, pytest configuration
docs/
  math_conventions.md       NORMATIVE: units, signs, grids, FFT conventions
  milestones.md             milestone ledger: scope, status, limitations
  handoffs/                 per-milestone learning handoff packages
src/
  ohlab/                    the importable package
tests/                      pytest suite
```

---

## Architecture

Two rules shape the codebase:

**1. The numerical optics core is independent of UI, plotting, and file I/O.**
`grid.py`, `field.py`, `propagation.py`, `algorithms/`, and `metrics.py` take
arrays and return arrays. Anything touching disk or screen lives in
`ohlab/io/`, `scripts/`, or `examples/`.

This is enforced by `pyproject.toml` rather than by convention: the runtime
dependency set is NumPy and SciPy only, so an `import matplotlib` inside the
core would fail in a clean install.

**2. `docs/math_conventions.md` is normative.**
Sign conventions, array layout, coordinate-grid centring, and FFT
normalization are specified there and must match the code. If the two
disagree, that is a bug — and changing a convention requires updating the
document, the code, the tests, and the document's Change Log together.

Mixing sign or ordering conventions is the dominant failure mode in this kind
of software, and it produces output that still *looks* like a hologram. Hence
the discipline.

---

## Verification philosophy

Visually plausible output is **not** evidence of correctness. A reconstruction
that resembles the target proves nothing on its own. Correctness claims in this
repository must rest on analytic ground truth, a conservation law, a symmetry,
a convergence study, or an independent implementation — and every numerical
comparison states its tolerance explicitly.

---

## Licence

Not yet chosen — see decision **D-1** in
[`docs/milestones.md`](docs/milestones.md). Until then, all rights reserved by
the author.
