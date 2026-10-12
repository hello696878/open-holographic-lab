# V2e — Portable virtual-experiment settings

Opening contract recorded 2026-10-12 before executable implementation. The
contract details below now describe the implemented boundary. Measured
acceptance, genuine browser evidence and publication are recorded separately
in `tests_and_evidence.md` and fresh ignored evidence; this document does not
predict their success.
Approved baseline: `9791db07ad182902fb027ab4e3caf9d2faccc966`.

## Document v1

Exactly six keys: `document_format="ohlab_virtual_experiment"`,
`document_version=1` (integer, not bool), `mode`, `model_contract`, complete
`experiment`, and `metadata={title,notes}`. Unknown/missing keys reject.

| mode | model_contract | existing scientific definition |
|---|---|---|
| sequential | v0_aligned_scalar_forward_v1 | V0 schema 1, including matching inner contract |
| two_path | v2b_unfolded_scalar_two_path_v1 | unchanged V2b experiment; no added inner contract/version |
| polarization | v2d_ideal_jones_same_plane_v1 | V2d schema 1, including matching inner contract |

The two-path wrapper identifier describes the existing model only. Document
compatibility is distinct from numerical-model compatibility. No migration,
defaults, field dropping, IDs/order changes or coefficient normalization.

Every object below requires exactly the listed keys. Records selected by a
`kind` discriminator require that exact discriminator and its complete field
set. Lengths and pitches are SI metres; angles are radians. Real fields accept
finite binary64 values under the unchanged mode validator, excluding booleans,
strings and complex JSON values. Integer fields require integers excluding bool.

| Shared record | Complete keys and domains |
|---|---|
| grid | `ny,nx,dy,dx`; positive integer counts, positive pitches |
| uniform source | `kind="uniform",amplitude,phase_rad`; nonnegative amplitude, finite phase |
| sequential/two-path Gaussian source | `kind="gaussian",amplitude,phase_rad,waist_radius_m,waist_z_m,center_x_m,center_y_m`; positive waist radius, nonnegative amplitude, finite signed phase/waist position/centres |
| polarization Gaussian source | `kind="gaussian",amplitude,phase_rad,waist_radius_m,center_x_m,center_y_m`; same domains, fixed internal waist position zero; `waist_z_m` is not an accepted field |

Sequential `experiment` requires
`schema_version,model_contract,wavelength_m,grid,source,components,observation`.
Its integer schema version is 1 and inner contract matches the wrapper.
`wavelength_m` is positive. Grid axes are 1..512; `components` is an ordered
list of 0..8 records:

| kind | Complete component keys |
|---|---|
| circular_aperture | `id,kind,z_m,radius_m` |
| rectangular_aperture | `id,kind,z_m,width_m,height_m` |
| thin_lens | `id,kind,z_m,focal_length_m` |

Component `z_m` is nonnegative and nondecreasing in stored order; equal
positions are legal and retain their order. Aperture sizes are positive;
focal length is signed and nonzero. `observation` requires `id,z_m`, with a
nonnegative position at or beyond the last component. Component/observation
IDs are unique across that train, match `[A-Za-z][A-Za-z0-9_-]{0,63}`, and
exclude reserved `source`. Existing usable-derived-geometry checks also apply.

Two-path `experiment` requires `wavelength_m,grid,source,two_arm_spec`.
Wavelength is positive and grid axes are 1..512. `two_arm_spec` requires
`arm_0_distance_m,arm_1_distance_m,relative_phase_rad`: nonnegative finite arm
distances and a finite signed, unwrapped relative phase. There is no inner
`schema_version` or `model_contract`. Port identities, ideal splitter/recombiner,
zero second input and unfolded common coordinates are fixed model assumptions,
not editable document fields. No topology, component IDs or sweep recipe is
invented by export.

Polarization `experiment` requires
`schema_version,model_contract,wavelength_m,grid,source,coefficients,elements,readout`.
Its integer schema version is 1 and inner contract matches the wrapper.
Wavelength is positive; axes are 1..128. `coefficients` requires `x,y`, each
requiring finite real `re,im`; arbitrary coefficients are neither normalized nor
phase-reset. `elements` is an ordered list of 0..8 records:

| kind | Complete element keys |
|---|---|
| linear_polarizer | `id,kind,axis_angle_rad` |
| linear_retarder | `id,kind,axis_angle_rad,retardance_rad` |

