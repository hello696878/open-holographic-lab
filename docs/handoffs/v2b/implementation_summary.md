# V2b implementation summary

Recorded 2026-10-06. Accepted starting revision:
`a215da74cb0f85e8727bbbdffb6408da4d3df3d4`. V2b connects the existing
classical scalar monochromatic two-path V2a calculation to a separate mode of
the existing local 3D bench. Sequential optics remains the default.

## Delivered behavior

The two-path editor accepts the supported V0 uniform/Gaussian incident source,
SI grid/wavelength, two nonnegative propagation distances and signed extra
arm-1 phase. UI units are nm, micrometres and millimetres where labelled;
radians are authoritative. Buttons select 0, pi/2 and pi. Nonzero phase is
never wrapped. Browser-authored negative-zero phase canonicalizes to positive
zero before validated identity, consistent with ordinary JSON.stringify.
This UI transport policy does not change V2a phase physics or Python's ability
to serialize genuine -0.0.

Validation samples no field and runs no solver. A deliberate Simulate samples
one source-plane SequentialExperiment with an empty train and observation z=0,
then calls public run_two_arm exactly once. Public TwoArmSpec and returned
fields, ten norms and properties supply all optical values. No Gaussian,
ASM, mixing or norm formula is duplicated in the adapter. Both output screens
show the actual immediate B_dagger results in their common transverse frame.
Cosmetic unfolded lanes add neither propagation nor reflection/flip/conjugation.
Uniform relative-phase cases display uniformly bright/dark outputs.

Distinct typed /api/v2b/validate, /simulate and /sweep routes preserve legacy
OHLABV1 routes, framing and limits. OHLAB2P carries ordered float64-le port-0
intensity, port-1 intensity, x and y. The client validates the entire bounded
frame, specification, identity, scalar records and payload before preparing
both new canvases/textures and atomically publishing one completed result.
Second-resource preparation/commit faults leave no half-active result, dispose
partial resources and preserve the old submitted result separately. Successful
numerical completion remains distinguishable from presentation failure and
never causes an automatic solver replay.

Both outputs share explicit color limits; only deliberate joint automatic
range selection changes them. Raw maxima, saturation, both original float64
readouts, coordinates, request/specification, original-input fractions, total
ratio, ten norms and signed differences remain available. Dark output is black;
undefined ratios remain null and small cancellation residuals are retained.
Camera/selection/resize/colors are presentation operations. Scientific edits
immediately detach both active textures. Prior results remain labelled with
original request and specification. Switching away and back invalidates late
attachment without aborting ongoing numerical work or automatically submitting.

Run Phase Sweep is a separate deliberate action. A frozen source/grid/two-arm
configuration requests exactly 17 literal phases, including independently
calculated 0 and 2*pi. The source is sampled once and public run_two_arm is
called once per phase. Only actual scalar rows are returned. Chart connections
are labelled visual interpolation; clicking does not compute, and simulating
that phase requires a separate explicit action. Expected numerical failure
returns HTTP 422, unexpected internal failure HTTP 500, with status failed,
completed genuine contiguous prefix, completed_count, failed_index and bounded
error. A failed sweep is never relabelled complete or filled with analytic rows.

Sequential, dual and sweep operations share one existing worker-lifetime gate.
A disconnected HTTP client leaves it busy until actual worker completion;
validation/health stay responsive, other numerical routes receive 409, and a
later intentional operation can run after completion. There are no production
fault-control endpoints.

## Validation and bounded resources

Fresh unchanged baseline: **2006 passed, 1 skipped in 110.00s (0:01:50)**.
First retained/new Python suite: **2079 passed, 1 skipped in 251.08s (0:04:11)**.
The original Windows symlink-privilege skip is retained; junction tests remain.
Installed frontend baseline: 65 tests; current final unit batch: 129 tests,
7 files, with typecheck exit 0. The production build succeeds with the retained
large-chunk warning. Final restored full suite after all isolated controls: **2079 passed, 1 skipped
in 256.93s (0:04:16)**. Both earlier suite outputs remain preserved separately.

