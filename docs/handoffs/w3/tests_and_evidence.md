# W3 tests and evidence

The implementation uses the existing Windows-native Python environment and the final frontend freeze09/production assets07. The candidate remains unstaged and uncommitted. User visual acceptance is a separate checkpoint; no commit, push or subsequent optics stage is authorized by this evidence.

## Validation results

| Check | Actual result | Evidence |
|---|---|---|
| Clean baseline Python |3910 passed,1 original Windows symlink skip; native0;146.68s pytest | baseline/python_01 |
| Final Python03 |4202 passed,1 original skip; native0;325.82s pytest | validation/python_final_03 |
| Final installed frontend09 |569 passed across35 files; native0;12.64s reported | frontend/full_unit_scroll_certificate_09 |
| Restored full frontend after negative controls04 |569 passed across35 files; native0;9.90s reported | validation/frontend_restored_full_07 |
| Final frontend typecheck09 |Native0; no output emitted | frontend/typecheck_scroll_certificate_09 |
| Production build07 |Native0; stable before/after source hashes | validation/production_build_final_07; build/source_asset_identity_07.json |
| Independent numerical validation |14 reference cases,0 failures;103 focused tests | core/validator_01; core/focused_05.txt |
| Numerical negative controls |12/12 new W3 faults and16/16 original W2 faults detected | core/negative_controls_02; core/w2_preservation_01 |
| Frontend negative controls04 |Original/restored63 pass; four intended single-assertion failures; live source hashes unchanged | frontend/negative_controls_04 |
| Strict protocol regression |Three expected pre-fix failures; corrected W3+unchanged W2 protocol suites113 pass | backend/halfspace_before_01; backend/halfspace_after_01 |
| Final W3 browser subset |20 invocations pass,0 skips/retries/flaky results; task-owned services closed | acceptance/w3_layout_05; acceptance/w3_05 |

Native subprocess exits, pytest/Vitest-reported durations and enclosing runner durations are recorded separately. Intentional copied-mutant exit1 is not a failing restored production suite. All referenced evidence is under C:/holographiclab/runs/w3_refractive_routing_implementation_01/ unless a different absolute path is given.

## Exact Python commands and complete raw output

The existing interpreter is C:/holographiclab/.venv/Scripts/python.exe, Python3.11.9. Both actual full-suite invocations disable bytecode and pytest cache writes. The original skip remains tests/test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction coverage is separate. No privilege elevation or test change was used to erase it.

### Clean baseline

[baseline/python_01/invocation.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/baseline/python_01/invocation.json); [baseline/python_01/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/baseline/python_01/result.json). Native exit 0; enclosing elapsed 149.70317697525024s. stderr is empty, SHA256 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.

```json
{
  "argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-m",
    "pytest",
    "-q",
    "-p",
    "no:cacheprovider"
  ],
  "cwd": "C:\\holographiclab"
}
```

[Complete original UTF-8 stdout](C:/holographiclab/runs/w3_refractive_routing_implementation_01/baseline/python_01/stdout.bin), SHA256 08b94760005d93f4a95454c4caff90185ec90d5b9fcb1729314981b91429f4ef. The following block preserves every original stdout byte and line ending.

```text
........................................................................ [  1%]
........................................................................ [  3%]
........................................................................ [  5%]
........................................................................ [  7%]
........................................................................ [  9%]
........................................................................ [ 11%]
........................................................................ [ 12%]
........................................................................ [ 14%]
........................................................................ [ 16%]
........................................................................ [ 18%]
........................................................................ [ 20%]
........................................................................ [ 22%]
........................................................................ [ 23%]
........................................................................ [ 25%]
........................................................................ [ 27%]
........................................................................ [ 29%]
........................................................................ [ 31%]
........................................................................ [ 33%]
........................................................................ [ 34%]
........................................................................ [ 36%]
........................................................................ [ 38%]
........................................................................ [ 40%]
........................................................................ [ 42%]
........................................................................ [ 44%]
........................................................................ [ 46%]
........................................................................ [ 47%]
........................................................................ [ 49%]
........................................................................ [ 51%]
........................................................................ [ 53%]
.............................................................s.......... [ 55%]
........................................................................ [ 57%]
........................................................................ [ 58%]
........................................................................ [ 60%]
........................................................................ [ 62%]
........................................................................ [ 64%]
........................................................................ [ 66%]
........................................................................ [ 68%]
........................................................................ [ 69%]
........................................................................ [ 71%]
........................................................................ [ 73%]
........................................................................ [ 75%]
........................................................................ [ 77%]
........................................................................ [ 79%]
........................................................................ [ 81%]
........................................................................ [ 82%]
........................................................................ [ 84%]
........................................................................ [ 86%]
........................................................................ [ 88%]
........................................................................ [ 90%]
........................................................................ [ 92%]
........................................................................ [ 93%]
........................................................................ [ 95%]
........................................................................ [ 97%]
........................................................................ [ 99%]
.......................                                                  [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
3910 passed, 1 skipped in 146.68s (0:02:26)
```

### Final Python03

[validation/python_final_03/invocation.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/validation/python_final_03/invocation.json); [validation/python_final_03/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/validation/python_final_03/result.json). Native exit 0; enclosing elapsed 327.31876707077026s. stderr is empty, SHA256 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.

```json
{
  "argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-m",
    "pytest",
    "-q",
    "-p",
    "no:cacheprovider"
  ],
  "cwd": "C:\\holographiclab"
}
```

[Complete original UTF-8 stdout](C:/holographiclab/runs/w3_refractive_routing_implementation_01/validation/python_final_03/stdout.bin), SHA256 6910c7a347fcbc64dcef01286bc8db85a2ba097b45a385dc0278e03da0d53f1f. The following block preserves every original stdout byte and line ending.

