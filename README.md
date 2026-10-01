# Open Holographic Lab

A reproducible **computer-generated holography (CGH)** simulator, built from
first principles with verifiable numerics.

The project develops holographic content-design tools, followed by a separately
approved browser-accessible virtual optics laboratory. **This repository is
currently pure software.** Physical SLM integration is a separate optional
future track; a virtual laboratory does not require physical hardware. See the
[roadmap](docs/roadmap.md) for the staged scope and model boundaries.

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
9. Author editable 2D intensity targets for the same explicit run workflow.

---

## Status

**Milestones 0–7 implemented and validated within their documented scope.** See the authoritative
[milestone ledger](docs/milestones.md) for dated acceptance evidence.
Milestone 7's clean-postcommit Designer generation and strict qualified replay
completed on 2026-09-30; the dated [publication closeout](docs/milestones.md#m7-publication-closeout--recorded-2026-10-01)
preserves the original precommit record. V0's sequential-optics foundation is
implemented and validated within its documented scope, with 1702 passing tests
and one retained Windows symlink skip. It is separate from CGH synthesis
and the future 3D bench; publication verification follows acceptance.

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
Milestone 6 adds the local Streamlit workbench for explicit creation, saved-result
inspection, verified loading and separately requested replay.

See [`docs/milestones.md`](docs/milestones.md) for the full ledger, and the
handoff packages for [Milestone 0](docs/handoffs/milestone_0/) and
[Milestone 1](docs/handoffs/milestone_1/) and
[Milestone 2](docs/handoffs/milestone_2/) and
[Milestone 3](docs/handoffs/milestone_3/) and
[Milestone 4](docs/handoffs/milestone_4/) and
[Milestone 5](docs/handoffs/milestone_5/) and
[Milestone 6](docs/handoffs/milestone_6/) — implementation summary, code map,
mathematics, test evidence, known limitations, and figures.
The [M7 handoff](docs/handoffs/milestone_7/implementation_summary.md) documents
editable design geometry, persistence and integration separately from the
unchanged scientific run contract.

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

## Local holographic workbench

The optional M6 workbench is a Traditional Chinese, single-page application
over the existing M2–M5 public APIs. Its `[ui]` extra declares
`streamlit==1.64.0`, `pillow>=10.0` and `matplotlib>=3.8`; NumPy/SciPy remain
the numerical core's only runtime dependencies. Installation into this existing
environment requires the constrained workflow in `AGENTS.md`, not an editable
project rebuild or automatic dependency upgrades. A missing optional UI package
does not prevent numerical-core/controller imports.

From the repository root, with the existing approved environment:

```powershell
Set-Location -LiteralPath 'C:\holographiclab'
.\.venv\Scripts\python.exe -B -X utf8 -m streamlit run .\apps\streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --server.enableCORS true --server.enableXsrfProtection true --browser.gatherUsageStats false
```

Open <http://127.0.0.1:8501> explicitly. `server.headless=true` disables
automatic browser launch; it does not remove the browser UI. The repository's
`.streamlit/config.toml` also disables file watching, run-on-save and fast reruns,
limits encoded uploads to 8 MiB, and keeps CORS/XSRF protections enabled.
If port 8501 is occupied, stop and report it; do not kill an unrelated service
or silently change the binding. Stop your own server with Ctrl+C when finished.

1. Set the draft in the sidebar and press **Generate & Save** once. The
   built-in quantized raster is always 64×64, with width 7.5 pixels (60 μm
   only at the default 8 μm pitch). Pitch edits reinterpret these fixed pixels.
   Upload mode accepts only M2's exact-size static 8-bit grayscale PNG, without
   resizing, color conversion or normalization. Blank targets fail M3's positive
   power requirement. Each new run explicitly supplies power-matched uniform
   illumination and seed initialization, with MSE/NMSE/explicit-range PSNR.
2. Inspect saved target, actual reconstruction, ideal phase, every residual
   sample, metrics, settings and illumination. Images share an intensity range
   including overshoot; PSNR's declared range is separate. Editing the draft
   leaves the saved result labeled as the previous submission.
3. Open an existing bundle, **Refresh**, or explicitly request **Strict replay**.
   The bounded list covers direct completed-looking `runs/m5/`, `runs/m6/` and `runs/m7/`
   children; listing is not verification. The text field also accepts a path
   relative to `runs/` (for example `m5/run-id`) or a full path inside it.
   With no selection, actions use the currently displayed bundle. No external
   paths, links, junctions, archives, overwrites, repair or deletion are offered.
   Diagnostic replay requires both explicit opt-in and its separate action.

New built-in/PNG runs use UUID directories under ignored `runs/m6/`; Designer
runs use `runs/m7/`. App limits are
1–512 pixels per side, 0–200 iterations, a work budget of
`ny*nx*max(1,iterations) <= 13,107,200`, and a seed in `[0,2**32-1]`.
Before opening, bundles are limited to 16 direct entries, 32 MiB per file
and 128 MiB total. These are application resource policies, not changes to
library contracts or proofs of optical sampling adequacy.

Integrity, qualification and comparison are separate. Save/load/refresh do not
replay: qualification stays `not_evaluated`, comparison `not_run`. A strict
unqualified replay does not compute a comparison. Explicit diagnostics can
compare but never upgrade qualification. Old M5 bundles remain readable but
can be unqualified under the M6 revision; their provenance is never rewritten.
Each status names its bundle and last evaluated operation, not continuous
monitoring. Files are assumed quiescent between separate public M5 calls.

Completed persistence is recorded before presentation. If rendering fails,
the UI retains the completed bundle path and reports the presentation failure;
select that path and explicitly Refresh after resolving the display problem.
No failure, browser reload or new session automatically regenerates a run.
Duplicate-event prevention covers one active session, not durable exactly-once
behavior across process crashes or multiple sessions. A hard interruption can
leave M5's reserved partial staging directory; it is never listed as a completed
experiment. A completed bundle can be reopened from a fresh session.

M6's [handoff](docs/handoffs/milestone_6/implementation_summary.md) and
[acceptance evidence](docs/handoffs/milestone_6/tests_and_evidence.md) distinguish
controller integration, installed-version AppTest and actual browser checks.
The ideal phase is not a calibrated SLM drive image. Existing periodic-model,
metric, integrity and replay limitations remain in force.

## Editable 2D targets

The M7 Designer target mode uses an ordered object list and numeric controls
for disks, axis-aligned rectangles and round-capped finite-width segments.
Select, add, edit, delete or reorder an object; selection alone does not alter
the design. Background and object values specify **intensity** in `[0,1]`.
Later objects overwrite earlier ones, including zero-valued objects. The live
preview rasterizes the design; it does not predict a reconstruction, solve,
save a run or replay anything.

Coordinates are pixels, with `+x` right, `+y` down and zero at array index
`[ny//2,nx//2]`. Pixel centers on a shape boundary are included. No antialiasing,
alpha blending, peak normalization or conversion through PNG occurs. A width-2
rectangle centered on zero can cover centers `-1,0,1`; geometric width is not a
pixel-count promise. Reversing a segment's endpoints retains its raster; the
rasterizer orders endpoints internally without rewriting the editable record.

The design canvas supplies the submitted `(ny,nx)`. Resizing changes the
centered sampling window and preserves all object coordinates and sizes;
off-canvas objects are not moved, wrapped or deleted. Pitches interpret the
fixed raster in metres and never rescale it. A pixel-space disk can therefore
be physically elliptical when `dx != dy`.

Save editable copies separately under ignored `runs/designs/`, or explicitly
download/import versioned JSON. An import validates fully before replacing the
editor; invalid input retains the previous design and selection. A design is
limited to 512 pixels per side, 64 objects, and 256 KiB of encoded JSON.
Coordinates lie in `[-4096,4096]` pixels and positive dimensions/radii are at
most 8192 pixels. The existing run work budget applies separately.

Press **Generate & Save** to capture one immutable design and scientific
settings. The app derives target amplitude with public M2, explicitly chooses
power-matched uniform illumination and calls M5 once with the actual float64
target and `input_png=None`. The submitted editable snapshot is saved as
`runs/designs/submissions/<run-uuid>.json`; the numerical bundle is a separate
`runs/m7/<run-uuid>/` directory. A zero design can preview/save/export, but
positive-power synthesis rejects it without substituting an image. If snapshot
storage fails, no solve starts; if M5 fails later, the snapshot is retained and
reported. Completed persistence remains distinct from presentation failure.

The explicit **load associated design** action verifies the numerical bundle,
validates and rasterizes its external design, then compares shape, dtype and
C-order target bytes. A missing, invalid or mismatched external design does
not prevent bundle inspection or replay and does not replace the editor. A
match establishes equal raster samples, not authenticated authorship or a
unique original drawing. Numerical replay uses saved actual arrays and never
requires that design file. M5 manifests, schema v1 and completed bundles are
unchanged. A newer source revision may leave an older run unqualified; explicit
diagnostics never upgrade qualification.

Built-in and strict uploaded-PNG modes remain available. Changing modes or
bundles revokes diagnostic opt-in; changing a design labels the old result as
an earlier submission instead of changing its identity. Text, fonts, dragging,
freehand drawing, general transforms and the future virtual optics laboratory
are outside M7. See [geometry conventions](docs/math_conventions.md#316-editable-2d-designs-and-deterministic-rasterization)
and the [M7 handoff](docs/handoffs/milestone_7/implementation_summary.md).

The standalone asymmetric example uses all three primitives on a 48×64 canvas,
round-trips its editable JSON and target bytes, and reports actual reconstruction
metrics. It writes new UUID destinations without opening the UI:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 examples/design_target.py
```

Add `--diagnostic` only to explicitly request numerical comparison when source
qualification does not pass. The captured candidate example, with 20 iterations
and seed 0, is in [M7 evidence](docs/handoffs/milestone_7/tests_and_evidence.md#asymmetric-example--completed).
It is not a quality guarantee for arbitrary hard-edged drawings.

## Sequential virtual optics (V0)

`ohlab.optics` supplies immutable `SequentialExperiment` specifications,
Gaussian/uniform sources, centered circular/rectangular apertures, signed ideal
thin lenses and an actual terminal observation field. One complete periodic
SI grid is retained through every forward interval using existing ASM with
`pad_factor=1`. Aperture loss is preserved; zero sources/blocked fields are valid.
There is no GS normalization, camera electronics, 3D viewer or new persistence.

```python
from ohlab import SamplingGrid
from ohlab.optics import (GaussianSource, ObservationPlane,
                         SequentialExperiment, ThinLens, run_experiment)

experiment = SequentialExperiment(
    wavelength_m=633e-9,
    grid=SamplingGrid(ny=512, nx=512, dy=4e-6, dx=4e-6),
    source=GaussianSource(amplitude=1, phase_rad=0, waist_radius_m=100e-6,
                          waist_z_m=0, center_x_m=0, center_y_m=0),
    components=(ThinLens(id="lens", z_m=0, focal_length_m=20e-3),),
    observation=ObservationPlane(id="screen", z_m=20e-3),
)
result = run_experiment(experiment, record_fields=("source", "after:lens"))
result.observation.data       # actual complex field, not an earlier-stage preview
result.observation.intensity  # arbitrary intensity units, not W/m²
result.stages                 # full-window sampled norms, signed changes/ratios
```

Standalone demonstration and explicit large optical acceptance (use a fresh
owned output directory for each invocation):

```powershell
.\.venv\Scripts\python.exe -B -X utf8 examples/sequential_optics.py
.\.venv\Scripts\python.exe -B -X utf8 scripts/validate_v0_optics.py --full --output runs/v0-full-new
```

The second command actually includes 2048²/1-µm bounded aperture acceptance.
The Gaussian and ideal lens models are paraxial; ASM still solves a periodic
sampled problem. Window/pitch convergence and independent references establish
only the documented cases. See the [exact schema/API and mathematical contract](docs/math_conventions.md#317-v0-aligned-sequential-optics--api-and-schema-contract)
and [V0 handoff](docs/handoffs/v0/implementation_summary.md) for tolerances,
arithmetic policy, full commands and limitations. No observation is calibrated
optical power or a simulated camera exposure.

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
    optics/                 aligned sequential sources, elements and observation
tests/                      pytest suite
apps/                       local controller, provenance, presentation and Streamlit UI
.streamlit/config.toml      loopback-only application configuration
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
`grid.py`, `field.py`, `propagation.py`, `targets.py`, `algorithms/`, `optics/`, and `metrics.py` take
arrays/fields and return numerical arrays, fields or scalars. Anything touching
disk or screen lives in `ohlab/io/`, `scripts/`, `examples/`, or `apps/`.

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
