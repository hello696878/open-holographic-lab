# V2c implementation summary

Recorded 2026-10-06. Accepted starting revision:
`886cdac549dcd4373be7d24f9f2211af03659371`. V2c delivers deterministic,
fully coherent monochromatic Jones fields and ideal uniform thin-element
actions at one stipulated common transverse reference plane.

This is a precommit implementation record. Focused tests, independent
validation, both standalone demonstrations, all isolated scientific controls,
the complete restored suite, protected-file/environment verification and
figure inspection/regeneration have passed. Exact evidence is in
[tests_and_evidence.md](tests_and_evidence.md). Clean-postcommit checks and
publication remain subsequent gates, recorded in the final completion report.
No future publication result is predicted here.

## Exact public API and ownership

Import directly from `ohlab.optics.polarization`; existing package initializers
and exports are unchanged:

```python
JonesField(*, x: ComplexField, y: ComplexField)
JonesField.from_scalar(scalar: ComplexField, *,
                       x_coefficient: complex,
                       y_coefficient: complex) -> JonesField
apply_linear_polarizer(field: JonesField, *,
                       axis_angle_rad: float) -> JonesField
apply_linear_retarder(field: JonesField, *,
                      axis_angle_rad: float,
                      retardance_rad: float) -> JonesField
transmission_ratio(incident: JonesField,
                   transmitted: JonesField) -> float | None
```

`JonesField` is frozen, keyword-only and `eq=False`; equality is identity
comparison. Its properties are `grid`, `wavelength_m`, `shape`, `intensity`
and `sampled_norm`. Both components require the canonical `SamplingGrid`
class, exactly equal `ny/nx/dy/dx`, matching array shapes, equal positive finite
vacuum wavelength, native finite complex128 data and usable positive pixel
area. Shape alone is insufficient. Matching metadata cannot establish physical
alignment; the common plane and x/y basis are explicit model assumptions.

Each component is independently snapshot through the supported public
`ComplexField` constructor. Same-object x/y inputs are valid. Stored native
complex128 arrays are read-only and share no numerical storage with caller
data or each other. Operations return new independently owned component
arrays, including exact retardance identities and dark outputs. Derived
intensity is a fresh writable native float64 array. This is the existing
reversible ndarray write-flag contract, without byte-backed storage or a
promise of irreversible immutability.

`from_scalar` keeps `Ux=cx*U` and `Uy=cy*U`, using arbitrary finite complex
coefficients. It neither normalizes coefficients nor resets common/relative
phase. The mathematical intensity/norm factor is `abs(cx)**2+abs(cy)**2`,
which may represent gain or loss. Both zero coefficients and zero scalar
fields are valid after required validation. A finite scalar whose own norm
is unusable may produce a valid exact-zero Jones field with zero coefficients.

Coefficients accept Python `int`, `float`, `complex` and NumPy integer,
floating and complex-floating numeric scalars. Angles accept Python
`int`/`float` and NumPy integer/floating numeric scalars. Python/NumPy booleans,
temporal scalars including `np.timedelta64`, strings, arrays and other objects
are rejected. Conversion is to finite binary64 components. Wider coefficient
precision may lose negligible tails; a nonzero wider angle rounding to zero
is rejected. Type errors raise `TypeError`; unusable values raise contextual
`ValueError`.

## Optical and diagnostic behavior

Retain `exp(-i*omega*t)`. The algebraic basis is
`e_theta=(cos(theta),sin(theta))`,
`e_perp=(-sin(theta),cos(theta))`. Increasing axis angle turns from +x
toward +y, appearing clockwise in the repository's y-down display. Element
coordinates use `R.T` and conversion back uses `R`, with these basis columns.

The polarizer applies `P=e_theta*e_theta.T` in complex amplitude. The
retarder applies `W=e_theta*e_theta.T+exp(i*delta)*e_perp*e_perp.T`.
The selected axis has reference phase zero; its perpendicular gets +delta.
QWP and HWP use delta=pi/2 and pi through the generic retarder. Returned
complex phase is preserved under this reference; there is no
`exp(-i*delta/2)` compensation, phase fitting or component phase reset.
These are supplied ideal parameters at the wavelength, without material
thickness/dispersion or absolute plate-path phase prediction.

