# Milestone 7 — Context for the separate tutor

Assume introductory physics, single-variable calculus and basic Python. This
handoff supports a separate interactive conversation; it does not certify a
lesson, require a quiz or restart the user's course.

The new Designer creates editable desired-intensity drawings inside the local
workbench. Its disks, rectangles and round-capped segments become sampled
arrays, then enter the existing amplitude/synthesis/metrics/run workflow only
after an explicit Generate & Save action. Start with the
[implementation summary](implementation_summary.md), [math used](math_used.md)
and [actual evidence](tests_and_evidence.md). The [code map](code_map.md) and
[known limitations](known_limitations.md) describe where each responsibility
and assumption belongs.

Useful conceptual connections:

- **A geometric drawing becomes samples.** A disk includes a pixel when the
  pixel's center lies within the specified radius. The boundary is included.
  A width-2 rectangle can cover centers `-1,0,1`; continuous distance and
  discrete sample count are different quantities.
- **Coordinates explain orientation.** Columns are `x`, rows are `y`, and
  positive `y` points downward. Zero is at `[ny//2,nx//2]`. Changing canvas
  size changes the sampled window; changing pitch changes physical scale.
  A pixel-space circle may be physically elliptical on unequal pitches.
- **Drawing order is assignment.** A later object replaces earlier intensity
  values, even with zero. This is not a model of two coherent optical beams.
  There is no hidden peak normalization, so an object's fractional brightness
  means the same thing before and after another object is added.
- **Intensity is not amplitude.** Intensity `0.25` leads to amplitude `0.5`.
  Neither is a phase map. The source illumination is explicitly selected for
  each submitted target outside the solver; matching power does not guarantee
  an exact reconstruction.
- **Floating-point evaluation has an order.** A segment is geometrically
  unchanged when endpoints are exchanged. Internally ordering endpoints makes
  both representations use the same arithmetic while the editable record
  preserves the user's orientation. This is different from enlarging an edge
  with a tolerance or changing an inconvenient input.
- **Preview and result have different identities.** Editing can update the
  desired raster without solving. The saved reconstruction belongs to a prior
  immutable submission until a new deliberate run is generated. Selecting an
  object is not an edit. Changing controls never rewrites old arrays.
- **An editable file is not a numerical bundle.** JSON retains shapes and
  order; M5 stores actual input/output arrays and scientific settings. A
  matching external design raster can help recover editing, but cannot prove
  unique authorship. Numerical replay does not need that external design.

If useful for the learner's current topic, compare an asymmetric small-grid
drawing to its explicit membership mask, then swap layer order, insert a
zero-intensity object or change one pitch. These are optional teaching ideas,
not claims that the learner performed them. For a completed synthesis, compare
the desired intensity, actual reconstruction, ideal phase, full amplitude
history and separately defined intensity metrics. Do not label any metric as
percentage accuracy or demand a Gaussian-quality threshold from hard edges.

Two figures show real application captures:

- [Designer preview](figures/fig01_designer_preview.png) — actual editor and desired raster.
- [Saved result](figures/fig02_designer_saved_result.png) — saved-run display with a later draft edit clearly marked.

Their viewport provenance and acceptance scope belong to the evidence document. They are
not optical correctness proofs. The [roadmap](../../roadmap.md) places a future
3D virtual optics laboratory after content-design work. A render camera will
not automatically become a simulated detector; that later product needs
separately validated physical models and approval.
