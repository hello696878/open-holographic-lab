# V2d implementation summary and exact application contract

Contract completed 2026-10-12 before V2d executable implementation. Accepted
baseline `ff669ab683bcf7b07b4a8ff9073c8557dc6ad1b8`. The approved scope is 35 paths:
nine modifications and twenty-six creations. Validation/build/owned loopback
and browser work, genuine screenshots, six handoffs, one commit and a normal
push are approved; package installation/version changes are not.

This record fixed the wire contract before executable implementation. The
implementation and precommit acceptance results below were added after their
execution; publication remains a separate clean-postcommit gate.
The latest approval supersedes the planning document's 34-path count and
commit subject, and expressly allows the narrow adapter-specific architecture
guard amendment. No scientific or product scope is broadened.

## Public scientific workflow

Sequential remains default; polarization is a third independent bench mode.
All elements act in submitted order at one common reference plane. Mesh spacing,
housing and thickness are illustrative. No physical z control, propagation,
extra optical phase, aperture/material/reflected-frame model or persistence.

The source boundary uses public SequentialExperiment.from_dict, empty
components and observation at zero. Gaussian waist_z_m is fixed at zero only
inside that adapter; unsupported app source fields are rejected. It is a V2d
input restriction, not a change to the broader source library. Public sampler
source/grid restrictions remain in effect; they are not V2c Jones restrictions.
Validation constructs immutable records but samples zero fields and applies
zero elements. Each compute operation samples once and creates incident Jones
once through from_scalar. Every element uses the corresponding public V2c
function. Public intensity, sampled_norm and transmission_ratio remain
authoritative; no optical equations are reproduced in app/frontend code.

## Exact submitted fields

Every object rejects unknown fields. Numeric booleans/nonfinite values fail.
New browser request numeric zeros canonicalize to +0; nonzero values are not
wrapped, snapped, rounded or reconstructed from shortened labels. Standard
JSON.stringify does not preserve negative zero. The V2d parser likewise returns
validated request numeric zeros as +0; returned numerical samples are captured
from the public fields. Radians are authoritative.
Complex values use exactly `{re,im}`; coefficients remain unnormalized.

Single/validation envelope fields, exactly:
`protocol_version`, `message_type`, `request_id`, `experiment`,
`experiment_sha256`. protocol_version is 1; message_type is
`polarization_submission`; request_id is canonical UUIDv4. Validation may carry
null experiment_sha256; compute requires the matching validation SHA. An
incorrect nonnull SHA is rejected even by validation.

Experiment fields, exactly:
`schema_version`, `model_contract`, `wavelength_m`, `grid`, `source`,
`coefficients`, `elements`, `readout`. schema_version=1;
model_contract=`v2d_ideal_jones_same_plane_v1`.

wavelength_m is positive metres. Source amplitude is nonnegative in field
units; source phase and element angles/retardance are finite radians with no
modulo restriction. Gaussian waist_radius_m is a positive 1/e amplitude radius
in metres; center_x_m/center_y_m are finite metres. Public source/grid derived
binary64 geometry checks also apply and can reject finite but unusable inputs.

- grid: exactly `ny,nx,dy,dx`; dimensions integer 1..128; pitches positive metres.
- uniform source: exactly `kind,amplitude,phase_rad`, kind=`uniform`.
- Gaussian source: exactly `kind,amplitude,phase_rad,waist_radius_m,center_x_m,center_y_m`,
  kind=`gaussian`. No submitted waist_z_m or other z field.
- coefficients: exactly `x,y`, each exactly `re,im` finite binary64 components.
- polarizer: exactly `id,kind,axis_angle_rad`, kind=`linear_polarizer`.
- retarder: exactly `id,kind,axis_angle_rad,retardance_rad`, kind=`linear_retarder`.
- elements: 0..8 ordered records; IDs match `[A-Za-z][A-Za-z0-9_-]{0,31}`,
  are unique and exclude `input`. Empty is identity. QWP/HWP are explicit
  retardance assignments pi/2 and pi, not extra hidden element kinds.
- readout: exactly `row,column`, integer indices within the submitted grid.

Validation reply fields: `protocol_version,message_type,request_id,
experiment_sha256,experiment`; message_type=`polarization_validation`.
The server SHA uses canonical complete validated JSON, including element order
and readout. Clients also compare full structural specification equality;
they do not assume Python/JavaScript float JSON text is identical.

