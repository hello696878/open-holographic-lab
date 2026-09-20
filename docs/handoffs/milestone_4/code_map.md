# Milestone 4 — Code map

Only the approved fifteen paths belong to M4. Existing numerical source,
tests, root initializer, shared validation utilities, dependency declarations,
engineering instructions, M0-M3 evidence, examples and figures are protected.

## Numerical module

`src/ohlab/metrics.py` exports exactly five keyword-only functions:

- `intensity_mse`: validated direct squared intensity error divided by count.
- `intensity_nmse`: error divided by usable positive target squared norm.
- `intensity_psnr`: validated exact numerical equality, otherwise log-domain
  PSNR with explicit range and usable positive MSE.
- `signal_region_power_fraction`: explicit ROI sum divided by full-window sum.
- `regional_intensity_cv`: explicit-region population variation, with an exact
  positive-constant identity shortcut.

Private helpers validate plain native arrays, comparisons and Boolean masks;
check nonnegative/positive finite scalars; and evaluate squared error/MSE.
They reuse existing public validators without modifying them. NumPy error
contexts are local. There is no file I/O, plotting, RNG, solver integration
wrapper, global configuration or root re-export in this module.

## Tests and independent evidence

`tests/test_metrics.py` owns M4 contract, hand-array, Decimal, scaling, domain,
ownership, error-setting and small actual-M3 integration checks. The expected
scores come from analytic values or independent scalar/high-precision sums.
Existing test files remain unchanged. The pre-existing architecture guard
automatically scans the new numerical module.

The exact isolated-mutation driver and reference measurement command are
preserved in `tests_and_evidence.md`. They are validation code, not alternate
production metrics or a new framework. Mutations occur only in fresh process
memory and source/test byte hashes are checked before and after.

## Example and figure generation

`examples/evaluate_reconstruction.py` constructs the fixed M2 intensity arrays,
explicitly configures source illumination and mask, invokes unchanged M3,
evaluates actual reconstruction intensity, and provides the three fixed flat
fixtures. It prints labeled scores and supports `--no-show` for headless use.
Its small figure helpers live outside the numerical core.

`scripts/make_m4_figures.py` reuses the example's fixed cases and plotting code
and writes only:

- `docs/handoffs/milestone_4/figures/fig01_m3_intensity_comparisons.png`
- `docs/handoffs/milestone_4/figures/fig02_region_power_and_variation.png`

It does not create a run bundle, configuration system or application server.

## Documentation

- `README.md`: usage, imports, interpretation, runnable example and handoff link.
- `docs/math_conventions.md`: version 0.7, new §3.14 and narrow §2.1 intensity
  scale clarification, without changing field normalization or units.
- `docs/milestones.md`: M4 scope/acceptance, with historical entries preserved.
- This directory: implementation summary, code map, mathematics, exact test
  evidence, limitations, and context for a separate tutor.

M5 and M6 remain outside this implementation.