```text
........................................................................ [  1%]
........................................................................ [  3%]
........................................................................ [  5%]
........................................................................ [  6%]
........................................................................ [  8%]
........................................................................ [ 10%]
........................................................................ [ 11%]
........................................................................ [ 13%]
........................................................................ [ 15%]
........................................................................ [ 17%]
........................................................................ [ 18%]
........................................................................ [ 20%]
........................................................................ [ 22%]
........................................................................ [ 23%]
........................................................................ [ 25%]
........................................................................ [ 27%]
........................................................................ [ 29%]
........................................................................ [ 30%]
........................................................................ [ 32%]
........................................................................ [ 34%]
........................................................................ [ 35%]
........................................................................ [ 37%]
........................................................................ [ 39%]
........................................................................ [ 41%]
........................................................................ [ 42%]
........................................................................ [ 44%]
........................................................................ [ 46%]
........................................................................ [ 47%]
........................................................................ [ 49%]
........................................................................ [ 51%]
........................................................................ [ 53%]
....................s................................................... [ 54%]
........................................................................ [ 56%]
........................................................................ [ 58%]
........................................................................ [ 59%]
........................................................................ [ 61%]
........................................................................ [ 63%]
........................................................................ [ 65%]
........................................................................ [ 66%]
........................................................................ [ 68%]
........................................................................ [ 70%]
........................................................................ [ 71%]
........................................................................ [ 73%]
........................................................................ [ 75%]
........................................................................ [ 77%]
........................................................................ [ 78%]
........................................................................ [ 80%]
........................................................................ [ 82%]
........................................................................ [ 83%]
........................................................................ [ 85%]
........................................................................ [ 87%]
........................................................................ [ 89%]
........................................................................ [ 90%]
........................................................................ [ 92%]
........................................................................ [ 94%]
........................................................................ [ 95%]
........................................................................ [ 97%]
........................................................................ [ 99%]
...........................                                              [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_run_artifacts.py:1101: this Windows account lacks symlink privilege; junction is tested separately
4202 passed, 1 skipped in 325.82s (0:05:25)
```

Earlier Python02 output is preserved at [validation/python_final_02/stdout.bin](C:/holographiclab/runs/w3_refractive_routing_implementation_01/validation/python_final_02/stdout.bin) and [validation/python_final_02/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/validation/python_final_02/result.json): 4199 passed/1 skipped, native0,174.83s pytest and176.30085349082947s enclosing duration. It predates the three protocol regressions and is historical evidence, not the final03 result.

## Installed frontend, build and restored protocol commands

These exact argv/cwd values come from saved invocation JSON. Result files retain native exits, raw stdout/stderr hashes and enclosing durations. No installation or dependency upgrade was performed.

**Full frontend09** — [frontend/full_unit_scroll_certificate_09/invocation.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/frontend/full_unit_scroll_certificate_09/invocation.json); [frontend/full_unit_scroll_certificate_09/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/frontend/full_unit_scroll_certificate_09/result.json); native 0, enclosing 13.21360969543457s.

```json
{
  "argv": [
    "C:\\Program Files\\nodejs\\node.exe",
    "node_modules/vitest/vitest.mjs",
    "run"
  ],
  "cwd": "C:\\holographiclab\\frontend\\bench"
}
```

**Restored full frontend07 after controls04** — [validation/frontend_restored_full_07/invocation.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/validation/frontend_restored_full_07/invocation.json); [validation/frontend_restored_full_07/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/validation/frontend_restored_full_07/result.json); native 0, enclosing 10.439442873001099s.

```json
{
  "argv": [
    "C:\\Program Files\\nodejs\\node.exe",
    "node_modules/vitest/vitest.mjs",
    "run"
  ],
  "cwd": "C:\\holographiclab\\frontend\\bench"
}
```

**Typecheck09** — [frontend/typecheck_scroll_certificate_09/invocation.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/frontend/typecheck_scroll_certificate_09/invocation.json); [frontend/typecheck_scroll_certificate_09/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/frontend/typecheck_scroll_certificate_09/result.json); native 0, enclosing 3.5003647804260254s.

```json
{
  "argv": [
    "C:\\Program Files\\nodejs\\node.exe",
    "node_modules/typescript/bin/tsc",
    "--noEmit"
  ],
  "cwd": "C:\\holographiclab\\frontend\\bench"
}
```

**Production build07** — [validation/production_build_final_07/invocation.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/validation/production_build_final_07/invocation.json); [validation/production_build_final_07/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/validation/production_build_final_07/result.json); native 0, enclosing 0.7121164798736572s.

```json
{
  "argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-X",
    "utf8",
    "C:\\holographiclab\\runs\\w3_refractive_routing_implementation_01\\build_verified_07.py"
  ],
  "cwd": "C:\\holographiclab"
}
```

**Corrected W3 and original W2 protocols** — [backend/halfspace_after_01/invocation.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/backend/halfspace_after_01/invocation.json); [backend/halfspace_after_01/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/backend/halfspace_after_01/result.json); native 0, enclosing 2.208841299987398s.

```json
{
  "argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-X",
    "utf8",
    "-m",
    "pytest",
    "-q",
    "-p",
    "no:cacheprovider",
    "tests/test_virtual_bench_refractive_routing_protocol.py",
    "tests/test_virtual_bench_geometric_routing_protocol.py",
    "--basetemp",
    "C:\\holographiclab\\runs\\w3_refractive_routing_implementation_01\\backend\\halfspace_after_01\\pytest_tmp"
  ],
  "cwd": "C:\\holographiclab"
}
```

