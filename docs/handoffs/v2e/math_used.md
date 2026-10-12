# V2e mathematical and numeric contract

V2e adds no optical formula, solver, propagation rule or mathematical
convention. [math_conventions.md](../../math_conventions.md) remains normative.
Documents record complete inputs to the three existing bench models, and
validation constructs specifications without sampling a field or applying an
optical element. A validated/restored setting is not a numerical result.

## Scientific values carried by a document

Lengths, wavelengths, pitches, radii and positions are SI metres; phases,
element axes and retardances are radians. Source amplitude and the real/imaginary
coefficient parts retain the existing arbitrary field scale. Grid counts,
schema versions and readout indices retain integer identity and mode bounds.
The full nested schemas and domains are in
[implementation_summary.md](implementation_summary.md).

Sequential settings describe the existing scalar aligned forward train: one
sampling grid, a source at z=0, ordered apertures/lenses and a downstream
observation plane. Equal component positions retain stored order. Negative
nonzero focal length is supported; longitudinal component/observation positions
remain nonnegative. Existing checks reject unusable derived binary64 geometry.

Two-path settings describe the existing ideal unfolded scalar two-arm model,
including both nonnegative arm distances and the independent unwrapped extra
arm-1 phase. The splitter/recombiner, ports and zero second input remain fixed.
The document does not infer physical mirror displacement, reflection frames,
additional carrier phase or propagation from the drawn geometry.

Polarization settings retain the existing scalar source plane, arbitrary
complex x/y coefficients, ordered ideal Jones actions and one readout index.
No coefficient normalization or common-phase reset occurs. Gaussian waist
position is fixed internally to zero and is omitted from this mode's schema.
All actions occur at one reference plane; illustrated spacing has no optical
effect. QWP/HWP are numeric retardances, not extra document element types.

## Decimal input, binary64 and exactness

The authoritative server uses the existing finite binary64 validators. JSON
numbers are not arbitrary-precision measurements: original decimal spelling
is discarded. A real field written as integer token `9007199254740993` rounds
once to binary64 `9007199254740992.0`. Integer count/version/index fields retain
strict integer type and their small existing ranges. Integer tokens beyond
finite binary64 magnitude reject at the raw document boundary.

The new boundary rejects a nonzero decimal coefficient that rounds to zero,
for example `1e-999`; it accepts an explicit zero token and permits the minimum
subnormal token `5e-324` where the field domain allows it. Overflow, nonfinite
constants and booleans in numeric fields reject. These are document policies;
the old parser and simulation endpoint domains are unchanged.

For supported finite nonzero values, preservation is exact binary64 identity,
not a tolerance comparison. Correspondence checks require the same value at
every numeric leaf across raw validation, browser preparation and final
validation. Ordered lists, IDs, readout indices, model/version and metadata also
must match. A valid second response alone does not excuse numeric drift.
Changing one editor field leaves every other authoritative loaded leaf intact.

An unchanged displayed string is not a reconstruction source. For example,
`0.020000000000000004` m may display as `20` mm, whose reparse would produce
`0.02` m. The binding remembers field identity, editor generation, painted text
and original SI value; unchanged cosmetic events preserve that value. Two
imports with identical visible text but different exact numbers must retain
their own values. Actual edits still use the existing unit conversion and
public validation for that edited field.

Negative-zero bit preservation is not supported by the browser document flow.
The existing two-path freezer uses +0 for phase zero; polarization preparation
uses +0 for numeric zeros; ordinary `JSON.stringify` writes any remaining -0
as 0. Sequential has no new zero walker. Other finite nonzero values are neither
wrapped, snapped, clamped nor normalized. The first raw-valid Python canonical
document can differ from the final browser-prepared canonical document only
under these existing zero semantics and ordinary numeric spelling. Tests must
not demand equal first/final bytes or hashes in legitimate signed-zero cases.

Only the final prepared canonical bytes are the import/export fixed point.
Reimport, unchanged application and reexport must reproduce those bytes on the
tested supported path. This does not preserve arbitrary original whitespace,
key order or decimal text, and it is no cross-version/platform guarantee.

## Three distinct identities

Let C be the complete canonical document bytes and E the existing mode-validated
SI experiment definition. Evidence may compute `SHA256(C)` to compare files.
The HTTP header instead uses the mode's unchanged `experiment_digest(E)`:
sorted compact Python JSON of E, `ensure_ascii=True`, no nonfinite values,
encoded as UTF-8 and hashed with SHA256. The complete canonical file uses
two-space indentation, `ensure_ascii=False` and a final LF instead.

The scientific digest covers every scientific input, including IDs/order and
readout where applicable. It excludes document wrapper, metadata and document
formatting. Changing only a title therefore changes file bytes without changing
the experiment digest. Different legal first/final zero representations may
change the existing digest. Only the final digest is installed after direct
equality with ordinary validation has been demonstrated for each mode.

A browser operation generation is a third, temporary identity for cancellation
and attachment. Later explicit simulations create fresh normal request IDs.
None of these hashes/generations is a signature, authorship claim, simulation
success, saved-result provenance or M5 qualified replay.

## Validation claims

Document tests assert exactness on the supported same-platform, identical-input
path. Independent API/browser acceptance compares complete returned arrays,
scalars and samples against retained original results and direct public APIs;
it must investigate any mismatch without silently adopting a tolerance.
Rounded metric labels and screenshots cannot prove this numeric claim.
Measured outcomes and limitations are in
[tests_and_evidence.md](tests_and_evidence.md); document correctness alone adds
no general optical-accuracy or convergence certification.
