# Milestone 6 — Code map

M6 stays outside `src/ohlab`. The approved tracked scope is twenty paths:
three modified files and seventeen new files. Historical source, tests,
examples, mathematical conventions and handoffs are protected.

## Application boundary

| New file | Responsibility |
|---|---|
| `apps/__init__.py` | Local application package; no numerical root exports |
| `apps/streamlit_app.py` | Traditional Chinese layout, widget events, stage/status messages and display recovery |
| `apps/workbench.py` | Draft/submission identity, operation tokens, busy state, app limits, controlled paths and public M2–M5 calls |
| `apps/provenance.py` | Current-source detection anchored to imported `ohlab`; no Git mutation |
| `apps/presentation.py` | Saved-data summaries, metric formatting and Matplotlib figures; no Streamlit, file loading, solve or metric evaluation |
| `.streamlit/config.toml` | Loopback/server protections, telemetry and rerun/watcher policy |

`apps.presentation.build_result_figures(*, arrays)` returns independent
image/history figures. It reads `target_intensity`, `reconstruction_intensity`,
`phase` and `residual_history`. It never regenerates these arrays.

`summarize_bundle(*, arrays, config, metrics)` returns fresh display metadata
under `grid`, `optics`, `solver`, `illumination`, `display` and `metrics`.
Source/target powers summarize saved amplitude arrays. Metric rows preserve
their saved numeric values and parameters, with mask counts where applicable.
`format_metric_value(name, value)` retains positive-infinite PSNR explicitly.

The UI owns returned figures and completed-result presentation. The controller
records successful persistence before invoking presentation, so figure failure
cannot turn a completed save into an automatic resubmission.

Controller records are `RunDraft`, `SubmittedRun` and `WorkbenchState`.
`submit_generate` validates and consumes the offered nonce;
`execute_pending_run` performs the accepted generation once. `open_bundle`,
`reverify_bundle` and `replay_bundle` are the explicit existing-run operations.
`record_presentation_failure` retains a completed bundle while recording its
separate display diagnostic. `detect_source_revision` is the shared M6
provenance helper; historical examples remain unchanged.

## Existing library calls

| Operation | Existing authority |
|---|---|
| Amplitude preparation | `ohlab.targets.intensity_to_amplitude` |
| Built-in and uploaded PNG interpretation | `ohlab.io.images.load_target_intensity` (including its existing grayscale-code conversion) |
| Scientific settings | `ohlab.io.config.RunConfig` |
| One coherent solve, metrics and publication | `ohlab.io.artifacts.run_and_save_bundle` |
| Integrity check | `verify_run_bundle` |
| Verified saved arrays/config/metrics | `load_run_bundle` |
| Qualification and numerical comparison | `replay_run_bundle` |

M5 remains responsible for schemas, manifests, typed arrays, scientific
orchestration and exact replay. No app import is added to the numerical package.
The built-in encoder writes the unchanged raster to an owned temporary PNG;
uploaded bytes use the same fixed internal pathname without re-encoding.
Opening loads once; reverify calls verify and then load; replay loads and then
calls public replay after app-limit checks and fresh provenance detection.

## Tests, configuration and documentation

| Path | Purpose |
|---|---|
| `tests/test_workbench_controller.py` | Real API/controller integration, ownership, policies, state and failure cases |
| `tests/test_workbench_streamlit.py` | Installed Streamlit AppTest interaction/status checks |
| `tests/test_workbench_architecture.py` | Optional-dependency and import-boundary checks |
| `pyproject.toml` (modified) | Optional pinned UI dependency declaration |
| `README.md` (modified) | User workflow, launch, supported inputs, limits and recovery |
| `docs/milestones.md` (modified) | Authoritative M6 scope and dated acceptance status |

The six new handoff documents are this code map, `implementation_summary.md`,
`math_used.md`, `tests_and_evidence.md`, `known_limitations.md` and
`tutor_context.md`. Actual UI captures are
`figures/fig01_create_and_inspect.png` and
`figures/fig02_verify_and_replay.png`. Their provenance and capture procedure
belong to [tests and evidence](tests_and_evidence.md).

Generated bundles, dependency reports, test fixtures and browser transcripts
remain in owned ignored locations under `runs/` or dedicated test temporary
directories. `.gitignore` is unchanged. There is no new artifact exporter,
figure-generator framework or archive format.
