# Milestone 4 — Context for the separate tutor

This is engineering context, not a record of completed lessons. No teaching
progress is inferred. Assume introductory physics, single-variable calculus
and basic Python. The separate tutoring conversation chooses its own pace;
engineering acceptance is independent of lessons or quizzes.

## Starting point

M3 provides a phase-only source and its actual forward reconstruction. A
complex field has amplitude A=abs(U) and intensity I=abs(U)². M3's recorded
residual compares amplitudes. M4 introduces five clearly named measurements
of intensities without changing that solver or its history.

## Suggested conceptual progression

1. Compare corresponding pixels of two small intensity arrays. Square each
   difference and average to obtain MSE. Explain why squaring prevents positive
   and negative errors from cancelling and gives squared-intensity units.
2. Divide the total squared error by the target's squared intensity norm to
   obtain this project's NMSE. For R=2T, derive NMSE=1. That is a numerical
   relative error, not a statement that every pixel or the image is 0% accurate.
3. Introduce PSNR as a logarithmic comparison with an explicitly declared
   reference range. Exact equality gives +infinity; a large error can give a
   negative value. Plot display maxima do not define this metric's range.
4. Sum intensity inside a drawn region and divide by the total window sum.
   Equal pixel area cancels. Compare exact T with 2T: power concentration is
   unchanged even though brightness fidelity is worse.
5. For a region meant to be flat, compute mean and population standard
   deviation, then CV. Contrast a flat patch, a varying patch, and outside
   leakage. CV can exceed one. A desired Gaussian profile is not supposed to
   be flat, so its shape should not be called a uniformity defect.

## Concrete artifacts

- `figures/fig01_m3_intensity_comparisons.png` compares exact target, twice the
  target, and actual M3 intensity with one fixed disk and shared display scales.
  The exact target fraction is below one because some target power is outside
  the disk. The reconstruction's overshoot is retained.
- `figures/fig02_region_power_and_variation.png` separates variation within a
  fixed flat region from power outside it.
- `examples/evaluate_reconstruction.py` prints all input parameters, regions,
  labeled metric values and the separate M3 amplitude residual.
- `math_used.md` gives definitions and derivations; `tests_and_evidence.md`
  distinguishes independent measurements from historical planning probes.

## Interpretation boundaries

The program uses relative intensity units, not calibrated W/m². These arrays
are a simulation, not an instrument. The region and declared range are inputs
to the question being asked. None of the scores is an aggregate percent
accuracy. Undefined divisions are reported instead of hidden with epsilon.
Finite tests and useful pictures support the stated calculations; they do not
establish physical accuracy for arbitrary optical geometries.

M5 and M6 are not part of this handoff. Do not treat this document as permission
to restart the course, mark a lesson complete, or begin a later milestone.
