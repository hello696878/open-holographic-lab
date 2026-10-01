# V0 — Code map

All paths are relative to the repository root. Public numerical entry points
are in `ohlab.optics`, without modifying `ohlab` root exports.

| File | Responsibility |
|---|---|
| `src/ohlab/optics/model.py` | Frozen source, component and observation records; exact tagged schema; IDs, order, finite SI/domain/resource/derived-geometry checks; defensive conversion |
| `src/ohlab/optics/elements.py` | Gaussian/uniform source sampling and centered aperture/lens transmissions; local arithmetic policy; owned arrays; no free-space propagation |
| `src/ohlab/optics/simulation.py` | Ordered interval orchestration using public M1 ASM; actual terminal field; scalar norm/stage records and bounded explicit stage recording |
| `src/ohlab/optics/__init__.py` | Bounded public submodule exports |
| `tests/test_optics_model.py` | Schema/type/domain/order/identity limits, immutable nested ownership and fresh exports |
| `tests/test_optics_elements.py` | Hand masks, anisotropic SI geometry, lens action/sign/intensity, source and arithmetic edge cases |
| `tests/test_optics_simulation.py` | Exact interval/stage behavior, terminal identity, zero norm, recording independence and complete-train correctness |
| `tests/test_optics_analytic.py` | Independently constructed direct DFT, full complex Gaussian references and actual waist behavior |
| `tests/test_optics_sampling.py` | Declared sampling/convergence checks and bounded continuous aperture comparison |
| `tests/test_optics_architecture.py` | No UI/I/O/plotting/optional dependency imports in new optics core; no replacement production FFT/kz path or changed root exports |
| `examples/sequential_optics.py` | Actual SI-spec-driven 512² example; six modest cases, reference comparison, norm/loss report and independent runtime/tracing/Windows memory measurements |
| `scripts/validate_v0_optics.py` | Preserved independent coordinate/frequency/DFT/transmission/update references; complex Gaussian and Fresnel references; required full sequential convergence; diagnostic measurements |
| `scripts/v0_negative_controls.py` | Owned isolated faults and independently detecting test assertions; production restoration/hash evidence |
| `scripts/generate_v0_figures.py` | Three actual numerical figures; no planning-table fallback; complete evidence required for aperture convergence figure |

The existing `SamplingGrid`, `ComplexField` and public
`propagate_angular_spectrum` are reused without editing them. Plotting, resource
inspection and evidence-file output stay in example/scripts, outside the core.
Neither a new disk schema nor M5 persistence/replay integration is added.

## Documentation and figures

The four modified documentation paths are `README.md`, `docs/roadmap.md`,
`docs/milestones.md` and `docs/math_conventions.md`. The math contract adds V0's
source/lens/schema/norm/arithmetic rules while retaining existing propagation
conventions. The dated M7 publication closeout cites existing postcommit
evidence without overwriting the historical precommit record.

The six documents here are implementation summary, code map, mathematics,
tests/evidence, known limitations and separate tutor context. Three figures:

- `figures/fig01_gaussian_free.png`: free Gaussian fields/profiles and independent complex discrepancy.
- `figures/fig02_lens_waist.png`: actual lens observations, Gaussian waist shift and explicit aperture loss.
- `figures/fig03_aperture_convergence.png`: all five measured window/pitch cases and separate sampled-area bias.

The exact approved tracked inventory is 27 paths: four numerical, six tests,
four example/evidence tools, four documentation edits, six handoff documents and
three figures. Publication/scope verification is in
[tests and evidence](tests_and_evidence.md). No later-stage renderer is included.