Independent actual HTTP validation passed 18 complete dual fixtures and 3
17-point sweeps against unchanged direct public V2a output: every transported
intensity/axis/norm/property matched exactly on identical captured inputs.
Known/near-dark/common-phase/unequal-carrier/evanescent cases also passed explicit
analytic bounds. Largest measured periodic fraction closure discrepancy was
4.440892098500626e-16 against rtol=atol=2e-13, preserving independent endpoints.
Maximum 512x512 accepted frame was 4,204,360 bytes; route bound is 4,218,896 bytes.
The loss fixture retained total output/input 0.5372364078808002.

All 14 deliberate fault variants across the 11 requested categories plus atomic
second-texture failure triggered their identifying assertions in isolated
copies. All selected restored tests passed and production hashes remained
unchanged. Actual controlled HTTP/browser partial failure preserved 3 genuine
rows and failed index 3 with 422. Separate genuine Chrome disconnect checks
passed for sequential, dual and sweep worker lifetime. The first ordinary
browser batch passed 18 and skipped 2 separate controlled cases; a subsequent
new GPU-camera check failed and is preserved. Its corrected isolated actual
GPU/readout check passed. The final whole-production Chrome rerun passed
**18 tests, with 3 controlled cases skipped in that ordinary batch (1.7m)**.
Those controls passed in separate actual-browser executions. Current V1 API
10 cases and V2b 18 dual/3 sweep cases passed on refreshed final assets.
All three genuine UI figures were regenerated and inspected.

Single-run axes cap 512, sweep axes cap 128, and sweep points exactly 17. App-owned
persistent 16 MiB/transient 32 MiB budgets include retained numerical arrays,
coordinate arrays, counted scalar JSON and owned preparation resources. They
exclude total JS heap, browser/process memory and internal renderer caches;
these are ownership budgets, not measured tab-memory claims. Ordinary retention
is one sequential result, one dual result and one scalar sweep. Atomic failed
presentation may additionally retain the new completed numerical result while
the prior displayed result remains recoverable; this bounded exception is
counted, not an unbounded result history. Repeated mode/result/sweep/resize/
color/stale sequences exercise disposal and bounded owned counts.

## Protected scope and publication boundary

The approved inventory is exactly 36 paths: 12 modifications and 24 creations,
listed below. All V0/V2a numerical source and scientific tests, mathematical
conventions, exports/initializers, M5 contracts, Streamlit apps, package files,
lockfile and historical handoffs/evidence are protected. Legacy browser
assertions are unchanged; only its screenshot-directory selection permits a
fresh ignored destination so historical V1 figures survive reruns.
No dependency install/version change, environment rebuild or global setting
change occurred. Final strict precommit inventory confirms exactly 36 changed paths:
12 approved modifications and 24 creations, with all 217 protected pre-existing
tracked files unchanged. Installed versions/all metadata/source locations
(53 entries, 52 names), Node package versions and lockfile bytes are unchanged.
The final record is `runs/v2b_acceptance_20261006/inventory_precommit.json`.

One commit with subject `feat(v2b): integrate two-path interference into 3D bench`
and a normal origin/main push are approved after complete precommit acceptance.
Clean-postcommit rebuilt assets/import locations, fresh sequential and dual
browser smoke, both direct-V2a readouts and one real 17-point sweep must pass
before push. Actual publication SHAs and final clean state belong to the
ignored verification record and completion report; no future outcome is claimed
here. V2c, reflection geometry, polarization, persistence, instruments,
hardware and later work are not started. Teaching remains separate.

## Exact approved inventory

