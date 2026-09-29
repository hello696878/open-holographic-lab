# Milestone 6 — Context for the separate tutor

The learner can use introductory physics, single-variable calculus and basic
Python. This document supports a separate interactive teaching conversation;
it does not certify completed lessons, impose a quiz or restart the course.

## What the learner can inspect

The local workbench connects already implemented target loading, synthesis,
metrics and saved-run replay. The useful starting sequence is to create the
default smooth-spot run, compare its target/reconstruction, inspect ideal
source phase and read the complete amplitude-error history. Then open the
saved run and distinguish inspection from an explicit replay.

The implementation description is in [implementation summary](implementation_summary.md),
the module map in [code map](code_map.md), and the mathematical meanings in
[math used](math_used.md). Use [tests and evidence](tests_and_evidence.md) to
check which behaviors were actually exercised. The two figures are intended
as real UI captures:

- [Create and inspect](figures/fig01_create_and_inspect.png)
- [Verify and replay](figures/fig02_verify_and_replay.png)

Do not infer unrecorded browser or postcommit results from those illustrations.

## Concepts to connect

**An image is a sampled design.** The fixed example has width 7.5 pixels.
Changing pixel pitch changes its size in metres without changing the raster.
The 60-micrometre width applies only at the default 8-micrometre pitch. Uploaded
grayscale codes become design intensity through `g/255`, not a calibrated
camera brightness measurement.

**Intensity and amplitude are different.** Target amplitude is the square
root of target intensity. New-run illumination is explicitly selected to
match source/target power for each target before the solver starts. This
choice is not evidence that one fixed light source can realize arbitrary
images, and equal power does not guarantee exact reconstruction.

**Phase color is not target brightness.** The source phase view shows radians,
with a fixed color scale. It is an ideal numerical quantity, not an SLM drive
image. The actual reconstruction is the propagated source's intensity; it is
not an intermediate image whose amplitude was forced to match the target.

**Several error quantities answer different questions.** The history is M3's
normalized squared amplitude error. Intensity MSE/NMSE compare squared
magnitudes; PSNR also requires a declared reference range. The shared image
color range does not supply that reference. None of these is percent accuracy.
Positive-infinite PSNR is an explicit exact-match outcome, not a large finite
score. A loaded regional metric retains the mask chosen for that run.

**A saved result has an identity.** Editing controls creates a new draft; it
does not change the old saved result. A deliberate submission captures settings
and input bytes together. If rendering fails after publication, the saved run
still exists and can be explicitly reopened. This is a useful example of
separating scientific computation, persistence and visualization.

**Verification has three meanings.** Integrity checks saved bytes against an
unsigned manifest and validates their structure. Qualification checks the
declared source/environment policy. Numerical comparison actually reruns and
compares outputs. A valid older run can pass integrity but be unqualified under
a newer commit, even when explicitly requested diagnostic comparison passes.
That is not automatically corruption and does not justify weakening the policy.

## Bounded exploration ideas

If relevant to the learner's current lesson, compare two intentional runs
whose seed or cycle count differs, while reading each run's saved parameters.
Observe that controls can change without automatically generating another run.
Changing pitch while keeping the built-in raster fixed can connect pixel and
physical coordinates. These are optional teaching activities, not assertions
that the learner has performed them or proofs of general convergence.

Keep the [known limitations](known_limitations.md) visible: the model is one
periodic lossless plane; the interface adds no sampling-adequacy guarantee,
calibration, hardware, new optical model or learning milestone.
