# V2e known limitations

Acceptance and publication outcomes are recorded in
[tests_and_evidence.md](tests_and_evidence.md) and fresh ignored evidence.
This handoff does not declare pending browser, postcommit or push checks passed.

## Settings, not saved results

A file contains one complete current valid draft and title/notes for sequential,
two_path or polarization mode. Export of an older last-result configuration is
deferred. The UI identifies the captured draft/revision even if a different
older result remains visible. A requested browser download is not proof of a
saved Windows path, and unexported drafts are not automatically saved.

Files contain no result arrays, intermediate fields, sweep rows/recipes,
requests, validation tokens, success/qualified badges, code provenance, camera,
animation or renderer state. Import restores settings and explicitly says
they have not yet been simulated. Recalculation requires an ordinary deliberate
simulation. Earlier retained results keep their original identity and cannot
be reattached as newly imported success.

This is not an M5 artifact bundle or replay format. There is no server file
store, autosave, workspace library, archive extraction, cloud sharing, remote
deployment or automatic migration. Version 1 and the three exact model pairs
are closed; unsupported or incomplete documents reject without filling defaults
or silently dropping fields.

## Numeric and text scope

The supported numeric contract is finite binary64 under existing per-mode
domains. Original decimal spelling and arbitrary-precision values are not
preserved. Wide finite integer tokens in real fields can round once in the
existing validator; unusable magnitudes and nonzero decimal underflow reject.
Representable subnormals remain permitted only where the field's domain and
usable-derived-geometry checks allow them. Negative-zero bits are not preserved
by ordinary browser serialization. Exact nonzero identity and final canonical
idempotence are the declared guarantees on the tested path.

No cross-Python/browser/library/platform/version bitwise recomputation or
future-model compatibility is claimed. Canonical Python formatting is tied
to the supported implementation, not a universal JSON canonicalization standard.
The first raw-valid canonical response is not necessarily a browser-wire fixed
point; only the second prepared response can be previewed/applied.

Input and canonical output independently cap at 32768 UTF-8 bytes. Root depth0,
depth12, 2048 value nodes, decoded token8192 scalars, title120 and notes2000 are
separate bounds. A text-valid document can still exceed the byte cap and reject;
metadata is never truncated. The strict parser runs before iterative depth/node
checks, with recursion failures bounded as errors; this is not pre-parse
enforcement of depth12.

Unicode scalar values are counted rather than UTF-16 code units or grapheme
clusters. Combining marks count separately, while a supplementary-plane
character counts once. Allowed text is preserved without trimming or Unicode
normalization. Lone surrogates and U+0000..001F/U+007F..009F controls reject,
except notes may contain TAB/LF; CR rejects. Text is displayed literally with
textContent, without HTML/Markdown interpretation.

## Model boundaries remain unchanged

Sequential remains scalar, monochromatic, aligned and forward with the existing
ordered element set. Two-path remains the fixed ideal unfolded two-arm scalar
model. Polarization remains ideal same-plane ordered Jones action, with its
existing waist-plane restriction and 128-axis cap. Document validation checks
public specification/resource/derived-geometry domains but samples no source,
applies no element, simulates no result and certifies no experiment's physical
accuracy. No new optics, reflection frames, vector propagation, hardware or
later stage is included.

## Operations, memory and browser evidence

Preview never changes an editor. Apply requires explicit replacement
acknowledgment and rechecks operation/destination identity and the shared busy
state. Application while optical work is active is blocked even if it became
busy after preview. Document validation itself neither enters nor releases the
scientific gate and remains available while actual computation runs. Cancellation
and stale replies cannot complete an older operation or partially replace data.

One active document operation, one queued latest intent, one preview and one
prepared download are bounded. URLs are retained until replacement, dismissal
or disposal; no arbitrary timer asserts that a browser consumed a download.
Reader listeners and reservations are released on completion/cancellation.
Buffers, Blob bytes, logical strings and reservations count toward the existing
16 MiB persistent / 32 MiB transient app-owned budgets. These conservative
counts do not measure total browser heap, process working set or GPU memory.
Application failure and later display-resource failure are separate outcomes.

Actual browser permission, download consumption, renamed-file upload and fresh
storage-isolated recomputation require genuine acceptance evidence. Unit tests,
mocked transport and controlled faults are supplementary and cannot replace
those checks. Any blocked required step must remain pending in the completion
report. The existing Windows file-symlink skip remains explained separately;
no privilege elevation or test weakening is implied by V2e.
