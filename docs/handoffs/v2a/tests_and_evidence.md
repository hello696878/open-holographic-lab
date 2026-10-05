# V2a tests and evidence

Recorded 2026-10-05. Accepted starting revision: `303a312fcbddfc9abefcef8c1424ae374ef872fe`. Initial checkout was clean synchronized main; ordinary network permission was required for live remote verification. No proxy/configuration changes were made. Existing Python 3.11.9, NumPy 2.4.6 and SciPy 1.17.1 remain installed. Historical planning and V1 browser results are not current acceptance.

## Exact baseline and first full retained/new suite

### Unchanged baseline

Executed from `C:\holographiclab` using the existing repository interpreter. The capture helper preserves command JSON and raw stdout/stderr/exit separately.

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 -m pytest -q -p no:cacheprovider --basetemp=runs/v2a_acceptance_20261005/pytest_baseline
```

Exact unedited stdout:

```text
........................................................................ [  3%]
........................................................................ [  7%]
........................................................................ [ 11%]
........................................................................ [ 15%]
........................................................................ [ 19%]
........................................................................ [ 23%]
........................................................................ [ 27%]
........................................................................ [ 31%]
........................................................................ [ 35%]
........................................................................ [ 39%]
........................................................................ [ 43%]
........................................................................ [ 47%]
........................................................................ [ 51%]
........................................................................ [ 55%]
........................................................................ [ 59%]
........................................................................ [ 63%]
..s..................................................................... [ 67%]
........................................................................ [ 71%]
........................................................................ [ 75%]
........................................................................ [ 79%]
........................................................................ [ 83%]
........................................................................ [ 87%]
........................................................................ [ 91%]
........................................................................ [ 95%]
........................................................................ [ 99%]
...                                                                      [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
1802 passed, 1 skipped in 126.67s (0:02:06)
```

Exit `0`; stderr is empty. Raw captures: `runs/v2a_acceptance_20261005/baseline_{command.json,stdout.txt,stderr.txt,exit.txt}`.

### Before isolated faults

Executed from `C:\holographiclab` using the existing repository interpreter. The capture helper preserves command JSON and raw stdout/stderr/exit separately.

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 -m pytest -q -p no:cacheprovider --basetemp=runs/v2a_acceptance_20261005/pytest_precontrols
```

Exact unedited stdout:

```text
........................................................................ [  3%]
........................................................................ [  7%]
........................................................................ [ 10%]
........................................................................ [ 14%]
........................................................................ [ 17%]
........................................................................ [ 21%]
........................................................................ [ 25%]
........................................................................ [ 28%]
........................................................................ [ 32%]
........................................................................ [ 35%]
........................................................................ [ 39%]
........................................................................ [ 43%]
........................................................................ [ 46%]
........................................................................ [ 50%]
........................................................................ [ 53%]
........................................................................ [ 57%]
........................................................................ [ 60%]
........................................................................ [ 64%]
..............................................................s......... [ 68%]
........................................................................ [ 71%]
........................................................................ [ 75%]
........................................................................ [ 78%]
........................................................................ [ 82%]
........................................................................ [ 86%]
........................................................................ [ 89%]
........................................................................ [ 93%]
........................................................................ [ 96%]
...............................................................          [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
2006 passed, 1 skipped in 223.75s (0:03:43)
```

Exit `0`; stderr is empty. Raw captures: `runs/v2a_acceptance_20261005/full_precontrols_{command.json,stdout.txt,stderr.txt,exit.txt}`.

The sole skip is the unchanged Windows file-symlink privilege case; junction behavior is separately tested. No privileges were elevated and no pre-existing tests were changed. The first full suite contains 204 additional V2a cases, not a quota or coverage-completeness claim.

## Independent validation and unchanged tolerances

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 scripts\validate_v2a_interference.py --output runs\v2a_acceptance_20261005\independent_2
```

Exit 0, empty stderr. Actual `independent_2/evidence.json` and raw `independent_2_*` captures retain every field/norm/phase and environment/source hash. `independent_1` remains an earlier successful run, before refining blocked-arm records to measure removed/surviving norms rather than merely writing their analytic half expectations. Final source hash: `aae60e19e65261992a99b820062e9b271389403d8cc784eacd67db9cd0cf9eef`; reference-script hash `ac26f49cb690b2f9e255e28b0db84a8eb478d2c6762ddbe788378cd4d3b0f306`.

The direct reference uses explicit centered physical coordinates, signed frequency bins, forward/inverse finite sums, a principal scalar axial root and literal mixing coefficients. It uses no FFT or production expected-result helpers. The regression also prohibits direct imported aliases, grid arrays and public propagation/mixer helpers. Dense references use <=256 samples. Equal-arm analytic algebra separately uses one unchanged public ASM call for W; it is not presented as independent propagation evidence.

| Check | rtol | atol | Actual worst measurement |
|---|---:|---:|---:|
| Shipped B†B against I | 0 | 2e-15 | 2.220446049250313e-16 absolute |
| Equal-arm complex fields, 8 declared + 4 near-dark phases | 2e-14 | 2e-14*Ain | 2.482534153247273e-16 input-scaled |
| Complete asymmetric direct DFT | 1e-11 | 1e-11*Ain | 1.1562283221955914e-15 input-scaled |
| Simultaneous nonzero coherent-input full DFT | 1e-11 | 1e-11*Ain | 5.360014067555462e-16 input-scaled |
| Lossless equal-arm total-norm residual | 2e-13 | 2e-13*Pin | 8.077935669463161e-16 relative to Pin |
| Ordered fraction error | 2e-13 | 2e-13 | 7.771561172376096e-16 absolute |

Ain is maximum input amplitude; Pin is original combined input sampled norm. Exact zero is tested separately. No tolerance was loosened, reference normalized or global phase fitted. The historical planning 3x4 probe observed a 1.1e-12 scaled floor with independently regrouped carrier/spatial phases; its source/results remain untouched. The shipped direct-sum implementation evaluates its full axial factor before summation and uses its own deterministic asymmetric fixture. Its measured smaller discrepancy does not replace that planning measurement.

### All phase points and signed residuals

| phi(rad) | output0/input | output1/input | total signed delta / Pin | max input-scaled complex error |
|---:|---:|---:|---:|---:|
| 0.0 | 0.9999999999999998 | 0.0 | -2.0194839173657902e-16 | 2.2887833992611187e-16 |
| 1.5707963267948966 | 0.4999999999999999 | 0.4999999999999999 | -2.0194839173657902e-16 | 2.220446049250313e-16 |
| 3.141592653589793 | 1.5407439555097883e-33 | 0.9999999999999998 | -2.0194839173657902e-16 | 2.482534153247273e-16 |
| 4.71238898038469 | 0.4999999999999999 | 0.4999999999999999 | -2.0194839173657902e-16 | 2.482534153247273e-16 |
| 6.283185307179586 | 0.9999999999999998 | 2.002967142162725e-32 | -2.0194839173657902e-16 | 2.2887833992611187e-16 |
| 0.37 | 0.9661636728030165 | 0.03383632719698278 | -8.077935669463161e-16 | 2.220446049250313e-16 |
| -0.83 | 0.8374378800356331 | 0.16256211996436631 | -6.058451752097371e-16 | 2.2301825219878386e-16 |
| 2.41 | 0.12794431730420366 | 0.8720556826957961 | -2.0194839173657902e-16 | 1.2393336671608795e-16 |
| -0.0001 | 0.9999999974999995 | 2.4999999979137447e-09 | -6.058451752097371e-16 | 2.2887833992611187e-16 |
| 0.0001 | 0.9999999974999997 | 2.4999999979184782e-09 | -4.0389678347315804e-16 | 1.2412670766236366e-16 |
| 3.141492653589793 | 2.499999997931208e-09 | 0.9999999974999995 | -6.058451752097371e-16 | 2.2887833992611187e-16 |
| 3.1416926535897933 | 2.4999999979221492e-09 | 0.9999999974999997 | -4.0389678347315804e-16 | 1.1102230246251565e-16 |

Near-dark phases are +/-1e-4 and pi+/-1e-4. Actual dark-port amplitude is about 5e-5 times input, roughly 2.5e9 times the declared absolute complex bound; its fraction is about 2.5e-9, visibly above 2e-13. Represented residuals at pi/2pi remain, not clamped. Common-global-phase complex covariance and intensity invariance, with distinct relative-phase sensitivity, were independently checked.

### Full complex, carrier and evanescent measurements

| Reference case | max absolute complex error | max input-scaled error |
|---|---:|---:|
| asymmetric_3x4 | 8.473409486550037e-16 | 5.538176135000024e-16 |
| asymmetric_5x6 | 2.2315206618374916e-15 | 1.1562283221955914e-15 |
| asymmetric_6x5 | 1.1836256121746794e-15 | 6.329548728206842e-16 |

All three arrays are asymmetric, anisotropic pitch 3.7/4.1 µm; wavelength 633 nm. Arms are 2/3 mm for 3x4 and 2.731/4.123 mm for 5x6, 6x5. Full complex arrays and difference maps are retained. Shipped B/B† coefficient discrepancies and MIT R/Q convention-translation residuals are exactly 0 observed; the numeric unitary residual is 2.220446049250313e-16. General simultaneous inputs 1+2i and .3-.7i, and the coherent (1,i) case, retain both ordered fields.

- Unequal-length DC, phi=0.0: fractions [0.75, 0.24999999999999994], max complex error 1.2412670766236366e-16.
- Unequal-length DC, phi=0.37: fractions [0.5764977611604384, 0.4235022388395618], max complex error 9.020562075079397e-17.
- Unequal-length off_axis, phi=0.37: fractions [0.5769549476353738, 0.423045052364626], max complex error 4.518280359883027e-16.

The DC lengths lambda/7 and lambda/7+lambda/6 independently distinguish the expected .75/.25 from missing-carrier 1/0 and double-carrier .25/.75. Off-axis on-grid propagation is separately checked.

Mixed propagating/evanescent 4x5 (pitches .22/.2 µm), unequal 80/130 nm arms: actual total ratio **0.9278073476242655**; signed propagation change `-6.924719215880432e-14` and recombination change `-2.0194839173657902e-28`. Independent complex maximum `6.661338147750939e-16`. Equal 100 nm arms have independent **tau=0.9275310453988844**; all 8 phases verify tau*cos²/sin² with original-input denominator. Algebraic mixer unitarity is not a calibrated evanescent electromagnetic energy law.

### Blocked-arm accounting

Actual incident norm `2.95745218e-10`; removed arm 1 `1.4787260899999998e-10`; survivor arm 0 `1.4787260899999998e-10`. Outputs `[7.393630449999998e-11, 7.393630449999998e-11]`; original-input fractions `[0.24999999999999992, 0.24999999999999992]`. Independently measured split-arm halves are checked against separate analytic expectations. All 8 surviving phases preserve each intensity. Removed half is accounted at the external blocking boundary, not hidden by output normalization or attributed to phase.

## Actual demonstration and shipped resources

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 examples\two_path_interference.py --n 64 --output runs\v2a_acceptance_20261005\demo64
```

Exit 0, empty stderr; actual total computation wall `0.06932430004235357`s. This includes streamed 8-phase sweep, blocked control and small DFT, excludes imports/evidenceI/O. The two demo processes were launched concurrently; these are observations, not benchmarks. Raw JSON/arrays and `demo64_*` captures are preserved.

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 examples\two_path_interference.py --n 128 --output runs\v2a_acceptance_20261005\demo128
```

Exit 0, empty stderr; actual total computation wall `0.10567860002629459`s. This includes streamed 8-phase sweep, blocked control and small DFT, excludes imports/evidenceI/O. The two demo processes were launched concurrently; these are observations, not benchmarks. Raw JSON/arrays and `demo128_*` captures are preserved.

The following measurements use shipped `run_two_arm`, not planning candidate arithmetic. Windows working-set snapshots are instantaneous; lifetime peak is whole process and cannot be reset per case. Python-traced peaks are not total process/native FFT memory.

| Grid | phases | wall(s) | traced peak(bytes) | process working set before/after(bytes) | lifetime peak after(bytes) |
|---|---:|---:|---:|---|---:|
| 64² | 8 | 0.0431883999845013 | 939779 | 39825408 / 40632320 | 40632320 |
| 128² | 8 | 0.08365350001258776 | 3692671 | 40235008 / 41447424 | 43888640 |
| 512² | 1 | 0.26396529999328777 | 50338610 | 44584960 / 53141504 | 94994432 |

At 64²/128²/512² a complex128 field occupies 65536/262144/4194304 bytes; two retained outputs double those sizes. Snapshots/intermediate copies/FFT temporaries explain the larger traced allocation. The 512² single phase is the bounded runner-cap/resource acceptance, not a universal memory promise.

## Preserved development failure

A new huge-pitch test intended to isolate radial-sum overflow initially used 3x4. The x-coordinate squared correctly overflowed first; its expected-message assertion failed. The exact output (1 failed, 152 passed) remains in `runs/v2a_core_20261005_002`. Correcting only that new fixture to 3x3 makes each squared coordinate finite while their sum overflows; no production source/tolerance changed. Final focused core suite 153 passed in 0.39 s, exit0/empty stderr, `runs/v2a_core_20261005_003`; earlier147pass capture remains in `_001`. Analytic/architecture focused suite 51 passed. No baseline/historical evidence was replaced.


## Twelve isolated deliberate faults

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 scripts\v2a_negative_controls.py --output-dir runs\v2a_acceptance_20261005\negative_controls_1
```

Exit 0. Each selected unchanged test function was executed directly in a fresh interpreter on an owned package copy before its mutation. Baseline exit 0 means the scientific assertion passed; mutant exit 10 means an actual `np.testing.assert_allclose` AssertionError with `Not equal to tolerance`. Setup/import/schema/non-assertion errors use exit 20 and cannot count as detection. These are direct assertion workers, not twelve full pytest runs.

| Fault | Actual detecting test function | baseline/mutant exit | copy restored |
|---|---|---|---|
| half_amplitude_factor | `test_coherent_two_input_hand_coefficients({'matrix': 'B'})` | 0 / 10 | True |
| missing_relative_i | `test_coherent_two_input_hand_coefficients({'matrix': 'B'})` | 0 / 10 | True |
| wrong_relative_i_sign | `test_coherent_two_input_hand_coefficients({'matrix': 'B'})` | 0 / 10 | True |
| intensity_addition | `test_equal_arm_complex_sweep_and_ordered_input_fractions({'phase': 0.0})` | 0 / 10 | True |
| reset_arm_phase | `test_complete_asymmetric_pipeline_independent_direct_dft({'ny': 3, 'nx': 4, 'z0': 0.002, 'z1': 0.003})` | 0 / 10 | True |
| ignore_prescribed_phase | `test_equal_arm_complex_sweep_and_ordered_input_fractions({'phase': 3.141592653589793})` | 0 / 10 | True |
| omit_ASM_carrier | `test_unequal_lengths_carrier_absolute_complex_plane_wave({'mode': 'DC', 'phase': 0.0})` | 0 / 10 | True |
| duplicate_ASM_carrier | `test_unequal_lengths_carrier_absolute_complex_plane_wave({'mode': 'DC', 'phase': 0.0})` | 0 / 10 | True |
| normalize_arm_after_loss | `test_forward_evanescent_unequal_arms_preserve_loss_full_complex({})` | 0 / 10 | True |
| flip_output_y | `test_complete_asymmetric_pipeline_independent_direct_dft({'ny': 3, 'nx': 4, 'z0': 0.002, 'z1': 0.003})` | 0 / 10 | True |
| swap_output_ports | `test_equal_arm_complex_sweep_and_ordered_input_fractions({'phase': 0.0})` | 0 / 10 | True |
| return_precombiner_fields | `test_equal_arm_complex_sweep_and_ordered_input_fractions({'phase': 0.0})` | 0 / 10 | True |

All twelve detections are scientific complex-array assertions on valid records. Final field faults occur before normal output-norm measurement, so constructor/schema failures cannot masquerade as detections. The loss-normalization fault specifically tests evanescent-arm renormalization; blocked-arm quarter/quarter/half behavior is independently checked across all eight survivor phases. Production was never mutated. The complete tracked/unignored inventory (229 files at execution) was unchanged; each copied module was restored byte-for-byte in finally. No unrelated files were restored. No exhaustive sensitivity claim is made.

Every control retains `baseline_command.json`, raw baseline stdout/stderr/exit, exact `mutation.json`, `mutated_interference.py.txt`, mutant command/raw stdout/stderr/exit and the restored package copy. Aggregate report, progress, production_before.json and production_after.json remain in `runs/v2a_acceptance_20261005/negative_controls_1/`. The reproducible actual mutation definitions are also in the approved tracked `scripts/v2a_negative_controls.py`.

### Exact mutation evidence

**half_amplitude_factor** — Use 0.5 field coefficients instead of 1/sqrt(2).
```python
# Replace exactly once:
scale = 1.0 / math.sqrt(2.0)
# With:
scale = 0.5
```
Original SHA-256 `aae60e19e65261992a99b820062e9b271389403d8cc784eacd67db9cd0cf9eef`; actual mutant `f0f3e0b98dc26071a64791b48fee24f2c937c80371cc921ac82915fa66c0eb18`.

**missing_relative_i** — Replace crossed ±i coefficients by a real positive coefficient.
```python
# Replace exactly once:
reflection = 1j if matrix == "B" else -1j
# With:
reflection = 1.0
```
Original SHA-256 `aae60e19e65261992a99b820062e9b271389403d8cc784eacd67db9cd0cf9eef`; actual mutant `fae84a5cbbf1607259e1d0b5dcd0cbfa81ebe1d8a2ab55dec4ceb78f90d447b4`.

**wrong_relative_i_sign** — Conjugate the chosen crossed phase signs while preserving unitary magnitude.
```python
# Replace exactly once:
reflection = 1j if matrix == "B" else -1j
# With:
reflection = -1j if matrix == "B" else 1j
```
Original SHA-256 `aae60e19e65261992a99b820062e9b271389403d8cc784eacd67db9cd0cf9eef`; actual mutant `43c3f76c6946d9d8110f0e3d4db833e4a6be7fed67e79068a12ea103008196a1`.

**intensity_addition** — Add incoherent intensities, replacing both coherent output phases by zero.
```python
# Replace exactly once:
mixed_0 = (port_0.data + reflection * port_1.data) * scale
            mixed_1 = (reflection * port_0.data + port_1.data) * scale
# With:
mixed_0 = np.sqrt((np.abs(port_0.data)**2 + np.abs(port_1.data)**2)/2).astype(np.complex128)
            mixed_1 = mixed_0.copy()
```
Original SHA-256 `aae60e19e65261992a99b820062e9b271389403d8cc784eacd67db9cd0cf9eef`; actual mutant `4d5e9e4a9047740d0958255fa0969f5724539e648b6bf7e0f782bef69eff5385`.

**reset_arm_phase** — Discard the incoming arm phase before the extra prescribed phase.
```python
# Replace exactly once:
rotated = field.data * complex(math.cos(phase), math.sin(phase))
# With:
rotated = np.abs(field.data) * complex(math.cos(phase), math.sin(phase))
```
Original SHA-256 `aae60e19e65261992a99b820062e9b271389403d8cc784eacd67db9cd0cf9eef`; actual mutant `d7f615e7c37d0ef6bd2c023d4ec5c882690bc394c971701d616f62a9285a6352`.

**ignore_prescribed_phase** — Ignore the arm-1 prescribed phase at pi.
```python
# Replace exactly once:
rotated = field.data * complex(math.cos(phase), math.sin(phase))
# With:
rotated = field.data.copy()
```
Original SHA-256 `aae60e19e65261992a99b820062e9b271389403d8cc784eacd67db9cd0cf9eef`; actual mutant `b1f0e4bffd909f77e51c0d9a22ba20b4b65e0bbe99a3b04b2590575779c75e77`.

**omit_ASM_carrier** — Multiply existing ASM output by exp(-ikL), removing its scalar carrier only.
```python
# Append to copied new module:

# OWNED DELIBERATE CONTROL: omit scalar carrier.
_v2a_original_asm = propagate_angular_spectrum
def propagate_angular_spectrum(field, *, distance_m, pad_factor):
    result = _v2a_original_asm(field, distance_m=distance_m, pad_factor=pad_factor)
    angle = -1 * (2 * math.pi / field.wavelength_m) * distance_m
    factor = complex(math.cos(angle), math.sin(angle))
    return ComplexField(data=result.data * factor, grid=result.grid,
                        wavelength_m=result.wavelength_m)

```
Original SHA-256 `aae60e19e65261992a99b820062e9b271389403d8cc784eacd67db9cd0cf9eef`; actual mutant `bd8ec9dd5d731b7359baefbd12647a6731d095fa02abb33ce1165df8a4607cac`.

**duplicate_ASM_carrier** — Multiply existing ASM output by an additional exp(+ikL).
```python
# Append to copied new module:

# OWNED DELIBERATE CONTROL: duplicate scalar carrier.
_v2a_original_asm = propagate_angular_spectrum
def propagate_angular_spectrum(field, *, distance_m, pad_factor):
    result = _v2a_original_asm(field, distance_m=distance_m, pad_factor=pad_factor)
    angle = 1 * (2 * math.pi / field.wavelength_m) * distance_m
    factor = complex(math.cos(angle), math.sin(angle))
    return ComplexField(data=result.data * factor, grid=result.grid,
                        wavelength_m=result.wavelength_m)

```
Original SHA-256 `aae60e19e65261992a99b820062e9b271389403d8cc784eacd67db9cd0cf9eef`; actual mutant `5305adf88aecb51c81fda352f9b3300efbaea9eab07efb8089f2fe8616c9cbd7`.

**normalize_arm_after_loss** — Rescale each propagated arm to hide supported forward-evanescent norm loss.
```python
# Append to copied new module:

# OWNED DELIBERATE CONTROL: replace lost arm norm by its pre-travel value.
_v2a_original_asm = propagate_angular_spectrum
def propagate_angular_spectrum(field, *, distance_m, pad_factor):
    result = _v2a_original_asm(field, distance_m=distance_m, pad_factor=pad_factor)
    before = float(np.sum(np.abs(field.data)**2, dtype=np.float64)*field.grid.dx*field.grid.dy)
    after = float(np.sum(np.abs(result.data)**2, dtype=np.float64)*result.grid.dx*result.grid.dy)
    factor = math.sqrt(before/after) if after > 0 else 1.0
    return ComplexField(data=result.data*factor, grid=result.grid,
                        wavelength_m=result.wavelength_m)

```
Original SHA-256 `aae60e19e65261992a99b820062e9b271389403d8cc784eacd67db9cd0cf9eef`; actual mutant `c7fa197ca3642aa0aa21fc81c77ce3693657ac22f3071c8515b84e6a06ca5b7b`.

**flip_output_y** — Flip output rows while retaining the same physical grid and valid scalar norms.
```python
# Replace exactly once:
outputs = mix_balanced(combiner_0, combiner_1, matrix="B_dagger")
# With:
outputs = tuple(ComplexField(data=np.flip(field.data, axis=0), grid=field.grid, wavelength_m=field.wavelength_m) for field in mix_balanced(combiner_0, combiner_1, matrix="B_dagger"))
```
Original SHA-256 `aae60e19e65261992a99b820062e9b271389403d8cc784eacd67db9cd0cf9eef`; actual mutant `5ea8bfc2f97cb1099a87bd7bd85f4d8b665818eb388a37e1c79fb257efbd4fef`.

**swap_output_ports** — Reverse final port ordering, recomputing each final measured norm normally.
```python
# Replace exactly once:
outputs = mix_balanced(combiner_0, combiner_1, matrix="B_dagger")
# With:
outputs = tuple(reversed(mix_balanced(combiner_0, combiner_1, matrix="B_dagger")))
```
Original SHA-256 `aae60e19e65261992a99b820062e9b271389403d8cc784eacd67db9cd0cf9eef`; actual mutant `69d3fbbda85e8292dcfc5273f008f666473f3e77f9447838141cb13491d9c392`.

**return_precombiner_fields** — Return the actual precombiner arm fields instead of coherent recombination.
```python
# Replace exactly once:
outputs = mix_balanced(combiner_0, combiner_1, matrix="B_dagger")
# With:
outputs = (combiner_0, combiner_1)
```
Original SHA-256 `aae60e19e65261992a99b820062e9b271389403d8cc784eacd67db9cd0cf9eef`; actual mutant `5d434055a2654b4dab43687f6fd43371188a323f2e23bb0a227fadbb3c847fe8`.

## Final full suite after controls/restoration

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 -m pytest -q -p no:cacheprovider --basetemp=runs/v2a_acceptance_20261005/pytest_final
```

Exact unedited stdout:

```text
........................................................................ [  3%]
........................................................................ [  7%]
........................................................................ [ 10%]
........................................................................ [ 14%]
........................................................................ [ 17%]
........................................................................ [ 21%]
........................................................................ [ 25%]
........................................................................ [ 28%]
........................................................................ [ 32%]
........................................................................ [ 35%]
........................................................................ [ 39%]
........................................................................ [ 43%]
........................................................................ [ 46%]
........................................................................ [ 50%]
........................................................................ [ 53%]
........................................................................ [ 57%]
........................................................................ [ 60%]
........................................................................ [ 64%]
..............................................................s......... [ 68%]
........................................................................ [ 71%]
........................................................................ [ 75%]
........................................................................ [ 78%]
........................................................................ [ 82%]
........................................................................ [ 86%]
........................................................................ [ 89%]
........................................................................ [ 93%]
........................................................................ [ 96%]
...............................................................          [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
2006 passed, 1 skipped in 254.93s (0:04:14)
```

Exit 0, empty stderr. Same retained skip and explanation; no old tests changed. Raw `final_*` captures preserve the command/output/exit. This run follows every deliberate fault and restoration.

## Generated, inspected and regenerated numerical figures

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 scripts\generate_v2a_figures.py --evidence runs\v2a_acceptance_20261005\independent_2
```

Exit `0`; stderr empty. Raw captures retain exact hashes.

```powershell
C:\holographiclab\.venv\Scripts\python.exe -B -X utf8 scripts\generate_v2a_figures.py --evidence runs\v2a_acceptance_20261005\independent_2 --output runs\v2a_acceptance_20261005\figures_regenerated
```

Exit `0`; stderr empty. Raw captures retain exact hashes.

All three final figures were viewed by the generating agent and root. Scientific labels, axes, reference planes, raw scales and the reserved provenance footer were inspected. The initial plotting layout overlapped the footer and x labels; only the approved generator layout was corrected, then all figures were regenerated. The initial independent_1 generation remains separately captured. Final figures use independent_2, with source-evidence SHA-256 `2941f5e7fd1edd42b2d7ff5babfe5ddc5a86eef38d33a50ff9629ae583d0921e`. The generator verifies current core source and every plotted stage norm and saved complex-array byte against actual validation records. Byte identity is same-platform provenance, separate from scientific tolerance comparisons.

| Final figure | SHA-256 of both original and regeneration | bytes |
|---|---|---:|
| fig01_unfolded_interferometer.png | `2cfcb53aadceb86bde1ec4c6362106fd2079ffda612ab0dbd5020935a7bea60e` | 147718 |
| fig02_phase_sweep.png | `5b09038c9dfbb4462e58067ce5e87ce8cc403877bc876662cb8b5caf5febcd50` | 305581 |
| fig03_reference_and_controls.png | `a9456567695decab2d31967ef1ea8fddadabfebd59f9b8d7928a4b33159f79c4` | 197942 |

Figure1 is an explicitly ideal unfolded schematic plus both outputs at phi=.37 on shared raw 0..1 intensity scale. Figure2 retains all eight points, all ten stage norms and signed differences; tau=1 is explicitly assumed for its propagating uniform input. Figure3 preserves actual half-removed/quarter-per-output accounting and asymmetric complex discrepancy maps. These are numerical figures, not V2b browser screenshots.

## Preservation, review and publication sequence

The starting inventory captured every tracked file and all 53 importlib.metadata entries representing 52 unique distribution names, including the two unchanged editable ohlab locations. Every metadata-directory file was hashed. The final protected-file/package comparison checks 207 pre-existing tracked files outside the four allowed documentation modifications; all existing numerical source, tests/guards, exports, apps/frontend/M5 contracts, dependencies, configuration, instructions and historical handoffs remain byte-identical. No install or persistent configuration change occurred. Matplotlib cache/bytecode overrides were confined to copied child-process environment mappings under owned ignored runs; parent and persistent settings were not changed.

The exact 22-path inventory is in the implementation summary. Complete diff/source/figure review and explicit approved-path staging precede one commit. Clean-postcommit import/source-location and 64² demo smoke precede normal origin/main push. Actual commit/local/live-remote/GitHub-API SHAs and final clean state are recorded afterward in ignored `publication_verification.json` and the completion report; this precommit snapshot does not predict them. No qualified-replay requirement is added.

V1 publication closeout is a dated read-back of existing evidence and user acceptance. No V1 frontend build/browser acceptance was rerun. V2b/later models and teaching/learning records were not started or changed.
