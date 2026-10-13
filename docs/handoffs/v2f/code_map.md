# V2f code map

The exact API, checkpoint fields, domains and exceptions are in
[implementation_summary.md](implementation_summary.md) and normative
math_conventions.md3.20. Acceptance is separately recorded in
[tests_and_evidence.md](tests_and_evidence.md).

| New path | Responsibility |
|---|---|
| src/ohlab/optics/polarized_interference.py | Eight-name numerical API, complete request/boundary validation, owned fixed-topology composition, measured Jones checkpoints and bounded action histories |
| tests/test_polarized_interference_primitives.py | Ordered four-component/two-port mixing, compatibility, complete preflight, phase/domain/caller settings and independent ownership |
| tests/test_polarized_interference_model.py | Frozen records, checkpoint/history connections, original denominators, cap and complete request checks, derived failures and result consistency |
| tests/test_polarized_interference_analytic.py | A–F, actual complex fields, scalar reductions, complex-first overlap, analyzer/loss/order/carrier/weak/direct-sum references |
| tests/test_polarized_interference_architecture.py | Public reuse, no optional UI/I/O imports/private helpers/second FFT or kz engine, no initializer reexports, exact call ordering |
| scripts/validate_v2f_interference.py | Independent literal matrices/Jones coefficients/finite propagation sums and actual shipped-function discrepancies/resources |
| scripts/v2f_negative_controls.py | Isolated new-module composition, reused-dependency behavior, demonstration and reference self-check mutations; intended detecting assertions and exact restoration hashes |
| examples/polarized_two_path_interference.py | Standalone32/64-grid classical demonstration; separate raw/analyzed fields and all17 phase markers |
| scripts/generate_v2f_figures.py | Three actual numerical figures and repeatable rendering outside the core |

## Public dependency boundary

New core -> public ComplexField/JonesField constructors and SamplingGrid;
public interference.mix_balanced/apply_uniform_phase; public scalar
propagate_angular_spectrum; public polarization.apply_linear_polarizer and
apply_linear_retarder. No old private helper is imported. Local cheap domain
arithmetic checks do not compute a transfer-function mesh or FFT.

The two mixers each call scalar mixing for matching x ports and matching y
ports. Four public ASM calls explicitly pass pad_factor=1, including zero
distance. Terminal action tuples are applied in supplied order; arm1 common
phase is applied to both components. Only two final Jones fields and scalar
records persist in the result. Downstream analyzers live in the example/tests.

## Protected boundary

Every existing numerical module/test, old architecture guard, initializer,
application, protocol, V2e document validator, M5 bundle, dependency/lockfile,
instruction and historical handoff remains protected. The four approved
documentation modifications add V2f and a dated existing-record V2e closeout.
The only tracked creations are the18 approved new paths. V2g is separate and
must explicitly plan interactive transport/resources and document compatibility.

Fresh raw acceptance outputs live under runs/v2f_acceptance_20261013_01 and
do not define a public persistence, result replay or qualified-replay format.
