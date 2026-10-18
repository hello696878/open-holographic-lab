# W1 — Known limitations

- One supported ordered scalar train:Gaussian source, one centered circular or
  rectangular aperture, one ideal thin lens, one observation plane. Other
  stored trains retain ordinary Sequential operation and are rejected by W1.
  Finite nonzero positive and negative focal lengths retain V0 semantics.
  No arbitrary element sequences, folding/reflection geometry, calculated ray
  tracer, branching, polarization propagation, material optics or hardware.
- The model is monochromatic in air on parallel planes and one fixed complete
  periodic transverse grid. Source Gaussian and ideal lens are paraxial models;
  public exact scalar ASM does not make their assumptions exact.
- Explicit `pad_factor=1` means full-window periodic computation. No padding,
  anti-aliasing, band-limited ASM, absorbing boundary, zero-crop restoration,
  automatic refinement, energy restoration or isolated-space accuracy promise.
- W1's resource caps are128 samples per transverse axis and25 total sections,
  including six event identities and at most19 optional interiors. These caps
  restrict execution, not physical validity. Ordinary Sequential's existing
  limits are unchanged. Unsupported grids are rejected rather than resized.
- A finite list of propagated sections samples z; it does not compute a
  continuous 3D Maxwell volume. The cursor selects actual returned ids. Sampled
  meridional curtains fill nearest-sample display bands within event-bounded
  segments; they are not additional quantitative planes, rays or side-scattered
  light measurements. Before/after sides at equal z remain distinct.
- Beam sheets use the actual float64 intensities and one explicit shared color
  range. Saturation, amber opacity and optional glow are display behavior;
  neither detector values nor numerical norms are changed. A clipped or
  diffracted field is not assigned a universal Gaussian waist/envelope.
- Finite-window truncation, periodic wraparound, hard-aperture center-sampling,
  lens phase sampling, transverse pitch, focal spot size and axial sampling are
  separate limitations. The clean260µm example's0.6623%/0.6058% pitch/window
  differences do not certify all settings. The80µm hard-aperture128² case has
  16.2646%/15.8519% differences; its visually computed field remains a periodic
  sampled preview. Earlier256² planning measurements concern a different grid
  and remain historical.
- Full complex Gaussian comparisons have fixture-dependent paraxial/window
  floors:at120mm the adequate free fixture is4.5857e-7, while the220mm example
  is1.7873e-5. No fitted phase/amplitude or hidden normalization removes them.
  The subwavelength evanescent test checks discrete forward-decay policy, not
  validity of a paraxial Gaussian/lens as a physical subwavelength experiment.
- Intensity is arbitrary amplitude-unit²; norm is amplitude-unit²m², not watts,
  calibrated irradiance or detector electronics. Propagation/lens roundoff and
  evanescent norm changes remain signed and distinct from actual aperture loss.
  Null dark ratios are undefined; no epsilon or power-renormalization policy
  replaces them. Local tails can underflow; unusable whole-field norms fail.
- Readonly array ownership prevents ordinary accidental aliasing, not hostile
  mutation/authentication. Transport and attachment revalidate complete frames;
  no result persistence, bundle-contract update or new settings-document mode
  is introduced.
- The16MiB persistent/32MiB transient budgets concern declared app-owned
  resources and overlap. They do not measure browser/V8 heap, all GPU allocations,
  driver memory or whole-process RSS. The backend's separate9,103,459B traced
  peak is not the browser budget or process lifetime peak. Local performance
  observations do not imply universal FPS or full GPU timing.
- W1 implementation evidence, actual production-browser/visual observations,
  failures, skips and remaining acceptance boundaries are recorded in
  [tests_and_evidence.md](tests_and_evidence.md). Numerical/backend passes alone
  do not prove product readiness. Publication requires its separate clean
  postcommit gate; no unperformed publication result is implied here.
- The original Windows file-symlink privilege skip remains. Junction coverage
  does not turn it into a pass. Existing milestone handoffs, historical evidence,
  R03 ideal semantics and learning records are preserved. Figure2a experimental
  reproduction remains unestablished; W1 begins no later stage or course state.
