# V2b context for the separate tutor

Codex is the engineering agent for the approved V2b scope.
This handoff supports a separate tutoring conversation. It does not assume
the learner has completed any lesson, quiz or previous course unit, and it
does not authorize changes to historical learning records. Engineering
acceptance/publication evidence is in
[tests_and_evidence.md](tests_and_evidence.md); teaching need not gate
already-approved engineering work.

Assume introductory physics, single-variable calculus and basic Python.
Introduce complex amplitudes/phase and two-channel matrix notation as
needed rather than assuming a linear-algebra course. Use the unchanged
[normative §3.18](../../math_conventions.md#318-v2a-coherent-two-path-interference)
and [math_used.md](math_used.md) for signs and port ordering.

## What this bench demonstrates

The initial sequential mode remains the existing V1 workflow. A separate
two-path mode accepts a supported uniform/Gaussian source, sampling grid,
wavelength, two nonnegative propagation distances and an extra signed
arm-1 phase. Explicit Simulate produces two actual V2a output intensities.
Editing validates the draft but does not simulate; Phase Sweep is another
explicit operation with 17 actual solver calls. Neither a plot-point click
nor camera/color changes calculate new optics.

The drawn topology is an ideal unfolded schematic:
input -> B -> two forward arms -> extra arm-1 phase -> B_dagger -> two
logical outputs. Both output images use one transverse frame and are
immediate recombiner outputs. Guide length and lane separation are cosmetic.
Avoid deriving phase from apparent scene length, teaching an unimplemented
mirror-displacement rule or attributing coefficients to a universal cube
reflection law.

## Suggested explanation and optional experiments

1. Begin with a complex amplitude as a magnitude and a phase. Explain why
   measured scalar intensity is its squared magnitude, so common phase can
   change a complex field while leaving intensity unchanged.
2. Use the fixed two-channel mixing convention to track the two ordered
   outputs. With equal arms, zero extra phase concentrates output in port 0;
   pi/2 shares the lossless uniform case; pi concentrates it in port 1.
   Ask for qualitative predictions before an explicit Simulate action.
3. Compare extra phase and propagation distance. The existing propagator
   already includes wavelength-sensitive travel phase and diffraction.
   The unequal-arm preset uses `L0=lambda/7`, `L1=L0+lambda/6`, phi=0 and
   retains the carrier-sensitive .75/.25 uniform case. No additional
   carrier belongs in the UI.
4. Read the original-input denominator before interpreting the sweep.
   Explain that the two output fractions can sum below one when the
   sampled model's forward propagation attenuates evanescent content.
   cos²/sin² alone assumes unit survival. Norms are amplitude-unit² m²,
   not calibrated watts; signed residuals are not percent accuracy.
5. Distinguish mathematical darkness from displayed black. Floating-point
   cancellation can leave tiny values. Shared grayscale clipping and byte
   quantization change presentation only; original float64 picks/maxima
   remain visible. Zero input has zero output and undefined ratios, shown
   explicitly rather than converted to misleading zero efficiency.
6. Inspect the actual 17-point sweep. Both endpoints are calculated;
   tolerance-based periodic closure is different from forced equality.
   Lines between markers are visual interpolation. A selected marker does
   not compute; the separate simulate-this-phase action requests arrays.
   A failed sweep has only a labelled genuine prefix.
7. Make a scientific edit and observe stale-result detachment. Explain
   why the prior-result panel preserves its original submission and why
   a late response cannot attach after switching modes away and back.
   A numerical result and a display failure are separate facts.

These are suggested teaching activities, not recorded completed lessons
or required engineering quizzes. Use the learner's current understanding
to choose a starting point.

## Useful artifacts and caveats

The genuine browser figures are [dual outputs](figures/fig01_dual_outputs.png),
[phase sweep](figures/fig02_phase_sweep.png) and
[stale/cross-mode state](figures/fig03_stale_cross_mode.png). Use them to
orient the learner, not as independent mathematical correctness evidence.
The [code map](code_map.md) identifies public APIs and acceptance tools.
Tests distinguish direct same-input V2a equivalence, analytic cases,
literal transport fixtures and isolated deliberate failures.

The model is scalar, monochromatic and periodic on one sampled window.
It has no physical mirror geometry, polarization, noise, hardware or
calibrated radiometry. Resource caps do not prove sufficient sampling.
Browser phase -0 becomes +0 as an explicit zero-phase UI/transport policy;
nonzero phases are not wrapped. Do not extend these limited results into
claims about a physical interferometer, a general convergence guarantee,
later milestones or the learner's course status.
