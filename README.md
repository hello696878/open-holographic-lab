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
7. Preserve exact inputs, outputs, configuration, metrics and history in
   integrity-checked bundles with an explicit replay criterion and
   source/environment qualification.
8. Expose these functions through a minimal application.

---

## Status

**Milestones 0, 1, 2, 3, 4 and 5 complete.** See the authoritative
[milestone ledger](docs/milestones.md) for dated acceptance evidence.

The package provides `SamplingGrid` (coordinate and frequency grids),
`ComplexField` (a sampled complex optical field), and free-space propagation by
the **Angular Spectrum Method**. Milestone 2 adds strict grayscale PNG loading
and array-only target intensity/amplitude preparation. Milestone 3 adds
single-plane phase-only Gerchberg–Saxton synthesis on a complete periodic,
lossless angular-spectrum grid, with explicit illumination and residual history.
Milestone 4 adds explicit intensity MSE/NMSE/PSNR, signal-region power fraction
and regional population CV, evaluated on the actual reconstruction.
Milestone 5 adds immutable run settings, verified typed artifacts and actual
replay with separate integrity, qualification and comparison reports.

See [`docs/milestones.md`](docs/milestones.md) for the full ledger, and the
handoff packages for [Milestone 0](docs/handoffs/milestone_0/) and
[Milestone 1](docs/handoffs/milestone_1/) and
[Milestone 2](docs/handoffs/milestone_2/) and
[Milestone 3](docs/handoffs/milestone_3/) and
[Milestone 4](docs/handoffs/milestone_4/) and
[Milestone 5](docs/handoffs/milestone_5/) — implementation summary, code map,
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

## Synthesize a phase-only hologram

```python
import numpy as np
from ohlab.algorithms import gerchberg_saxton

# Continue from the loaded target amplitude and grid above. The example
# deliberately configures illumination separately for each target.
source_amplitude = np.full(grid.shape, np.sqrt(np.sum(amplitude**2) / amplitude.size))
result = gerchberg_saxton(
    target_amplitude=amplitude, source_amplitude=source_amplitude,
    grid=grid, wavelength_m=633e-9, distance_m=5e-3,
    iterations=50, seed=0,
)
phase_rad = result.phase
reconstructed_intensity = result.reconstruction.intensity
loss = result.residual_history  # initial value and all 50 completed cycles
```

The solver requires plain native `float64` arrays, exact grid shape, finite
nonnegative amplitudes and positive representable power. Amplitudes may exceed
one. Source and target energies must agree to relative tolerance `1e-12`,
absolute tolerance zero; the solver never rescales either input. Supply exactly
one of `seed` or `initial_phase`. Power compatibility does not guarantee that
the target can be synthesized exactly. A blank M2 image remains a valid image
but is rejected by this solver.

This is one fixed **periodic** grid, equivalent to ASM `pad_factor=1`, with
no evanescent samples even at zero distance or zero iterations. It does not
validate arbitrary isolated finite-aperture optics. Existing ASM still
defaults to `pad_factor=2`. The result contains the last source iterate and
its actual forward reconstruction, never a target-projected intermediate.
The dimensionless loss is `sum((abs(reconstruction)-A_target)**2)/sum(A_target**2)`;
it is neither percent accuracy nor an intensity error or diffraction efficiency.
See the [M3 contract](docs/handoffs/milestone_3/implementation_summary.md)
and [limitations](docs/handoffs/milestone_3/known_limitations.md).

```powershell
.\.venv\Scripts\python.exe -B examples\synthesize_hologram.py --no-show
.\.venv\Scripts\python.exe -B examples\synthesize_hologram.py --input target.png --ny 64 --nx 64 --no-show
.\.venv\Scripts\python.exe -B scripts\make_m3_figures.py
.\.venv\Scripts\python.exe -B scripts\probe_m3_evidence.py
```

The default demo creates a deterministic 64-by-64 grayscale PNG and loads it
through the strict M2 decoder. It uses seed 0, 50 cycles, 633 nm wavelength,
8 micrometre pitches and 5 mm distance. It prints the explicitly configured
uniform source amplitude and both powers. Illumination is configured separately
for each target; this is not constant illumination across arbitrary images.
Target and actual reconstruction share a displayed intensity maximum that is
reported without clipping overshoot to one. Phase is an ideal numerical
visualization, not a calibrated SLM drive image. Omit `--no-show` to display it.

## Evaluate reconstruction quality

```python
from ohlab.metrics import (
    intensity_mse, intensity_nmse, intensity_psnr,
    signal_region_power_fraction, regional_intensity_cv,
)

# Continue from the M3 example: evaluate its actual forward reconstruction.
reconstructed_intensity = result.reconstruction.intensity
mse = intensity_mse(target_intensity=intensity,
                    reconstruction_intensity=reconstructed_intensity)
nmse = intensity_nmse(target_intensity=intensity,
                      reconstruction_intensity=reconstructed_intensity)
psnr_db = intensity_psnr(target_intensity=intensity,
                        reconstruction_intensity=reconstructed_intensity,
                        data_range=1.0)  # explicitly declared M2 design range
# Supply a Boolean mask of exactly the image shape, defined for the task.
# fraction = signal_region_power_fraction(
#     reconstruction_intensity=reconstructed_intensity, signal_mask=mask)
# cv = regional_intensity_cv(intensity=reconstructed_intensity, mask=mask)
```

MSE uses intensity units squared. NMSE divides squared intensity error by
`sum(I_target**2)`, the squared intensity norm, not optical power or M3's
amplitude residual. PSNR needs an explicit positive `data_range`; exact matches
return `+inf` and negative scores remain negative. No clipping or independent
image normalization occurs. Native `float64` nonempty 2-D arrays are required;
values above one and read-only/noncontiguous inputs are supported.

