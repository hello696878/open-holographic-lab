# W2 tests and evidence

This is the uncommitted implementation candidate's current evidence record.
The final Python/frontend, actual W2 browser, compatibility and controlled
gates have completed within the qualifications below. This candidate stops
for visual review; these results do not authorize publication or assert user
acceptance.

The accepted parent is `721156cef44bc76425d7d437cc258b6481acf204`.
Implementation and validation are authorized; staging, commit and push are
not. The original five planning files and their 42-path inventory remain
frozen. The exact initial identities, 438 tracked-file hashes and installed
distribution inventory are recorded in
[preflight.json](C:/holographiclab/runs/w2_geometric_routing_implementation_01/preflight.json).

All paths below belong to the fresh ignored evidence root
`C:\holographiclab\runs\w2_geometric_routing_implementation_01` unless
explicitly identified as historical. Evidence is append-only between
invocations. Raw stdout, stderr, argv, return code and source manifests are
retained; excerpts below do not replace those raw files.

## Baseline and required current checks

| Check | Current recorded result | Evidence classification |
|---|---|---|
| Unchanged Python baseline | **3653 passed, 1 skipped in 190.24s (0:03:10)** | Before implementation |
| Unchanged installed frontend baseline | **445 passed, 28 files**, Vitest duration 9.87s | Before implementation; initial sandbox spawn failure retained |
| Final Python candidate 03 | **3910 passed, 1 skipped in 300.98s (0:05:00)** | Required full suite; exit 0; source unchanged throughout |
| Final frontend candidate 04 typecheck | Exit 0 | Required check; source unchanged throughout |
| Final frontend candidate 04 unit suite | **495 passed, 32 files**, Vitest duration 13.39s | Required full installed suite; exit 0; source unchanged throughout |
| Final frontend candidate 04 production build | Exit 0; Vite reports 368ms | Required build; source unchanged throughout; bundle-size warning retained |

Baseline raw evidence:
[Python stdout](C:/holographiclab/runs/w2_geometric_routing_implementation_01/baseline/python.stdout.txt),
[Python invocation](C:/holographiclab/runs/w2_geometric_routing_implementation_01/baseline/python.json),
[frontend stdout](C:/holographiclab/runs/w2_geometric_routing_implementation_01/baseline/frontend_permission.stdout.txt),
[frontend invocation](C:/holographiclab/runs/w2_geometric_routing_implementation_01/baseline/frontend_permission.json).
The first frontend launch failed before tests during sandbox `spawn EPERM`;
its original stdout/stderr remain under `baseline/frontend.*`. The identical
installed suite then ran with normal process permission, without installing
dependencies or changing assertions.

Both baseline and current Python retain the existing skip, verbatim:

```text
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
```

Exact final Python command from the repository root:

```powershell
C:\holographiclab\.venv\Scripts\python.exe -m pytest -q
```

Exact final frontend commands, working directory
`C:\holographiclab\frontend\bench`:

```powershell
& 'C:\Program Files\nodejs\node.exe' node_modules/typescript/bin/tsc --noEmit
& 'C:\Program Files\nodejs\node.exe' node_modules/vitest/vitest.mjs run
& 'C:\Program Files\nodejs\node.exe' node_modules/vite/bin/vite.js build --outDir C:\holographiclab\runs\w2_geometric_routing_implementation_01\acceptance\frontend_final_04\assets
```

Required result manifests and unedited streams:
[Python result](C:/holographiclab/runs/w2_geometric_routing_implementation_01/acceptance/python_final_03/result.json),
[Python stdout](C:/holographiclab/runs/w2_geometric_routing_implementation_01/acceptance/python_final_03/stdout.txt),
[Python stderr](C:/holographiclab/runs/w2_geometric_routing_implementation_01/acceptance/python_final_03/stderr.txt),
[frontend declaration](C:/holographiclab/runs/w2_geometric_routing_implementation_01/acceptance/frontend_final_04/plan.json),
[typecheck result](C:/holographiclab/runs/w2_geometric_routing_implementation_01/acceptance/frontend_final_04/typecheck.json),
[unit result](C:/holographiclab/runs/w2_geometric_routing_implementation_01/acceptance/frontend_final_04/unit.json),
[unit stdout](C:/holographiclab/runs/w2_geometric_routing_implementation_01/acceptance/frontend_final_04/unit.stdout.txt),
[build result](C:/holographiclab/runs/w2_geometric_routing_implementation_01/acceptance/frontend_final_04/build.json),
[build stdout](C:/holographiclab/runs/w2_geometric_routing_implementation_01/acceptance/frontend_final_04/build.stdout.txt),
[build stderr](C:/holographiclab/runs/w2_geometric_routing_implementation_01/acceptance/frontend_final_04/build.stderr.txt).

