# V0 — Tests and reproducible evidence

Recorded 2026-10-01, using the existing Windows-native interpreter
`C:\holographiclab\.venv\Scripts\python.exe`, from accepted M7 baseline
`3b94a2262ae11f7d2316ac4fc5d168fa4881c859`. No package installation, environment
rebuild, global setting change, server or browser is part of V0.

Raw captures belong to ignored `runs/v0_acceptance_20261001/`; key reference
code and reproduction procedures are tracked in approved scripts. Captured
text below is unedited except Markdown LF representation of Windows CRLF.
Planning probes are earlier measurements, not substituted for shipped V0
acceptance. The mathematical definitions are in [math used](math_used.md).

## Baseline — exit 0

Exact command:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest -q -p no:cacheprovider --basetemp=runs/v0_acceptance_20261001/pytest_baseline
```

Exact `baseline_stdout.txt` output:

```text
........................................................................ [  4%]
........................................................................ [  9%]
........................................................................ [ 13%]
........................................................................ [ 18%]
........................................................................ [ 22%]
........................................................................ [ 27%]
........................................................................ [ 32%]
........................................................................ [ 36%]
........................................................................ [ 41%]
........................................................................ [ 45%]
........................................................................ [ 50%]
........................................................................ [ 54%]
........................................................................ [ 59%]
........................................................................ [ 64%]
..............s......................................................... [ 68%]
........................................................................ [ 73%]
........................................................................ [ 77%]
........................................................................ [ 82%]
........................................................................ [ 87%]
........................................................................ [ 91%]
........................................................................ [ 96%]
...........................................................              [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
1570 passed, 1 skipped in 272.58s (0:04:32)
```

Stderr is empty. The existing file-symlink privilege skip remains separate from
real junction coverage and is not removed through elevated privileges.

## Acceptance procedures

The required full run retains every declared continuous-aperture case and
executes the 2048²/1-µm fixture sequentially, releasing large arrays between
cases. The independent references do not use production source/component
helpers to construct expectations. Small direct DFT additionally constructs
its own physical coordinates, signed frequencies, transfer factors,
transmissions and ordered updates. Shared-M1 comparisons are regressions,
not independent optical ground truth.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 scripts\validate_v0_optics.py --full --output runs/v0_acceptance_20261001/full_optical_validation_diagnostics_final
.\.venv\Scripts\python.exe -B -X utf8 examples\sequential_optics.py --output runs/v0_acceptance_20261001/agent_demo/demo_02.json
.\.venv\Scripts\python.exe -B -X utf8 scripts\generate_v0_figures.py --validation-report runs/v0_acceptance_20261001/full_optical_validation_diagnostics_final/validation_report.json
```

Evidence filenames are newly owned captures; repeat numerical validation/demo
uses a fresh output filename. Figure regeneration intentionally rewrites only
the three approved generated PNGs. The convergence figure refuses incomplete
or failing full evidence; it contains no planning-value fallback.

The independently defined aperture metric uses inclusive physical ROI
`|x|<=100 µm AND |y|<=100 µm` and the continuous original 80×120-µm aperture:
`sqrt(sum_ROI(abs(U-Uref)**2)/sum_ROI(abs(Uref)**2))`. It retains amplitude,
carrier and complex prefactor with no fitting, phase alignment, reference-area
adjustment or changed comparison region. Its approved finest-case bound is
0.035; coarse cases need not meet that finest-case bound but must remain reported.



## Initial implementation discoveries, retained separately

The first model/elements run had two failed expectations and 84 passes. The
test fixtures used `waist_z_m=1e300` / observation `z_m=1e300`, but their derived
phase was still finite (about 1e307). The unusable-geometry fixtures were
corrected to 1e308, without changing production behavior or a scientific
tolerance. Subsequent model runs were 89 passes and then 91 passes as resource
limit/dark-source cases were added. The actual initial output follows.

The initial runner test collection used pytest's reserved parametrization name
`request`. It was renamed `selectors`, with no production change; the next
captured run passed 19 tests. The original error was observed directly in tool
output and has no durable raw capture; it is summarized here, not reconstructed
or counted as scientific detection.

The initial diagnostic test compared `25.000000000000004` radius samples against
the exact float `25.0`: one failure and 20 passes in 4.43s. It was corrected to
an explicit float tolerance; no optical-acceptance threshold changed. That
initial output likewise exists only in conversation, not a claimed raw file.
The next captured independent run passed 21 tests.

Cross-review found cancellation in `1-erf(...)` for an exceptionally small
continuous Gaussian outside-window fraction. The diagnostic was changed to a
stable erfc union expression and independently checked using scaled quadrature.
The final value is 8.801041976094034e-93; earlier reports' rounded zero and all
earlier captures are preserved separately, not relabelled final measurements.
This changed only the approved diagnostic/reference script and a new sampling
test, not the propagated fields, optical tolerances or protected M1 code.
The final independent/diagnostic focused run passed 22 tests.


### Initial model/elements fixture failures

Exact `agent_model/pytest_01.txt`:

```text
..............................................................F...F..... [ 83%]
..............                                                           [100%]
================================== FAILURES ===================================
_ test_unusable_derived_geometry_rejected_even_with_zero_amplitude[changes2] __

changes = {'source': {'waist_z_m': 1e+300}}

    @pytest.mark.parametrize("changes", [
        {"source": {"waist_radius_m": 1e-300}},
        {"source": {"center_x_m": 1e300}},
        {"source": {"waist_z_m": 1e300}},
        {"grid": {"dx": 1e300}},
        {"grid": {"dx": 1e-300}},
        {"wavelength_m": 1e-300},
        {"observation": {"z_m": 1e300}},
    ])
    def test_unusable_derived_geometry_rejected_even_with_zero_amplitude(changes):
        definition = spec()
        definition["source"]["amplitude"] = 0
        for key, value in changes.items():
            if isinstance(value, dict):
                definition[key].update(value)
            else:
                definition[key] = value
>       with pytest.raises(ValueError, match="derived geometry"):
E       Failed: DID NOT RAISE ValueError

tests\test_optics_model.py:210: Failed
_ test_unusable_derived_geometry_rejected_even_with_zero_amplitude[changes6] __

changes = {'observation': {'z_m': 1e+300}}

    @pytest.mark.parametrize("changes", [
        {"source": {"waist_radius_m": 1e-300}},
        {"source": {"center_x_m": 1e300}},
        {"source": {"waist_z_m": 1e300}},
        {"grid": {"dx": 1e300}},
        {"grid": {"dx": 1e-300}},
        {"wavelength_m": 1e-300},
        {"observation": {"z_m": 1e300}},
    ])
    def test_unusable_derived_geometry_rejected_even_with_zero_amplitude(changes):
        definition = spec()
        definition["source"]["amplitude"] = 0
        for key, value in changes.items():
            if isinstance(value, dict):
                definition[key].update(value)
            else:
                definition[key] = value
>       with pytest.raises(ValueError, match="derived geometry"):
E       Failed: DID NOT RAISE ValueError

tests\test_optics_model.py:210: Failed
=========================== short test summary info ===========================
FAILED tests/test_optics_model.py::test_unusable_derived_geometry_rejected_even_with_zero_amplitude[changes2]
FAILED tests/test_optics_model.py::test_unusable_derived_geometry_rejected_even_with_zero_amplitude[changes6]
2 failed, 84 passed in 0.40s
```


### Corrected model/elements run

Exact `agent_model/pytest_02.txt`:

```text
........................................................................ [ 80%]
.................                                                        [100%]
89 passed in 0.14s
```


### Model/elements with added boundary cases

Exact `agent_model/pytest_03.txt`:

```text
........................................................................ [ 79%]
...................                                                      [100%]
91 passed in 0.25s
```


### Runner after reserved-name correction

Exact `runner_v2_stdout.txt`:

```text
...................                                                      [100%]
19 passed in 0.54s
```


### Independent optical tests

Exact `focused_independent_stdout.txt`:

```text
.....................                                                    [100%]
21 passed in 2.42s
```


### Final independent/diagnostic focused tests

Exact `focused_independent_diagnostics_final_stdout.txt`:

```text
......................                                                   [100%]
22 passed in 26.62s
```


## Shipped full optical acceptance — exit 0

The final report is `full_optical_validation_diagnostics_final/validation_report.json`.
Its exact command is shown above. Stderr is empty; every required large case
actually ran, sequentially. Total measured script runtime was
13.938340100023197s. Earlier complete reports (11.3334992s and
14.150029999989783s) are separate captures, superseded only by the diagnostic
additions/stable-tail correction. No numerical error or tolerance is replaced
without explanation.

Source reference uses separate amplitude/curvature/Gouy/carrier factors with
A0=2.3, w0=45 µm, phase=0.47 rad, center=(5,-7) µm, and s=-3,0,+3 mm. Relative L2 tolerance
is 2e-11; samplewise checks use explicit rtol/atol in the tracked tests.


| s (mm) | Relative complex L2 | Maximum absolute complex error |
|---|---|---|
| -3 | 1.36827161637e-12 | 4.96530036836e-12 |
| -0 | 6.09976126402e-17 | 2.48253415325e-16 |
| 3 | 1.36827330817e-12 | 4.96536344124e-12 |


Direct-DFT cases use asymmetric mixed-parity grids, unequal pitches and separated noncommuting elements. Relative L2 bound 1e-10; componentwise rtol=1e-10 and atol=1e-10 times reference peak amplitude. Independently derived absolute norms are also compared.


| Shape (ny,nx) | Relative complex L2 | Max absolute error | Reference norm | Actual norm |
|---|---|---|---|---|
| (5, 6) | 4.15217627786e-12 | 5.96746448662e-12 | 1.44413842345e-09 | 1.44413842345e-09 |
| (6, 5) | 3.60332802006e-12 | 6.08586483776e-12 | 2.05663415494e-09 | 2.05663415494e-09 |


### All declared Gaussian window/pitch cases

λ=633 nm, A0=1, w0=100 µm, original waist/source z=0, phase=0, centered. Observation z=20 mm. Free complex-L2 bound 1e-6; signed-lens bound 5e-5 for sufficiently large windows. Small divergent-window counterexamples remain explicitly unaccepted. No fit, phase alignment or norm matching.


| n | Pitch (µm) | f (mm) | Relative complex L2 | Second-moment radius (µm) | Acceptance applies |
|---|---|---|---|---|---|
| 256 | 4 | free | 5.00925194208e-07 | 107.814367981 | True |
| 256 | 4 | 20 | 2.56663245264e-05 | 40.2986171785 | True |
| 256 | 4 | -20 | 0.00102140474657 | 204.020789984 | False |
| 512 | 4 | free | 5.00927157786e-07 | 107.81436798 | True |
| 512 | 4 | 20 | 2.56663246369e-05 | 40.2986171784 | True |
| 512 | 4 | -20 | 2.56663246364e-05 | 204.02097873 | True |
| 1024 | 4 | free | 5.00930583566e-07 | 107.814367981 | True |
| 1024 | 4 | 20 | 2.56663258262e-05 | 40.2986171784 | True |
| 1024 | 4 | -20 | 2.56663258257e-05 | 204.02097873 | True |
| 512 | 2 | free | 5.00925365856e-07 | 107.814367981 | True |
| 512 | 2 | 20 | 2.56663245264e-05 | 40.2986171785 | True |
| 512 | 2 | -20 | 0.00102011760321 | 204.020788882 | False |
| 1024 | 2 | free | 5.00927329572e-07 | 107.81436798 | True |
| 1024 | 2 | 20 | 2.56663246369e-05 | 40.2986171784 | True |
| 1024 | 2 | -20 | 2.56663246364e-05 | 204.02097873 | True |


Refinement leaves free errors near 5.0093e-7 and lens errors near 2.5666e-5. These fixture-specific ASM-versus-paraxial floors are not automatically rounded away or replaced by bit identity. Relative norm differences are 2.22e-16–4.44e-16 in these propagating-spectrum fixtures.


### Gaussian waist behavior

The predicted minimum is 17.205882758272114 mm, not 20 mm. Width rtol=1e-4; complex relative-L2 bound 5e-5. Neighboring observations are distinct experiments and all contain their actual terminal propagation.


| Observation z (mm) | ASM radius (µm) | Analytic radius (µm) | Relative complex L2 |
|---|---|---|---|
| 16.2058827583 | 37.7638023214 | 37.7639834927 | 2.07972619584e-05 |
| 17.2058827583 | 37.3772474052 | 37.3772473687 | 2.20805844374e-05 |
| 18.2058827583 | 37.7641870981 | 37.7639834927 | 2.33638945144e-05 |
| 20 | 40.2986171784 | 40.2980315909 | 2.56663246369e-05 |


### All five bounded continuous-aperture cases

The physical experiment/reference/ROI/metric is specified above and in the math handoff. Finest gate is <=0.035 only at 2048²/1-µm pitch. All coarser cases exceed that finest-case threshold, and remain visible; this is the expected bounded convergence evidence, not a hidden failing acceptance test.


| n | Pitch (µm) | Window (mm) | ROI samples | Relative complex L2 | Sampled area (m²) | Area bias | Below 0.035 |
|---|---|---|---|---|---|---|---|
| 512 | 4 | 2.048 | 2601 | 0.110377718934 | 1.0416e-08 | 0.085 | False |
| 1024 | 4 | 4.096 | 2601 | 0.110411682289 | 1.0416e-08 | 0.085 | False |
| 1024 | 2 | 2.048 | 10201 | 0.05445426184 | 1.0004e-08 | 0.0420833333333 | False |
| 2048 | 2 | 4.096 | 10201 | 0.0544660529761 | 1.0004e-08 | 0.0420833333333 | False |
| 2048 | 1 | 2.048 | 40401 | 0.0270850644795 | 9.801e-09 | 0.0209375 | True |


Physical area remains 9.6e-9 m². The finest sampled area is 9.801e-9 m², a 0.0209375 relative area excess. Enlarging the window alone barely changes the complex error; pitch refinement reduces it. Finest 0.027085064479543036 is about 2.71% relative complex L2, not an intensity error, worst-pixel percentage, universal accuracy or sub-percent claim.


### Fixed physical clipped-Gaussian convergence

Same centered A0=1, phase=0, w0=100-µm source; 80-µm circular aperture and f=20-mm lens colocated at z=0; observation z=20 mm; fixed inclusive ±100-µm ROI. Final default demonstration uses this exact physical fixture. These are same-geometry numerical comparisons, not an independent continuous clipped-Gaussian ground truth.


| n | Pitch (µm) | Source norm | After-aperture norm | Full terminal norm | Selected-ROI norm |
|---|---|---|---|---|---|
| 256 | 4 | 1.57079632679e-08 | 1.13416230158e-08 | 1.13416230158e-08 | 1.05084697931e-08 |
| 512 | 4 | 1.57079632679e-08 | 1.13416230158e-08 | 1.13416230158e-08 | 1.05017986084e-08 |
| 1024 | 4 | 1.57079632679e-08 | 1.13416230158e-08 | 1.13416230158e-08 | 1.05017695891e-08 |
| 512 | 2 | 1.57079632679e-08 | 1.13387865173e-08 | 1.13387865173e-08 | 1.05035370501e-08 |
| 1024 | 2 | 1.57079632679e-08 | 1.13387865173e-08 | 1.13387865173e-08 | 1.04985105797e-08 |


| Comparison | First (n,pitch m) | Second (n,pitch m) | Relative complex L2 on common ROI centers |
|---|---|---|---|
| larger_window_same_pitch | [256, 4e-06] | [512, 4e-06] | 0.0275577572335 |
| larger_window_same_pitch | [512, 4e-06] | [1024, 4e-06] | 0.00159688078489 |
| larger_window_same_pitch | [512, 2e-06] | [1024, 2e-06] | 0.0238791043752 |
| refined_pitch_same_extent_common_centers | [256, 4e-06] | [512, 2e-06] | 0.0247035432195 |
| refined_pitch_same_extent_common_centers | [512, 4e-06] | [1024, 2e-06] | 0.00933706894736 |


The smallest 2-µm-pitch window retains a 0.0238791043752 enlargement discrepancy; smaller pitch alone is no wraparound guarantee. The default 512²/4-µm demonstration differs from the enlarged 1024²/4-µm result by 0.00159688078489 in the declared ROI. No general clipped-beam accuracy threshold is claimed.


### Sampling and continuous-model diagnostics

Analytic Gaussian norm outside the initial source rectangle is 8.801041976094034e-93; outer-five-percent sampled source norm fraction is 7.039094107539546e-76. The source has 25.000000000000004 radius samples and zero evanescent spectral norm for this grid. The analytic adjacent lens-phase increment is 2.028883217673922 rad per axis at the full-window extremum. At 20 mm the maximum analytic propagating transfer-phase increment is 4.876131274562795 rad; source-occupied-bin maximum is 0.40775735818897374 rad. Occupied threshold is spectral intensity >1e-10 of its peak, and the reported occupancy is **the initial source before elements**: apertures/lenses can broaden it. These numbers are diagnostics, not an accuracy badge or an unwrapped-angle argument.

For the rectangular Fresnel reference, extremal aperture-to-ROI displacement is (140,160) µm: rho²/z²=0.001808, maximal quartic path-phase magnitude=0.020279303175324143 rad, exact spherical-minus-quadratic phase=-0.0202609913764958 rad, and relative inverse-distance amplitude difference=0.0009027760199911139. These are local geometry/kernel estimates, separate from sampled-area bias and **not an integrated-field L2 error bound**.


## Nine detecting negative controls — exit 0

Exact command:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 scripts\v0_negative_controls.py --output runs/v0_acceptance_20261001/negative_controls
```

All nine unmutated isolated baselines returned 0. All nine deliberately faulty copies returned the dedicated scientific-AssertionError status 10, rather than import, collection, setup or unrelated exceptions. Production was never mutated; four new numerical-module hashes match before/after. Copies retain their actual fault source and output. The controls demonstrate these concrete faults, not all possible defects.


| Control | Actual fault | Independently detecting assertion |
|---|---|---|
| Wrong lens sign | Negate signed focal length | Analytic signed pointwise complex phase |
| dx on both axes | Transmission on dy=dx grid, retain caller metadata | Hand-listed anisotropic circle membership |
| Wrong SI units | Multiply focal length by 1000 | Analytic SI complex phase |
| Omitted aperture | Return incident field for apertures | Independent absolute transmitted norm |
| Amplitude/intensity confusion | Square-root prescribed source amplitude | Amplitude 2 gives intensity 4 |
| Renormalize after loss | Restore incident norm after aperture | Independent absolute transmitted norm |
| Separated action order | Exchange lens/aperture kinds while retaining position order | Complete independently summed separated train |
| Intermediate crop | Zero exterior after every interval | Complete independently summed separated train |
| Earlier observation field | Return source as terminal and adjust terminal scalar norm coherently | Independent actual terminal complex field |


The ordering control uses separated noncommuting actions, not an exchange of colocated commuting scalar masks/phases. The earlier-field control updates scalar metadata to remain constructor-consistent so an independent complex-field assertion, not merely a constructor check, detects it. Binary 0/1 masks do not distinguish a mask from its square; the amplitude-two source control supplies the nontrivial distinction.


## Shipped standalone demonstration and resources — exit 0

Exact final demo command is shown above. Stderr is empty. `agent_demo/demo_01.json` retains the initial radius-70-µm, phase-0.3, clipped-waist-plane run. Final `demo_02.json` aligns its aperture radius to 80 µm, common source phase to zero and clipped observation to 20 mm so the exact physical demo matches the convergence fixture. This is an explained fixture alignment, not replacement of unexplained historical numbers. The free and four unbounded lens cases use the same source. No Gaussian reference is supplied for the clipped case.


| Case | Terminal z (mm) | Measured runtime (s) | Second-moment radius (µm) | Independent unbounded complex L2 |
|---|---|---|---|---|
| free | 20 | 0.1100859 | 107.81436798 | 5.00927157786e-07 |
| lens_before_waist | 15.2058827583 | 0.150356999977 | 38.9008001681 | 1.95139564989e-05 |
| lens_at_waist | 17.2058827583 | 0.142716800008 | 37.3772474052 | 2.20805844374e-05 |
| lens_after_waist | 19.2058827583 | 0.145707599993 | 38.9015472256 | 2.46472191763e-05 |
| lens_at_f | 20 | 0.147251199989 | 40.2986171784 | 2.56663246369e-05 |
| aperture_lens | 20 | 0.181576599978 | 183.425076125 | not applicable |


| Stage | z (m) | Actual full-window norm | Signed current-minus-previous |
|---|---|---|---|
| source | 0 | 1.57079632679e-08 | undefined/source |
| before:aperture | 0 | 1.57079632679e-08 | 0 |
| after:aperture | 0 | 1.13416230158e-08 | -4.36634025215e-09 |
| before:lens | 0 | 1.13416230158e-08 | 0 |
| after:lens | 0 | 1.13416230158e-08 | 0 |
| observation | 0.02 | 1.13416230158e-08 | 3.30872245021e-24 |


The clipped field's full-window second moment includes broad diffraction tails and is not relabelled a Gaussian waist. The terminal full-window norm and selected-ROI norm are separate; no escaped-power estimate is fabricated.


### Separate resource measurement

The resource pass runs the shipped 512² source/aperture/lens train without recorded intermediate fields. Untraced runtime is measured in its own run; a second run measures tracemalloc after imports/spec creation and garbage collection, with no field/result at baseline. One complex128 array size is exact. Windows values are existing-process snapshots and lifetime peak, not per-call peak. Private commit includes imported-runtime/reservation costs and is not traced allocation or physical working set. n² scaling to larger grids is explicitly extrapolated, not measured. Exact final resource record:

```json
{
  "experiment": {
    "schema_version": 1,
    "model_contract": "v0_aligned_scalar_forward_v1",
    "wavelength_m": 6.33e-07,
    "grid": {
      "ny": 512,
      "nx": 512,
      "dy": 4e-06,
      "dx": 4e-06
    },
    "source": {
      "amplitude": 1.0,
      "phase_rad": 0.0,
      "waist_radius_m": 0.0001,
      "waist_z_m": 0.0,
      "center_x_m": 0.0,
      "center_y_m": 0.0,
      "kind": "gaussian"
    },
    "components": [
      {
        "id": "aperture",
        "z_m": 0.0,
        "radius_m": 8e-05,
        "kind": "circular_aperture"
      },
      {
        "id": "lens",
        "z_m": 0.0,
        "focal_length_m": 0.02,
        "kind": "thin_lens"
      }
    ],
    "observation": {
      "id": "screen",
      "z_m": 0.02
    }
  },
  "untraced_runtime_s": 0.16494190000230446,
  "single_complex128_field_bytes": 4194304,
  "tracing_baseline": "imports/spec completed; no field or result retained; gc collected",
  "traced_baseline_current_bytes": 0,
  "traced_baseline_peak_bytes": 0,
  "traced_current_bytes_with_terminal_result": 4201692,
  "traced_peak_bytes": 27269094,
  "windows_process_before": {
    "working_set_bytes": 54263808,
    "private_commit_bytes": 1589981184,
    "process_lifetime_peak_working_set_bytes": 81432576
  },
  "windows_process_after": {
    "working_set_bytes": 58478592,
    "private_commit_bytes": 1594191872,
    "process_lifetime_peak_working_set_bytes": 81563648
  },
  "process_measurement_scope": "working set/private commit snapshots; peak is lifetime peak, not call-only peak",
  "extrapolated_traced_peak_bytes_1024": 109076376,
  "extrapolated_traced_peak_bytes_2048": 436305504,
  "extrapolation_scope": "n-squared estimate for this train, not measured memory or a reservation guarantee"
}
```


## Figure generation, inspection and regeneration

All three figures use actual shipped calculations, common unnormalized intensity scales where appropriate, an actual-spec longitudinal schematic and labelled display-only phase masking below 1e-6 of each field's peak intensity. View limits do not crop propagation arrays or error metrics. Figure 3 includes all five actual full-validation cases, the physical ROI/reference and separate sampled-area bias.

Every final image was visually inspected; figures 1/2 remained byte-identical after the final diagnostic-only evidence update. Figure 3 was inspected with the latest evidence hash. The full generator then reran: `figures_diagnostics_final_01_stdout.txt` and `_02_stdout.txt` match exactly, all PNG SHA-256 values match, exit codes are 0 and stderr is empty. Exact final generator output follows.


### Final figure generator and identical regeneration

Exact `agent_demo/figures_diagnostics_final_02_stdout.txt`:

```text
docs/handoffs/v0/figures/fig01_gaussian_free.png sha256=1d8935ef3d7733b818a449aeb0460df626b55888b2890184e0db6ae9320f83bd
docs/handoffs/v0/figures/fig02_lens_waist.png sha256=84994b24f2f7c83e6bec8629847ed5d69f2695a315f34a1a5458a9863d0030cd
docs/handoffs/v0/figures/fig03_aperture_convergence.png sha256=c5b7a0c3a68c640b959f022a0b8b86cf1dbf28b3d4e9c1185e82adf8ee5823be
full validation evidence sha256=093ae384f62f9f4adbd6a7240ef0a58274243ad82fb82fdca5da7d4b93e957c9
Shared intensity scales; no display normalization; phase-only mask I < 1e-6 max(I).
```


## Durable exact optical and negative-control captures

The following final optical JSON output preserves every actual window/pitch result and diagnostic rather than relying on ignored scratch files alone. The negative-control JSON preserves exact mutations, detecting assertion names and actual baseline/fault output, including tolerances and differences. Script code remains tracked in the approved inventory.


### Final full required optical validation stdout

Exact `full_optical_validation_diagnostics_final_stdout.txt`:

```text
aperture 512 x 512, pitch 4e-06 m: ROI complex L2 0.110377718934
aperture 1024 x 1024, pitch 4e-06 m: ROI complex L2 0.110411682289
aperture 1024 x 1024, pitch 2e-06 m: ROI complex L2 0.05445426184
aperture 2048 x 2048, pitch 2e-06 m: ROI complex L2 0.0544660529761
aperture 2048 x 2048, pitch 1e-06 m: ROI complex L2 0.0270850644795
{
  "validation_mode": "full_required_acceptance",
  "wavelength_m": 6.33e-07,
  "source_checks": [
    {
      "s_m": -0.003,
      "relative_complex_l2": 1.3682716163722414e-12,
      "max_absolute": 4.965300368364033e-12,
      "tolerance_relative": 2e-11,
      "passed": true
    },
    {
      "s_m": -0.0,
      "relative_complex_l2": 6.099761264021637e-17,
      "max_absolute": 2.482534153247273e-16,
      "tolerance_relative": 2e-11,
      "passed": true
    },
    {
      "s_m": 0.003,
      "relative_complex_l2": 1.3682733081653782e-12,
      "max_absolute": 4.965363441243223e-12,
      "tolerance_relative": 2e-11,
      "passed": true
    }
  ],
  "direct_dft": [
    {
      "shape": [
        5,
        6
      ],
      "relative_complex_l2": 4.152176277858248e-12,
      "max_absolute": 5.9674644866178315e-12,
      "reference_norm": 1.4441384234468963e-09,
      "actual_norm": 1.4441384234456255e-09,
      "tolerance_relative": 1e-10,
      "passed": true
    },
    {
      "shape": [
        6,
        5
      ],
      "relative_complex_l2": 3.6033280200646695e-12,
      "max_absolute": 6.085864837760485e-12,
      "reference_norm": 2.056634154939173e-09,
      "actual_norm": 2.0566341549375344e-09,
      "tolerance_relative": 1e-10,
      "passed": true
    }
  ],
  "gaussian": [
    {
      "n": 256,
      "pitch_m": 4e-06,
      "focal_length_m": null,
      "z_m": 0.02,
      "relative_complex_l2": 5.009251942083436e-07,
      "seconds": 0.020222899998771027,
      "relative_norm_difference": 2.220446049250313e-16,
      "analytic_radius_m": 0.00010781433740508999,
      "second_moment_radius_m": 0.00010781436798072092,
      "acceptance_applies": true,
      "tolerance_relative": 1e-06,
      "passed": true,
      "interpretation": "finite-pitch/window ASM versus paraxial Gaussian; model floor retained"
    },
    {
      "n": 256,
      "pitch_m": 4e-06,
      "focal_length_m": 0.02,
      "z_m": 0.02,
      "relative_complex_l2": 2.5666324526412245e-05,
      "seconds": 0.027243500022450462,
      "relative_norm_difference": 2.220446049250313e-16,
      "analytic_radius_m": 4.029803159086791e-05,
      "second_moment_radius_m": 4.029861717850913e-05,
      "acceptance_applies": true,
      "tolerance_relative": 5e-05,
      "passed": true,
      "interpretation": "finite-pitch/window ASM versus paraxial Gaussian; model floor retained"
    },
    {
      "n": 256,
      "pitch_m": 4e-06,
      "focal_length_m": -0.02,
      "z_m": 0.02,
      "relative_complex_l2": 0.0010214047465718142,
      "seconds": 0.02663020000909455,
      "relative_norm_difference": 2.220446049250313e-16,
      "analytic_radius_m": 0.0002040194386574441,
      "second_moment_radius_m": 0.0002040207899843378,
      "acceptance_applies": false,
      "tolerance_relative": 5e-05,
      "passed": false,
      "interpretation": "small-window counterexample; not accepted as isolated optics"
    },
    {
      "n": 512,
      "pitch_m": 4e-06,
      "focal_length_m": null,
      "z_m": 0.02,
      "relative_complex_l2": 5.009271577859e-07,
      "seconds": 0.09203269999125041,
      "relative_norm_difference": 2.220446049250313e-16,
      "analytic_radius_m": 0.00010781433740508999,
      "second_moment_radius_m": 0.00010781436798041511,
      "acceptance_applies": true,
      "tolerance_relative": 1e-06,
      "passed": true,
      "interpretation": "finite-pitch/window ASM versus paraxial Gaussian; model floor retained"
    },
    {
      "n": 512,
      "pitch_m": 4e-06,
      "focal_length_m": 0.02,
      "z_m": 0.02,
      "relative_complex_l2": 2.566632463693277e-05,
      "seconds": 0.12199009998585097,
      "relative_norm_difference": 4.440892098500626e-16,
      "analytic_radius_m": 4.029803159086791e-05,
      "second_moment_radius_m": 4.0298617178439376e-05,
      "acceptance_applies": true,
      "tolerance_relative": 5e-05,
      "passed": true,
      "interpretation": "finite-pitch/window ASM versus paraxial Gaussian; model floor retained"
    },
    {
      "n": 512,
      "pitch_m": 4e-06,
      "focal_length_m": -0.02,
      "z_m": 0.02,
      "relative_complex_l2": 2.5666324636443386e-05,
      "seconds": 0.13872819999232888,
      "relative_norm_difference": 4.440892098500626e-16,
      "analytic_radius_m": 0.0002040194386574441,
      "second_moment_radius_m": 0.00020402097873044433,
      "acceptance_applies": true,
      "tolerance_relative": 5e-05,
      "passed": true,
      "interpretation": "finite-pitch/window ASM versus paraxial Gaussian; model floor retained"
    },
    {
      "n": 1024,
      "pitch_m": 4e-06,
      "focal_length_m": null,
      "z_m": 0.02,
      "relative_complex_l2": 5.009305835655016e-07,
      "seconds": 0.40191740001318976,
      "relative_norm_difference": 4.440892098500626e-16,
      "analytic_radius_m": 0.00010781433740508999,
      "second_moment_radius_m": 0.00010781436798052316,
      "acceptance_applies": true,
      "tolerance_relative": 1e-06,
      "passed": true,
      "interpretation": "finite-pitch/window ASM versus paraxial Gaussian; model floor retained"
    },
    {
      "n": 1024,
      "pitch_m": 4e-06,
      "focal_length_m": 0.02,
      "z_m": 0.02,
      "relative_complex_l2": 2.5666325826158478e-05,
      "seconds": 0.5766944999922998,
      "relative_norm_difference": 4.440892098500626e-16,
      "analytic_radius_m": 4.029803159086791e-05,
      "second_moment_radius_m": 4.029861717838018e-05,
      "acceptance_applies": true,
      "tolerance_relative": 5e-05,
      "passed": true,
      "interpretation": "finite-pitch/window ASM versus paraxial Gaussian; model floor retained"
    },
    {
      "n": 1024,
      "pitch_m": 4e-06,
      "focal_length_m": -0.02,
      "z_m": 0.02,
      "relative_complex_l2": 2.5666325825668625e-05,
      "seconds": 0.6012167000153568,
      "relative_norm_difference": 4.440892098500626e-16,
      "analytic_radius_m": 0.0002040194386574441,
      "second_moment_radius_m": 0.00020402097873028862,
      "acceptance_applies": true,
      "tolerance_relative": 5e-05,
      "passed": true,
      "interpretation": "finite-pitch/window ASM versus paraxial Gaussian; model floor retained"
    },
    {
      "n": 512,
      "pitch_m": 2e-06,
      "focal_length_m": null,
      "z_m": 0.02,
      "relative_complex_l2": 5.0092536585602e-07,
      "seconds": 0.1023589999822434,
      "relative_norm_difference": 4.440892098500626e-16,
      "analytic_radius_m": 0.00010781433740508999,
      "second_moment_radius_m": 0.00010781436798072092,
      "acceptance_applies": true,
      "tolerance_relative": 1e-06,
      "passed": true,
      "interpretation": "finite-pitch/window ASM versus paraxial Gaussian; model floor retained"
    },
    {
      "n": 512,
      "pitch_m": 2e-06,
      "focal_length_m": 0.02,
      "z_m": 0.02,
      "relative_complex_l2": 2.5666324526387403e-05,
      "seconds": 0.11963530001230538,
      "relative_norm_difference": 4.440892098500626e-16,
      "analytic_radius_m": 4.029803159086791e-05,
      "second_moment_radius_m": 4.029861717850913e-05,
      "acceptance_applies": true,
      "tolerance_relative": 5e-05,
      "passed": true,
      "interpretation": "finite-pitch/window ASM versus paraxial Gaussian; model floor retained"
    },
    {
      "n": 512,
      "pitch_m": 2e-06,
      "focal_length_m": -0.02,
      "z_m": 0.02,
      "relative_complex_l2": 0.0010201176032134387,
      "seconds": 0.12762720001046546,
      "relative_norm_difference": 4.440892098500626e-16,
      "analytic_radius_m": 0.0002040194386574441,
      "second_moment_radius_m": 0.0002040207888820631,
      "acceptance_applies": false,
      "tolerance_relative": 5e-05,
      "passed": false,
      "interpretation": "small-window counterexample; not accepted as isolated optics"
    },
    {
      "n": 1024,
      "pitch_m": 2e-06,
      "focal_length_m": null,
      "z_m": 0.02,
      "relative_complex_l2": 5.009273295719743e-07,
      "seconds": 0.39713970001321286,
      "relative_norm_difference": 4.440892098500626e-16,
      "analytic_radius_m": 0.00010781433740508999,
      "second_moment_radius_m": 0.00010781436798041512,
      "acceptance_applies": true,
      "tolerance_relative": 1e-06,
      "passed": true,
      "interpretation": "finite-pitch/window ASM versus paraxial Gaussian; model floor retained"
    },
    {
      "n": 1024,
      "pitch_m": 2e-06,
      "focal_length_m": 0.02,
      "z_m": 0.02,
      "relative_complex_l2": 2.566632463690686e-05,
      "seconds": 0.5546069999982137,
      "relative_norm_difference": 4.440892098500626e-16,
      "analytic_radius_m": 4.029803159086791e-05,
      "second_moment_radius_m": 4.029861717843937e-05,
      "acceptance_applies": true,
      "tolerance_relative": 5e-05,
      "passed": true,
      "interpretation": "finite-pitch/window ASM versus paraxial Gaussian; model floor retained"
    },
    {
      "n": 1024,
      "pitch_m": 2e-06,
      "focal_length_m": -0.02,
      "z_m": 0.02,
      "relative_complex_l2": 2.566632463644782e-05,
      "seconds": 0.4978949000069406,
      "relative_norm_difference": 4.440892098500626e-16,
      "analytic_radius_m": 0.0002040194386574441,
      "second_moment_radius_m": 0.0002040209787304443,
      "acceptance_applies": true,
      "tolerance_relative": 5e-05,
      "passed": true,
      "interpretation": "finite-pitch/window ASM versus paraxial Gaussian; model floor retained"
    }
  ],
  "waist_scan": {
    "rayleigh_m": 0.049630215696521214,
    "predicted_minimum_z_m": 0.017205882758272114,
    "records": [
      {
        "z_m": 0.016205882758272113,
        "radius_m": 3.776380232137333e-05,
        "analytic_radius_m": 3.776398349273007e-05,
        "relative_complex_l2": 2.0797261958362457e-05
      },
      {
        "z_m": 0.017205882758272114,
        "radius_m": 3.737724740518674e-05,
        "analytic_radius_m": 3.7377247368739484e-05,
        "relative_complex_l2": 2.2080584437366085e-05
      },
      {
        "z_m": 0.018205882758272115,
        "radius_m": 3.776418709812026e-05,
        "analytic_radius_m": 3.776398349273006e-05,
        "relative_complex_l2": 2.3363894514448664e-05
      },
      {
        "z_m": 0.02,
        "radius_m": 4.0298617178439376e-05,
        "analytic_radius_m": 4.029803159086791e-05,
        "relative_complex_l2": 2.566632463693277e-05
      }
    ],
    "passed": true,
    "width_relative_tolerance": 0.0001,
    "complex_relative_tolerance": 5e-05
  },
  "aperture_convergence": [
    {
      "n": 512,
      "pitch_m": 4e-06,
      "extent_m": 0.002048,
      "seconds": 0.09322480001719669,
      "relative_complex_l2_roi": 0.11037771893366682,
      "relative_complex_l2": 0.11037771893366682,
      "roi_rule": "abs(x)<=100e-6 AND abs(y)<=100e-6, inclusive center coordinates",
      "roi_sample_count": 2601,
      "normalization": "absolute unit incident complex amplitude, continuous 80x120um aperture",
      "sampled_area_m2": 1.0415999999999999e-08,
      "physical_area_m2": 9.600000000000002e-09,
      "relative_sampled_area_bias": 0.08499999999999974,
      "finest_gate_applies": false,
      "finest_threshold": 0.035,
      "below_finest_threshold": false,
      "passed": false,
      "limitation": "Complex L2 ROI metric; not intensity, worst-pixel or universal percent accuracy."
    },
    {
      "n": 1024,
      "pitch_m": 4e-06,
      "extent_m": 0.004096,
      "seconds": 0.3087967000028584,
      "relative_complex_l2_roi": 0.1104116822886557,
      "relative_complex_l2": 0.1104116822886557,
      "roi_rule": "abs(x)<=100e-6 AND abs(y)<=100e-6, inclusive center coordinates",
      "roi_sample_count": 2601,
      "normalization": "absolute unit incident complex amplitude, continuous 80x120um aperture",
      "sampled_area_m2": 1.0415999999999999e-08,
      "physical_area_m2": 9.600000000000002e-09,
      "relative_sampled_area_bias": 0.08499999999999974,
      "finest_gate_applies": false,
      "finest_threshold": 0.035,
      "below_finest_threshold": false,
      "passed": false,
      "limitation": "Complex L2 ROI metric; not intensity, worst-pixel or universal percent accuracy."
    },
    {
      "n": 1024,
      "pitch_m": 2e-06,
      "extent_m": 0.002048,
      "seconds": 0.3477804999856744,
      "relative_complex_l2_roi": 0.05445426184002286,
      "relative_complex_l2": 0.05445426184002286,
      "roi_rule": "abs(x)<=100e-6 AND abs(y)<=100e-6, inclusive center coordinates",
      "roi_sample_count": 10201,
      "normalization": "absolute unit incident complex amplitude, continuous 80x120um aperture",
      "sampled_area_m2": 1.0003999999999998e-08,
      "physical_area_m2": 9.600000000000002e-09,
      "relative_sampled_area_bias": 0.04208333333333303,
      "finest_gate_applies": false,
      "finest_threshold": 0.035,
      "below_finest_threshold": false,
      "passed": false,
      "limitation": "Complex L2 ROI metric; not intensity, worst-pixel or universal percent accuracy."
    },
    {
      "n": 2048,
      "pitch_m": 2e-06,
      "extent_m": 0.004096,
      "seconds": 2.1731451000086963,
      "relative_complex_l2_roi": 0.05446605297614645,
      "relative_complex_l2": 0.05446605297614645,
      "roi_rule": "abs(x)<=100e-6 AND abs(y)<=100e-6, inclusive center coordinates",
      "roi_sample_count": 10201,
      "normalization": "absolute unit incident complex amplitude, continuous 80x120um aperture",
      "sampled_area_m2": 1.0003999999999998e-08,
      "physical_area_m2": 9.600000000000002e-09,
      "relative_sampled_area_bias": 0.04208333333333303,
      "finest_gate_applies": false,
      "finest_threshold": 0.035,
      "below_finest_threshold": false,
      "passed": false,
      "limitation": "Complex L2 ROI metric; not intensity, worst-pixel or universal percent accuracy."
    },
    {
      "n": 2048,
      "pitch_m": 1e-06,
      "extent_m": 0.002048,
      "seconds": 2.424051599984523,
      "relative_complex_l2_roi": 0.027085064479543036,
      "relative_complex_l2": 0.027085064479543036,
      "roi_rule": "abs(x)<=100e-6 AND abs(y)<=100e-6, inclusive center coordinates",
      "roi_sample_count": 40401,
      "normalization": "absolute unit incident complex amplitude, continuous 80x120um aperture",
      "sampled_area_m2": 9.800999999999998e-09,
      "physical_area_m2": 9.600000000000002e-09,
      "relative_sampled_area_bias": 0.02093749999999961,
      "finest_gate_applies": true,
      "finest_threshold": 0.035,
      "below_finest_threshold": true,
      "passed": true,
      "limitation": "Complex L2 ROI metric; not intensity, worst-pixel or universal percent accuracy."
    }
  ],
  "apertured_gaussian_convergence": {
    "cases": [
      {
        "n": 256,
        "pitch_m": 4e-06,
        "circular_radius_m": 8e-05,
        "focal_length_m": 0.02,
        "observation_z_m": 0.02,
        "source_norm": 1.5707963267948965e-08,
        "after_aperture_norm": 1.1341623015797918e-08,
        "final_norm": 1.1341623015797921e-08,
        "selected_roi_norm": 1.0508469793075611e-08
      },
      {
        "n": 512,
        "pitch_m": 4e-06,
        "circular_radius_m": 8e-05,
        "focal_length_m": 0.02,
        "observation_z_m": 0.02,
        "source_norm": 1.5707963267948965e-08,
        "after_aperture_norm": 1.1341623015797918e-08,
        "final_norm": 1.1341623015797921e-08,
        "selected_roi_norm": 1.0501798608385716e-08
      },
      {
        "n": 1024,
        "pitch_m": 4e-06,
        "circular_radius_m": 8e-05,
        "focal_length_m": 0.02,
        "observation_z_m": 0.02,
        "source_norm": 1.5707963267948965e-08,
        "after_aperture_norm": 1.1341623015797918e-08,
        "final_norm": 1.1341623015797921e-08,
        "selected_roi_norm": 1.0501769589094171e-08
      },
      {
        "n": 512,
        "pitch_m": 2e-06,
        "circular_radius_m": 8e-05,
        "focal_length_m": 0.02,
        "observation_z_m": 0.02,
        "source_norm": 1.5707963267948965e-08,
        "after_aperture_norm": 1.1338786517259813e-08,
        "final_norm": 1.1338786517259816e-08,
        "selected_roi_norm": 1.0503537050128602e-08
      },
      {
        "n": 1024,
        "pitch_m": 2e-06,
        "circular_radius_m": 8e-05,
        "focal_length_m": 0.02,
        "observation_z_m": 0.02,
        "source_norm": 1.5707963267948965e-08,
        "after_aperture_norm": 1.1338786517259813e-08,
        "final_norm": 1.1338786517259818e-08,
        "selected_roi_norm": 1.0498510579682364e-08
      }
    ],
    "comparisons": [
      {
        "kind": "larger_window_same_pitch",
        "first": [
          256,
          4e-06
        ],
        "second": [
          512,
          4e-06
        ],
        "relative_complex_l2_roi": 0.027557757233547392
      },
      {
        "kind": "larger_window_same_pitch",
        "first": [
          512,
          4e-06
        ],
        "second": [
          1024,
          4e-06
        ],
        "relative_complex_l2_roi": 0.0015968807848949537
      },
      {
        "kind": "larger_window_same_pitch",
        "first": [
          512,
          2e-06
        ],
        "second": [
          1024,
          2e-06
        ],
        "relative_complex_l2_roi": 0.023879104375197805
      },
      {
        "kind": "refined_pitch_same_extent_common_centers",
        "first": [
          256,
          4e-06
        ],
        "second": [
          512,
          2e-06
        ],
        "relative_complex_l2_roi": 0.024703543219539242
      },
      {
        "kind": "refined_pitch_same_extent_common_centers",
        "first": [
          512,
          4e-06
        ],
        "second": [
          1024,
          2e-06
        ],
        "relative_complex_l2_roi": 0.009337068947363284
      }
    ],
    "interpretation": "same fixed physical Gaussian, circle, lens and ROI; no continuous-reference claim"
  },
  "diagnostics": {
    "extent_x_m": 0.002048,
    "extent_y_m": 0.002048,
    "pitch_x_m": 4e-06,
    "pitch_y_m": 4e-06,
    "window_policy": "one complete periodic window; no intermediate crop",
    "continuous_gaussian_fraction_outside_source_rectangle": 8.801041976094034e-93,
    "source_radius_samples_xy": [
      25.000000000000004,
      25.000000000000004
    ],
    "lens_phase_sampling": [
      {
        "id": "lens",
        "max_analytic_adjacent_phase_rad_xy": [
          2.028883217673922,
          2.028883217673922
        ]
      }
    ],
    "source_outer_five_percent_norm_fraction": 7.039094107539546e-76,
    "source_evanescent_spectral_norm_fraction": 0.0,
    "occupied_threshold_relative_to_peak_spectral_intensity": 1e-10,
    "occupied_spectrum_stage": "source before all thin-element actions",
    "occupied_bin_fraction": 0.005878448486328125,
    "transfer_phase_sampling": [
      {
        "distance_m": 0.0,
        "max_analytic_propagating_phase_increment_xy": [
          0.0,
          0.0
        ],
        "max_occupied_phase_increment_xy": [
          0.0,
          0.0
        ]
      },
      {
        "distance_m": 0.02,
        "max_analytic_propagating_phase_increment_xy": [
          4.876131274562795,
          4.876131274562795
        ],
        "max_occupied_phase_increment_xy": [
          0.40775735818897374,
          0.40775735818897374
        ]
      }
    ],
    "limitations": "Indicators distinguish source truncation, pitch, lens and transfer phase. They do not prove isolated-field accuracy; window/refinement evidence is required. Occupied-bin filtering uses the source spectrum; elements can change that spectrum."
  },
  "fresnel_model_estimates": {
    "maximum_transverse_displacement_m": [
      0.00014,
      0.00016
    ],
    "max_rho_squared_over_z_squared": 0.0018080000000000001,
    "maximum_quartic_path_phase_magnitude_rad": 0.020279303175324143,
    "exact_spherical_minus_quadratic_path_phase_rad": -0.0202609913764958,
    "relative_inverse_distance_amplitude_difference": 0.0009027760199911139,
    "interpretation": "Extremal geometric path/kernel estimates, not an integrated-field L2 bound or calibration."
  },
  "reference_policy": "independent physical coordinates/source/transmissions/direct sums; no fitting or normalization",
  "acceptance_passed": true,
  "required_2048_finest_case_executed": true,
  "total_seconds": 13.938340100023197
}
```


### Actual negative-control stdout

Exact `negative_controls_stdout.txt`:

```text
wrong_lens_sign: baseline=0, mutation=10, detected=True
dx_used_for_both_axes: baseline=0, mutation=10, detected=True
incorrect_si_units: baseline=0, mutation=10, detected=True
omitted_aperture: baseline=0, mutation=10, detected=True
source_amplitude_as_intensity: baseline=0, mutation=10, detected=True
renormalization_after_aperture: baseline=0, mutation=10, detected=True
wrong_separated_component_order: baseline=0, mutation=10, detected=True
intermediate_cropping: baseline=0, mutation=10, detected=True
earlier_field_as_observation: baseline=0, mutation=10, detected=True
{
  "controls": [
    {
      "control": "wrong_lens_sign",
      "mutated_module": "elements.py",
      "actual_mutation": "# Deliberate isolated fault: reverse the signed focal length.\nfrom dataclasses import replace as _nc_replace\n_nc_original_apply = apply_component\ndef apply_component(field, component):\n    if isinstance(component, ThinLens):\n        component = _nc_replace(component, focal_length_m=-component.focal_length_m)\n    return _nc_original_apply(field, component)",
      "independently_detecting_assertion": "signed_lens_complex_phase",
      "command": [
        "C:\\holographiclab\\.venv\\Scripts\\python.exe",
        "-B",
        "-X",
        "utf8",
        "C:\\holographiclab\\scripts\\v0_negative_controls.py",
        "--worker",
        "C:\\holographiclab\\runs\\v0_acceptance_20261001\\negative_controls\\wrong_lens_sign",
        "wrong_lens_sign"
      ],
      "baseline_exit_code": 0,
      "mutation_exit_code": 10,
      "scientific_detection": true,
      "baseline_stdout": "{\"status\": \"independent_assertion_passed\", \"control\": \"wrong_lens_sign\", \"assertion\": \"signed_lens_complex_phase\"}\r\n",
      "mutated_stdout": "{\"status\": \"scientific_assertion_failed\", \"control\": \"wrong_lens_sign\", \"assertion\": \"signed_lens_complex_phase\", \"detail\": \"\\nNot equal to tolerance rtol=2e-14, atol=2e-14\\n\\nMismatched elements: 1 / 1 (100%)\\nMax absolute difference among violations: 0.39443892\\nMax relative difference among violations: 0.39443892\\n ACTUAL: array(0.980359+0.197219j)\\n DESIRED: array(0.980359-0.197219j)\"}\r\n",
      "setup_or_exception_failure": false
    },
    {
      "control": "dx_used_for_both_axes",
      "mutated_module": "elements.py",
      "actual_mutation": "# Deliberate isolated fault: compute transmissions with dy=dx.\n_nc_original_apply = apply_component\ndef apply_component(field, component):\n    wrong_grid = SamplingGrid(ny=field.grid.ny, nx=field.grid.nx,\n                              dy=field.grid.dx, dx=field.grid.dx)\n    wrong_field = ComplexField(data=field.data, grid=wrong_grid,\n                               wavelength_m=field.wavelength_m)\n    output = _nc_original_apply(wrong_field, component)\n    return _owned_field(output.data, field.grid, field.wavelength_m)",
      "independently_detecting_assertion": "hand_listed_anisotropic_circle",
      "command": [
        "C:\\holographiclab\\.venv\\Scripts\\python.exe",
        "-B",
        "-X",
        "utf8",
        "C:\\holographiclab\\scripts\\v0_negative_controls.py",
        "--worker",
        "C:\\holographiclab\\runs\\v0_acceptance_20261001\\negative_controls\\dx_used_for_both_axes",
        "dx_used_for_both_axes"
      ],
      "baseline_exit_code": 0,
      "mutation_exit_code": 10,
      "scientific_detection": true,
      "baseline_stdout": "{\"status\": \"independent_assertion_passed\", \"control\": \"dx_used_for_both_axes\", \"assertion\": \"hand_listed_anisotropic_circle\"}\r\n",
      "mutated_stdout": "{\"status\": \"scientific_assertion_failed\", \"control\": \"dx_used_for_both_axes\", \"assertion\": \"hand_listed_anisotropic_circle\", \"detail\": \"\\nArrays are not equal\\n\\nMismatched elements: 6 / 35 (17.1%)\\nFirst 5 mismatches are at indices:\\n [0, 3]: True (ACTUAL), False (DESIRED)\\n [1, 2]: True (ACTUAL), False (DESIRED)\\n [1, 4]: True (ACTUAL), False (DESIRED)\\n [3, 2]: True (ACTUAL), False (DESIRED)\\n [3, 4]: True (ACTUAL), False (DESIRED)\\n ACTUAL: array([[False, False, False,  True, False, False, False],\\n       [False, False,  True,  True,  True, False, False],\\n       [False,  True,  True,  True,  True,  True, False],...\\n DESIRED: array([[False, False, False, False, False, False, False],\\n       [False, False, False,  True, False, False, False],\\n       [False,  True,  True,  True,  True,  True, False],...\"}\r\n",
      "setup_or_exception_failure": false
    },
    {
      "control": "incorrect_si_units",
      "mutated_module": "elements.py",
      "actual_mutation": "# Deliberate isolated fault: interpret focal length in millimetres as metres.\nfrom dataclasses import replace as _nc_replace\n_nc_original_apply = apply_component\ndef apply_component(field, component):\n    if isinstance(component, ThinLens):\n        component = _nc_replace(component, focal_length_m=component.focal_length_m*1000)\n    return _nc_original_apply(field, component)",
      "independently_detecting_assertion": "signed_lens_complex_phase",
      "command": [
        "C:\\holographiclab\\.venv\\Scripts\\python.exe",
        "-B",
        "-X",
        "utf8",
        "C:\\holographiclab\\scripts\\v0_negative_controls.py",
        "--worker",
        "C:\\holographiclab\\runs\\v0_acceptance_20261001\\negative_controls\\incorrect_si_units",
        "incorrect_si_units"
      ],
      "baseline_exit_code": 0,
      "mutation_exit_code": 10,
      "scientific_detection": true,
      "baseline_stdout": "{\"status\": \"independent_assertion_passed\", \"control\": \"incorrect_si_units\", \"assertion\": \"signed_lens_complex_phase\"}\r\n",
      "mutated_stdout": "{\"status\": \"scientific_assertion_failed\", \"control\": \"incorrect_si_units\", \"assertion\": \"signed_lens_complex_phase\", \"detail\": \"\\nNot equal to tolerance rtol=2e-14, atol=2e-14\\n\\nMismatched elements: 1 / 1 (100%)\\nMax absolute difference among violations: 0.19799749\\nMax relative difference among violations: 0.19799749\\n ACTUAL: array(1.-0.000199j)\\n DESIRED: array(0.980359-0.197219j)\"}\r\n",
      "setup_or_exception_failure": false
    },
    {
      "control": "omitted_aperture",
      "mutated_module": "elements.py",
      "actual_mutation": "# Deliberate isolated fault: omit every aperture action.\n_nc_original_apply = apply_component\ndef apply_component(field, component):\n    if isinstance(component, (CircularAperture, RectangularAperture)):\n        return _owned_field(field.data, field.grid, field.wavelength_m)\n    return _nc_original_apply(field, component)",
      "independently_detecting_assertion": "absolute_aperture_transmitted_norm",
      "command": [
        "C:\\holographiclab\\.venv\\Scripts\\python.exe",
        "-B",
        "-X",
        "utf8",
        "C:\\holographiclab\\scripts\\v0_negative_controls.py",
        "--worker",
        "C:\\holographiclab\\runs\\v0_acceptance_20261001\\negative_controls\\omitted_aperture",
        "omitted_aperture"
      ],
      "baseline_exit_code": 0,
      "mutation_exit_code": 10,
      "scientific_detection": true,
      "baseline_stdout": "{\"status\": \"independent_assertion_passed\", \"control\": \"omitted_aperture\", \"assertion\": \"absolute_aperture_transmitted_norm\"}\r\n",
      "mutated_stdout": "{\"status\": \"scientific_assertion_failed\", \"control\": \"omitted_aperture\", \"assertion\": \"absolute_aperture_transmitted_norm\", \"detail\": \"\\nNot equal to tolerance rtol=2e-14, atol=0\\n\\nMismatched elements: 1 / 1 (100%)\\nMax absolute difference among violations: 2.24e-08\\nMax relative difference among violations: 4.\\n ACTUAL: array(2.8e-08)\\n DESIRED: array(5.6e-09)\"}\r\n",
      "setup_or_exception_failure": false
    },
    {
      "control": "source_amplitude_as_intensity",
      "mutated_module": "elements.py",
      "actual_mutation": "# Deliberate isolated fault: sqrt the prescribed field amplitude.\nfrom dataclasses import replace as _nc_replace\n_nc_original_source = sample_source\ndef sample_source(experiment):\n    wrong_source = _nc_replace(experiment.source, amplitude=math.sqrt(experiment.source.amplitude))\n    return _nc_original_source(_nc_replace(experiment, source=wrong_source))",
      "independently_detecting_assertion": "amplitude_two_produces_intensity_four",
      "command": [
        "C:\\holographiclab\\.venv\\Scripts\\python.exe",
        "-B",
        "-X",
        "utf8",
        "C:\\holographiclab\\scripts\\v0_negative_controls.py",
        "--worker",
        "C:\\holographiclab\\runs\\v0_acceptance_20261001\\negative_controls\\source_amplitude_as_intensity",
        "source_amplitude_as_intensity"
      ],
      "baseline_exit_code": 0,
      "mutation_exit_code": 10,
      "scientific_detection": true,
      "baseline_stdout": "{\"status\": \"independent_assertion_passed\", \"control\": \"source_amplitude_as_intensity\", \"assertion\": \"amplitude_two_produces_intensity_four\"}\r\n",
      "mutated_stdout": "{\"status\": \"scientific_assertion_failed\", \"control\": \"source_amplitude_as_intensity\", \"assertion\": \"amplitude_two_produces_intensity_four\", \"detail\": \"\\nNot equal to tolerance rtol=2e-14, atol=8e-14\\n\\nMismatched elements: 49 / 49 (100%)\\nFirst 5 mismatches are at indices:\\n [0, 0]: 1.9999999999999996 (ACTUAL), 4.0 (DESIRED)\\n [0, 1]: 1.9999999999999996 (ACTUAL), 4.0 (DESIRED)\\n [0, 2]: 1.9999999999999996 (ACTUAL), 4.0 (DESIRED)\\n [0, 3]: 1.9999999999999996 (ACTUAL), 4.0 (DESIRED)\\n [0, 4]: 1.9999999999999996 (ACTUAL), 4.0 (DESIRED)\\nMax absolute difference among violations: 2.\\nMax relative difference among violations: 0.5\\n ACTUAL: array([[2., 2., 2., 2., 2., 2., 2.],\\n       [2., 2., 2., 2., 2., 2., 2.],\\n       [2., 2., 2., 2., 2., 2., 2.],...\\n DESIRED: array([[4., 4., 4., 4., 4., 4., 4.],\\n       [4., 4., 4., 4., 4., 4., 4.],\\n       [4., 4., 4., 4., 4., 4., 4.],...\"}\r\n",
      "setup_or_exception_failure": false
    },
    {
      "control": "renormalization_after_aperture",
      "mutated_module": "elements.py",
      "actual_mutation": "# Deliberate isolated fault: restore incident sampled norm after aperture loss.\n_nc_original_apply = apply_component\ndef apply_component(field, component):\n    output = _nc_original_apply(field, component)\n    if isinstance(component, (CircularAperture, RectangularAperture)):\n        before = float(np.sum(np.abs(field.data)**2))\n        after = float(np.sum(np.abs(output.data)**2))\n        if after:\n            output = _owned_field(output.data*math.sqrt(before/after), field.grid, field.wavelength_m)\n    return output",
      "independently_detecting_assertion": "absolute_aperture_transmitted_norm",
      "command": [
        "C:\\holographiclab\\.venv\\Scripts\\python.exe",
        "-B",
        "-X",
        "utf8",
        "C:\\holographiclab\\scripts\\v0_negative_controls.py",
        "--worker",
        "C:\\holographiclab\\runs\\v0_acceptance_20261001\\negative_controls\\renormalization_after_aperture",
        "renormalization_after_aperture"
      ],
      "baseline_exit_code": 0,
      "mutation_exit_code": 10,
      "scientific_detection": true,
      "baseline_stdout": "{\"status\": \"independent_assertion_passed\", \"control\": \"renormalization_after_aperture\", \"assertion\": \"absolute_aperture_transmitted_norm\"}\r\n",
      "mutated_stdout": "{\"status\": \"scientific_assertion_failed\", \"control\": \"renormalization_after_aperture\", \"assertion\": \"absolute_aperture_transmitted_norm\", \"detail\": \"\\nNot equal to tolerance rtol=2e-14, atol=0\\n\\nMismatched elements: 1 / 1 (100%)\\nMax absolute difference among violations: 2.24e-08\\nMax relative difference among violations: 4.\\n ACTUAL: array(2.8e-08)\\n DESIRED: array(5.6e-09)\"}\r\n",
      "setup_or_exception_failure": false
    },
    {
      "control": "wrong_separated_component_order",
      "mutated_module": "simulation.py",
      "actual_mutation": "# Deliberate isolated fault: exchange separated lens/aperture actions, retaining z order.\n_nc_original_run = run_experiment\ndef run_experiment(experiment, *, record_fields=()):\n    spec = experiment.to_dict()\n    components = spec['components']\n    if len(components) >= 2:\n        first, second = components[0].copy(), components[1].copy()\n        first_z, second_z = first['z_m'], second['z_m']\n        second['z_m'], first['z_m'] = first_z, second_z\n        components[0], components[1] = second, first\n    wrong = SequentialExperiment.from_dict(spec)\n    return _nc_original_run(wrong, record_fields=record_fields)",
      "independently_detecting_assertion": "independent_separated_train_complex_field",
      "command": [
        "C:\\holographiclab\\.venv\\Scripts\\python.exe",
        "-B",
        "-X",
        "utf8",
        "C:\\holographiclab\\scripts\\v0_negative_controls.py",
        "--worker",
        "C:\\holographiclab\\runs\\v0_acceptance_20261001\\negative_controls\\wrong_separated_component_order",
        "wrong_separated_component_order"
      ],
      "baseline_exit_code": 0,
      "mutation_exit_code": 10,
      "scientific_detection": true,
      "baseline_stdout": "{\"status\": \"independent_assertion_passed\", \"control\": \"wrong_separated_component_order\", \"assertion\": \"independent_separated_train_complex_field\"}\r\n",
      "mutated_stdout": "{\"status\": \"scientific_assertion_failed\", \"control\": \"wrong_separated_component_order\", \"assertion\": \"independent_separated_train_complex_field\", \"detail\": \"\\nNot equal to tolerance rtol=1e-10, atol=1.3965e-10\\n\\nMismatched elements: 30 / 30 (100%)\\nFirst 5 mismatches are at indices:\\n [0, 0]: (-0.11174427307600464+0.3244628574840852j) (ACTUAL), (-0.12077898237028588+0.14449850024154043j) (DESIRED)\\n [0, 1]: (-0.08221928913884306+0.18137080990263177j) (ACTUAL), (-0.10351503439549313+0.3281018202077067j) (DESIRED)\\n [0, 2]: (0.09143250629333599+0.25908309276849545j) (ACTUAL), (0.09074299897213199+0.20205636531326931j) (DESIRED)\\n [0, 3]: (0.10902917009737201+0.4323055395068103j) (ACTUAL), (0.1650052090101201+0.4122111334755528j) (DESIRED)\\n [0, 4]: (0.15862190875747745+0.20413207989491067j) (ACTUAL), (0.1590904106078373+0.14357990936270643j) (DESIRED)\\nMax absolute difference among violations: 0.57669994\\nMax relative difference among violations: 0.99744261\\n ACTUAL: array([[-1.117443e-01+0.324463j, -8.221929e-02+0.181371j,\\n         9.143251e-02+0.259083j,  1.090292e-01+0.432306j,\\n         1.586219e-01+0.204132j, -2.869874e-04+0.092405j],...\\n DESIRED: array([[-0.120779+0.144499j, -0.103515+0.328102j,  0.090743+0.202056j,\\n         0.165005+0.412211j,  0.15909 +0.14358j , -0.021305+0.241571j],\\n       [ 0.263065+0.378353j,  0.707295+0.456173j,  0.535546-0.083571j,...\"}\r\n",
      "setup_or_exception_failure": false
    },
    {
      "control": "intermediate_cropping",
      "mutated_module": "simulation.py",
      "actual_mutation": "# Deliberate isolated fault: discard exterior field after each interval.\n_nc_original_propagate = propagate_angular_spectrum\ndef propagate_angular_spectrum(field, *, distance_m, pad_factor=1):\n    output = _nc_original_propagate(field, distance_m=distance_m, pad_factor=pad_factor)\n    cropped = output.data.copy()\n    ny, nx = cropped.shape\n    keep = np.zeros(cropped.shape, dtype=bool)\n    keep[max(0,ny//2-1):ny//2+2, max(0,nx//2-1):nx//2+2] = True\n    cropped[~keep] = 0\n    return _owned_field(cropped, field.grid, field.wavelength_m)",
      "independently_detecting_assertion": "independent_separated_train_complex_field",
      "command": [
        "C:\\holographiclab\\.venv\\Scripts\\python.exe",
        "-B",
        "-X",
        "utf8",
        "C:\\holographiclab\\scripts\\v0_negative_controls.py",
        "--worker",
        "C:\\holographiclab\\runs\\v0_acceptance_20261001\\negative_controls\\intermediate_cropping",
        "intermediate_cropping"
      ],
      "baseline_exit_code": 0,
      "mutation_exit_code": 10,
      "scientific_detection": true,
      "baseline_stdout": "{\"status\": \"independent_assertion_passed\", \"control\": \"intermediate_cropping\", \"assertion\": \"independent_separated_train_complex_field\"}\r\n",
      "mutated_stdout": "{\"status\": \"scientific_assertion_failed\", \"control\": \"intermediate_cropping\", \"assertion\": \"independent_separated_train_complex_field\", \"detail\": \"\\nNot equal to tolerance rtol=1e-10, atol=1.3965e-10\\n\\nMismatched elements: 30 / 30 (100%)\\nFirst 5 mismatches are at indices:\\n [0, 0]: 0j (ACTUAL), (-0.12077898237028588+0.14449850024154043j) (DESIRED)\\n [0, 1]: 0j (ACTUAL), (-0.10351503439549313+0.3281018202077067j) (DESIRED)\\n [0, 2]: 0j (ACTUAL), (0.09074299897213199+0.20205636531326931j) (DESIRED)\\n [0, 3]: 0j (ACTUAL), (0.1650052090101201+0.4122111334755528j) (DESIRED)\\n [0, 4]: 0j (ACTUAL), (0.1590904106078373+0.14357990936270643j) (DESIRED)\\nMax absolute difference among violations: 1.10538166\\nMax relative difference among violations: 1.12132358\\n ACTUAL: array([[0.      +0.j      , 0.      +0.j      , 0.      +0.j      ,\\n        0.      +0.j      , 0.      +0.j      , 0.      +0.j      ],\\n       [0.      +0.j      , 0.      +0.j      , 0.583269-0.318128j,...\\n DESIRED: array([[-0.120779+0.144499j, -0.103515+0.328102j,  0.090743+0.202056j,\\n         0.165005+0.412211j,  0.15909 +0.14358j , -0.021305+0.241571j],\\n       [ 0.263065+0.378353j,  0.707295+0.456173j,  0.535546-0.083571j,...\"}\r\n",
      "setup_or_exception_failure": false
    },
    {
      "control": "earlier_field_as_observation",
      "mutated_module": "simulation.py",
      "actual_mutation": "# Deliberate isolated fault: coherently relabel source as terminal field.\n# Update the scalar terminal norm too, so constructor consistency is not detection.\nfrom dataclasses import replace as _nc_replace\n_nc_original_run = run_experiment\ndef run_experiment(experiment, *, record_fields=()):\n    actual = _nc_original_run(experiment, record_fields=record_fields)\n    earlier = sample_source(experiment)\n    terminal = _nc_replace(actual.stages[-1], norm=_sampled_norm(earlier))\n    return _nc_replace(actual, observation=earlier, stages=actual.stages[:-1]+(terminal,))",
      "independently_detecting_assertion": "independent_terminal_complex_field",
      "command": [
        "C:\\holographiclab\\.venv\\Scripts\\python.exe",
        "-B",
        "-X",
        "utf8",
        "C:\\holographiclab\\scripts\\v0_negative_controls.py",
        "--worker",
        "C:\\holographiclab\\runs\\v0_acceptance_20261001\\negative_controls\\earlier_field_as_observation",
        "earlier_field_as_observation"
      ],
      "baseline_exit_code": 0,
      "mutation_exit_code": 10,
      "scientific_detection": true,
      "baseline_stdout": "{\"status\": \"independent_assertion_passed\", \"control\": \"earlier_field_as_observation\", \"assertion\": \"independent_terminal_complex_field\"}\r\n",
      "mutated_stdout": "{\"status\": \"scientific_assertion_failed\", \"control\": \"earlier_field_as_observation\", \"assertion\": \"independent_terminal_complex_field\", \"detail\": \"\\nNot equal to tolerance rtol=1e-10, atol=1.3965e-10\\n\\nMismatched elements: 30 / 30 (100%)\\nFirst 5 mismatches are at indices:\\n [0, 0]: (0.19703035356849444-0.019348749118204823j) (ACTUAL), (-0.12077898237028588+0.14449850024154043j) (DESIRED)\\n [0, 1]: (0.4114957241617348-0.08114432642169626j) (ACTUAL), (-0.10351503439549313+0.3281018202077067j) (DESIRED)\\n [0, 2]: (0.6656777686594724-0.17610506840912962j) (ACTUAL), (0.09074299897213199+0.20205636531326931j) (DESIRED)\\n [0, 3]: (0.8395517120604218-0.2502374338726604j) (ACTUAL), (0.1650052090101201+0.4122111334755528j) (DESIRED)\\n [0, 4]: (0.8281930048272792-0.24520560706461678j) (ACTUAL), (0.1590904106078373+0.14357990936270643j) (DESIRED)\\nMax absolute difference among violations: 1.12418704\\nMax relative difference among violations: 3.61106725\\n ACTUAL: array([[0.19703 -0.019349j, 0.411496-0.081144j, 0.665678-0.176105j,\\n        0.839552-0.250237j, 0.828193-0.245206j, 0.638899-0.16528j ],\\n       [0.339068-0.057898j, 0.703102-0.191513j, 1.131865-0.387516j,...\\n DESIRED: array([[-0.120779+0.144499j, -0.103515+0.328102j,  0.090743+0.202056j,\\n         0.165005+0.412211j,  0.15909 +0.14358j , -0.021305+0.241571j],\\n       [ 0.263065+0.378353j,  0.707295+0.456173j,  0.535546-0.083571j,...\"}\r\n",
      "setup_or_exception_failure": false
    }
  ],
  "production_hashes_before": {
    "__init__.py": "4ebecb89eaa579e8da253297b75d950503b0e3c40879de8bc84813046a3017b1",
    "model.py": "fc3a3587c67beaf4f52510f27d58f7e13c6c6d31273a8036ba41dddccdd83e02",
    "elements.py": "983a88f3814f03260c6fabd2d537f6d68bb0a0cb422b3a3bc705b9ca0fa766bc",
    "simulation.py": "faa97d9655e1e83fe2bb088f8a1f35041eddda11e8663206f4ffa2d1506021c9"
  },
  "production_hashes_after": {
    "__init__.py": "4ebecb89eaa579e8da253297b75d950503b0e3c40879de8bc84813046a3017b1",
    "model.py": "fc3a3587c67beaf4f52510f27d58f7e13c6c6d31273a8036ba41dddccdd83e02",
    "elements.py": "983a88f3814f03260c6fabd2d537f6d68bb0a0cb422b3a3bc705b9ca0fa766bc",
    "simulation.py": "faa97d9655e1e83fe2bb088f8a1f35041eddda11e8663206f4ffa2d1506021c9"
  },
  "production_unchanged": true,
  "acceptance_passed": true,
  "restoration": "Production was never mutated; only owned isolated copies retain deliberate faults.",
  "limitations": "Nine demonstrated faults; no assertion that all possible scientific defects are detectable."
}
```


## Final retained suite — exit 0

The first complete candidate suite passed 1701 tests with the retained skip in
195.12s. The later stable-tail diagnostic correction added one independently
integrated sampling regression; the final full suite then passed 1702 tests
with the same skip. No protected test or optical acceptance tolerance changed.
These are actual successive measurements, not replacements of the baseline.

Exact final command from the repository root:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest -q -p no:cacheprovider --basetemp=runs/v0_acceptance_20261001/pytest_full_suite_final
```

Exact `full_suite_final_stdout.txt`, with CRLF represented as LF:

```text
........................................................................ [  4%]
........................................................................ [  8%]
........................................................................ [ 12%]
........................................................................ [ 16%]
........................................................................ [ 21%]
........................................................................ [ 25%]
........................................................................ [ 29%]
........................................................................ [ 33%]
........................................................................ [ 38%]
........................................................................ [ 42%]
........................................................................ [ 46%]
........................................................................ [ 50%]
........................................................................ [ 54%]
........................................................................ [ 59%]
........................................................................ [ 63%]
........................................................................ [ 67%]
..s..................................................................... [ 71%]
........................................................................ [ 76%]
........................................................................ [ 80%]
........................................................................ [ 84%]
........................................................................ [ 88%]
........................................................................ [ 93%]
........................................................................ [ 97%]
...............................................                          [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
1702 passed, 1 skipped in 184.06s (0:03:04)
```

Final stderr is empty. The suite retains all 1571 baseline cases and adds
132 cases: 1703 total, including the single explained skip.

Raw final stdout SHA-256: `723305fecb54653fe0f365e6ee4fb1535471c79438d11e6cc4e28d7a88c7b844`.

## Exact scope and retained environment

All 149 pre-existing tracked paths were hashed before implementation. The 145
outside the four approved documentation modifications retain identical SHA-256
bytes, including all existing numerical code, package-root exports, tests and
guards, apps, M5 contracts, dependency/configuration declarations, instructions
and historical handoffs. Exactly 27 paths are changed: 23 created, four modified.
The reviewed pending membership exactly matches this approved list:

```text
README.md
docs/handoffs/v0/code_map.md
docs/handoffs/v0/figures/fig01_gaussian_free.png
docs/handoffs/v0/figures/fig02_lens_waist.png
docs/handoffs/v0/figures/fig03_aperture_convergence.png
docs/handoffs/v0/implementation_summary.md
docs/handoffs/v0/known_limitations.md
docs/handoffs/v0/math_used.md
docs/handoffs/v0/tests_and_evidence.md
docs/handoffs/v0/tutor_context.md
docs/math_conventions.md
docs/milestones.md
docs/roadmap.md
examples/sequential_optics.py
scripts/generate_v0_figures.py
scripts/v0_negative_controls.py
scripts/validate_v0_optics.py
src/ohlab/optics/__init__.py
src/ohlab/optics/elements.py
src/ohlab/optics/model.py
src/ohlab/optics/simulation.py
tests/test_optics_analytic.py
tests/test_optics_architecture.py
tests/test_optics_elements.py
tests/test_optics_model.py
tests/test_optics_sampling.py
tests/test_optics_simulation.py
```

The actual V0 starting inventory has 52 distributions. All 52 current name,
version, captured METADATA SHA-256 and source-location records match it. The
inventory hashes `read_text("METADATA") or ""`; editable ohlab has egg-info
PKG-INFO instead, so its separate package-metadata bytes were not captured at
the start and are not claimed independently hash-verified. Its version/source
location and all protected source/configuration bytes match. No installation,
upgrade, rebuild or environment/settings operation was performed. M7's older
53-distribution record remains historical and is not rewritten to this count.

The ignored scope checker initially needed correction for missing editable
METADATA and comparison-name casing/underscore normalization. Those helper
exceptions/false comparisons are retained as separate initial evidence; the
corrected comparison uses exactly the initial lowercase-name keys and matches
all captured records. They were not environment changes or scientific fault
detections. `scope_reviewed_final.json` records empty protected-file and
installed-distribution differences and exact allowed pending membership.

## Publication boundary at this precommit snapshot

Acceptance is complete. One commit and normal push are approved. After that
commit, the actual clean checkout must pass import/source-location and the
standalone demo smoke check before pushing. Local HEAD, live origin/main and
GitHub API SHA must agree, and the final tree must be clean. These later
outcomes belong to ignored publication evidence and the completion report;
this precommit document does not predict them or insert its own commit SHA.
V0 has no new M5 bundle, provenance migration or qualified-replay requirement.
V1/V2/V3, hardware and the 3D viewer remain unstarted; the existing port-8501
server was not used, stopped or modified.