Angles and retardances are finite signed radians without wrapping or snapping.
Element IDs are unique, match `[A-Za-z][A-Za-z0-9_-]{0,31}`, and exclude reserved
`input`. `readout` requires integer `row,column`, respectively in
`0..ny-1,0..nx-1`. QWP/HWP buttons supply numeric retardances; there are no new
named element kinds. Actions remain ideal and ordered at one common plane,
with no longitudinal coordinate or added propagation.

Only the current valid draft is exported, frozen with title/notes at the user's
action. Results, sweeps, requests, tokens, badges, camera/animation and renderer
state are excluded. There is no server file store or autosave.

## HTTP and identity contract

Only new route: `POST /api/v2e/documents/validate`. Request Content-Type must
be exactly `application/json` or `application/json; charset=utf-8` after the
existing case/outer-whitespace handling. Original bounded upload bytes enter
authoritative parsing before any frontend parse/stringify.

Success is HTTP 200, `Content-Type: application/json`, canonical UTF-8 JSON
body (no BOM), and `X-OHLab-Experiment-SHA256: <64 lowercase hex digits>`.
Existing security headers, including `Cache-Control: no-store`, apply.
Canonical output uses Python `json.dumps(sort_keys=True, indent=2,
ensure_ascii=False, allow_nan=False)`, LF and one final newline. List order
is preserved. Input and output independently must be at most 32768 bytes.

The header is exactly the existing mode-specific **scientific experiment**
digest after that mode's validation: sequential protocol.experiment_digest of
the validated SequentialExperiment, two_path_protocol.experiment_digest of
the validated experiment.to_dict(), or polarization_protocol.experiment_digest
of validated PolarizationExperiment.to_dict(). Those existing contracts hash
sorted compact Python JSON of the complete SI definition (UTF-8, ensure_ascii,
no nonfinite values). The wrapper, metadata and document whitespace are NOT
covered. Equality with ordinary mode validation must be directly demonstrated
for each mode before this value is installed as a controller validation hash.

SHA256 of complete canonical file bytes is a separate evidence-only document
identity. A browser operation generation is temporary cancellation/attachment
identity. Neither is the scientific header. No hash means authorship, signature,
successful simulation, code provenance or qualified replay. Hashes/tokens are
not persistent document keys; later ordinary simulation uses a fresh request ID.

Errors have the existing generic shape:
`{protocol_version:1,request_id:null,error:{code,message}}`; message is bounded
to 300 characters and no partial document succeeds.

| HTTP | code/policy |
|---|---|
| 400 | existing invalid_headers, invalid_host, invalid_framing, invalid_length; invalid_json for malformed/duplicate/UTF-8/BOM/nonstandard/nonfinite/overflow/underflow/unusable numeric or recursion input |
| 403 | existing invalid_origin |
| 404/405 | existing http_error for unavailable path/method |
| 408 | existing body_timeout (five-second body deadline) |
| 413 | existing body_too_large before decoding, including streamed input |
| 415 | existing invalid_content_type |
| 422 | unsupported_document_version, unsupported_document_mode, unsupported_model_contract, invalid_document, invalid_metadata, invalid_experiment, document_structure_limit, canonical_document_too_large |
| 499 | disconnected before complete document receipt |
| 500 | bounded document_failed for unexpected validation/encoding failure, without internal details |

Document validation never returns busy merely because science is active. It
never acquires/submits/releases the worker gate, samples sources, constructs
incident Jones fields, applies elements, computes, sweeps or writes uploads.
Existing routes retain schemas, parser policy, caps, errors and worker lifetime.

## Raw limits and text

Enforce byte cap before UTF-8 decoding. Reject BOM, duplicate decoded keys,
nonstandard/nonfinite/overflow numbers and nonzero decimal underflow to zero.
Structural checks occur before mode construction: root object at container
depth 0, maximum container depth 12, maximum 2048 value nodes (each root,
container and primitive once; keys do not add value nodes), maximum decoded
string token 8192 Unicode scalar values, including keys. Iterative checks follow
strict parsing; parser recursion failures are bounded errors, not a claim of
pre-parse depth enforcement.

