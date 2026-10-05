# V2a code map

Recorded 2026-10-05. Direct imports use `ohlab.optics.interference`; existing
root/optics initializers and M0–V1 source/tests remain unchanged.

| Approved path | Responsibility |
|---|---|
| `src/ohlab/optics/interference.py` | Public two-port mixing, phase primitive, fixed frozen records, validated two-arm runner and sampled norm diagnostics |
| `tests/test_interference_model.py` | Scalar/tuple/result validation, diagnostics, darkness, contextual arithmetic, cap and ownership contracts |
| `tests/test_interference_primitives.py` | Independent complex coefficients, simultaneous inputs, inverse composition, exact compatibility, phase covariance and nonmutation |
| `tests/test_interference_analytic.py` | Equal-arm phases, near darkness, unequal-length carrier, independent asymmetric DFT, evanescence and blocked-arm budgets |
| `tests/test_interference_architecture.py` | Dependency isolation, no duplicate FFT/ASM, public propagation calls and reference independence |
| `scripts/validate_v2a_interference.py` | Reproducible independent coordinates/DFT/analytic reference measurements, tolerance margins, raw evidence and resource probes |
| `scripts/v2a_negative_controls.py` | Twelve exact isolated mutations, green baselines and scientific assertion failures; production hash preservation |
| `examples/two_path_interference.py` | Modest deliberate 64²/optional128² experiment; both outputs, every phase, original-input fractions and raw evidence |
| `scripts/generate_v2a_figures.py` | Headless three-figure rendering from actual evidence, independent of the numerical core |
| `README.md` | Direct-module usage, modest commands and boundaries |
| `docs/math_conventions.md` | Normative §3.18, version0.11 and accompanying change log |
| `docs/milestones.md` | Current V2a acceptance and dated evidence-backed V1 closeout |
| `docs/roadmap.md` | V2a → separately approved V2b → later richer physical models |
| Six `docs/handoffs/v2a/*.md` | Summary, map, mathematics, actual evidence, limitations and separate tutor context |
| Three `docs/handoffs/v2a/figures/*.png` | Ideal schematic/actual shared-scale outputs, sweep/norm residuals and independent reference/blocked control |

`run_two_arm` snapshots the input, supplies an exact zero second port, calls
`mix_balanced(...,matrix="B")`, existing public ASM once per arm with pad1,
`apply_uniform_phase` only on arm1, and `mix_balanced(...,matrix="B_dagger")`.
It measures the five ordered scalar pairs and returns only two final fields.
Records derive totals/residuals/ratios; no intermediate arrays or duplicate
aggregate records persist.

The public `ComplexField` constructor establishes fresh read-only ndarray
ownership for outputs; no internal data replacement or byte-backed hardening
is introduced. Private helpers only validate arithmetic/metadata and measure
the declared norm; they do not duplicate a propagation kernel.

Evidence directories under ignored `runs/` are regenerable local acceptance
artifacts, not a new persistence, load, replay or generic experiment schema.
Reproduction and source-location checks appear in [tests_and_evidence.md](tests_and_evidence.md).
