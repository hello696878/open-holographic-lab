# W3 — Ideal refractive routing implementation candidate

Implementation and validation are approved within the frozen46-path inventory. This candidate must remain UNSTAGED and UNCOMMITTED for visual review; commit/push are not authorized. Current acceptance status is recorded in tests_and_evidence.md. No later optics or persistence is included.

## Frozen scientific and wire contract

Baseline828c7ff9080b174d5eae73b36f2c43608a4c94d7. Approved contract SHA256 a7fad2d71ddd1a422a8202b2dcc6eff184b8a77f392aa5593ddf69608cbd0777 is preserved in runs/w3_refractive_routing_plan_01/model_contract.json, not rewritten. The following contract is completed before executable integration.

Model `w3_ideal_refractive_routing_v1`, scene schema1/protocol1. POST `/api/w3/validate` consumes request_id+scene; POST `/api/w3/trace` consumes request_id+scene_sha256+scene. Validation owns/admits the complete scene and never traces. Trace owns the same actual-worker-lifetime gate through encoding. UUID4 and canonical full-scene SHA256 bind model/request/scene/branch/event identity. A short e0002 alone cannot attach.

One nominal-unit source outside at most one closed homogeneous convex body. Exterior and interior indices each[1,2.5]; ideal constant indices with no material database. Geometry dimensions[1e-4,.25]m; source/body position components within±10m; angles stored in[-stored_pi,+stored_pi]. Body IDs match[A-Za-z][A-Za-z0-9_-]{0,31}; exterior ID=`exterior`, interior=`body:<id>`, even for equal indices. No bodies is supported by the exact delegated W2 path.

Body forms: centered rectangular_block has |x|<=width/2, |y|<=height/2, |z|<=depth/2, facesx_min/x_max/y_min/y_max/z_min/z_max. right_triangular_prism is x>=0,z>=0,x/leg_x+z/leg_z<=1, |y|<=height/2; origin is midpoint of right-angle extrusion edge, facesx_min/z_min/hypotenuse/y_min/y_max; both Y ends are triangles. All faces are real finite boundaries.

SI/right-handed+Y up, column vectors active B=storedRzRyRx (X thenY thenZ), uniformdisplay10. Body is affineimage of the exact canonical polytope under exact stored B. Shared vertices/halfspaces, inverse-transpose covectors and reciprocal-Gram UV are authoritative; display triangles/shaders/picking/mounts never solve optics. Purely outward normals and declared local bases are returned for inspection. Internal angles are radians; UI converts returned values to degrees and only edited degree inputs back to radians. TIR outgoing_angle_rad is the ACTUAL reflected angle, not a transmitted angle. No critical-angle output or transmission direction is invented when absent.

Old mirror/ideal_splitter_50_50/beam_stop/receiver schemas stay exactW2 and may coexist only wholly exterior, certified by a body separating halfspace using conservative finite-face sphere. Contact/overlap/embedded/unresolved separation is rejected, not moved. All body vertices and old complete apertures lie strictly inside source-centred1m sphere. Sufficient separation may reject physically separated corner configurations.

For incoming propagation d and incident-facing covector a (outward m for entry, -m for exit): A=a.a, S=d.d, rho=ni/nt, q=d-a*(d.a)/A, K=S-rho²(q.q). lower(K)>0 permits rho*q-sqrt(K/A)*a; upper(K)<0 uses d-2*a*(d.a)/A. K crossing0, grazing/edge/order/medium disagreement fails. No clamp, origin nudge, face inflation, autoaim, interval reset or normalization repair. Enter/exit refraction changes medium only with geometric proof; TIR keeps the incident medium including high-index exterior cases. Equal indices keep direction/enclosure exactly while crossing IDs remain distinct.

Input norm32epsilon, output128epsilon; epsilon=2^-52. Body-present point/direction component interval widths<=1e-8m/1e-8 respectively, else unsupported_numerical_input. No-body delegation applies exact old W2 admission, diagnostics and IDs, not this new width gate. Known preceding departure root alone is suppressed with a side certificate; later returns are permitted. Small residuals do not prove bounds. Exact storedB/input references and ideal-angle references are separate.

Body-present limits:1body,6bodyfaces,16totalfaces (block10old/prism11old),32inherited interactions,31ever-createdbranches (root+parents),128combinedrecords,64events,128segments,1m sphere,10m true cumulative length. No-body retains63/256/128/256 and exact W2 behavior. Exact capacities allowed, pair allocations atomic, FIFO/T-beforeR. Interaction costs segment+event, endpoint segmentonly, knownpoint terminal neither. Receiver/stop at32 wins; continuing event32 is processed then truncated with outgoingmedium. Global caps account every unresolved leaf with its weight/medium. Incomplete is distinct from unsupported/error. Only terminal leaves enter ledger, signed residual retained without rescaling. Full order is the frozen queue_precedence contract.

