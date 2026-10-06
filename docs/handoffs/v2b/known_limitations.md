# V2b known limitations

V2b is the existing V1 local bench plus an ideal unfolded two-path mode using
the unchanged public V0/V2a numerical APIs. It does not add mirror/reflection
geometry, polarization, arbitrary topology, shutters, coatings, calibrated
radiometry, hardware, public deployment, persistence or V2c work.

## Numerical and visual meaning

The scalar monochromatic sampled window is periodic. Gaussian sampling and
existing ASM assumptions still apply. The per-axis caps limit resources;
they do not certify adequate sampling, negligible wraparound or physical
accuracy for every accepted specification. Binary64 large phases retain the
existing finite argument-precision limits.

Both output arrays are measured immediately after B_dagger in the same
canonical transverse frame. Mesh separation and guide lengths are cosmetic.
There is no added output travel, physical reflection flip, conjugation,
geometric lane-phase inference or universal beam-splitter orientation law.
Both graphics textures use the same UV row mapping; raw picks preserve the
original row/column and metre axes. Equal modes with uniform phase show
brightness redistribution without invented spatial fringes.

Intensity has amplitude-unit² units. Sampled norms have amplitude-unit² m²
units, not watts or authenticated efficiency. Fractions divide by original
input; evanescent survival below one, tiny dark-port values, signed residuals
and zero-input null ratios remain as returned. Display range can saturate
large values or render small nonzero values black; maxima, saturation
notices and original float64 picks preserve that distinction. Screenshots
are presentation evidence, not a numerical accuracy measurement.

Browser-authored numeric -0 source/arm phase becomes +0 before validated
identity. This narrow transport/UI policy does not preserve the impossible
ordinary `JSON.stringify(-0)` sign round trip and does not modify nonzero
phases. Radians are authoritative; the degree label is not another input.
Metres remain authoritative for propagation; mm/µm/nm controls are explicit
convenience conversions.

Extreme valid binary64 specifications can exceed Float32 scene-coordinate
range. Derived scene geometry is preflighted and rejected as a presentation
failure before prior scene resources are discarded. Numerical validity does
not guarantee displayability on WebGL2. Context loss/unsupported rendering
is reported separately; no fabricated image or automatic numerical retry
substitutes for it.

## Requests, failures and lifetime

Sequential mode remains the default. Each mode owns its own draft/result
type. Scientific edits detach both current dual displays. Mode changes
invalidate pending attachment eligibility even on an away-and-back switch.
Late results retain their own submitted specification in the prior area.
Camera, selection, resize and color controls do not validate or simulate.

One shared client operation gate suppresses duplicate clicks; one server
gate rejects concurrent accepted numerical operations without a queue.
This is not durable exactly-once delivery across reloads, crashes or lost
responses. Abort/disconnect cannot terminate a running Python thread. The
server remains busy until actual worker and encoding completion; a client
interruption leaves backend completion unknown until separately observed.
There is no forced cancellation, automatic retry, diagnostic replay or
background job system.

Both ports, identity, arrays and diagnostics form one completed result.
New textures/canvases/readouts are prepared before publication, with cleanup
on second-resource failure. A presentation failure after numerical success
keeps the new completed numerical result separate from the prior recoverable
result; it is not reported as failed optics and does not resubmit the solver.
Normal replacement retains one dual result; this failure-recovery exception
may hold the previous result and the one new completed result. There is no
result history or image stack.

The explicit sweep fixes source, grid and both arm distances and makes 17
actual phase calls. Its scientific identity excludes the unused current
draft's extra phase. Attachment eligibility still tracks all scientific
edits, including that draft phase. Endpoint equality is tolerance-based;
actual independently computed 0 and 2pi values are preserved. A failed
sweep is an overall failed operation with a genuine contiguous prefix only,
prominently labelled FAILED/PARTIAL; missing points are not fabricated or
interpolated across. The browser can select a computed row without work and
separately request its full dual arrays.

## Exact transport and status boundaries

All POST request bodies are capped at 32,768 bytes, strict UTF-8 JSON with
duplicate/nonfinite rejection, supported JSON Content-Type and a five-second
body-read timeout. Single axes are 1..512; sweep axes are 1..128 with exactly
17 predeclared literal phases. Validation allocates no scientific fields and
runs no sampler/solver.

