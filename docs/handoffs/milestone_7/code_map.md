# Milestone 7 — Code map

M7's approved scope is exactly 24 tracked paths: six modifications and eighteen
new files. Existing numerical modules, root exports, M5 schemas, old tests and
architecture guards, dependency declarations, server configuration and
historical handoffs remain protected.

## New model, file boundary and editor

| Path | Responsibility |
|---|---|
| `src/ohlab/target_design.py` | Strict immutable `TargetDesign2D` and deterministic intensity rasterization; no UI, plotting, filesystem or optical solver |
| `src/ohlab/io/designs.py` | Bounded strict JSON conversion and exclusive editable-file persistence |
| `apps/designer.py` | Designer editor state, validated replacement/selection and explicit editable-copy persistence |
| `examples/design_target.py` | Asymmetric all-primitive example, design round trip, existing numerical pipeline and actual metrics |

Public functions are `rasterize_target_design`, `design_to_json`,
`design_from_json`, `save_design` and `load_design`, imported from their
defining modules. There are no new package-root exports. The model's
`to_dict()` yields fresh nested data.

## Modified application files

| Path | Responsibility added by M7 |
|---|---|
| `apps/workbench.py` | Design-aware immutable draft/submission identity, canvas-authoritative grid, snapshot-before-run sequencing, verified external association, M7 output/listing and retained M6 guards |
| `apps/streamlit_app.py` | Traditional Chinese Designer widgets, explicit JSON actions, live raster preview, associated-design action, status/diagnostic wiring |
| `apps/presentation.py` | Target preview display while preserving saved-result presentation and independent common intensity scales |

Designer computation uses public `intensity_to_amplitude`, `RunConfig` and
`run_and_save_bundle`; loading/integrity/replay retain M5's public boundary.
The actual float64 design raster reaches M5 with `input_png=None`. Preview
pixels are not read back as scientific data. Completed-run presentation uses
the saved bundle, not the current editable design.

Application helpers are deliberately separate from the public scientific API.
`apps.designer.EditorState` retains the immutable design, transient selection,
last editor error and explicit saved-copy path. `select_object`, `replace_design`,
`import_design`, `update_canvas`, `add_object`, `update_object`, `delete_object`
and `move_object` validate editor operations; `save_copy` is the explicit
filesystem action. `apps.presentation.build_target_preview(*, intensity)`
returns a target-only Matplotlib figure, without a solver or file readback.

`apps.workbench.load_associated_design(state, selection, *, runs_root,
offered_nonce)` returns a matching `TargetDesign2D` or `None`. Workbench state
separately records `association_status` (`not_evaluated`, `missing`, `invalid`,
`mismatch`, `match`), its path/error and numerical bundle integrity. A matching
result can explicitly replace the editor; a failed external association leaves
an otherwise valid loaded bundle available.

## Tests

| New path | Evidence scope |
|---|---|
| `tests/test_target_design.py` | Strict schema, geometry, independent memberships, endpoint order, overwrite, exact samples and ownership |
| `tests/test_design_io.py` | JSON round trips, invalid inputs, bounds and safe new-file publication/failure handling |
| `tests/test_designer_controller.py` | Real M2–M5 integration, immutable submissions, power matching, snapshot and association failures, replay independence |
| `tests/test_designer_streamlit.py` | Installed Streamlit AppTest editor/action/state behavior |
| `tests/test_designer_architecture.py` | Numerical/UI/I/O import boundaries and protection of existing contracts |

These layers are distinct from real browser acceptance and deliberate
negative controls. Exact commands, results and limits belong to
[tests and evidence](tests_and_evidence.md), without a test-count quota.

## Documentation and figures

The other modified files are `README.md`, `docs/milestones.md` and
`docs/math_conventions.md` (new §3.16/version 0.9 only, preserving earlier
sections). `docs/roadmap.md` is new. M6 receives only a dated ledger closeout;
its precommit/handoff evidence remains historical.

The six new handoff documents are this code map, `implementation_summary.md`,
`math_used.md`, `tests_and_evidence.md`, `known_limitations.md` and
`tutor_context.md`. Two genuine UI viewport captures are saved at:

- `figures/fig01_designer_preview.png`
- `figures/fig02_designer_saved_result.png`

Actual capture dimensions, hashes and source content are recorded in
[tests and evidence](tests_and_evidence.md#genuine-captured-viewports). Runtime
designs, bundles, raw transcripts and disposable fixtures live in ignored
`runs/`; no artifact is added to an old completed M5 bundle.
