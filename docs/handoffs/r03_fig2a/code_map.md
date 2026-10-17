# A implementation map

The exact approved inventory is frozen in
`runs/r03_ideal_polarization_impl_01/scope.json`. There are41 paths:
10 pre-existing modifications and31 creations. No package initializer or
dependency/lockfile changes are required.

| Responsibility | Files |
|---|---|
| Small statistical measurement primitive | `src/ohlab/optics/polarization_statistics.py`: `PolarizationMeasurement`, `measure_coherency`, `coherency_from_samples`, `analyzer_intensity` |
| Fixed ideal ensemble | `src/ohlab/optics/r03_fig2a.py`: `IdealPolarizationSpec`, `IdealPolarizationResult`, `run_ideal_polarization` |
| Independent numerical evidence | `tests/test_polarization_statistics.py`, `tests/test_polarization_statistics_analytic.py`, `tests/test_r03_fig2a.py`; `scripts/validate_r03_fig2a.py`, `scripts/r03_fig2a_negative_controls.py` |
| Core boundary | `tests/test_polarization_statistics_architecture.py` |
| Strict closed JSON contract | `apps/virtual_bench/r03_fig2a_protocol.py` and its protocol tests |
| Immutable validated settings and one core call | `apps/virtual_bench/r03_fig2a_adapter.py` and its adapter tests |
| Existing service integration | `apps/virtual_bench/server.py`; `tests/test_virtual_bench_r03_fig2a_server.py` |
| Narrow architecture guards | `tests/test_virtual_bench_architecture.py`, `tests/test_virtual_bench_r03_fig2a_architecture.py` |
| Browser decoding and immutable identity | `frontend/bench/src/r03_fig2a_contracts.ts`; `frontend/bench/tests/r03_fig2a_transport.test.ts` |
| Submitted/result lifecycle | `frontend/bench/src/r03_fig2a_state.ts`; `frontend/bench/tests/r03_fig2a_state.test.ts` |
| Phase/readout preparation and declared ownership | `frontend/bench/src/r03_fig2a_display.ts`; `frontend/bench/tests/r03_fig2a_display.test.ts` |
| Original mounted schematic | `frontend/bench/src/r03_fig2a_apparatus.ts` |
| Integrated research workspace | `frontend/bench/src/r03_fig2a_workspace.ts` |
| Existing application/renderer integration | `frontend/bench/src/main.ts`, `state.ts`, `scene.ts`, `styles.css` |
| Actual production-browser checks | `frontend/bench/tests/r03_fig2a.browser.spec.ts` |
| Orientation, normative appended contract and stage boundary | `README.md`, `docs/math_conventions.md`, `docs/roadmap.md`, `docs/milestones.md` |
| New handoff and genuine application figures | This directory's six Markdown documents and two PNG captures |

## Data flow

An explicit browser submission binds complete settings, a request UUID and the
validated SHA256 identity. The existing service admits the calculation through
its shared actual-Future-lifetime gate. The adapter calls the public ideal
runner once. That runner generates one local16×16 realization, applies the
declared algebraic elements and measures four uncentered second moments.
The response transports both actual phase arrays and all authoritative readings.
The browser validates the closed response and publishes its mask/readout in one
prepared transaction. Display recovery operates on retained completed data.

All four existing ordinary modes retain their contracts and document formats.
A is separate navigation and has no settings import/export. It reuses the one
existing WebGL renderer and restores the old apparatus/camera on return.
The existing all-mode release includes A's result/display owners while keeping
scientific drafts and useful documents. No second backend queue is created.

## Reproduction

Use the existing Windows interpreter and installed frontend tools. Exact current
commands, unedited streams and application acceptance evidence are listed in
[tests and evidence](tests_and_evidence.md). Numerical scripts require a fresh
owned output directory and refuse to overwrite previous runs. No test imports
or executes the paper's code or MAT data.
