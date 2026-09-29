# Milestone 6 — Local holographic workbench

Implementation handoff prepared on **2026-09-29**, from accepted M5 baseline
`a2e7f999d37beb937c7ebff9f13db441cc1ed4ec`. Current acceptance and publication
status belongs to the [milestone ledger](../../milestones.md); exact outcomes
belong to [tests and evidence](tests_and_evidence.md). This document does not
substitute an implementation description for completed browser acceptance.

M6 places a local, single-user Streamlit interface over the existing M2–M5
functions. Numerical source, mathematical conventions, schemas, root exports,
existing tests, historical examples and earlier handoffs remain unchanged.
The interface uses Traditional Chinese explanations with English scientific
terms. It adds no optical model, optimization algorithm or hardware output.

## Three user operations

1. **Create a run.** Choose the fixed built-in 64×64 grayscale raster or a
   supported uploaded PNG. Edit the grid, optics, cycle count, seed and PSNR
   range. Explicitly generate and save one run to a new UUID child of `runs/m6`.
2. **Inspect the saved result.** View saved target intensity, actual
   reconstruction intensity, ideal numerical phase, every residual sample,
   actual saved metrics, configuration and prescribed illumination.
3. **Open, verify and replay.** Choose a completed bundle within the bounded
   runs-directory scope. Load through M5, explicitly reverify/refresh it or
   request strict replay. Diagnostic replay requires a separate opt-in and
   action; it is never enabled automatically for dirty source.

The built-in raster has Gaussian width 7.5 pixels and remains fixed when
pitches change. The width corresponds to 60 micrometres only at the default
8-micrometre pitch. Uploaded images retain M2's exact shape and static 8-bit
grayscale PNG contract. There is no resize, rotation, color conversion,
gamma correction, target normalization or substitute image after an error.

User-facing nm, micrometres and mm are converted once at the controller
boundary. New runs use seeded initialization and three metrics: intensity
MSE, intensity NMSE and PSNR with explicit `data_range`. Loaded runs retain
their saved initialization, metric parameters, masks and illumination,
including explicit-phase and nonuniform-source bundles.

## Existing APIs remain authoritative

The fixed built-in raster is encoded as an app-owned PNG; uploads retain their
exact supplied bytes. Both use public `load_target_intensity` and
`intensity_to_amplitude`, and both pass the same temporary PNG to M5 for
retained provenance. The encoder does not become a second image decoder.
The controller explicitly configures a uniform source amplitude for each new
target using `sqrt(sum(A_target**2)/A_target.size)`. This is disclosed
per-target illumination configuration outside the solver, not a claim of
fixed illumination across arbitrary images.

`RunConfig` receives the scientific settings. One intentional generation
calls `run_and_save_bundle` once; the resulting saved bundle supplies the
display. There is no preview solve followed by a second solve when saving.
Opening calls `load_run_bundle` once after stat-only preflight. Explicit
reverification calls `verify_run_bundle` and then loads a fresh verified
snapshot. Replay loads through M5, checks app operating limits, detects current
provenance and calls `replay_run_bundle` with the explicitly chosen diagnostic
flag. These separate calls assume local bundle files are not concurrently
changed between operations. Presentation never reads artifact files directly or
duplicates decoder, metric, solver, manifest or replay implementation.

## Submission and failure boundaries

Ordinary draft widgets can rerun the application without synthesis, publication,
artifact verification or replay. The explicit action captures an immutable submitted
snapshot, operation token and destination. The token is consumed before
calling the writer; a busy guard disables conflicting operations. Upload
identity includes exact bytes, so replacement with different same-size
content under the same filename changes the draft identity.

Completed arrays remain associated with their submitted identity and saved
configuration. Editing a draft marks the existing result as belonging to an
earlier submission; it never relabels old arrays with new controls. Reloading
the browser or starting a new session does not submit work automatically.
The guarantee concerns tested active-session behavior, not durable exactly-once
execution across crashes or multiple sessions.

Successful publication is recorded before display generation. If presentation
then fails, the completed bundle/path remains available, the UI distinguishes
successful saving from failed presentation, and a later explicit load can
recover the display. It does not remove the bundle or rerun generation.
Before-publication failures produce no success badge for that request.

