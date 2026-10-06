# V2c context for the separate tutor

This document supports the user's separate tutoring conversation. Assume
introductory physics, single-variable calculus and basic Python. It does not
assert that a lesson or course is complete, change learning records, restart
the course or gate approved engineering on lessons or quizzes.

## A useful conceptual entry

At one sampled position, a scalar optical field is a complex number carrying
amplitude and phase. A Jones field carries two such numbers: Ux and Uy are the
x/y components of the same transverse optical field at that position. Each
component also has a spatial array. These two components are different from
V2a's two optical paths/ports. A future interferometer with polarization would
need to keep both kinds of index.

The model is deterministic classical fully coherent monochromatic light.
The physical field is Re([Ux,Uy]*exp(-i*omega*t)). Complex numbers do not mean
the measured field is complex; they compactly specify two real sinusoidal
motions with amplitudes and phase offsets. For (1,+i)/sqrt(2), the real vector
is (cos(tau),sin(tau))/sqrt(2), where tau is dimensionless optical phase. For
(1,-i)/sqrt(2), its y component has the opposite sign. Use those explicit
component/rotation descriptions rather than importing an unspecified
right/left circular-polarization label.

The fixed x/y basis uses the repository's +y-down display. An increasing angle
turns algebraically from +x toward +y, appearing clockwise on screen. Changing
an element's axis, describing the same vector in another basis and changing
a later camera view are separate operations. Matching grid/wavelength metadata
does not measure physical alignment; a common plane/basis is an assumption.

## From projection to intensity

An ideal linear polarizer selects the real unit axis
e_theta=(cos(theta),sin(theta)). Its transmitted scalar component is
cos(theta)*Ux+sin(theta)*Uy; multiplying that number by e_theta gives the new
vector. This is an amplitude projection. The squared intensity factor emerges
after calculating the resulting intensity; it must not be multiplied into
the field amplitude a second time.

Total polarization-insensitive intensity is abs(Ux)^2+abs(Uy)^2. For components
(1,1), it is two, not the four obtained by treating them as one scalar sum.
A 45-degree analyzer actually projects the vector first. For (1,1), its output
is again (1,1), with intensity two. For (1,-1), the same projection is dark in
the ideal mathematics. This illustrates how relative phase affects analyzer
output even when the original total intensity is the same.

For x-polarized unit-norm input, an analyzer at theta transmits a norm fraction
cos(theta)^2: Malus law for this prepared polarized input. Crossed horizontal
and vertical polarizers are ideally dark. Inserting a 45-degree polarizer
between them yields norm 1/4. The middle projection changes the surviving
polarization as it loses norm. This particular 1/4 fixture is not an
unpolarized-light experiment and must not be taught as one.

## A retarder changes relative phase

Let e_perp=(-sin(theta),cos(theta)). Conversion into the element's basis uses
R.T, where R has columns e_theta and e_perp; conversion back uses R. An ideal
retarder leaves the axis component at phase zero and multiplies the
perpendicular component by exp(i*delta), preserving its magnitude.

With delta=pi/2, a 45-degree linear state (1,1)/sqrt(2) at axis zero becomes
(1,i)/sqrt(2). With delta=pi, x-polarized input at axis pi/8 becomes
(1,1)/sqrt(2), subject to ordinary floating-point residuals. These are quarter-
and half-wave cases of one generic ideal operation, not separate material
models. The model does not predict plate thickness, dispersion, coatings,
walk-off or an absolute optical-path phase.

The selected complex phase is part of the API. A QWP at pi/4 sends (1,0) to
((1+i)/2,(1-i)/2). That is a circular state with a selected common phase.
Replacing it with (1,-i)/sqrt(2) would remove that common phase. Isolated
intensity would be unchanged, but the actual complex output and later coherent
comparisons would differ. Do not fit or remove phase when checking evidence.

Order matters: applying P(0) then W(pi/4,pi/2) to (1,0) gives the two-component
output above, with norm one. Reversing those actions gives ((1+i)/2,0), with
norm 1/2. These are concrete noncommuting operations; the retarder can change
which part a later analyzer transmits.

## Norm, undefined ratios and numerical evidence

The sampled norm is sum(I,dtype=float64)*dx*dy, with that left-to-right
evaluation order. It approximates the area integral over the sampled window.
Its units are amplitude-unit^2*m^2, not watts. Ideal retarders preserve norm
within measured tolerance; polarizers can reduce it without normalization.
Arbitrary construction coefficients scale both amplitudes and norm and are
not silently normalized.

The transmission diagnostic divides an output norm by an incident norm after
checking compatible metadata. It does not certify that one field was produced
by an optical element. Independently supplying a doubled amplitude gives a
ratio of four. That is valid as a comparison and does not mean a passive
polarizer amplifies light. An exactly zero denominator gives None, because
its ratio is undefined; there is no epsilon added to invent a value.

Binary64 pi/2 is not exactly mathematical pi/2, so represented crossed outputs
can contain tiny positive residuals. Preserve those instead of snapping them
to zero. Near pi/2+/-1e-9, fractions are about 1e-18: a generic 2e-13 absolute
bound could pass a wrongly zeroed result. The focused checks separately compare
complex components, intensity, norm and ratio against an 80-digit Decimal
reference evaluated at the actual supplied binary64 angle. They prove the
selected weak signals survived, not arbitrary relative accuracy near darkness.
Exact-zero inputs are tested separately. Overflow and unusable whole-field
norms/ratios fail rather than being normalized or silently repaired.

## Evidence to explore when appropriate

The demo has 64x64 and 32x32 cases. The three committed figures show actual
Malus outputs/loss, retarder components/independent discrepancies and real-time
ellipse traces. Ellipses use the actual named nonzero sampled vector,
Re([Ux,Uy]*exp(-i*tau)), with equal component-axis scales and y downward.
Their arrows indicate increasing dimensionless optical phase. They are
calculated pedagogical views, not fitted ellipses, calibrated measurements,
slowed femtosecond movies or V2d screenshots.

References and their explicit convention translation are in
[math_used.md](math_used.md); commands, measured bounds and detecting controls
are in [tests_and_evidence.md](tests_and_evidence.md). The normative contract is
[math conventions section 3.19](../../math_conventions.md#319-v2c-ideal-jones-polarization-at-one-reference-plane).
[known_limitations.md](known_limitations.md) distinguishes ndarray ownership
from security and explains the physical/numerical limits. Existing package
exports and scalar/port contracts are unchanged.

V2c adds no propagation, reflected/tilted frames, statistical Stokes/Mueller
analysis, material model, hardware, UI or persistence. Separately approved V2d
would add 3D presentation; polarized interferometry and richer instruments
remain later work. Existing browser evidence stays historical, and the
virtual-experiment save/load gap is not resolved here.
