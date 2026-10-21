# W2 context for the separate tutor

This document supports a separate teaching conversation. It does not assert
that the learner has completed a lesson, passed a quiz or mastered any listed
topic. It does not restart a course, edit historical learning records or gate
approved engineering work on tutoring. Product acceptance and current test
evidence belong in [tests_and_evidence.md](tests_and_evidence.md), not here.

## What the engineering slice represents

The existing laboratory gains a separate English `Geometric Routing`
workspace. One explicitly specified ray meets finite ideal mirrors, an ideal
50:50 splitter, beam stops and receivers. The backend calculates the actual
intersections; the 3D apparatus displays returned positions and directions.
Moving a mirror can make a receiver miss. An explicit Trace is required to
calculate again; camera motion and inspecting a branch do not change physics.

The ray line is a geometrical path. Its drawn width/glow is only visibility
support. It does not represent a Gaussian beam waist, divergence, diffraction,
side-scattered light or a measured detector image. W1 remains the separate
computed aligned-wave-field experience. W2 has no phase/polarization/
interference/refraction or calibrated power model.

## Useful conceptual starting points

For an introductory physics/calculus/Python learner, begin with a 3-vector
as three coordinates and a ray as a starting position plus travel direction:

```text
position(t) = origin + t * direction
```

Positions are in metres; direction is dimensionless and nominally unit.
The world is right-handed XYZ, Y up. A plane has a point and a normal, a
vector perpendicular to that plane. A plane intersection is only a candidate:
the actual point must lie within the disk or rectangle's finite boundary.
A ray missing a small mirror does not bounce off its infinite extension.

The dot product measures a component in a direction. Reflection changes the
normal component's sign and keeps the tangent component:

```text
reflected = incoming - 2 * dot(incoming, normal) * normal
```

Here incoming points toward the hit. Some graphics books point their
incident-direction label away from the surface; translating that convention
is essential before comparing signs. Reversing the normal sign does not
change the reflected propagation direction in this two-sided ideal model.

Local U/V coordinates use the surface's tangent basis. They answer where
the receiver was hit in metres relative to its own center and orientation.
They are not camera pixels. Active rotations use column vectors and
`Rz(z) Ry(y) Rx(x)`: apply X, then Y, then Z. UI fields name the axis and
degrees; stored angles are radians. A later tutor may introduce matrices
gradually; understanding one 45-degree plane giving a90-degree fold is
enough to start.

## Concrete examples available for discussion

The A preset starts at `(0,.08,0)m` toward+Z, reaches a mirror at
`(0,.08,.2)m`, then turns toward a receiver at `(.2,.08,.2)m`. The hand
route length is `.2+.2=.4m`.

B adds a second mirror at `(.2,.08,.2)m` and receiver at
`(.2,.08,.4)m`: +Z, then+X, then+Z, hand length `.6m`. This is an opportunity
to separate apparatus position/orientation from a preconnected drawing.
An ordinary pose edit can move the calculated hit outside the receiver.

C splits an incoming relative weight1 into T=.5 and R=.5. A beam stop in
one arm absorbs that arm's .5 at its actual hit while the other receiver
still detects .5. These are ideal relative bookkeeping weights, not watts
and not complex amplitudes. There is no fringe pattern where lines cross.

The engineering tests independently compare these examples with hand values
and high-precision references. A tutor should avoid presenting a screenshot
alone as scientific correctness evidence.

## Finite arithmetic without misleading intuition

Binary64 numbers approximate most decimal values. Even a nominal unit
direction or a90-degree rotation can contain small arithmetic residuals.
The implementation retains these values rather than repeatedly normalizing
or snapping them. Geometric distance is calculated from endpoints; it is
not blindly equated with the ray parameter.

The program also carries conservative intervals enclosing arithmetic states.
If it cannot decide which finite hit is first, or whether a point is inside
an edge, it reports ambiguity. It does not enlarge the mirror until a
demonstration looks connected. Exact-rational trigonometric certificates and
independent Decimal references are engineering tools; the introductory
lesson can first explain lower/upper bounds with a number line.

The drawing is bounded by a sphere1m from the source. An escaped endpoint
means leaving that declared trace region. Limits on work can return an
incomplete result. The four terminal categories are detected, absorbed,
escaped and resource-truncated. A computational limit must not be taught as
an absorbing optical component; all original weight remains accounted for.

## Handoff boundaries

Core validation currently includes full32-stage references, finite misses,
revisits and branch/record limits. This teaching note does not replace final
integrated product evidence or the user's visual review. Source/reference
details are in [math_used.md](math_used.md), boundaries in
[known_limitations.md](known_limitations.md), and code ownership in
[code_map.md](code_map.md). No claims about lesson completion or changes to
the learner's historical course state are made.
