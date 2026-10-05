# V2a implementation summary

Recorded 2026-10-05. Accepted starting revision:
`303a312fcbddfc9abefcef8c1424ae374ef872fe`. This milestone delivers the approved
classical scalar monochromatic two-path numerical foundation. It is separate
from the V1 3D bench and from future V2b dual-output integration.

## Public behavior

Import these six APIs directly from `ohlab.optics.interference`:

- `mix_balanced(port_0, port_1, *, matrix="B"|"B_dagger")`: both ordered
  coherent fields; explicit ideal B or its inverse.
- `apply_uniform_phase(field, *, phase_rad)`: independent field multiplied by
  exp(i*phase), including a fresh copy at zero phase.
- `TwoArmSpec(*, arm_0_distance_m, arm_1_distance_m, relative_phase_rad)`:
  frozen finite nonnegative SI paths and signed radians.
- `TwoArmNorms(*, inputs, split, propagated, combiner, outputs)`: exactly ten
  scalar sampled norms with derived totals, signed stage differences and
  original-input fractions.
- `TwoArmResult(*, spec, outputs, norms)`: frozen, keyword-only, eq=False;
  two independently owned final fields and consistent scalar records.
- `run_two_arm(incident, *, spec)`: B, one existing public forward ASM per
  arm at pad1, phase only on arm1, B_dagger and both actual outputs.

Every pair is ordered (0,1). B has crossed +i/sqrt(2), its inverse crossed
-i/sqrt(2). Equal arms have bright port0 at zero extra phase and port1=-iW
at pi, where W=P(L)U. Input-normalized fractions are tau*cos²(phi/2) and
tau*sin²(phi/2), tau=N(W)/N(U); bare cos²/sin² assumes tau=1.

Exact canonical grid/wavelength compatibility and usable arithmetic are
required before shortcuts. Shape alone is insufficient; no resampling or
physical registration is inferred. Same-object inputs at both logical ports
are valid. The runner alone caps each axis at 512 before copies/FFT work.

Supported `ComplexField` constructors provide independent complex128 storage
with read-only stored arrays. There is no new byte-backed locking or internal
field mutation. Ten stage norms use sum(abs(U)²,float64)*dx*dy in
amplitude-unit²·m², not watts. Aggregate/residual/ratio properties derive from
those measurements. Zero input has None ratios; represented cancellation
residuals remain. Caller NumPy error settings are restored.

## Validation and protected scope

The unchanged baseline passed 1802 tests with one retained Windows symlink skip.
The first retained/new suite passed 2006 tests with the same skip. Independent
complex, asymmetric direct-DFT, unequal-carrier, common/relative phase,
near-dark, mixed evanescent and blocked-arm cases passed unchanged tolerance
bounds. Actual 64²/128² demos and bounded 512² resources ran. All three numerical
figures were visually inspected and regenerated with identical bytes.
The final isolated-control/restoration and post-control suite records are
reported in [tests_and_evidence.md](tests_and_evidence.md).

The exact approved inventory is 22 paths: 4 existing documentation modifications
and 18 new numerical/tests/scripts/example/handoff/figure files. All 207 protected
pre-existing tracked files and the installed-distribution versions, metadata
hashes and source locations are checked against the starting inventory.
Existing M0–V1 numerical source, tests/guards, package initializers, M5 contracts,
applications/frontend/lockfile, dependency declarations, settings/instructions
and historical handoffs remain unchanged.

Only an evidence-backed dated V1 publication closeout is added to the ledger;
its original precommit and separately executed browser results are preserved.
No browser/server/frontend operation is part of V2a acceptance.

## Handoff and publication boundary

See [code_map.md](code_map.md), [math_used.md](math_used.md),
[tests_and_evidence.md](tests_and_evidence.md),
[known_limitations.md](known_limitations.md), and
[tutor_context.md](tutor_context.md). Essential reproducible reference and
fault-control source is committed in the approved scripts; ignored raw evidence
is not a new persistence or replay format.

One commit with subject `feat(v2a): simulate coherent two-path interference`
and a normal origin/main push are approved after acceptance. Clean-postcommit
source-location and modest-demo smoke precede pushing; actual SHA/publication
outcomes remain in ignored evidence and the completion report, rather than
being predicted in this precommit snapshot. No new qualified-replay gate exists.

V2b, later reflection geometry, polarization, instruments, deployment and
hardware remain unstarted. Teaching and learning records remain separate.

## Final precommit acceptance

All twelve isolated deliberate faults failed their intended scientific assertions on valid records; each copied module was restored exactly and production inventory stayed unchanged. Final full-suite result: **2006 passed, 1 skipped in 254.93s (0:04:14)**. The unchanged Windows symlink skip remains. No scope expansion or tolerance relaxation was needed.

## Exact changed-file inventory

```text
README.md
docs/math_conventions.md
docs/milestones.md
docs/roadmap.md
src/ohlab/optics/interference.py
tests/test_interference_model.py
tests/test_interference_primitives.py
tests/test_interference_analytic.py
tests/test_interference_architecture.py
scripts/validate_v2a_interference.py
scripts/v2a_negative_controls.py
scripts/generate_v2a_figures.py
examples/two_path_interference.py
docs/handoffs/v2a/implementation_summary.md
docs/handoffs/v2a/code_map.md
docs/handoffs/v2a/math_used.md
docs/handoffs/v2a/tests_and_evidence.md
docs/handoffs/v2a/known_limitations.md
docs/handoffs/v2a/tutor_context.md
docs/handoffs/v2a/figures/fig01_unfolded_interferometer.png
docs/handoffs/v2a/figures/fig02_phase_sweep.png
docs/handoffs/v2a/figures/fig03_reference_and_controls.png
```
