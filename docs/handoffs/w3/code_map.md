# W3 code map

The exact 46-path inventory remains the frozen planning inventory. Existing
settings, scalar/Jones/wave controllers, renderer and numerical owners stay in
their original files. W3 is selected inside the existing Geometric Routing
workspace; W2 remains the default.

| Owner | Responsibility |
|---|---|
| `src/ohlab/optics/geometric_routing.py` | Additive documented public certified geometry seam. Original W2 implementation remains the baseline prefix. |
| `src/ohlab/optics/refractive_routing.py` | `RefractiveScene.from_dict`, `validate_scene`, `trace_routes`; owned immutable scene/results, closed body admission, finite nearest intersections, propagated Snell/TIR and medium/terminal accounting. Only exact documented public geometry imports. |
| `apps/virtual_bench/refractive_routing_adapter.py` | Own UUID/digest and validated submission, one public trace call, separate numerical and encoding failures. Validation never calls trace. |
| `apps/virtual_bench/refractive_routing_protocol.py` | Closed versioned JSON, identity/graph/medium/cap validation, bounded atomic encoding/decoding; no optical implementation. |
| `apps/virtual_bench/server.py` | W3 POST endpoints and eleventh operation through the existing actual-Future gate, including encoding; W3-specific closed boundary errors. |
| `frontend/bench/src/refractive_routing_contracts.ts` | Independent wire/graph validation, exact scene identity, frozen A/B/C inputs and resource charges. No JavaScript Snell solver. |
| `frontend/bench/src/refractive_routing_state.ts` | Explicit Trace actor, draft/revision/attachment identity, stale detachment, admission, numerical completion and manual presentation recovery. |
| `frontend/bench/src/refractive_routing_apparatus.ts` | Display returned finite vertices/normals/segments with existing Three.js, mounted transparent body and reusable annotations. Display triangles never determine intersections. |
| `frontend/bench/src/refractive_routing_panels.ts` | Source/body/index/pose controls, full-value local scrolling, face/event selection and medium/angle readouts. |
| Existing `main.ts`, `state.ts`, `geometric_routing_workspace.ts`, `styles.css` | Lazy actor integration, model switch, aggregate unchanged global budgets, explicit release and namespaced W3 layout. |
| `scripts/validate_w3_refractive_routing.py` | Independent Decimal/scalar/vector references and exact original operator stress outside the numerical core. |
| `scripts/w3_acceptance.py`, `w3_controlled_acceptance_server.py` | Exclusive fresh evidence, exact discovered browser identities and explicitly labelled worker/transport controls. Ordinary production browser evidence uses a production child. |

New core/geometry/reference/compatibility tests, adapter/protocol/server/architecture
tests and frontend transport/state/apparatus/browser tests remain in their
approved new paths. The existing W2 response capture gains explicit optional
W3 configuration while retaining its original defaults and one-response clone.
The global architecture guard gains only the exact adapter-to-public-core edge.

Ownership flows from copied input to immutable admitted scene, bounded numerical
result, validated response and prepared display. Atomic publication checks the
complete request/model/scene identity; selecting a short event ID additionally
binds branch and event. Presentation failure retains completed numerics for a
manual recovery without submitting another scientific request.
