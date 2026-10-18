# W1 — Context for the separate tutor

This is a teaching handoff, not a lesson-completion record or a prerequisite for
approved engineering work. It assumes introductory physics, single-variable
calculus and basic Python. No course restart, quiz gate or inferred learning
status is intended.

## What the product calculates

The user configures a Gaussian laser envelope, a physical aperture, an ideal
thin lens and an observation plane, then explicitly selects Simulate. The
software calculates a limited set of transverse complex fields at stated
distances. The visible beam sheets show intensities derived from those actual
fields. They are not images blended between source and detector.

The first supported train has exactly those two optical elements, in that order,
with up to 128 samples along each transverse axis and 25 returned sections.
Both converging and diverging signed focal lengths use the same existing ideal
model. These software limits do not guarantee adequate physical sampling.

A complex field stores two real numbers at each grid point, representing
amplitude and phase. Its intensity is real-part squared plus imaginary-part
squared. Two fields can have the same immediate intensity but different phases
and therefore evolve differently. The ideal thin lens illustrates this:its
phase changes at the lens plane, while pointwise intensity there is essentially
unchanged; downstream interference produces focusing or defocusing.

The aperture instead multiplies the incoming complex field by a physical0/1
mask. It removes amplitude outside its opening. Treat the planes immediately
before and after it as separate events, even though their longitudinal position
is identical. This distinction prevents the software from inventing continuous
intensity through a discontinuous mask.

## Useful explanations and small exercises

1. Connect array indices with physical positions. Rows are y, columns are x;
   x[j]=(j−nx//2)dx. For both even/odd counts, the middle indexed sample is at
   zero. Translate a selected row/column into micrometres before discussing
   orientation of a texture.
2. Explain intensity versus sampled norm. Intensity is a value at one sample;
   norm sums all intensities with a sample-area factor. A smaller aperture can
   reduce total norm without forcing the largest displayed pixel to dim. A
   shared color scale makes honest before/after comparisons possible.
3. Use the explicit W1 example and keep its display range fixed. Move the
   cursor among genuine sections, inspect the named side of the aperture, then
   change aperture or focal length. Point out STALE before submitting again.
   A camera move or cursor move reads old calculated data; it does not run optics.
4. Contrast a converging and diverging lens on an informative fixture. For an
   ideal unapertured Gaussian the minimum radius need not occur exactly one
   focal length after the lens. Do not apply that Gaussian formula universally
   after hard clipping/diffraction.
5. Separate visual interpolation from computation. The axial curtains use
   nearest returned samples for presentation and break at thin-element events.
   They are not measured side-scattering, computed rays or extra numerical planes.

For a first explanation, propagation can be described as decomposing a sampled
wave into spatial-frequency components, advancing each component's phase and
combining them again. W1 reuses the existing Angular Spectrum Method; a detailed
Fourier-transform derivation can be introduced separately when useful. No new
production FFT formula is needed to understand why upstream phase matters.

## Evidence and its limits

Independent dense DFT sums check all25 complete complex fields on small
asymmetric grids. Analytic Gaussian/lens references retain amplitude and phase,
not just a visually plausible width. Aperture masks, coordinates, loss,
co-located events and unchanged terminal output have separate checks. Deliberate
wrong-anchor, wrong-side, double-phase, normalization, transpose, interpolation
and duplicate-run faults are detected by the intended assertions.

The finite transverse grid is periodic and has finite pitch. The clean example
has sub-percent fixed-geometry pitch/window differences, but a strongly clipped
128² case differs by roughly16%. That is an instructive retained limitation,
not an error to hide by normalizing the image. Small signed norm residuals can
be floating-point arithmetic; calibrated watts, hardware response, realistic
scattering and continuous3D electromagnetic claims are absent.

Use the actual screenshots, recording, observations and acceptance boundaries
in [tests_and_evidence.md](tests_and_evidence.md) alongside this scientific
context. Numerical summaries alone do not establish product acceptance or
publication. W1 does not change the ideal R03 ensemble model or establish
Figure 2a experimental agreement.
