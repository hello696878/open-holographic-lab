# Milestone 5 — Known limitations

Recorded 2026-09-23. These boundaries do not authorize later work.

1. **One bounded scientific contract.** Schema v1 covers normalized M2 target
   intensities in `[0,1]`, existing single-plane periodic lossless M3 synthesis
   and the five M4 metrics. It does not persist every possible arbitrary-scale
   M3 target, alternate solver, hardware setup or future convention. Unsupported
   versions and unknown fields fail; there is no migration framework.

2. **Existing physics and arithmetic remain unchanged.** Saving a bundle adds
   no propagation-sampling guarantee, calibrated irradiance, SLM encoding,
   convergence guarantee, registration or numerical rescaling. A valid
   `RunConfig` can still fail existing solver/metric domain checks. Blank M2
   targets are not valid positive-power M3 requests. Undefined/extreme-scale
   arithmetic remains an error. M4 results are not clipped, including finite
   fraction roundoff slightly above one.

3. **Integrity is relative to an unsigned manifest.** Hashes detect changed
   artifact bytes when checked against the retained manifest. They do not
   establish authorship or prevent a party replacing both artifacts and hashes.
   Integrity/schema validation also does not establish metric correctness;
   replay performs semantic derivation and metric checks separately.

4. **Qualification is metadata policy, not attestation.** The API accepts
   explicitly labeled caller provenance and never invokes Git. A supplied SHA
   does not prove which source executed. The example's Git detector anchors to
   the imported package checkout and records dirty state, but is not a code-
   signing system. Both clean equal revisions, package version and required
   runtime fields must match. Executable path, CPU count and provenance method
   are visible information rather than equality gates.

5. **No universal replay guarantee.** Exact array/scalar comparisons apply to
   the tested environment and declared criterion. Matching metadata does not
   guarantee every OS, CPU, dependency build, FFT implementation or future
   version is bit-identical. Unqualified default replay is `not_run`.
   Diagnostic mode never upgrades qualification and has no tolerance fallback.
   A numerical/domain error can raise instead of producing a comparison report.

6. **NPY and ownership are intentionally narrow.** Only NPY 1.0 C-order simple
   role-defined dtypes are accepted, with a bounded header and exact payload
   length. This is not a general NumPy file loader. Foreign byte order can be
   inspected without conversion, but diagnostic numerical replay fails its
   native-byte-order gate and reports comparison `not_run`. Read-only ndarray
   flags follow the project's normal
   ownership convention, not a security boundary against deliberate flag
   changes or Python internals. Concurrent mutation during initial caller-array
   capture is not made atomic across all inputs.

7. **Finite resource and path scope.** Whole encoded files and numerical arrays
   are buffered. There is no global file-size, memory-budget or hostile-input
   resource-management framework. Filenames are a strict flat allowlist;
   bundle roots and direct entries reject links/reparse points. This is not
   complete hardening against concurrent malicious filesystem replacement or
   every ancestor-path race. Arbitrary archives and extraction are unsupported.
   The host lacked privilege to create a real file symlink, so that specific
   filesystem check was skipped. A real Windows junction rejection check
   passed; this does not replace the skipped file-symlink case.

8. **PNG provenance has a defined boundary.** At save time, exact copied PNG
   bytes are decoded with public M2 and compared with captured target bits.
   Loading/replay later hashes the retained copy but does not decode it again.
   Numerical replay uses saved amplitudes and never needs the external original
   PNG path. PNG capture requires the optional existing decoder; array-only
   runs do not. Declared Pillow versions participate in PNG-run qualification.

9. **Publication covers ordinary failures on the tested Windows filesystem.**
   The parent directory must exist; destinations are not intentionally
   overwritten. Exclusive sibling staging, file fsync, verification and rename
   do not provide a power-loss durability or cross-filesystem fallback guarantee.
   POSIX concurrent-writer no-clobber semantics are not promised. There is no
   locking/job-management system. A killed process can leave a reserved partial
   directory, which public readers reject. Cleanup preserves its original
   exception and reports leftover staging when owned-file removal fails; it
   does not recursively delete unrelated entries.

   Candidate focused/full-suite validation intermittently encountered ordinary
   directory-rename `WinError 5` in different fixtures, including an
   outside-sandbox full-suite run. A separate 100-save probe passed without
   reproducing the denial. No handle leak or cause was identified. The bounded
   response retries only Windows `PermissionError.winerror == 5` while the
   destination is absent, for at most four attempts with 10/30/100 ms waits.
   Destination appearance stops retries; other errors are not retried;
   exhaustion preserves the first access-denial error. The 140 ms maximum
   explicit wait is not a guarantee that host access denial will clear.
   There is no overwrite, lock or cross-filesystem copy fallback. See
   [tests and evidence](tests_and_evidence.md) for the observed failures,
   isolated probe and direct retry-safety checks.

10. **Evidence is finite and provenance timing is explicit.** Tests, failure
    injection, isolated controls and fresh-process relocation demonstrate the
    stated cases, not absence of all defects. Candidate runs before commit are
    dirty/unqualified. A fresh clean-postcommit example is a separate required
    publication check, recorded in ignored captures and the completion report.
    No clean final revision is fabricated in this handoff. See
    [tests and evidence](tests_and_evidence.md) for exact commands and outcomes.

The two figures explain roles and verification flow; they are not bundle
artifacts or numerical correctness evidence. M6, migration, cloud storage,
databases, preview export, hardware and deferred enhancements remain unstarted.