```text
README.md
docs/milestones.md
docs/roadmap.md
apps/virtual_bench/server.py
tests/test_virtual_bench_architecture.py
frontend/bench/index.html
frontend/bench/src/state.ts
frontend/bench/src/detector.ts
frontend/bench/src/scene.ts
frontend/bench/src/main.ts
frontend/bench/src/styles.css
frontend/bench/tests/bench.browser.spec.ts
apps/virtual_bench/two_path_adapter.py
apps/virtual_bench/two_path_protocol.py
tests/test_virtual_bench_two_path_adapter.py
tests/test_virtual_bench_two_path_protocol.py
tests/test_virtual_bench_two_path_server.py
frontend/bench/src/two_path_contracts.ts
frontend/bench/src/two_path_state.ts
frontend/bench/src/two_path_presets.ts
frontend/bench/src/phase_sweep.ts
frontend/bench/tests/two_path_transport.test.ts
frontend/bench/tests/two_path_state.test.ts
frontend/bench/tests/two_path_display.test.ts
frontend/bench/tests/two_path.browser.spec.ts
scripts/validate_v2b_bench.py
scripts/v2b_negative_controls.py
docs/handoffs/v2b/implementation_summary.md
docs/handoffs/v2b/code_map.md
docs/handoffs/v2b/math_used.md
docs/handoffs/v2b/tests_and_evidence.md
docs/handoffs/v2b/known_limitations.md
docs/handoffs/v2b/tutor_context.md
docs/handoffs/v2b/figures/fig01_dual_outputs.png
docs/handoffs/v2b/figures/fig02_phase_sweep.png
docs/handoffs/v2b/figures/fig03_stale_cross_mode.png
```

## Exact new wire schemas

All listed object keys are exact: unknown, missing, duplicate and nonfinite
values fail closed. This is a version-1 V2b transport, distinct from retained
OHLABV1. Request IDs are canonical lowercase UUIDv4 strings. Numbers below use SI;
float pairs are ordered port 0,port 1. Neither complex fields nor arm intermediates
are transported. The source-plane adapter reuses public V0 validation.

### Single request and validation

POST /api/v2b/validate and /api/v2b/simulate accept the same envelope:

```json
{
  "protocol_version": 1,
  "message_type": "two_path_submission",
  "request_id": "684d2f11-30f9-4bc4-b6b3-faa8a44b8c1a",
  "experiment": {
    "wavelength_m": 6.33e-7,
    "grid": {"ny": 64, "nx": 64, "dy": 4e-6, "dx": 4e-6},
    "source": {"kind": "uniform", "amplitude": 1.0, "phase_rad": 0.0},
    "two_arm_spec": {
      "arm_0_distance_m": 0.002,
      "arm_1_distance_m": 0.002,
      "relative_phase_rad": 1.5707963267948966
    }
  }
}
```

The exact experiment keys are wavelength_m,grid,source,two_arm_spec. Grid has
ny,nx,dy,dx. Uniform source has kind,amplitude,phase_rad; Gaussian source has
kind,amplitude,phase_rad,waist_radius_m,waist_z_m,center_x_m,center_y_m. The
uniform/Gaussian public source domains remain unchanged. Single axes are
integers 1..512, pitches/wavelength positive finite, arm distances nonnegative
finite, and phase finite signed radians. Validation returns HTTP 200 with exactly:

```text
{
  protocol_version: 1,
  message_type: "two_path_validation",
  request_id: submitted ID,
  experiment_sha256: canonical complete SI experiment SHA256,
  experiment: canonical complete experiment
}
```

The digest uses Python JSON sort_keys=True,separators=(",",":"),
ensure_ascii=True,allow_nan=False. The browser treats the validated canonical
echo/identity as authoritative while requiring structural agreement with the
frozen request. Ordinary browser negative-zero phase is positive zero before
this step; no general custom JSON serializer is used.

### Complete dual frame

HTTP 200 application/octet-stream uses 16-byte little-endian `<8sII>` preamble:
8-byte magic `OHLAB2P\0`, JSON-header byte count, reserved 0. Strict UTF-8 header
is at most 16384 bytes, followed by zero padding to an 8-byte boundary. Exact
header keys and nested scalar records are:

```text
{
  protocol_version: 1,
  message_type: "two_path_result",
  request_id,
  experiment_sha256,
  experiment,
  ports: ["port_0", "port_1"],
  norms: {
    inputs: [N0, N1], split: [N0, N1], propagated: [N0, N1],
    combiner: [N0, N1], outputs: [N0, N1]
  },
  diagnostics: {
    inputs_total, split_total, propagated_total, combiner_total, outputs_total,
    split_delta, propagation_delta, phase_delta, recombination_delta, total_delta,
    output_fractions: [number|null, number|null],
    total_output_ratio: number|null
  },
  arrays: [four descriptors in the order below],
  intensity_max: [maximum_port_0, maximum_port_1]
}
```

