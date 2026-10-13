# V2f tests and evidence

Recorded 2026-10-13. Accepted starting commit:
`1dde19c4c1d5419714523828c338bc0c948ea82c`. Fresh owned ignored captures:
`C:\holographiclab\runs\v2f_acceptance_20261013_01`.
These are current Windows/Python 3.11.9/NumPy 2.4.6 measurements, not replacements
for historical V2a–V2e or planning measurements. No frontend, browser, server,
npm, dependency or service work was performed for V2f; ports 8501/8510 were
left untouched.

Before editing, main/HEAD/upstream/live remote matched the accepted baseline,
with clean synchronized main. Inventory recorded 321 tracked files and 53
installed distribution version/location/metadata entries. The exact API,
checkpoint names and supported domain were completed before executable source;
`opening_contract_record.json` records that order and the original contract.
Only the approved four existing documentation files and eighteen creations
belong to this milestone. All 317 other existing tracked files are protected.

## Fresh unchanged baseline

Working directory: `C:\holographiclab`. Exact child command:

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider --basetemp C:\holographiclab\runs\v2f_acceptance_20261013_01\baseline_tmp -rs
```

Unedited stdout:

```text
........................................................................ [  2%]
........................................................................ [  5%]
........................................................................ [  7%]
........................................................................ [ 10%]
........................................................................ [ 13%]
........................................................................ [ 15%]
........................................................................ [ 18%]
........................................................................ [ 21%]
........................................................................ [ 23%]
........................................................................ [ 26%]
........................................................................ [ 29%]
........................................................................ [ 31%]
........................................................................ [ 34%]
........................................................................ [ 37%]
........................................................................ [ 39%]
........................................................................ [ 42%]
........................................................................ [ 45%]
........................................................................ [ 47%]
........................................................................ [ 50%]
........................................................................ [ 53%]
........................................................................ [ 55%]
........................................................................ [ 58%]
...................................................s.................... [ 61%]
........................................................................ [ 63%]
........................................................................ [ 66%]
........................................................................ [ 69%]
........................................................................ [ 71%]
........................................................................ [ 74%]
........................................................................ [ 77%]
........................................................................ [ 79%]
........................................................................ [ 82%]
........................................................................ [ 85%]
........................................................................ [ 87%]
........................................................................ [ 90%]
........................................................................ [ 93%]
........................................................................ [ 95%]
........................................................................ [ 98%]
.....................................                                    [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
2700 passed, 1 skipped in 233.03s (0:03:53)
```

Stderr: empty (0 bytes).

Exit code: `0`. Original argv, byte streams and exit metadata: `baseline_*` in the owned evidence directory.

## Restored final complete Python suite

Working directory: `C:\holographiclab`. Exact child command:

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider --basetemp C:\holographiclab\runs\v2f_acceptance_20261013_01\final_tmp03 -rs
```

Unedited stdout:

```text
........................................................................ [  2%]
........................................................................ [  4%]
........................................................................ [  7%]
........................................................................ [  9%]
........................................................................ [ 12%]
........................................................................ [ 14%]
........................................................................ [ 17%]
........................................................................ [ 19%]
........................................................................ [ 22%]
........................................................................ [ 24%]
........................................................................ [ 26%]
........................................................................ [ 29%]
........................................................................ [ 31%]
........................................................................ [ 34%]
........................................................................ [ 36%]
........................................................................ [ 39%]
........................................................................ [ 41%]
........................................................................ [ 44%]
........................................................................ [ 46%]
........................................................................ [ 48%]
........................................................................ [ 51%]
........................................................................ [ 53%]
........................................................................ [ 56%]
........................................................................ [ 58%]
........................................................................ [ 61%]
........................................................................ [ 63%]
.....s.................................................................. [ 66%]
........................................................................ [ 68%]
........................................................................ [ 70%]
........................................................................ [ 73%]
........................................................................ [ 75%]
........................................................................ [ 78%]
........................................................................ [ 80%]
........................................................................ [ 83%]
........................................................................ [ 85%]
........................................................................ [ 88%]
........................................................................ [ 90%]
........................................................................ [ 92%]
........................................................................ [ 95%]
........................................................................ [ 97%]
...............................................................          [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
2942 passed, 1 skipped in 243.99s (0:04:03)
```

Stderr: empty (0 bytes).

Exit code: `0`. Original argv, byte streams and exit metadata: `final_suite03_*` in the owned evidence directory.

## Final focused new-test execution

Working directory: `C:\holographiclab`. Exact child command:

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider --basetemp C:\holographiclab\runs\v2f_acceptance_20261013_01\tests\focused_tmp03 tests/test_polarized_interference_primitives.py tests/test_polarized_interference_model.py tests/test_polarized_interference_analytic.py tests/test_polarized_interference_architecture.py -rs
```

Unedited stdout:

```text
........................................................................ [ 29%]
........................................................................ [ 59%]
........................................................................ [ 89%]
..........................                                               [100%]
242 passed in 1.22s
```

Stderr: empty (0 bytes).

Exit code: `0`. Original argv, byte streams and exit metadata: `tests/focused03_*` in the owned evidence directory.

The only skip is the existing Windows file-symlink privilege case at
`tests/test_run_artifacts.py:1101`; junction behavior is separately tested.
No privilege elevation or old test modification was used. Four new test files
add 242 cases. The final complete run follows the final tolerance-scale
correction and the complete restored fault-control matrix. Earlier full runs
`final_suite01` and `final_suite02` remain preserved as intermediate evidence.

## Independent evidence and measured tolerances

`evidence/validation_final04/validation.json` contains complete-field complex
comparison metrics, norms and samples, checkpoint budgets, all 17 fixed markers,
additional asymmetric phases, raw
and downstream analyzer values, exact source hashes and resource snapshots.
Expected tiny fields independently construct physical coordinates, signed bins,
principal kz, finite Fourier sums, literal four-component port mixing and
expanded Jones coefficients. No production propagation/mixing/Jones helper,
phase fitting or reference normalization supplies expected fields. Direct-sum
shapes are 3x4, 5x6 and 6x5; the dense reference caps spatial samples at 64.
Tests also block production numerical helpers while evaluating these references.

The larger 32/64 demo reference factors a common publicly propagated envelope
and independent hand Jones/port algebra. It is explicitly not an independent
large-grid propagation reference; the tiny direct sums provide that evidence.

`Ain` is the maximum absolute incident component sample across applicable
input ports. `Nin` is independently reduced original combined Jones input norm,
never adjusted. Error/Ain means maximum component absolute discrepancy divided
by Ain; norm error/Nin uses original input norm. Fractions use absolute error;
selected weak relative error is abs(actual-reference)/reference.

| Quantity | rtol | atol |
|---|---:|---:|
| Literal matrix/identity | 0 | 2e-15 |
| Ordinary complex components | 2e-14 | 2e-14 Ain |
| Intensity | 2e-13 | 2e-13 Ain^2 |
| Jones norms | 2e-13 | 2e-13 Nin |
| Ordinary fractions | 2e-13 | 2e-13 |
| Complete independent direct sums | 1e-11 | 1e-11 Ain |
| Selected near-dark fractions | 2e-13 | 1e-40 |
| Corresponding near-dark norms | 2e-13 | 1e-40 Nin |

These approved bounds were measured unchanged against shipped functions.
They are finite-fixture acceptance bounds, not universal forward-error claims.

| Final measured maximum | Value |
|---|---:|
| ordinary_complex_over_Ain | 3.376611507232129e-16 |
| fraction_absolute_error | 6.661338147750939e-16 |
| analyzer_fraction_absolute_error | 2.220446049250313e-16 |
| direct_complex_over_Ain | 7.783100087124842e-16 |
| direct_norm_over_Nin | 4.042360219746071e-16 |
| selected_near_dark_relative_error | 9.466330862652152e-16 |

The literal block unitarity discrepancy is 2.220446049250313e-16. Both pure-x
and pure-y selected reductions to V2a measured zero complex/fraction discrepancy
in these fixtures; the contract permits the declared tolerance, not universal
bit identity. The complex-first hand anchor j0=(1,i)/sqrt(2), j1=(1,1)/sqrt(2)
has gamma=(1-i)/2 and phi=pi/2 fractions
0.7499999999999997 / 0.24999999999999992. Missing conjugation reverses the
hand expectation. The actual circular fixture Ain is 0.7071067811865475;
its scaled complex maximum is 3.3537189618722464e-16.

Matched orthogonal linear and circular states give raw half/half. Equal
45-degree analyzers of matched orthogonal linear arms give
((1+cos(phi))/4,(1-cos(phi))/4), total one half of original input. Raw fields
are preserved; pre/post norms, removed norms, original-input fractions and
separately named downstream-input ratios are stored. Arm1 polarizer pi/3 retains
5/8 and removes 3/8 of original input, without surviving-power normalization.
Noncommuting actions, retarder common phase and unequal-distance carrier-once
cases compare actual complete fields. Evanescent decay is measured as inherited
discrete scalar behavior, not calibrated vector electromagnetic power.

All 17 k*pi/8 markers (k=0..16) are separately evaluated, including 0 and 2*pi.
There is no forced periodic closure or continuous-visibility certification.
Twelve selected near-dark phases use 80-digit Decimal expansions at the actual
binary64 phases, including both signs and pi offsets. At +/-1e-9 the actual
dark fraction is 2.499999999999999e-19 versus 2.5e-19 reference; the smallest
four near-dark fractions have maximum relative discrepancy
3.8518601947994343e-16. Their roughly 5e-10 component survives while the much
smaller roughly 2.5e-19 quadrature rounds to zero. The fraction-level relative
claim does not extend to every real/imaginary quadrature. Nothing is clipped.

Ordinary unsupported-input and derived-stage exception tests are separate
from mutation evidence. They verify contextual failures, no partial result,
combined-norm semantics at Jones-only intermediates, scalar output validation,
caller floating-point setting restoration, metadata/canonical-grid validation,
runner-only cap before avoidable work and independent output ownership.

## Exact independent validator/resource execution

Working directory: `C:\holographiclab`. Exact child command:

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -X utf8 scripts/validate_v2f_interference.py --output-dir runs/v2f_acceptance_20261013_01/evidence/validation_final04 --resources
```

Unedited stdout:

```text
{
  "acceptance_passed": true,
  "output": "C:\\holographiclab\\runs\\v2f_acceptance_20261013_01\\evidence\\validation_final04\\validation.json",
  "fixed_phase_markers": 17,
  "direct_cases": 3,
  "near_dark_cases": 12,
  "maxima": {
    "ordinary_complex_over_Ain": 3.376611507232129e-16,
    "fraction_absolute_error": 6.661338147750939e-16,
    "analyzer_fraction_absolute_error": 2.220446049250313e-16,
    "direct_complex_over_Ain": 7.783100087124842e-16,
    "direct_norm_over_Nin": 4.042360219746071e-16,
    "selected_near_dark_relative_error": 9.466330862652152e-16
  },
  "resources": [
    {
      "shape": [
        32,
        32
      ],
      "iterations_per_separate_interval": 20,
      "wall_seconds_without_tracing": 0.03765479987487197,
      "wall_seconds_per_runner_without_tracing": 0.0018827399937435985,
      "traced_current_bytes": 105477,
      "traced_peak_bytes": 412945,
      "process_before": {
        "working_set_bytes": 40808448,
        "private_bytes": 837025792,
        "process_lifetime_peak_working_set_bytes": 40808448
      },
      "process_after_wall": {
        "working_set_bytes": 41316352,
        "private_bytes": 837435392,
        "process_lifetime_peak_working_set_bytes": 41316352
      },
      "process_after_trace": {
        "working_set_bytes": 41451520,
        "private_bytes": 837492736,
        "process_lifetime_peak_working_set_bytes": 41451520
      },
      "output_four_component_bytes": 65536,
      "norms": {
        "inputs": [
          2.479918062869987e-09,
          0.0
        ],
        "split": [
          1.2399590314349935e-09,
          1.2399590314349935e-09
        ],
        "propagated": [
          1.2399590314349935e-09,
          1.2399590314349935e-09
        ],
        "elements": [
          9.877009409447175e-10,
          1.2006010121699718e-09
        ],
        "combiner": [
          9.877009409447175e-10,
          1.2006010121699716e-09
        ],
        "outputs": [
          1.7422572120035956e-09,
          4.460447411110933e-10
        ],
        "arm_action_norms": [
          [
            9.877009409447175e-10,
            9.877009409447175e-10
          ],
          [
            1.2399590314349935e-09,
            1.2006010121699718e-09
          ]
        ],
        "inputs_total": 2.479918062869987e-09,
        "split_total": 2.479918062869987e-09,
        "propagated_total": 2.479918062869987e-09,
        "elements_total": 2.1883019531146892e-09,
        "combiner_total": 2.188301953114689e-09,
        "outputs_total": 2.188301953114689e-09,
        "split_delta": 0.0,
        "propagation_delta": 0.0,
        "elements_delta": -2.9161610975529776e-10,
        "phase_delta": -4.1359030627651384e-25,
        "recombination_delta": 0.0,
        "total_delta": -2.9161610975529817e-10,
        "propagation_deltas": [
          0.0,
          0.0
        ],
        "element_deltas": [
          -2.5225809049027604e-10,
          -3.935801926502172e-11
        ],
        "phase_deltas": [
          0.0,
          -2.0679515313825692e-25
        ],
        "arm_action_deltas": [
          [
            -2.5225809049027604e-10,
            0.0
          ],
          [
            0.0,
            -3.935801926502172e-11
          ]
        ],
        "output_fractions": [
          0.7025462808990136,
          0.17986269296127055
        ],
        "total_output_ratio": 0.8824089738602842
      },
      "interpretation": "actual shipped runner; tracing excludes input construction and reference/serialization; process snapshots/lifetime peaks are whole process, not isolated native peaks; observations are not guarantees"
    },
    {
      "shape": [
        64,
        64
      ],
      "iterations_per_separate_interval": 20,
      "wall_seconds_without_tracing": 0.087572299875319,
      "wall_seconds_per_runner_without_tracing": 0.00437861499376595,
      "traced_current_bytes": 301371,
      "traced_peak_bytes": 1518208,
      "process_before": {
        "working_set_bytes": 42020864,
        "private_bytes": 838098944,
        "process_lifetime_peak_working_set_bytes": 42020864
      },
      "process_after_wall": {
        "working_set_bytes": 42553344,
        "private_bytes": 839188480,
        "process_lifetime_peak_working_set_bytes": 43167744
      },
      "process_after_trace": {
        "working_set_bytes": 42217472,
        "private_bytes": 839204864,
        "process_lifetime_peak_working_set_bytes": 43253760
      },
      "output_four_component_bytes": 262144,
      "norms": {
        "inputs": [
          2.4822508953789477e-09,
          0.0
        ],
        "split": [
          1.2411254476894739e-09,
          1.2411254476894739e-09
        ],
        "propagated": [
          1.2411254476894739e-09,
          1.2411254476894739e-09
        ],
        "elements": [
          9.886300607001904e-10,
          1.2017304047549186e-09
        ],
        "combiner": [
          9.886300607001904e-10,
          1.2017304047549186e-09
        ],
        "outputs": [
          1.7441600046827715e-09,
          4.4620046077233704e-10
        ],
        "arm_action_norms": [
          [
            9.8863006070019e-10,
            9.886300607001904e-10
          ],
          [
            1.2411254476894739e-09,
            1.2017304047549186e-09
          ]
        ],
        "inputs_total": 2.4822508953789477e-09,
        "split_total": 2.4822508953789477e-09,
        "propagated_total": 2.4822508953789477e-09,
        "elements_total": 2.1903604654551088e-09,
        "combiner_total": 2.1903604654551088e-09,
        "outputs_total": 2.1903604654551088e-09,
        "split_delta": 0.0,
        "propagation_delta": 0.0,
        "elements_delta": -2.9189042992383896e-10,
        "phase_delta": 0.0,
        "recombination_delta": 0.0,
        "total_delta": -2.9189042992383896e-10,
        "propagation_deltas": [
          0.0,
          0.0
        ],
        "element_deltas": [
          -2.524953869892835e-10,
          -3.939504293455528e-11
        ],
        "phase_deltas": [
          0.0,
          0.0
        ],
        "arm_action_deltas": [
          [
            -2.524953869892839e-10,
            4.1359030627651384e-25
          ],
          [
            0.0,
            -3.939504293455528e-11
          ]
        ],
        "output_fractions": [
          0.7026525835602541,
          0.17975639030003
        ],
        "total_output_ratio": 0.8824089738602842
      },
      "interpretation": "actual shipped runner; tracing excludes input construction and reference/serialization; process snapshots/lifetime peaks are whole process, not isolated native peaks; observations are not guarantees"
    },
    {
      "shape": [
        128,
        128
      ],
      "iterations_per_separate_interval": 20,
      "wall_seconds_without_tracing": 0.5967820999212563,
      "wall_seconds_per_runner_without_tracing": 0.029839104996062814,
      "traced_current_bytes": 1086516,
      "traced_peak_bytes": 5940658,
      "process_before": {
        "working_set_bytes": 42999808,
        "private_bytes": 839233536,
        "process_lifetime_peak_working_set_bytes": 44359680
      },
      "process_after_wall": {
        "working_set_bytes": 44236800,
        "private_bytes": 840192000,
        "process_lifetime_peak_working_set_bytes": 48320512
      },
      "process_after_trace": {
        "working_set_bytes": 43237376,
        "private_bytes": 839172096,
        "process_lifetime_peak_working_set_bytes": 48345088
      },
      "output_four_component_bytes": 1048576,
      "norms": {
        "inputs": [
          2.4822508954176358e-09,
          0.0
        ],
        "split": [
          1.2411254477088175e-09,
          1.2411254477088175e-09
        ],
        "propagated": [
          1.2411254477088179e-09,
          1.2411254477088179e-09
        ],
        "elements": [
          9.886300607155989e-10,
          1.2017304047736486e-09
        ],
        "combiner": [
          9.886300607155989e-10,
          1.2017304047736486e-09
        ],
        "outputs": [
          1.7441600047648057e-09,
          4.462004607244415e-10
        ],
        "arm_action_norms": [
          [
            9.886300607155987e-10,
            9.886300607155989e-10
          ],
          [
            1.2411254477088179e-09,
            1.2017304047736486e-09
          ]
        ],
        "inputs_total": 2.4822508954176358e-09,
        "split_total": 2.482250895417635e-09,
        "propagated_total": 2.4822508954176358e-09,
        "elements_total": 2.1903604654892473e-09,
        "combiner_total": 2.1903604654892473e-09,
        "outputs_total": 2.1903604654892473e-09,
        "split_delta": -8.271806125530277e-25,
        "propagation_delta": 8.271806125530277e-25,
        "elements_delta": -2.9189042992838846e-10,
        "phase_delta": 0.0,
        "recombination_delta": 0.0,
        "total_delta": -2.9189042992838846e-10,
        "propagation_deltas": [
          4.1359030627651384e-25,
          4.1359030627651384e-25
        ],
        "element_deltas": [
          -2.52495386993219e-10,
          -3.9395042935169256e-11
        ],
        "phase_deltas": [
          0.0,
          0.0
        ],
        "arm_action_deltas": [
          [
            -2.524953869932192e-10,
            2.0679515313825692e-25
          ],
          [
            0.0,
            -3.9395042935169256e-11
          ]
        ],
        "output_fractions": [
          0.7026525835823509,
          0.17975639027793314
        ],
        "total_output_ratio": 0.882408973860284
      },
      "interpretation": "actual shipped runner; tracing excludes input construction and reference/serialization; process snapshots/lifetime peaks are whole process, not isolated native peaks; observations are not guarantees"
    }
  ]
}
```

Stderr: empty (0 bytes).

Exit code: `0`. Original argv, byte streams and exit metadata: `validator_final04_*` in the owned evidence directory.

## Actual fault-control classification and restoration

All actual variants below execute in isolated package/source copies under the
owned ignored evidence directory. Original production bytes are never mutated.
Each records original assertions exit 0 -> intended scientific AssertionError
exit 10 -> exact copied-source restoration -> restored assertions exit 0.
Setup/import/schema crashes are not counted. The final report records hashes
before/after for all 30 production sources/tests/scripts and verifies they match
current files. The restored final full suite runs afterward.

| Actual variant | Classification |
|---|---|
| swap_optical_ports | production composition/dependency-binding mutation in copied new module |
| swap_polarization_components | production composition/dependency-binding mutation in copied new module |
| omit_x_component | production composition/dependency-binding mutation in copied new module |
| omit_y_component | production composition/dependency-binding mutation in copied new module |
| wrong_splitter_sign | production composition/dependency-binding mutation in copied new module |
| common_phase_only_x | production composition/dependency-binding mutation in copied new module |
| reverse_retardance_sign | production composition/dependency-binding mutation in copied new module |
| drop_retarder_common_phase | production composition/dependency-binding mutation in copied new module |
| reset_terminal_common_phase | production composition/dependency-binding mutation in copied new module |
| incoherent_arm_addition | production composition/dependency-binding mutation in copied new module |
| scalar_sum_orthogonal_components | reused public-dependency behavior mutation installed only in copied new module |
| omit_propagation_carrier | production composition/dependency-binding mutation in copied new module |
| double_propagation_carrier | production composition/dependency-binding mutation in copied new module |
| normalize_terminal_polarizer_loss | production composition/dependency-binding mutation in copied new module |
| filtered_outputs_returned_as_raw | production composition/dependency-binding mutation in copied new module |
| silently_delete_unsupported_tiny_component | production composition/dependency-binding mutation in copied new module |
| reverse_terminal_action_order | production composition/dependency-binding mutation in copied new module |
| normalize_downstream_analyzer_loss | demonstration implementation mutation in copied new example |
| missing_overlap_conjugation | independent-reference self-check mutation; runner has no overlap branch |
| discard_overlap_argument | independent-reference self-check mutation; runner has no overlap branch |

Totals: 16 new-module production composition/dependency-binding variants,
one reused public JonesField intensity-behavior counterfactual, one demonstration
analyzer-accounting mutation and two independent-overlap-oracle self-checks.
The runner never computes an overlap; those last two are not production branches.
The intensity counterfactual is similarly not a new intensity branch in the
runner. These controls show the named assertions detect these variants, not
gap-free correctness. Full raw per-variant streams, hashes and exit metadata
are in `evidence/negative_final04/`; the summary is
`negative_control_report.json` there.

## Exact final fault-control execution

Working directory: `C:\holographiclab`. Exact child command:

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -X utf8 scripts/v2f_negative_controls.py --output-dir runs/v2f_acceptance_20261013_01/evidence/negative_final04
```

Unedited stdout:

```text
swap_optical_ports: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
swap_polarization_components: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
omit_x_component: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
omit_y_component: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
wrong_splitter_sign: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
common_phase_only_x: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
reverse_retardance_sign: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
drop_retarder_common_phase: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
reset_terminal_common_phase: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
incoherent_arm_addition: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
scalar_sum_orthogonal_components: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
omit_propagation_carrier: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
double_propagation_carrier: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
normalize_terminal_polarizer_loss: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
filtered_outputs_returned_as_raw: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
silently_delete_unsupported_tiny_component: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
reverse_terminal_action_order: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
normalize_downstream_analyzer_loss: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
missing_overlap_conjugation: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
discard_overlap_argument: original=0 mutant=10 restored=0 intended_detection=True exact_restoration=True
{
  "acceptance_passed": true,
  "executed_variants": 20,
  "classification_counts": {
    "demonstration implementation mutation in copied new example": 1,
    "independent-reference self-check mutation; runner has no overlap branch": 2,
    "production composition/dependency-binding mutation in copied new module": 16,
    "reused public-dependency behavior mutation installed only in copied new module": 1
  },
  "production_hashes_unchanged": true
}
```

Stderr: empty (0 bytes).

Exit code: `0`. Original argv, byte streams and exit metadata: `negative_final04_*` in the owned evidence directory.

## Numerical demonstrations and shipped-runner resources

Each demo records 34 sweep rows: identical/orthogonal arms times 17 actual phase
markers. It retains selected raw/analyzed field arrays and scalar sweep data,
not every intermediate full field. JSON/NPZ files are disposable evidence,
not a public persistence format, M5 bundle or qualified replay.

| Demo | Wall seconds including embedded validation | Evidence |
|---|---:|---|
| 32x32 | 0.42627339996397495 | evidence/demo32_02/demo.json and demo_arrays.npz |
| 64x64 | 0.5033096000552177 | evidence/demo64_02/demo.json and demo_arrays.npz |

The following are actual shipped-runner observations. Each size uses 20
untraced runner calls for wall time and a separate 20-call traced interval.
Input construction, references and serialization are outside tracing. Traced
peaks are interval allocation peaks, not isolated one-call/native peaks.

| Grid | Untraced seconds/call | Traced current bytes | Traced interval peak bytes | Four final arrays bytes |
|---|---:|---:|---:|---:|
| 32x32 | 0.0018827399937435985 | 105477 | 412945 | 65536 |
| 64x64 | 0.00437861499376595 | 301371 | 1518208 | 262144 |
| 128x128 | 0.029839104996062814 | 1086516 | 5940658 | 1048576 |

Whole-process Windows snapshots, in bytes, are separate measurements:

| Grid / snapshot | Working set | Private bytes | Process lifetime peak working set |
|---|---:|---:|---:|
| 32 / process_before | 40808448 | 837025792 | 40808448 |
| 32 / process_after_wall | 41316352 | 837435392 | 41316352 |
| 32 / process_after_trace | 41451520 | 837492736 | 41451520 |
| 64 / process_before | 42020864 | 838098944 | 42020864 |
| 64 / process_after_wall | 42553344 | 839188480 | 43167744 |
| 64 / process_after_trace | 42217472 | 839204864 | 43253760 |
| 128 / process_before | 42999808 | 839233536 | 44359680 |
| 128 / process_after_wall | 44236800 | 840192000 | 48320512 |
| 128 / process_after_trace | 43237376 | 839172096 | 48345088 |

These are observations from this process, not portable runtime/memory guarantees.
Planning traced compositions and prior captures remain separate and are not
used to claim a performance improvement.

## Exact 32-grid demonstration

Working directory: `C:\holographiclab`. Exact child command:

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -X utf8 examples/polarized_two_path_interference.py --n 32 --output-dir runs/v2f_acceptance_20261013_01/evidence/demo32_02
```

Unedited stdout:

```text
{
  "acceptance_passed": true,
  "shape": [
    32,
    32
  ],
  "output": "C:\\holographiclab\\runs\\v2f_acceptance_20261013_01\\evidence\\demo32_02",
  "phase_markers_per_case": 17,
  "sweep_rows": 34,
  "wall_seconds_including_validation": 0.42627339996397495,
  "maximum_demo_complex_error_over_Ain": 6.753223014464258e-16,
  "independent_maxima": {
    "ordinary_complex_over_Ain": 3.376611507232129e-16,
    "fraction_absolute_error": 6.661338147750939e-16,
    "analyzer_fraction_absolute_error": 2.220446049250313e-16,
    "direct_complex_over_Ain": 7.783100087124842e-16,
    "direct_norm_over_Nin": 4.042360219746071e-16,
    "selected_near_dark_relative_error": 9.466330862652152e-16
  }
}
```

Stderr: empty (0 bytes).

Exit code: `0`. Original argv, byte streams and exit metadata: `demo32_02_*` in the owned evidence directory.

## Exact 64-grid demonstration

Working directory: `C:\holographiclab`. Exact child command:

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -X utf8 examples/polarized_two_path_interference.py --n 64 --output-dir runs/v2f_acceptance_20261013_01/evidence/demo64_02
```

Unedited stdout:

```text
{
  "acceptance_passed": true,
  "shape": [
    64,
    64
  ],
  "output": "C:\\holographiclab\\runs\\v2f_acceptance_20261013_01\\evidence\\demo64_02",
  "phase_markers_per_case": 17,
  "sweep_rows": 34,
  "wall_seconds_including_validation": 0.5033096000552177,
  "maximum_demo_complex_error_over_Ain": 5.578801654593729e-16,
  "independent_maxima": {
    "ordinary_complex_over_Ain": 3.376611507232129e-16,
    "fraction_absolute_error": 6.661338147750939e-16,
    "analyzer_fraction_absolute_error": 2.220446049250313e-16,
    "direct_complex_over_Ain": 7.783100087124842e-16,
    "direct_norm_over_Nin": 4.042360219746071e-16,
    "selected_near_dark_relative_error": 9.466330862652152e-16
  }
}
```

Stderr: empty (0 bytes).

Exit code: `0`. Original argv, byte streams and exit metadata: `demo64_02_*` in the owned evidence directory.

## Figures, provenance and regeneration

All three final PNGs were inspected at original resolution. The topology is
explicitly ideal/unfolded; intensity maps use common scales, physical halfpixel
edges and y-down orientation. Uniform phase changes produce brightness changes,
not invented stripes. Separate analyzer loss, all 17 marker points, signed
residuals, full complex reference discrepancies and weak-signal limits are
labelled. Display magnifications are explicit. Text/footers are readable.

The generator verifies current source/evidence hashes and exactly recomputes
selected arrays and norms before plotting. All three final PNGs regenerated
byte-identically using the same final64 evidence. Figure footer evidence SHA256:
`4984a300c9071b39826a365e64161423f17075c60d861b2f3fa2f79725bc851d`.

| Committed figure | Bytes | SHA256 |
|---|---:|---|
| fig01_ideal_topology_and_outputs.png | 195089 | daabc1610f13036e7831c0bb1299331ebc0ad2b99505ba74af4b44684ef0f982 |
| fig02_phase_and_analyzer_fractions.png | 284755 | e284d586774eb2026a49e62d31ec22e13db5b7e656e252dbb97cc2bf0a989846 |
| fig03_complex_overlap_and_reference.png | 223208 | 39d5b44aa1eb10e6f2a781410aeb8d2a540124df0d8ba28d991dfcfcf19b7502 |

For plotting only, a copied child environment mapping sets MPLCONFIGDIR to the
owned evidence directory. Parent/persistent settings and proxy/TLS/pip settings
were not modified. No dependency/index operation occurred in V2f.

## Exact final figure generation

Working directory: `C:\holographiclab`. Exact child command:

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -X utf8 scripts/generate_v2f_figures.py --evidence-dir runs/v2f_acceptance_20261013_01/evidence/demo64_02
```

Unedited stdout:

```text
{
  "demo_json_sha256": "4984a300c9071b39826a365e64161423f17075c60d861b2f3fa2f79725bc851d",
  "selected_arrays_recomputed_byte_identically": true,
  "figures": {
    "fig01_ideal_topology_and_outputs.png": {
      "path": "C:\\holographiclab\\docs\\handoffs\\v2f\\figures\\fig01_ideal_topology_and_outputs.png",
      "bytes": 195089,
      "sha256": "daabc1610f13036e7831c0bb1299331ebc0ad2b99505ba74af4b44684ef0f982"
    },
    "fig02_phase_and_analyzer_fractions.png": {
      "path": "C:\\holographiclab\\docs\\handoffs\\v2f\\figures\\fig02_phase_and_analyzer_fractions.png",
      "bytes": 284755,
      "sha256": "e284d586774eb2026a49e62d31ec22e13db5b7e656e252dbb97cc2bf0a989846"
    },
    "fig03_complex_overlap_and_reference.png": {
      "path": "C:\\holographiclab\\docs\\handoffs\\v2f\\figures\\fig03_complex_overlap_and_reference.png",
      "bytes": 223208,
      "sha256": "39d5b44aa1eb10e6f2a781410aeb8d2a540124df0d8ba28d991dfcfcf19b7502"
    }
  }
}
```

Stderr: empty (0 bytes).

Exit code: `0`. Original argv, byte streams and exit metadata: `figures_final04_*` in the owned evidence directory.

## Exact figure regeneration

Working directory: `C:\holographiclab`. Exact child command:

```powershell
& 'C:\holographiclab\.venv\Scripts\python.exe' -B -X utf8 scripts/generate_v2f_figures.py --evidence-dir runs/v2f_acceptance_20261013_01/evidence/demo64_02 --output-dir runs/v2f_acceptance_20261013_01/evidence/figure_regeneration_final02
```

Unedited stdout:

```text
{
  "demo_json_sha256": "4984a300c9071b39826a365e64161423f17075c60d861b2f3fa2f79725bc851d",
  "selected_arrays_recomputed_byte_identically": true,
  "figures": {
    "fig01_ideal_topology_and_outputs.png": {
      "path": "C:\\holographiclab\\runs\\v2f_acceptance_20261013_01\\evidence\\figure_regeneration_final02\\fig01_ideal_topology_and_outputs.png",
      "bytes": 195089,
      "sha256": "daabc1610f13036e7831c0bb1299331ebc0ad2b99505ba74af4b44684ef0f982"
    },
    "fig02_phase_and_analyzer_fractions.png": {
      "path": "C:\\holographiclab\\runs\\v2f_acceptance_20261013_01\\evidence\\figure_regeneration_final02\\fig02_phase_and_analyzer_fractions.png",
      "bytes": 284755,
      "sha256": "e284d586774eb2026a49e62d31ec22e13db5b7e656e252dbb97cc2bf0a989846"
    },
    "fig03_complex_overlap_and_reference.png": {
      "path": "C:\\holographiclab\\runs\\v2f_acceptance_20261013_01\\evidence\\figure_regeneration_final02\\fig03_complex_overlap_and_reference.png",
      "bytes": 223208,
      "sha256": "39d5b44aa1eb10e6f2a781410aeb8d2a540124df0d8ba28d991dfcfcf19b7502"
    }
  }
}
```

Stderr: empty (0 bytes).

Exit code: `0`. Original argv, byte streams and exit metadata: `regenerate_final02_*` in the owned evidence directory.

## Preserved failures, corrections and scope

- Initial new-core smoke exposed missing chained context at an extra-phase
  scalar preflight. The new wrapper was corrected; smoke01 remains and smoke02
  passed. No old scalar/Jones implementation changed.
- A tampered enormous canonical grid dimension exposed a raw OverflowError.
  Narrow new geometry validation now raises contextual ValueError with cause;
  geometry_probe01/02 and the new regression preserve the evidence.
- The original validator uniform expected shape (2,1,1) did not match actual
  (2,2,3). `validator_shape_reproducer01_*` preserves the failure. Explicit
  uniform-reference broadcasting is limited to the declared (2,1,1) case;
  every other expected shape must match exactly. No fixture/tolerance changed.
- An initial PowerShell quoting SyntaxError occurred before plotting. The
  saved `evidence/figure_orchestration_failure01.json` is a tool-result copy,
  explicitly not a native subprocess capture. Corrected child orchestration
  and actual successful streams are separately preserved.
- Figure physical edges and footer clearance were corrected in new plotting
  code. Initial images remain in owned ignored evidence directories.
- Review found the circular fixture's reference Ain was incorrectly 1 instead
  of its actual maximum component amplitude 1/sqrt(2). The scale and reported
  metric were corrected, tightening the effective absolute bound. No fixture
  or declared tolerance changed. Final04 validator, demo02, final04 figures and
  final04 controls cover the current files; earlier captures remain preserved.
- The new primitive inverse test initially used fixed atol=5e-14, slightly
  above 2e-14 times its actual fixture Ain. It now derives Ain from the actual
  source arrays and applies the declared bound. Focused03, final04 controls and
  final_suite03 follow this tightening; no implementation/tolerance was loosened.
- Git reports existing LF-to-CRLF conversion policy on approved documentation.
  No Git configuration or renormalization is used; explicit before/after-stage
  working-file byte hashes and sizes verify preservation.

The final scope checks compare complete pending/staged inventories with the
literal approved 22 paths, all 317 protected working-file hashes and all 53
installed distribution version/metadata/location records. Only approved paths
are staged. Six new handoff documents and three calculated figures complete
the numerical deliverable. Historical handoffs and numerical evidence remain
unchanged. V2e closeout is explicitly dated historical publication read-back.

## Publication boundary

This committed document records precommit acceptance. The explicitly approved
single commit, clean-postcommit source/import check and fresh numerical64 demo,
normal push, local/live-remote/GitHub API SHA comparison and final clean/sync
state are later gates. Their actual results belong to fresh ignored
postcommit/publication captures and the completion report, avoiding a predicted
commit SHA or a self-referential tracked amendment. No qualified-replay gate
is invented. A failure at a later gate must be reported rather than relabelled.

V2g interactive integration, new document modes, material/reflection models,
hardware and deployment remain separately approved future work. Teaching is
separate; no lesson or learning progress is inferred.
