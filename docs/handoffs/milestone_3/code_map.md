# Milestone 3 — Code map

Only four existing files and sixteen new files form the approved M3 change.

| Path | Responsibility |
|---|---|
| `src/ohlab/algorithms/__init__.py` | Explicit algorithm/result exports; no root API expansion |
| `src/ohlab/algorithms/gerchberg_saxton.py` | Strict M3 validation, result ownership, local exact-zero phase rule, per-solve public H construction and GS cycles |
| `tests/test_gerchberg_saxton.py` | Public contracts, ownership, initialization, zeros, domain, operator identities, declared fixtures/PNG and returned-field consistency |
| `tests/test_gerchberg_saxton_reference.py` | Independent scalar DFT iterations, feasible fixed points and analytic plane wave |
| `examples/synthesize_hologram.py` | Standalone strict-PNG-to-solver demonstration, explicit illumination and plotting |
| `scripts/probe_m3_evidence.py` | Reproducible fixture definitions, raw histories, arithmetic/operator/sampling and performance measurements |
| `scripts/make_m3_figures.py` | Regenerates exactly the three M3 illustrations |
| `README.md` | Current API orientation and runnable commands |
| `src/ohlab/__init__.py` | Module docstring only; executable imports, exports and version unchanged |
| `docs/math_conventions.md` | Normative §3.13 and version 0.6 change-log entry |
| `docs/milestones.md` | Dated M3 delivery and acceptance record; historical evidence preserved |
| `docs/handoffs/milestone_3/implementation_summary.md` | API, contracts, iteration and scope |
| `docs/handoffs/milestone_3/code_map.md` | This map |
| `docs/handoffs/milestone_3/math_used.md` | Projection/operator/power/residual derivation and references |
| `docs/handoffs/milestone_3/tests_and_evidence.md` | Exact commands/output, tolerances, controls, measurements and provenance |
| `docs/handoffs/milestone_3/known_limitations.md` | Model, numerical, evidence and product limits |
| `docs/handoffs/milestone_3/tutor_context.md` | Context for separate teaching without assuming learning status |
| `docs/handoffs/milestone_3/figures/fig01_single_plane_gs.png` | Default target, phase, actual reconstruction and raw history |
| `docs/handoffs/milestone_3/figures/fig02_seed_histories.png` | All predeclared seed histories for all three fixtures |
| `docs/handoffs/milestone_3/figures/fig03_rectangular_case.png` | Asymmetric grid example with unequal pitches |

The solver depends on existing `SamplingGrid`, `ComplexField`, validation
helpers and the public `angular_spectrum_transfer_function`. It performs no
disk access, PNG decoding or plotting. Existing static architecture/RNG guards
scan the new source module without needing guard changes. Image loading remains
in `ohlab.io.images`; target conversion remains in `ohlab.targets`.

The direct reference in the new tests uses explicit scalar analysis/synthesis
sums, manual signed bins and a scalar transfer phase. It must stay independent
of production FFT and transfer-function helpers. The test/evidence documents
name tolerances and mutation controls; those are bounded validation evidence,
not production algorithm alternatives.

Historical handoffs, all existing tests, numerical modules, loader, dependencies,
AGENTS.md, CLAUDE.md and old figures are outside the modification allowlist.
Ignored run files are reproducible local captures; essential source, parameters
and accepted results are preserved in the approved script and handoff.