Each descriptor has exactly name,role,port_id,dtype,order,shape,offset_bytes,
nbytes,units. Offsets are relative to payload start, contiguous with no gaps,
no overlap and no trailing payload. Dtype is "float64-le", order "C".

| Ordered name | role / port_id | shape | units |
|---|---|---|---|
| intensity_port_0 | intensity / port_0 |[ny,nx]|amplitude_unit^2|
| intensity_port_1 | intensity / port_1 |[ny,nx]|amplitude_unit^2|
| x_m | coordinate / null |[nx]|m|
| y_m | coordinate / null |[ny]|m|

Byte count is 8 times the shape product. Intensities are finite and nonnegative;
axes exactly follow the submitted canonical grid. Maxima, norms and diagnostic
relationships are validated before publication. Norms use amplitude-unit² m²,
fractions use the original input total; zero-input ratios are null. The complete
route cap is 4,218,896 bytes; [known_limitations.md](known_limitations.md) derives
its complete bound and preserves the old legacy cap.

### Sweep request, complete and failed replies

POST /api/v2b/sweep accepts exactly:

```text
{
  protocol_version: 1,
  message_type: "two_path_sweep_submission",
  request_id,
  fixed_experiment: {
    wavelength_m, grid, source, arm_0_distance_m, arm_1_distance_m
  },
  phases_rad: exact 17-value list below
}
```

The fixed experiment is flat and excludes the unused current-draft extra phase.
Grid/source structures and domains remain as above, except sweep axes 1..128.
The exact requested literal list is:

```json
[
  0.0, 0.39269908169872414, 0.7853981633974483, 1.1780972450961724,
  1.5707963267948966, 1.9634954084936207, 2.356194490192345,
  2.748893571891069, 3.141592653589793, 3.5342917352885173,
  3.9269908169872414, 4.319689898685965, 4.71238898038469,
  5.105088062083414, 5.497787143782138, 5.890486225480862,
  6.283185307179586
]
```

The response is strict JSON, at most 65536 bytes, with exactly:

```text
{
  protocol_version: 1,
  message_type: "two_path_sweep_result",
  request_id,
  fixed_experiment_sha256,
  fixed_experiment,
  phases_rad,
  status: "complete" | "failed",
  requested_count: 17,
  completed_count,
  failed_index: integer|null,
  rows: [actual contiguous rows],
  error: {code, message}|null
}
```

The digest hashes canonical {fixed_experiment,phases_rad} using the same Python
JSON policy. Each actual row has exactly:

```text
{
  index, phase_rad, input_norm,
  output_norms: [N0, N1], output_fractions: [number|null, number|null],
  total_output_ratio: number|null,
  split_delta, propagation_delta, phase_delta, recombination_delta, total_delta
}
```

Complete HTTP 200 requires status complete, all 17 genuine rows,
completed_count 17, failed_index null,error null. Expected numerical/domain failure
returns 422, unexpected internal loop failure 500: status failed,
completed_count 0..16, failed_index=completed_count, actual completed prefix only.
Error code is a 1..64-character string; message 1..300 characters.
Expected failure code is numerical_failure; unexpected failure code sweep_failed
with a generic internal message. A source-sampling failure has zero genuine rows
and failed index 0. No invisible retry, analytic substitute or missing row is
allowed. Encoding failure cannot safely publish this schema and uses the
regular error envelope instead.

### Regular failures

V2b regular errors have exactly:

```text
{
  protocol_version: 1,
  message_type: "two_path_error",
  request_id: submitted ID|null,
  error: {code: bounded string, message: bounded string}
}
```

HTTP 400 invalid JSON/body framing; 408 body-read timeout; 413 oversized request;
415 unsupported Content-Type;422 invalid experiment or single numerical failure;
409 shared gate busy;500 executor submission, encoding or unexpected single
failure;503 cancelled before worker starts;499 observed client interruption
when a reply is still deliverable. Shared Host/header/Origin and unknown-route/
method rejection preserve the existing generic V1 error envelope and 400/403 or
404/405. The exact status/code table, security boundaries and interruption
limitations are in [known_limitations.md](known_limitations.md). A disconnect
is not a scientific completed/failed sweep response.