The production build retains its existing warning about chunks larger than500kB after minification in [validation/production_build_final_07/stderr.bin](C:/holographiclab/runs/w3_refractive_routing_implementation_01/validation/production_build_final_07/stderr.bin). The warning is not an installation failure, and build success is not a rendering-performance guarantee.

## Independent science and numerical policy

The shipped validator uses Decimal90, explicitly constructs stored affine matrices and finite halfspaces, and derives scalar-normal Snell references independently of production geometry/operator helpers. It covers A_slab, B_prism, C_TIR, B_index1.3, B_yaw10, D_multiple_returns, normal, equal_index, exterior_TIR, block_side, triangle_end_hit, triangle_end_miss, finite_plane_miss and combined_XYZ_pose. All14 cases pass with every reference component enclosed.

Predeclared comparisons use position absolute5e-12m, direction absolute2e-12, angle absolute2e-12rad and relative2e-12 tolerances. Measured maxima are2.1503618086384608e-17m position,4.496919387021123e-16 direction and5.551115123125783e-16rad scalar angle. These comparison tolerances do not replace runtime admission.

Measured slab perpendicular displacement is0.005814413464563082m. The exact stored-input Decimal reference is0.00581441346456308086586134791740355269349690925089804035972344578524749643957433267443901079m; measured absolute error is7.6074018934879327587485733974965127604652655421475250356042566732556098921e-19m. The separately qualified ideal-real30-degree/exact0.03m reference is0.00581441346456308213176018471985290728012769694753748701837740287280889858453506865047552713m. It does not replace the stored binary64 direction/thickness target. Parallel-emergence component difference is1.1102230246251565e-16.

The exact planned algebraic operator/point stress calls the shipped Snell/TIR and admission owners. It first rejects operation14 with UnsupportedNumericalInputError: direction width1.474560851200124e-8 exceeds fixed1e-8. This is one algebraic fixture, not a realizable closed-body browser path, a universal14-event cap or a32-event guarantee. Its accepted prefix and failure are preserved without trimming uncertainty or changing thresholds.

Inputs, declared tolerances, exact source identities and results: [core/validator_01/inputs.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/core/validator_01/inputs.json); [core/validator_01/predeclared.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/core/validator_01/predeclared.json); [core/validator_01/results.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/core/validator_01/results.json); [core/validator_01_stdout.txt](C:/holographiclab/runs/w3_refractive_routing_implementation_01/core/validator_01_stdout.txt).

