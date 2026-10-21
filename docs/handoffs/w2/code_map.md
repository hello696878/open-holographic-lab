# W2 code map

W2 adds one `Geometric Routing` workspace to the existing laboratory. This
map describes the approved 42-path candidate and actual module boundaries;
it does not declare the full product/browser gates accepted. Current gate
status, exact outputs and remaining work belong in
[tests_and_evidence.md](tests_and_evidence.md). Publication is not authorized.

## One calculation, separate owners

1. `GeometricRoutingWorkspace` renders the editor and submitted result.
   `GeometricRoutingController` owns the draft, validation generation,
   revision/attachment epoch, explicit Trace identity and retained results.
2. Validation posts the complete scene to `/api/w2/validate`. The server's
   strict JSON parser and `validate_submission` create an immutable
   `GeometricScene`; this operation constructs frames/admission certificates
   but does not trace or acquire the computation gate.
3. Trace submits the UUID, opaque validated scene digest and complete scene.
   The existing server `ComputationGate` runs `trace_submission` inside its
   one actual-worker lifetime. The adapter invokes `trace_routes` exactly
   once, then validates/encodes its result before that worker ends.
4. The browser consumes the original bounded response. Full scene/digest,
   frame, record/relationship, limit, status and weight checks precede
   publication. The controller rejects attachment after a revision or epoch
   change. Numerical completion and display failure remain separate.
5. `prepareGeometricRoutingDisplay` prepares returned geometry for the shared
   renderer. Its transaction can commit/finalize or dispose/rollback. Manual
   presentation recovery reuses a fresh retained result without tracing.

## New numerical and API modules

| Path | Responsibility and public boundary |
|---|---|
| `src/ohlab/optics/geometric_routing.py` | `GeometricScene.from_dict/to_dict`, `validate_scene`, `trace_routes`, immutable `GeometricTraceResult`; finite-face geometry, certified propagated intervals, deterministic branches, actual terminal points and leaf-weight ledger. No UI, I/O or wave-solver import. |
| `apps/virtual_bench/geometric_routing_adapter.py` | `ValidatedGeometricSubmission`, `validate_submission`, `validation_reply`, `trace_submission`, contextual `RoutingNumericalError`. Captures owned request identity and delegates once to the public numerical module. |
| `apps/virtual_bench/geometric_routing_protocol.py` | Strict request parsing, canonical `scene_digest`, validation/trace encoding, `validate_trace_reply`, `decode_trace_result`, bounded errors. Closed records and graph validation; no scientific imports or intersection formula. |

The immutable core DTO serializes ten fields; the adapter/protocol add the
version/message/UUID/model/digest envelope. Non-wire `pose_certificates` and
result `certificates` retain numerical enclosures for independent validation.
They are not a hidden new response or settings-document version.

## New frontend modules

| Path | Responsibility |
|---|---|
| `frontend/bench/src/geometric_routing_contracts.ts` | Closed scene/result types, `W2_PRESETS`, bounded fetch/strict decode, structural identity, fixed limits and declared resource ownership. No frontend optical solver. |
| `frontend/bench/src/geometric_routing_state.ts` | `GeometricRoutingController`: explicit `trace`, draft edits and validation, late-result detachment, separate current/previous/completed numerical owners, transactional presentation recovery and result release. |
| `frontend/bench/src/geometric_routing_apparatus.ts` | `createGeometricRoutingApparatus`, `prepareGeometricRoutingDisplay`, `routingDisplayMatrix`; mounted finite faces, returned paths/hits, DOM-label projection, selection and disposal. Uniform `W2_WORLD_SCALE=10`; picking is interaction only. |
| `frontend/bench/src/geometric_routing_workspace.ts` | English editor and inspector, A/B/C preset loading, camera actions, selected branch/hit, full-precision bounded readouts, terminal ledger and unsupported scene-file notice. |

Camera/selection/branch inspection do not call Trace. Editing changes only
the named numeric component; initial display formatting is not a scientific
write. W2 never stretches W1 field textures around returned ray segments.

## Nine existing integration paths