Nonzero angles are evaluated as supplied, without wrapping/snapping.
Floating pi/2 and pi retain ordinary residuals. Exact +/-0 retardance returns
byte-preserving independent component copies after full validation. Other
operations do not promise signed-zero bit preservation.

Total intensity is `abs(Ux)**2+abs(Uy)**2`, in amplitude-unit^2, without
a scalar x/y interference cross term. An analyzer first projects the actual
vector. Sampled norm is `sum(I,dtype=float64)*dx*dy`, evaluated left-to-right,
in amplitude-unit^2*m^2, not watts. Polarizer loss remains; retarder norm
preservation is measured within explicit tolerance.

The dimensionless ratio is transmitted/incident sampled norm. Both fields
and exact compatibility are checked before returning `None` for exactly
zero incident norm. The diagnostic does not authenticate a causal optical
transformation: an independently supplied compatible field with twice the
amplitude gives ratio four. Finite ratios above one are retained without
clamping or epsilon denominators; passive contraction is checked separately.

Local arithmetic reports overflow, invalid results and unusable reductions.
Individual products/squared tails may underflow; a tiny orthogonal component
beside a usable one is retained. A represented nonzero combined field whose
entire norm rounds to zero is rejected. Ratio division uses strict local
NumPy underflow handling, including inexact positive subnormal division when
NumPy reports underflow. Caller error settings are preserved on success and
failure. No global warning/settings change, rescaling fallback or
propagation-frequency/wavenumber restriction is introduced.

## Demonstrated acceptance and remaining boundaries

The fresh unchanged baseline was **2079 passed, 1 skipped in 257.50s
(0:04:17)**. The original Windows file-symlink privilege skip remains; junction
behavior is tested separately. Focused new tests passed **277 in 1.08s**.
The final complete restored suite passed **2356 passed, 1 skipped in 113.31s
(0:01:53)**. All 249 protected pre-existing tracked paths and all 53 installed
distribution entries (52 unique names), versions, metadata hashes and locations
match the captured baseline. The exact pending set is the approved 22 paths.
All three final numerical figures were visually inspected and regenerated
byte-identically after correcting title/legend layout within the figure script.

Independent validation retains all thirteen Malus angles, all five selected
near-extinction offsets, literal complex outputs, asymmetric components,
unitarity, inverse composition, common-phase covariance, loss/conservation
and noncommuting order. Ordinary and focused signal-specific tolerances were
not loosened. Selected weak components, intensity, norm and ratios remain
positive and agree with a bounded 80-digit direct-angle Decimal reference.
The worst selected weak relative error was `2.0194839179460514e-16`;
worst input-scaled complex error was `2.479436791899844e-16`.

Both shipped 64x64 and 32x32 demonstrations passed with actual complete arrays
and labelled center-sample ellipse points. Crossed-polarizer ratio was
`3.749399456654644e-33`; inserting the 45-degree middle polarizer gave
`0.25000000000000006` for already x-polarized input. Fifteen actual isolated
fault variants passed original assertions, failed intended scientific
assertions and passed exact copied restoration. Production source was never
mutated; setup/validation exceptions did not count as detections.

Evidence is under ignored `runs/v2c_acceptance_20261006_01/`, with exact
commands, stdout/stderr, exit records, validation rows, demo arrays and
negative-control source/hash records. Essential reference/probe code remains
in the approved scripts, not solely in ignored evidence. The exact 22-path
scope is mapped in [code_map.md](code_map.md); mathematics and primary-source
translation are in [math_used.md](math_used.md).

V2c adds no propagation, polarized interferometer, reflected/tilted frame,
longitudinal/full-vector Maxwell solution, statistical unpolarized light,
Stokes/Mueller analysis, material/coating/walk-off model, calibrated instrument,
hardware, spatially varying element, persistence, 3D mode or deployment.
Historical frontend/browser evidence remains historical. No servers/browser
sessions, npm, packages, global settings or existing scientific contracts are
changed by this milestone's approved numerical work.

One milestone commit and a normal `origin/main` push are approved after
acceptance. At this precommit record, commit, clean-postcommit import/source
and fresh-demo smoke, push and three-way SHA verification remain **PENDING**.
No new qualified-replay gate is introduced. Stop after V2c; separately approved
V2d and later work remain unstarted. Teaching and historical learning records
remain separate.
