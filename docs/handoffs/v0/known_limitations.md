# V0 — Known limitations

This milestone supports a bounded scalar aligned forward experiment, rather
than a general laboratory or a continuous-optics accuracy guarantee.

- One monochromatic scalar field in n=1, parallel planes, a fixed complete
  grid and one forward axis. No tilted/rotated elements, branching, mirrors,
  polarization, interference model extensions, partial coherence, RGB,
  cameras/electronics, calibrated radiometry, SLMs or hardware.
- Gaussian sampling and ideal lens phase are paraxial descriptions. Reusing
  exact scalar ASM does not make those source/element assumptions exact.
  Signed focal length is supported, without aberration or implicit clear aperture.
- The full grid is periodic. A larger window can reduce observed wraparound
  for a particular localized experiment but does not guarantee isolated-space
  accuracy. Uniform illumination enlarges with its window; compare an explicit
  fixed physical aperture when claiming the same bounded experiment.
- Inclusive hard-edge center sampling produces finite area and boundary bias.
  The approved aperture comparison is a fixture-specific relative complex-L2
  bound of 0.035 at 1-µm pitch, not sub-percent or worst-pixel accuracy. Coarser
  failed-threshold cases remain recorded. No antialiasing or fitted reference
  aperture is introduced to manufacture agreement.
- Lens phase, transfer-function sampling, truncation, edge sampling, wraparound
  and focal spot sampling require separate consideration. Reported analytic
  increments/spectral occupancy are diagnostics, not a universal sampling badge.
  Band-limited ASM remains outside V0.
- Unapertured Gaussian ABCD references include phase/prefactor and approximate
  ASM with measured paraxial floors. They are not ground truth for a clipped
  Gaussian. Its same-geometry window/pitch studies are convergence evidence,
  not an independent exact continuous reference.
- The Fresnel reference omits nonparaxial path/amplitude terms. Separately
  estimated omitted terms are not a rigorous full diffraction-error bound.
- Norm has arbitrary amplitude-unit²·m² units. Selected-region norm, aperture
  removal, full periodic norm and numerical window effects are distinct. An
  ideal observation plane is not a detector with area integration, exposure,
  noise, saturation or calibrated watts.
- Dark fields are valid, while unusable whole-field norm arithmetic fails.
  Local allowed tail underflow can erase exceptionally small numerical tails;
  binary64 cannot promise representation of all continuous nonzero tails.
- Execution limits are 2048 per axis, 16 components and four explicitly
  requested intermediate fields. They do not reserve memory or establish
  runtime limits on every machine. Traced allocations are not process working
  set; process snapshots and lifetime peaks are labelled separately. Large-grid
  n² estimates remain estimates.
- Stable IDs are for future selection, not universal scene identities or
  authenticated authorship. Schema conversion is in-memory only: no new
  persistence, migrations, M5 bundle schema, qualification or replay badge.
- No server or browser acceptance is needed or performed for this numerical
  milestone. The pre-existing port-8501 server is not task-owned and is unused.
  V1/V2/V3 and a 3D viewer remain unimplemented.

The existing Windows file-symlink privilege skip is preserved; its separate
junction coverage does not turn the skipped file-symlink case into a pass.
Historical M0–M7 measurements/handoffs remain intact. Finite assertions and
negative controls establish their recorded cases; no gap-free claim is made.
