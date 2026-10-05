# V2a context for the separate tutor

This document supports the user's separate tutoring conversation. It does not
state that any lesson or course is complete and does not gate engineering.
Assume introductory physics, single-variable calculus and basic Python.

## Suggested conceptual entry

Represent the optical field at each sample by a complex number. Its magnitude
sets amplitude and its angle records phase. Intensity is the squared magnitude.
Adding complex amplitudes can cancel or reinforce; adding intensities alone
loses that information. A phase multiplication rotates the complex number and
preserves its magnitude.

For this ideal mixer, the ordered fields are transformed by
`[[1,i],[i,1]]/sqrt(2)`. A lone input U becomes U/sqrt(2) in arm0 and
iU/sqrt(2) in arm1. The chosen recombiner uses the inverse matrix with -i.
The factor sqrt(2) makes each split arm carry half the sampled norm.
The crossed i is essential: use coherent simultaneous inputs (1,i) to see
that B produces (0,sqrt(2)*i). Conservation alone does not settle the phase.

Forward propagation changes complex field, not merely its intensity. The
existing angular-spectrum method already contains the travel phase. The
additional phi is an independently prescribed uniform phase on arm1.
For equal arms, both share W=P(L)U and the outputs are
`exp(i*phi/2)*cos(phi/2)*W` and `-exp(i*phi/2)*sin(phi/2)*W`.
At phi=0, port0 is bright; at pi, port1 is -iW. These labels depend on the
declared matrices/order/reference planes and are not universal cube labels.

The fraction denominator matters. This model reports output norm divided by
original input norm. If propagation leaves a fraction tau, the outputs are
tau*cos²(phi/2) and tau*sin²(phi/2). Bare cos²/sin² assumes tau=1. Blocking
one arm after splitting removes half the original norm; the two remaining
outputs each carry one quarter. A phase on the sole survivor changes neither
output intensity. Do not normalize that removal away.

## Evidence to explore when appropriate

The three committed numerical figures show the ideal unfolded schematic,
both actual equal-mode outputs on the same raw intensity scale, all eight
phase points, signed norm differences, the blocked-arm budget and asymmetric
complex-reference discrepancies. Equal modes under uniform phase redistribute
brightness; these panels intentionally show no invented spatial stripes.
The independent small direct DFT constructs coordinates and sums itself;
it does not call the production FFT/propagator to obtain expected answers.

Near-dark tests use phases on both sides of zero and pi. Small cancellation
residuals are measured with an input-scaled absolute tolerance, since relative
error against an exact dark reference is meaningless. Exact zero input is a
different case with undefined ratios. Tiny negative roundoff residuals are not
physical absorption.

Sources and the explicit MIT convention translation are in
[math_used.md](math_used.md); actual results and limitations are in
[tests_and_evidence.md](tests_and_evidence.md) and
[known_limitations.md](known_limitations.md). The existing V0/V1 records remain
historical. Future 3D dual-output integration and richer physics were not begun.
