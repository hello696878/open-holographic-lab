# Milestone 6 — Known limitations

These limits describe the local workbench and do not authorize later work.
Current acceptance status and remaining checks are recorded in
[tests and evidence](tests_and_evidence.md) and the
[milestone ledger](../../milestones.md).

1. **Existing numerical model.** The workbench retains M3's single-plane,
   complete periodic lossless grid, equal-power requirement and finite-float64
   domain. It adds no sampling-adequacy guarantee, convergence guarantee,
   isolated-aperture model, calibrated radiometry or hardware phase encoding.

2. **Strict targets and fixed example.** Uploaded PNGs must satisfy M2 without
   implicit conversion or resizing. Blank targets are valid M2 data but fail
   positive-power synthesis. The built-in raster is fixed at 64×64 with width
   7.5 pixels; changing pitch changes physical interpretation, not its samples.

3. **Bounded app workload.** Encoded uploads are limited to 8 MiB, each grid
   dimension to 512, new cycles to 200 and
   `ny*nx*max(1,iterations)` to 13,107,200. New seeds are 0–`2**32-1`.
   Existing-bundle preflight permits at most 16 direct entries, 32 MiB per file
   and 128 MiB total. These limits are not memory/runtime guarantees or changes
   to the broader library contract. Larger valid bundles may be outside app
   policy without being corrupt.

4. **Local trusted single-user scope.** The server binds to loopback and needs
   no external service for ordinary numerical runs. It is not an authenticated
   public upload service or multiuser application. There is no cloud deployment,
   tunnel, recursive filesystem browser, archive extraction or hostile
   concurrent-filesystem security guarantee.

5. **Session-bounded submission protection.** Tokens, immutable snapshots,
   disabled controls and consumed operations protect the tested active-session
   flow. They do not provide durable exactly-once execution across crashes,
   reloads or multiple sessions. Reload/new-session behavior is deliberately
   passive. Failed or interrupted generation is not automatically retried.

6. **Synchronous computation.** The UI shows genuine stages and a spinner,
   without solver progress callbacks or invented percentages. There is no
   background queue, cancellation protocol or checkpoint/restart framework.
   Hard termination can still leave M5's reserved incomplete directory; the
   app excludes it from completed-run selection and does not repair/delete it.

7. **Saving and displaying can fail separately.** A completed M5 bundle is
   retained if summary or plot generation subsequently fails. The UI reports
   successful persistence separately and requires explicit load/refresh for
   recovery. It never erases that run or silently solves again. Before-save
   failure must not inherit an earlier result's success status.

8. **Verification describes a snapshot.** A displayed integrity or replay
   report belongs to the selected bundle and latest explicit operation. It is
   not continuous monitoring after external file changes. Corruption/errors
   are not converted into passing badges. M5 remains responsible for file
   validation; the app does not read unverified arrays for display. Separate
   load/verify/replay calls assume no concurrent external change between them;
   the UI is not an atomic filesystem-monitoring or snapshot service.

9. **Exact provenance policy remains strict.** Source detection is bounded
   Git metadata anchored to imported `ohlab`, not attestation. Dirty or absent
   metadata is visible. Old M5 bundles can remain unqualified under M6 despite
   unchanged numerical outputs. Diagnostic replay is separately requested and
   never upgrades qualification. Nonexecuted foreign-byte-order comparisons
   remain `not_run`; no casting or tolerance fallback is introduced.

10. **Display interpretation.** Color scaling is a visualization choice,
    separate from PSNR range and physical brightness. Ideal phase is not an
    SLM image. M3 residual and intensity metrics are distinct; none is percent
    accuracy. Saved regional metrics retain their original masks and do not
    automatically establish a uniformity or efficiency claim.

11. **Optional framework and finite environment evidence.** Streamlit 1.64.0
    is an optional UI dependency. Core/controller imports remain independent
    of it. Dependency resolution, preserved package versions, import probes,
    AppTest and browser operation are separate checks. A missing-UI skip is
    not evidence that UI acceptance passed. No all-platform or cross-version
    browser/plot identity is promised.

12. **Browser acceptance cannot be simulated away.** AppTest checks supported
    widget/state behavior, including the installed uploader interface, but
    does not replace real file-picker, rapid-click, layout or browser-reload
    evidence. Any required manual browser step remains pending until performed.
    Actual screenshots illustrate observed states, not proof of all states.

13. **Existing filesystem limits persist.** M5's bounded Windows rename retry
    does not guarantee host access denials disappear, cross-platform no-clobber
    concurrency or power-loss durability. The existing file-symlink test stays
    skipped where the account lacks privilege; a passed junction case does not
    relabel that skip. No elevation or environmental repair is added.

14. **Publication timing is explicit.** Precommit source is dirty/unqualified.
    A fresh clean-postcommit UI run and strict qualified replay are separate
    requirements before push. Their actual SHA/output belong to ignored
    captures and the completion report, avoiding self-referential commits.

Hardware controls, RGB, multiple depths, 3D scenes, additional optimizers,
databases, authentication, calibrated export and later milestones remain
outside this work. Teaching is separate; no lesson completion is inferred.
