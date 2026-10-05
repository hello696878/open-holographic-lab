# V1 context for the separate tutor

This document supports a separate tutoring conversation. It does not assert
that a lesson, quiz or course step is complete, restart the learner's course,
or gate already-approved engineering work on teaching. The engineer remains
responsible for implementation and recorded acceptance.

Assume introductory physics, single-variable calculus and basic Python. Build
on the existing V0 handoff rather than requiring advanced wave-optics derivations
before the learner can discuss the interface.

## Useful ideas to connect

The browser is a view and editor of an experiment, while Python V0 is the
scientific authority. Rotating a camera changes what the observer sees, not
the wavelength, lens position or terminal plane. Changing an optical property
creates a different draft; it does not turn the previous output into a result
of that new experiment.

A simulation is an intentional submission of one complete frozen specification.
The resulting array and diagnostics belong to that specification. The stale
result panel is useful for comparison precisely because it keeps its original
identity and observation position. Fast repeated clicks are suppressed, but
that does not imply durable exactly-once computation across reloads or crashes.

Array entries represent samples at physical centers, and cells around those
centers have finite edges. Even and odd sample counts place the full surface
center differently: an even surface is displaced by half a pitch, while both
grids still have a sample at the physical origin. A row is y and a column is x;
the screen/world y mapping is explicitly chosen rather than part of propagation.
The 3×4 distinct-number fixture is a concrete way to reason about a transpose
or vertical flip without advanced optics.

SI units remain metres internally. The UI's nm/µm/mm labels are conversions at
the editing boundary. The bench's schematic scale is another independent
presentation choice, disclosed because its transverse and longitudinal scales
differ. A thick lens glyph does not add a physical hard aperture to an ideal
thin-lens operation.

Intensity values and colors are distinct. The default shared 0–10 gray range
allows aperture/no-aperture comparison without automatically stretching both
to white. A saturated white pixel may represent a value above the limit; a
black-looking weak pixel need not be mathematically zero. The raw float64
readout and maximum settle that distinction. Dark zero illumination is valid,
and a ratio with zero incident norm is undefined/null, not made-up efficiency.

Browser abort is about communication. A Python worker already computing may
continue, so the server must keep its busy gate until actual completion. That
distinction can be explained through a submitted calculation whose display
window closes while the computation remains active.

## Optional demonstrations for the tutor

- Compare the three parameterized presets using the same display limits and
  original scalar norms; discuss where the aperture acts in list order.
- Edit one lens focal length or observation position, observe the stale marker,
  and submit explicitly to compare the new result with the old specification.
- Orbit/pan/zoom and read a selected pixel without changing the submitted data.
- Use the mixed-parity fixture to locate physical sample centers/cell edges.
- Compare original value, display clipping and explicitly selected color range.

These are suggested teaching activities, not claims that they have been taught
or completed. The scientific limitations remain those of V0; visual plausibility
alone is not correctness evidence. Exact test/build/API/browser results and
pending gates belong in `tests_and_evidence.md`.
