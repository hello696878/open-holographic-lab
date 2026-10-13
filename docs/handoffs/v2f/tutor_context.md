# V2f context for the separate tutor

This is supporting material for a future tutoring conversation, not a lesson
completion record, quiz requirement or course restart. Engineering validation
is separately documented. Assume introductory physics, single-variable
calculus and basic Python; introduce complex amplitudes and vectors explicitly.

An optical port labels a beam path; x/y label two polarization components of
the SAME path at a point. V2f therefore has four entries, ordered
(port0.x,port0.y,port1.x,port1.y). The ideal splitter combines matching
polarization entries across ports, never x with y as though they were paths.

Complex amplitudes retain phase. Magnitude squared gives scalar intensity;
for orthogonal polarization components, total intensity is the sum of their
individual squares, not the square of their scalar sum. Coherent fields in
the same polarization combine before taking intensity. This explains why
identically polarized arms show phase-dependent port brightness while
orthogonal arms have half/half polarization-insensitive outputs in the ideal
matched lossless fixture.

Projecting BOTH outputs through equal45-degree analyzers selects a common
polarization direction, allowing their component amplitudes to interfere.
The analyzed fractions become (1+cos(phi))/4 and (1-cos(phi))/4 of original
input; their sum is half. The removed half is analyzer loss, not missing power
to normalize away. Raw and analyzed outputs are separate measurements.

The model's ideal retarder leaves its selected axis at phase zero and gives
the perpendicular axis +delta. A common phase that does not change an isolated
polarization ellipse can change interference relative to another arm. Keep
the actual complex state rather than an equivalent normalized representative.
For example, x changing to -x in only one arm shifts the response. Classical
coherent optics explains these cases; no photon or quantum-eraser claim is made.

The same scalar propagator is applied to x/y envelopes through aligned,
homogeneous, polarization-independent arms. This is a bounded low-angle
composition, not a general vector electromagnetic solver. Uniform terminal
actions have no independent travel positions. Equal-mode uniform phase changes
brightness, not invented spatial stripes; unequal spatial modes need not
cancel completely. A viewing diagram is not ray-traced mirror geometry.

The six checkpoint pairs and short action histories make losses and signed
numerical residuals visible. Fractions always name their denominator; zero
incident norm is undefined. Near-zero arithmetic and tiny unsupported scalar
components are limitations to explain, not values to silently clip. Existing
public constructors preserve independent arrays, while read-only flags are not
an irreversible security boundary.

Use the three calculated figures, example commands and exact measured evidence
in this handoff. Do not infer that the user has learned these topics or that
any exercise has been completed. V2g interactive/document integration remains
a separately approved later engineering stage.