The numerical owner's exact recorded commands are retained in core/owner_review_01.json:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest -q -p no:cacheprovider tests/test_optics_geometric_geometry_seam.py tests/test_optics_refractive_routing.py tests/test_optics_refractive_routing_references.py tests/test_optics_refractive_routing_architecture.py tests/test_optics_geometric_routing_compatibility.py --basetemp runs/w3_refractive_routing_implementation_01/core/pytest_05
.\.venv\Scripts\python.exe -B -X utf8 runs/w3_refractive_routing_implementation_01/core/negative_controls_02.py
.\.venv\Scripts\python.exe -B -X utf8 scripts/validate_w2_geometric_routing.py --output-dir runs/w3_refractive_routing_implementation_01/core/w2_preservation_01 --negative-controls
```

The focused numerical suite passes103 tests in4.08s, native0. W3 copied faults produce17 intended call-phase assertion failures, detecting12/12 faults;14 unmutated selected tests pass and all127 source/test hashes remain equal. Original W2 validation detects its unchanged16/16 fault targets. No working-tree numerical source was mutated for these controls. Setup/import errors are not credited as scientific detection.

Frontend controls04 detect fake Fresnel output, unsupported dispersion, stale identity attachment and a hidden trace on selection through four intended single-assertion failures. Original/restored focused checks63 pass, and the subsequent full installed suite again passes569/35 files in9.90s. These detectors prove representation/copy/state/submission invariants, not independent optical science.

[core/owner_review_01.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/core/owner_review_01.json); [core/negative_controls_02/summary.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/core/negative_controls_02/summary.json); [core/w2_preservation_01/report.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/core/w2_preservation_01/report.json); [frontend/negative_controls_04/report.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/frontend/negative_controls_04/report.json); [validation/frontend_restored_full_07/stdout.bin](C:/holographiclab/runs/w3_refractive_routing_implementation_01/validation/frontend_restored_full_07/stdout.bin).

## Certificate validation and exact compatibility

A genuine-block regression first demonstrated that the Python protocol accepted non-target halfspaces[-1,1] or[-1,0], and a target halfspace[-1,-0.5]. All three failed DID NOT RAISE before correction:3 failed/0.38s, pytest native1. The enclosing evidence wrapper returned0 only because the expected failure was observed. The minimum correction maps positional certificates using already validated canonical face order, requires target lo<=0<=hi and every other upper<0. The corrected W3+unchanged W2 protocol suite passes113/1.71s/native0, with source hashes stable and independent peer confirmation.

The frontend independently enforces canonical face order and the same predicates. Its preserved focused before run reports7 failed,8 passed and31 filtered tests; those31 are unselected cases from the deliberate testNamePattern, not acceptance skips. Target-excluding-zero cases already rejected; the new failures expose non-target straddling/touchingzero in genuine A/B/C and swapped slab face order. Final full569-test runs include the correction. Numerical inputs, arithmetic, schema keys and tolerances are unchanged.

Independent accepted-source differential02 passes15 scientific rows and4 original W2 error rows. Scientific values, IDs, ledger/status/caps and diagnostics match canonical JSON bytes produced from isolated accepted Git source. The independent frozen-spec W3 no-body projection does not call the production projection helper. W3 wrapper bytes intentionally differ. For unknown-key, finite-edge, nearest-tie and nonunit-source errors the comparison verifies unchanged W2 behavior; it does not claim W3 error equivalence outside jointly admitted inputs.

[backend/halfspace_before_01/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/backend/halfspace_before_01/result.json); [backend/halfspace_after_01/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/backend/halfspace_after_01/result.json); [frontend/halfspace_certificate_correction_01/report.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/frontend/halfspace_certificate_correction_01/report.json); [compatibility/differential_02/report.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/compatibility/differential_02/report.json); [compatibility/baseline_reference/source_identity.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/compatibility/baseline_reference/source_identity.json).

## Source-matched CPU, wire and allocation measurements

CPU03/extreme03 use actual public adapters and the final strict protocol. CPU03 separately times validation and25 warm trace+strict-encoding samples. A separate tracemalloc sample includes validation, trace, encoding and JSONparse after imports. HTTP/queue/render time, native/RSS/browser/GPU memory are excluded. Both invocations exit0; extreme03 source hashes are equal before/after.

| CPU03 fixture | Validation s | Trace+encode median s | Min–max s | Trace/validation bytes | Python traced peak bytes |
|---|---:|---:|---:|---:|---:|
| W3_A_parallel_slab | 0.039526799926534295 | 0.03265629999805242 | 0.022451800061389804–0.05069200007710606 | 16122/8934 | 466466 |
| W3_B_prism_deviation | 0.03871580003760755 | 0.027294299914501607 | 0.025127900065854192–0.042663600062951446 | 13529/6784 | 278810 |
| W3_C_prism_TIR | 0.03166290000081062 | 0.027713799965567887 | 0.019646600005216897–0.03198189998511225 | 15614/6838 | 302350 |
| B_index1.3 | 0.035806500003673136 | 0.01982669997960329 | 0.013896699994802475–0.029737800010479987 | 13505/6784 | 276346 |
| B_yaw10_label | 0.018174300086684525 | 0.014856799971312284 | 0.01397159998305142–0.016917800065129995 | 15345/8123 | 279986 |
| max_block_faces_IDs_numeric | 0.05307000002358109 | 0.026384300086647272 | 0.023776300018653274–0.03830569994170219 | 21172/13387 | 565720 |
| max_prism_faces_IDs | 0.03155569999944419 | 0.023619999992661178 | 0.021218399982899427–0.03690349997486919 | 17585/10566 | 548702 |
| max_block_dimensions | 0.04942199995275587 | 0.031428399961441755 | 0.023762900033034384–0.08721180004067719 | 15968/9537 | 323686 |
| max_prism_dimensions | 0.08390270010568202 | 0.056452599936164916 | 0.04758620006032288–0.09239699994213879 | 13563/6978 | 278862 |
| no_body_record256 | 0.0505069000646472 | 0.3136729000834748 | 0.24684299994260073–0.3921739000361413 | 271484/3573 | 3530730 |

| Extreme03 fixture | Request/trace/validation bytes | Admit+trace+encode s | Python traced peak bytes | Branches/events/segments | Status |
|---|---:|---:|---:|---:|---|
| no_body_record256_maxIDs | 2327/289525/4705 | 0.1522493000375107 | 3648422 | 53/128/128 | incomplete |
| body_record128_maxIDs | 2727/157513/16165 | 0.20857979997526854 | 1829788 | 27/64/64 | incomplete |

These actual accepted maximum-record scenes use64-ASCII old IDs,32-ASCII body IDs and nontrivial numeric spellings. They do not prove every possible encoded spelling; atomic512KiB encoding remains authoritative. Incomplete cases preserve every terminal weight rather than becoming complete by assertion. [resources/cpu_03/report.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/resources/cpu_03/report.json); [resources/extreme_03/report.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/resources/extreme_03/report.json); [resources/extreme_03/identity.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/resources/extreme_03/identity.json).

Production frontend owner03/extreme_owner04 load actual final freeze09 decoder and Three CPU factories using the installed compiler and genuine cpu03/extreme03 bytes. Charge includes decoded records, unique backing stores, geometry/material ownership, state, prospective1MiB DOM and old/new/incoming overlap. Test-held raw buffers are excluded. Each source inventory remains unchanged during its native0 probe.

| Final owner fixture | Wire bytes | Retained envelope bytes | Incoming envelope bytes | Within4/8MiB |
|---|---:|---:|---:|---|
| owner03/B_index1.3.json | 13505 | 1223124 | 1539288 | True/True |
| owner03/B_yaw10_label.json | 15345 | 1223124 | 1546648 | True/True |
| owner03/max_block_dimensions.json | 15968 | 1240104 | 1566120 | True/True |
| owner03/max_block_faces_IDs_numeric.json | 21172 | 1342324 | 1689156 | True/True |
| owner03/max_prism_dimensions.json | 13563 | 1223748 | 1540144 | True/True |
| owner03/max_prism_faces_IDs.json | 17585 | 1337220 | 1669704 | True/True |
| owner03/no_body_record256.json | 271484 | 2454564 | 3802644 | True/True |
| owner03/W3_A_parallel_slab.json | 16122 | 1239480 | 1566112 | True/True |
| owner03/W3_B_prism_deviation.json | 13529 | 1223124 | 1539384 | True/True |
| owner03/W3_C_prism_TIR.json | 15614 | 1234140 | 1558740 | True/True |
| extreme_owner04/body_record128_maxIDs.json | 157513 | 1936526 | 2828722 | True/True |
| extreme_owner04/no_body_record256_maxIDs.json | 289525 | 2479192 | 3899436 | True/True |

Each row records500 passive selections without growth and disposed display/apparatus charges0. Global16/32MiB, W3local4/8MiB and W2local2/4MiB remain unchanged. These are app-owned representation charges, not whole-process/native/GPU measurements. [resources/owner_03/report.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/resources/owner_03/report.json); [resources/extreme_owner_04/report.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/resources/extreme_owner_04/report.json). Earlier cpu02/extreme02/owner02/extreme_owner03 measurements remain preserved under their original identities; they are not overwritten or relabelled as final guard timings.

Exact resource reproduction argv/cwd and native exits are recorded in the following invocation/result pairs:

[resources/cpu_invocation_03/invocation.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/resources/cpu_invocation_03/invocation.json); [resources/cpu_invocation_03/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/resources/cpu_invocation_03/result.json) — native 0.

```json
{
  "argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-X",
    "utf8",
    "runs/w3_refractive_routing_implementation_01/resource_cpu.py",
    "--dest",
    "resources/cpu_03"
  ],
  "cwd": "C:\\holographiclab"
}
```

[resources/extreme_invocation_03/invocation.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/resources/extreme_invocation_03/invocation.json); [resources/extreme_invocation_03/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/resources/extreme_invocation_03/result.json) — native 0.

```json
{
  "argv": [
    "C:\\holographiclab\\.venv\\Scripts\\python.exe",
    "-B",
    "-X",
    "utf8",
    "runs/w3_refractive_routing_implementation_01/resource_extreme_final_03.py"
  ],
  "cwd": "C:\\holographiclab"
}
```

[resources/owner_invocation_03/invocation.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/resources/owner_invocation_03/invocation.json); [resources/owner_invocation_03/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/resources/owner_invocation_03/result.json) — native 0.

```json
{
  "argv": [
    "C:\\Program Files\\nodejs\\node.exe",
    "C:\\holographiclab\\runs\\w3_refractive_routing_implementation_01\\owner_probe.mjs",
    "C:\\holographiclab\\runs\\w3_refractive_routing_implementation_01\\resources\\cpu_03",
    "resources/owner_03"
  ],
  "cwd": "C:\\holographiclab"
}
```

[resources/extreme_owner_invocation_04/invocation.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/resources/extreme_owner_invocation_04/invocation.json); [resources/extreme_owner_invocation_04/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/resources/extreme_owner_invocation_04/result.json) — native 0.

```json
{
  "argv": [
    "C:\\Program Files\\nodejs\\node.exe",
    "C:\\holographiclab\\runs\\w3_refractive_routing_implementation_01\\owner_probe.mjs",
    "C:\\holographiclab\\runs\\w3_refractive_routing_implementation_01\\resources\\extreme_03",
    "resources/extreme_owner_04"
  ],
  "cwd": "C:\\holographiclab"
}
```

## Final W3 browser, layout and resource observations

Final assets07/freeze09 pass20 W3 invocations: separate B10 plus the19 B/C invocations in w3_05. All exact required IDs have native browser0, one attempt, retry0,0skips/0unexpected/0flaky, source identity unchanged and successful task-owned cleanup. C04 includes DOM, malformed, wrongidentity, wrongmodel, wrongdigest and wrongmedium as separate declared modes. Production B cases use an assets-only factory; faults are labelled controlled children. No synthetic DTO or second HTTP replay substitutes for captured original bytes.

[acceptance/layout_first_05/plan.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/acceptance/layout_first_05/plan.json); [acceptance/w3_layout_05/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/acceptance/w3_layout_05/result.json); [acceptance/w3_05/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/acceptance/w3_05/result.json). Each invocation retains declaration.json, served_identity.json, exact selection, raw stdout/stderr, browser result and cleanup.

B10 verifies1366×768,1440×900,1920×1080 and actual isolated Chrome200% content zoom. All21 cells are nowrap. Desktop event containers have client/scroll width297/569px; keyboard and pointer reach scrollLeft272 and the complete authoritative string0.18193087514269732 is unobscured. Canvas sizes are736×258.4375,810×390.4375 and1290×570.4375px, with root scroll width exactly the viewport width and stationary canvas during local access. Native scrollend/right-boundary records replace a guessed animation delay while preserving33 arrow actions, assertions, thresholds and timeouts.

Actual200% zoom reports innerWidth709, outerWidth1440, DPR2, visualViewport.scale1 and root scrollWidth709. Its adapted table is654/654px, so full values are visible without horizontal movement; keyboard/pointer scrollLeft0. This uses an isolated profile, not CSS/device/pinch emulation or user-profile changes. Each real normal/zoom context performs one intentional trace; passive scrolling causes none.

B11 records four explicit traces over42.068s of test actions. The original1440×900 WebM duration is42.56s from installed ffmpeg metadata,3485193 bytes, SHA2560e562673efe6ac88c992092dcd05065a5207b1d8d4e0459a021be4baf85ff22e. B index1.2, B index1.3, B+10degY and C/TIR have distinct request UUIDs/scene digests and detected endpoints respectively[0.006090605385328992,0.08,0.12],[-0.004016576768008456,0.08,0.12],[0.003614231619547034,0.08,0.12] and[-0.04,0.08,0.05999999999999999]m. C records entry, internal TIR, exit and receiver under its current identity. Ideal weight1 is bookkeeping, not Fresnel transmission.

The actual headless120-RAF sample reports mean 4.546666666666685ms, p50 4.200000000000728ms, p95 8.200000000000728ms, min 3.7999999999992724ms and max 20.799999999999272ms. Renderer-wide counters are34 geometries,1 texture,16 programs and44 draw calls; renderer/controls/RAF owner counts are each1. Triangle count is NOT_EXPOSED by the unchanged public snapshot. These observations are not universal FPS or total GPU-memory guarantees.

The B11 final global app-owned retained snapshot is653410 bytes. W3 charge344102=72480 numerical+215926 rendering+55696 state; DOM138612 is already included in rendering and must not be added twice. This is a snapshot, not a maximum process-memory claim. B08 mixed-mode explicit release reduces global charge9354222→767818 bytes; W3 numerical71914→0 and W219774→0 while documents and the invalid draft remain preserved. B09 actual context loss/manual recovery retains the original response with one trace. CPU/Node and browser observations have separate allocation scopes.

Detailed browser records: [acceptance\w3_05\W3-B11\browser\custom_w3_evidence_dir\a566b40610da617b8bf70d78\recording_observations.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/acceptance/w3_05/W3-B11/browser/custom_w3_evidence_dir/a566b40610da617b8bf70d78/recording_observations.json); [Original normal-speed recording](C:/holographiclab/runs/w3_refractive_routing_implementation_01/acceptance/w3_05/W3-B11/browser/custom_w3_evidence_dir/a566b40610da617b8bf70d78/recording/page@ec9c2ddad482f3e9600c51e1b62eb28b.webm); [acceptance\w3_layout_05\W3-B10\browser\custom_w3_evidence_dir\981a4364d63af289f353bc17\actual_zoom.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/acceptance/w3_layout_05/W3-B10/browser/custom_w3_evidence_dir/981a4364d63af289f353bc17/actual_zoom.json); [acceptance\w3_layout_05\W3-B10\browser\custom_w3_evidence_dir\981a4364d63af289f353bc17\actual_zoom_access.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/acceptance/w3_layout_05/W3-B10/browser/custom_w3_evidence_dir/981a4364d63af289f353bc17/actual_zoom_access.json).

## Genuine figures and engineering media review

Ten final screenshots were inspected at original resolution, including the three approved A/B/C figures, stale and ambiguity states, desktop sizes and actual200% zoom. Eight original video frames at1,6,11,16,21,26,31 and36s were decoded without resizing, overlays, composition or speed changes and visually inspected. An additional review viewed the A/B/C figures and four sampled video frames. This is engineering sampling, not continuous inspection of every motion frame or the user's final visual acceptance.

The reviewed samples show the editable mounted prism, the detached state after index1.3, explicit recomputed exit refraction, the changed pose/top view and current body-to-body TIR. Still images independently establish presentation only; numerical correctness and no-hidden-trace assertions rely on separate evidence.

| Approved genuine figure | Bytes | SHA256 |
|---|---:|---|
| [parallel_slab.png](C:/holographiclab/docs/handoffs/w3/figures/parallel_slab.png) | 170700 | de0a9abea250680cfdec3673dbbbcf8b73fcd437b0fe535a84f0c934900e46c9 |
| [prism_deviation.png](C:/holographiclab/docs/handoffs/w3/figures/prism_deviation.png) | 181949 | 9545274a798a6096308830319f7638e4ade62e5331de4020dc71bde64ab970f5 |
| [prism_tir.png](C:/holographiclab/docs/handoffs/w3/figures/prism_tir.png) | 180573 | ab599599f8d4111959b598aba7adc2e4953902456ae4c0b5c924b0ec8d693775 |

[frontend/visual_qa_02/figure_copies.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/frontend/visual_qa_02/figure_copies.json) proves byte-identical copies of final B01/B02/B03 screenshots; no reencoding, resizing or annotation. [frontend/visual_qa_02/VISUAL_QA.md](C:/holographiclab/runs/w3_refractive_routing_implementation_01/frontend/visual_qa_02/VISUAL_QA.md); [frontend/recording_qa_01/manifest.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/frontend/recording_qa_01/manifest.json); [frontend/recording_qa_01/PIXEL_REVIEW.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/frontend/recording_qa_01/PIXEL_REVIEW.json). The earlier video-not-yet-reviewed statement in the original screenshot report is a historical creation-time status; the later video review addendum records completed eight-frame inspection.

Remaining presentation limitation: dense source/receiver world labels partly overlap in default prism views. Selected quantitative event badges, Inspector identities and the component list remain readable. Long vector/certificate rows require local horizontal scrolling; no single screenshot proves all columns fit simultaneously. The200% capture is a scrolled numeric close view, not simultaneous visibility of its offscreen bench/header. No further redesign or all-screen accessibility guarantee is claimed.

## Preserved failures and in-scope corrections

These are historical execution snapshots with original artifacts retained. Fresh later runs use separate destinations and source declarations. No failed result is replaced by a later green count.

| Historical evidence | Actual failure and correction provenance |
|---|---|
| baseline/frontend_unit_01; frontend/focused_unit_01 | Native1 during Vite startup with spawn EPERM, before assertion execution. The normal permission path later runs the same installed tooling; baseline498 passes. No package/environment rebuild. |
| core/smoke_01.txt; smoke_02.txt | Initial five presets reject unresolved finite parallel side-face ordering. A swept-plane exclusion certificate in the additive public seam permits the actual finite routes; no epsilon or tolerance relaxation. |
| core/focused_01.txt |2 failed/95 passed: combined-XYZ reference fixture and import isolation. Later focused02–05 remain preserved; final103 passes. |
| frontend/typecheck_02 |Native2 from a readonly-vector to mutable-array test cast. Corrected test typing is covered by later typecheck/full suites. |
| backend/security_before_01; security_after_01 |24 new W3 boundary-envelope failures and2 original-W2 preservation passes. Narrow W3-aware mapping is corrected;228 focused tests pass, with old W2 responses preserved. |
| core/negative_controls_01 |10/12 intended faults detected, native1. One criticality mutant trips a different side guard and is not credited; the original queued-leaf fixture does not reach a pending queue. Revised isolated mutations retain real guards and add recordcap2 reachability; controls02 detects12/12 without numerical threshold changes. |
| frontend/negative_controls_01–04 |Original copied mutants and outputs preserved. Final04 detects four intended single-assertion faults and restores63 focused checks; subsequent full569 tests pass. |
| browser_helpers/inputs_01/FAILED.json |Pure fixture preparation stops on an out-of-scope provenance path before copying files. Fresh inputs02 copies44 referenced files,19 control plans and11 contenders, with no service/browser launch. |
| acceptance/w3_01; core/browser_B03_interval_diagnosis_01.json |B01/B02 pass at their original assets; B03 incorrectly compares an outward K endpoint with nominal scalar tolerance. Exact-rational diagnosis shows[-0.12500000000030223,-0.12499999999969845] encloses-1/8 and is strictly negative. Only the incorrect test comparison changes; no new K-width policy or uncertainty trimming. |
| frontend/presentation_gap_01 |Bounded A-readout and B03-assertion correction is preserved as a reviewed patch/application with exact source identities; original scientific values remain authoritative. |
| acceptance/w3_02 |B01–B09 pass on assets05; B10 fails actual canvas height250 versus unchanged>250. A bounded W3 header CSS correction produces later assets06. |
| acceptance/w3_layout_03 |B10 on assets06 fails keyboard endpoint241 versus272. Source-qualified diagnostics distinguish native completion and real sticky-column occlusion; assertions/timeouts are not weakened. |
| frontend/scroll_diagnosis_01/run_01 |One genuine Trace/native observations; optional CSS control blocked by existing CSP, native1. CSP is not bypassed; browser/service cleanup passes. |
| frontend/scroll_diagnosis_01/run_02 |Native0 diagnostic with one Trace, no page intervention/error, source/result unchanged. Native scroll ultimately reaches272, but the sticky ID column obscures leading scalar digits; this is diagnostic success, not acceptance. |
| backend/halfspace_before_01 |Three genuine certificate forgeries produce expected DID NOT RAISE failures; after correction113 protocol tests pass. |
| frontend/halfspace_certificate_before_01 |Seven expected certificate failures,8 passes and31 deliberately filtered tests. Canonical order and strict other-face guards are added; final full suites pass569 without that filter. |
| acceptance/prepare_invocation_04 |Discovery rejects basename owners lacking tests/ prefixes, native1 before Playwright subprocess/output-directory/service/browser creation. Fresh preparation05 fixes only owner paths, runs discovery-only successfully and freezes the same136-invocation inventory. |

Key failure artifacts: [baseline/frontend_unit_01/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/baseline/frontend_unit_01/result.json); [core/focused_01.txt](C:/holographiclab/runs/w3_refractive_routing_implementation_01/core/focused_01.txt); [backend/security_before_01/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/backend/security_before_01/result.json); [core/negative_controls_01/summary.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/core/negative_controls_01/summary.json); [acceptance/w3_01/STOPPED.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/acceptance/w3_01/STOPPED.json); [core/browser_B03_interval_diagnosis_01.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/core/browser_B03_interval_diagnosis_01.json); [acceptance/w3_02/STOPPED.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/acceptance/w3_02/STOPPED.json); [acceptance/w3_layout_03/STOPPED.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/acceptance/w3_layout_03/STOPPED.json); [frontend/scroll_diagnosis_01/run_01/browser/failure.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/frontend/scroll_diagnosis_01/run_01/browser/failure.json); [frontend/scroll_diagnosis_01/run_02/browser/diagnosis.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/frontend/scroll_diagnosis_01/run_02/browser/diagnosis.json); [acceptance/prepare_invocation_04/stderr.bin](C:/holographiclab/runs/w3_refractive_routing_implementation_01/acceptance/prepare_invocation_04/stderr.bin); [acceptance/prepare_invocation_05/result.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/acceptance/prepare_invocation_05/result.json).

## Legacy browser preservation

The frozen plan declares136 invocations and119 distinct IDs across12 owners, including20 W3 invocations and116 non-W3 invocations. Eight ordinary controlled-only IDs execute through19 exact labelled controls rather than being skipped. All original recording cases remain included. Results below must come from actual completed final-source groups; discovery-only entries are not acceptance results.

| Final group | Required / passed | Actual skips / retries | Native exit | Enclosing seconds |
|---|---:|---:|---:|---:|
| w3_layout | 1 / 1 | 0 / 0 | 0 | 23.352571 |
| w3 | 19 / 19 | 0 / 0 | 0 | 351.223624 |
| legacy | 55 / 55 | 0 / 0 | 0 | 940.362686 |
| english | 7 / 7 | 0 / 0 | 0 | 103.393908 |
| w2 | 23 / 23 | 0 / 0 | 0 | 395.752110 |
| w1 | 12 / 12 | 0 / 0 | 0 | 276.071353 |
| legacy_controls | 19 / 19 | 0 / 0 | 0 | 354.814367 |

**All136 invocations passed across119 distinct discovered IDs; actual skips0, retries0, flaky0.** Each raw Playwright result has one passed attempt and each owned service has native0 cleanup with port8510 free. The independent disk audit cross-checks every ID, mode, fixture/source/tool/build identity, original-response/output ownership and all four recording files. Earlier failed attempts remain separate historical evidence, not hidden retries of this final declaration.

[Per-invocation matrix](C:/holographiclab/runs/w3_refractive_routing_implementation_01/acceptance/final_matrix01/matrix.md); [machine audit and136 records](C:/holographiclab/runs/w3_refractive_routing_implementation_01/acceptance/final_matrix01/summary.json); [recording identities](C:/holographiclab/runs/w3_refractive_routing_implementation_01/acceptance/final_matrix01/recordings.json). The remaining-groups enclosing runner returned0; its2071.4793615341187s covers five sequential groups and is not the duration of one scientific computation.

## Final source, scope and environment verification

The accepted baseline is main828c7ff9080b174d5eae73b36f2c43608a4c94d7. Preflight records the exact46 approved paths,471 baseline tracked files,81 planning files,8885 historical W2 files and53 existing Python distributions. Python3.11.9, NumPy2.4.6, SciPy1.17.1 and pytest9.1.1 remain the recorded environment. No installation/upgrade, lockfile change, Conda/WSL switch, venv recreation, persistent environment/pip/global Git change or historical/planning rewrite is part of this stage.

The source-qualified pre-browser report preserves458 protected tracked files, all planning/history bytes and distribution/package metadata, with empty index and no unrelated path. Its earlier43/46 status correctly precedes the three genuine figure copies. Final exact inventory/diff and environment proof belong below rather than being inferred from that intermediate snapshot.

The complete pre-closeout check passed: exactly46 approved changed paths (13 modifications/33 creations), no unrelated path, empty staged inventory, baseline main HEAD/upstream unchanged,458 protected tracked hashes unchanged,81 planning files and8885 W2 historical files unchanged, all53 Python distribution versions/metadata and seven frontend package manifests unchanged. This snapshot precedes final handoff prose assembly; it does not pretend to hash the later prose.

[Complete pre-closeout report](C:/holographiclab/runs/w3_refractive_routing_implementation_01/scope/pre_closeout_01/report.json). The separate final review export records all46 final file bytes, binary PNG patches, per-file hashes and the raw empty-index identity. Its final artifacts are [review_final.diff](C:/holographiclab/runs/w3_refractive_routing_implementation_01/review/final_01/review_final.diff) and [review_manifest.json](C:/holographiclab/runs/w3_refractive_routing_implementation_01/review/final_01/review_manifest.json). The final post-export environment/history/working-tree check is stored separately at scope/final_01/report.json. These latter artifacts are generated after this prose to avoid embedding a self-referential diff hash; the completion report must verify their actual success before delivery.

No stage, commit or push occurred. The working tree intentionally retains the approved46-path candidate; it is not claimed clean. No later optics, persistence, hardware, deployment or teaching-state work began.

## Reproduction and visual review

To review the exact build candidate, first require port 127.0.0.1:8510 to be free and the following evidence destination to be unused. Preserve any unrelated listener; do not terminate it, reuse an existing evidence directory or choose an arbitrary port. From C:/holographiclab, launch only this owned production child:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 .\runs\w3_refractive_routing_implementation_01\browser_helpers\production_child.py --manifest .\runs\w3_refractive_routing_implementation_01\build\source_asset_identity_07.json --evidence-dir C:\holographiclab\runs\w3_refractive_routing_implementation_01\manual_visual_review_01
```

