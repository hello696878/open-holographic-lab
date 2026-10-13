# V2f known limitations

This is one ideal unfolded coherent monochromatic two-arm experiment with
both port and polarization indices. Reference planes and identity transverse
basis mapping are stipulated. Metadata equality cannot verify alignment.
The ideal polarization-independent B/B_dagger pair is not a coating law,
physical cube-rotation rule, mirror/reflected-frame model or quantum process.

Each arm has zero to two uniform public Jones actions at its terminal plane.
There is no travel between those actions, material thickness/dispersion,
arbitrary graph, cavity, tilt, spatially varying element, longitudinal field,
noise, Stokes/Mueller extension or calibrated instrument. Retarder phase uses
V2c's selected-axis zero/perpendicular +delta convention; physical plate path
phase is not predicted. Extra common arm1 phase is separately supplied.

## Complete-pipeline numerical domain

V2f supports the explicit intersection needed by reused scalar mixing/phase
and Jones actions. A valid original JonesField does not guarantee success.
A tiny component beside a usable orthogonal component can be valid for Jones
actions but unsupported by scalar mixing/phase. Their outputs are also checked;
splitting, cancellation or an arm action can create a later unusable component.
Such errors are contextual and return no partial result. Components are never
deleted/rescaled to manufacture darkness or a successful result.

Pure Jones intermediates retain V2c combined-norm semantics. This restriction
is not imposed at every Jones-only stage. Exact zero fields remain distinct
from represented nonzero underflow. Bounded tails and inherited forward
evanescent decay may underflow; wider dynamic-range support would need a new
separately approved primitive, not an old-contract edit.

Static prevalidation checks all records, parameters and geometry before work,
including all four mixer component norms. It cannot certify all derived states.
Finite binary64 inputs can still cause unusable products/reductions/ratios.
Large finite angles have ordinary argument-precision limits; there is no
modulo, snapping, arbitrary-precision production path or normalization fallback.
The strict ratio policy can reject an inexact positive subnormal result.
Caller floating-point settings are restored rather than changed globally.

## Propagation, accounting and evidence

Scalar ASM is applied independently to x/y, at pad_factor=1 with nonnegative
distances, as a newly bounded aligned homogeneous Jones-envelope composition.
This is physically a low-angle model, not arbitrary-angle vector Maxwell
propagation. Pad1 is a complete periodic window, with wrap-around; no automatic
anti-aliasing, crop/resampling or convergence correction is supplied. Inherited
evanescent arithmetic is not calibrated vector electromagnetic energy transport.

Norms are measured combined Jones reductions in amplitude-unit²*m², not watts.
Their reduction can differ in last bits from sums of separately reduced scalar
norms. Signed residuals remain; no measured value is adjusted to force
conservation. Fractions use original input and are undefined at zero input.
Analyzers are separate downstream operations and cannot overwrite raw outputs.
User-supplied scalar histories do not authenticate discarded intermediate fields.

Generic input-scaled bounds do not establish relative accuracy at zero or in
every tiny quadrature. Selected near-dark fractions have independent actual-
binary64 phase references and focused bounds. A much smaller quadrature can
round to zero even when the selected signal survives; this limitation is not
permission to clip other represented signals. Distinct0 and2*pi evaluations
retain residuals. Sampled extrema are not exact continuous fringe visibility.

The runner-only128-axis cap is a resource policy, not a sampling certificate.
Runtime observations, Python-traced allocations, process snapshots and lifetime
peaks are different measurements and not portable guarantees. Results retain
only final fields/scalars; public ndarray ownership/read-only flags remain
reversible, not a security boundary or hardened immutable storage.

Actual checks, original failures/retries, controls/restoration and resource
observations are in [tests_and_evidence.md](tests_and_evidence.md). Specific
mutations establish intended detecting assertions, not gap-free correctness.
Reference-oracle mutations are distinct from production branches and ordinary
documented exception tests. The Windows file-symlink privilege skip remains;
junction behavior is separately tested, without privilege elevation.

## Deferred integration and preserved history

No initializer/export, old numerical module/test/guard, app/frontend, transport,
V2e schema, M5 bundle, dependency/lockfile or historical handoff is changed.
Historical frontend/browser results are not rerun for this numerical milestone.
V2g requires separate approval and explicit new-mode document compatibility;
V2e remains closed to sequential/two_path/polarization. No public persistence,
qualified replay, new hardware, reflection geometry or deployment is included.
Teaching remains separate; no learning progress is inferred.