The build writes exclusively to this invocation's fresh assets directory; it
does not replace an old accepted build. Its files are recorded in
[asset_manifest.json](C:/holographiclab/runs/w2_geometric_routing_implementation_01/acceptance/frontend_final_04/asset_manifest.json).
The JavaScript asset is 1,047.13 kB (gzip 272.16 kB); the existing >500 kB
warning remains visible. No warning threshold or build setting was changed.

These are snapshot qualifications. If any source relevant to a check changes
later, its manifest must be compared and any superseding result identified
explicitly; an earlier passing check is not silently relabelled current.

## Preserved required failures and invalidated qualification

`acceptance/frontend_final_01` is a genuine failed required invocation:
**492 passed, 1 failed**, exit 1. The new test-owned response-capture helper's
oversize test hit its unchanged 5000ms timeout. The production build was not
run after that failure. Original
[stdout](C:/holographiclab/runs/w2_geometric_routing_implementation_01/acceptance/frontend_final_01/unit.stdout.txt),
[stderr](C:/holographiclab/runs/w2_geometric_routing_implementation_01/acceptance/frontend_final_01/unit.stderr.txt)
and result remain intact; this failure is not reclassified as development.

An independent installed-Node probe established that awaiting cancellation
of a cloned tee reader waits for the untouched original branch. Before the
original response was consumed, cancellation had not settled; after it was
consumed, it had settled and all 524289 original bytes remained unchanged.
This follows the documented tee-cancellation behavior in the
[WHATWG Streams Standard](https://streams.spec.whatwg.org/#readable-stream-default-tee).

The deterministic repair changed only the new test helper: request clone
cancellation without awaiting it, handle its rejection, and propagate the
oversize failure immediately. The same original fetch Promise, one HTTP
request, one bounded armed clone and all existing assertions remain. A new
assertion checks that the original response remains intact. No timeout,
retry, production code, dependency or old test changed for this repair.

[Repair record](C:/holographiclab/runs/w2_geometric_routing_implementation_01/integration/capture_cancel_diagnosis_01/repair_record.json),
[probe stdout](C:/holographiclab/runs/w2_geometric_routing_implementation_01/integration/capture_cancel_diagnosis_01/stdout.txt),
[focused repair result](C:/holographiclab/runs/w2_geometric_routing_implementation_01/integration/capture_cancel_focused_01/result.json):
7 capture tests passed once. Full frontend candidate 02 passed 493 tests after that repair. Subsequent
approved UI/actor corrections produced final candidate 04 with 495 passes.
All changed candidates and earlier raw results remain separately identified;
this is not an unchanged retry until green.

`acceptance/python_final_01` is **not an accepted final suite** despite its
underlying **3902 passed, 1 skipped** output. Concurrent approved adapter
error-classification changes and six new regressions landed during execution.
The before/after manifest detected three changed paths. Its raw output and
[qualification_invalidated.json](C:/holographiclab/runs/w2_geometric_routing_implementation_01/acceptance/python_final_01/qualification_invalidated.json)
remain intact. Candidate 03 above was run after the final Python sources froze and
has `source_unchanged: true` with no changed paths.

Other development failures remain under their original directories. In
particular, `core/development_core_final_01` recorded 73 passed / 1 failed:
an exact-zero sum-of-squares interval had a negative-subnormal lower endpoint.
The implementation intersected that interval with the exact mathematical
nonnegative constraint; the original assertion was preserved. The frontend
development geometry-allocation assertion also caught an unused 140-byte
PlaneGeometry allocation, corrected by conditional allocation. Neither is
hidden by deleting, overwriting or weakening its detector.

## Independent numerical and finite-geometry evidence

The focused core invocation has **78 passed in 2.12s**, zero skips.
Exact command, source hashes and unedited streams are in
[development_core_final_03](C:/holographiclab/runs/w2_geometric_routing_implementation_01/core/development_core_final_03/invocation.json).
The standalone validator reports **14 direct cases and 16 isolated deliberate
source faults detected**, with original source unchanged and restored
assertions passing:

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 scripts/validate_w2_geometric_routing.py --output-dir C:\holographiclab\runs\w2_geometric_routing_implementation_01\core\validator_result_03 --negative-controls
```

[Validator report](C:/holographiclab/runs/w2_geometric_routing_implementation_01/core/validator_result_03/report.json),
[core manifest](C:/holographiclab/runs/w2_geometric_routing_implementation_01/core/core_handoff_manifest.json),
[full enclosure derivation](C:/holographiclab/runs/w2_geometric_routing_implementation_01/core/NUMERICAL_CONTRACT_AND_EVIDENCE.md).

The shipped 32-stage policy composes outward binary64 intervals through exact
stored-angle pose construction, origin/direction, plane parameter and point,
finite-domain inclusion, nearest ordering, Householder reflection, sphere
crossing, geometric norm and accumulated distance. Exact rational 32-term
Taylor certificates with bounded omitted tails enclose sine/cosine; no claim
is based on merely expanding libm results by one nextafter. Intersecting a
hit enclosure with its exact plane constraint reduces wrapping without
moving the nominal physical point. Finite-face Gram/singular-value bounds
are conservative culling bounds, not inflated apertures.

Assumptions are supported IEEE binary64 round-to-nearest, gradual underflow,
no FTZ/fastmath, correctly directed nextafter, and square-root error no more
than one binary64 ulp. Arithmetic outside the contract fails. Unresolved
edges, near-launch/coplanar roots, ties or hit/distance overlap remain
ambiguity. Direction drift is retained and geometric distances use
`hypot(end-start)`, not unqualified ray parameter t.

Independent Decimal recurrences using 160 digits call no production intersection or
reflection helpers. Stored binary64 frames and independently evaluated ideal
real-angle rotations are different comparison targets. Complete axial and
oblique 32-hit trajectories, including a translated source at
(9.5, -9.3, 9.1) m, check every propagated pose/ray/hit/local/reflection/length
certificate against its reference. The ordinary independent comparison uses
rtol=2e-13, direction atol=2e-13, and point/length
atol=2e-13*max(1m, coordinate norms, cumulative length). Interval inclusion
is checked as enclosure membership rather than replacing bounds with those
comparison tolerances.

For the recorded oblique 32-hit case:

| Quantity | Measured observation |
|---|---:|
| Max nominal point error against stored-frame target | 5.551115123125783e-17 m |
| Max nominal direction error against stored-frame target | 5.551115123125783e-16 |
| Max nominal point error against ideal-angle target | 1.1934897514720433e-15 m |
| Max nominal direction error against ideal-angle target | 1.1546319456101628e-14 |
| Conservative propagated point bound | 2.678725824489803e-9 m |
| Direction norm drift | 1.2212453270876722e-14 |

The much smaller observed errors are not substituted for the conservative
bound. Interval composition is the conditional enclosure argument; a small
observed error alone is not a proof of conservatism or uniform grazing
accuracy.

Direct independent A/B/C checks cover one-mirror 0.4 m detection, two-mirror
0.6 m detection, splitter 0.5/0.5 detection, and a stop changing only one
branch to absorption. Additional tests cover disk/rectangle off-axis hits,
local receiver coordinates, 3D poses, nearest-hit array reordering, both
sides, finite misses, irrelevant coplanar planes, near-parallel and close
surfaces, revisits, all caps and queued-weight accounting, source/result
nonmutation and caller floating-point settings. Pure geometry invariance
tests keep transformed scenes inside the supported domain.

The sixteen deliberately faulty isolated source copies target reflection
sign, rotation order, local basis, finite aperture, catalog ordering,
irrelevant infinite-plane rejection, revisit suppression, arbitrary origin
epsilon, lost/duplicated splitter weight, dropped queued weight, truncation
mislabelled complete/absorbed/detected, singleton pose certificates and reset
departure uncertainty. All produce substantive assertion failures; setup and
import failures are not counted. Production core SHA256 before and after:
`08c469499aaa5652d307bc3b5a9b1421231c8cf50782c5aac04c5ba0176f164d`.

## API, transport and controller evidence

Current focused API development integration has **189 passed in 4.40s**:
[exact command](C:/holographiclab/runs/w2_geometric_routing_implementation_01/api/integration_dev_05/invocation.json),
[stdout](C:/holographiclab/runs/w2_geometric_routing_implementation_01/api/integration_dev_05/stdout.txt),
[trust review/addendum](C:/holographiclab/runs/w2_geometric_routing_implementation_01/api/trust_audit_01/final_adapter_addendum.json).
These regressions cover strict schema/identity/graph/ledger validation,
request and response caps, distinct error classifications, pure validation,
actual-worker-lifetime coverage through encoding, all nine old operations
sharing W2's gate, disconnect/cancellation and protected architecture rules.
They are ASGI/direct evidence, not a browser pass or another optical solver.

Current adapter SHA256 is
`7f459b3048f64b036ead189713cf70a1909af28bb073174526167ca3fb7109bc`;
protocol SHA256 is
`af31515df438ef988e5edf218425df7636a28b228b551b75e5f7821f47d56376`.

The genuine record-cap core case passes public adapter validation, exactly
one public trace, strict production encoding and identity-bound decoding:
**180815 response bytes**, 53 created branches, 128 segments plus 128 hits,
truncated weight 1, signed residual 0; direct pipeline elapsed
0.13407259993255138 s. Its original validation/trace bytes and hashes remain
under
[adapter_pipeline_record256_01](C:/holographiclab/runs/w2_geometric_routing_implementation_01/core/adapter_pipeline_record256_01).

The current TypeScript decoder independently consumed those preserved real
bytes without another optical/HTTP request:
[genuine_cap_decode_01](C:/holographiclab/runs/w2_geometric_routing_implementation_01/frontend/genuine_cap_decode_01/stdout.txt).
It accepted 26 immediately capped child birth-hit terminals with exact graph
identity and the same ledger. This is actual cross-language compatibility,
not a live browser execution.

Separate independently authored schema stress uses 16 elements, 63 branches,
128 hits plus 128 segments and maximum 64-character element/branch IDs. The
protocol rejects one extra record/branch and fails rather than truncating
when its byte cap is exceeded. This fixture is explicitly nonphysical;
neither it nor the measured 180815-byte genuine case is a formal worst-case
serializer bound.

A separate bounded non-optical numeric representation probe is retained in
`integration/handoff_draft_01/numeric_serializer_01`. It runs the actual
production serializer and strict identity-bound decoder on a schema-valid
graph with maximum record/branch/element/identifier counts, long finite
binary64 literals, minimum positive subnormal and maximum finite uncertainty
endpoints. The accepted payload is **227990 B**, with 6141 numeric tokens,
longest token 24 B; every numeric value round-trips bitwise. No tracer module,
optical function or test runner is invoked. This synthetic graph is explicitly
not an optical route and its measured size is not called a proven maximum.

For the shipped finite-float DTO, a separate conservative closed-grammar
size argument gives **427884 B < 524288 B**: exact fixed keys/punctuation;
every string/null overcharged as a 64-character ASCII value; every finite
float or bounded counter overcharged as a 32-byte token; 16 rectangle
elements/frames; 63 branches and (independently overcounted) terminals; two
outgoing records for every hit; maximize all h=0..128 and s=256-h. This
ignores tighter graph constraints. The numerical argument applies to Python
3.11 shortest-round-trip finite binary64 representations and the core's
bounded integer metadata, rather than arbitrary objects supplied directly
to the protocol. Detailed assumptions and primary serializer sources are in
the probe's README/report.

The broader protocol schema can accept 309-digit builtin integers in some
unconstrained finite numeric fields. A separate schema-valid **667286 B**
huge-integer uncertainty graph was deliberately rejected by the actual encoder
with `trace response exceeds524288-byte limit`. It is not produced by the
float64 core. This confirms atomic rejection; the cap was unchanged and no
records were omitted. Do not generalize the tighter typed-float bound to all
objects that the representation validator alone could accept.

Frontend source controls separately detected all four intended actor/resource
faults: stale attachment, hidden trace on passive viewing, duplicate Trace
admission and understated apparatus ownership. The initial source-control snapshot had 40 passing checks;
each faulty case hit its named substantive assertion, selected restored
checks passed, and its final restored 40 passed with all seven source/test byte
hashes restored. Subsequent DOM accounting and two actor regressions increased
the current focused selection to 43 checks. Final source controls 02 reran
**43 original passes, all four intended faults detected, 43 restored passes**
with exact seven-owner restoration and no import/setup failures counted.
The final actor SHA256 is
`3a14b2d00afda478427fc3d24c67d5999f6bbbe1e8a31452d7b665e23ca6cb72`. Evidence:
[fault summary](C:/holographiclab/runs/w2_geometric_routing_implementation_01/frontend/fault_controls_02/summary.json),
[post-control compatibility](C:/holographiclab/runs/w2_geometric_routing_implementation_01/frontend/post_control_compatibility.json),
[frontend notes](C:/holographiclab/runs/w2_geometric_routing_implementation_01/frontend/FRONTEND_IMPLEMENTATION_NOTES.md).
These are actor/resource controls, distinct from numerical negative controls,
schema rejection tests and labelled controlled browser failures.

## Resource and runtime evidence boundaries

Global app-owned limits remain **16 MiB persistent / 32 MiB transient**;
W2's operation admission remains **2 MiB retained / 4 MiB transient**.
Current recorded figures have different scopes:

| Observation | Recorded amount | What it does not establish |
|---|---:|---|
| Genuine record-cap core DTO serialization | 180581 B | Protocol/identity overhead or worst-case JSON |
| Same genuine result through adapter wire | 180815 B | Worst-case response bound or browser memory |
| Python traced retained result records | 919604 B | JS/native/GPU/RSS ownership |
| Python encode/decode traced current / peak | 1627838 / 2454198 B | Browser transient peak |
| TS same-result parsed reservation | 586724 B | Live rendering/old-result/DOM overlap |
| TS same-result number / UTF-16 string-key / container reserves | 48072 / 124644 / 414008 B | A total engine heap measurement |
| TS retained raw bytes / response text | 0 / 0 B | Native fetch/clone storage |

Source accounting includes persistent draft and validation snapshots, frozen
active request, completion identity, preset templates, immutable result DTOs,
actual geometry buffers, declared scene/material resources, labels and DOM
field/text/container reservations. A 1 MiB future inspector reservation is
admitted before synchronous result attachment inside W2's existing 2 MiB
retained policy. Root global accounting must include retained old modes and
documents, prepared replacement/rollback and overlap without eviction or
budget increases. Actual selected browser admission/release and owner snapshots are recorded
below. They remain distinct from the offline full-record prepare formula and
a continuous native-memory or transient-peak measurement.

The direct core times include validation/trace/serialization only, excluding
HTTP, worker scheduling, browser and GPU. A/B/C recorded about 0.009/0.009/
0.006 s; the genuine record-cap case about 0.111 s. Live request duration,
response bytes, frame intervals and CPU render-submission times must be
reported from genuine production browser operation. CPU submission is not
GPU completion or a guaranteed frame rate.


## Preserved product failures, bounded repairs and execution safeguards

The first required W2 browser group stopped at B03 after two passes. Adding a
stop while the Trace Data tab was active left the new component's inspector
hidden, so the existing pose-edit locator reached its unchanged test timeout.
`acceptance/browser_w2_01/stopped.json` and its original case 003 output remain.
The one-line current workspace correction selects the Inspector after an
explicit Add action. It changes presentation only; the original test and its
timeout were preserved. Frontend candidate 03 then passed its required checks.

W2 group 02 later recorded 19 passing invocations and one failure at C04:
`completedRequestId` remained null at the existing 5000 ms poll after an
intentional DOM preparation error. Source diagnosis found that a subscriber
failure could replace newly completed ownership with an old displayed result,
and the actor could then automatically attach after recording a display error.
The bounded final correction prefers `completedNumerical` in notification
failure handling and suppresses automatic attachment when completion
publication has a render error. Two added unit regressions cover first-result
and replacement-result publication failures. Each requires manual display
recovery, retains the same new numerical object/identity and proves there is
no new scientific request. Original assertions and timeouts remain unchanged.

The original group 02 failure, captured numerical response and diagnosis are
preserved under `acceptance/browser_w2_02` and
`integration/dom_failure_repair_01`. Final source controls 02 and frontend candidate 04
checks pass on the corrected, frozen source. Final browser candidate 04 is a new changed
candidate qualification; earlier failed required invocations remain failures.

A separate static orchestration audit found unresolved legacy service asset
sentinels, incomplete relative fixture closure, teardown not being a required
acceptance condition, and missing build-source manifest comparison. The owned
ignored driver now resolves those paths, copies the full byte-identical
provenance-checked 16-file / 24785-byte fixture tree, requires child exit 0 / free
owned port/no hold timeout, and compares build source hashes before and after
execution. These are execution/provenance safeguards, not new numerical
measurements or amendments to protected old assertions. Audit and provenance:
`integration/browser_orchestration_audit_01/report.json` and
`integration/legacy_fixture_closure_01/provenance.json`.

## Final actual W2 production-browser group

[Final group summary](C:/holographiclab/runs/w2_geometric_routing_implementation_01/acceptance/browser_w2_04/summary.json)
records **20 passing invocations / 19 unique declared test IDs**, zero skips,
zero failures and retries = 0. One transport-rejection ID executes separately
for malformed bytes and wrong UUID. Each invocation uses one worker, one test,
a fresh owned evidence root and the installed Chrome 155.0.8059.85. Every
selected case reports exact coverage and unchanged source identity; served
assets match final frontend candidate 04. Discovery's list-only skipped labels are not
execution results.

The current cases demonstrate genuine A/B/C optical responses and local
coordinates, an ordinary pose-edit finite miss, stale/late-result detachment,
passive camera/branch inspection, explicit Trace, ambiguity rejection, domain
and 32-hit truncation, mixed-mode release, actual WebGL context recovery,
actual 200% content zoom, and bounded transport/presentation controls.
The controlled DOM failure now preserves the completed original result and
manual presentation recovery attaches it without repeating the optical call.
Shared-worker tests include all ten route contenders, actual encoding hold
and disconnect, older-operation contention and independently observed idle.
Controlled holds and altered child-only transport are labelled controls;
malformed/wrong-identity replies are never counted as scientific success.

All 20 owned service children exit 0, all 20 cleanup records observe the owned
port free, and no service-hold timeout marker exists. These teardown checks
are distinct from the actual browser pass assertions. No unrelated service or
port 8501 was managed. Detailed aggregation and exact input/source hashes are
in
[final browser resource report](C:/holographiclab/runs/w2_geometric_routing_implementation_01/integration/browser_resource_summary_02/report.json).

### Genuine visual evidence and layout

The approved handoff figures are byte-identical copies of actual final candidate 04
production-browser captures, with originals, checksums and source case IDs in
[integration/media_handoff_01/manifest.json](C:/holographiclab/runs/w2_geometric_routing_implementation_01/integration/media_handoff_01/manifest.json):

- [Reflected receiver hit](figures/folded_route.png).
- [Pose edit followed by actual finite miss](figures/trace_inspection.png).
- [Separate split and blocked terminal weights](figures/split_blocked_route.png).

Current 1366×768, 1440×900 and 1920×1080 checks show root scrollWidth equal to
viewport width, English text and nowrap scalar cells. The central canvas
rectangles are 736×325.4375, 810×457.4375 and 1290×637.4375 CSS px respectively.
Actual Chrome 200% content zoom in a disposable task profile reports
outerWidth = 1440, innerWidth = 709, devicePixelRatio = 2, visualViewport.scale = 1 and
root scrollWidth = 709; its full terminal table is 654 CSS px wide. This is not
CSS/pinch/device-scale emulation and does not alter the user's browser profile.

The actual normal-speed workflow lasts 36.056 s and its saved WebM container
reports 36.64 s, 2684052 bytes, SHA256
`e6a78bd2a16b26b56eb72d5ee585f8ba1efa1dbe6159796258ed567f47d7c9bd`:
[production interaction recording](C:/holographiclab/runs/w2_geometric_routing_implementation_01/acceptance/browser_w2_04/014/browser/custom_w2_evidence_dir/5523191c6c8996b0e5f2a3e7/recording/page@7855c8474f7159e22122ce33dbab13d7.webm).
It shows explicit Trace, hit/branch inspection, mirror pose editing and stale
paths, explicit recomputation to a finite miss, then split/stop weights. Its
scientific request list contains exactly three intentional W2 trace calls.
No artificial animation between precomputed route drawings is used.

### Actual runtime and ownership observations

**Final Python candidate 03 ran concurrently with this W2 browser workflow.** These are
observations under that concurrent load, not isolated performance benchmarks.
The 21 ordinary successful routing worker operations measure public tracing
plus full strict encoding: 0.476–12.155 ms, median = 2.273 ms, p95 = 8.348 ms.
Actual responses are 1591–29344 B, median = 3875 B. All 19 saved original browser
identity captures match service genuine/returned SHA256 and byte counts.
Their HTTP+decode median is 46.9 ms, decode subset median = 1.4 ms, presentation
attachment median = 1.5 ms. HTTP+decode includes decode; these timings must not be
summed as independent phases. Controlled holds/faults/errors are excluded
from the ordinary worker statistics.

Across 31 saved W2 snapshot occurrences, independent maxima are 132958 B
numerical, 325932 B rendering, 29066 B state, 223346 B DOM already within rendering,
and 482906 B W2 total. Component maxima may come from different snapshots and
must not be added. The largest saved global account is 9030730 B. These are
explicit app-owned reservations and actual CPU buffer stores, not total
browser/native/GPU heap or a measured continuous transient peak.

B08 preserves a prepared settings document and old-mode/R03/W1/W2 results,
then explicitly releases results with invalid mirror text `-` intact:

| Account | Before release | After release |
|---|---:|---:|
| Global retained | 9030730 B | 622976 B |
| Old numerical arrays | 2121728 B | 0 B |
| Old result canvases | 1048576 B | 0 B |
| W1 (shared alias removed) | 5382640 B | 234420 B |
| R03 | 269740 B | 247212 B |
| W2 total | 191874 B | 125172 B |
| W2 numerics | 19774 B | 0 B |
| Prepared document | 2816 B | 2816 B |

Declared ownership falls by 8407754 B. W2 current/previous/completed IDs become
null; useful apparatus/draft/invalid input remain. Document state, prepared
download and metadata are exactly unchanged, and view changes/release add no
scientific requests.

The recording's final W2/global accounts are 227906 / 413070 B. Its last 600
retained RAF intervals have median = 4.2 ms, p95 = 8.3 ms, p99 = 8.4 ms, max = 12.5 ms. Last 600
CPU `renderer.render` submission times have median = 0.55 ms, p95 = 0.9 ms, p99 = 1.401 ms,
max = 3.0 ms. The app instrumentation records one renderer, one controls instance
and one RAF loop, 47 final draw calls. Percentiles use linear sorted interpolation
at (n-1)*p. The bounded sample buffers do not describe the full recording
population. Submission brackets rendering after controls/labels update and
does not wait for GPU completion; these are not GPU timings or guaranteed FPS.

### Final-source full-record owner formula, separately qualified

[resource_max_record_02/report.json](C:/holographiclab/runs/w2_geometric_routing_implementation_01/integration/resource_max_record_02/report.json)
replays the unchanged genuine 180815-byte cap-record response through current
strict decoding, actual controller state and Three.js CPU-side factories.
No optical work, HTTP, browser / WebGL / native DOM, test suite or build occurs.
Exactly two preparation phases are required before PASS.

The actual first prepare formula is 586724 B result + 268776 B route + 55496 B
apparatus + 5372 B exact derived production label reservation + 51004 B current
state + 1048576 B prospective DOM cap = **2015948 B**, below the unchanged 2 MiB
reservation by **81204 B**. Actual unique route/apparatus backing stores are
5352 / 26056 B. The second old/new ownership replay totals 2015932 B for the same
prepare formula. The conservative new-incoming transport/state/display envelope
is 2837512 B, below 4 MiB; old retained ownership is separately included by root
global 16 / 32 MiB admission. Both display owners and the apparatus report 0 B
following disposal, and numerical ownership releases to 0 B.

No DOM shim is used. The 5372 B label figure derives the exact unchanged
production title formula; the full 128-hit inspector DOM is not created here.
Same original UUID/bytes are replayed twice only to model independent old/new
owners, not two real submissions. The 81 KiB headroom is specific to the actual
9-element cap case and saved source identities, not a universal margin for
all 16-element/max-identifier scenes or full-cap browser attachment.
The initial resource_max_record_01 setup returned the wrong validation seam
type, ran zero preparations and produced an invalid vacuous PASS; it remains
explicitly invalidated in its original qualification record. Corrected fresh
probes require a valid draft and exactly two phases. No old failure is erased.

## Final compatibility and closeout checkpoint — 2026-10-21

The fixed final frontend 04 source/assets completed every predeclared group:

| Group | Passing invocations | Controlled-only skips | Current summary under acceptance/ |
|---|---:|---:|---|
| W2, including both transport faults | 20 | 0 | browser_w2_04/summary.json |
| Original 63 legacy IDs | 55 | 8 | browser_legacy_04/summary.json |
| W1, including genuine held encoding/disconnect | 12 | 0 | browser_w1_04/summary.json |
| English interface | 7 | 0 | browser_english_04/summary.json |
| Fresh legacy controlled scenarios | 19 | 0 | browser_legacy_controls_04/summary.json |

Total: **121 isolated invocations, 113 passes, 8 expected exclusions, 101
unique declared IDs**. The legacy controls execute the eight excluded IDs
under their required distinct operations/failure positions; they are separate
scenarios, not retries. All invocations use workers=1/retries=0, exactly one
selected test and one attempt, exact ID/file/title coverage, unchanged source
identity and fresh owned output roles. No forced clicks, larger timeouts or
protected assertion amendments were introduced.

[Full serial execution record](C:/holographiclab/runs/w2_geometric_routing_implementation_01/acceptance/final_browser_sequence_04/summary.json),
[exact coverage and teardown review](C:/holographiclab/runs/w2_geometric_routing_implementation_01/closeout/review_01/browser_coverage.json).
All 121 owned service children exited 0 and observed their port free after
shutdown; no coordination timeout marker remained. Browser contexts and
recording/zoom profiles were closed by their owners. No unrelated process or
service on port 8501 was managed. The final owned listener on 8510 is closed.

The prior browser_legacy_01 results remain separately preserved as candidate
03 evidence. Historical numerical/document fixtures are reused with exact
byte/hash provenance, not relabelled fresh measurements. Fresh current
functional passes do not explain or repair the accepted W1.1 history's
unknown CDP cause or its lost, unverifiable overwritten screenshot.

[Protection/environment audit](C:/holographiclab/runs/w2_geometric_routing_implementation_01/integration/protection_audit_02/report.json)
confirms all 429 protected tracked files, five frozen planning files and the
approval hash unchanged; 53 distributions/395 metadata files, seven frontend
package identities, Node and Chrome 155.0.8059.85 are unchanged. No dependency,
lockfile, browser version or persistent/global setting was changed. The sole
pre-existing test amendment is the exact adapter import permission; no old
scientific assertion was changed. The final 90-source production manifest
and all served asset hashes match.

The working tree contains exactly **9 approved modifications and 33 approved
creations**, all unstaged. Full file hashes, line counts and human review diff:
[42-path review](C:/holographiclab/runs/w2_geometric_routing_implementation_01/closeout/review_01/REVIEW.md),
[complete text diff and PNG identities](C:/holographiclab/runs/w2_geometric_routing_implementation_01/closeout/review_01/review_final.diff).
HEAD and local upstream remain `721156cef44bc76425d7d437cc258b6481acf204`
on main; the read-only live origin/main check matches the same baseline:
[remote evidence](C:/holographiclab/runs/w2_geometric_routing_implementation_01/integration/remote_final_01.json).
No staging, commit, push, history rewrite or publication occurred.

This is the uncommitted **visual-review checkpoint**, with no required test
failure outstanding. Resource/native-DOM, floating-point and ideal-model
qualifications above remain in force. No refraction, folded-wave coupling,
new persistence, Figure 2a reconciliation, hardware, deployment or teaching
state work was started. Publication requires separate explicit approval.

## Unedited final current output

The following blocks copy complete named UTF-8 streams, with only Markdown
fences added. The original raw files and result/source manifests remain the
authority. Python candidate 03 reports 300.98 s test duration; the invocation's measured
wall duration is 302.657 s, exit 0, source_unchanged=true, changed_paths=[].

### Python final candidate 03 stdout

```text
........................................................................ [  1%]
........................................................................ [  3%]
........................................................................ [  5%]
........................................................................ [  7%]
........................................................................ [  9%]
........................................................................ [ 11%]
........................................................................ [ 12%]
........................................................................ [ 14%]
........................................................................ [ 16%]
........................................................................ [ 18%]
........................................................................ [ 20%]
........................................................................ [ 22%]
........................................................................ [ 23%]
........................................................................ [ 25%]
........................................................................ [ 27%]
........................................................................ [ 29%]
........................................................................ [ 31%]
........................................................................ [ 33%]
........................................................................ [ 34%]
........................................................................ [ 36%]
........................................................................ [ 38%]
........................................................................ [ 40%]
........................................................................ [ 42%]
........................................................................ [ 44%]
........................................................................ [ 46%]
........................................................................ [ 47%]
........................................................................ [ 49%]
........................................................................ [ 51%]
........................................................................ [ 53%]
.............................................................s.......... [ 55%]
........................................................................ [ 57%]
........................................................................ [ 58%]
........................................................................ [ 60%]
........................................................................ [ 62%]
........................................................................ [ 64%]
........................................................................ [ 66%]
........................................................................ [ 68%]
........................................................................ [ 69%]
........................................................................ [ 71%]
........................................................................ [ 73%]
........................................................................ [ 75%]
........................................................................ [ 77%]
........................................................................ [ 79%]
........................................................................ [ 81%]
........................................................................ [ 82%]
........................................................................ [ 84%]
........................................................................ [ 86%]
........................................................................ [ 88%]
........................................................................ [ 90%]
........................................................................ [ 92%]
........................................................................ [ 93%]
........................................................................ [ 95%]
........................................................................ [ 97%]
........................................................................ [ 99%]
.......................                                                  [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
3910 passed, 1 skipped in 300.98s (0:05:00)
```

### Frontend final candidate 04 unit stdout

```text

 RUN  v5.0.3 C:/holographiclab/frontend/bench


 Test Files  32 passed (32)
      Tests  495 passed (495)
   Start at  14:56:27
   Duration  13.39s (import 59%, tests 21%, transform 17%, worker 2%)

    Isolate  32 workers spawned · ~178ms startup each (spawn + environment, per file)
             at least ~5.53s faster with isolate: false — reuses workers across files instead of one per file

```

### Frontend final candidate 04 build stdout

```text
vite v8.3.2 building client environment for production...
transforming...
✓ 45 modules transformed.
rendering chunks...
computing gzip size...
../../runs/w2_geometric_routing_implementation_01/acceptance/frontend_final_04/assets/index.html                     0.53 kB │ gzip:   0.33 kB
../../runs/w2_geometric_routing_implementation_01/acceptance/frontend_final_04/assets/assets/index-Cgp8ZCVl.css     41.19 kB │ gzip:   8.12 kB
../../runs/w2_geometric_routing_implementation_01/acceptance/frontend_final_04/assets/assets/index-BqHE3Co0.js   1,047.13 kB │ gzip: 272.16 kB

✓ built in 368ms
```

### Frontend final candidate 04 build stderr, warning retained

```text
[plugin builtin:vite-reporter] 
(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rolldownOptions.output.codeSplitting to improve chunking: https://rolldown.rs/reference/OutputOptions.codeSplitting
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
```

### Preserved required frontend candidate 01 failure stderr

```text

⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  tests/w2_response_capture.test.ts > bounded original W2 response capture instrumentation > rejects declared and streaming oversize separately
Error: Test timed out in 5000ms.
If this is a long-running test, pass a timeout value as the last argument or configure it globally with "testTimeout".
 ❯ tests/w2_response_capture.test.ts:40:3
     38|     await expect(x.capture.consume('token')).rejects.toThrow('request …
     39|   });
     40|   it('rejects declared and streaming oversize separately', async () =>…
       |   ^
     41|     for (const response of [new Response('{}', { headers: { 'content-l…
     42|       const x = fixture(response); x.capture.fetch(...args);

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/1]⎯

```
