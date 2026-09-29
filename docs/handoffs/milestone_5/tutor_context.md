# Milestone 5 — Context for the separate tutor

This is engineering context, not a record of completed lessons. Assume
introductory physics, single-variable calculus and basic Python. The separate
tutoring conversation chooses its pace; no lesson completion or quiz gate is
implied by engineering acceptance.

## Starting point

M2 turns grayscale design intensity into target amplitude. M3 produces a
complex source field, its actual reconstructed field and amplitude-error
history. M4 measures reconstructed intensity. M5 keeps the inputs, outputs
and their meaning together so that a later process can inspect and rerun the
same experiment. It introduces no new optics.

A useful starting analogy is a laboratory notebook with the actual data
attached: the settings explain what was requested, precise arrays preserve
what was computed, and provenance records the software used. A screenshot
alone cannot retain complex field values or every float64 digit.

## Suggested conceptual progression

1. Follow one pixel from grayscale code to `I=g/255`, then `A=sqrt(I)`.
   Explain why target intensity and actual target-amplitude input can both be
   useful records. Source illumination is another input, explicitly selected
   outside the solver; the wrapper does not silently normalize it.
2. Distinguish complex field, phase and intensity. The complex source is saved
   directly. Rebuilding it from displayed phase and amplitude is not a promise
   of identical floating-point bits. Images in the handoff are illustrations,
   not replacements for numerical arrays.
3. Read the human-readable configuration. Grid pitches, wavelength and
   distance have units; iteration count and initialization are explicit. A
   seed is an instruction to an RNG in a recorded environment. Explicit phase
   is instead a saved numerical input. M5 preserves the original choice.
4. Explain a hash as a compact check of file bytes. Changing an artifact
   without changing its stored digest is detected. A person who can replace
   both data and manifest can create a new matching pair; this is not a
   signature or proof of who ran the experiment.
5. Separate the three questions: Are the saved files intact? Does current
   source/environment meet the qualification rules? Does a new computation
   reproduce the saved numbers exactly? One answer does not imply the others.
   Dirty source can produce a matching diagnostic replay while remaining
   unqualified. Matching metadata can accompany a failed numerical comparison.
6. Revisit metric parameters. PSNR needs its declared range, and fraction/CV
   need their own regions. The smooth-target example's disk excludes tails,
   so its exact target need not have fraction one. Its Gaussian profile should
   not be labeled a flatness defect. M3's amplitude residual remains separate.

## Concrete artifacts

- [Bundle anatomy](figures/fig01_run_bundle_anatomy.png) distinguishes
  authoritative inputs/complex outputs, checked derivations and PNG provenance.
- [Integrity and replay](figures/fig02_integrity_and_replay.png) shows publication
  and the three independent verification outcomes.
- `examples/run_bundle.py` uses a fixed 64×64 PNG, seed 0, 50 cycles, 633 nm,
  8 µm pitches and 5 mm distance, with explicitly configured illumination.
  It prints named metrics and provenance and requires no graphical window.
- [Mathematics](math_used.md) explains the exact comparisons and unchanged
  quantities. [Tests and evidence](tests_and_evidence.md) contains reproducible
  commands and measured outcomes, including failures deliberately detected.

Run directories are ignored local outputs. Their names identify locations,
not scientific uniqueness. The saved relative references allow relocation;
fresh-process replay must not rely on live arrays, cached results or the
original external PNG. Exact replay is a measured computational property,
not proof that the optical model describes every real experiment.

M6 and deferred work are not part of this handoff. Do not restart the user's
course, infer learning progress or begin later milestones from this document.