Sweep envelope fields: all single envelope fields plus `selected_element_id,
angles_rad`; message_type=`polarization_sweep_submission`. The selected ID
must name an existing linear polarizer. Exactly thirteen actual radians are
accepted, one-time converted from [-90,-75,-60,-45,-30,-15,0,15,30,45,60,75,90]
degrees. Both endpoints are independently computed. All nonswept settings
remain frozen. Every point starts from the original incident field and applies
the entire ordered train, giving 13*L element calls (104 for eight).

## Exact result fields and binary framing

Result header fields: `protocol_version,message_type,request_id,
experiment_sha256,experiment,ordered_stage_ids,stages,readout,arrays,intensity_max`.
message_type=`polarization_result`. ordered_stage_ids is exactly
`["input",...submitted element IDs]`. intensity_max contains the two actual
public intensity maxima in incident/final order.

Stage fields: `stage_id,kind,norm,previous_norm,delta_norm,
adjacent_transmission_ratio,incident_transmission_ratio,sample`.
kind is `input`, `linear_polarizer` or `linear_retarder` as applicable. norm is
actual sampled_norm. previous_norm/delta_norm/adjacent_transmission_ratio are
null for input; later delta_norm retains signed output-minus-previous norm.
incident_transmission_ratio always uses the constructed incident Jones field
through the public ratio, including input-to-itself 1 or null. Zero denominators
yield null without epsilon. Ratios alone certify neither causality nor hardware
gain/efficiency. sample contains exactly `x,y`, each `{re,im}` from that actual
stage's returned field. No intermediate full field/image stack is retained.

Returned readout fields: `row,column,x_m,y_m`, with actual public axis values.
It remains part of submitted identity. Another intensity pixel can be inspected
without relabeling this complex sample. A new complex sample needs an explicit
submitted operation; no hidden complex cache or automatic solve.

Arrays are ordered incident_intensity, final_intensity, x_m, y_m. Descriptor
fields: `name,role,stage_id,dtype,order,shape,offset_bytes,nbytes,units`.
Roles are intensity,intensity,coordinate,coordinate; stage IDs are input,
last-element-ID-or-input,null,null. dtype=`float64-le`; order=`C`;
shapes are [ny,nx],[ny,nx],[nx],[ny]; offsets are contiguous from payload zero.
Intensity units are amplitude_unit^2 and coordinate units m. Norm/delta units
are amplitude_unit^2*m^2, not calibrated watts; ratios are dimensionless.

Framing: magic `OHLABPL\0` (eight bytes), little-endian `<8sII>` preamble with
actual UTF-8 header length and reserved zero; zero padding to eight-byte
alignment; original float64 ordered payload. Validate exact role/order/shape,
offsets/lengths/endian/padding/finite values, stage/readout/full specification
and known server SHA before publication. Cross-format frames fail closed.
OHLABV1/OHLAB2P bytes, routes, caps and old behavior remain protected.

Caps: request 32768, header 16384, payload 264192, complete frame 280592 bytes;
maximum axis 128, eight elements, one selected index and nine stage-sample
records. Payload is 8*(2*nx*ny+nx+ny); maximum frame is
16+16384+264192. Sweep cap is thirteen points and 65536 JSON bytes.
Preserve the existing 16 MiB persistent/32 MiB transient app-owned budgets;
count actual retained, incoming, decoded, preparation and failed-overlap
buffers across all modes, deduplicating aliases. No whole-JS-heap/GPU claim.

## Exact sweep result and errors

Sweep outer fields: `protocol_version,message_type,status,request_id,
experiment_sha256,sweep_sha256,experiment,selected_element_id,angles_rad,
ordered_stage_ids,requested_count,rows,completed_count,failed_index,error`.
message_type=`polarization_sweep_result`; requested_count=13;
sweep_sha256 hashes canonical `{experiment,selected_element_id,angles_rad}`.

Row fields: `index,axis_angle_rad,stages,final_norm,
incident_transmission_ratio,total_delta`. stages use exactly the above scalar
stage fields except sample. total_delta is final-minus-original incident norm.
Rows contain only genuine scalars, no images/complex stack or analytic curve.