The unchanged bench strict parser runs first. A second bounded stdlib decode
adds document-only numeric hooks; it does not provide a different JSON grammar.
Its recursion exception is also converted to a raw JSON error. Nonzero decimal
coefficients rounding to binary64 zero (for example `1e-999`) reject; explicit
zero tokens and representable subnormals such as `5e-324` may pass if the field's
domain permits them. Integer tokens too large for finite binary64 reject as raw
input. Wider finite integer tokens in real fields use the existing conversion:
`9007199254740993` rounds once to `9007199254740992.0`. Count/version/index
fields retain integer type and their existing bounds. Original decimal spelling
and arbitrary-precision values are not preserved. No new safe-integer rule is
imposed on real fields and no legacy endpoint/parser is globally tightened.

Title allows 0..120 and notes 0..2000 Unicode scalar values, both strings
required. Reject lone surrogates and U+0000..001F/U+007F..009F controls, except
notes permit U+0009 TAB and U+000A LF. CR rejects. Preserve allowed text exactly,
including Chinese, supplementary-plane characters and combining sequences;
no trimming or Unicode normalization. Output UTF-8 size is independently capped
without truncation or raising the cap. Render with textContent, never HTML.

## Browser preparation and editor transition

One import operation makes two sequential bounded document requests: raw strict
validation; then fresh closed owned data through existing mode freezer and
ordinary JSON.stringify followed by final validation. Compare correspondence
across both stages: all finite nonzero binary64 leaves exactly, integer fields,
mode/model/version, IDs/order/readout/text unchanged. Only existing browser
zero representation may differ. No new zero walker or general serializer.
Only the second reply's bytes/data/hash can reach preview/apply. Final prepared
canonical bytes must survive import and unchanged reexport byte-identically.

Existing zero behavior is explicit: the two-path browser freezer maps phase
zero to +0, polarization numeric preparation maps zero to +0, and ordinary
`JSON.stringify` serializes any remaining -0 as 0. Sequential has no added
zero walker. The first Python response may therefore contain -0 in compatible
fields and need not equal the final response's bytes or digest. Negative-zero
bit preservation is not supported. The first digest is never installed;
the final digest is checked directly against ordinary validation for each
mode. A current-draft export needs one validation call because the frozen
draft is already serialized through the existing browser path.

Preview changes no editor. Explicit replacement acknowledgment is required;
apply synchronously rechecks generation, prepared identity, destination state
and shared busy gate, prepares all replacement state before publishing, advances
attachment eligibility and detaches stale presentation/retry eligibility. Prior
results retain their original identities. Successful apply says
`設定已還原，尚未模擬`; ordinary simulation remains explicit.

The mode controllers prepare a complete frozen replacement and synchronous
commit before publishing it. They advance revision and attachment epoch, cancel
old validation eligibility, clear current results/sweeps and completed-result
retry eligibility where present, and keep prior completed data under its old
identity. Presentation teardown/rendering happens after the coherent settings
commit and reports a separate presentation failure. Import never obtains a
successful optical status merely from validation or from a retained old result.

Authoritative SI bindings retain unchanged loaded values rather than reparsing
shortened display text or converting unchanged display units again. Binding
identity includes field and editor generation. Metadata is outside science.
One active document operation/preview/download owns readers, buffers, listeners
and Blob URL within existing budgets; URLs survive useful download lifetime.
Download status is prepared/requested, not proof of a saved Windows path.

There is at most one active reader/fetch operation, one queued latest intent,
one preview and one prepared download. Supersession aborts old asynchronous
work and rejects its generation before publication. Readers clear handlers and
abort listeners after completion. A prepared URL survives a download click;
successful replacement, explicit dismissal or disposal revokes it. Failed
replacement does not revoke a still-useful earlier download. Owned input/reply
buffers, Blob bytes, logical UTF-16 string bytes, reader reservations and
active-operation reservations participate in the existing 16 MiB persistent /
32 MiB transient app-owned budgets. These are conservative ownership bounds,
not whole browser heap/process/GPU measurements.

## Acceptance status

Implementation contract described above; measured acceptance and publication
outcomes belong in `tests_and_evidence.md` and fresh ignored evidence. No claims
of optical accuracy, cross-platform/version bitwise reproduction, result
persistence or later optics follow from document validation.
The approved 35-path inventory, isolated fault controls, real fresh-session
three-mode portability/recomputation and clean-postcommit checks are required.
