# V2c tests and evidence

Recorded 2026-10-06; accepted baseline `886cdac549dcd4373be7d24f9f2211af03659371`. This is precommit numerical acceptance. Publication is a later, separately recorded gate; no future result is asserted here.

## Provenance and preserved starting state

Clean `main`, upstream `origin/main`, ahead/behind 0/0 and live remote matched the required baseline before editing. The complete twelve local planning/probe records were read and SHA-256 captured in `runs/v2c_acceptance_20261006_01/planning_readback.json`, with their recorded source checked. They remain planning evidence, distinct from the shipped measurements below. Fresh owned ignored evidence is `runs/v2c_acceptance_20261006_01/`; command JSON, original stdout/stderr, exits, hashes, arrays and copied mutations remain there. Essential oracle/probe/control code is committed in the approved scripts. No environment change or dependency installation occurred.

```json
{
  "interpreter": "C:\\holographiclab\\.venv\\Scripts\\python.exe",
  "python": "3.11.9",
  "numpy": "2.4.6",
  "scipy": "1.17.1",
  "platform": "Windows-10-10.0.26100-SP0",
  "polarization_source": "C:\\holographiclab\\src\\ohlab\\optics\\polarization.py",
  "source_sha256": "48779f28cc194488bc8ac11e96196f848663ec16e86c9f1f97388af88b801de2",
  "reference_source_sha256": "ce155695031a69e591ba65b29671f433b82c90289e395dfe3f079eb881b7dc73"
}
```

## Fresh baseline and complete restored suite