Success is HTTP200/status=`complete`, thirteen rows, completed_count=13,
failed_index/error null. Failure is status=`failed`, HTTP422/code
`numerical_failure` for public domain/arithmetic failure or HTTP500/code
`sweep_failed` for unexpected failure. failed_index=completed_count, with only
the contiguous genuine prefix. First/interior/last-point failures are separate
acceptance cases. error is exactly `{code,message}`, code at most64 ASCII
characters and message at most 300 characters, without internal detail leakage.
No automatic retry, fabricated remainder or connected missing segment.

Other new-route errors have exactly `protocol_version,message_type,request_id,
error`, message_type=`polarization_error`; request_id may be null if invalid.
HTTP/code pairs:400 invalid_framing/invalid_length/invalid_json;
408 body_timeout;413 body_too_large;415 invalid_content_type;
422 invalid_experiment/numerical_failure;409 busy;499 disconnected;
503 cancelled_before_start;500 submission_failed/simulation_failed.
Existing Host/Origin/method/static boundary responses remain unchanged.

## Display, animation and worker distinctions

Trajectories evaluate only Re([Ux,Uy]*exp(-i*tau)) from returned samples;
equal x/y component scales, +x right/+y down, view along +z, one shared tau.
Preserve common phase and compare fixed-tau markers independently. All four
returned real/imaginary parts equal zero means no defined polarization state;
nonzero tiny components with zero squared intensity remain nonzero and may
have a disclosed display precision/scale limitation. No epsilon/normalization.

Incident/final intensities share limits; magnification affects display only.
Camera/selection/stage/color/tau changes issue zero scientific requests.
Optical edits detach; immutable earlier identities remain visible. Prepare both
intensity views, trajectories, scalars and identity atomically; later-resource
failure cleans all new resources, preserves original view and retains numerical
completion separately. Context loss does not trigger diagnostic replay.

Use one owned bounded trajectory callback in the existing render loop; pause,
reset, replacement and mode switches remove obsolete updates without stopping
the shared renderer. No listener/timer/resource accumulation.

All five compute kinds use the one actual-worker-lifetime gate through result
encoding. HTTP abort/disconnect does not release running work early; concurrent
compute gets409, health/validation stay responsive. Keep loopback security and
task-owned port policy. Controlled child tooling has an explicit main guard and
no production fault/release endpoint or automatic production fallback.

## Acceptance and publication status

Implementation and required precommit acceptance are complete within this
bounded model. Fresh Python baseline was 2356 passed/1 skipped; the final suite
was 2523 passed/1 skipped. Installed frontend baseline was 129 unit tests;
final 186 unit tests, typecheck and production build passed. The unchanged
Windows symlink-privilege skip remains; no privileges/tests were changed to
remove it. Exact unedited output and provenance are in tests_and_evidence.md.

Current production API checks passed 10 sequential cases, 18 two-path cases plus
three sweeps, and 28 polarization cases plus three sweeps. The full three-mode
Chrome rerun passed 28 scenarios, with five controlled-service tests deliberately
skipped there. Separately invoked child services passed all six numerical/
unexpected first/interior/last polarization failures, the legacy partial sweep,
and disconnect acceptance for each of the five actual worker holders. Production
and controlled evidence remain distinct; supplemental injected browser transport/
allocation fixtures do not replace genuine public-output checks.

All 26 isolated fault variants across 21 categories detected their intended
assertions; originals/restored assertions passed, copied sources were restored
exactly and production hashes were unchanged. A first Chrome sweep-click
failure was preserved and fixed by making the decorative line ignore pointer
events; assertions were unchanged. A standalone encoder boolean-zero mismatch
was demonstrated, then guarded with four new malformed-angle regressions.
Neither correction changed scientific formulas or tolerances.

Actual observed three-mode ownership and conservative operation-phase bounds
remain below 16 MiB persistent/32 MiB transient. Use the current ownedMemory/
polarization.budget inventory; legacy twoPath debug budget fields are narrower
compatibility estimates. The bounds exclude whole heap, browser/GPU/driver
memory, and are not measured process-memory peaks. Three genuine production UI
captures are inspected and prepared under figures/. Historical handoffs,
scientific files/tests, package metadata and lockfile remain protected.

Approved commit subject: `feat(v2d): add interactive Jones polarization experiments`.
Clean-postcommit rebuilt owned assets, imported source ownership and genuine
all-three-mode browser smoke including a thirteen-point polarization sweep must
pass before normal origin/main push and three-way SHA verification. No new
qualified replay gate. Stop after V2d; tutoring/learning records stay separate.