`OHLAB2P` is a transient response, not an archive schema. Its `<8sII`
preamble carries magic `OHLAB2P\0`, bounded header length and reserved zero.
The JSON header is at most 16,384 bytes and zero-padded to eight-byte
alignment. Ordered payload is intensity_port_0, intensity_port_1, x_m, y_m,
all C-order little-endian float64, with exact typed descriptors and identity.
At 512x512 its payload is `8*(2*512*512+512+512)=4,202,496` bytes; the complete
cap is `16+16,384+4,202,496=4,218,896` bytes. The strict scalar sweep response
cap is 65,536 bytes. Legacy `OHLABV1` bytes and its 2,359,296-byte cap remain
unchanged; the parsers reject the other format.

| Condition | HTTP status / response |
|---|---|
| Valid single validation, simulation or complete sweep | 200; typed validation JSON, complete dual frame or complete scalar sweep |
| Invalid JSON/body framing | 400; `two_path_error` |
| Body read timeout / oversized body / unsupported Content-Type | 408 / 413 / 415; `two_path_error` |
| Invalid public input/specification | 422; `two_path_error` |
| Another numerical operation still owns the gate | 409; `two_path_error`, no queue |
| Single numerical/domain failure | 422; `two_path_error` |
| Expected numerical/domain failure during sweep | 422; strict `two_path_sweep_result`, status failed, genuine prefix |
| Unexpected failure during sweep loop | 500; strict failed sweep with genuine prefix and generic internal message |
| Executor submission, result/response encoding or invalid worker reply | 500; bounded generic `two_path_error` |
| Future cancelled before worker starts | 503; `two_path_error` |
| Detected client disconnect | 499; interruption envelope if a response can still be delivered, not a scientific sweep completion |

The failed sweep schema includes version/type, request/fixed-specification
identity, fixed experiment, exact phases, failed status, requested/completed
counts, failed_index equal to prefix length, genuine rows and bounded
error.code/error.message. Encoding failure cannot safely publish that schema
and uses the regular error envelope instead. Common Host/header/Origin and
unknown-path/method rejection preserve the existing V1 generic error
envelope: 400/403 and 404/405 respectively. Exact field lists and tests are
in [implementation_summary.md](implementation_summary.md) and the protocol
modules; no complex fields or arm intermediates are transported.

## App-owned resource policy

The budgets are **16 MiB persistent** and **32 MiB transient** app-owned
data, not the entire JS heap, browser tab, GPU or Python process. Persistent
accounting deduplicates retained scientific ArrayBuffers: one sequential
result, one dual result, the necessary previous-plus-new numerical
presentation-failure exception, and one serialized scalar sweep. It also
counts actual both-mode 2D intensity-canvas backing stores and active
detector-texture RGBA source arrays. Current/last aliases count once.

The transient dual estimate takes the maximum of distinct reachable phases,
rather than summing objects whose ownership lifetimes do not overlap:

- Transport: retained bytes plus bounded response chunks and their joined frame.
- Decode: retained bytes plus the joined frame and decoded scientific arrays.
- Presentation preparation: retained bytes plus decoded arrays, two RGBA texture sources, two 2D canvas stores and bounded per-port conversion buffers.

The UI adds a 128 KiB accounting allowance before preparation checks.
Scalar-sweep accounting uses serialized JSON byte size; JS object/string
overhead is excluded. Also excluded are renderer framebuffers/caches,
GPU/driver allocations, general DOM/listener overhead and unrelated
browser/runtime allocations. These limits do not measure or bound Python
FFT working memory. Resource evidence assesses the approved deterministic
repeated mode/result/sweep/resize/range/stale sequence; renderer internal
caches need not become zero, and a single count is not a general leak proof.

Obsolete detector textures, canvases and task-owned geometries/materials are
disposed or zero-sized. There is no persistent experiment store; reload
discards draft/view/results and returns to a passive sequential preset.

## Environment and evidence scope

The server is task-owned and loopback-only at 127.0.0.1:8510, with exact
Host/same-origin POST policy, owned production assets and no public CORS.
It is not an authenticated multiuser/public deployment. Acceptance uses the
existing Windows project interpreter, installed frontend tools and unchanged
dependency declarations/lockfile; cross-platform/version/GPU equivalence
requires separate evidence.

Controlled failures and asymmetric frames identify integration faults;
they are labelled isolated controls, not claims that the unmodified public
solver normally produces malformed data. Current measured runs, retained
failed attempts, remaining uncertainty and publication gates are recorded
in [tests_and_evidence.md](tests_and_evidence.md). This limitations document
does not claim commit, clean-postcommit acceptance or push has already
occurred. Historical evidence remains historical. No later stage or lesson
completion is assumed.