| Modified path | Bounded integration |
|---|---|
| `README.md` | Workspace operation and model limitations. |
| `docs/math_conventions.md` | New independent §3.23 and Change Log; old model contracts remain. |
| `docs/milestones.md` | W2 scope/current evidence state without revising historical completion evidence. |
| `apps/virtual_bench/server.py` | W2 routes, strict body parser and dispatch through the existing worker gate; loopback boundary and old routes remain. |
| `frontend/bench/src/main.ts` | Workspace switching, resource admission/ownership, document visibility preservation and global release wiring. |
| `frontend/bench/src/scene.ts` | W2 group attach/replace/detach, camera preservation, shared animation/render loop and label updater; no numerical intersections. |
| `frontend/bench/src/state.ts` | Only the shared client gate's W2 mode/Trace-kind extension. |
| `frontend/bench/src/styles.css` | Namespaced routing layout, readable nonwrapping scalars and bounded scroll access. |
| `tests/test_virtual_bench_architecture.py` | Exact new adapter-to-public-core permission; old forbidden imports and existing exceptions stay intact. |

No existing numerical source, package initializer, dependency/lockfile,
settings v1/v2 schema, old capture owner or historical handoff is an approved
modification. The frozen inventory is preserved at
`runs/w2_geometric_routing_plan_01/inspection/proposed_inventory.json`.

## Validation and evidence owners

| New paths | Scope |
|---|---|
| `tests/test_optics_geometric_routing.py` | Public type/value validation, finite domains, ambiguity, nearest order, real caps/equality precedence, revisits, immutable ownership and caller floating-point settings. |
| `tests/test_optics_geometric_routing_references.py` | Independent hand, Fraction and Decimal160 references; pose, 3D/local frames, full32-state chains for stored-frame and ideal-angle targets, covariance and detecting numerical controls. |
| `tests/test_optics_geometric_routing_architecture.py` | Passive core, standard-library-only dependency guard, unchanged old exports and deliberately forbidden-source controls. |
| `tests/test_virtual_bench_geometric_routing_{adapter,protocol,server,architecture}.py` | Owned delegation, strict JSON/graph/cap rules, actual ASGI/shared-gate lifetime and the exact architecture boundary. |
| `frontend/bench/tests/geometric_routing_{transport,state,apparatus}.test.ts` | Decoder/identity/resources, explicit operation state and returned presentation ownership. |
| `frontend/bench/tests/geometric_routing.browser.spec.ts` | Genuine production interaction, numerical/raw-response comparison, controlled failures, old-workspace regressions and visual evidence. |
| `frontend/bench/tests/support/w2_response_capture.ts`, `frontend/bench/tests/w2_response_capture.test.ts` | Test-only original-response clone with one fetch, exact identity, bounded retention, consume/cleanup and behavioral checks. |
| `scripts/validate_w2_geometric_routing.py` | Independent direct numerical/reference/resource evidence, optional saved original-browser JSON comparison, isolated deliberate numerical source faults and restored assertions. |
| `scripts/w2_controlled_acceptance_server.py` | Opt-in test-only production child with declared work/encoding holds; no production fault route. |
| `scripts/w2_acceptance.py`, `tests/test_w2_acceptance_isolation.py` | Fresh invocation/test evidence destinations, containment/collision/reparse checks, source/test-ID declarations, exclusive artifacts and honest result classification. |

The six new handoff documents are `implementation_summary.md`, `code_map.md`,
`math_used.md`, `tests_and_evidence.md`, `known_limitations.md` and
`tutor_context.md`. The three approved figure paths are genuine production
`figures/folded_route.png`, `figures/split_blocked_route.png` and
`figures/trace_inspection.png`; planning mockups cannot fill those roles.

## Reproduction and current core evidence

Use the existing Windows interpreter, with no environment rebuild:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest -q -p no:cacheprovider tests/test_optics_geometric_routing.py tests/test_optics_geometric_routing_references.py tests/test_optics_geometric_routing_architecture.py
.\.venv\Scripts\python.exe -B -X utf8 scripts/validate_w2_geometric_routing.py --output-dir runs\NEW_EXCLUSIVE_CORE_EVIDENCE --negative-controls
```

The second command requires a new output directory. Current core evidence is
under `runs/w2_geometric_routing_implementation_01/core/`:
`development_core_final_03`, `validator_result_03`,
`adapter_pipeline_record256_01`, `NUMERICAL_CONTRACT_AND_EVIDENCE.md` and
`core_handoff_manifest.json`. The current78 focused passes and14 direct /
16 deliberate-fault checks do not stand in for the final Python, frontend,
ASGI, controlled, production-browser or visual-review gates.
