# V0 — Aligned sequential virtual optics

Prepared 2026-10-01 from accepted M7 baseline
`3b94a2262ae11f7d2316ac4fc5d168fa4881c859`. The dated
[milestone ledger](../../milestones.md) records acceptance/publication state;
[tests and evidence](tests_and_evidence.md) records actual validation. This
handoff does not invent an M5 run bundle or qualified-replay requirement.

## Supported experiment

One scalar monochromatic forward train in air, on one complete fixed
`SamplingGrid`: a Gaussian or uniform sampled source at z=0, zero or more
centered circular/rectangular apertures and ideal thin lenses, and one terminal
ideal observation plane. Absolute metres are authoritative. Stored component
positions must be nondecreasing; colocated entries retain list order. The
runner derives intervals, calls existing public M1 angular-spectrum propagation
with `pad_factor=1` exactly once per interval, then applies each thin element.
It also applies the final observation interval. No intermediate crop, hidden
padding, normalization or copied production propagation kernel is introduced.

The exact schema, scalar types, public signatures, IDs and selectors are
specified in [mathematical conventions §3.17](../../math_conventions.md#317-v0-aligned-sequential-optics--api-and-schema-contract).
The optical model is distinct from M3 equal-power synthesis, M5 configuration
and M7 pixel-coordinate target authoring.

## API and ownership

Import from `ohlab.optics`; existing package-root exports are unchanged:

```python
SequentialExperiment.from_dict(mapping)
experiment.to_dict()
sample_source(experiment)                  # ComplexField at z=0
apply_component(field, component)          # transmission only, no travel
run_experiment(experiment, record_fields=())
```

The immutable experiment owns nested source/component/plane records and an
ordered tuple. Exported dictionaries/lists are defensive copies. Real scalars
accept Python/NumPy integer and floating scalars, excluding booleans; scientific
parameters are finite binary64. Errors are informative `TypeError`/`ValueError`.
Unsupported models, unknown keys, duplicate identities, decreasing positions
and invalid physical dimensions fail explicitly.

`SequentialResult` holds its experiment, actual terminal complex field, all
scalar stage records, and at most four specifically requested intermediate
fields. Selectors are `source`, `before:<id>`, `after:<id>` and `observation`.
The terminal is always available; requesting its redundant recording is an
error. All stored field arrays have owned read-only complex128 storage.

At most 2048 samples per axis and 16 elements are supported. These are execution
limits, not sampling/accuracy guarantees.

## Physical and arithmetic behavior

Gaussian waist amplitude/radius/location/center/phase are explicit. Waist radius
means 1/e amplitude, equivalently 1/e² intensity. Uniform illumination fills
the periodic sampled window; a bounded illuminated area requires an aperture.
Apertures are inclusive center-sampled physical-metre 0/1 amplitude masks.
An ideal lens multiplies by `exp(-i*k*(x²+y²)/(2*f))`, with signed nonzero f,
and has no implicit aperture. Focusing occurs during subsequent travel.

Zero sources and fully blocked fields are valid. Sampled norm is
`sum(abs(U)**2)*dx*dy`, labelled amplitude-unit²·m², not watts. Stage differences
are signed and unclamped; undefined incident-zero ratios have no numeric value.
The ideal observation returns U and |U|² without camera electronics.

Overflow, invalid arithmetic and unusable derived geometry fail explicitly.
Documented decaying tails can round to zero locally without changing caller
error settings or M1's forward evanescent policy. A nonzero field whose complete
sampled norm underflows to zero is rejected. See [math used](math_used.md).

## Standalone demonstration and evidence

`examples/sequential_optics.py` executes six modest specification-driven cases:
one Gaussian free-space case, four lens observation positions, and one explicit
aperture/lens case. It prints actual configurations, norms, signed aperture
effects, independent unbounded-Gaussian comparisons where applicable, and
separate shipped runtime/memory measurements. The clipped Gaussian is not
misrepresented as an unbounded ABCD reference.

`scripts/validate_v0_optics.py --full` preserves independent direct-DFT,
sign-matched Gaussian and bounded continuous Fresnel references and sequential
window/pitch convergence. `scripts/v0_negative_controls.py` isolates deliberate
faults. `scripts/generate_v0_figures.py` consumes actual full-validation evidence,
recomputes the modest demonstration and produces the three approved numerical
figures. No UI/server/browser or 3D viewer is launched.

Existing M0–M7 numerical modules/tests, apps, root exports, dependency and
configuration declarations, instructions, M5 contracts and historical handoffs
are protected. V1/V2/V3, hardware, new storage and target-editor enhancements are
outside this milestone. Tutor material supports the separate teaching
conversation and asserts no course or lesson completion.