Weight contract `ideal_route_weights_no_fresnel_v1`; visible exact statement: **Ideal route weights; Fresnel losses are not modeled.** Refraction/TIR preserve bookkeepingweight, only approved ideal splitter divides it. No physical100% transmission/coating/calibratedpower, polarization, dispersion, wave coupling or source bundle. OPL, phase/groupdelay and persistence are deferred.

Request32KiB/reply512KiB UTF8 caps; overflow is atomicerror, never clipped/partialsuccess. Global retained16MiB/transient32MiB unchanged; oldW2local2/4MiB unchanged, W3newlocal4/8MiB within global aggregateadmission. Count real metadata/DOM/buffers/geometry/overlap; no autoeviction. ExplicitRelease removes results only; display recovery reuses ownednumerics without tracing. These budgets are not total V8/GPU/RSS guarantees.

## Closed key sets

- `scene_closed_keys`: `schema_version`, `model_contract`, `source`, `exterior_medium`, `bodies`, `elements`.
- `validation_reply_closed_keys`: `protocol_version`, `message_type`, `model_contract`, `request_id`, `scene_sha256`, `scene`, `weight_model`, `media`, `body_faces`, `legacy_surface_frames`, `limits`.
- `trace_reply_closed_keys`: `protocol_version`, `message_type`, `model_contract`, `request_id`, `scene_sha256`, `scene`, `weight_model`, `media`, `body_faces`, `legacy_surface_frames`, `limits`, `status`, `branches`, `segments`, `events`, `terminals`, `ledger`, `diagnostics`.
- `branch_closed_keys`: `id`, `parent_id`, `parent_event_id`, `origin_m`, `initial_direction`, `initial_medium_id`, `initial_refractive_index`, `relative_weight`, `start_cumulative_m`, `start_interaction_count`, `outcome`.
- `segment_closed_keys`: `id`, `branch_id`, `start_m`, `end_m`, `direction`, `medium_id`, `refractive_index`, `relative_weight`, `length_m`, `cumulative_end_m`, `event_id`.
- `event_common_closed_keys`: `id`, `segment_id`, `branch_id`, `target`, `classification`, `position_m`, `local_uv_m`, `incident_direction`, `incident_medium_id`, `incident_refractive_index`, `incoming_weight`, `outgoing`, `segment_length_m`, `cumulative_length_m`, `numerical_bounds`.
- `dielectric_event_extra_closed_keys`: `outward_normal`, `local_basis`, `incident_angle_rad`, `outgoing_angle_rad`.
- `outgoing_closed_keys`: `branch_id`, `direction`, `medium_id`, `refractive_index`, `relative_weight`.
- `body_face_closed_keys`: `body_id`, `face_id`, `vertices_m`, `plane_covector`, `outward_normal`, `local_origin_m`, `local_basis`, `numerical_bounds`.
- `event_common_bounds_closed_keys`: `t_parameter_interval_m`, `position_intervals_m`, `local_uv_intervals_m`, `incident_direction_intervals`, `outgoing_direction_intervals`, `cumulative_length_interval_m`, `plane_residual_m`.
- `dielectric_event_extra_bounds_closed_keys`: `snell_discriminant_interval`, `incident_side_interval`, `outgoing_side_interval`, `body_halfspace_intervals_m`.
- `terminal_closed_keys`: `branch_id`, `category`, `element_id`, `event_id`, `position_m`, `medium_id`, `refractive_index`, `cumulative_length_m`, `relative_weight`, `reason`.
- `ledger_closed_keys`: `input_weight`, `detected_weight`, `absorbed_weight`, `escaped_weight`, `truncated_weight`, `signed_residual`.
- `diagnostic_closed_keys`: `predicate_policy`, `max_direction_norm_residual`, `max_frame_residual`, `max_plane_residual_m`, `max_point_width_m`, `max_direction_width`.
- `no_body_diagnostics_closed_keys`: `predicate_policy`, `max_direction_norm_residual`, `max_frame_orthogonality_residual`, `max_plane_residual_m`, `max_point_error_bound_m`.
- `error_reply_closed_keys`: `protocol_version`, `message_type`, `request_id`, `model_contract`, `error`.
- `error_detail_closed_keys`: `code`, `message`.

Trace message_type=`refractive_trace_result`; validation=`refractive_scene_validation`; error=`refractive_routing_error`. Allowed error codes: `invalid_scene`, `numerical_ambiguity`, `medium_state_ambiguity`, `unsupported_numerical_input`, `numerical_failure`, `busy`, `request_body_too_large`, `encoding_failed`, `response_too_large`, `trace_failed`, `disconnected`, `cancelled_before_start`, `submission_failed`.

Plane/halfspace residuals labelled_m are signed physical distances (covector dot displacement /covectornorm), not raw scaledplane products. Body diagnostic max_frame_residual/normresidual/directionwidth are dimensionless; max_plane_residual_m/max_point_width_m metres. Body predicate=binary64_closed_body_outward_v1. No-body copies exactold5diagnostic keys/predicate/zero-baseds0000/h0000 IDs. Its losslessprojection restores W2modelconstant, field names, limits and all10corekeys exactly; no wirebyte identity is claimed for the distinct W3wrapper.
