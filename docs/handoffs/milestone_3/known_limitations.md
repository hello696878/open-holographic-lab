# Milestone 3 — Known limitations

Recorded 2026-09-16. This milestone implements a discrete periodic synthesis
problem, not a calibrated optical instrument.

1. **One full periodic plane.** Every pixel is constrained, with fixed grid
   and pitches. There is no crop, padding, support window, free exterior region,
   multi-plane synthesis or isolated-aperture accuracy guarantee. M1's padding
   and sampling limitations remain unchanged.
2. **Lossless sampled domain only.** Any evanescent frequency sample is
   rejected, including at zero distance/iterations. There is no decay-inversion
   regularization or band-limited ASM. The evidence script's analytic phase-step
   calculation is specific to its sampled configurations and enforces no
   production sampling-adequacy criterion.
   A cutoff-rounding geometry whose sequential public radicand is negative
   is rejected even if its summed-frequency comparison passes. M3 does not
   clamp that arithmetic to grazing zero or change M1's public behavior.
3. **Power equality is only necessary.** Strict positive representable energy
   and power are required. Arbitrary targets may be incompatible with fixed
   source amplitude, stagnate or finish with substantial error. No universal
   convergence or unique-phase recovery is promised. The last iterate is
   returned after a fixed count; there is no best-iterate search or success flag.
4. **Residual meaning is narrow.** It is normalized squared amplitude error
   over the entire grid. It is not M4's intensity metrics, diffraction
   efficiency, percent pixels or percent accuracy. M4 is not started.
5. **Finite float64 range.** Invalid or unusable derived arithmetic raises
   rather than rescaling. This is not arbitrary-precision or scale-invariant
   computation over every finite float64 amplitude. Exact-zero phase ties are
   deterministic; physically meaningful phase is undefined on zero support.
6. **Reproducibility scope.** Determinism and tolerances are measured on the
   stated Windows/Python/NumPy environment. Cross-platform bit identity,
   all supported dependency versions and arbitrary large grids are untested.
   Timing is machine/load dependent. Traced allocation peaks are not process
   memory; absolute lifetime working-set peaks include interpreter/imports.
7. **Ideal phase visualization.** The example does not create calibrated SLM
   commands, model phase quantization or export a reusable artifact bundle.
   Illumination is explicitly configured separately for each target; it does
   not demonstrate fixed illumination across arbitrary images. Shared plotting
   scales retain reconstruction overshoot rather than clipping it to one.
8. **Strict existing PNG boundary.** No resizing, RGB conversion, gamma/profile
   processing or orientation correction is added. Blank PNGs remain valid M2
   images but are rejected by the solver's positive-power contract.
9. **Finite evidence.** Independent complete-iteration references, constructed
   fixed points and six deliberate mutation categories catch specific failure
   modes. They do not establish that every possible defect is detectable.
   The predeclared three fixtures/four seeds are not a general image benchmark.

No existing implementation, historical measurement, learning record, dependency
or old figure was revised as part of M3. Hardware, GPU/ML, RGB, multi-depth,
web application, general CLI, exporter and later milestones remain deferred.
