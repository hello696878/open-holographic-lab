# W3 mathematics

The complete contract is in `implementation_summary.md` and normative §3.24.
Frozen derivations remain in `runs/w3_refractive_routing_plan_01/NUMERICAL_POLICY.md`
and `PRIMARY_REFERENCE_NOTES.md`. New measured results are recorded separately
in `tests_and_evidence.md`; planning numbers are never replacement measurements.

The physical target is the exact affine image of a canonical block/prism under
the stored binary64 active matrix B=RzRyRx. A transformed plane uses B^-T times
its local outward covector. Outward interval cofactor inversion encloses the
transformed covectors; a separate exact Fraction inverse verifies containment
for the stored-B affine witness. Common vertices and halfspaces define a closed body;
reciprocal-Gram coordinates identify positions on possibly nonorthogonal face
bases. World-edge predicates and finite triangular ends participate in the
same nearest-hit decision. A supporting-plane crossing alone is not entry.

Let d be the incoming propagation direction, and a the incident-facing
covector: outward on entry, inward on exit. Set A=a·a, S=d·d, rho=ni/nt,
q=d-a(d·a)/A and K=S-rho²(q·q). Certified K>0 gives
rho*q-sqrt(K/A)*a. Certified K<0 gives d-2a(d·a)/A. Both preserve the inherited
direction norm algebraically, without renormalization. Intervals propagate
through every operation and subsequent position/length. A zero-containing K,
uncertain side/order or exceeded width fails closed rather than selecting a
visually plausible route.

For exactly equal stored indices, orthogonal decomposition gives
K=(d·a)^2/A. Evaluate this equivalent expression with existing enclosures to
avoid subtracting correlated intervals. The same strict-positive gate applies;
only then does the exact identity preserve d and its enclosure. Medium IDs
still change at certified entry/exit. This refinement neither resets error nor
introduces a critical-angle tolerance.

Entry changes exterior to body, exit reverses it, and TIR keeps the incident
medium. The known preceding face root alone can be excluded for one straight
leg under a side certificate; later returns to the same face remain possible.
The returned outward normal is distinct from the incident-facing calculation
covector. TIR displays its actual reflected angle; no transmitted direction,
transmitted angle or unsupported critical angle is fabricated.

Independent Decimal references construct geometry and scalar/vector Snell
solutions without production helpers. Exact stored-input/affine comparisons
are distinct from ideal real-angle comparisons. A residual near zero is not
an enclosure proof. The original alternating-interface algebraic stress is
also distinct from a physically realizable trajectory through one closed body.

Refraction/TIR preserve ideal bookkeeping weights; approved splitters divide
them. Every pending leaf is accounted at truncation, signed residual is retained,
and unsupported arithmetic is an error rather than absorption or truncation.
These results make no Fresnel, polarization, dispersion, phase or power claim.

The declared reference comparisons use Decimal precision 90, position atol
5e-12 m, direction atol 2e-12, angle atol 2e-12 rad and rtol 2e-12. The shipped
14-case run observed maximum position discrepancy 2.1503618086384608e-17 m and
direction discrepancy 4.496919387021123e-16. Every independently referenced
component must also lie inside its propagated enclosure; comparison tolerance
does not enlarge an enclosure. The slab's measured perpendicular displacement
is 0.005814413464563082 m. Its exact stored-input reference and separate ideal
real-30-degree/0.03 m reference are preserved as distinct Decimal strings in
`core/validator_01/results.json` under the implementation evidence root.

The first browser C test mistakenly compared the lower endpoint of the K
interval to the exact scalar target with a nominal-value tolerance. For C's
exact stored inputs, d=(0,0,1), equal prism legs and B=I give q=(-1/2,0,1/2),
rho=3/2 and K=-1/8. The actual interval
[-0.12500000000030223,-0.12499999999969845] encloses that target with a strictly
negative upper bound. Endpoints are conservative bounds, not nominal estimates.
The correct independent acceptance is finite ordered bounds containing -1/8
and strictly below zero, alongside unchanged nominal geometry/angle and
position/direction width checks. No global tolerance or production arithmetic
is changed to accommodate that test correction.

The visible parallel-block displacement is a display-derived nominal geometric
quantity: `||(exit-entry) cross incoming|| / ||incoming||`. It uses actual
returned points and direction, qualified by the same branch, two opposite block
faces, entry/exit refraction, the same exterior index and forward parallel
emergence. It is the perpendicular separation of lines, not a same-coordinate
plane shift. The Inspector displays full metre and millimetre strings only
under the current full request/model/scene/branch/event identity. It is absent
for stale, prism, TIR, adjacent-face or unqualified routes. This readout does not
solve Snell again, alter a route or add a wire field; no separately certified
uncertainty for the derived scalar is claimed.
