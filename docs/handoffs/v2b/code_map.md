# V2b code map

V2b extends the existing local V1 bench with a separate two-path mode. The
unchanged public V0 source sampler and V2a solver remain the numerical
authority. This document maps the implementation; measured acceptance and
publication records belong to [tests_and_evidence.md](tests_and_evidence.md).

## Python boundary

| File | Responsibility |
|---|---|
| [two_path_adapter.py](../../../apps/virtual_bench/two_path_adapter.py) | Exact typed envelopes; public source-plane validation; owned frozen submissions; one source sample and one `run_two_arm` call for a single result; one source sample and 17 actual runner calls for a complete sweep; genuine failed prefixes. |
| [two_path_protocol.py](../../../apps/virtual_bench/two_path_protocol.py) | Canonical specification hashes, `OHLAB2P` dual-intensity framing, direct copies of returned norms/properties, scalar sweep JSON, route-specific byte caps and the literal phase list. |
| [server.py](../../../apps/virtual_bench/server.py) | Existing loopback/static/body/security boundary; new `/api/v2b/validate`, `/api/v2b/simulate` and `/api/v2b/sweep` routes; one dispatcher and shared computation gate covering legacy sequential, dual and sweep work. |
| [test_virtual_bench_two_path_adapter.py](../../../tests/test_virtual_bench_two_path_adapter.py) | Zero-call validation, exact operation call counts, identical-input direct V2a comparisons, analytic/near-dark/carrier/common-phase cases, actual evanescent survival and failed-sweep provenance. |
| [test_virtual_bench_two_path_protocol.py](../../../tests/test_virtual_bench_two_path_protocol.py) | Independently decoded literal framing, asymmetric port fixtures, endian/axes/padding/descriptor checks, maximum frame bound, invalid-array rejection and scalar sweep structure. |
| [test_virtual_bench_two_path_server.py](../../../tests/test_virtual_bench_two_path_server.py) | Actual ASGI route execution; all active/blocked operation pairs; disconnect/cancellation lifetime; busy, submission, numerical and encoding failures; deliberate recovery; typed partial sweeps and strict JSON. |
| [test_virtual_bench_architecture.py](../../../tests/test_virtual_bench_architecture.py) | Narrow public `ohlab.optics.interference` import allowance and guards against copied optical formulas/private numerical helpers. |

`adapter.py` and `protocol.py` retain the legacy V1 scientific and wire
semantics. The existing `ohlab.optics.SequentialExperiment` and public
`sample_source` supply a validated source at z=0 with an empty component
train. The existing public `ohlab.optics.interference.TwoArmSpec` and
`run_two_arm` implement the complete fixed topology. No numerical core,
existing scientific test, package export or mathematical convention is
changed by V2b.

## Browser and presentation

| File | Responsibility |
|---|---|
| [two_path_contracts.ts](../../../frontend/bench/src/two_path_contracts.ts) | Distinct request/result types, phase-only browser signed-zero canonicalization, strict complete-frame decoding into original float64 arrays, exact echo/identity/scalar validation and bounded fetches. |
| [two_path_state.ts](../../../frontend/bench/src/two_path_state.ts) | Separate scientific draft, validation generation, frozen submission/revision/attachment epoch, explicit single/sweep operations, prior-result retention and atomic presentation preparation. |
| [two_path_presets.ts](../../../frontend/bench/src/two_path_presets.ts) | 64x64 uniform, 128x128 Gaussian and carrier-sensitive unequal-arm examples. Preset selection validates without simulation. |
| [phase_sweep.ts](../../../frontend/bench/src/phase_sweep.ts) | Plot positions from actual returned scalar rows and phase-wise app-owned byte estimates; no optical curve generation or image stacks. |
| [state.ts](../../../frontend/bench/src/state.ts) | Shared client operation gate and sequential attachment invalidation when leaving its mode. |
| [detector.ts](../../../frontend/bench/src/detector.ts) | One common grayscale mapping, joint explicit automatic range, two-texture/two-canvas preparation and cleanup on second-resource failure. Scientific float64 arrays stay unchanged. |
| [scene.ts](../../../frontend/bench/src/scene.ts) | Fixed ideal unfolded topology; same-frame immediate output screens; paired texture commit/rollback/finalization; Float32 presentation-range preflight; owned scene-resource disposal. |
| [main.ts](../../../frontend/bench/src/main.ts), [styles.css](../../../frontend/bench/src/styles.css), [index.html](../../../frontend/bench/index.html) | Mode selector, SI-scaled source/arm editors, phase buttons, dual panels/picks, ten norms, signed diagnostics, stale/prior-result area, explicit phase sweep and labelled partial chart. |

The browser prepares both textures, both detached 2D canvases and the readout
content before synchronous publication. The controller publishes the complete
decoded result only after presentation commit; finalization then releases old
resources. Preparation/commit failure disposes the new resources and retains
the completed numerical result separately from the previous recoverable
result. It never retries the solver automatically.

The 3D texture row reversal is the existing graphics-UV mapping for both
ports, not a physical flip of one output. Raw picks use the original array
indices and common physical axes. Display conversion uses sRGB grayscale
RGBA bytes, unlit materials, no tone mapping, nearest filtering and no
mipmaps; it does not change numerical precision.

## Acceptance tools and evidence

| File | Responsibility |
|---|---|
| [two_path_transport.test.ts](../../../frontend/bench/tests/two_path_transport.test.ts) | Independently constructed frames and strict transport/scalar/error tests. |
| [two_path_state.test.ts](../../../frontend/bench/tests/two_path_state.test.ts) | Explicit submission, rapid-click gate, scientific staleness, held cross-mode responses, signed-zero policy and presentation failure recovery. |
| [two_path_display.test.ts](../../../frontend/bench/tests/two_path_display.test.ts) | Asymmetric paired mapping, common limits/raw reads, dark displays, second-resource failure, resource accounting and presentation-range rejection. |
| [two_path.browser.spec.ts](../../../frontend/bench/tests/two_path.browser.spec.ts) | Production-browser two-path actions, genuine API results, both picks, actual sweep, controlled failure, stale/mode transitions, reload/context loss and deterministic resource sequence. |
| [bench.browser.spec.ts](../../../frontend/bench/tests/bench.browser.spec.ts) | Retained V1 browser assertions rerun against the current service/build; screenshot destination is separated from historical evidence. |
| [validate_v2b_bench.py](../../../scripts/validate_v2b_bench.py) | Independent HTTP decoder and same-input public V2a oracle, source-location evidence, analytic fixtures, actual endpoint closure and controlled partial response checks. |
| [v2b_negative_controls.py](../../../scripts/v2b_negative_controls.py) | Owned isolated mutations with targeted detecting assertions and production-file hash preservation. |

The approved figures are genuine browser captures, not generated explanatory
drawings. Their capture context and hashes belong to the evidence record:

- [fig01_dual_outputs.png](figures/fig01_dual_outputs.png) — the two actual output panels and their common scientific result.
- [fig02_phase_sweep.png](figures/fig02_phase_sweep.png) — returned phase-sweep measurements and the explicitly interpolated chart.
- [fig03_stale_cross_mode.png](figures/fig03_stale_cross_mode.png) — stale/prior-result and mode-attachment behavior.

See [implementation_summary.md](implementation_summary.md) for the workflow
and exact wire keys, [math_used.md](math_used.md) for the reused mathematics,
[known_limitations.md](known_limitations.md) for interpretation/resource
boundaries, and [tutor_context.md](tutor_context.md) for the separate tutor.
