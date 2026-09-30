# Milestone 7 — Known limitations

Recorded **2026-09-30**. This document describes the approved M7 boundary;
performed validation is separately recorded in [tests and evidence](tests_and_evidence.md).

1. **A bounded content editor.** Only disks, axis-aligned rectangles and
   round-capped segments are supported through an ordered list and numeric
   controls. Text/fonts, dragging, freehand input, general transformations,
   additional compositing rules and arbitrary assets remain deferred.

2. **Center sampling, not antialiasing.** Inclusive membership and no epsilon
   expansion make exact discrete rules inspectable. Narrow/edge geometry may
   cover unexpectedly few or many centers; geometric width is not a covered
   pixel count. Binary64 evaluation is not exact real arithmetic. Endpoint
   reversal uses one internal evaluation order, without changing stored
   orientation. Unusable arithmetic raises rather than changing the geometry.

3. **Pixel authoring is distinct from physical distance.** Positive `y` is
   downward; even grids have one more negative than positive coordinate.
   Pitches reinterpret the same raster in metres. Unequal pitches can make a
   pixel disk physically elliptical. Canvas resize changes the sampled window
   and can make existing objects leave/re-enter it; no automatic repositioning,
   rescaling, deletion or wraparound occurs.

4. **Resource limits are app/model policy.** At most 512 pixels per side,
   64 objects, 256 KiB JSON, coordinate magnitudes 4096 pixels and positive
   sizes/radii up to 8192 pixels are accepted. The existing synthesis work
   budget applies separately. These limits do not guarantee adequate optical
   sampling, fast computation on every host or useful reconstruction quality.

5. **Desired intensity is not an optical field.** Values in `[0,1]` have no
   calibrated radiometric interpretation. Ordered overwrite does not simulate
   coherent source addition. Previewing does not propagate light; the actual
   reconstruction requires an explicit run. Equal source/target power is an
   explicit per-target illumination choice and does not guarantee synthesis.
   Empty/zero drawings may be stored but cannot satisfy positive-power GS.

6. **Editable storage is outside run integrity.** Design JSON and submission
   copies are not in the M5 manifest. They can be missing, malformed or
   externally replaced without invalidating intact numerical bundles. An
   explicit association compares the rendered target bytes; a UUID name alone
   is insufficient. Raster agreement proves neither original authorship nor
   a unique source drawing. Replay remains independent of this external file.

7. **Persistence can partially succeed across the two independent products.**
   A snapshot failure prevents generation. Once a snapshot is saved, later
   M5 failure retains/reports it; there is no cross-document transaction that
   rolls it back. Completed bundle persistence is recorded before presentation
   and survives render failure. Recovery never silently regenerates the run.
   The bounded new-file writer offers no database, migration, overwrite,
   locking, archive, backup or hostile concurrent-filesystem guarantee.

8. **State protection is finite.** Nonce consumption/busy handling prevents
   the tested duplicate/stale actions within an active session. It is not
   durable exactly-once operation across process crashes or multiple sessions.
   Invalid import preserves the prior editor; invalid submission must not
   borrow previous success badges. Selection alone is not an edit. Browser
   reload or design load never starts generation automatically.

9. **Existing numerical and provenance limits persist.** M3 remains the
   periodic, complete-grid, lossless single-plane model. M4 metrics and raw
   amplitude residual answer different questions, and no arbitrary hard-edge
   design receives the old Gaussian acceptance threshold. New source commits
   may make old bundles unqualified; diagnostics never upgrade qualification.
   M5's unsigned manifest and declared Git metadata are not authentication.

10. **Evidence has separate layers.** Independent small-grid checks,
    controller tests, installed AppTest and actual browser interaction prove
    their stated cases, not all possible inputs/event schedules. Genuine UI
    screenshots document their captured viewports. Precommit browser cases
    completed, including actual same-name and invalid-import recovery. Earlier
    dismissed permission requests performed no import and remain separate from
    the completed interactions; no browser settings were bypassed or changed.
    Clean-postcommit UI generation/strict replay is a later publication gate.

11. **Earlier host limitations remain.** The existing Windows file-symlink
    privilege skip is retained; a passed real-junction case does not erase it.
    M5's bounded rename retry does not promise all host access denials will
    clear. Historical M6 Proactor connection-close errors retain their
    unconfirmed cause; no dependency/server repair is part of M7.

The future virtual laboratory, physical components, remote deployment,
calibration and hardware remain separately approved roadmap work. No teaching
progress is asserted or reset.