The signal-region fraction divides selected intensity by full-window intensity;
it describes power concentration, not calibrated hardware efficiency or target
brightness fidelity. CV uses population standard deviation (`ddof=0`) divided
by regional mean, can exceed one, and describes uniformity only where flat
brightness is intended. Undefined denominators and unusable float64 arithmetic
raise errors without adding epsilon. See the
[M4 contract](docs/handoffs/milestone_4/implementation_summary.md) and
[limitations](docs/handoffs/milestone_4/known_limitations.md).

Run the separate example from PowerShell, or select the existing project
interpreter in VS Code and run `examples/evaluate_reconstruction.py`:

```powershell
.\.venv\Scripts\python.exe -B examples\evaluate_reconstruction.py --no-show
.\.venv\Scripts\python.exe -B scripts\make_m4_figures.py
```

Omit `--no-show` to display the figures. The fixed 64-by-64 smooth-spot case
compares the exact target, twice the target and the actual seed-0 M3 result.
Its predeclared radius-15-pixel disk excludes some target power, so even the
exact target's signal fraction is below one. The declared PSNR range is one;
shared display limits include overshoot. CV is illustrated separately with
fixed flat-region fixtures. The example does not change the solver or export
a run-artifact bundle.

## Save and replay a scientific run

Milestone 5 adds a transparent directory bundle through
`ohlab.io.config.RunConfig` and four functions in `ohlab.io.artifacts`:
`run_and_save_bundle`, `verify_run_bundle`, `load_run_bundle`, and
`replay_run_bundle`. The wrapper computes its own M2/M3/M4 results from owned
C-order snapshots; it never accepts unrelated caller-supplied outputs.
Schema v1 covers normalized M2 design intensity in `[0,1]`, with explicit
source illumination, unchanged M3 initialization and exact metric parameters.

```powershell
.\.venv\Scripts\python.exe -B examples\run_bundle.py
.\.venv\Scripts\python.exe -B examples\run_bundle.py --output runs\m5\my-new-run
.\.venv\Scripts\python.exe -B scripts\make_m5_figures.py
```

The headless example creates a deterministic temporary grayscale PNG, supplies
power-compatible illumination, synthesizes its phase, evaluates four named
metrics, saves under ignored `runs/`, verifies, reloads and replays. A fresh
UUID names each default run; it is only a directory label. An explicit output
directory must not already exist and its parent must exist. The example
prints exact parameters, software/source provenance, metrics and three
distinct outcomes:

- **Artifact integrity:** SHA-256 over every declared file, including config
  and metrics, relative to an unsigned manifest.
- **Source/environment qualification:** independently collected current
  environment and current source provenance agree under the declared policy.
- **Numerical comparison:** actual replay matches the recorded arrays and
  finite scalar bits, with no tolerance fallback.

The example anchors optional Git detection to the imported package's checkout.
Dirty candidate source is recorded as dirty and uses an explicitly reported
diagnostic replay; its comparison can pass while qualification remains
unqualified. A clean checkout requires qualified replay. The reusable I/O API
does not invoke Git; supplied revision metadata is a declaration, not code
attestation. Without qualified provenance, default replay reports `not_run`.

Bundles contain strict JSON metadata and NPY 1.0 numerical arrays, including
both target intensity/amplitude, source amplitude, actual complex source and
reconstruction, phase, intensity, history and requested masks. Seed mode
records its seed; explicit mode preserves the raw initial phase. A retained
input PNG is optional hashed provenance, never the sole replay input. No
original absolute input path is required. Arrays load read-only with pickle
disabled; invalid paths, files and schemas fail explicitly.

An existing destination is refused. Temporary sibling publication and bounded
cleanup are tested on Windows; they do not guarantee power-loss durability.
Transient Windows rename error 5 receives at most three short waits while the
destination remains absent; persistent errors still fail with bounded cleanup.
Replay is measured in the recorded environment, with no cross-platform or
cross-version bitwise promise. See the [complete API/schema contract](docs/handoffs/milestone_5/implementation_summary.md),
[test evidence](docs/handoffs/milestone_5/tests_and_evidence.md), and
[limitations](docs/handoffs/milestone_5/known_limitations.md).

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
    io/config.py            immutable versioned scientific run settings
    io/artifacts.py         verified run capture, loading and exact replay
    algorithms/             periodic single-plane Gerchberg–Saxton solver
    metrics.py              pure intensity errors and regional diagnostics
tests/                      pytest suite
examples/load_target.py     standalone target demonstration
scripts/make_m2_figures.py   deterministic M2 figure generator
examples/synthesize_hologram.py standalone M3 PNG-to-hologram demonstration
scripts/make_m3_figures.py   deterministic M3 figure generator
scripts/probe_m3_evidence.py reproducible M3 numerical/performance evidence
examples/evaluate_reconstruction.py standalone M4 metric demonstration
scripts/make_m4_figures.py   deterministic M4 figure generator
examples/run_bundle.py      standalone M5 capture/verify/replay example
scripts/make_m5_figures.py   explanatory M5 bundle/replay diagrams
```

---

## Architecture

Two rules shape the codebase:

**1. The numerical optics core is independent of UI, plotting, and file I/O.**
`grid.py`, `field.py`, `propagation.py`, `targets.py`, `algorithms/`, and `metrics.py` take
arrays/fields and return numerical arrays, fields or scalars. Anything touching
disk or screen lives in `ohlab/io/`, `scripts/`, or `examples/`.

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
