# V2c known limitations

Recorded 2026-10-06. V2c models deterministic, fully coherent classical
monochromatic Jones components at one stipulated common transverse plane.
Uniform ideal thin elements act independently at each sampled position. This
is not a vector propagation solver or a claim of Maxwell transversality for
arbitrary nonparaxial spatial spectra. There are no longitudinal components,
statistical mixtures, partially polarized/unpolarized illumination, quantum
states, Stokes/Mueller framework, noise or calibrated instruments.

## Plane, basis and ideal element scope

Both components require canonical SamplingGrid objects, exactly equal
ny/nx/dy/dx, shape and wavelength. Canonical grids fix the existing coordinates;
subclasses that can change them are rejected. Matching metadata cannot verify
physical alignment or determine an unknown transverse frame. No registration,
resampling, axis flip, conjugation or inferred basis mapping occurs.

Positive element angle turns algebraically from +x toward +y and appears
clockwise in the existing y-down display. Element rotation, passive basis
conversion and viewing-camera rotation are different operations. V2c does not
handle tilted/reflected frames, mirrors or handedness changes. Its x/y
polarization components are not V2a's ordered optical ports. A future polarized
interferometer would need both indices and separately defined frame mappings.

The linear retarder gives its selected axis phase zero and its perpendicular
axis phase +delta under exp(-i*omega*t). QWP and HWP are supplied delta=pi/2
and pi cases, not material predictions. The model does not determine thickness,
dispersion, fast/slow material axes, walk-off, coatings or absolute plate-path
phase. Returned complex phase follows the selected reference; removing its
common phase would change this API even if isolated intensity stayed equal.
Circular states use explicit component labels, without ambiguous right/left
labels. Nonzero angles are evaluated as supplied without wrapping or snapping.

## Arithmetic, darkness and diagnostics

Components and coefficients use complex128; real parameters and intensity use
binary64. Wider NumPy scalars are downcast. Finite input values alone do not
guarantee usable squares, sums, products or ratios. A usable positive dx*dy is
required, and sampled norm is evaluated literally left-to-right as
sum(I,dtype=float64)*dx*dy. An intermediate can fail even when a differently
associated or arbitrary-precision expression could succeed. Same-plane actions
do not impose the propagation model's frequency/wavenumber restrictions.

Local products and negligible squared tails may underflow. A tiny orthogonal
component remains valid beside a usable one. Construction and diagnostic access
reject a represented nonzero combined field whose complete sampled norm rounds
to zero. Exact zero fields are valid; all metadata and supplied parameters are
still checked. Both zero coefficients can produce a valid exact-zero Jones
field from a finite scalar whose own derived norm is unusable.

Overflow, invalid arithmetic and unusable reductions raise contextual
ValueError. Ratio division also raises on NumPy-reported underflow, including
an inexact positive subnormal result, and rejects a positive ratio rounded to
zero. Caller NumPy error settings are preserved. There is no rescaling fallback,
arbitrary-precision production path, global warning suppression, epsilon
denominator or normalization of polarizer loss.

Floating pi/2 and pi retain ordinary residuals; they do not represent bit-exact
extinction or exact complex eigenvalues. Very large arguments have finite
argument precision. Ordinary input-scaled bounds and the separately measured
weak-signal bounds apply to the declared fixtures only. The five actual
binary64 near-extinction angles retain separate positive complex-component,
intensity, norm and ratio checks against bounded 80-digit Decimal references.
They establish preservation of those selected signals, including fractions of
order 1e-18, not arbitrary-dynamic-range relative accuracy or accuracy against
mathematical zero. Exact dark-input assertions remain separate.

Intensity is abs(Ux)**2+abs(Uy)**2 in amplitude-unit^2. Sampled norm has
amplitude-unit^2*m^2, not watts. A transmission ratio compares two compatible
field norms but cannot authenticate a causal optical action. Independently
constructed output amplitude twice the incident gives ratio four. That is not
passive polarizer gain; contraction and retarder conservation are separate
scientific checks. Zero incident norm makes the ratio undefined (None), even
when an independently supplied output is nonzero.

## Ownership and evidence scope

JonesField snapshots both components through the unchanged public ComplexField
constructor, including same-object arguments. Stored arrays are independently
owned, native complex128 and read-only; operations return fresh copies even for
identity/dark cases. Derived intensity is fresh writable float64. These are
the existing reversible ndarray write-flag semantics, not byte-backed storage,
irreversible immutability or a security boundary. Frozen records do not protect
against deliberately reopening arrays or bypassing Python's public interface.

Independent validation, measured comparisons and the 15 isolated fault
variants are documented in [tests_and_evidence.md](tests_and_evidence.md).
Specific scientific assertions detect those mutations; their restoration does
not establish a universal zero-gap correctness guarantee. Setup/import errors
are not scientific detections. Runtime is an observation of the shipped demo
on this environment. Tracemalloc measures traced allocations; process snapshots
and estimates are distinct from a total process peak or portable resource
guarantee.

The three figures are calculated numerical/teaching evidence, not V2d UI
screenshots. Ellipses use the actual named nonzero sample and dimensionless
optical phase tau; they are not measured femtosecond dynamics or fitted curves.
The three-polarizer norm 1/4 belongs to already x-polarized unit-norm input,
not unpolarized illumination. Raw demonstration JSON/arrays do not add a
save/load, archive or qualified-replay contract.

## Deferred work and preserved history

Existing package initializers/exports, scalar numerical code/tests, V0/V2a
schemas, web protocols, frontend/lockfile, Streamlit apps and M5 replay remain
unchanged. V2b browser/frontend measurements remain dated historical evidence;
V2c does not rerun or extend their validation scope. The existing Windows
file-symlink skip remains: this account lacks symlink privilege and junction
behavior is tested separately. No privilege elevation is used to remove it.

V2d 3D polarization presentation, polarized propagation/branching/recombination,
frame/reflection geometry, richer material/instrument models, spatially varying
elements, persistence, remote deployment and hardware require separate approval.
There is no sequence runner, public general-matrix API, element registry or
new scene/z schema. Virtual-experiment save/load remains a separate product gap.

Teaching stays in the separate tutoring conversation. This milestone does not
change learning records, restart a course, assert lesson completion or gate
approved engineering on instruction.
