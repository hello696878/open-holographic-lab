# W4 tutor context

This handoff supports the separate tutoring conversation. It does not assert
that a lesson has occurred, require a quiz before engineering proceeds, restart
a course or change any learning record. Engineering and publication authority
remain in AGENTS.md and the user's bounded W4 approval. The candidate is
unstaged/uncommitted. Dated closeout2026-10-29 records4616 Python passes/one
original skip,636 frontend passes and160 passing browser conditions plus one
focused recording, on the recorded Chrome.47. Installed Chrome.48 changed
externally and its acceptance is NOT_RUN. The final recording received qualified
engineering frame review; the user's visual acceptance remains pending. No lesson
state follows from these engineering results.

Assume introductory physics, single-variable calculus and basic Python. A useful
entry is the distinction between a ray's geometric path, its carried polarization
and its dimensionless fraction of initial optical power. W3 supplies ideal
directions without Fresnel loss; explicitly selected W4 adds power partition and
within-ray polarization at supported finite dielectric interfaces. W1 diffraction
fields remain a different model and do not follow these folded rays.

Start with a normal uncoated n=1 to1.5 interface. The field reflection coefficient
has a sign while the power fraction is its magnitude squared. Here R=.04 and
T=.96; the transmitted power includes an index/cosine flux factor, rather than
being |t|² alone. A first straight passage through two faces gives.96²=.9216.
Subsequent internally reflected paths have separate finite geometry and powers.
Only terminal leaves are summed: a split parent is not an extra detected photon
or second power contribution. The actual bounded normal result remains
incomplete, with3.932160000000004e-9 unresolved rather than a rounded zero.

Introduce transverse e1/e2 axes before local s/p. Source e1=+X,e2=+Y for+Z;
the incidence plane at a rotated face defines local s/p, so source-e1 is not
universally “p”. Camera movement changes neither. Under a legitimate basis
change the numerical matrix entries can change while world polarization and
power remain invariant. At exact normal incidence the incidence plane is not
unique; a justified gauge gives the same physical answer. Numerical code needs
an actual geometric relation to use this case safely.

The compact2x2 coherency matrix C records how transverse complex components
correlate. Store two real diagonal powers and the real/imaginary off-diagonal.
Its trace is the entire ray power, not a normalized matrix later multiplied by
another weight. Each reflection/transmission transforms C with a field operator
and its conjugate transpose. This carries partial/unpolarized light correctly
and preserves TIR's relative s/p phase. Setting every child back to unpolarized
would lose information; an unpolarized TIR example alone cannot reveal that bug.
A linear45 input and a separate phase-sensitive algebraic test can.

Raw Stokes values are another description of the same within-ray state. Their
normalized forms and DoP divide by total power; they are undefined at exact zero,
so the UI shows null instead of inventing0/0. Do not confuse a branch's normalized
polarization with its cumulative power. The code preserves small signed roundoff
under documented bounds; it does not clip values into a plausible picture.

Near Brewster incidence a tiny reflection can still be positive for the actual
stored floating-point direction. Rounding an ideal angle label does not prove
an exact zero. The original seven weak fixtures compare signed amplitudes and
coherency/power against independent high precision with zero absolute tolerance.
Distinguish exact algebraic zero, represented weak positive power, unrepresentable
underflow and an unresolved geometry decision. The last two are errors rather
than fictitious absorption.

Finally distinguish coherent component interference **within one ray** from
coherent addition **between different paths**. W4 retains the former but assumes
incoherent scalar receiver sums for the latter. It does not predict etalon
fringes or a combined receiver polarization without an additional measurement
model. The analytic infinite incoherent slab series is a comparison, not data
inserted into a finite truncated computation. A scientifically useful display
must state these assumptions even when the scene looks realistic.

Suggested source reading, when useful to the tutor: normative conventions§3.25;
`fresnel_interface.py` for frames/coherency/maps; `fresnel_routing.py` for terminal
accounting; independent reference tests for what has been verified. Exact commands,
failed attempts and evidence limitations are in [tests and evidence](tests_and_evidence.md).
No lesson completion or understanding is inferred by this handoff.
