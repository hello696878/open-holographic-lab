# V1 code map

Paths are repository-relative. V1 presentation/application code is separated
from the unchanged scientific implementation in `src/ohlab/optics/`.

## Python application boundary

| File | Responsibility |
|---|---|
| `apps/virtual_bench/__init__.py` | New application package; no automatic server launch |
| `apps/virtual_bench/adapter.py` | Duplicate-key/finite JSON parsing, cheap resource/type limits, authoritative V0 validation, one public solver call |
| `apps/virtual_bench/protocol.py` | Canonical server experiment digest and bounded terminal intensity/axis frame encoding |
| `apps/virtual_bench/server.py` | Exact local Host/Origin boundary, streamed request limit, private executor and lifetime gate, owned static assets, loopback CLI |

`ValidatedSubmission` owns the V0 specification. `simulate_submission` calls
`run_experiment(..., record_fields=())`; `encode_result` uses its actual terminal
field and original scalar stages. `ComputationGate` controls actual future
lifetime rather than the HTTP handler's lifetime. `OwnedStaticFiles` limits
access to the owned build and rejects link/path escapes.

## Frontend application

| File | Responsibility |
|---|---|
| `frontend/bench/src/contracts.ts` | Exact schema types, duplicate-key JSON reader, bounded HTTP body consumption, strict endian-aware complete-frame validation |
| `frontend/bench/src/presets.ts` | Three explicitly parameterized public-V0-based presets, returning fresh editable copies |
| `frontend/bench/src/state.ts` | Authoritative validated draft, transient invalid strings, edit/request generations, frozen submissions, stale/late result policy |
| `frontend/bench/src/mapping.ts` | SI-to-world presentation scales, even/odd pixel-cell geometry, UV centers and unclamped pixel picking |
| `frontend/bench/src/scene.ts` | Three.js scene/camera/picking/z rail, controlled GPU resource ownership and read-only rendering evidence |
| `frontend/bench/src/detector.ts` | Display-only RGBA, texture row reversal/settings, ordinary 2D result panel and explicit color limits |
| `frontend/bench/src/main.ts` | Traditional Chinese panels, browser event wiring, specification/result labels, raw selected-pixel readout |
| `frontend/bench/src/styles.css` | Local responsive presentation; no external font/asset requirement |
| `frontend/bench/index.html` | Local application entry |

`BenchController` exposes a frozen state snapshot and immediate subscriptions.
Its initial `validateInitial` performs validation only. `edit`/`replaceCandidate`
invalidate the current bench texture before waiting for validation.
`simulate` sets busy before the first await, freezes the submitted experiment,
requires matching UUID/specification/server digest and complete decoder success,
and never retries. A result completed after an edit may remain only in the
separate last-result panel. Presentation exceptions are recorded separately.

The intensity/x/y arrays are fresh float64 decoder-owned buffers. Presentation
consumers use them read-only; RGBA products cannot become scientific inputs.
Only read-only browser evidence hooks are exposed, without solver/state-edit
backdoors.

## Tests and evidence tools

| File | Independent acceptance focus |
|---|---|
| `tests/test_virtual_bench_adapter.py` | Exact V0 integration, validation-only and one-call behavior, input/resource failures |
| `tests/test_virtual_bench_protocol.py` | Independent byte/descriptor/scalar checks and frame bounds |
| `tests/test_virtual_bench_server.py` | ASGI/stream/boundary behavior and controlled worker/disconnect/exception lifetime |
| `tests/test_virtual_bench_architecture.py` | Scientific import/source boundary and local asset architecture |
| `frontend/bench/tests/state.test.ts` | Controlled promises/request counts, frozen snapshots, invalid edits, stale/late/malformed replies, view-failure separation |
| `frontend/bench/tests/mapping.test.ts` | Independent 3×4 and 2×5 physical/UV fixtures and explicit edge policy |
| `frontend/bench/tests/transport.test.ts` | Manually specified byte fixture, malformed frames, null semantics, finite/endian/shape/identity checks, bounded HTTP ownership |
| `frontend/bench/tests/detector.test.ts` | Original values, shared-range loss comparison, explicit texture configuration and intermediate gray |
| `frontend/bench/tests/bench.browser.spec.ts` | Served production application in installed Chrome, genuine WebGL/events/data readout and resource acceptance |
| `scripts/validate_v1_bench.py` | Real loopback HTTP, served asset hashes/source location, independent decoder and direct public V0 comparison |
| `scripts/v1_negative_controls.py` | Owned isolated deliberate mutations and actual detecting assertions |

The stdlib ASGI harness avoids adding a Python test dependency. It does not
replace real HTTP or browser acceptance. Test/evidence scratch belongs under
ignored `runs/` or scoped frontend generated directories.

## Toolchain, documentation and exact scope

The new frontend `package.json`, lockfile v3, `tsconfig.json`, `vite.config.ts`,
`vitest.config.ts` and `playwright.config.ts` declare the approved local tools,
production build and installed-Chrome tests. The root `.gitignore` modification
is limited to scoped frontend generated/cache rules. `pyproject.toml` records
existing Starlette/Uvicorn versions in a bench extra without refreshing the
installed distribution.

The five modified existing files are `.gitignore`, `pyproject.toml`, `README.md`,
`docs/roadmap.md` and `docs/milestones.md`. The 39 new files comprise eight backend
and Python tests, twenty frontend files, two scripts, six handoff documents and
three genuine screenshots. The approved total is 44 paths. Final inventory
verification is a separate required completion gate.
