# V2c code map

Recorded 2026-10-06. The approved scope contains exactly 22 paths: four
documentation modifications and eighteen creations. Direct imports use
`ohlab.optics.polarization`. Existing root/optics initializers, scalar numerical
code/tests/guards, V0/V2a schemas, web protocols, frontend/lockfile, Streamlit,
M5 replay, dependency declarations and engineering instructions are protected.

| Approved path | Responsibility |
|---|---|
| `src/ohlab/optics/polarization.py` | Four direct-module public symbols, `JonesField.from_scalar`, exact common-plane compatibility, public-constructor ownership, ideal amplitude projection/retardance and combined diagnostics |
| `tests/test_polarization_model.py` | Frozen keyword-only representation, same-object snapshots, independent intensity/norm, arbitrary coefficients, exact metadata, common/relative phase, ratio four and zero-shortcut validation |
| `tests/test_polarization_primitives.py` | Scalar families, invalid arguments, identity copies, caller settings, usable area/norm, tail retention, strict ratio underflow and absence of propagation geometry limits |
| `tests/test_polarization_analytic.py` | Literal selected complex fixtures, expanded asymmetric references, thirteen Malus points, five Decimal weak cases, public-basis unitarity, inverse composition, contraction/conservation and noncommuting order |
| `tests/test_polarization_architecture.py` | Fresh-process optional-dependency/I/O isolation, bounded public API, no numerical propagation/plotting/I/O/random/global-error-setting path |
| `examples/jones_polarization.py` | Default64/alternate32 actual demonstrations, complete arrays/diagnostic rows, actual unnormalized center-sample ellipse points and separately scoped shipped runtime/memory observations |
| `scripts/validate_v2c_polarization.py` | Preserved literal/expanded references, bounded direct-angle Decimal oracle, declarations/tolerances, independent intensity/norm/ratio checks, measured discrepancies and source/runtime provenance |
| `scripts/v2c_negative_controls.py` | Fifteen concrete scientific variants in owned copies, passing originals, actual assertion failures, exact restoration and unchanged production hashes |
| `scripts/generate_v2c_figures.py` | Headless three-PNG rendering from passed64 demo evidence, source/hash checks, byte-identical actual-array recomputation and explicitly labelled independent overlays |
| `README.md` | Direct-module usage, modest interpreter commands, selected conventions and bounded scope |
| `docs/math_conventions.md` | New normative §3.19 and accompanying Change Log entry; existing scalar conventions preserved |
| `docs/milestones.md` | Current V2c acceptance record and dated V2b publication read-back without new browser validation |
| `docs/roadmap.md` | V2c numerical foundation -> separately approved V2d 3D polarization -> later interference, reflected frames and instruments; persistence remains separate |
| `docs/handoffs/v2c/implementation_summary.md` | Public behavior, approved representation, scope and dated implementation/acceptance boundaries |
| `docs/handoffs/v2c/code_map.md` | This exact path map and execution/data boundaries |
| `docs/handoffs/v2c/math_used.md` | Basis/time/reference-phase derivation, diagnostics, independent fixtures/tolerances and primary-reference translation |
| `docs/handoffs/v2c/tests_and_evidence.md` | Exact commands/output, measurements, weak signals, fault detections/restoration, resources and publication boundaries |
| `docs/handoffs/v2c/known_limitations.md` | Physical, numerical, storage, demonstration and evidence limits |
| `docs/handoffs/v2c/tutor_context.md` | Background for the separate tutor without asserting learning progress |
| `docs/handoffs/v2c/figures/fig01_malus_and_loss.png` | All actual Malus points, independent analytic overlay and crossed/middle-polarizer loss diagnostics |
| `docs/handoffs/v2c/figures/fig02_retarders_and_components.png` | Actual selected complex QWP/HWP components, norm conservation and independent discrepancy evidence |
| `docs/handoffs/v2c/figures/fig03_polarization_ellipses.png` | Unfitted real-time vectors at a declared nonzero sample, equal component axes, y-down and dimensionless phase direction |

## Numerical flow and ownership

`JonesField.__post_init__` validates each existing public scalar component,
the canonical grid, exact compatibility and usable pixel area. It independently
snapshots both components with public `ComplexField(...)`, checks combined
sampled norm, then stores the snapshots. No existing field's internal data is
replaced. Private helpers validate metadata/storage, calculate the approved
diagnostics and construct outputs through public constructors; they are not
a general numerics framework or propagation implementation.

`from_scalar` validates the scalar and both coefficients, multiplies the
actual complex envelope independently by each arbitrary finite coefficient,
and constructs a Jones pair. A zero-output case still performs required
validation; it does not require the unused scalar norm to be usable.

`apply_linear_polarizer` computes the axis projection `c*Ux+s*Uy` and
returns its actual x/y components `(c*projection,s*projection)`.
`apply_linear_retarder` converts into axis/perpendicular components, gives
only the perpendicular component phase `exp(i*delta)`, and converts back.
Exact +/-0 delta returns independent byte-preserving copies after validation.
The demonstrated operation order is expressed by nested public calls, without
a new sequence runner or graph/schema.

`intensity` and `sampled_norm` revalidate component storage and calculate
`I=abs(Ux)**2+abs(Uy)**2`, `N=sum(I,float64)*dx*dy` left-to-right. Norm
viability is combined: a tiny y tail beside usable x is permissible.
`transmission_ratio` validates both fields and exact shared metadata, then
derives transmitted/incident norm without causal certification, clamping or
an epsilon denominator. Exactly zero incident norm returns `None`.

## Evidence and presentation boundaries

The validator's expanded coefficients differ from production's axis-projection
calculation. Expected arrays and literal complex fixtures never call production
matrix/application helpers. Its weak oracle uses direct 80-digit Decimal
sin/cos series at the exact actual binary64 angle, not `epsilon**2`.
Matrix unitarity is observed through public x/y basis-field actions; no new
public matrix constructor is exposed.

The demo saves actual complete component/intensity arrays for every declared
Malus and weak case plus actual ellipse points. These ignored JSON/NPZ records
are reproducible acceptance evidence, not a load/save API, M5 bundle or generic
experiment-persistence schema. The figure script checks current source hashes
and recomputes saved arrays exactly before plotting; that repeatability check
is separate from independent scientific tolerance checks.

The negative-control runner copies production and selected new assertions into
fresh owned directories. Fourteen variants mutate the copied core calculation;
the order variant changes the copied explicit composition while preserving its
independent literal expected field. It distinguishes scientific `AssertionError`
from setup/import/validation failures and restores copied affected bytes exactly.
Production hashes must match before and after the run.

Plotting, file writing, subprocess orchestration and process-memory observations
remain in scripts/examples, outside the numerical core. No frontend, browser,
server, hardware, package or settings action is part of this V2c execution flow.
Clean-postcommit source/demo checks and publication outcomes are separately
recorded; they are pending in the initial precommit handoff snapshot.
