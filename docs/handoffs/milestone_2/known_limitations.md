# Milestone 2 — Known limitations

Validated on 2026-09-16. These are boundaries of the implemented contract,
not authorization to begin subsequent work.

1. **Strict input subset.** Only static source 8-bit grayscale PNG (color
   type 0, decoded `L`) without transparency or APNG is accepted. RGB,
   palettes, alpha, low/high bit depths and other file formats need explicit
   conversion outside this API. No general image conversion is implemented.
2. **Exact size only.** There is no resize, interpolation, crop, pad, rotation
   or grid-pitch inference. A different input size raises an error.
3. **Design codes, not calibrated radiometry.** Gamma, profiles and exposure
   metadata are not applied. A normalized target is a specification; it is
   not an irradiance measurement.
4. **No phase or hologram.** No target class, phase assignment, complex-field
   construction, propagation, Gerchberg–Saxton, metrics, run-artifact system,
   hardware or UI is delivered. Milestone 3 remains not started.
5. **Memory buffering.** After the fixed-header check, the loader buffers the
   complete encoded file for a consistent verification/decode snapshot, then
   creates decoder storage, a uint8 copy and float64 output. It is not a
   streaming or resource-budgeted loader. File metadata/encoded size is not
   subject to a new project-specific byte quota. Existing Pillow protection
   settings are retained.
6. **Finite malformed-input coverage.** Signature/header, CRC, truncation,
   invalid compressed pixels, APNG and transparency regressions are tested.
   The loader is not a complete PNG conformance validator and does not
   promise one error class for every conceivable malformed stream.
   Existing decompression-bomb warnings/errors remain decoder diagnostics.
7. **Version evidence is specific.** Pillow 12.3.0, NumPy 2.4.6, SciPy 1.17.1,
   Python 3.11.9 and Windows were tested. The new `pillow>=10.0` declaration
   is not evidence across all permitted versions. Fresh subprocesses block
   Pillow imports; they are import-isolation checks, not an uninstalled or
   multi-version test environment. No installed package metadata was refreshed.
8. **Bounded architecture analysis.** C06 covers ordinary AST imports,
   including aliases, relative paths and nested function imports. Dynamic
   imports or arbitrary object/attribute flows are not resolved. C07 retains
   its existing scope rather than becoming a general RNG analyzer.
9. **Unchanged optical limitations.** M1's transfer function can be
   undersampled at long ranges; automatic sampling-adequacy enforcement and
   band-limited ASM remain absent. FFT periodicity and zero-padding/cropping
   trade-offs remain. Target preparation does not make a chosen propagation
   grid physically adequate, particularly at sharp image edges.
10. **Evidence has finite scope.** Five targeted mutations were tested, not
    all possible errors. Reproducible figures and sensible-looking images do
    not replace independent numerical tests. Same-platform figure hashes
    do not promise byte-identical rendering across matplotlib/font versions.
11. **GUI execution not separately exercised.** The example's default and
    explicit-path routes and matplotlib headless rendering passed. VS Code
    selection and interactive window behavior were not separately automated.
12. **Local test temporary directory.** The default Windows pytest temporary
    root denied access. A fresh ignored repository-local `--basetemp` allowed
    file-based tests without changing dependencies, permissions or test
    assertions. This environment adjustment is included in exact commands.

Historical M0/M1 documents and their dated correction record remain intact.
For interpretation of older numerical claims, consult
[the existing corrective-maintenance record](../../corrections/m0_m1_contract_and_evidence.md).
