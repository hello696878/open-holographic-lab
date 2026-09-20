# Milestone 4 — Known limitations

Recorded 2026-09-20.

1. **Declared intensity scale and alignment.** Inputs must already describe
   corresponding pixels on the same scale. There is no registration, resize,
   normalization, clipping or radiometric conversion. Values above one are
   accepted; metadata about scale cannot be inferred from bare arrays.
2. **Explicit metric meanings.** Target-normalized intensity NMSE uses a
   squared intensity norm, not optical power, NRMSE or M3's amplitude residual.
   PSNR depends on the caller's explicit reference range. No single metric is
   a percent accuracy, perceptual score or guarantee of correct reconstruction.
3. **Regions and window matter.** The user chooses the Boolean mask. The power
   fraction denominator is the supplied window; changing that window changes
   the quantity. A desired target can have power outside its declared signal
   region. Matching the fraction does not establish brightness fidelity.
4. **Uniformity requires a suitable task.** CV describes variation only inside
   the selected region. It is a uniformity diagnostic only when flat brightness
   is intended. It can exceed one and is never converted into 1-CV. The Gaussian
   demo is not labeled speckle or poor uniformity; separate flat fixtures are used.
5. **Undefined ratios fail.** Zero target squared norm, zero full-window power,
   and empty/zero-mean CV regions raise. Empty signal masks are valid with usable
   positive full power and yield zero. Exact-match PSNR intentionally returns
   positive infinity, so a downstream consumer must support that value.
6. **Finite float64 range.** Finite arrays can still produce unusable squares,
   sums, ratios or variance. NumPy-reported underflow is rejected, including
   tiny intermediates even if a larger total might remain positive. No scaling,
   epsilon, higher-precision fallback or general robust-arithmetic framework is
   added. NMSE still needs a usable target norm for identical images. Validated
   exact-match PSNR and positive-constant CV bypass unnecessary arithmetic.
7. **Existing M3 model.** Reconstruction remains a complete periodic lossless
   sampled ASM problem. M4 adds no physical sampling guarantee, hardware model,
   source-normalized efficiency, convergence guarantee or solver improvements.
8. **Finite validation.** Independent reference fixtures and seven deliberately
   incorrect mutations demonstrate specific checks, not absence of all possible
   defects. No new general image benchmark or test-count target is claimed.
9. **Environment scope.** Numerical tolerances, deterministic figures and
   headless operation were checked in the stated Windows project environment.
   Cross-platform bit identity, every dependency version and interactive VS Code
   figure-window behavior are not separately validated.

Existing implementations, tests, dependencies, historical evidence and figures
are preserved. Configuration/run-artifact export (M5), application work (M6),
hardware, GPU, RGB, multiple planes and deferred enhancements remain unstarted.
