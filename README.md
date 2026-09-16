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

**Milestones 0, 1 and 2 complete.** See the authoritative
[milestone ledger](docs/milestones.md) for dated acceptance evidence.

The package provides `SamplingGrid` (coordinate and frequency grids),
`ComplexField` (a sampled complex optical field), and free-space propagation by
the **Angular Spectrum Method**. Milestone 2 adds strict grayscale PNG loading
and array-only target intensity/amplitude preparation. Phase retrieval remains
deferred to Milestone 3.

See [`docs/milestones.md`](docs/milestones.md) for the full ledger, and the
handoff packages for [Milestone 0](docs/handoffs/milestone_0/) and
[Milestone 1](docs/handoffs/milestone_1/) and
[Milestone 2](docs/handoffs/milestone_2/) — implementation summary, code map,
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
- Optional image loading: Pillow ≥ 10.0 through the `[images]` extra.
  M2 was tested with the existing Pillow 12.3.0; the declared range is not
  a claim that every permitted version was tested.

---

## Install

For a new environment, from the repository root on Windows:

```
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

On Linux/macOS the interpreter path is `./.venv/bin/python` instead.

The `[dev]` extra adds `pytest`, `matplotlib`, and `pillow`; the narrower
`[images]` extra adds only Pillow (`pip install -e ".[images]" in a new
environment). **The numerical core does not depend on these extras.**
The standalone demo and figure generator also need matplotlib from `[dev]`.

For this existing checkout, use `C:\holographiclab\.venv\Scripts\python.exe`.
These setup instructions do not authorize recreating its environment or
installing/upgrading packages; follow `AGENTS.md` if the environment is missing.

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

## Prepare a target image

```python
from ohlab import SamplingGrid
from ohlab.io.images import load_target_intensity
from ohlab.targets import intensity_to_amplitude

grid = SamplingGrid(ny=480, nx=640, dy=5e-6, dx=3.74e-6)
intensity = load_target_intensity("target.png", grid=grid)
amplitude = intensity_to_amplitude(intensity, grid=grid)
```

The file must contain a static 8-bit grayscale PNG (source bit depth 8,
color type 0, decoded mode `L`), without transparency or APNG metadata.
Declared and decoded dimensions must match `grid.shape` exactly. Pixel
`[i, j]` stays at `(grid.x[j], grid.y[i])`; nothing is resized, rotated,
cropped or padded. PNG content, rather than the filename extension, is checked.

`I_target = g / 255`, then `A_target = sqrt(I_target)`. There is no gamma/profile
conversion, clipping, thresholding, contrast stretching or peak/power
normalization. All-zero targets stay valid and zero. These are normalized
design values, not calibrated irradiance. Amplitude supplies no phase and is
not a complex field or an SLM phase pattern.

For an existing plain `uint8` array, use
`ohlab.targets.grayscale8_to_intensity(grayscale, grid=grid)`.
`intensity_to_amplitude` accepts only a plain native `float64` array of finite
values in `[0, 1]`. Both require shape `(ny, nx)` and return fresh, writable,
C-contiguous native `float64` arrays without modifying the input or grid.
Pillow is imported only when the file loader is called. Genuine filesystem
errors retain their exception types; identified decoder errors include path,
stage and their original cause. See the [M2 contract](docs/handoffs/milestone_2/implementation_summary.md)
and [limitations](docs/handoffs/milestone_2/known_limitations.md).

Run the deterministic synthetic example from PowerShell, or select the same
interpreter in VS Code and run `examples/load_target.py`:

```powershell
.\.venv\Scripts\python.exe -B examples\load_target.py
.\.venv\Scripts\python.exe -B examples\load_target.py --no-show
.\.venv\Scripts\python.exe -B examples\load_target.py --input target.png --ny 480 --nx 640 --dx-m 3.74e-6 --dy-m 5e-6
.\.venv\Scripts\python.exe -B scripts\make_m2_figures.py
```

The example displays intensity and amplitude on fixed `[0, 1]` scales and
reports `max(abs(A_target**2 - I_target))`. Its default PNG is temporary.
The generator writes only the three M2 handoff figures.

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

If Windows denies access to pytest's default temporary directory, use a fresh
repository-local temporary directory for file-based tests:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --basetemp .pytest_cache/m2-local-run
```

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
    targets.py              pure intensity/amplitude array functions
    io/images.py            optional strict PNG decoder
tests/                      pytest suite
examples/load_target.py     standalone target demonstration
scripts/make_m2_figures.py   deterministic M2 figure generator
```

---

## Architecture

Two rules shape the codebase:

**1. The numerical optics core is independent of UI, plotting, and file I/O.**
`grid.py`, `field.py`, `propagation.py`, `targets.py`, `algorithms/`, and `metrics.py` take
arrays and return arrays. Anything touching disk or screen lives in
`ohlab/io/`, `scripts/`, or `examples/`.

Base runtime dependencies remain NumPy and SciPy. The C06 static guard in
`tests/test_fft_conventions.py` permits `PIL` only in `ohlab/io/images.py`
and rejects ordinary imports of `ohlab.io` from every numerical-core module
and the root initializer. Other forbidden-dependency and RNG restrictions
remain in place. Fresh-subprocess tests block Pillow to verify core import
isolation; these checks are not a compatibility matrix across Pillow versions.

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
