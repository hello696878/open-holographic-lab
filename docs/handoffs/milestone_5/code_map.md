# Milestone 5 — Code map

The approved scope is exactly seventeen tracked paths. No existing numerical
implementation, test, architecture guard, package initializer, dependency,
`.gitignore`, engineering instruction or historical handoff is modified.

## I/O boundary

`src/ohlab/io/config.py` exposes `RunConfig`. Private schema validators enforce
exact nested keys, JSON-compatible scalar types, fixed algorithm/contract,
initialization exclusivity and per-metric parameters. Canonical JSON bytes
provide immutable ownership; `to_dict()` provides a defensive deep copy.
Private JSON helpers implement deterministic writing and duplicate-key/
nonstandard-constant rejection. This module performs no file access or optics.

`src/ohlab/io/artifacts.py` exposes four functions:

| Function | Responsibility |
|---|---|
| `run_and_save_bundle` | Capture owned inputs; call public M2/M3/M4; write, validate and publish one coherent run |
| `verify_run_bundle` | Check exact inventory, all hashes, schema and typed array structure without solving |
| `load_run_bundle` | Return owned read-only arrays and metadata from those same verified snapshots |
| `replay_run_bundle` | Qualify independently obtained current provenance, then recompute and compare exact outputs/metrics when permitted |

Private helpers group provenance/environment collection, conditional roles,
input snapshots, existing public-function dispatch, NPY validation, manifest
validation and transaction handling. `_write_file(path, data, owned)` registers
a cleanup path only after exclusive creation succeeds. `_validated_contents`
serves staged verification and public readers without exposing a public
skip-validation option. `_publish` adds only the bounded Windows access-denial
rename retry described in the implementation summary; it never retries an
existing destination or adds an overwrite/copy fallback. The internal
return-record classes are not public
constructors; their attribute contracts are in the
[implementation summary](implementation_summary.md).

No second RNG, propagation kernel, solver or metric formula is introduced.
PNG checks delegate to `ohlab.io.images`; Pillow remains confined to that
existing decoder module. The existing architecture guard already permits
I/O modules to import the core, while forbidding the reverse direction.
No root re-export or guard relaxation is needed.

## Tests, example and figures

`tests/test_run_config.py` checks schema and nested ownership, scalar
serialization and invalid settings. `tests/test_run_artifacts.py` checks
capture, format/integrity, conditional inventory, transaction failures,
qualification, exact replay and fresh-process relocation. These are the
only new test files. Existing tests remain unchanged. The reproducible
negative-control driver, exact output and finite coverage claims belong in
[tests and evidence](tests_and_evidence.md), not in a new production framework.

`examples/run_bundle.py` makes a deterministic temporary grayscale PNG under
ignored `runs/`, declares uniform per-target illumination and a fixed mask,
then saves, verifies, loads and replays. Its `_detect_source_revision` is an
example-layer optional Git detector anchored to the imported package.
`--output` selects a new destination; it is not an M6 application CLI.

`scripts/make_m5_figures.py` uses matplotlib's Agg backend to create exactly
two explanatory diagrams. It does not execute the solver, export bundle
previews or substitute images for numerical evidence.

## Exact file inventory

| Path | Action |
|---|---|
| `README.md` | Modify: M5 imports, usage and interpretation |
| `docs/math_conventions.md` | Modify: qualified reproducibility and §3.15 contract |
| `docs/milestones.md` | Modify: scoped M5 delivery and acceptance evidence |
| `src/ohlab/io/config.py` | Create |
| `src/ohlab/io/artifacts.py` | Create |
| `tests/test_run_config.py` | Create |
| `tests/test_run_artifacts.py` | Create |
| `examples/run_bundle.py` | Create |
| `scripts/make_m5_figures.py` | Create |
| `docs/handoffs/milestone_5/implementation_summary.md` | Create |
| `docs/handoffs/milestone_5/code_map.md` | Create |
| `docs/handoffs/milestone_5/math_used.md` | Create |
| `docs/handoffs/milestone_5/tests_and_evidence.md` | Create |
| `docs/handoffs/milestone_5/known_limitations.md` | Create |
| `docs/handoffs/milestone_5/tutor_context.md` | Create |
| `docs/handoffs/milestone_5/figures/fig01_run_bundle_anatomy.png` | Create |
| `docs/handoffs/milestone_5/figures/fig02_integrity_and_replay.png` | Create |

Generated bundles and local evidence captures stay ignored. Essential commands,
parameters and accepted results are preserved in the handoff. M6 is not started.