Bytecode and pytest cache writes were disabled; each run had its own fresh ignored basetemp. The old numerical/tests/guards were preserved. This unchanged baseline completed before any implementation edits:

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --basetemp C:\holographiclab\runs\v2c_acceptance_20261006_01\baseline_tmp -rs
```

Exact unedited stdout (line ending representation only):

```text
........................................................................ [  3%]
........................................................................ [  6%]
........................................................................ [ 10%]
........................................................................ [ 13%]
........................................................................ [ 17%]
........................................................................ [ 20%]
........................................................................ [ 24%]
........................................................................ [ 27%]
........................................................................ [ 31%]
........................................................................ [ 34%]
........................................................................ [ 38%]
........................................................................ [ 41%]
........................................................................ [ 45%]
........................................................................ [ 48%]
........................................................................ [ 51%]
........................................................................ [ 55%]
........................................................................ [ 58%]
........................................................................ [ 62%]
..............................................................s......... [ 65%]
........................................................................ [ 69%]
........................................................................ [ 72%]
........................................................................ [ 76%]
........................................................................ [ 79%]
........................................................................ [ 83%]
........................................................................ [ 86%]
........................................................................ [ 90%]
........................................................................ [ 93%]
........................................................................ [ 96%]
................................................................         [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
2079 passed, 1 skipped in 257.50s (0:04:17)
```

Stderr: empty. Exit 0.

Initial new focused suite was `272 passed in 1.01s`; it is preserved in `focused_initial_*`. Five bounded model/underflow cases were added after review; no old tests changed. The final focused result was:

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --basetemp C:\holographiclab\runs\v2c_acceptance_20261006_01\focused_final_tmp tests/test_polarization_model.py tests/test_polarization_primitives.py tests/test_polarization_analytic.py tests/test_polarization_architecture.py -rs
```

Exact unedited stdout (line ending representation only):

```text
........................................................................ [ 25%]
........................................................................ [ 51%]
........................................................................ [ 77%]
.............................................................            [100%]
277 passed in 1.08s
```

Stderr: empty. Exit 0.

After all fifteen fault variants and exact restoration, the complete suite was:

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --basetemp C:\holographiclab\runs\v2c_acceptance_20261006_01\final_suite_tmp -rs
```

Exact unedited stdout (line ending representation only):

```text
........................................................................ [  3%]
........................................................................ [  6%]
........................................................................ [  9%]
........................................................................ [ 12%]
........................................................................ [ 15%]
........................................................................ [ 18%]
........................................................................ [ 21%]
........................................................................ [ 24%]
........................................................................ [ 27%]
........................................................................ [ 30%]
........................................................................ [ 33%]
........................................................................ [ 36%]
........................................................................ [ 39%]
........................................................................ [ 42%]
........................................................................ [ 45%]
........................................................................ [ 48%]
........................................................................ [ 51%]
........................................................................ [ 54%]
........................................................................ [ 58%]
........................................................................ [ 61%]
........................................................................ [ 64%]
........................................................................ [ 67%]
...................................................s.................... [ 70%]
........................................................................ [ 73%]
........................................................................ [ 76%]
........................................................................ [ 79%]
........................................................................ [ 82%]
........................................................................ [ 85%]
........................................................................ [ 88%]
........................................................................ [ 91%]
........................................................................ [ 94%]
........................................................................ [ 97%]
.....................................................                    [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
2356 passed, 1 skipped in 113.31s (0:01:53)
```

Stderr: empty. Exit 0.

The one skip in both full runs is unchanged: `tests/test_run_artifacts.py:1101`, this Windows account lacks file-symlink privilege; junction behavior is tested separately. No test edits or privilege elevation removed it. Baseline 2080 and final 2357 cases differ by 277 new tests, including parametrizations. No scientific acceptance command failed. Figure visual review did identify layout overlap and required the bounded rendering correction described below.

## Independent validation and tolerance measurement

Expected complex arrays use literal hand fixtures and independently expanded scalar coefficients, not production matrix/application helpers. Intensity expectations use separate real/imaginary squares; norm/ratio expectations reduce independently. Unitarity is observed through public x/y basis-field actions without exposing a new matrix API. No phase fit, normalization, tolerance relaxation, modulo wrapping or output clipping was used.

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 scripts\validate_v2c_polarization.py --output-dir runs\v2c_acceptance_20261006_01\validation
```

Exact unedited stdout (line ending representation only):

```text
{
  "acceptance_passed": true,
  "output": "C:\\holographiclab\\runs\\v2c_acceptance_20261006_01\\validation\\validation.json",
  "shape": [
    32,
    32
  ],
  "malus_cases": 13,
  "weak_cases": 5,
  "maxima": {
    "complex_input_scaled_error": 2.479436791899844e-16,
    "malus_absolute_error": 2.220446049250313e-16,
    "unitarity_entry_error": 4.440892098500626e-16,
    "inverse_input_scaled_error": 4.512643077139003e-16,
    "common_phase_covariance_input_scaled_error": 2.479436791899844e-16,
    "polarizer_idempotence_input_scaled_error": 1.142963886598413e-16,
    "retarder_relative_norm_error": 4.640716422278097e-16,
    "selected_weak_relative_error": 2.0194839179460514e-16
  }
}
```

Stderr: empty. Exit 0.

| Quantity | rtol | atol |
| --- | --- | --- |
| Matrix unitarity | 0 | 2e-15 |
| Complex components | 2e-14 | 2e-14*Ain |
| Intensity | 2e-13 | 2e-13*Ain^2 |
| Sampled norm | 2e-13 | 2e-13*Nin |
| Ratio | 2e-13 | 2e-13 |
| Selected weak components/intensity/ratio | 2e-14 | 1e-48 |
| Selected weak sampled norm | 2e-14 | 1e-48*Nin |

Ain is the maximum incident component amplitude; Nin is the independently calculated combined incident norm. These measured fixture bounds preserve both relative and absolute terms. Exact comparisons apply only to declared identities, zero input, ratio-four literal arithmetic, source restoration and same-platform repeatability.

| Measured discrepancy | Maximum |
| --- | --- |
| complex_input_scaled_error | 2.479436791899844e-16 |
| malus_absolute_error | 2.220446049250313e-16 |
| unitarity_entry_error | 4.440892098500626e-16 |
| inverse_input_scaled_error | 4.512643077139003e-16 |
| common_phase_covariance_input_scaled_error | 2.479436791899844e-16 |
| polarizer_idempotence_input_scaled_error | 1.142963886598413e-16 |
| retarder_relative_norm_error | 4.640716422278097e-16 |
| selected_weak_relative_error | 2.0194839179460514e-16 |

All 35 retarder cases use an asymmetric3x4 spatial fixture, seven axes and five retardances, alongside inverse, common-phase covariance, component intensity, loss/conservation and polarizer idempotence/contraction tests. This is finite-case evidence, not universal physical or arbitrary-dynamic-range accuracy.

## All thirteen Malus points

Rows below are actual shipped64x64 polarizer outputs. The converted binary64 angles are used as supplied. The 32x32 case retains the same complete set. Intensity fraction is computed from the vector output, not by multiplying the incident field amplitude by cos-squared.

| Degrees | Actual radians | Angle hex | Actual norm ratio | Independent cos-squared |
| --- | --- | --- | --- | --- |
| -90 | -1.5707963267948966 | -0x1.921fb54442d18p+0 | 3.749399456654644e-33 | 3.749399456654644e-33 |
| -75 | -1.3089969389957472 | -0x1.4f1a6c638d03fp+0 | 0.06698729810778067 | 0.06698729810778066 |
| -60 | -1.0471975511965976 | -0x1.0c152382d7365p+0 | 0.25000000000000006 | 0.2500000000000001 |
| -45 | -0.7853981633974483 | -0x1.921fb54442d18p-1 | 0.5000000000000001 | 0.5000000000000001 |
| -30 | -0.5235987755982988 | -0x1.0c152382d7365p-1 | 0.75 | 0.7500000000000001 |
| -15 | -0.2617993877991494 | -0x1.0c152382d7365p-2 | 0.9330127018922192 | 0.9330127018922194 |
| 0 | 0.0 | 0x0.0p+0 | 1.0 | 1.0 |
| 15 | 0.2617993877991494 | 0x1.0c152382d7365p-2 | 0.9330127018922192 | 0.9330127018922194 |
| 30 | 0.5235987755982988 | 0x1.0c152382d7365p-1 | 0.75 | 0.7500000000000001 |
| 45 | 0.7853981633974483 | 0x1.921fb54442d18p-1 | 0.5000000000000001 | 0.5000000000000001 |
| 60 | 1.0471975511965976 | 0x1.0c152382d7365p+0 | 0.25000000000000006 | 0.2500000000000001 |
| 75 | 1.3089969389957472 | 0x1.4f1a6c638d03fp+0 | 0.06698729810778067 | 0.06698729810778066 |
| 90 | 1.5707963267948966 | 0x1.921fb54442d18p+0 | 3.749399456654644e-33 | 3.749399456654644e-33 |

## Selected weak signals

The bounded stdlib oracle evaluates direct Taylor sin/cos with 80-digit Decimal arithmetic at `Decimal.from_float(actual_angle)`; each case converged in 38 terms. It does not use epsilon-squared or rounded-pi subtraction. The reference source retains the exact binary64 angle, hex, Decimal components and reference intensity. Positivity and components/intensity/norm/ratio are asserted separately, with signal-appropriate bounds; generic 2e-13 atol alone would not detect a clipped 1e-18 fraction.

| Offset rad | Actual radians | Angle hex |
| --- | --- | --- |
| -1e-06 | 1.5707953267948966 | 0x1.921fa47d4b30dp+0 |
| -1e-09 | 1.5707963257948965 | 0x1.921fb53ff74e8p+0 |
| 0.0 | 1.5707963267948966 | 0x1.921fb54442d18p+0 |
| 1e-09 | 1.5707963277948966 | 0x1.921fb5488e548p+0 |
| 1e-06 | 1.5707973267948965 | 0x1.921fc60b3a723p+0 |

| Offset | Actual Ux real | Actual Uy real | Actual I | Actual N | Actual T |
| --- | --- | --- | --- | --- | --- |
| -1e-06 | 9.999999999575979e-13 | 9.99999999978299e-07 | 9.99999999957598e-13 | 6.213631999736532e-20 | 9.999999999575983e-13 |
| -1e-09 | 1.0000002879454427e-18 | 1.000000143972711e-09 | 1.0000002879454427e-18 | 6.213633789187017e-26 | 1.0000002879454427e-18 |
| 0.0 | 3.749399456654644e-33 | 6.123233995736766e-17 | 3.749399456654644e-33 | 2.329738844465191e-40 | 3.749399456654644e-33 |
| 1e-09 | 1.0000000430160625e-18 | -1.000000021508031e-09 | 1.0000000430160625e-18 | 6.213632267285982e-26 | 1.0000000430160623e-18 |
| 1e-06 | 9.999999997126686e-13 | -9.999999998558343e-07 | 9.999999997126686e-13 | 6.21363199821463e-20 | 9.999999997126688e-13 |

Imaginary components are zero or signed zero. Intensity units are amplitude-unit², norm units amplitude-unit²*m², and T dimensionless. Norms above belong to 64² inputN=6.213632e-08;32² norms are one quarter. All represented weak components in magnitude and all three weak diagnostics are positive, including the floating-pi/2 residual.

| Offset | x relative error | y relative error | I relative error | N relative error | T relative error |
| --- | --- | --- | --- | --- | --- |
| -1e-06 | 2.01948391745142e-16 | 0.0 | 0.0 | 1.9372022921426015e-16 | 2.01948391745142e-16 |
| -1e-09 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 1e-09 | 0.0 | 0.0 | 0.0 | 1.8474599921509257e-16 | 1.9259298615413165e-16 |
| 1e-06 | 0.0 | 0.0 | 0.0 | 1.9372022926170797e-16 | 2.0194839179460514e-16 |

This proves retention/accuracy of the five predeclared represented signals, not relative accuracy over arbitrary dynamic ranges. Exact dark input remains a separate test, with zero norm and undefined (`None`) ratio. Strict ratio division rejects NumPy-reported underflow even if an inexact positive subnormal survives; local caller error settings are restored on success/failure.

## Literal phase and operation-order evidence

| Fixture | Actual [Ux,Uy] as [real,imag] | Independent expected | Max complex discrepancy |
| --- | --- | --- | --- |
| P0_11 | [[1.0, 0.0], [0.0, 0.0]] | [[1.0, 0.0], [0.0, 0.0]] | 0.0 |
| P90_11 | [[6.123233995736766e-17, 0.0], [1.0, 0.0]] | [[0.0, 0.0], [1.0, 0.0]] | 6.123233995736766e-17 |
| QWP0_linear45 | [[0.7071067811865475, 0.0], [4.329780281177466e-17, 0.7071067811865475]] | [[0.7071067811865475, 0.0], [0.0, 0.7071067811865475]] | 4.329780281177466e-17 |
| HWP_pi8_x | [[0.7071067811865475, 1.7934537145592996e-17], [0.7071067811865476, -4.3297802811774664e-17]] | [[0.7071067811865475, 0.0], [0.7071067811865475, 0.0]] | 1.1916648594468846e-16 |
| QWP45_x | [[0.5000000000000001, 0.5000000000000001], [0.5000000000000001, -0.5000000000000001]] | [[0.5, 0.5], [0.5, -0.5]] | 1.5700924586837752e-16 |

The rotated-QWP expected output is `((1+i)/2,(1-i)/2)`; its common phase is retained. Order uses actual nested public operations on x input, with unchanged independent literal references:

| Order | Actual components [real,imag] | Norm ratio | Max complex discrepancy |
| --- | --- | --- | --- |
| P_then_W | [[0.5000000000000001, 0.5000000000000001], [0.5000000000000001, -0.5000000000000001]] | 1.0000000000000002 | 1.5700924586837752e-16 |
| W_then_P | [[0.5000000000000001, 0.5000000000000001], [0.0, 0.0]] | 0.5000000000000001 | 1.5700924586837752e-16 |

Crossed ratio: `3.749399456654644e-33`; three-polarizer ratio: `0.25000000000000006` for already x-polarized input, not unpolarized illumination. Coefficients `(2+0.5j,-0.7+1j)` preserve exact expected component products and give `5.739999999999999` versus mathematical 5.74. The independently constructed doubled-amplitude output gives ratio `4.0`; this diagnostic cannot certify passive gain or a causal transformation. Passive contraction and ideal-retarder conservation are tested independently.

## Fifteen actual scientific negative controls

The harness copies the package and selected new assertions into fresh owned ignored directories. Production is never mutated. The order fault changes only the copied actual nested composition, leaving its literal expectation unchanged. Each worker verifies its imported copied source location. Exit 10 exclusively means the selected scientific AssertionError; setup/import/validation/nonassertion failures have a separate exit 20 and never count.

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 scripts\v2c_negative_controls.py --output-dir runs\v2c_acceptance_20261006_01\negative_controls
```

Exact unedited stdout (line ending representation only):

```text
scalar_sum_intensity: original=0 mutant=10 restored=0 scientific_detection=True exact_restoration=True
cos_squared_amplitude: original=0 mutant=10 restored=0 scientific_detection=True exact_restoration=True
missing_imaginary_qwp: original=0 mutant=10 restored=0 scientific_detection=True exact_restoration=True
reversed_retardance_sign: original=0 mutant=10 restored=0 scientific_detection=True exact_restoration=True
wrong_axis_convention: original=0 mutant=10 restored=0 scientific_detection=True exact_restoration=True
reversed_element_order: original=0 mutant=10 restored=0 scientific_detection=True exact_restoration=True
normalize_polarizer_loss: original=0 mutant=10 restored=0 scientific_detection=True exact_restoration=True
drop_x_component: original=0 mutant=10 restored=0 scientific_detection=True exact_restoration=True
drop_y_component: original=0 mutant=10 restored=0 scientific_detection=True exact_restoration=True
swap_xy_components: original=0 mutant=10 restored=0 scientific_detection=True exact_restoration=True
reset_input_common_phase: original=0 mutant=10 restored=0 scientific_detection=True exact_restoration=True
reset_coefficient_relative_phase: original=0 mutant=10 restored=0 scientific_detection=True exact_restoration=True
retarder_common_phase_variant: original=0 mutant=10 restored=0 scientific_detection=True exact_restoration=True
truncate_weak_intensity: original=0 mutant=10 restored=0 scientific_detection=True exact_restoration=True
truncate_weak_ratio: original=0 mutant=10 restored=0 scientific_detection=True exact_restoration=True
{
  "executed_variants": 15,
  "acceptance_passed": true,
  "production_unchanged": true
}
```

Stderr: empty. Exit 0.

| Actual variant | Affected copied path | Selected assertion | Original/mutant/restored exits | Exact restoration |
| --- | --- | --- | --- | --- |
| scalar_sum_intensity | src/ohlab/optics/polarization.py | test_total_intensity_sums_orthogonal_component_intensities | 0 / 10 / 0 | True |
| cos_squared_amplitude | src/ohlab/optics/polarization.py | test_malus_sweep_all_declared_angles | 0 / 10 / 0 | True |
| missing_imaginary_qwp | src/ohlab/optics/polarization.py | test_qwp_axis_zero_preserves_imaginary_phase | 0 / 10 / 0 | True |
| reversed_retardance_sign | src/ohlab/optics/polarization.py | test_qwp_axis_zero_preserves_imaginary_phase | 0 / 10 / 0 | True |
| wrong_axis_convention | src/ohlab/optics/polarization.py | test_hwp_nontrivial_axis_preserves_selected_phase | 0 / 10 / 0 | True |
| reversed_element_order | tests/test_polarization_analytic.py | test_noncommuting_order_has_distinct_complex_outputs | 0 / 10 / 0 | True |
| normalize_polarizer_loss | src/ohlab/optics/polarization.py | test_malus_sweep_all_declared_angles | 0 / 10 / 0 | True |
| drop_x_component | src/ohlab/optics/polarization.py | test_retarder_expanded_complex_reference_inverse_and_norm | 0 / 10 / 0 | True |
| drop_y_component | src/ohlab/optics/polarization.py | test_retarder_expanded_complex_reference_inverse_and_norm | 0 / 10 / 0 | True |
| swap_xy_components | src/ohlab/optics/polarization.py | test_retarder_expanded_complex_reference_inverse_and_norm | 0 / 10 / 0 | True |
| reset_input_common_phase | src/ohlab/optics/polarization.py | test_from_scalar_preserves_arbitrary_common_and_relative_phase | 0 / 10 / 0 | True |
| reset_coefficient_relative_phase | src/ohlab/optics/polarization.py | test_from_scalar_preserves_arbitrary_common_and_relative_phase | 0 / 10 / 0 | True |
| retarder_common_phase_variant | src/ohlab/optics/polarization.py | test_qwp_rotated_axis_preserves_selected_common_phase | 0 / 10 / 0 | True |
| truncate_weak_intensity | src/ohlab/optics/polarization.py | test_weak_extinction_retains_positive_components_and_diagnostics | 0 / 10 / 0 | True |
| truncate_weak_ratio | src/ohlab/optics/polarization.py | test_weak_extinction_retains_positive_components_and_diagnostics | 0 / 10 / 0 | True |

Executed 15 variants, including separate droppedx/droppedy/swap, common/relative resets and weak-intensity/weak-ratio truncations. All 15 had passing originals, intended scientific failures on valid records, exact copied byte restoration and passing restored assertions. Production tracked+new-file SHA inventory matched before/after. Mutated sources, commands, tracebacks and hashes are preserved per variant under `negative_controls/`. The full 2356-pass/1-skip restored suite above ran afterward. Specific detections are not an exhaustive correctness proof.

## Actual64² and 32² demonstration/resource measurements

Each demo retains 81 arrays: complete components/intensity for every Malus/weak point and declared fixture, five 257-point sample ellipses and tau. Samples are row/column(n//2,n//2), x=y=0 m; traces are actual `Re([Ux,Uy]*exp(-i*tau))`, unscaled/unfitted, with equal component axes and+y downward. Tau is dimensionless optical phase. These are numerical teaching figures, not V2d screenshots, unpolarized experiments, calibrated measurements or a persistence schema.

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 examples\jones_polarization.py --n 64 --output-dir runs\v2c_acceptance_20261006_01\demo64
```

Exact unedited stdout (line ending representation only):

```text
{
  "acceptance_passed": true,
  "output": "C:\\holographiclab\\runs\\v2c_acceptance_20261006_01\\demo64",
  "shape": [
    64,
    64
  ],
  "malus_points": 13,
  "weak_points": 5,
  "crossed_ratio": 3.749399456654644e-33,
  "three_polarizers_ratio": 0.25000000000000006,
  "maxima": {
    "complex_input_scaled_error": 2.479436791899844e-16,
    "malus_absolute_error": 2.220446049250313e-16,
    "unitarity_entry_error": 4.440892098500626e-16,
    "inverse_input_scaled_error": 4.512643077139003e-16,
    "common_phase_covariance_input_scaled_error": 2.479436791899844e-16,
    "polarizer_idempotence_input_scaled_error": 1.142963886598413e-16,
    "retarder_relative_norm_error": 4.640716422278097e-16,
    "selected_weak_relative_error": 2.0194839179460514e-16
  },
  "resources": {
    "shape": [
      64,
      64
    ],
    "iterations": 20,
    "element_applications": 40,
    "polarizer_axis_rad": 0.37,
    "retarder_axis_rad": 0.61,
    "retardance_rad": 0.83,
    "wall_seconds": 0.009327700012363493,
    "wall_seconds_per_two_element_application": 0.00046638500061817466,
    "traced_current_bytes": 133387,
    "traced_peak_bytes": 889643,
    "process_before": {
      "working_set_bytes": 44335104,
      "private_bytes": 840523776,
      "process_lifetime_peak_working_set_bytes": 44335104
    },
    "process_after": {
      "working_set_bytes": 44797952,
      "private_bytes": 840925184,
      "process_lifetime_peak_working_set_bytes": 44797952
    },
    "input_component_array_bytes": 131072,
    "final_component_array_bytes": 131072,
    "final_sampled_norm": 2.2868022467814077e-07,
    "measurement_scope": "single observation of shipped public operations, input/reference/serialization excluded; traced allocations, instantaneous whole-process values and lifetime peaks are distinct, not portable guarantees"
  }
}
```

Stderr: empty. Exit 0.

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 examples\jones_polarization.py --n 32 --output-dir runs\v2c_acceptance_20261006_01\demo32
```

Exact unedited stdout (line ending representation only):

```text
{
  "acceptance_passed": true,
  "output": "C:\\holographiclab\\runs\\v2c_acceptance_20261006_01\\demo32",
  "shape": [
    32,
    32
  ],
  "malus_points": 13,
  "weak_points": 5,
  "crossed_ratio": 3.749399456654644e-33,
  "three_polarizers_ratio": 0.25000000000000006,
  "maxima": {
    "complex_input_scaled_error": 2.479436791899844e-16,
    "malus_absolute_error": 2.220446049250313e-16,
    "unitarity_entry_error": 4.440892098500626e-16,
    "inverse_input_scaled_error": 4.512643077139003e-16,
    "common_phase_covariance_input_scaled_error": 2.479436791899844e-16,
    "polarizer_idempotence_input_scaled_error": 1.142963886598413e-16,
    "retarder_relative_norm_error": 4.640716422278097e-16,
    "selected_weak_relative_error": 2.0194839179460514e-16
  },
  "resources": {
    "shape": [
      32,
      32
    ],
    "iterations": 20,
    "element_applications": 40,
    "polarizer_axis_rad": 0.37,
    "retarder_axis_rad": 0.61,
    "retardance_rad": 0.83,
    "wall_seconds": 0.007568500004708767,
    "wall_seconds_per_two_element_application": 0.00037842500023543835,
    "traced_current_bytes": 35083,
    "traced_peak_bytes": 226091,
    "process_before": {
      "working_set_bytes": 39895040,
      "private_bytes": 835878912,
      "process_lifetime_peak_working_set_bytes": 39895040
    },
    "process_after": {
      "working_set_bytes": 40292352,
      "private_bytes": 836415488,
      "process_lifetime_peak_working_set_bytes": 40292352
    },
    "input_component_array_bytes": 32768,
    "final_component_array_bytes": 32768,
    "final_sampled_norm": 5.717005616953519e-08,
    "measurement_scope": "single observation of shipped public operations, input/reference/serialization excluded; traced allocations, instantaneous whole-process values and lifetime peaks are distinct, not portable guarantees"
  }
}
```

Stderr: empty. Exit 0.

| Size | Scientific demo seconds, excluding resource/serialization | 20 two-element applications seconds | Traced current / peak bytes | Working set before / after bytes | Private bytes before / after |
| --- | --- | --- | --- | --- | --- |
| 64² | 0.1615571000147611 | 0.009327700012363493 | 133387 / 889643 | 44335104 / 44797952 | 840523776 / 840925184 |
| 32² | 0.144342300016433 | 0.007568500004708767 | 35083 / 226091 | 39895040 / 40292352 | 835878912 / 836415488 |

The timed interval contains 40 actual element actions: 20 independent P(.37)->W(.61,.83) pairs, each starting from the same incident. Input construction/reference/serialization are excluded. Tracemalloc observations can include tracked NumPy buffers but are not all native/process memory. Windows working-set/private values are instantaneous whole-process observations; process-lifetime working-set peaks printed above have a different scope. Array-byte counts are exact storage accounting, not memory measurements. Timings were single observations while acceptance processes ran, not a benchmark or portable guarantee. Planning arithmetic probes are not substituted for these shipped runs.

## Figure inspection and regeneration

Initial rendering commands exited0 and numerical/source/array checks passed, but visual inspection found overlapping main/subplot titles in figures2/3. Initial PNGs, hashes and stdout remain under `figures_initial_layout/`, `figure_initial_inspection.json` and `figures_*`. Only layout rectangle/title/subtitle positions and legend clearance changed; numerical arrays/reference bounds did not. Final versions were all viewed and passed legibility, axis/phase/direction/amplitude checks. Fresh regeneration recomputed all saved arrays byte-identically, then produced identical PNG bytes:

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 scripts\generate_v2c_figures.py --evidence-dir runs\v2c_acceptance_20261006_01\demo64 --output-dir docs\handoffs\v2c\figures
```

Exact unedited stdout (line ending representation only):

```text
{
  "evidence": "C:\\holographiclab\\runs\\v2c_acceptance_20261006_01\\demo64",
  "evidence_sha256": "cd8327a605cf8b43e338823f98f9d6f04a050aac21195f045a30276bd8e70f55",
  "figures": {
    "fig01_malus_and_loss.png": {
      "path": "C:\\holographiclab\\docs\\handoffs\\v2c\\figures\\fig01_malus_and_loss.png",
      "sha256": "1b0828ee4124fd10804b5c65f5af581557d37f59ad76565bef7174edf18ab53d"
    },
    "fig02_retarders_and_components.png": {
      "path": "C:\\holographiclab\\docs\\handoffs\\v2c\\figures\\fig02_retarders_and_components.png",
      "sha256": "0a672c4cd7b6b32b812fca05874d16ff2c577683db8b8e24d7f8b5ea1868a018"
    },
    "fig03_polarization_ellipses.png": {
      "path": "C:\\holographiclab\\docs\\handoffs\\v2c\\figures\\fig03_polarization_ellipses.png",
      "sha256": "6d514c832e6cb141a66a19b2c1f65eb772020323cd0201a1a2e4fa9fd10196fd"
    }
  },
  "saved_arrays_recomputed_byte_identically": true
}
```

Stderr: empty. Exit 0.

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 scripts\generate_v2c_figures.py --evidence-dir runs\v2c_acceptance_20261006_01\demo64 --output-dir runs\v2c_acceptance_20261006_01\figure_regeneration
```

Exact unedited stdout (line ending representation only):

```text
{
  "evidence": "C:\\holographiclab\\runs\\v2c_acceptance_20261006_01\\demo64",
  "evidence_sha256": "cd8327a605cf8b43e338823f98f9d6f04a050aac21195f045a30276bd8e70f55",
  "figures": {
    "fig01_malus_and_loss.png": {
      "path": "C:\\holographiclab\\runs\\v2c_acceptance_20261006_01\\figure_regeneration\\fig01_malus_and_loss.png",
      "sha256": "1b0828ee4124fd10804b5c65f5af581557d37f59ad76565bef7174edf18ab53d"
    },
    "fig02_retarders_and_components.png": {
      "path": "C:\\holographiclab\\runs\\v2c_acceptance_20261006_01\\figure_regeneration\\fig02_retarders_and_components.png",
      "sha256": "0a672c4cd7b6b32b812fca05874d16ff2c577683db8b8e24d7f8b5ea1868a018"
    },
    "fig03_polarization_ellipses.png": {
      "path": "C:\\holographiclab\\runs\\v2c_acceptance_20261006_01\\figure_regeneration\\fig03_polarization_ellipses.png",
      "sha256": "6d514c832e6cb141a66a19b2c1f65eb772020323cd0201a1a2e4fa9fd10196fd"
    }
  },
  "saved_arrays_recomputed_byte_identically": true
}
```

Stderr: empty. Exit 0.

| Final figure | Bytes | SHA-256 | Visually inspected / regenerated |
| --- | --- | --- | --- |
| fig01_malus_and_loss.png | 161187 | 1b0828ee4124fd10804b5c65f5af581557d37f59ad76565bef7174edf18ab53d | yes / byte-identical |
| fig02_retarders_and_components.png | 230945 | 0a672c4cd7b6b32b812fca05874d16ff2c577683db8b8e24d7f8b5ea1868a018 | yes / byte-identical |
| fig03_polarization_ellipses.png | 222064 | 6d514c832e6cb141a66a19b2c1f65eb772020323cd0201a1a2e4fa9fd10196fd | yes / byte-identical |

Fig02 plots signed norm-ratio residuals and labels a 1e-18 display floor for exactly zero discrepancy values; raw errors/norms stay unchanged. Ellipse amplitudes are not normalized. Plotting/I/O remain outside the core.

## Protected scope and publication boundary

Exactly 22 paths: 4 existing documentation modifications and 18 creations, listed in [code_map.md](code_map.md). SHA verification compares all 249 protected pre-existing tracked paths against the 253-file baseline. Installed distribution inventory compares 53 entries (52 unique names), versions, metadata-file hashes and locations. The final result is recorded in `precommit_inventory.json`; existing executable source/tests/guards, exports, schemas/protocols, frontend/lockfile, apps, M5, dependency declarations, engineering instructions and historical handoffs/figures are protected. No packages/global settings changed, npm/frontend execution occurred, or 8501/8510 server/browser sessions were launched or managed. V2b publication closeout is a dated read-back of its existing publication JSON; historical browser/control distinctions remain historical.

One approved commit uses `feat(v2c): model ideal Jones polarization elements`. Clean-postcommit import/source-location and fresh 64² demo smoke must pass before a normal origin/main push. Actual commit SHA, remote/API agreement, clean synchronized final state and completed protected verification are recorded afterward in ignored evidence and the completion report; they are pending in this precommit document. No new qualified-replay gate is imposed. No V2d or later work started. Separate teaching/historical learning records are unchanged. No material scope deviation or tolerance relaxation occurred; added validation cases and corrected plot layout stayed within the 22 approved paths.

Documentation assembly initially rejected the baseline command record because it is a list, whereas later command records are objects; a second attempt used theta_rad where Malus records use radians. The helper was corrected to use the actual saved formats. No tracked document was written by either failed attempt and no scientific evidence was altered. These assembly failures are distinct from the passing acceptance commands.