Open http://127.0.0.1:8510, choose Geometric Routing and select W3. Use the approved A/B/C presets and explicit Trace. The child verifies the manifest/source and serves assets07 with assets-only injection; it does not add control endpoints or replace numerical workers. Stop the owned terminal with Ctrl+C when finished. Existing 8501 and unrelated services remain untouched. This reproduction command is documented here; preparing this handoff does not execute it.

For ordinary rebuilt default assets, README documents the existing installed-toolchain commands:

```powershell
Set-Location C:\holographiclab\frontend\bench
& 'C:\Program Files\nodejs\npm.cmd' run --ignore-scripts build
Set-Location C:\holographiclab
.\.venv\Scripts\python.exe -B -X utf8 -m apps.virtual_bench.server
```

These rebuild default production assets and are separate from reviewing the frozen assets07 evidence. They do not authorize installing dependencies or rebuilding the environment. See C:/holographiclab/README.md for the normal product workflow.

## Physical and numerical limitations

The supported model is direction-only ideal geometry with one exterior source and at most one closed homogeneous convex block or right-triangular prism, constant positive media and admitted exterior legacy elements. All finite side/end polygons participate; stored affine B uses inverse-transpose covectors and reciprocal-Gram UV, not assumed orthogonality or renderer triangles. Refraction changes medium only at a certified finite crossing; TIR retains medium and ideal bookkeeping weight. Immediate departure exclusion never blacklists the entire body or suppresses legitimate later returns.

Body-present limits are31 created branches,128 combined records,64 events,128 segments and32 interactions. Every queued terminal weight/medium is retained during truncation. No-body delegates exact public W2 behavior/caps63/256/128/256, original IDs, diagnostics and predicate policy. Domain radius is1m and supported path length10m. Body point/direction widths are fixed1e-8; nominal output norm tolerance is128epsilon. Critical/grazing/edge/vertex/order/medium ambiguity fails loudly; no clamp, normalization, epsilon displacement or uncertainty reset silently repairs it. Conservative intervals can reject plausible nominal scenes.

There is no Fresnel-power branching, dispersion, polarization transport, coherent wave phase, detector image formation, multiple-body engine, material database, GPU numerical solver, camera hardware or scene persistence. W1 fields are not projected onto folded refractive routes. Existing document v1/v2 and M5 contracts remain separate. Engineering media review does not establish the user's final visual acceptance or teaching completion.

The stage ends at an unstaged, uncommitted visual-review checkpoint after required evidence and task-owned cleanup. No later milestone, commit or push is implied.
