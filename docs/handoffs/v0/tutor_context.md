# V0 — Context for the separate tutor

This supports a separate teaching conversation. It does not assert that any
lesson is complete, change historical learning records, restart a course or
gate approved engineering work on a quiz. Assume introductory physics,
single-variable calculus and basic Python.

## What the learner can inspect

The example models one source and an ordered row of ideal optical actions.
A complex field assigns a magnitude and phase to each sampled position.
Intensity is the squared magnitude, so amplitude two means intensity four.
The grid translates array indices into physical metres: columns are x, rows
are y; different x/y pitches can still represent a physical circle correctly.

A Gaussian source is bright at its center and decreases smoothly. Its waist
radius is where field amplitude falls to 1/e of its peak; intensity there is
1/e². This is a physical beam radius, not the pixel width of an image-design
Gaussian. A uniform sampled source fills a periodic computational window;
a finite illuminated rectangle needs an explicit aperture.

An aperture multiplies field by zero or one. It removes samples' contributions
to the norm without restoring the lost norm elsewhere. The binary boundary
is included at sample centers, which creates measurable finite-pitch area bias.
A lens multiplies by a phase pattern of unit magnitude: intensity immediately
after the lens stays approximately the same, yet interference during later
propagation can focus the field. The ideal lens has no hidden aperture.

The terminal plane is an ideal observation of the simulated complex field.
Its intensity is not a camera image with exposure/noise/saturation. The sampled
norm adds intensity times each sample-cell area; its arbitrary units are not
watts. A completely dark/blocked field is valid, and division by its zero
incident norm is undefined rather than a meaningful efficiency.

## Three useful conversations

1. Use `fig01_gaussian_free.png` to compare the source and propagated Gaussian.
   Ask what changed in intensity, width and phase while full-window norm stayed
   nearly constant. The analytical Gaussian and ASM are different models, so
   their small complex discrepancy is informative rather than forced to zero.
2. Use `fig02_lens_waist.png` to separate immediate phase action from later
   focusing. The finite Gaussian reaches its new minimum near 17.206 mm in
   this fixture, before the lens's 20-mm focal distance. Compare the independently
   predicted width with actual sampled widths at neighboring planes. Then add
   the explicit aperture and observe actual norm loss, without normalization.
3. Use `fig03_aperture_convergence.png` to explain why a plausible diffraction
   image is insufficient validation. Enlarging the periodic window is different
   from refining pitch. The finest recorded complex-L2 error is about 2.7%;
   coarser cases remain visible, and sampled-area bias is tracked separately.

## Bridge to equations

Begin with `I=|U|²` and aperture multiplication. Then explain a lens's quadratic
phase and the distinction between an absolute z position and the travel
distance between two planes. The runner computes each interval once; equal-z
components have distinct before/after stages.

For a Gaussian, introduce waist size and Rayleigh distance before curvature
and Gouy phase. The sign-matched parameter `q=s-i*zR` follows this repository's
complex-field convention; reference books can use the opposite sign. Full
complex comparisons require amplitude and phase continuity, not only matching
beam width. The [math handoff](math_used.md) provides the explicit expressions
and inspected primary references when the learner is ready.

Explain periodic sampling before suggesting larger grids. Display-only phase
masking hides dark pixels' unhelpful phase, but never changes the calculation
or metrics. A crop in a figure is a view, not an optical aperture. The current
model has no 3D scene, camera electronics, hardware or new stored run format.
