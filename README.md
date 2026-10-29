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

## Independent ideal statistical polarization workspace

The research workspace is **Ideal statistical polarization — independent
theoretical model**. One explicitly submitted 256-state Gaussian phase ensemble
drives the actual phase-mask display beside coherency, full/normalized Stokes,
DoP and mean intensity. Its second-moment observation is an explicit ideal
assumption; a random mask does not itself establish incoherent collection.
The labelled population prediction never replaces the finite result.

Use the existing virtual-bench service and its separate research navigation.
The four original modes and version1/version2 settings documents are unchanged.
Research settings export, sweeps, fitting and measured-data import are absent.
Visible functional light paths are schematic, not calculated rays or diffraction.
See the [model conventions](docs/math_conventions.md#321-a-ideal-statistical-polarization-independently-declared-ensemble)
and [A handoff](docs/handoffs/r03_fig2a/implementation_summary.md).
**Figure 2a experimental reproduction, PAX calibration and experimental
agreement remain unestablished.**

## Computed geometric routing workspace

The separately bounded **Geometric Routing** workspace adds finite ideal
mirrors, deterministic ideal 50:50 splitters, beam stops and receivers to the
existing 3D bench. Load A/B/C, select a component, edit its SI position or
X/Y/Z rotation, and press **Trace** deliberately. Actual intersections govern
the displayed paths and receiver hit/relative-weight readouts. Edits detach
old paths; camera and inspection actions do not compute.

This is a single-ray ideal geometry model, not a wave calculation, real
beam-splitter cube, calibrated-power measurement or physical beam-width model.
Mounts and path thickness are labelled display aids. Routing scene import/
export is unsupported; the four existing modes and their v1/v2 documents stay
unchanged. See the [W2 contract and current validation status](docs/handoffs/w2/implementation_summary.md)
and [limitations](docs/handoffs/w2/known_limitations.md). W2 remains an
uncommitted implementation candidate awaiting visual review; publication is
not authorized by this implementation pass.

## Ideal refractive routing candidate (W3)

Inside **Geometric Routing**, the separate **Ideal Refractive Routing** model
adds a mounted finite block or right triangular prism. Load **Parallel Slab**,
**Prism Deviation** or **Prism with Internal TIR**, edit supported body shape,
pose or interior/exterior index, then press **Trace**. Actual finite boundaries
produce incident/internal/emergent segments with authoritative medium and event
inspection. Edits detach current paths and event details; viewing and opacity
never trace. W2 remains a separate unchanged model.

**Ideal route weights; Fresnel losses are not modeled.** This is constant-index
single-ray geometry, not calibrated power, dispersion or a folded W1 wave field.
No routing persistence is added. The [W3 contract](docs/handoffs/w3/implementation_summary.md),
[validation status](docs/handoffs/w3/tests_and_evidence.md) and
[limitations](docs/handoffs/w3/known_limitations.md) define the current candidate.
This W3 pass authorizes implementation and validation only; the complete
candidate remains unstaged/uncommitted for visual review. No commit or push.
Historical W2 checkpoint prose above remains its original dated evidence.

## Fresnel Power Routing candidate (W4)

Inside **Geometric Routing**, explicitly select **Fresnel Power Routing** for
the separate W4 model. Load **Normal Slab**, **Refracting Prism** or **TIR Prism**;
choose unpolarized, source-e1, source-e2 or source-45-degree polarization, edit
the supported body pose/index, and press **Trace**. Finite reflected and
transmitted paths carry their own polarization coherency state. Deliberate
inspection distinguishes local pure-s/p fractions, actual incident-state
fractions, cumulative child power and terminal totals. Edits detach old routes
and events; camera, opacity and inspection never trace.

**Receiver total — incoherent path sum.** Values are dimensionless fractions
of source optical power, not calibrated watts or detector irradiance. A positive
unresolved fraction makes traversal **incomplete**, even when numerically small.
TIR preserves reflected polarization phase without inventing a propagating
transmitted ray. Path thickness, direction markers and mounts are display aids.
No coatings, dispersion, coherent multipath, W1 wave coupling or routing
persistence is introduced. W2 and W3 retain their separate meanings/defaults.

The [W4 contract and launch instructions](docs/handoffs/w4/implementation_summary.md),
[current validation status](docs/handoffs/w4/tests_and_evidence.md) and
[limitations](docs/handoffs/w4/known_limitations.md) define this bounded candidate.
Dated closeout (2026-10-29): implementation and recorded validation are complete
within the reported scope:4616 Python passes/one existing skip,636 frontend
passes, typecheck and build,160 browser conditions/134 IDs plus one focused
42.64s recording. Browser evidence belongs to Chrome156.0.8078.47. The installed
browser subsequently changed externally to156.0.8078.48; the strict current
freeze comparison fails on that sole identity change, and .48 acceptance is
**NOT_RUN**. Source/assets and recorded evidence remain verified. The candidate
awaits the **user's visual review**, stays **unstaged and uncommitted**, and is
not published. No staging, commit or push is authorized. Earlier W2/W3 checkpoint
prose remains historical.

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

Dated current state (2026-10-12): V2c was accepted and published at
`ff669ab683bcf7b07b4a8ff9073c8557dc6ad1b8`; its
[dated closeout](docs/milestones.md#v2c-publication-closeout--recorded-2026-10-12)
preserves the original numerical evidence. V2d adds a separately approved
interactive ideal Jones mode alongside sequential and two-path modes. Exact
contracts, current acceptance and limitations are in the
[V2d handoff](docs/handoffs/v2d/implementation_summary.md) and authoritative
[milestone ledger](docs/milestones.md). Earlier measurements remain historical.

V2d's dated publication closeout records revision
`9791db07ad182902fb027ab4e3caf9d2faccc966`. The next approved priority, V2e,
implements portable **settings-only** JSON documents for sequential, two-path and
polarization experiments. It exports the current valid draft, previews a raw
import, and requires explicit replacement acknowledgement. Restored settings
are **not yet simulated**: an ordinary simulation must be submitted separately.
See the [V2e contract and workflow](docs/handoffs/v2e/implementation_summary.md)
and [acceptance evidence](docs/handoffs/v2e/tests_and_evidence.md).

V2f adds a standalone ideal **polarization-sensitive two-path** numerical
experiment. It keeps optical ports distinct from x/y polarization components,
uses public scalar ASM for the two aligned transverse envelopes, permits at
most two ordered terminal Jones actions per arm, and returns both raw Jones
outputs with measured norm/loss histories. Output analyzers remain separate.
See the [V2f API and supported numerical domain](docs/handoffs/v2f/implementation_summary.md)
and [actual evidence and limitations](docs/handoffs/v2f/tests_and_evidence.md).
V2g integrates a fourth **polarized two-path** bench mode with explicit single
simulations and 17-point phase sweeps. Raw and optional analyzed outputs share
one comparison scale; analyzer loss remains separate from raw propagation.
Settings documents have an explicit compatibility boundary: version 1 keeps
the existing three modes, and version 2 accepts only `polarized_two_path`.
Applying settings performs no optics. The deliberate **Release retained
calculation results in all modes; keep experiment settings and documents**
action frees app-owned calculations while preserving drafts, documents and camera.
See the [V2g application contract](docs/handoffs/v2g/implementation_summary.md),
[validation evidence](docs/handoffs/v2g/tests_and_evidence.md) and
[limits](docs/handoffs/v2g/known_limitations.md). V2f's published numerical
revision is `431346c16e7275f2a4d6798c6efbf689b0056e91`; its historical evidence
remains unchanged.

The standalone example opens no GUI, browser or server. Use a fresh output
directory for each evidence capture:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 examples\polarized_two_path_interference.py --n 32 --output-dir runs\v2f-demo32-NEW
.\.venv\Scripts\python.exe -B -X utf8 examples\polarized_two_path_interference.py --n 64 --output-dir runs\v2f-demo64-NEW
.\.venv\Scripts\python.exe -B -X utf8 scripts\validate_v2f_interference.py --resources
.\.venv\Scripts\python.exe -B -X utf8 scripts\generate_v2f_figures.py --evidence-dir runs\v2f-demo64-NEW --output-dir runs\v2f-figures-NEW
```

This is a bounded low-angle Jones-envelope composition on a periodic grid,
not a full-vector or reflected-frame electromagnetic solver. Valid Jones
inputs can leave the supported scalar/Jones numerical intersection at a later
stage and fail contextually. No tiny component is silently dropped or rescaled;
loss, complex phase and represented residuals remain visible. The example's
JSON/NPZ files are disposable evidence, not saved-result bundles or qualified replay.

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

## Interactive virtual optical bench (V1)

V1 connects the existing public V0 model to a local Three.js/WebGL2 bench and
ordinary Traditional Chinese panels. Load one of three presets, select a
component, edit its supported parameters or use the constrained z rail, then
press **Simulate**. Edits validate without solving. Orbit/pan/zoom, selection,
resize and color limits affect presentation only. Earlier results remain
separately labeled after an optical edit; their texture leaves the editable bench.

Use the existing project Python and reviewed local Node/npm installation. The
bench extra records already installed Starlette/Uvicorn; these commands do not
authorize rebuilding or installing into the existing Python environment.

```powershell
Set-Location C:\holographiclab\frontend\bench
& 'C:\Program Files\nodejs\npm.cmd' run --ignore-scripts build
Set-Location C:\holographiclab
.\.venv\Scripts\python.exe -B -X utf8 -m apps.virtual_bench.server
```

Open [the local bench](http://127.0.0.1:8510). It serves only this checkout's
owned production assets and API at that origin. It stops if assets are missing
or port 8510 is occupied; it does not manage another service. Ordinary use needs
no Node server or external asset/CDN access. Stop the owned terminal with Ctrl+C.

The display uses transverse 1 mm/world-unit and longitudinal 10 mm/world-unit
schematic scales. Cosmetic lens housings impose no physical aperture. The
initial shared intensity range is 0–10 amplitude-unit²; raw float64 readouts,
maximum, saturation notices and V0 scalar stage records remain visible.
Explicit automatic color limits change colors only. Optical accuracy still
depends on the unchanged V0 periodic-grid, paraxial and sampling assumptions.
There is no experiment persistence or new scientific replay qualification.

Development/acceptance commands use the reviewed tools with lifecycle hooks
disabled; no browser download or automatic tool repair is part of the workflow:

```powershell
Set-Location C:\holographiclab\frontend\bench
& 'C:\Program Files\nodejs\npm.cmd' run --ignore-scripts typecheck
& 'C:\Program Files\nodejs\npm.cmd' run --ignore-scripts test:unit
Set-Location C:\holographiclab
.\.venv\Scripts\python.exe -B -X utf8 scripts\validate_v1_bench.py --output runs\v1-new\api_evidence_1.json
.\.venv\Scripts\python.exe -B -X utf8 scripts\v1_negative_controls.py --output-dir runs\v1-controls-new
Set-Location C:\holographiclab\frontend\bench
# These variables belong to this disposable acceptance terminal only.
$env:V1_EVIDENCE_DIR = 'runs/v1-new'
$env:V1_API_EVIDENCE = 'api_evidence_1.json'
& 'C:\Program Files\nodejs\npm.cmd' run --ignore-scripts test:browser
```

Browser acceptance requires an already running owned production service and a
fresh `V1_EVIDENCE_DIR` containing the independently generated API evidence.
Choose new evidence names for each run; raw captures are never overwritten.
The controlled disconnect case uses a separate owned synchronization harness,
not a production test-control endpoint. See the [V1 handoff](docs/handoffs/v1/implementation_summary.md)
and [exact evidence/reproduction notes](docs/handoffs/v1/tests_and_evidence.md).
The existing Streamlit application is unchanged. V2a adds the independent
numerical foundation below; V2b extends this same local bench in a separate mode. Later stages and hardware remain deferred.

## Coherent two-path interference (V2a)

V2a adds a classical scalar monochromatic, ideal unfolded two-path model.
It uses a balanced B splitter, existing forward ASM in each arm, an extra
uniform phase only on arm 1, and the explicitly selected inverse B_dagger
recombiner. Both ordered complex outputs are retained. It is independent of
the V1 bench and adds no mirror geometry, polarization, coating model,
instrument, persistence or browser integration.

Import its APIs from the new module directly; package exports are unchanged:

```python
from ohlab import ComplexField, SamplingGrid
from ohlab.optics.interference import TwoArmSpec, run_two_arm

grid = SamplingGrid(ny=64, nx=64, dy=4e-6, dx=4e-6)
incident = ComplexField.uniform(grid=grid, wavelength_m=633e-9)
spec = TwoArmSpec(arm_0_distance_m=2e-3, arm_1_distance_m=2e-3,
                  relative_phase_rad=0.37)
result = run_two_arm(incident, spec=spec)
port_0, port_1 = result.outputs
print(result.norms.output_fractions, result.norms.total_output_ratio)
```

Fields must have exactly matching grid metadata, coordinate convention and
wavelength. Public constructors provide independent complex128 read-only
arrays. The runner caps each axis at 512; this is a resource policy, not proof
of adequate optical sampling. Norms are sampled amplitude-unit²·m², not watts.
Output fractions use original total input as their denominator. Equal-arm
fractions are `tau*cos(phi/2)**2` and `tau*sin(phi/2)**2`, where tau is the
propagation survival ratio; bare cos²/sin² requires lossless propagation.
Zero input gives undefined ratios (`None`), and tiny dark-port residuals remain.
Uniform phase on equal spatial modes changes brightness, not spatial stripes.

Using the existing environment, run the modest standalone example (64² by
default, optional `--size 128`), independent validation and isolated controls.
Each evidence destination must be fresh under ignored `runs/`:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 examples\two_path_interference.py --output runs\v2a-demo-new
.\.venv\Scripts\python.exe -B -X utf8 scripts\validate_v2a_interference.py --output runs\v2a-validation-new
.\.venv\Scripts\python.exe -B -X utf8 scripts\v2a_negative_controls.py --output-dir runs\v2a-controls-new
```

The exact APIs, port/phase translation, ten stage norms and signed diagnostic
properties are normative in [§3.18](docs/math_conventions.md#318-v2a-coherent-two-path-interference).
See the [V2a handoff](docs/handoffs/v2a/implementation_summary.md) and
[evidence/reproduction commands](docs/handoffs/v2a/tests_and_evidence.md).
V2a is used by the separately approved V2b dual-output 3D integration,
then later reflection geometry, polarization and instruments.

## Interactive two-path mode (V2b)

Use the same installed production build and loopback launch commands as V1.
Sequential optics remains the default. Select **Two-path**, choose a uniform
or Gaussian source, set the SI-labelled grid/wavelength controls, both arm
distances and the extra arm-1 phase in radians, then explicitly **Simulate**.
The two screens are immediate ordered B_dagger outputs in a common transverse
frame. Dashed paths are an ideal unfolded schematic; mesh spacing adds no
physical travel, mirrors or phase.

Both outputs share one grayscale range. The explicit joint automatic range
changes display only. Inspect either port's original float64 pixel, coordinates,
raw maximum, original-input fractions, all ten norms and signed residuals.
Dark-port residuals and undefined ratios remain visible as returned by V2a.
Scientific edits detach both current screens; prior results retain their
original request/specification in a labelled area. Mode switches invalidate
pending attachment eligibility. No edit, preset, selection or reload calculates.

**Run Phase Sweep** makes exactly 17 actual V2a calls on a frozen source/grid/
distance specification, including distinct calls at 0 and 2*pi. It returns
scalar rows, without image stacks. Lines between calculated markers are visual
interpolation; clicking a marker does not compute. **Simulate selected phase**
is a separate explicit request. Failed sweeps show only a genuine completed
prefix, with a failed/partial label and non-2xx status. Browser-authored phase
`-0` canonicalizes to `+0`; nonzero radians are preserved without modulo reduction.

Single axes are capped at 512, sweep axes at 128. All numerical routes share
one worker-lifetime gate; disconnect does not release running work. The new
`OHLAB2P` result and strict sweep schema are documented in the
[V2b handoff](docs/handoffs/v2b/implementation_summary.md). Legacy V1 transport
remains unchanged. App-owned data budgets are 16 MiB persistent / 32 MiB
transient, with explicit exclusions for renderer/GPU/whole-process memory.

With that task-owned local server running, create fresh independent evidence:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 scripts\validate_v2b_bench.py --output runs\v2b-new\api_evidence.json
.\.venv\Scripts\python.exe -B -X utf8 scripts\v2b_negative_controls.py --output-dir runs\v2b-controls-new
```

See [tests and reproduction commands](docs/handoffs/v2b/tests_and_evidence.md)
for installed-tool browser checks, controlled failures and genuine screenshots.
Reflection geometry, polarization, instruments, persistence and deployment
remain outside V2b.

## Ideal Jones polarization (V2c)

The standalone `ohlab.optics.polarization` module adds fully coherent
monochromatic x/y components and ideal uniform polarizer/retarder action at
one stipulated transverse reference plane. These components are distinct from
V2a's optical ports. Existing scalar propagation and both bench modes retain
their original contracts. This numerical stage adds no 3D polarization mode.

```python
from math import pi, sqrt
from ohlab import ComplexField, SamplingGrid
from ohlab.optics.polarization import (
    JonesField, apply_linear_polarizer, apply_linear_retarder,
    transmission_ratio,
)

grid = SamplingGrid(ny=64, nx=64, dy=4e-6, dx=4e-6)
scalar = ComplexField.uniform(grid=grid, wavelength_m=633e-9)
linear_45 = JonesField.from_scalar(
    scalar, x_coefficient=1/sqrt(2), y_coefficient=1/sqrt(2))
quarter_wave = apply_linear_retarder(
    linear_45, axis_angle_rad=0, retardance_rad=pi/2)
analyzed = apply_linear_polarizer(quarter_wave, axis_angle_rad=pi/4)
print(quarter_wave.x.data[32, 32], quarter_wave.y.data[32, 32])
print(analyzed.sampled_norm, transmission_ratio(quarter_wave, analyzed))
```

Two public `ComplexField` snapshots preserve independently owned read-only
complex128 components. Grids and wavelengths must match exactly; matching
metadata cannot prove physical alignment. Arbitrary finite scalar coefficients
change amplitude and norm without normalization or phase reset. Intensity is
`abs(Ux)**2+abs(Uy)**2`; sampled norm is `sum(I)*dx*dy`, in
amplitude-unit²·m², not watts. A zero incident norm gives an undefined ratio
(`None`). Ratios compare compatible fields without certifying an element action;
an independently supplied double-amplitude field has ratio four.

The retarder leaves its declared axis at reference phase zero and gives its
perpendicular axis `+delta`, using `exp(-i*omega*t)`. QWP/HWP are delta=pi/2/pi.
Returned common phase is preserved; no absolute physical plate-path phase is
predicted. Positive axis angle turns from +x toward +y, clockwise in the
existing y-down display. Extinction residuals remain unclamped. See the
[normative contract](docs/math_conventions.md#319-v2c-ideal-jones-polarization-at-one-reference-plane)
and [V2c handoff](docs/handoffs/v2c/implementation_summary.md).

Use fresh output locations with the existing interpreter:

```powershell
.\.venv\Scripts\python.exe -B examples\jones_polarization.py --n 64 --output-dir runs\v2c-demo-new
.\.venv\Scripts\python.exe -B scripts\validate_v2c_polarization.py --output-dir runs\v2c-validation-new
.\.venv\Scripts\python.exe -B scripts\v2c_negative_controls.py --output-dir runs\v2c-controls-new
.\.venv\Scripts\python.exe -B scripts\generate_v2c_figures.py --evidence-dir runs\v2c-demo-new --output-dir runs\v2c-figures-new
```

The demo also supports `--n 32`. It retains every declared actual Malus point,
complex QWP/HWP outputs, norm loss/conservation and bounded independent weak
signals. Ellipses use actual sampled components and dimensionless optical phase;
the three-polarizer fixture starts with already x-polarized light. Numerical
figures are not V2d screenshots. Polarized interference, reflected frames,
statistical polarization, richer instruments and virtual-experiment save/load
remain separate future work. V2b's dated
[publication closeout](docs/milestones.md#v2b-publication-closeout--recorded-2026-10-06)
uses existing publication records; frontend/browser measurements remain historical.

## Interactive ideal Jones mode (V2d)

Build and launch the same local bench using the existing installed tools:

```powershell
Set-Location C:\holographiclab\frontend\bench
& 'C:\Program Files\nodejs\npm.cmd' run --ignore-scripts build
Set-Location C:\holographiclab
.\.venv\Scripts\python.exe -B -X utf8 -m apps.virtual_bench.server
```

Open [the local bench](http://127.0.0.1:8510), choose **Jones polarization**, set
the scalar source and actual complex x/y coefficients, and add/reorder ideal
linear polarizers or retarders. QWP/HWP buttons assign delta=pi/2/pi radians.
Press **Simulate** explicitly. Gaussian illumination is sampled at its waist;
the app rejects source z fields. All actions occur at one reference plane;
mesh spacing and housing add no propagation, thickness or optical phase.

The result preserves original incident/final float64 intensities, stage norms,
adjacent and original-incident ratios, signed norm differences and one submitted
complex sample per stage. Row/column and actual physical coordinates remain
visible. Clicking another intensity pixel does not relabel the fixed complex
sample. Editing its requested indices needs another explicit simulation.

Trajectories display only Re([Ux,Uy]*exp(-i*tau)), with common tau and equal
x/y scales, +x right/+y down. Common phase and arbitrary coefficient amplitude
remain intact. Exact zero complex components mean no defined polarization
state. A nonzero tiny sample can have zero rounded intensity or invisible
motion; display-scale/precision limitations are reported. Manual magnification
changes display only. Camera, stage, color and playback controls do not solve.

Select a polarizer and explicitly request its thirteen-point angle sweep.
Every actual angle restarts the full train from the original incident field.
Selecting a row only inspects it; applying its angle and simulating is a
separate action. Failed sweeps retain only their genuine completed prefix.
Numerical completion and presentation failure remain distinct, without replay.

The distinct OHLABPL format and `/api/v2d/validate`, `/simulate`, `/sweep`
routes preserve existing scalar protocols. Grid cap 128 per axis, eight elements,
nine selected samples and bounded frames/sweeps are resource limits, not
accuracy guarantees. All five computation kinds share one worker-lifetime gate;
busy requests fail with HTTP409 without a queue/retry. The server remains loopback-only
and refuses an occupied port. No package installation is implied by these
commands. No persistence, polarized interference, deployment or hardware.

With that task-owned service running, write fresh validation evidence:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 scripts\validate_v2d_bench.py --output runs\v2d-new\api_evidence.json
.\.venv\Scripts\python.exe -B -X utf8 scripts\v2d_negative_controls.py --output-dir runs\v2d-controls-new
```

The validator uses real public V2c outputs and independent analytic checks.
Fault controls run isolated copies; they do not start a server or browser.
Browser capture redirection and explicit controlled-child commands are in
[tests and evidence](docs/handoffs/v2d/tests_and_evidence.md). Use fresh capture
directories to preserve historical screenshots. Teaching remains separate.

## Interactive polarized two-path mode (V2g)

Use the existing installed frontend and project interpreter. From the repository
root, build the default assets and explicitly launch the local bench:

```powershell
Push-Location frontend/bench
& 'C:\Program Files\nodejs\node.exe' node_modules/vite/bin/vite.js build
Pop-Location
.\.venv\Scripts\python.exe -B -X utf8 -m apps.virtual_bench.server
```

Open [the local bench](http://127.0.0.1:8510) and choose polarized two-path.
Sequential remains the passive default. Configure the full uniform/Gaussian
source, arbitrary complex x/y coefficients, two forward distances, zero-to-two
ordered terminal actions per arm, common arm-1 phase and optional shared output
analyzer. The signed Gaussian waist position and transverse center remain
effective. The analyzer angle is saved and validated even when disabled.

**Simulate** makes one deliberate calculation; **17-point phase sweep** makes
one deliberate sweep. Each enabled measurement keeps both raw and both analyzed
outputs separate. View, color, picking and marker selection perform no optics.
The single comparison range applies to every available image; original float64
readouts, maxima and saturation remain visible. Choosing a phase marker requires
a separate explicit action to obtain its full images. Failed measurements and
partial sweeps never receive a complete-result label.

Export the current valid draft to `polarized_two_path-settings.json`. A genuine
new-mode document uses version2; the earlier three modes retain version1 and
their original exports. Upload previews exact settings, and Apply requires
replacement acknowledgement. Restored settings are **not yet simulated**.
Neither document version contains results, sweep recipes or replay qualification.

The deliberately scoped release action discards retained calculations and views
in **all modes** while preserving settings, invalid editor text, metadata, useful
document previews/downloads and camera. It is blocked during numerical work and
does not compute, retry, revalidate documents or delete files. Fixed 16 MiB / 32 MiB
app-owned budgets can reject work without eviction. Release permits a later
deliberate calculation; numerical completion and display failure stay separate.

New routes are `/api/v2g/validate`, `/api/v2g/simulate` and `/api/v2g/sweep`;
the old routes are unchanged. `OHLABPT` carries ordered little-endian float64
images and shared axes, public scalar histories and immutable request identity.
At 128x128 the raw/analyzed payload caps are 264192/526336 bytes, with frame
caps 280592/542736. Request and scalar-sweep caps remain 32768/65536. All seven
compute kinds share one actual-worker-lifetime gate through encoding and
disconnect. Health, validation and settings operations do no optics.

The service remains only 127.0.0.1:8510. An occupied port is a blocker; do not
manage its occupant or switch binding. No new dependency or browser installation
is needed. Exact schemas, current evidence, classified controls and genuine
screenshots are in the [V2g handoff](docs/handoffs/v2g/implementation_summary.md).
This is an ideal aligned low-angle Jones-envelope model; later optics and
deployment require separate approval. Teaching remains separate.

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
  virtual_bench/            V1 loopback adapter and owned production asset service
frontend/bench/             V1 TypeScript/Three.js source and locked development tools
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

## W1 — calculated wave-field sections

In the existing Sequential bench, enable **Computed Sections** and explicitly
load the W1 example or configure a Gaussian source, one circular/rectangular
aperture, one ideal thin lens, and an observation plane in that order. Press
**Simulate** to calculate. W1 accepts at most 128 samples on either transverse
axis and 25 sections; ordinary Sequential retains its existing 512-axis limit.
Unsupported drafts are rejected without changing their parameters.

The cursor selects cached calculated sections, including distinct before/after
events at the same position. Camera, cursor and display changes do not propagate
fields. Optical edits detach the displayed result until explicit recomputation.
The common initial intensity scale is 0–3 amplitude-unit² and remains fixed
across calculations until deliberately changed. Decorative glow is labelled;
raw intensity, physical coordinates and sampled norms remain authoritative.

This is a scalar periodic-window ASM preview with ideal paraxial Gaussian/lens
elements, not ray tracing, side-scattering measurement or a volumetric Maxwell
solution. Strong clipping and insufficient sampling can produce substantial
window/grid sensitivity. Read the [W1 handoff](docs/handoffs/w1/implementation_summary.md)
and [numerical contract](docs/math_conventions.md#322-w1-computed-wave-field-sections).
The existing loopback-service commands above serve W1 without new dependencies.

## Licence

Not yet chosen — see decision **D-1** in
[`docs/milestones.md`](docs/milestones.md). Until then, all rights reserved by
the author.
