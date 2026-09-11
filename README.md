# Open Holographic Lab

A reproducible **computer-generated holography (CGH)** simulator, built from
first principles with verifiable numerics.

The long-term system is a programmable holographic laboratory: a scene editor,
a CGH compiler, a calibration engine, a fixed phase-only SLM optical system,
and a device service. **This repository is currently pure software** — there is
no hardware component, and none is being designed yet.

Engineering work starts with [`AGENTS.md`](AGENTS.md), the active engineering
entry point for scope approval, environment safeguards, validation, and Git
workflow. `CLAUDE.md` is retained as legacy reference material.

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

**Milestones 0 and 1 complete — 291 tests passing.** Milestone 2 not started.

The package provides `SamplingGrid` (coordinate and frequency grids),
`ComplexField` (a sampled complex optical field), and free-space propagation by
the **Angular Spectrum Method**. There is no phase retrieval, and no file or
plotting support yet.

See [`docs/milestones.md`](docs/milestones.md) for the full ledger, and the
handoff packages for [Milestone 0](docs/handoffs/milestone_0/) and
[Milestone 1](docs/handoffs/milestone_1/) — implementation summary, code map,
mathematics, test evidence, known limitations, and figures.

```python
from ohlab import ComplexField, SamplingGrid
from ohlab.units import NM, UM

grid = SamplingGrid(ny=256, nx=256, dy=3.74 * UM, dx=3.74 * UM)

field = ComplexField.random_phase(
    grid=grid, wavelength_m=633 * NM, seed=0
)

field.amplitude     # |U|,   (256, 256) float64, >= 0
field.phase         # arg U, (256, 256) float64, in (-pi, +pi]
field.intensity     # |U|^2, (256, 256) float64  <- what a camera would see
field.power         # total power, a.u. * m^2

grid.x              # x coordinates in metres, x[nx // 2] == 0.0 exactly
grid.fx_fft         # spatial frequencies, FFT order, cycles/m
grid.fx_centered    # spatial frequencies, centred order

import math
math.degrees(grid.max_diffraction_angle_rad(633 * NM, axis="x"))  # 4.855
```

Propagating a field through free space:

```python
from ohlab import ComplexField, SamplingGrid, propagate_angular_spectrum
from ohlab.units import MM, NM, UM

grid = SamplingGrid.square(n=512, pitch=4 * UM)
source = ComplexField.uniform(grid=grid, wavelength_m=633 * NM)

out = propagate_angular_spectrum(source, distance_m=50 * MM)

out.intensity          # what a camera at z = 50 mm would record
out.phase              # the phase there
```

`propagate_angular_spectrum` takes a signed `distance_m` in metres. It defaults
to `pad_factor=2`, which embeds the field in a larger zero-valued window to
reduce circular wrap-around; pass `pad_factor=1` to propagate on the original
periodic DFT window instead. Neither is universally correct — they are
different boundary conditions, and the trade-off is documented in
[`docs/math_conventions.md`](docs/math_conventions.md) §3.9.4.

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
AGENTS.md                   active engineering entry point and workflow
CLAUDE.md                   legacy reference material
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
