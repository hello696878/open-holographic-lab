# V2e code map

This map describes portable settings documents only. Measured acceptance and
publication status are in [tests_and_evidence.md](tests_and_evidence.md).
The complete wrapper, nested schemas, numeric domains, limits and HTTP codes
are in [implementation_summary.md](implementation_summary.md).

## Backend boundary

| Path | Responsibility |
|---|---|
| `apps/virtual_bench/experiment_documents.py` | Six-key schema/model mapping; strict original-byte entry point; document-only numeric hooks; iterative structure/text checks; existing mode validation; owned canonical UTF-8 bytes and transient scientific digest |
| `apps/virtual_bench/adapter.py` | Narrow public `validate_experiment(spec)` extraction of the existing cheap caps and `SequentialExperiment.from_dict`; unchanged submission envelope delegates to it |
| `apps/virtual_bench/two_path_adapter.py` | Equivalent public `validate_experiment(spec)` extraction for the unchanged source plane and `TwoArmSpec`; unchanged submission envelope delegates to it |
| `apps/virtual_bench/server.py` | Optional `_read_json(..., parser=...)` callback with unchanged default; only `POST /api/v2e/documents/validate` selects the document parser and returns canonical bytes plus hash header |

`strict_document_loads(bytes)` caps original bytes before UTF-8 decoding and
first calls unchanged `strict_json_loads`. Its second stdlib numeric-hook
decode rejects nonzero decimal underflow and unusable integer magnitude;
recursion failures become bounded raw JSON errors. `validate_document(payload)`
runs iterative value/container/key/text checks before constructing a mode's
validated specification. `document_from_json(bytes)` combines these steps.

`ValidatedDocument` owns immutable `canonical_bytes` and the transient
`experiment_sha256`; `to_dict()` returns fresh containers. Canonical encoding
sorts object keys while retaining list order and independently checks the
output byte cap. The response contains no JSON envelope or saved hash field.

Reused without modification: `polarization_adapter.PolarizationExperiment`,
the three mode protocol `experiment_digest` helpers, public specification
constructors and the existing LocalBoundary/body framing. Scientific code,
M5 bundles, wire protocols, source sampling, optical actions, workers and
their actual-lifetime gate remain outside the new document module/handler.
Existing architecture guards are unchanged.

## Browser data and operations

| Path | Responsibility |
|---|---|
| `frontend/bench/src/experiment_documents.ts` | Closed owned document data, scalar-counted metadata, strict bounded response handling, mode freezer/browser serialization, exact correspondence checks and fetch API |
| `frontend/bench/src/experiment_document_state.ts` | Frozen current-draft export, two-stage raw import, operation generations, cancellation, preview/acknowledgment, synchronous application, ownership admission and disposal |
| `frontend/bench/src/experiment_document_files.ts` | One bounded FileReader, listener cleanup, one Blob URL/download, replacement/dismissal/disposal; filenames never become server paths |
| `frontend/bench/src/numeric_fields.ts` | `NumericFieldBinding`: unchanged painted text preserves the authoritative SI leaf only when field, generation and exact value also match |
| `frontend/bench/src/main.ts` | Settings panel, per-mode metadata and valid-draft selection, field bindings, all-mode context token, destination preparation, later presentation teardown and resource accounting |
| `frontend/bench/src/state.ts` | Sequential `prepareValidatedSettings`/`restoreValidatedSettings`; atomic replacement, revision/attachment advancement and current-result detachment |
| `frontend/bench/src/two_path_state.ts` | Equivalent two-path replacement, including sweep/selected-point and completed-result retry detachment |
| `frontend/bench/src/polarization_state.ts` | Equivalent polarization replacement, including readout/train state, selected stage and completed-result retry detachment |
| `frontend/bench/src/styles.css` | Settings panel and acknowledgment/download presentation |

Import sends untouched file bytes first. Only after authoritative validation
does the browser parse owned data, check correspondence with the original
supported definition, apply the existing mode freezer and ordinary JSON
serialization, and validate a second time. All nonzero values, IDs, ordering,
readout and text must correspond; only the documented zero representation may
differ. Only the second response reaches preview/apply. Export freezes the
current valid draft and metadata at one action and needs one document request.

`ExperimentDocumentController` serializes operations through one active intent
and one latest queued intent. Both import stages share one generation and
context. Context includes active mode, all editor revisions/attachment epochs
and metadata generation. A superseded reply cannot publish a preview or
download. Apply rechecks preview identity, acknowledgment, context and shared
busy state after all throwing preparation and before committing. State commits
precede presentation; no import action submits science.

Metadata lives outside the scientific controllers. Camera/selection/display
state is not a document field. The files owner retains download URLs through
their useful lifetime and clears reader handlers/listeners on completion.
Document buffers, Blob bytes, logical strings and reservations are included in
the existing app-owned persistent/transient budgets alongside numerical and
display retention.

## Verification and evidence entry points

| Path | Purpose |
|---|---|
| `tests/test_virtual_bench_experiment_documents.py` | Independent complete fixtures; canonical bytes/digests, exact numeric/order/text preservation, closed schemas, limits and zero optical work |
| `tests/test_virtual_bench_document_server.py` | Raw HTTP precedence/error codes, exact body/header, framing/security, worker/disconnect gate independence and old-route policy preservation |
| `tests/test_virtual_bench_document_architecture.py` | Explicit import/call boundary, no optical formulas/private/dynamic/file/gate bypass, passive import and guard detector controls |
| `frontend/bench/tests/experiment_documents.test.ts` | Owned contracts, response bounds, Unicode, correspondence, zero policy and serialization |
| `frontend/bench/tests/experiment_document_state.test.ts` | Frozen exports, two-stage consistency, stale replies, transaction/busy checks, metadata and budgets |
| `frontend/bench/tests/experiment_document_files.test.ts` | Reader cancellation/listener cleanup and Blob URL lifetimes |
| `frontend/bench/tests/numeric_fields.test.ts` | Field/generation/value-bound unchanged-text preservation |
| `frontend/bench/tests/experiment_documents.browser.spec.ts` | Actual downloads, closed/fresh isolated contexts, renamed uploads, preview/apply, explicit recomputation, race/resource and numeric editor cases |
| `scripts/validate_v2e_documents.py` | Independent direct-public references, document API/canonical/hash checks, full-array/scalar/sample comparison and browser evidence review |
| `scripts/v2e_negative_controls.py` | Owned isolated fault copies, intended assertion detection, original/restored passes and production hash comparison |

The test harness may retain expected arrays and result evidence; exported
product documents never do. Controlled fault evidence and genuine production
browser evidence must remain distinguishable. Three screenshot paths are
reserved for genuine inspected UI captures under `figures/`; their presence or
this map alone is not acceptance evidence. No dependency or installed-package
change is part of this map.
