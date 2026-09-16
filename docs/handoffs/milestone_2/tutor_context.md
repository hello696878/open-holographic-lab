# Milestone 2 — Context for the separate tutor

Engineering delivered strict target preparation on 2026-09-16. This document
supports a separate tutoring conversation. It does not assert that the user
has completed a lesson, change any learning record, restart the course, or
gate approved engineering work on a quiz.

Assume introductory physics, single-variable calculus and basic Python.
The current software boundary is deliberately small: from a grayscale code
to a real intensity array and its real amplitude array. Read
[math used](math_used.md) and [known limitations](known_limitations.md) first.

## Ideas the tutor can build on

A pixel stores a number from 0 to 255. Here the number specifies the desired
intensity via division by 255. This is an explicit design decision, not a
universal interpretation of every image file. It preserves brightness between
different targets: a code of 64 means the same intensity in a dim image and
in an image containing full white.

The project's complex field obeys `I = |U|²`. To turn a desired intensity into
the desired magnitude of a future field, take the square root. Mid-gray code
128 therefore gives `I ≈ 0.502` and `A ≈ 0.708`. Using 0.502 as amplitude
would instead produce intensity near 0.252.

A magnitude does not tell us the complex phase. `A exp(i phi)` has the same
intensity for every phase. The target arrays in this milestone are constraints,
not an already-designed field, reconstruction or phase-only SLM pattern.
Phase retrieval belongs to a later, separately authorized milestone.

Array rows correspond to y and columns to x. The caller supplies the physical
pixel pitches in metres. The loader preserves shape and orientation, with
`+y` downward and origin at `[ny//2, nx//2]`. It rejects size mismatches
instead of deciding how to interpolate or change the physical field of view.

## Demonstration material

~~~powershell
.\.venv\Scripts\python.exe -B examples\load_target.py
~~~

This makes a temporary deterministic grayscale PNG, loads it, shows intensity
and amplitude on fixed `[0, 1]` display scales, and reports the maximum
`abs(A**2 - I)`. The default measured residual was approximately `5.55e-17`.
The roundoff is tiny but not mathematically zero; black pixels remain zero.
A `--no-show` mode renders headlessly and was the engineering verification
route. No complex field is constructed or propagated.

Suggested figures, with their purpose:

- [Code → intensity → amplitude](figures/fig01_code_intensity_amplitude.png):
  distinguish stored integer code from real intensity and real amplitude.
- [Rectangular orientation](figures/fig02_rectangular_orientation.png):
  follow asymmetric corners and locate the origin at both parity combinations.
- [Brightness across images](figures/fig03_cross_image_brightness.png):
  compare doubled intensity with amplitude multiplied by `sqrt(2)`.

A tutor may use the examples to discuss how equal code values should remain
equal across images, why a zero target is valid input, and why a target alone
does not solve an inverse optical problem. These are optional teaching topics,
not engineering acceptance requirements or statements about learner progress.

## What the evidence establishes

Independent high-precision references cover all 256 grayscale codes. Separate
tests cover input validation, ownership, orientation, file-format rejection,
decoder lifecycle, optional dependencies and the architecture boundary.
Deliberate mutations confirm selected regressions are caught. Figures are
explanatory illustrations of those contracts, not independent proof of optical
correctness.

No M3 algorithm has begun. Existing propagation sampling, boundary and
evanescent limitations still matter when these target constraints are eventually
used in an optical computation.
