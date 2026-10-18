# W1 — Code map and ownership

This map describes the implemented W1 boundary. Executed acceptance and
publication conditions are recorded in tests_and_evidence.md and its manifests.

| Path | Responsibility |
|---|---|
| `src/ohlab/optics/wave_field.py` | Bounded supported train; noncomputing plan validation/allocation; one V0 run; public ASM sampling; exact canonical terminal; owned readonly intensities/axes and diagnostics |
| `apps/virtual_bench/wave_field_adapter.py` | Cheap grid/train caps, immutable strict submission, existing experiment validator/digest, public sampler invocation and numerical-error boundary |
| `apps/virtual_bench/wave_field_protocol.py` | Distinct bounded binary frame; exact metadata/arrays and independent revalidation; no optical calculation |
| `apps/virtual_bench/server.py` | `/api/w1/simulate`, existing loopback boundary, existing shared actual-worker-lifetime computation gate through encoding/disconnect |
| `frontend/bench/src/wave_field_contracts.ts` | Frozen explicit example; exact plan metadata; bounded frame fetch/decoding and result/resource accounting |
| `frontend/bench/src/wave_field_state.ts` | Existing Sequential-draft observer; explicit request; shared gate; stale/late detachment; numerical/presentation separation; admission and release |
| `frontend/bench/src/wave_field_display.ts` | Shared-range textures, raw section inspection, event-split nearest-sample curtains, transactional preparation/disposal |
| `frontend/bench/src/wave_field_apparatus.ts` | Bounded mounted source/aperture/lens/detector geometry and labels |
| `frontend/bench/src/wave_field_workspace.ts` | Optional existing-Sequential view, cursor/readout, explicit example, display and camera controls |
| `frontend/bench/src/main.ts`, `scene.ts`, `styles.css` | Existing app/renderer/lifecycle integration and namespaced W1 presentation |
| `scripts/validate_w1_wave_field.py` | Independent physical-coordinate dense DFT, full complex Gaussian/lens references, fixed-geometry sampling comparisons and separated timing/allocation/RSS observations |
| `scripts/w1_negative_controls.py` | Copied-new-module scientific/ownership faults, positive/restored assertions and source/test hashes |
| `scripts/w1_controlled_acceptance_server.py` | Task-owned controlled-worker/encoding/failure acceptance harness; not a production fault endpoint |

## Public numerical API

Import directly from `ohlab.optics.wave_field`; existing package exports remain
unchanged:

```python
validate_sampling(experiment: SequentialExperiment,
                  interior_z_m: tuple[float, ...]) -> tuple[float, ...]
default_interior_positions(experiment: SequentialExperiment) -> tuple[float, ...]
section_plan(experiment: SequentialExperiment, *,
             interior_z_m: tuple[float, ...]) -> tuple[WaveFieldPosition, ...]
sample_wave_field(experiment: SequentialExperiment, *,
                  interior_z_m: tuple[float, ...]) -> WaveFieldResult
```

All positions/distances are metres. The first three functions perform no optical
calculation. `WaveFieldPosition` fields are `id`, `stage`, `z_m`,
`anchor_selector`, `anchor_z_m`, `separation_m`. `WaveFieldPlane` adds `norm`,
`previous_norm`, `delta_norm`, `transmission_ratio`, `comparison`,
`on_axis_intensity`, `max_intensity`. Public frozen records validate types,
finiteness, identity, geometry and diagnostic arithmetic.

`WaveFieldResult` contains `experiment`, exact `interior_z_m`, `canonical`,
`planes`, readonly float64 `intensities`, `x_m`, `y_m`; `observation` aliases
`canonical.observation`. Intensities/axes are defensively owned. Existing
readonly-array semantics are not a hardened storage/authentication boundary.

## Transport

POST `/api/w1/simulate` accepts exactly `request_id`, unchanged `experiment`,
and `sampling: {interior_z_m: [...]}`. Validation is noncomputing. The result is
`OHLABWF\0`, protocol version1, message type `w1_wave_field`.

The16-byte `<8sII` preamble carries magic, UTF-8 JSON header length and reserved
zero. Zero padding aligns the payload to8 bytes. Header keys are
`protocol_version`, `message_type`, `request_id`, `experiment_sha256`,
`experiment`, `sampling`, `ordered_section_ids`, `planes`, `stages`, `arrays`.
Array descriptors name exact C-order `float64-le` shape, offset, length and unit;
payload order is intensity stack, x metres, y metres. Full frozen experiment and
request/plan identity are checked before attachment. No intermediate complex
arrays are transported.

Caps:body32,768B; header65,536B; each axis128; at most25 sections;
response3,344,400B. Existing schemas/routes/formats remain separate and unchanged.
The server's single existing worker gate covers all numerical kinds; cancellation
of the HTTP handler does not terminate or release a still-running worker.

## Test map

The three `test_optics_wave_field*.py` files cover93 numerical/ownership,
independent analytic/DFT and architecture checks. Four new
`test_virtual_bench_wave_field*.py` files cover adapter, protocol, route/gate and
architecture behavior. The sole existing architecture-test extension permits
only the named new public W1 adapter/protocol imports. Frontend transport,
state, display, apparatus and production-browser tests occupy the five planned
`wave_field*` test files. Their executed results are in tests_and_evidence.md.

The complete approved inventory remains40 paths:8 modifications/32 creations.
The frozen absolute list and planning-file hashes are under
`runs/w1_implementation_01/frozen/` and `preflight.json`. The full literal
inventory also appears in tests_and_evidence.md; the staging/protection
manifests verify actual paths against that inventory.

## Shared resource ownership

W1 contributes its intensity/axis buffers, active textures, sampled curtain and
sheet geometry, plots, readout backing store and mounted apparatus to the
existing aggregate admission calculation. The scene retains one renderer,
control object, observer and RAF loop. Old/new preparation overlap is admitted
before transport and numerical completion is separate from presentation failure.

Three.js labels in W1 and R03 borrow the same global Sprite quad: two backing
buffers, 92 bytes. The W1 apparatus exposes borrowed buffer identities; when R03
also retains labels, main.ts subtracts precisely that alias from the W1 charge.
The cross-factory test compares actual backing identities. Neither factory
disposes Three's global borrowed geometry. This accounting describes declared
app-owned payload/buffer bytes, not the entire JavaScript heap or GPU memory.
