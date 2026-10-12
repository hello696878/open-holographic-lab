# V2d code map

Recorded 2026-10-12. Approved scope: exactly 35 paths, nine modifications and
twenty-six creations. Exact schemas are fixed in implementation_summary.md.

| Path | Responsibility |
|---|---|
| apps/virtual_bench/polarization_adapter.py | Strict immutable V2d spec, public source-plane construction, ordered public Jones calls, stage/sample capture, genuine full-train sweep |
| apps/virtual_bench/polarization_protocol.py | Scientific-independent framing/identity/finite transport, four ordered float64 arrays and bounded scalar sweep replies |
| apps/virtual_bench/server.py | Three new routes sharing the existing actual-worker-lifetime gate and local security boundary |
| tests/test_virtual_bench_architecture.py | Narrow explicit public polarization import permission only for polarization_adapter.py; unrelated guards retained |
| tests/test_virtual_bench_polarization_adapter.py | Direct-public fidelity, ownership, ordered calls, source/coefficients, samples and sweep prefixes |
| tests/test_virtual_bench_polarization_protocol.py | Identity, framing/caps/roles/endian/finite values and malformed transport rejection |
| tests/test_virtual_bench_polarization_server.py | Five-operation busy matrix, responsive validation/health, disconnect/failure lifetime and local boundary |
| tests/test_virtual_bench_polarization_architecture.py | Intended public imports, forbidden dependency/private/solver imports and passive independent boundaries |
| frontend/bench/src/polarization_contracts.ts | Distinct strict V2d request/result/sweep parsing and complete identity |
| frontend/bench/src/polarization_state.ts | Third-mode drafts/immutable submissions, gate sharing, stale responses and numerical/presentation separation |
| frontend/bench/src/polarization_presets.ts | Explicit finite coefficients and ideal analyzer/crossed/QWP/HWP presets in authoritative radians |
| frontend/bench/src/polarization_display.ts | Generic intensity pair preparation, actual-sample trajectory relation, fixed-tau/darkness and owned resources |
| frontend/bench/src/main.ts | Third-mode UI, controls, all-mode ownership, atomic result transaction and read-only acceptance snapshot |
| frontend/bench/src/scene.ts | Procedural schematic element/axis meshes, incident/final textures, picking/disposal and owned trajectory callback |
| frontend/bench/src/state.ts | Existing synchronous client gate extended to polarization |
| frontend/bench/src/styles.css | Accessible third-mode layout and paired readouts |
| frontend/bench/tests/polarization_transport.test.ts | Independently constructed frames, strict identities/limits/sweeps |
| frontend/bench/tests/polarization_state.test.ts | Edits, requests, late/cross-mode responses, rapid clicks and explicit operations |
| frontend/bench/tests/polarization_display.test.ts | Shared scales, fixed-tau common phase, tiny nonzero sample, atomic rollback and teardown |
| frontend/bench/tests/polarization.browser.spec.ts | Genuine production and separately controlled browser acceptance, snapshots and UI screenshots |
| scripts/validate_v2d_bench.py | Real HTTP captures versus direct public operations and unchanged independent analytic/Decimal references |
| scripts/v2d_negative_controls.py | Reproducible isolated mutations, intended assertions, exact restoration and production hashes |
| scripts/v2d_controlled_acceptance_server.py | Explicit test-only child service for genuine failed prefixes and controlled real-worker disconnects |
| README.md | Workflow, exact installed-tool build/launch commands and scope |
| docs/milestones.md | V2d evidence and dated read-back of existing V2c publication record |
| docs/roadmap.md | Current bounded integration and remaining deferred work |
| docs/handoffs/v2d/implementation_summary.md | Complete exact new wire/scientific/display contract and acceptance status |
| docs/handoffs/v2d/code_map.md | This map and protected boundaries |
| docs/handoffs/v2d/math_used.md | Unchanged public scientific conventions and independent presentation expectations |
| docs/handoffs/v2d/tests_and_evidence.md | Exact fresh commands/outputs, provenance, controls/resources and limitations |
| docs/handoffs/v2d/known_limitations.md | Physical, arithmetic, transport, presentation and evidence boundaries |
| docs/handoffs/v2d/tutor_context.md | Support for separate tutoring without learning claims |
| docs/handoffs/v2d/figures/fig01_complex_transformation.png | Genuine UI transformation with actual complex-sample trajectory |
| docs/handoffs/v2d/figures/fig02_angle_sweep.png | Genuine computed thirteen-point sweep |
| docs/handoffs/v2d/figures/fig03_order_loss_stale.png | Genuine ordered elements, loss and original-configuration stale result |

All other existing tracked files are protected, including numerical modules,
scientific tests/guards, normative math, exports, V0/V2a schemas, M5 bundles,
Streamlit, legacy app adapters/protocols and frontend helpers/tests/configs,
dependency declarations/lockfile, engineering instructions and historical
handoffs/figures. No essential new acceptance code is hidden solely in ignored
captures. The controlled server is not imported by production.