## Display contract

`apps/presentation.py` exposes three helpers, independent of Streamlit:

```python
build_result_figures(*, arrays) -> tuple[Figure, Figure]
summarize_bundle(*, arrays, config, metrics) -> dict
format_metric_value(name, value) -> str
```

The figure pair contains the three image views and complete raw residual
history. Target and reconstruction share intensity bounds, including values
above one. Phase uses a fixed `[-pi,+pi]` radian color axis. Array rows remain
downward; axes label pixel rows/columns. PSNR's saved reference range is
independent of the image color scale. Positive-infinite PSNR displays as
`+∞`, not a finite substitute. The residual is M3's squared amplitude error,
not intensity NMSE or percent accuracy.

The summary retains the exact saved grid, optics, solver/initialization and
metric parameters. Loaded regional metrics show their actual mask role and
selected-pixel count. Source amplitude is described as uniform or nonuniform
from its saved values, without inferring why a loaded source was chosen.
Power summaries use the saved prescribed source and target amplitudes. No
M4 metric is recalculated for presentation. Inputs remain unchanged.

Figures use Matplotlib `Figure` objects without pyplot's global registry.
English plot labels avoid adding a font dependency; surrounding explanations
remain Traditional Chinese. Display exceptions propagate to the separate
presentation-failure path.

## Status and provenance

Artifact integrity, source/environment qualification and numerical comparison
have separate fields. Generate/load/refresh do not run replay merely to fill
badges: qualification remains unevaluated and comparison remains `not_run`.
Reports apply to their particular bundle and last evaluated snapshot, not
continuous monitoring of files on disk.

The app detects source state from the checkout supplying imported `ohlab`,
not the current working directory or a saved SHA. It re-detects for relevant
operations. This is bounded Git metadata detection, not source attestation.
M5 retains its exact source/environment policy: dirty, unavailable or
mismatched source is unqualified; strict replay then does not run comparisons.
Explicit diagnostics may compare successfully while staying unqualified.
Foreign-byte-order nonexecution remains `not_run`.

## Operating limits and launch

New uploads are limited to 8 MiB encoded bytes. Grid dimensions are 1–512,
cycles 0–200, seed 0–`2**32-1`, and
`ny * nx * max(1, iterations) <= 13_107_200`. Existing bundles receive a
preflight limit of 16 direct entries, 32 MiB per file and 128 MiB total.
These are application operating limits, not changes to library contracts or
proofs of optical sampling adequacy. A valid larger bundle may be outside the
app limits without being corrupt.

Temporary uploads use unique app-owned directories and fixed internal names.
Browser filenames never choose output paths. Completed-run selection excludes
upload staging and reserved partial bundles. Selected paths retain their
identity for M5's link/reparse checks; there is no archive import, repair,
overwrite, deletion or unrestricted filesystem browser.

The optional `ui` extra pins Streamlit 1.64.0 and declares Pillow/matplotlib.
Dependency installation evidence separately records the new-package set and
preservation of every pre-existing distribution. No numerical dependency
upgrade is part of M6.

From PowerShell or a VS Code terminal:

```powershell
Set-Location C:\holographiclab
.\.venv\Scripts\python.exe -B -X utf8 -m streamlit run apps\streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

Open `http://127.0.0.1:8501` explicitly. Headless means the server does not
open a browser itself; it does not remove the browser interface. Repository
configuration keeps CORS/XSRF protections enabled and disables usage telemetry,
run-on-save, file watching and fast reruns. An occupied port is reported, not
freed by terminating another service.

## Acceptance boundary

Controller/API, installed-version AppTest and actual browser evidence are
separate. The two committed figures are actual application screenshots,
not mockups or numerical correctness evidence. Pending browser checks cannot
be replaced by controller or AppTest success. See [tests and evidence](tests_and_evidence.md)
for the current recorded outcomes, failure injections and negative controls.

Precommit runs honestly retain dirty/unqualified provenance. After the single
clean M6 commit, a fresh small run must be created through the real UI and
strictly replayed under that same revision/environment before push. That
postcommit output belongs in ignored run captures and the completion report;
old M5 bundles need not become qualified. The handoff asserts no lesson
completion and begins no later milestone.
