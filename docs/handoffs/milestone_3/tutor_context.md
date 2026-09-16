# Milestone 3 — Context for the separate tutor

Codex completed engineering work under the approved M3 scope. Teaching remains
in a separate conversation. This document assumes introductory physics,
single-variable calculus and basic Python; it does not assert that the learner
has completed any lesson, quiz or earlier topic, and does not restart a course.

Begin from the existing conventions: a pixel carries a complex field
`U=A exp(i phi)`, amplitude squared gives intensity, and propagation changes
the entire field through interference. A grayscale target supplies intensity,
then its square root supplies amplitude; it does not supply phase.

A phase-only hologram changes the phase at the source while preserving a
specified source amplitude. Walk through one cycle using
[fig01_single_plane_gs.png](figures/fig01_single_plane_gs.png): propagate the
source, compare actual target-plane amplitude, impose the desired target
amplitude, propagate backward and restore source amplitude. The target-replaced
field is an intermediate step, not a measured reconstruction.

Connect initialization and indexing carefully. Index zero is already an actual
forward reconstruction. Fifty cycles produce fifty-one recorded residuals.
The returned reconstruction is from the final returned source. Zero cycles is
a useful initialization check. At zero distance propagation is identity, but
amplitude projections still occur and can reset phase where the target is zero.

Distinguish inverse from adjoint without requiring prior linear algebra: an
inverse undoes an operation; an adjoint is the operation paired with it in an
inner-product identity. They coincide here because the full periodic operator
preserves energy and all sampled kz values are real. Cropping can discard
information, so backward cropped propagation generally cannot undo it.

Use [fig02_seed_histories.png](figures/fig02_seed_histories.png) to explain that
different explicit starting phases give different finite outcomes. Do not
label the squared amplitude residual percent accuracy. Equal power is required
but does not prove exact feasibility, unique phase or arbitrary convergence.
All four declared seeds are shown, not just the best result.

[fig03_rectangular_case.png](figures/fig03_rectangular_case.png) keeps row/column
orientation and unequal pitches visible. All figures use a periodic grid and
ideal numerical phase. They are not isolated-aperture validation or calibrated
SLM drive patterns. Source illumination is explicitly configured per target.

For correctness evidence, contrast visual resemblance with the independent
scalar direct-DFT complete-cycle calculation, constructed feasible fixed point,
source-amplitude conservation and rebuilding a source from the returned phase.
Explain why a round trip alone can pass under two mutually wrong signs, and
why a loss measured after target replacement is misleadingly zero.

Use [math_used.md](math_used.md) and [tests_and_evidence.md](tests_and_evidence.md)
for exact definitions and measured limits. Planning probes and shipped-solver
measurements are distinct evidence. Continuous synthetic designs and decoded
8-bit images are also distinct arrays. M4 quality metrics remain outside this
handoff and have not been implemented.
