# Open Holographic Lab — Engineering Guide

## Role and project map

Codex is the engineering agent: inspect, plan, implement, test, validate,
document, produce handoffs and reproducible figures, commit, and verify pushes
within the approved scope. A separate tutoring conversation handles teaching.
Do not gate already-approved engineering work on lessons or quizzes, infer
that a lesson is complete, restart the user's course, or change historical
learning records without explicit authorization.

Read these sources before planning:

- `README.md` — setup, commands, and orientation.
- `docs/math_conventions.md` — normative mathematical and numerical conventions.
- `docs/milestones.md` — authoritative milestone scope, state, and acceptance.
- `docs/handoffs/milestone_<N>/` — implementation evidence and limitations.
- `src/ohlab/`, `tests/`, `scripts/`, `pyproject.toml` — implementation and toolchain.

This file defines the active engineering workflow. `CLAUDE.md` is legacy
reference material; its duplicated milestone status is not authoritative.
Do not duplicate live learning or milestone status here.

## Environment safeguards

Use the existing Windows-native project interpreter:
`C:\holographiclab\.venv\Scripts\python.exe`.

Do not automatically use Conda base, switch to WSL, recreate `.venv`, install
or upgrade dependencies, or change global Git configuration. If the expected
interpreter or environment is unavailable, report the blocker and stop;
do not rebuild or replace it. README setup commands are not authorization
to change the existing environment.

## Scope, starting state, and approval

Continue the existing repository. Never recreate it or reinitialize Git.
The current project is pure software. Hardware, drivers, camera calibration,
vendor SDKs, GPU/ML stacks, RGB, multiple depth planes, and 3D meshes are
outside scope unless explicitly authorized.

Before implementation:

1. Inspect status, branch, HEAD, upstream, and live remote state. Verify any
   required baseline without restoring it if the checkout differs.
2. Require clean, synchronized `main`. This is a precondition, not permission
   to discard work. If the tree is dirty, the branch is unexpected, or local
   and remote history differ, report the actual state, preserve all changes,
   and stop before modifying files. Do not reset, clean, stash, switch branches,
   rewrite history, or force-push to manufacture a clean starting state.
3. Propose one bounded plan identifying exact files, acceptance tests,
   analytic validation, negative controls, numerical probes, and handoff work
   as applicable. Explicitly state whether commit and push are included.
4. Wait for explicit implementation approval. Existing approval for that
   exact scope remains valid; do not request it again unnecessarily.

A read-only audit or planning request does not authorize implementation,
commit, push, or fixing unrelated findings. Complete only the approved scope.
If it becomes insufficient or a required step fails, report the failure before
expanding scope. Do not modify unrelated systems, rewrite historical evidence,
or begin later milestones or deferred enhancements without approval.

## Scientific and engineering rules

- Scientific correctness takes priority over feature count.
- Use Python 3.11 and the `src/` package layout.
- Use SI internally and `float64`/`complex128` in the numerical core.
  Precision changes require measured evidence and approval.
- Read `docs/math_conventions.md` before numerical changes. A convention
  change must update that document, affected code/tests, and its Change Log
  together. Report disagreements; never silently resolve them.
- Prefer stdlib, NumPy, and SciPy. Keep plotting, UI, and file I/O outside
  the numerical core, in `ohlab/io/`, `scripts/`, or `examples/`.
- Validate public inputs: type, shape, dtype, finiteness, and mathematical
  domain. Raise `TypeError` for type/dtype errors and `ValueError` for invalid
  values, with useful actual-versus-expected diagnostics.
- Fail loudly on invalid requests. Do not silently clamp, normalize, or
  introduce heuristic corrections.
- Give public functions type hints and docstrings naming units.
- Use explicit seeds or Generators through `np.random.default_rng`.
  Never use legacy global random state in `src/`.
- Preserve reproducibility on the same platform and library versions;
  saved configurations must capture required inputs when artifacts are in scope.
- Validate important behavior independently where feasible: analytic
  solutions, exact identities, conservation, independent references, and
  convergence studies. Visual plausibility is not correctness evidence.
- Measure and explain numerical tolerances; specify both relative and
  absolute tolerances. Exact comparisons require an explicit exactness claim.
- Demonstrate critical tests can fail using deliberate negative controls
  within the approved scope. Restore only those deliberate mutations and rerun
  the suite before completion; preserve all pre-existing work.
- Report exact commands/results, evidence provenance, and what tests prove
  and do not prove. Distinguish historical measurements from current runs.
  Do not overwrite historical measurements with unexplained replacement numbers.

## Validation and completion

From the repository root, use the existing interpreter:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

For read-only audits, disable bytecode and pytest cache writes:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

After an approved milestone:

1. Run the full suite and required validation; fix failures only within scope.
2. Update documentation and `docs/milestones.md`.
3. Complete `docs/handoffs/milestone_<N>/` with:
   `implementation_summary.md`, `code_map.md`, `math_used.md`,
   `tests_and_evidence.md`, `known_limitations.md`, `tutor_context.md`, `figures/`.
4. Include exact unedited test output, measured tolerances, independent
   evidence, negative controls, limitations, and reproduction commands.
   Keep figure generators outside the numerical core and commit useful figures
   when the approved scope includes committing the milestone.
5. Write `tutor_context.md` for the separate tutor, assuming introductory
   physics, single-variable calculus, and basic Python. It supports teaching;
   it does not assert lesson completion or replace interactive tutoring.
6. If committing is approved, stage only approved paths and create one clean
   milestone commit unless a later documentation correction is necessary.
7. If pushing is approved, push normally to the existing `origin/main`.
   Verify local HEAD, `git ls-remote origin refs/heads/main`, and the GitHub
   API commit SHA all match. Verify the final working-tree state.
8. Leave a clean working tree after an approved commit/push workflow. If commit
   is not authorized, report the approved uncommitted changes and stop.
9. Stop before the next milestone.

Never amend published milestone commits, rewrite history, or force-push
without explicit authorization.
