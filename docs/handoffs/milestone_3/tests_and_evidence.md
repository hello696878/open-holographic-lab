# Milestone 3 — Tests and evidence

Current implementation evidence, **2026-09-16**, from accepted baseline
`4dfa5c5032adbb627b74ec52ace0b435ac6dba5c`. Historical planning evidence is
identified separately below. Earlier handoffs and measurements are unchanged.

## Starting state and environment

Before implementation: clean `main`, upstream `origin/main`, ahead/behind
`0/0`; local HEAD and live `git ls-remote origin refs/heads/main` matched the
required baseline. The existing `C:\holographiclab\.venv\Scripts\python.exe`
was present. All 72 existing tracked file byte hashes were captured before
modifying existing files. No packages, environment or global Git settings were
changed. All commands below run from `C:\holographiclab`.

File-based tests use fresh dedicated ignored `.pytest_cache` basetemp paths
for the known Windows default-temp permission issue. These directories contain
only this task's test fixtures; no user data is removed.

## Baseline suite

Command, exit 0:

~~~powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --basetemp .pytest_cache/m3-implementation-baseline-20260916-a
~~~

Exact output:

~~~text
........................................................................ [ 14%]
........................................................................ [ 29%]
........................................................................ [ 43%]
........................................................................ [ 58%]
........................................................................ [ 73%]
........................................................................ [ 87%]
...........................................................              [100%]
491 passed in 4.73s
~~~

## Preserved planning fixtures and interpretation

The exploratory planning probe ran before M3 existed, using existing public
`ComplexField` projection methods and `propagate_angular_spectrum(...,
pad_factor=1)` at every step. Its elapsed times are historical probe timings,
not measurements of the shipped solver. The exact original script's SHA-256,
parameters and recorded endpoints are preserved below; the essential fixture
code is now committed in `scripts/probe_m3_evidence.py::planning_fixture` and
independently reproduced in `tests/test_gerchberg_saxton.py`.

The predeclared seeds are **0, 1, 2, 3**, each with **50 cycles**, wavelength
**633e-9 m**, distance **+5e-3 m**, and source-phase initialization uniform on
`[-pi,pi)` through `default_rng(seed)`. The complete target is constrained.

| Fixture | (ny, nx) | dy, dx [m] | Continuous design intensity |
|---|---|---|---|
| smooth_spot_64 | (64, 64) | 8e-6, 8e-6 | `exp(-0.5*((x/60e-6)**2+(y/60e-6)**2))` |
| two_features_64 | (64, 64) | 8e-6, 8e-6 | The two-Gaussian expression below |
| two_features_rect | (48, 64) | 10e-6, 8e-6 | The same two-Gaussian expression |

~~~python
0.65 * np.exp(-0.5 * (((x + 80e-6) / 32e-6)**2 + ((y + 48e-6) / 40e-6)**2)) \
+ 0.35 * np.exp(-0.5 * (((x - 72e-6) / 40e-6)**2 + ((y - 64e-6) / 28e-6)**2))
~~~

Coordinates follow the original centered grid. In every acceptance fixture,
`codes = rint(255*design).astype(uint8)`, M2 maps `I=codes/255`, then `A=sqrt(I)`.
Planning source amplitude is exactly `sqrt(mean(I))`, filling the complete grid.
The standalone demo separately uses the approved explicit formula
`sqrt(sum(A_target**2)/(nx*ny))`. Neither formula is hidden inside the solver.
Their evaluation-order difference is measured rather than silently conflated.

Every declared case must satisfy `rho_50 < 0.05` and `rho_50 < 0.1*rho_0`.
No fixture, seed, cycle count or threshold was selected again after observing
implementation results. Continuous prequantization designs are different
arrays, evaluated separately; they do not replace the quantized fixtures.

The full raw histories and final current runtime/memory data appear later.
A raw normalized squared amplitude residual is not percent accuracy, intensity
MSE, a pixel count or diffraction efficiency.


Original planning source SHA-256: `7e914ddd237e1fc151793f55e86ba1594a4b9fe2bf1365ca197d2dee3086f3e3`.

Historical planning endpoints (not shipped-solver measurements):

| Fixture | Seed | rho_0 | rho_50 | Probe elapsed [s] |
|---|---:|---:|---:|---:|
| smooth_spot_64 | 0 | 0.99105418117628941 | 0.017125299052456723 | 0.10725800000363961 |
| smooth_spot_64 | 1 | 0.99760288724375035 | 0.016694784541118089 | 0.086449399997945875 |
| smooth_spot_64 | 2 | 0.99962357682740388 | 0.014344758005132971 | 0.089806800009682775 |
| smooth_spot_64 | 3 | 1.0037224371986919 | 0.015919803568154665 | 0.087563999986741692 |
| two_features_64 | 0 | 1.2193654443597639 | 0.036116918721973909 | 0.082736500015016645 |
| two_features_64 | 1 | 1.205476068810247 | 0.036612380296920814 | 0.1064889999688603 |
| two_features_64 | 2 | 1.2125652885224496 | 0.038941522585850458 | 0.10389420000137761 |
| two_features_64 | 3 | 1.2105930187246314 | 0.034151650734589568 | 0.084645199996884912 |
| two_features_rect | 0 | 1.192628191648109 | 0.037651719668775438 | 0.055681099998764694 |
| two_features_rect | 1 | 1.1840781177155155 | 0.036637075285440794 | 0.058483799977693707 |
| two_features_rect | 2 | 1.1842858363557385 | 0.034672248336859009 | 0.053453600034117699 |
| two_features_rect | 3 | 1.1568588931942665 | 0.031786333196884356 | 0.065195300034247339 |

## Recovered fixture identity

Comparison against the original planning arrays, exact output:

~~~text
smooth_spot_64: planning codes, intensity, target amplitude and source amplitude recovered byte-for-byte
  codes SHA256=90e5ec20195346539a5676decda679d502402574b8239a1288a63b1273c2961b
  planning amplitude=2.93462716737912188e-01, demo amplitude=2.93462716737912188e-01, delta_ulps=0.0
two_features_64: planning codes, intensity, target amplitude and source amplitude recovered byte-for-byte
  codes SHA256=eba6dfe6c0d800d4393730ce25c2a3a1bab37e62a7439c4a7ac3cdc17f7a046e
  planning amplitude=1.71101758866631481e-01, demo amplitude=1.71101758866631481e-01, delta_ulps=0.0
two_features_rect: planning codes, intensity, target amplitude and source amplitude recovered byte-for-byte
  codes SHA256=6d8d455d12fa52f9d7012593e32287814041e537825e3c22d961e69089b987ae
  planning amplitude=1.76722527470852653e-01, demo amplitude=1.76722527470852653e-01, delta_ulps=0.0
~~~

## Independent reference measurements and tolerances

The complete-cycle reference uses scalar physical-coordinate sums, manual signed
frequency bins, scalar analytic H and independently implemented projections.
It never calls FFT or production H to form expected arrays. Both signs of
0.2 mm are tested on (3,5) and (5,8), at N=0,1,3. Four constructed feasible
fixed points start from their known phase and run four cycles; this does not
assert unique recovery from arbitrary phase. An on-grid plane wave supplies
an additional analytic complex-phase reference.

| Quantity | Largest measured error | Explicit rtol | Explicit atol |
|---|---:|---:|---:|
| Complete-cycle source / input peak | 2.3097588609057244e-15 | 1e-12 | 1e-13 * input peak |
| Complete-cycle reconstruction / input peak | 2.292370215650064e-15 | 1e-12 | 1e-13 * input peak |
| Complete-cycle normalized residual | 1.1796119636642288e-16 absolute | 1e-12 | 1e-14 |
| Constructed fixed-point amplitude | 2.7755575615628914e-16 absolute | 1e-12 | 1e-13 * input peak |
| Constructed fixed-point residual | 2.5449426724359463e-31 | 0 | 1e-26 |
| Analytic plane-wave residual | 7.106288447861476e-32 | 0 | 1e-26 |
| Prescribed source amplitude, twelve fixtures | 3.783182534961273e-16 relative | 5e-15 | 0 |
| Source power, twelve fixtures | 4.311332007509935e-16 relative | 5e-15 | 0 |
| Reconstruction power, twelve fixtures | 6.466998011264903e-16 relative | 5e-15 | 0 |

Field absolute bounds use prescribed input scale, never a possibly corrupted
output. They accommodate cancellation near zero and accumulated FFT/scalar-sum
roundoff with margin, not physical-model error. Source projection/power uses
tighter bounds because the measured errors are only a few float64 epsilons.
The fixed-point residual is a squared roundoff error, explaining its smaller
absolute bound. These are measured finite-case tolerances, not exhaustive bounds
for every grid. The separate input power-compatibility threshold remains
1e-12 relative with absolute zero.

For reproducibility, copy the following driver verbatim to the ignored
`runs/m3/reference_probe.py` (create the directory if needed), then run:

~~~powershell
.\.venv\Scripts\python.exe -B runs\m3\reference_probe.py
~~~

Exact driver:

~~~python
"""Shipped M3 reference measurements; run from repository root with python -B.

The independent reference functions and exact fixtures are committed in the
two M3 test modules. This driver reports errors without changing tolerances.
Its exact source and output are preserved in the milestone evidence handoff.
"""
from pathlib import Path
import cmath
import json
import math
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from test_gerchberg_saxton_reference import (
    _direct_propagation, _problem, _project_reference, _residual_reference,
)
from test_gerchberg_saxton import PREDECLARED_CASES, _predeclared_problem
from ohlab import SamplingGrid
from ohlab.algorithms import gerchberg_saxton

LAM = 633e-9
records = []

def error_record(kind, shape, distance, source, actual, expected_source,
                 expected_reconstruction, expected_history, **extras):
    peak = float(source.max())
    record = dict(
        kind=kind, shape=shape, distance_m=distance, input_peak=peak,
        source_maxabs_over_input_peak=float(np.max(np.abs(actual.source_field.data - expected_source)) / peak),
        reconstruction_maxabs_over_input_peak=float(np.max(np.abs(actual.reconstruction.data - expected_reconstruction)) / peak),
        history_maxabs=float(np.max(np.abs(actual.residual_history - expected_history))),
        source_amplitude_max_relative=float(np.max(np.abs(actual.source_field.amplitude - source) / source)),
        **extras,
    )
    records.append(record)
    print(json.dumps(record, sort_keys=True))

for shape in ((3, 5), (5, 8)):
    for distance in (2e-4, -2e-4):
        for cycles in (0, 1, 3):
            grid, source, target, phase, expected_source = _problem(shape)
            expected_history = []
            for k in range(cycles + 1):
                expected_reconstruction = _direct_propagation(expected_source, grid, distance)
                expected_history.append(_residual_reference(expected_reconstruction, target))
                if k < cycles:
                    expected_source = _project_reference(
                        _direct_propagation(_project_reference(expected_reconstruction, target), grid, -distance),
                        source,
                    )
            actual = gerchberg_saxton(target_amplitude=target, source_amplitude=source,
                grid=grid, wavelength_m=LAM, distance_m=distance,
                iterations=cycles, initial_phase=phase)
            error_record("direct_complete_cycles", shape, distance, source, actual,
                expected_source, expected_reconstruction, expected_history, iterations=cycles)

        grid, source, _, phase, expected_source = _problem(shape)
        expected_reconstruction = _direct_propagation(expected_source, grid, distance)
        target = np.array([abs(complex(v)) for v in expected_reconstruction.flat], dtype=np.float64).reshape(shape)
        actual = gerchberg_saxton(target_amplitude=target, source_amplitude=source,
            grid=grid, wavelength_m=LAM, distance_m=distance, iterations=4, initial_phase=phase)
        error_record("direct_constructed_fixed_point", shape, distance, source, actual,
            expected_source, expected_reconstruction, np.zeros(5),
            amplitude_maxabs=float(np.max(np.abs(actual.reconstruction.amplitude - target))))

grid = SamplingGrid(ny=5, nx=8, dy=10e-6, dx=8e-6)
x, y = grid.meshgrid()
fx, fy = 2 / grid.extent_x, -1 / grid.extent_y
phase = 2 * np.pi * (fx * x + fy * y) + 0.3
source = np.full(grid.shape, 0.7, dtype=np.float64)
distance = 2e-4
kz = 2 * math.pi * math.sqrt((1 / LAM)**2 - fx**2 - fy**2)
expected_source = source * np.exp(1j * phase)
expected_reconstruction = expected_source * cmath.exp(1j * kz * distance)
actual = gerchberg_saxton(target_amplitude=source, source_amplitude=source, grid=grid,
    wavelength_m=LAM, distance_m=distance, iterations=3, initial_phase=phase)
error_record("analytic_plane_wave", grid.shape, distance, source, actual,
    expected_source, expected_reconstruction, np.zeros(4))

for case in PREDECLARED_CASES:
    name, grid, codes, intensity, target, source = _predeclared_problem(case)
    power = math.fsum(float(v)**2 for v in source.flat) * grid.pixel_area
    for seed in (0, 1, 2, 3):
        actual = gerchberg_saxton(target_amplitude=target, source_amplitude=source,
            grid=grid, wavelength_m=LAM, distance_m=5e-3, iterations=50, seed=seed)
        record = dict(kind="predeclared_projection_precision", fixture=name, seed=seed,
            source_amplitude_max_relative=float(np.max(np.abs(actual.source_field.amplitude-source)/source)),
            source_power_relative=abs(actual.source_field.power-power)/power,
            reconstruction_power_relative=abs(actual.reconstruction.power-power)/power,
            initial_residual=float(actual.residual_history[0]), final_residual=float(actual.residual_history[-1]))
        records.append(record)
        print(json.dumps(record, sort_keys=True))

print("MAXIMA " + json.dumps({key: max(r[key] for r in records if key in r) for key in (
    "source_maxabs_over_input_peak", "reconstruction_maxabs_over_input_peak",
    "history_maxabs", "source_amplitude_max_relative", "source_power_relative",
    "reconstruction_power_relative", "amplitude_maxabs")}, sort_keys=True))
~~~

Exact measurement output (exit 0):

~~~text
{"distance_m": 0.0002, "history_maxabs": 5.551115123125783e-17, "input_peak": 0.3, "iterations": 0, "kind": "direct_complete_cycles", "reconstruction_maxabs_over_input_peak": 1.0952443179748476e-15, "shape": [3, 5], "source_amplitude_max_relative": 1.8503717077085943e-16, "source_maxabs_over_input_peak": 0.0}
{"distance_m": 0.0002, "history_maxabs": 5.551115123125783e-17, "input_peak": 0.3, "iterations": 1, "kind": "direct_complete_cycles", "reconstruction_maxabs_over_input_peak": 6.386853722596775e-16, "shape": [3, 5], "source_amplitude_max_relative": 2.1350442781253008e-16, "source_maxabs_over_input_peak": 3.9252311467094383e-16}
{"distance_m": 0.0002, "history_maxabs": 5.551115123125783e-17, "input_peak": 0.3, "iterations": 3, "kind": "direct_complete_cycles", "reconstruction_maxabs_over_input_peak": 9.609943586518524e-16, "shape": [3, 5], "source_amplitude_max_relative": 2.220446049250313e-16, "source_maxabs_over_input_peak": 7.459086818853016e-16}
{"amplitude_maxabs": 2.220446049250313e-16, "distance_m": 0.0002, "history_maxabs": 2.5449426724359463e-31, "input_peak": 0.3, "kind": "direct_constructed_fixed_point", "reconstruction_maxabs_over_input_peak": 9.435081445006127e-16, "shape": [3, 5], "source_amplitude_max_relative": 1.8503717077085943e-16, "source_maxabs_over_input_peak": 1.0467283057891834e-15}
{"distance_m": -0.0002, "history_maxabs": 2.7755575615628914e-17, "input_peak": 0.3, "iterations": 0, "kind": "direct_complete_cycles", "reconstruction_maxabs_over_input_peak": 6.73545468406711e-16, "shape": [3, 5], "source_amplitude_max_relative": 1.8503717077085943e-16, "source_maxabs_over_input_peak": 0.0}
{"distance_m": -0.0002, "history_maxabs": 2.7755575615628914e-17, "input_peak": 0.3, "iterations": 1, "kind": "direct_complete_cycles", "reconstruction_maxabs_over_input_peak": 6.542051911182396e-16, "shape": [3, 5], "source_amplitude_max_relative": 2.1350442781253008e-16, "source_maxabs_over_input_peak": 5.394714207615781e-16}
{"distance_m": -0.0002, "history_maxabs": 4.163336342344337e-17, "input_peak": 0.3, "iterations": 3, "kind": "direct_complete_cycles", "reconstruction_maxabs_over_input_peak": 1.1188630228279524e-15, "shape": [3, 5], "source_amplitude_max_relative": 2.05596856412066e-16, "source_maxabs_over_input_peak": 8.691332018924847e-16}
{"amplitude_maxabs": 1.6653345369377348e-16, "distance_m": -0.0002, "history_maxabs": 1.3940450307610916e-31, "input_peak": 0.3, "kind": "direct_constructed_fixed_point", "reconstruction_maxabs_over_input_peak": 1.3753876507444552e-15, "shape": [3, 5], "source_amplitude_max_relative": 1.8503717077085943e-16, "source_maxabs_over_input_peak": 1.3877787807814457e-15}
{"distance_m": 0.0002, "history_maxabs": 5.551115123125783e-17, "input_peak": 0.38, "iterations": 0, "kind": "direct_complete_cycles", "reconstruction_maxabs_over_input_peak": 5.704683564646536e-16, "shape": [5, 8], "source_amplitude_max_relative": 1.914177628664063e-16, "source_maxabs_over_input_peak": 0.0}
{"distance_m": 0.0002, "history_maxabs": 1.1796119636642288e-16, "input_peak": 0.38, "iterations": 1, "kind": "direct_complete_cycles", "reconstruction_maxabs_over_input_peak": 1.8948471112449627e-15, "shape": [5, 8], "source_amplitude_max_relative": 2.05596856412066e-16, "source_maxabs_over_input_peak": 1.7411507091464966e-15}
{"distance_m": 0.0002, "history_maxabs": 1.1796119636642288e-16, "input_peak": 0.38, "iterations": 3, "kind": "direct_complete_cycles", "reconstruction_maxabs_over_input_peak": 2.292370215650064e-15, "shape": [5, 8], "source_amplitude_max_relative": 2.1350442781253008e-16, "source_maxabs_over_input_peak": 2.3097588609057244e-15}
{"amplitude_maxabs": 2.7755575615628914e-16, "distance_m": 0.0002, "history_maxabs": 1.4734255708795858e-31, "input_peak": 0.38, "kind": "direct_constructed_fixed_point", "reconstruction_maxabs_over_input_peak": 8.795299706958336e-16, "shape": [5, 8], "source_amplitude_max_relative": 2.1350442781253008e-16, "source_maxabs_over_input_peak": 6.734046403316979e-16}
{"distance_m": -0.0002, "history_maxabs": 6.938893903907228e-17, "input_peak": 0.38, "iterations": 0, "kind": "direct_complete_cycles", "reconstruction_maxabs_over_input_peak": 6.532984613808613e-16, "shape": [5, 8], "source_amplitude_max_relative": 1.914177628664063e-16, "source_maxabs_over_input_peak": 0.0}
{"distance_m": -0.0002, "history_maxabs": 6.938893903907228e-17, "input_peak": 0.38, "iterations": 1, "kind": "direct_complete_cycles", "reconstruction_maxabs_over_input_peak": 1.0069661244430707e-15, "shape": [5, 8], "source_amplitude_max_relative": 2.1350442781253008e-16, "source_maxabs_over_input_peak": 7.900590873329056e-16}
{"distance_m": -0.0002, "history_maxabs": 6.938893903907228e-17, "input_peak": 0.38, "iterations": 3, "kind": "direct_complete_cycles", "reconstruction_maxabs_over_input_peak": 2.0684919067806554e-15, "shape": [5, 8], "source_amplitude_max_relative": 2.05596856412066e-16, "source_maxabs_over_input_peak": 1.9458575832503e-15}
{"amplitude_maxabs": 1.6653345369377348e-16, "distance_m": -0.0002, "history_maxabs": 1.1970189584906773e-31, "input_peak": 0.38, "kind": "direct_constructed_fixed_point", "reconstruction_maxabs_over_input_peak": 8.009569688583678e-16, "shape": [5, 8], "source_amplitude_max_relative": 2.1350442781253008e-16, "source_maxabs_over_input_peak": 8.705753545732483e-16}
{"distance_m": 0.0002, "history_maxabs": 7.106288447861476e-32, "input_peak": 0.7, "kind": "analytic_plane_wave", "reconstruction_maxabs_over_input_peak": 1.2983752430364539e-15, "shape": [5, 8], "source_amplitude_max_relative": 1.5860328923216522e-16, "source_maxabs_over_input_peak": 1.1435783884965158e-15}
{"final_residual": 0.017125299052456723, "fixture": "smooth_spot_64", "initial_residual": 0.9910541811762894, "kind": "predeclared_projection_precision", "reconstruction_power_relative": 2.931193875012813e-16, "seed": 0, "source_amplitude_max_relative": 1.8915912674806364e-16, "source_power_relative": 1.4655969375064064e-16}
{"final_residual": 0.01669478454111809, "fixture": "smooth_spot_64", "initial_residual": 0.9976028872437503, "kind": "predeclared_projection_precision", "reconstruction_power_relative": 1.4655969375064064e-16, "seed": 1, "source_amplitude_max_relative": 3.783182534961273e-16, "source_power_relative": 1.4655969375064064e-16}
{"final_residual": 0.014344758005132971, "fixture": "smooth_spot_64", "initial_residual": 0.9996235768274039, "kind": "predeclared_projection_precision", "reconstruction_power_relative": 1.4655969375064064e-16, "seed": 2, "source_amplitude_max_relative": 1.8915912674806364e-16, "source_power_relative": 1.4655969375064064e-16}
{"final_residual": 0.015919803568154665, "fixture": "smooth_spot_64", "initial_residual": 1.003722437198692, "kind": "predeclared_projection_precision", "reconstruction_power_relative": 1.4655969375064064e-16, "seed": 3, "source_amplitude_max_relative": 1.8915912674806364e-16, "source_power_relative": 1.4655969375064064e-16}
{"final_residual": 0.03611691872197391, "fixture": "two_features_64", "initial_residual": 1.219365444359764, "kind": "predeclared_projection_precision", "reconstruction_power_relative": 6.466998011264903e-16, "seed": 0, "source_amplitude_max_relative": 3.2443355111578397e-16, "source_power_relative": 4.311332007509935e-16}
{"final_residual": 0.036612380296920814, "fixture": "two_features_64", "initial_residual": 1.205476068810247, "kind": "predeclared_projection_precision", "reconstruction_power_relative": 4.311332007509935e-16, "seed": 1, "source_amplitude_max_relative": 3.2443355111578397e-16, "source_power_relative": 4.311332007509935e-16}
{"final_residual": 0.03894152258585046, "fixture": "two_features_64", "initial_residual": 1.2125652885224496, "kind": "predeclared_projection_precision", "reconstruction_power_relative": 4.311332007509935e-16, "seed": 2, "source_amplitude_max_relative": 3.2443355111578397e-16, "source_power_relative": 4.311332007509935e-16}
{"final_residual": 0.03415165073458957, "fixture": "two_features_64", "initial_residual": 1.2105930187246314, "kind": "predeclared_projection_precision", "reconstruction_power_relative": 4.311332007509935e-16, "seed": 3, "source_amplitude_max_relative": 3.2443355111578397e-16, "source_power_relative": 4.311332007509935e-16}
{"final_residual": 0.03765171966877544, "fixture": "two_features_rect", "initial_residual": 1.192628191648109, "kind": "predeclared_projection_precision", "reconstruction_power_relative": 0.0, "seed": 0, "source_amplitude_max_relative": 3.1411474261770867e-16, "source_power_relative": 0.0}
{"final_residual": 0.036637075285440794, "fixture": "two_features_rect", "initial_residual": 1.1840781177155155, "kind": "predeclared_projection_precision", "reconstruction_power_relative": 0.0, "seed": 1, "source_amplitude_max_relative": 3.1411474261770867e-16, "source_power_relative": 0.0}
{"final_residual": 0.03467224833685901, "fixture": "two_features_rect", "initial_residual": 1.1842858363557385, "kind": "predeclared_projection_precision", "reconstruction_power_relative": 0.0, "seed": 2, "source_amplitude_max_relative": 3.1411474261770867e-16, "source_power_relative": 0.0}
{"final_residual": 0.031786333196884356, "fixture": "two_features_rect", "initial_residual": 1.1568588931942665, "kind": "predeclared_projection_precision", "reconstruction_power_relative": 0.0, "seed": 3, "source_amplitude_max_relative": 3.1411474261770867e-16, "source_power_relative": 0.0}
MAXIMA {"amplitude_maxabs": 2.7755575615628914e-16, "history_maxabs": 1.1796119636642288e-16, "reconstruction_maxabs_over_input_peak": 2.292370215650064e-15, "reconstruction_power_relative": 6.466998011264903e-16, "source_amplitude_max_relative": 3.783182534961273e-16, "source_maxabs_over_input_peak": 2.3097588609057244e-15, "source_power_relative": 4.311332007509935e-16}
~~~

## Floating-point grazing-cutoff discovery and regression

Review found a concrete domain corner in which the summed frequency comparison
passes but the public transfer formula
`(1/lambda)**2 - fx**2 - fy**2` is slightly negative after sequential float64
subtraction. At z=1 mm the first reproducer has minimum public |H|
0.9999652905794315, violating the selected lossless M3 model. The M3-only guard
rejects this unusable geometry before public H construction, including N=0
and z=0. It does not compute another kz/H, clamp radicands, or alter M1.
Six regression cases cover the first rounded-cutoff grid; three exact-grazing
cases separately preserve acceptance of representable grazing zero.

Copy this driver to ignored `runs/m3/grazing_cutoff_probe.py` and run:

~~~powershell
.\.venv\Scripts\python.exe -B runs\m3\grazing_cutoff_probe.py
~~~

Exact driver:

~~~python
"""Reproduce the rounded grazing-cutoff M3 domain guard; no source mutation."""
import json
import numpy as np
from ohlab.grid import SamplingGrid
from ohlab.propagation import angular_spectrum_transfer_function
from ohlab.algorithms import gerchberg_saxton

for dx, dy, wavelength in [
    (1e-6, 1.3e-6, 1.5852479782092003e-6),
    (3.74e-6, 1.9e-5, 7.339166584063931e-6),
]:
    grid = SamplingGrid(ny=4, nx=6, dx=dx, dy=dy)
    fx, fy = grid.freq_meshgrid(order="fft")
    cutoff = (1.0 / wavelength) ** 2
    radicand = cutoff - fx**2 - fy**2
    transfer = angular_spectrum_transfer_function(
        grid, wavelength_m=wavelength, distance_m=0.001
    )
    print(json.dumps({
        "shape": grid.shape, "dx_m": dx, "dy_m": dy,
        "wavelength_m": wavelength,
        "sum_predicate_evanescent_count": int(np.count_nonzero(fx**2 + fy**2 > cutoff)),
        "negative_sequential_radicands": int(np.count_nonzero(radicand < 0.0)),
        "minimum_sequential_radicand_m_minus_2": float(np.min(radicand)),
        "minimum_abs_public_H_at_1mm": float(np.min(np.abs(transfer))),
    }, sort_keys=True))
    amplitude = np.ones(grid.shape, dtype=np.float64)
    for distance in (-0.001, 0.0, 0.001):
        for iterations in (0, 1):
            try:
                gerchberg_saxton(
                    target_amplitude=amplitude, source_amplitude=amplitude,
                    grid=grid, wavelength_m=wavelength, distance_m=distance,
                    iterations=iterations, seed=0,
                )
            except ValueError as error:
                assert "floating-point cutoff geometry" in str(error), str(error)
                print(f"z={distance!r}, N={iterations}: ValueError: {error}")
            else:
                raise AssertionError("Expected lossless cutoff-domain rejection")

~~~

Exact output, exit 0 (the caught ValueErrors are the intended domain result):

~~~text
{"dx_m": 1e-06, "dy_m": 1.3e-06, "minimum_abs_public_H_at_1mm": 0.9999652905794315, "minimum_sequential_radicand_m_minus_2": -3.0517578125e-05, "negative_sequential_radicands": 1, "shape": [4, 6], "sum_predicate_evanescent_count": 0, "wavelength_m": 1.5852479782092003e-06}
z=-0.001, N=0: ValueError: floating-point cutoff geometry cannot represent the lossless GS domain: 1 of 24 public transfer radicands are negative (minimum -3.0517578125e-05); this is unsupported even at zero distance or zero iterations
z=-0.001, N=1: ValueError: floating-point cutoff geometry cannot represent the lossless GS domain: 1 of 24 public transfer radicands are negative (minimum -3.0517578125e-05); this is unsupported even at zero distance or zero iterations
z=0.0, N=0: ValueError: floating-point cutoff geometry cannot represent the lossless GS domain: 1 of 24 public transfer radicands are negative (minimum -3.0517578125e-05); this is unsupported even at zero distance or zero iterations
z=0.0, N=1: ValueError: floating-point cutoff geometry cannot represent the lossless GS domain: 1 of 24 public transfer radicands are negative (minimum -3.0517578125e-05); this is unsupported even at zero distance or zero iterations
z=0.001, N=0: ValueError: floating-point cutoff geometry cannot represent the lossless GS domain: 1 of 24 public transfer radicands are negative (minimum -3.0517578125e-05); this is unsupported even at zero distance or zero iterations
z=0.001, N=1: ValueError: floating-point cutoff geometry cannot represent the lossless GS domain: 1 of 24 public transfer radicands are negative (minimum -3.0517578125e-05); this is unsupported even at zero distance or zero iterations
{"dx_m": 3.74e-06, "dy_m": 1.9e-05, "minimum_abs_public_H_at_1mm": 0.9999951491385888, "minimum_sequential_radicand_m_minus_2": -5.960464477539062e-07, "negative_sequential_radicands": 1, "shape": [4, 6], "sum_predicate_evanescent_count": 0, "wavelength_m": 7.339166584063931e-06}
z=-0.001, N=0: ValueError: floating-point cutoff geometry cannot represent the lossless GS domain: 1 of 24 public transfer radicands are negative (minimum -5.960464477539062e-07); this is unsupported even at zero distance or zero iterations
z=-0.001, N=1: ValueError: floating-point cutoff geometry cannot represent the lossless GS domain: 1 of 24 public transfer radicands are negative (minimum -5.960464477539062e-07); this is unsupported even at zero distance or zero iterations
z=0.0, N=0: ValueError: floating-point cutoff geometry cannot represent the lossless GS domain: 1 of 24 public transfer radicands are negative (minimum -5.960464477539062e-07); this is unsupported even at zero distance or zero iterations
z=0.0, N=1: ValueError: floating-point cutoff geometry cannot represent the lossless GS domain: 1 of 24 public transfer radicands are negative (minimum -5.960464477539062e-07); this is unsupported even at zero distance or zero iterations
z=0.001, N=0: ValueError: floating-point cutoff geometry cannot represent the lossless GS domain: 1 of 24 public transfer radicands are negative (minimum -5.960464477539062e-07); this is unsupported even at zero distance or zero iterations
z=0.001, N=1: ValueError: floating-point cutoff geometry cannot represent the lossless GS domain: 1 of 24 public transfer radicands are negative (minimum -5.960464477539062e-07); this is unsupported even at zero distance or zero iterations
~~~

## Seven isolated mutations across six required categories

Each mutation existed only in a fresh subprocess. The driver required pytest
exit 1, assertion failures during test calls, and no collection/setup/teardown
failures. All 27 source/test file hashes matched before and after each child.
Process exit discarded the in-memory replacement; no source restoration from
a backup was needed. The subsequent normal full suite below ran the actual
unmodified implementation. These controls demonstrate finite detection, not
zero possible test gaps.

| Mutation | Assertion exercised | Observed result |
|---|---|---|
| Omit source projection (`current=returned`) | Nonuniform prescribed source amplitude | 1 failed |
| Omit target projection | Independent complete-cycle complex field/history | 8 failed, 4 N=0 passed |
| Use forward H for the backward leg | Signed-distance independent complete-cycle reference | 8 failed, 4 N=0 passed |
| Use target amplitude squared in target projection | Nonbinary independent complex reference | 8 failed, 4 N=0 passed |
| Return target-projected reconstruction | Rebuild returned phase and propagate by public ASM | 9 failed |
| Evaluate residual after target replacement | Independently recomputed actual residual | 9 failed |
| Add 0.2 rad to returned phase | Rebuilt source/reconstruction consistency | 9 failed |

There are 52 assertion failures across seven deliberately broken runs. The
projected-field and post-projection-loss mutations separately exercise one
required category. All seven verification-driver children returned zero
because the intended test failures were observed.

Copy the following exact driver to ignored `runs/m3/negative_controls.py`,
then run from the repository root:

~~~powershell
.\.venv\Scripts\python.exe -B runs\m3\negative_controls.py --all
~~~

Exact driver:

~~~python
"""Isolated in-memory M3 mutations; no project source/test files are changed.

Each invocation is a fresh python -B process. All expected failures must be
assertion failures during test calls, never collection/setup/teardown errors.
The exact driver and unedited transcript are copied into the M3 handoff.
"""
from pathlib import Path
import hashlib
import importlib
import inspect
import json
import subprocess
import sys
import textwrap
import uuid

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = importlib.import_module("ohlab.algorithms")
MODULE = importlib.import_module("ohlab.algorithms.gerchberg_saxton")
CASES = {
    "missing_source_projection": (
        "current = _project_amplitude(returned, source)", "current = returned", 1,
        "tests/test_gerchberg_saxton.py::test_gs_result_and_prescribed_nonuniform_amplitude"),
    "missing_target_projection": (
        "constrained = _project_amplitude(reconstruction, target)", "constrained = reconstruction", 1,
        "tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft"),
    "wrong_backward_direction": (
        "returned = _apply_transfer(constrained, backward, identity=identity)",
        "returned = _apply_transfer(constrained, forward, identity=identity)", 1,
        "tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft"),
    "amplitude_treated_as_intensity": (
        "constrained = _project_amplitude(reconstruction, target)",
        "constrained = _project_amplitude(reconstruction, target**2)", 1,
        "tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft"),
    "target_projected_reconstruction": (
        "reconstruction=ComplexField(data=reconstruction, grid=grid, wavelength_m=wavelength)",
        "reconstruction=ComplexField(data=_project_amplitude(reconstruction, target), grid=grid, wavelength_m=wavelength)", 1,
        "tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss"),
    "post_projection_loss": (
        "_amplitude_residual(reconstruction, target, target_energy)",
        "_amplitude_residual(_project_amplitude(reconstruction, target), target, target_energy)", 2,
        "tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss"),
    "inconsistent_returned_phase": (
        "return _phase_with_zero_tie(self.source_field.data)",
        "return _phase_with_zero_tie(self.source_field.data) + 0.2", 1,
        "tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss"),
}

def inventory():
    paths = sorted((ROOT / "src" / "ohlab").rglob("*.py")) + sorted((ROOT / "tests").rglob("*.py"))
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}

if sys.argv[1:] == ["--all"]:
    transcript = bytearray()
    def emit(data):
        encoded = data.encode("utf-8") if isinstance(data, str) else data
        transcript.extend(encoded)
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--all"]
    emit("PARENT COMMAND " + subprocess.list2cmdline(command) + "\n")
    successful = True
    for name in CASES:
        command = [sys.executable, "-B", str(Path(__file__).resolve()), name]
        emit("COMMAND " + subprocess.list2cmdline(command) + "\n")
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, check=False)
        emit(completed.stdout)
        emit(completed.stderr)
        emit(f"DRIVER CHILD EXIT: {completed.returncode}\n")
        successful = successful and completed.returncode == 0
    emit(f"ALL SEVEN MUTATIONS VERIFIED: {successful}\n")
    (ROOT / "runs" / "m3" / "negative_controls_output.txt").write_bytes(transcript)
    raise SystemExit(0 if successful else 1)

case = sys.argv[1]
old, new, occurrences, selector = CASES[case]
before = inventory()
if case == "inconsistent_returned_phase":
    source = textwrap.dedent(inspect.getsource(MODULE.GerchbergSaxtonResult.phase.fget))
    assert source.count(old) == occurrences
    namespace = dict(MODULE.__dict__)
    exec(compile(source.replace(old, new), "<isolated M3 phase mutation>", "exec"), namespace)
    # inspect.getsource includes @property, so this is the replacement descriptor.
    MODULE.GerchbergSaxtonResult.phase = namespace["phase"]
else:
    source = inspect.getsource(MODULE.gerchberg_saxton)
    assert source.count(old) == occurrences
    exec(compile(source.replace(old, new), "<isolated M3 solver mutation>", "exec"), MODULE.__dict__)
    PACKAGE.gerchberg_saxton = MODULE.gerchberg_saxton

class Reports:
    def __init__(self):
        self.call_failures = []
        self.other_failures = []
    def pytest_runtest_logreport(self, report):
        if report.failed:
            (self.call_failures if report.when == "call" else self.other_failures).append(report)
    def pytest_collectreport(self, report):
        if report.failed:
            self.other_failures.append(report)

reports = Reports()
temporary = ROOT / "runs" / "m3" / ("negative-pytest-" + case + "-" + uuid.uuid4().hex)
arguments = ["-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", str(temporary), selector]
print("CASE " + case)
print("MUTATION " + repr(old) + " -> " + repr(new))
print("PYTEST ARGS " + json.dumps(arguments))
exit_code = int(pytest.main(arguments, plugins=[reports]))
unchanged = inventory() == before
assertion_failures = all("AssertionError" in str(report.longrepr) for report in reports.call_failures)
verified = exit_code == 1 and bool(reports.call_failures) and not reports.other_failures and assertion_failures and unchanged
print(f"NEGATIVE CONTROL VERIFIED: {verified}; pytest exit={exit_code}; assertion call failures={len(reports.call_failures)}; other failures={len(reports.other_failures)}")
print(f"SOURCE/TEST HASHES UNCHANGED: {unchanged}; files={len(before)}")
raise SystemExit(0 if verified else 1)
~~~

Complete unedited transcript (including original whitespace in pytest errors):

~~~text
PARENT COMMAND C:\holographiclab\.venv\Scripts\python.exe -B C:\holographiclab\runs\m3\negative_controls.py --all
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B C:\holographiclab\runs\m3\negative_controls.py missing_source_projection
CASE missing_source_projection
MUTATION 'current = _project_amplitude(returned, source)' -> 'current = returned'
PYTEST ARGS ["-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", "C:\\holographiclab\\runs\\m3\\negative-pytest-missing_source_projection-e320d91d88644edf95f25b715fcb753e", "tests/test_gerchberg_saxton.py::test_gs_result_and_prescribed_nonuniform_amplitude"]
F                                                                        [100%]
================================== FAILURES ===================================
E   AssertionError: 
    Not equal to tolerance rtol=5e-15, atol=0
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: 0.29122450727262655 (ACTUAL), 0.2 (DESIRED)
     [0, 1]: 0.35408153896244166 (ACTUAL), 0.25 (DESIRED)
     [0, 2]: 0.36595864631140285 (ACTUAL), 0.30000000000000004 (DESIRED)
     [0, 3]: 0.3872580675183342 (ACTUAL), 0.35 (DESIRED)
     [0, 4]: 0.46383052322324125 (ACTUAL), 0.4 (DESIRED)
    Max absolute difference among violations: 0.37116317
    Max relative difference among violations: 0.51877835
     ACTUAL: array([[0.291225, 0.354082, 0.365959, 0.387258, 0.463831],
           [0.549732, 0.471967, 0.584741, 0.288733, 0.753409],
           [0.979702, 0.798129, 0.844484, 0.648661, 0.528837]])
     DESIRED: array([[0.2 , 0.25, 0.3 , 0.35, 0.4 ],
           [0.45, 0.5 , 0.55, 0.6 , 0.65],
           [0.7 , 0.75, 0.8 , 0.85, 0.9 ]])
C:\holographiclab\tests\test_gerchberg_saxton.py:75: AssertionError:
=========================== short test summary info ===========================
FAILED tests/test_gerchberg_saxton.py::test_gs_result_and_prescribed_nonuniform_amplitude
1 failed in 0.13s
NEGATIVE CONTROL VERIFIED: True; pytest exit=1; assertion call failures=1; other failures=0
SOURCE/TEST HASHES UNCHANGED: True; files=27
DRIVER CHILD EXIT: 0
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B C:\holographiclab\runs\m3\negative_controls.py missing_target_projection
CASE missing_target_projection
MUTATION 'constrained = _project_amplitude(reconstruction, target)' -> 'constrained = reconstruction'
PYTEST ARGS ["-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", "C:\\holographiclab\\runs\\m3\\negative-pytest-missing_target_projection-f79055f22bfa447d8381b17ae6ecb5bd", "tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft"]
....FFFFFFFF                                                             [100%]
================================== FAILURES ===================================
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.17551651237807456+0.0958851077208406j) (ACTUAL), (0.19095430775074929+0.059468078423908534j) (DESIRED)
     [0, 1]: (0.06710265761546878+0.20951666602192096j) (ACTUAL), (0.0337421701065892+0.21739702379862058j) (DESIRED)
     [0, 2]: (0.1356267062424218+0.19800352661968385j) (ACTUAL), (0.16105052083760607+0.1779402420419165j) (DESIRED)
     [0, 3]: (0.25988478171519847+0.007739524070875168j) (ACTUAL), (0.2584027005343457-0.028775759878016366j) (DESIRED)
     [0, 4]: (0.2705282566390104-0.07221123430504234j) (ACTUAL), (0.2778098682772297-0.03495249759013376j) (DESIRED)
    Max absolute difference among violations: 0.12441731
    Max relative difference among violations: 0.41472435
     ACTUAL: array([[0.175517+9.588511e-02j, 0.067103+2.095167e-01j,
            0.135627+1.980035e-01j, 0.259885+7.739524e-03j,
            0.270528-7.221123e-02j],...
     DESIRED: array([[0.190954+0.059468j, 0.033742+0.217397j, 0.161051+0.17794j ,
            0.258403-0.028776j, 0.27781 -0.034952j],
           [0.209927-0.005535j, 0.184245+0.137672j, 0.242389+0.061219j,...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3.8e-14
    
    Mismatched elements: 40 / 40 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.17551651237807453+0.09588510772084063j) (ACTUAL), (0.18438453763566176+0.07747478480695019j) (DESIRED)
     [0, 1]: (0.10645898907886468+0.19252657905937604j) (ACTUAL), (0.054814232211907635+0.2130619626939991j) (DESIRED)
     [0, 2]: (0.06419971886990097+0.23125396450012634j) (ACTUAL), (0.07482688450281882+0.22803714029868427j) (DESIRED)
     [0, 3]: (0.12581516891138553+0.22753141161562623j) (ACTUAL), (0.13015886285192305+0.2250748107210007j) (DESIRED)
     [0, 4]: (0.2457231173293044+0.13423915080917684j) (ACTUAL), (0.22494764069786996+0.16672899851094294j) (DESIRED)
    Max absolute difference among violations: 0.17623059
    Max relative difference among violations: 0.52750191
     ACTUAL: array([[ 0.175517+0.095885j,  0.106459+0.192527j,  0.0642  +0.231254j,
             0.125815+0.227531j,  0.245723+0.134239j,  0.299353-0.019691j,
             0.305708-0.094566j,  0.339267-0.022317j],...
     DESIRED: array([[ 0.184385+0.077475j,  0.054814+0.213062j,  0.074827+0.228037j,
             0.130159+0.225075j,  0.224948+0.166729j,  0.299858-0.009238j,
             0.287647-0.140212j,  0.337784-0.038757j],...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.17551651237807456+0.09588510772084058j) (ACTUAL), (0.18638766014406047+0.07252337654868406j) (DESIRED)
     [0, 1]: (0.06710265761546878+0.20951666602192096j) (ACTUAL), (0.11653037705750312+0.1866029775293957j) (DESIRED)
     [0, 2]: (0.13562670624242176+0.19800352661968385j) (ACTUAL), (0.11442475353783108+0.2109667646284756j) (DESIRED)
     [0, 3]: (0.25988478171519847+0.0077395240708751645j) (ACTUAL), (0.2594165909505394+0.017407824091496882j) (DESIRED)
     [0, 4]: (0.2705282566390104-0.0722112343050424j) (ACTUAL), (0.2708333700842483-0.071058325682559j) (DESIRED)
    Max absolute difference among violations: 0.05448061
    Max relative difference among violations: 0.24763912
     ACTUAL: array([[0.175517+9.588511e-02j, 0.067103+2.095167e-01j,
            0.135627+1.980035e-01j, 0.259885+7.739524e-03j,
            0.270528-7.221123e-02j],...
     DESIRED: array([[0.186388+0.072523j, 0.11653 +0.186603j, 0.114425+0.210967j,
            0.259417+0.017408j, 0.270833-0.071058j],
           [0.200312-0.06305j , 0.193793+0.123873j, 0.197765+0.152935j,...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3.8e-14
    
    Mismatched elements: 40 / 40 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.17551651237807459+0.09588510772084055j) (ACTUAL), (0.1711003725142266+0.10355994653094838j) (DESIRED)
     [0, 1]: (0.10645898907886464+0.19252657905937606j) (ACTUAL), (0.14497855010730035+0.1654727168109142j) (DESIRED)
     [0, 2]: (0.06419971886990088+0.23125396450012636j) (ACTUAL), (-0.002963480383337303+0.23998170301924598j) (DESIRED)
     [0, 3]: (0.1258151689113855+0.22753141161562626j) (ACTUAL), (0.11020788860862395+0.2354871998398833j) (DESIRED)
     [0, 4]: (0.24572311732930432+0.13423915080917692j) (ACTUAL), (0.257372601314686+0.1102694159434597j) (DESIRED)
    Max absolute difference among violations: 0.09505027
    Max relative difference among violations: 0.30661377
     ACTUAL: array([[ 0.175517+0.095885j,  0.106459+0.192527j,  0.0642  +0.231254j,
             0.125815+0.227531j,  0.245723+0.134239j,  0.299353-0.019691j,
             0.305708-0.094566j,  0.339267-0.022317j],...
     DESIRED: array([[ 0.1711  +0.10356j ,  0.144979+0.165473j, -0.002963+0.239982j,
             0.110208+0.235487j,  0.257373+0.110269j,  0.299789+0.011255j,
             0.318263-0.033294j,  0.337151-0.043925j],...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.17551651237807456+0.09588510772084058j) (ACTUAL), (0.1844988308943591+0.07720221109925991j) (DESIRED)
     [0, 1]: (0.06710265761546894+0.2095166660219209j) (ACTUAL), (0.042744783780447014+0.21580751483570454j) (DESIRED)
     [0, 2]: (0.13562670624242185+0.1980035266196838j) (ACTUAL), (0.19205538228174218+0.14392612735919033j) (DESIRED)
     [0, 3]: (0.25988478171519847+0.007739524070875307j) (ACTUAL), (0.25801961114412014-0.03202936566710349j) (DESIRED)
     [0, 4]: (0.2705282566390104-0.07221123430504225j) (ACTUAL), (0.27701282774439945-0.040790847809915556j) (DESIRED)
    Max absolute difference among violations: 0.14442237
    Max relative difference among violations: 0.51378146
     ACTUAL: array([[0.175517+9.588511e-02j, 0.067103+2.095167e-01j,
            0.135627+1.980035e-01j, 0.259885+7.739524e-03j,
            0.270528-7.221123e-02j],...
     DESIRED: array([[0.184499+0.077202j, 0.042745+0.215808j, 0.192055+0.143926j,
            0.25802 -0.032029j, 0.277013-0.040791j],
           [0.204526+0.047636j, 0.18897 +0.131112j, 0.248648+0.02596j ,...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3.8e-14
    
    Mismatched elements: 40 / 40 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.17551651237807453+0.09588510772084066j) (ACTUAL), (0.1750413692834641+0.09674977539700008j) (DESIRED)
     [0, 1]: (0.10645898907886472+0.192526579059376j) (ACTUAL), (0.02224020234717381+0.21887296178275828j) (DESIRED)
     [0, 2]: (0.06419971886990097+0.23125396450012634j) (ACTUAL), (0.06981001866163489+0.22962264978538638j) (DESIRED)
     [0, 3]: (0.1258151689113855+0.22753141161562626j) (ACTUAL), (0.12488547882487619+0.22804301607083127j) (DESIRED)
     [0, 4]: (0.24572311732930435+0.1342391508091769j) (ACTUAL), (0.17069989588510354+0.22194942114097713j) (DESIRED)
    Max absolute difference among violations: 0.28492851
    Max relative difference among violations: 0.79736432
     ACTUAL: array([[ 0.175517+0.095885j,  0.106459+0.192527j,  0.0642  +0.231254j,
             0.125815+0.227531j,  0.245723+0.134239j,  0.299353-0.019691j,
             0.305708-0.094566j,  0.339267-0.022317j],...
     DESIRED: array([[ 0.175041+0.09675j ,  0.02224 +0.218873j,  0.06981 +0.229623j,
             0.124885+0.228043j,  0.1707  +0.221949j,  0.299893-0.008009j,
             0.259178-0.187688j,  0.331152-0.077061j],...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.17551651237807456+0.0958851077208406j) (ACTUAL), (0.19792522048202582+0.028733379493917417j) (DESIRED)
     [0, 1]: (0.06710265761546888+0.20951666602192093j) (ACTUAL), (0.16551392545444224+0.14493150271994468j) (DESIRED)
     [0, 2]: (0.13562670624242174+0.19800352661968385j) (ACTUAL), (0.11394474871714068+0.2112264051670332j) (DESIRED)
     [0, 3]: (0.25988478171519847+0.007739524070875219j) (ACTUAL), (0.25774576118430115+0.03416317595782322j) (DESIRED)
     [0, 4]: (0.2705282566390104-0.07221123430504237j) (ACTUAL), (0.27164129788152025-0.06790438340227518j) (DESIRED)
    Max absolute difference among violations: 0.1177116
    Max relative difference among violations: 0.53505273
     ACTUAL: array([[0.175517+9.588511e-02j, 0.067103+2.095167e-01j,
            0.135627+1.980035e-01j, 0.259885+7.739524e-03j,
            0.270528-7.221123e-02j],...
     DESIRED: array([[0.197925+0.028733j, 0.165514+0.144932j, 0.113945+0.211226j,
            0.257746+0.034163j, 0.271641-0.067904j],
           [0.197407-0.071628j, 0.195876+0.120551j, 0.170955+0.182413j,...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3.8e-14
    
    Mismatched elements: 40 / 40 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.17551651237807456+0.09588510772084058j) (ACTUAL), (0.18100162894492733+0.08507884766076029j) (DESIRED)
     [0, 1]: (0.10645898907886459+0.1925265790593761j) (ACTUAL), (0.16777257040038995+0.1423108028972017j) (DESIRED)
     [0, 2]: (0.06419971886990088+0.23125396450012636j) (ACTUAL), (-0.026602624878904146+0.23852106898459163j) (DESIRED)
     [0, 3]: (0.12581516891138553+0.22753141161562623j) (ACTUAL), (0.08814298627324915+0.244603380947267j) (DESIRED)
     [0, 4]: (0.24572311732930432+0.13423915080917698j) (ACTUAL), (0.27018298710962+0.07349254027806444j) (DESIRED)
    Max absolute difference among violations: 0.17061296
    Max relative difference among violations: 0.55036439
     ACTUAL: array([[ 0.175517+0.095885j,  0.106459+0.192527j,  0.0642  +0.231254j,
             0.125815+0.227531j,  0.245723+0.134239j,  0.299353-0.019691j,
             0.305708-0.094566j,  0.339267-0.022317j],...
     DESIRED: array([[ 0.181002+0.085079j,  0.167773+0.142311j, -0.026603+0.238521j,
             0.088143+0.244603j,  0.270183+0.073493j,  0.283953+0.096801j,
             0.318506+0.030881j,  0.334588-0.060424j],...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
=========================== short test summary info ===========================
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[1-0.0002-shape0]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[1-0.0002-shape1]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[1--0.0002-shape0]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[1--0.0002-shape1]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[3-0.0002-shape0]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[3-0.0002-shape1]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[3--0.0002-shape0]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[3--0.0002-shape1]
8 failed, 4 passed in 0.14s
NEGATIVE CONTROL VERIFIED: True; pytest exit=1; assertion call failures=8; other failures=0
SOURCE/TEST HASHES UNCHANGED: True; files=27
DRIVER CHILD EXIT: 0
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B C:\holographiclab\runs\m3\negative_controls.py wrong_backward_direction
CASE wrong_backward_direction
MUTATION 'returned = _apply_transfer(constrained, backward, identity=identity)' -> 'returned = _apply_transfer(constrained, forward, identity=identity)'
PYTEST ARGS ["-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", "C:\\holographiclab\\runs\\m3\\negative-pytest-wrong_backward_direction-c3bd1f810b794edab5a1193e990e109b", "tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft"]
....FFFFFFFF                                                             [100%]
================================== FAILURES ===================================
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.19208379531599867-0.0557118979841966j) (ACTUAL), (0.19095430775074929+0.059468078423908534j) (DESIRED)
     [0, 1]: (0.20946863717918263+0.06725243518487606j) (ACTUAL), (0.0337421701065892+0.21739702379862058j) (DESIRED)
     [0, 2]: (0.2253546043482497+0.08255484418884115j) (ACTUAL), (0.16105052083760607+0.1779402420419165j) (DESIRED)
     [0, 3]: (0.20990436983750155-0.1534280141405779j) (ACTUAL), (0.2584027005343457-0.028775759878016366j) (DESIRED)
     [0, 4]: (0.15338441159035016-0.23425034104795253j) (ACTUAL), (0.2778098682772297-0.03495249759013376j) (DESIRED)
    Max absolute difference among violations: 0.2711549
    Max relative difference among violations: 1.05061167
     ACTUAL: array([[0.192084-0.055712j, 0.209469+0.067252j, 0.225355+0.082555j,
            0.209904-0.153428j, 0.153384-0.23425j ],
           [0.127833-0.166609j, 0.227977-0.030436j, 0.249411-0.017156j,...
     DESIRED: array([[0.190954+0.059468j, 0.033742+0.217397j, 0.161051+0.17794j ,
            0.258403-0.028776j, 0.27781 -0.034952j],
           [0.209927-0.005535j, 0.184245+0.137672j, 0.242389+0.061219j,...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3.8e-14
    
    Mismatched elements: 40 / 40 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.1821014159692773-0.08269869589046877j) (ACTUAL), (0.18438453763566176+0.07747478480695019j) (DESIRED)
     [0, 1]: (0.21116749813079802+0.061711325809606574j) (ACTUAL), (0.054814232211907635+0.2130619626939991j) (DESIRED)
     [0, 2]: (0.12435620617549922+0.20526941804768858j) (ACTUAL), (0.07482688450281882+0.22803714029868427j) (DESIRED)
     [0, 3]: (0.24763724987464258+0.0792198994856964j) (ACTUAL), (0.13015886285192305+0.2250748107210007j) (DESIRED)
     [0, 4]: (0.2138932321034314-0.18069223907060214j) (ACTUAL), (0.22494764069786996+0.16672899851094294j) (DESIRED)
    Max absolute difference among violations: 0.73621825
    Max relative difference among violations: 1.93741644
     ACTUAL: array([[ 0.182101-0.082699j,  0.211167+0.061711j,  0.124356+0.205269j,
             0.247637+0.07922j ,  0.213893-0.180692j,  0.149874-0.25988j ,
             0.001481-0.319997j, -0.026874-0.338936j],...
     DESIRED: array([[ 0.184385+0.077475j,  0.054814+0.213062j,  0.074827+0.228037j,
             0.130159+0.225075j,  0.224948+0.166729j,  0.299858-0.009238j,
             0.287647-0.140212j,  0.337784-0.038757j],...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.11394970809868649+0.1643638160430213j) (ACTUAL), (0.18638766014406047+0.07252337654868406j) (DESIRED)
     [0, 1]: (-0.11635514536086596+0.18671229243960277j) (ACTUAL), (0.11653037705750312+0.1866029775293957j) (DESIRED)
     [0, 2]: (0.0010592813736376339+0.23999766232813907j) (ACTUAL), (0.11442475353783108+0.2109667646284756j) (DESIRED)
     [0, 3]: (0.21530205603236735+0.14575673112496507j) (ACTUAL), (0.2594165909505394+0.017407824091496882j) (DESIRED)
     [0, 4]: (0.23225690366303697+0.15638647863820831j) (ACTUAL), (0.2708333700842483-0.071058325682559j) (DESIRED)
    Max absolute difference among violations: 0.27060917
    Max relative difference among violations: 1.05857067
     ACTUAL: array([[ 0.11395 +0.164364j, -0.116355+0.186712j,  0.001059+0.239998j,
             0.215302+0.145757j,  0.232257+0.156386j],
           [ 0.17258 +0.119651j,  0.041761+0.226177j,  0.138346+0.208232j,...
     DESIRED: array([[0.186388+0.072523j, 0.11653 +0.186603j, 0.114425+0.210967j,
            0.259417+0.017408j, 0.270833-0.071058j],
           [0.200312-0.06305j , 0.193793+0.123873j, 0.197765+0.152935j,...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3.8e-14
    
    Mismatched elements: 40 / 40 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.09653609668794093+0.1751593047378772j) (ACTUAL), (0.1711003725142266+0.10355994653094838j) (DESIRED)
     [0, 1]: (-0.06192106805992942+0.2111060902255489j) (ACTUAL), (0.14497855010730035+0.1654727168109142j) (DESIRED)
     [0, 2]: (-0.07611576688264232+0.22761017119598864j) (ACTUAL), (-0.002963480383337303+0.23998170301924598j) (DESIRED)
     [0, 3]: (-0.05129800461890822+0.2548892204902327j) (ACTUAL), (0.11020788860862395+0.2354871998398833j) (DESIRED)
     [0, 4]: (-0.024520752203809938+0.27892424188542553j) (ACTUAL), (0.257372601314686+0.1102694159434597j) (DESIRED)
    Max absolute difference among violations: 0.74366629
    Max relative difference among violations: 1.95701655
     ACTUAL: array([[ 0.096536+0.175159j, -0.061921+0.211106j, -0.076116+0.22761j ,
            -0.051298+0.254889j, -0.024521+0.278924j,  0.143931+0.263218j,
             0.197812+0.251536j,  0.140697+0.309523j],...
     DESIRED: array([[ 0.1711  +0.10356j ,  0.144979+0.165473j, -0.002963+0.239982j,
             0.110208+0.235487j,  0.257373+0.110269j,  0.299789+0.011255j,
             0.318263-0.033294j,  0.337151-0.043925j],...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (-0.013343079201857727-0.1995544092156647j) (ACTUAL), (0.1844988308943591+0.07720221109925991j) (DESIRED)
     [0, 1]: (0.08212695575500752-0.20409596551234185j) (ACTUAL), (0.042744783780447014+0.21580751483570454j) (DESIRED)
     [0, 2]: (0.11254513560904633-0.21197545247207608j) (ACTUAL), (0.19205538228174218+0.14392612735919033j) (DESIRED)
     [0, 3]: (-0.12134533372329809-0.22994631978699162j) (ACTUAL), (0.25801961114412014-0.03202936566710349j) (DESIRED)
     [0, 4]: (-0.19988765997994395-0.19607377026961642j) (ACTUAL), (0.27701282774439945-0.040790847809915556j) (DESIRED)
    Max absolute difference among violations: 0.53094212
    Max relative difference among violations: 1.91702835
     ACTUAL: array([[-0.013343-0.199554j,  0.082127-0.204096j,  0.112545-0.211975j,
            -0.121345-0.229946j, -0.199888-0.196074j],
           [-0.104137-0.182361j,  0.03372 -0.227515j,  0.032836-0.247834j,...
     DESIRED: array([[0.184499+0.077202j, 0.042745+0.215808j, 0.192055+0.143926j,
            0.25802 -0.032029j, 0.277013-0.040791j],
           [0.204526+0.047636j, 0.18897 +0.131112j, 0.248648+0.02596j ,...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3.8e-14
    
    Mismatched elements: 40 / 40 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (-0.18319830520790714+0.08023952248705436j) (ACTUAL), (0.1750413692834641+0.09674977539700008j) (DESIRED)
     [0, 1]: (-0.20231674262972446-0.08641721849086463j) (ACTUAL), (0.02224020234717381+0.21887296178275828j) (DESIRED)
     [0, 2]: (0.11921249520579832-0.20829877816926223j) (ACTUAL), (0.06981001866163489+0.22962264978538638j) (DESIRED)
     [0, 3]: (-0.021478995648008956-0.25911127483371466j) (ACTUAL), (0.12488547882487619+0.22804301607083127j) (DESIRED)
     [0, 4]: (-0.27913789563844355+0.021955300465750956j) (ACTUAL), (0.17069989588510354+0.22194942114097713j) (DESIRED)
    Max absolute difference among violations: 0.69058499
    Max relative difference among violations: 1.97309997
     ACTUAL: array([[-0.183198+0.08024j , -0.202317-0.086417j,  0.119212-0.208299j,
            -0.021479-0.259111j, -0.279138+0.021955j, -0.229571+0.193125j,
             0.109015+0.300858j,  0.255456+0.224371j],...
     DESIRED: array([[ 0.175041+0.09675j ,  0.02224 +0.218873j,  0.06981 +0.229623j,
             0.124885+0.228043j,  0.1707  +0.221949j,  0.299893-0.008009j,
             0.259178-0.187688j,  0.331152-0.077061j],...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (-0.1729523111544327+0.10043653750672761j) (ACTUAL), (0.19792522048202582+0.028733379493917417j) (DESIRED)
     [0, 1]: (-0.10138543114593598-0.19524598421312708j) (ACTUAL), (0.16551392545444224+0.14493150271994468j) (DESIRED)
     [0, 2]: (-0.2385677368889601-0.026180811975183512j) (ACTUAL), (0.11394474871714068+0.2112264051670332j) (DESIRED)
     [0, 3]: (-0.10491611357616236+0.23789201145072908j) (ACTUAL), (0.25774576118430115+0.03416317595782322j) (DESIRED)
     [0, 4]: (-0.10141496377057066+0.26098851530941714j) (ACTUAL), (0.27164129788152025-0.06790438340227518j) (DESIRED)
    Max absolute difference among violations: 0.52804889
    Max relative difference among violations: 1.96538216
     ACTUAL: array([[-0.172952+0.100437j, -0.101385-0.195246j, -0.238568-0.026181j,
            -0.104916+0.237892j, -0.101415+0.260989j],
           [-0.121115+0.171555j, -0.221616+0.061534j, -0.164   +0.18869j ,...
     DESIRED: array([[0.197925+0.028733j, 0.165514+0.144932j, 0.113945+0.211226j,
            0.257746+0.034163j, 0.271641-0.067904j],
           [0.197407-0.071628j, 0.195876+0.120551j, 0.170955+0.182413j,...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3.8e-14
    
    Mismatched elements: 40 / 40 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (-0.15934888500566488+0.1208632816344625j) (ACTUAL), (0.18100162894492733+0.08507884766076029j) (DESIRED)
     [0, 1]: (-0.21232488414151435-0.05760332954172447j) (ACTUAL), (0.16777257040038995+0.1423108028972017j) (DESIRED)
     [0, 2]: (-0.23723929661940724-0.03629760514867225j) (ACTUAL), (-0.026602624878904146+0.23852106898459163j) (DESIRED)
     [0, 3]: (-0.2596908925896817-0.012674395684781738j) (ACTUAL), (0.08814298627324915+0.244603380947267j) (DESIRED)
     [0, 4]: (-0.22367641123165527-0.16843058825085025j) (ACTUAL), (0.27018298710962+0.07349254027806444j) (DESIRED)
    Max absolute difference among violations: 0.66501151
    Max relative difference among violations: 1.99866275
     ACTUAL: array([[-0.159349+0.120863j, -0.212325-0.057603j, -0.237239-0.036298j,
            -0.259691-0.012674j, -0.223676-0.168431j, -0.13286 -0.268976j,
            -0.298208+0.11607j , -0.278774+0.194641j],...
     DESIRED: array([[ 0.181002+0.085079j,  0.167773+0.142311j, -0.026603+0.238521j,
             0.088143+0.244603j,  0.270183+0.073493j,  0.283953+0.096801j,
             0.318506+0.030881j,  0.334588-0.060424j],...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
=========================== short test summary info ===========================
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[1-0.0002-shape0]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[1-0.0002-shape1]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[1--0.0002-shape0]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[1--0.0002-shape1]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[3-0.0002-shape0]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[3-0.0002-shape1]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[3--0.0002-shape0]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[3--0.0002-shape1]
8 failed, 4 passed in 0.11s
NEGATIVE CONTROL VERIFIED: True; pytest exit=1; assertion call failures=8; other failures=0
SOURCE/TEST HASHES UNCHANGED: True; files=27
DRIVER CHILD EXIT: 0
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B C:\holographiclab\runs\m3\negative_controls.py amplitude_treated_as_intensity
CASE amplitude_treated_as_intensity
MUTATION 'constrained = _project_amplitude(reconstruction, target)' -> 'constrained = _project_amplitude(reconstruction, target**2)'
PYTEST ARGS ["-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", "C:\\holographiclab\\runs\\m3\\negative-pytest-amplitude_treated_as_intensity-af35f10841544e88b52927ee6eb4ad5b", "tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft"]
....FFFFFFFF                                                             [100%]
================================== FAILURES ===================================
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.197200129777381+0.03334829554541132j) (ACTUAL), (0.19095430775074929+0.059468078423908534j) (DESIRED)
     [0, 1]: (-0.00998193657488311+0.2197734309287977j) (ACTUAL), (0.0337421701065892+0.21739702379862058j) (DESIRED)
     [0, 2]: (0.17741338868138096+0.16163071959435577j) (ACTUAL), (0.16105052083760607+0.1779402420419165j) (DESIRED)
     [0, 3]: (0.24925942728511866-0.07395767647441778j) (ACTUAL), (0.2584027005343457-0.028775759878016366j) (DESIRED)
     [0, 4]: (0.27991089597507096-0.007063307612798383j) (ACTUAL), (0.2778098682772297-0.03495249759013376j) (DESIRED)
    Max absolute difference among violations: 0.06680128
    Max relative difference among violations: 0.26720513
     ACTUAL: array([[ 0.1972  +0.033348j, -0.009982+0.219773j,  0.177413+0.161631j,
             0.249259-0.073958j,  0.279911-0.007063j],
           [ 0.209966+0.003789j,  0.181547+0.141212j,  0.249947-0.005154j,...
     DESIRED: array([[0.190954+0.059468j, 0.033742+0.217397j, 0.161051+0.17794j ,
            0.258403-0.028776j, 0.27781 -0.034952j],
           [0.209927-0.005535j, 0.184245+0.137672j, 0.242389+0.061219j,...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3.8e-14
    
    Mismatched elements: 40 / 40 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.190710847247908+0.06024427559515606j) (ACTUAL), (0.18438453763566176+0.07747478480695019j) (DESIRED)
     [0, 1]: (0.024547056415115284+0.21862626105148747j) (ACTUAL), (0.054814232211907635+0.2130619626939991j) (DESIRED)
     [0, 2]: (0.10605525833421306+0.2152958015839216j) (ACTUAL), (0.07482688450281882+0.22803714029868427j) (DESIRED)
     [0, 3]: (0.1675230587054908+0.19883667871385471j) (ACTUAL), (0.13015886285192305+0.2250748107210007j) (DESIRED)
     [0, 4]: (0.2124116046215786+0.18243165904547978j) (ACTUAL), (0.22494764069786996+0.16672899851094294j) (DESIRED)
    Max absolute difference among violations: 0.13334886
    Max relative difference among violations: 0.36040233
     ACTUAL: array([[ 0.190711+0.060244j,  0.024547+0.218626j,  0.106055+0.215296j,
             0.167523+0.198837j,  0.212412+0.182432j,  0.299954-0.005241j,
             0.265293-0.17894j ,  0.33873 -0.029358j],...
     DESIRED: array([[ 0.184385+0.077475j,  0.054814+0.213062j,  0.074827+0.228037j,
             0.130159+0.225075j,  0.224948+0.166729j,  0.299858-0.009238j,
             0.287647-0.140212j,  0.337784-0.038757j],...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.17780032702542753+0.09158080426405434j) (ACTUAL), (0.18638766014406047+0.07252337654868406j) (DESIRED)
     [0, 1]: (0.13312166993560484+0.17515313583706082j) (ACTUAL), (0.11653037705750312+0.1866029775293957j) (DESIRED)
     [0, 2]: (0.06814514277848167+0.23012222733951704j) (ACTUAL), (0.11442475353783108+0.2109667646284756j) (DESIRED)
     [0, 3]: (0.25745986136917864+0.036254927716978184j) (ACTUAL), (0.2594165909505394+0.017407824091496882j) (DESIRED)
     [0, 4]: (0.25833378651085576-0.10799840159448479j) (ACTUAL), (0.2708333700842483-0.071058325682559j) (DESIRED)
    Max absolute difference among violations: 0.0629757
    Max relative difference among violations: 0.209919
     ACTUAL: array([[0.1778  +0.091581j, 0.133122+0.175153j, 0.068145+0.230122j,
            0.25746 +0.036255j, 0.258334-0.107998j],
           [0.195407-0.076917j, 0.195839+0.120611j, 0.171183+0.182199j,...
     DESIRED: array([[0.186388+0.072523j, 0.11653 +0.186603j, 0.114425+0.210967j,
            0.259417+0.017408j, 0.270833-0.071058j],
           [0.200312-0.06305j , 0.193793+0.123873j, 0.197765+0.152935j,...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3.8e-14
    
    Mismatched elements: 40 / 40 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.15527837253164342+0.1260500972785193j) (ACTUAL), (0.1711003725142266+0.10355994653094838j) (DESIRED)
     [0, 1]: (0.16490838727742307+0.14562013530264095j) (ACTUAL), (0.14497855010730035+0.1654727168109142j) (DESIRED)
     [0, 2]: (-0.05585498347133647+0.23340998440815838j) (ACTUAL), (-0.002963480383337303+0.23998170301924598j) (DESIRED)
     [0, 3]: (0.10081430473676278+0.23965908278311326j) (ACTUAL), (0.11020788860862395+0.2354871998398833j) (DESIRED)
     [0, 4]: (0.26837988751686104+0.07982628624981267j) (ACTUAL), (0.257372601314686+0.1102694159434597j) (DESIRED)
    Max absolute difference among violations: 0.09365856
    Max relative difference among violations: 0.3121952
     ACTUAL: array([[ 0.155278+0.12605j ,  0.164908+0.14562j , -0.055855+0.23341j ,
             0.100814+0.239659j,  0.26838 +0.079826j,  0.281709+0.103152j,
             0.319631+0.015372j,  0.335178-0.057057j],...
     DESIRED: array([[ 0.1711  +0.10356j ,  0.144979+0.165473j, -0.002963+0.239982j,
             0.110208+0.235487j,  0.257373+0.110269j,  0.299789+0.011255j,
             0.318263-0.033294j,  0.337151-0.043925j],...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.19131568933732124+0.05829499990038242j) (ACTUAL), (0.1844988308943591+0.07720221109925991j) (DESIRED)
     [0, 1]: (-0.03515224031047001+0.2171734790464871j) (ACTUAL), (0.042744783780447014+0.21580751483570454j) (DESIRED)
     [0, 2]: (0.21547998742008678+0.10568053284043967j) (ACTUAL), (0.19205538228174218+0.14392612735919033j) (DESIRED)
     [0, 3]: (0.24557639839376724-0.08539456980362227j) (ACTUAL), (0.25801961114412014-0.03202936566710349j) (DESIRED)
     [0, 4]: (0.27950575696989477-0.016629245944604035j) (ACTUAL), (0.27701282774439945-0.040790847809915556j) (DESIRED)
    Max absolute difference among violations: 0.0989494
    Max relative difference among violations: 0.39579759
     ACTUAL: array([[ 0.191316+0.058295j, -0.035152+0.217173j,  0.21548 +0.105681j,
             0.245576-0.085395j,  0.279506-0.016629j],
           [ 0.199794+0.064671j,  0.196085+0.120212j,  0.239244-0.072541j,...
     DESIRED: array([[0.184499+0.077202j, 0.042745+0.215808j, 0.192055+0.143926j,
            0.25802 -0.032029j, 0.277013-0.040791j],
           [0.204526+0.047636j, 0.18897 +0.131112j, 0.248648+0.02596j ,...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3.8e-14
    
    Mismatched elements: 40 / 40 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.18555409488177455+0.07463027450442224j) (ACTUAL), (0.1750413692834641+0.09674977539700008j) (DESIRED)
     [0, 1]: (-0.02538235886959871+0.21853085790847687j) (ACTUAL), (0.02224020234717381+0.21887296178275828j) (DESIRED)
     [0, 2]: (0.11772293839126392+0.20914423199439827j) (ACTUAL), (0.06981001866163489+0.22962264978538638j) (DESIRED)
     [0, 3]: (0.1794789995084732+0.1881150943848937j) (ACTUAL), (0.12488547882487619+0.22804301607083127j) (DESIRED)
     [0, 4]: (0.1304778969762425+0.24774082909495773j) (ACTUAL), (0.17069989588510354+0.22194942114097713j) (DESIRED)
    Max absolute difference among violations: 0.19565917
    Max relative difference among violations: 0.52880856
     ACTUAL: array([[ 0.185554+0.07463j , -0.025382+0.218531j,  0.117723+0.209144j,
             0.179479+0.188115j,  0.130478+0.247741j,  0.29996 -0.004896j,
             0.210085-0.24138j ,  0.332705-0.070051j],...
     DESIRED: array([[ 0.175041+0.09675j ,  0.02224 +0.218873j,  0.06981 +0.229623j,
             0.124885+0.228043j,  0.1707  +0.221949j,  0.299893-0.008009j,
             0.259178-0.187688j,  0.331152-0.077061j],...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.1944333295369483+0.04685808751087128j) (ACTUAL), (0.19792522048202582+0.028733379493917417j) (DESIRED)
     [0, 1]: (0.18104388922330597+0.12499244047101132j) (ACTUAL), (0.16551392545444224+0.14493150271994468j) (DESIRED)
     [0, 2]: (0.04764971520856587+0.23522224520768137j) (ACTUAL), (0.11394474871714068+0.2112264051670332j) (DESIRED)
     [0, 3]: (0.2540906015557877+0.05511774851187179j) (ACTUAL), (0.25774576118430115+0.03416317595782322j) (DESIRED)
     [0, 4]: (0.25863655825133197-0.10727129502297149j) (ACTUAL), (0.27164129788152025-0.06790438340227518j) (DESIRED)
    Max absolute difference among violations: 0.07050413
    Max relative difference among violations: 0.29376719
     ACTUAL: array([[0.194433+0.046858j, 0.181044+0.124992j, 0.04765 +0.235222j,
            0.254091+0.055118j, 0.258637-0.107271j],
           [0.187186-0.095192j, 0.194969+0.122012j, 0.116479+0.221207j,...
     DESIRED: array([[0.197925+0.028733j, 0.165514+0.144932j, 0.113945+0.211226j,
            0.257746+0.034163j, 0.271641-0.067904j],
           [0.197407-0.071628j, 0.195876+0.120551j, 0.170955+0.182413j,...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=3.8e-14
    
    Mismatched elements: 40 / 40 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.16869217124878194+0.10743812805224982j) (ACTUAL), (0.18100162894492733+0.08507884766076029j) (DESIRED)
     [0, 1]: (0.18841122008508895+0.11358350296609176j) (ACTUAL), (0.16777257040038995+0.1423108028972017j) (DESIRED)
     [0, 2]: (-0.08268253781085556+0.2253077849102344j) (ACTUAL), (-0.026602624878904146+0.23852106898459163j) (DESIRED)
     [0, 3]: (0.06861058920766314+0.250783944957761j) (ACTUAL), (0.08814298627324915+0.244603380947267j) (DESIRED)
     [0, 4]: (0.27912539005903764+0.022113720274755094j) (ACTUAL), (0.27018298710962+0.07349254027806444j) (DESIRED)
    Max absolute difference among violations: 0.16902572
    Max relative difference among violations: 0.56341906
     ACTUAL: array([[ 0.168692+0.107438j,  0.188411+0.113584j, -0.082683+0.225308j,
             0.068611+0.250784j,  0.279125+0.022114j,  0.186554+0.234942j,
             0.281323+0.152503j,  0.329896-0.082273j],...
     DESIRED: array([[ 0.181002+0.085079j,  0.167773+0.142311j, -0.026603+0.238521j,
             0.088143+0.244603j,  0.270183+0.073493j,  0.283953+0.096801j,
             0.318506+0.030881j,  0.334588-0.060424j],...
C:\holographiclab\tests\test_gerchberg_saxton_reference.py:119: AssertionError:
=========================== short test summary info ===========================
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[1-0.0002-shape0]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[1-0.0002-shape1]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[1--0.0002-shape0]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[1--0.0002-shape1]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[3-0.0002-shape0]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[3-0.0002-shape1]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[3--0.0002-shape0]
FAILED tests/test_gerchberg_saxton_reference.py::test_gs_complete_iteration_and_history_match_independent_direct_dft[3--0.0002-shape1]
8 failed, 4 passed in 0.14s
NEGATIVE CONTROL VERIFIED: True; pytest exit=1; assertion call failures=8; other failures=0
SOURCE/TEST HASHES UNCHANGED: True; files=27
DRIVER CHILD EXIT: 0
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B C:\holographiclab\runs\m3\negative_controls.py target_projected_reconstruction
CASE target_projected_reconstruction
MUTATION 'reconstruction=ComplexField(data=reconstruction, grid=grid, wavelength_m=wavelength)' -> 'reconstruction=ComplexField(data=_project_amplitude(reconstruction, target), grid=grid, wavelength_m=wavelength)'
PYTEST ARGS ["-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", "C:\\holographiclab\\runs\\m3\\negative-pytest-target_projected_reconstruction-381d436a72b44a31bb0f533a5fe165cf", "tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss"]
FFFFFFFFF                                                                [100%]
================================== FAILURES ===================================
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.31424702881637173-0.15410647254441462j) (ACTUAL), (0.2076635134049014-0.1018380082941355j) (DESIRED)
     [0, 1]: (0.0708892900437707+0.39366827222560136j) (ACTUAL), (0.04552181913067706+0.2527955333545443j) (DESIRED)
     [0, 2]: (0.18870147042371999+0.06627031809132904j) (ACTUAL), (0.16620448854527153+0.05836957337624047j) (DESIRED)
     [0, 3]: (-0.24997583757099576+0.0034757201669790845j) (ACTUAL), (-0.23663250236729788+0.003290191438631166j) (DESIRED)
     [0, 4]: (-0.03817527854548447-0.29756116700264285j) (ACTUAL), (-0.02561851767980986-0.1996861924294662j) (DESIRED)
    Max absolute difference among violations: 0.42091288
    Max relative difference among violations: 0.98094972
     ACTUAL: array([[ 0.314247-0.154106j,  0.070889+0.393668j,  0.188701+0.06627j ,
            -0.249976+0.003476j, -0.038175-0.297561j],
           [ 0.379425+0.464797j, -0.452144+0.466975j,  0.09372 +0.440132j,...
     DESIRED: array([[ 0.207664-0.101838j,  0.045522+0.252796j,  0.166204+0.05837j ,
            -0.236633+0.00329j , -0.025619-0.199686j],
           [ 0.266992+0.327067j, -0.433342+0.447556j,  0.091197+0.428281j,...
C:\holographiclab\tests\test_gerchberg_saxton.py:105: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (-0.32287070540881524+0.1351092431657213j) (ACTUAL), (-0.1808183222069369+0.075665665093219j) (DESIRED)
     [0, 1]: (-0.39817375718387377+0.038179301854244674j) (ACTUAL), (-0.24939303068849095+0.023913308266078848j) (DESIRED)
     [0, 2]: (-0.1966922622328371+0.03622366598963783j) (ACTUAL), (-0.4187749308504878+0.07712333493833412j) (DESIRED)
     [0, 3]: (0.18429887497307293-0.16891987652037765j) (ACTUAL), (0.31782069412744285-0.29129983791530045j) (DESIRED)
     [0, 4]: (0.26119179209538285-0.14757658263424564j) (ACTUAL), (0.5225836854703052-0.2952662249583777j) (DESIRED)
    Max absolute difference among violations: 0.30022983
    Max relative difference among violations: 0.78560835
     ACTUAL: array([[-0.322871+1.351092e-01j, -0.398174+3.817930e-02j,
            -0.196692+3.622367e-02j,  0.184299-1.689199e-01j,
             0.261192-1.475766e-01j],...
     DESIRED: array([[-0.180818+7.566567e-02j, -0.249393+2.391331e-02j,
            -0.418775+7.712333e-02j,  0.317821-2.912998e-01j,
             0.522584-2.952662e-01j],...
C:\holographiclab\tests\test_gerchberg_saxton.py:105: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.24733887746889607+0.2476357803154189j) (ACTUAL), (0.14133650141079776+0.1415061601802394j) (DESIRED)
     [0, 1]: (-0.31944146620710473+0.2407429119776015j) (ACTUAL), (-0.19965091637944044+0.15046431998600093j) (DESIRED)
     [0, 2]: (-0.0321376552719535+0.19740104131848213j) (ACTUAL), (-0.04820648290793026+0.2961015619777232j) (DESIRED)
     [0, 3]: (-0.03878713680554847-0.24697278801201494j) (ACTUAL), (-0.05430199152776785-0.3457619032168209j) (DESIRED)
     [0, 4]: (0.09300314650335335-0.28521994099374576j) (ACTUAL), (0.12400419533780445-0.38029325465832764j) (DESIRED)
    Max absolute difference among violations: 0.15
    Max relative difference among violations: 0.75
     ACTUAL: array([[ 0.247339+0.247636j, -0.319441+0.240743j, -0.032138+0.197401j,
            -0.038787-0.246973j,  0.093003-0.28522j ],
           [-0.42039 +0.428103j, -0.649644-0.0215j  , -0.194738+0.405681j,...
     DESIRED: array([[ 0.141337+0.141506j, -0.199651+0.150464j, -0.048206+0.296102j,
            -0.054302-0.345762j,  0.124004-0.380293j],
           [-0.315293+0.321077j, -0.499726-0.016538j, -0.238013+0.495833j,...
C:\holographiclab\tests\test_gerchberg_saxton.py:105: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.3238133889387533-0.13283406620291224j) (ACTUAL), (0.23139815613067063-0.09492367839214672j) (DESIRED)
     [0, 1]: (0.06593703188318524+0.39452795569697696j) (ACTUAL), (0.04248056017216528+0.25417838933482195j) (DESIRED)
     [0, 2]: (0.19590686269711546+0.04025544867683814j) (ACTUAL), (0.16121045169238096+0.03312594043377583j) (DESIRED)
     [0, 3]: (-0.24276605770211865+0.0597046164695126j) (ACTUAL), (-0.22964391491032787+0.056477425197150474j) (DESIRED)
     [0, 4]: (0.003616213431165624-0.2999782042089396j) (ACTUAL), (0.003145940789006059-0.26096735892314116j) (DESIRED)
    Max absolute difference among violations: 0.28975227
    Max relative difference among violations: 0.55216955
     ACTUAL: array([[ 0.323813-0.132834j,  0.065937+0.394528j,  0.195907+0.040255j,
            -0.242766+0.059705j,  0.003616-0.299978j],
           [ 0.361621+0.47878j , -0.437936+0.480325j,  0.008584+0.449918j,...
     DESIRED: array([[ 0.231398-0.094924j,  0.042481+0.254178j,  0.16121 +0.033126j,
            -0.229644+0.056477j,  0.003146-0.260967j],
           [ 0.282355+0.373833j, -0.410031+0.449718j,  0.009089+0.476409j,...
C:\holographiclab\tests\test_gerchberg_saxton.py:105: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (-0.34986524091842147+0.009711498190025628j) (ACTUAL), (-0.2654359098835197+0.007367923580046934j) (DESIRED)
     [0, 1]: (-0.37224717087687365+0.14639687077995775j) (ACTUAL), (-0.31571941826991834+0.12416571164344122j) (DESIRED)
     [0, 2]: (-0.19910805214981583+0.018867526841274792j) (ACTUAL), (-0.4175676891144571+0.039568814507250874j) (DESIRED)
     [0, 3]: (0.17289256822925664-0.1805772960565415j) (ACTUAL), (0.2963343092817556-0.30950577486896985j) (DESIRED)
     [0, 4]: (0.266371145563191-0.13800874179324052j) (ACTUAL), (0.47874058066448694-0.24803882208479439j) (DESIRED)
    Max absolute difference among violations: 0.23918068
    Max relative difference among violations: 0.52317179
     ACTUAL: array([[-0.349865+0.009711j, -0.372247+0.146397j, -0.199108+0.018868j,
             0.172893-0.180577j,  0.266371-0.138009j],
           [-0.395055-0.451588j, -0.615094-0.21014j , -0.449941+0.007306j,...
     DESIRED: array([[-0.265436+0.007368j, -0.315719+0.124166j, -0.417568+0.039569j,
             0.296334-0.309506j,  0.478741-0.248039j],
           [-0.339095-0.38762j , -0.511356-0.174699j, -0.622624+0.01011j ,...
C:\holographiclab\tests\test_gerchberg_saxton.py:105: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.24733887746889605+0.2476357803154189j) (ACTUAL), (0.14133650141079776+0.1415061601802394j) (DESIRED)
     [0, 1]: (-0.31944146620710473+0.2407429119776015j) (ACTUAL), (-0.19965091637944044+0.15046431998600093j) (DESIRED)
     [0, 2]: (-0.0321376552719535+0.19740104131848213j) (ACTUAL), (-0.04820648290793026+0.2961015619777232j) (DESIRED)
     [0, 3]: (-0.03878713680554847-0.24697278801201494j) (ACTUAL), (-0.05430199152776785-0.3457619032168209j) (DESIRED)
     [0, 4]: (0.09300314650335335-0.28521994099374576j) (ACTUAL), (0.12400419533780445-0.38029325465832764j) (DESIRED)
    Max absolute difference among violations: 0.15
    Max relative difference among violations: 0.75
     ACTUAL: array([[ 0.247339+0.247636j, -0.319441+0.240743j, -0.032138+0.197401j,
            -0.038787-0.246973j,  0.093003-0.28522j ],
           [-0.42039 +0.428103j, -0.649644-0.0215j  , -0.194738+0.405681j,...
     DESIRED: array([[ 0.141337+0.141506j, -0.199651+0.150464j, -0.048206+0.296102j,
            -0.054302-0.345762j,  0.124004-0.380293j],
           [-0.315293+0.321077j, -0.499726-0.016538j, -0.238013+0.495833j,...
C:\holographiclab\tests\test_gerchberg_saxton.py:105: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.33970728852924714-0.08425531508520298j) (ACTUAL), (0.2546362009586003-0.06315570512705915j) (DESIRED)
     [0, 1]: (0.05098226876203792+0.3967377071465168j) (ACTUAL), (0.03526451032618445+0.2744240558567058j) (DESIRED)
     [0, 2]: (0.19210773689580762-0.05562928567554293j) (ACTUAL), (0.16717764429788828-0.04841019463081543j) (DESIRED)
     [0, 3]: (-0.21499746043278845+0.12757778806458264j) (ACTUAL), (-0.20244736283582232+0.12013065967435639j) (DESIRED)
     [0, 4]: (0.0001455750330311545-0.2999999646798476j) (ACTUAL), (0.00015258186588455272-0.314439594640885j) (DESIRED)
    Max absolute difference among violations: 0.23209605
    Max relative difference among violations: 0.44571038
     ACTUAL: array([[ 3.397073e-01-0.084255j,  5.098227e-02+0.396738j,
             1.921077e-01-0.055629j, -2.149975e-01+0.127578j,
             1.455750e-04-0.3j     ],...
     DESIRED: array([[ 2.546362e-01-0.063156j,  3.526451e-02+0.274424j,
             1.671776e-01-0.04841j , -2.024474e-01+0.120131j,
             1.525819e-04-0.31444j ],...
C:\holographiclab\tests\test_gerchberg_saxton.py:105: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (-0.31482035433701144-0.15293182956833587j) (ACTUAL), (-0.24771383386066886-0.12033316556509946j) (DESIRED)
     [0, 1]: (-0.3058643758016474+0.2577731243079244j) (ACTUAL), (-0.34445724932926924+0.2902980156397842j) (DESIRED)
     [0, 2]: (-0.1999740683394048+0.00322055768261717j) (ACTUAL), (-0.3604538815642446+0.005805065262415134j) (DESIRED)
     [0, 3]: (0.17117342456724496-0.18220773507708637j) (ACTUAL), (0.29073399027397373-0.3094755042242771j) (DESIRED)
     [0, 4]: (0.27470910482651867-0.12056080509607087j) (ACTUAL), (0.39441261062052596-0.1730947429153556j) (DESIRED)
    Max absolute difference among violations: 0.18282354
    Max relative difference among violations: 0.44521594
     ACTUAL: array([[-0.31482 -0.152932j, -0.305864+0.257773j, -0.199974+0.003221j,
             0.171173-0.182208j,  0.274709-0.120561j],
           [-0.303759-0.517427j, -0.632804-0.148523j, -0.442946-0.079366j,...
     DESIRED: array([[-0.247714-0.120333j, -0.344457+0.290298j, -0.360454+0.005805j,
             0.290734-0.309476j,  0.394413-0.173095j],
           [-0.281813-0.480043j, -0.636891-0.149482j, -0.504092-0.090322j,...
C:\holographiclab\tests\test_gerchberg_saxton.py:105: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.24733887746889605+0.2476357803154189j) (ACTUAL), (0.14133650141079776+0.1415061601802394j) (DESIRED)
     [0, 1]: (-0.31944146620710473+0.2407429119776015j) (ACTUAL), (-0.19965091637944044+0.15046431998600093j) (DESIRED)
     [0, 2]: (-0.0321376552719535+0.19740104131848213j) (ACTUAL), (-0.04820648290793026+0.2961015619777232j) (DESIRED)
     [0, 3]: (-0.03878713680554847-0.24697278801201494j) (ACTUAL), (-0.05430199152776785-0.3457619032168209j) (DESIRED)
     [0, 4]: (0.09300314650335335-0.28521994099374576j) (ACTUAL), (0.12400419533780445-0.38029325465832764j) (DESIRED)
    Max absolute difference among violations: 0.15
    Max relative difference among violations: 0.75
     ACTUAL: array([[ 0.247339+0.247636j, -0.319441+0.240743j, -0.032138+0.197401j,
            -0.038787-0.246973j,  0.093003-0.28522j ],
           [-0.42039 +0.428103j, -0.649644-0.0215j  , -0.194738+0.405681j,...
     DESIRED: array([[ 0.141337+0.141506j, -0.199651+0.150464j, -0.048206+0.296102j,
            -0.054302-0.345762j,  0.124004-0.380293j],
           [-0.315293+0.321077j, -0.499726-0.016538j, -0.238013+0.495833j,...
C:\holographiclab\tests\test_gerchberg_saxton.py:105: AssertionError:
=========================== short test summary info ===========================
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[0-0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[0--0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[0-0.0]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[1-0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[1--0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[1-0.0]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[4-0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[4--0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[4-0.0]
9 failed in 0.22s
NEGATIVE CONTROL VERIFIED: True; pytest exit=1; assertion call failures=9; other failures=0
SOURCE/TEST HASHES UNCHANGED: True; files=27
DRIVER CHILD EXIT: 0
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B C:\holographiclab\runs\m3\negative_controls.py post_projection_loss
CASE post_projection_loss
MUTATION '_amplitude_residual(reconstruction, target, target_energy)' -> '_amplitude_residual(_project_amplitude(reconstruction, target), target, target_energy)'
PYTEST ARGS ["-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", "C:\\holographiclab\\runs\\m3\\negative-pytest-post_projection_loss-99697d4258204c598d0664b14df52950", "tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss"]
FFFFFFFFF                                                                [100%]
================================== FAILURES ===================================
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=1e-14
    
    Mismatched elements: 1 / 1 (100%)
    Max absolute difference among violations: 0.10264749
    Max relative difference among violations: 1.
     ACTUAL: array(4.706807e-33)
     DESIRED: array(0.102647)
C:\holographiclab\tests\test_gerchberg_saxton.py:108: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=1e-14
    
    Mismatched elements: 1 / 1 (100%)
    Max absolute difference among violations: 0.10317418
    Max relative difference among violations: 1.
     ACTUAL: array(2.353404e-33)
     DESIRED: array(0.103174)
C:\holographiclab\tests\test_gerchberg_saxton.py:108: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=1e-14
    
    Mismatched elements: 1 / 1 (100%)
    Max absolute difference among violations: 0.04295943
    Max relative difference among violations: 1.
     ACTUAL: array(3.088842e-33)
     DESIRED: array(0.042959)
C:\holographiclab\tests\test_gerchberg_saxton.py:108: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=1e-14
    
    Mismatched elements: 1 / 1 (100%)
    Max absolute difference among violations: 0.06089564
    Max relative difference among violations: 1.
     ACTUAL: array(1.059032e-32)
     DESIRED: array(0.060896)
C:\holographiclab\tests\test_gerchberg_saxton.py:108: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=1e-14
    
    Mismatched elements: 1 / 1 (100%)
    Max absolute difference among violations: 0.05319568
    Max relative difference among violations: 1.
     ACTUAL: array(4.706807e-33)
     DESIRED: array(0.053196)
C:\holographiclab\tests\test_gerchberg_saxton.py:108: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=1e-14
    
    Mismatched elements: 1 / 1 (100%)
    Max absolute difference among violations: 0.04295943
    Max relative difference among violations: 1.
     ACTUAL: array(3.088842e-33)
     DESIRED: array(0.042959)
C:\holographiclab\tests\test_gerchberg_saxton.py:108: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=1e-14
    
    Mismatched elements: 1 / 1 (100%)
    Max absolute difference among violations: 0.03514171
    Max relative difference among violations: 1.
     ACTUAL: array(8.972351e-33)
     DESIRED: array(0.035142)
C:\holographiclab\tests\test_gerchberg_saxton.py:108: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=1e-14
    
    Mismatched elements: 1 / 1 (100%)
    Max absolute difference among violations: 0.0262579
    Max relative difference among violations: 1.
     ACTUAL: array(1.206119e-32)
     DESIRED: array(0.026258)
C:\holographiclab\tests\test_gerchberg_saxton.py:108: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=1e-14
    
    Mismatched elements: 1 / 1 (100%)
    Max absolute difference among violations: 0.04295943
    Max relative difference among violations: 1.
     ACTUAL: array(3.088842e-33)
     DESIRED: array(0.042959)
C:\holographiclab\tests\test_gerchberg_saxton.py:108: AssertionError:
=========================== short test summary info ===========================
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[0-0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[0--0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[0-0.0]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[1-0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[1--0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[1-0.0]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[4-0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[4--0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[4-0.0]
9 failed in 0.21s
NEGATIVE CONTROL VERIFIED: True; pytest exit=1; assertion call failures=9; other failures=0
SOURCE/TEST HASHES UNCHANGED: True; files=27
DRIVER CHILD EXIT: 0
COMMAND C:\holographiclab\.venv\Scripts\python.exe -B C:\holographiclab\runs\m3\negative_controls.py inconsistent_returned_phase
CASE inconsistent_returned_phase
MUTATION 'return _phase_with_zero_tie(self.source_field.data)' -> 'return _phase_with_zero_tie(self.source_field.data) + 0.2'
PYTEST ARGS ["-q", "--tb=line", "-p", "no:cacheprovider", "--basetemp", "C:\\holographiclab\\runs\\m3\\negative-pytest-inconsistent_returned_phase-e281d53f7a744b269ebe2646710f83e7", "tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss"]
FFFFFFFFF                                                                [100%]
================================== FAILURES ===================================
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.14133650141079776+0.14150616018023937j) (ACTUAL), (0.11040624711534748+0.16676468630350022j) (DESIRED)
     [0, 1]: (-0.19965091637944044+0.15046431998600093j) (ACTUAL), (-0.22556383613901887+0.10780053722616527j) (DESIRED)
     [0, 2]: (-0.04820648290793026+0.2961015619777232j) (ACTUAL), (-0.10607186189882412+0.2806220948416514j) (DESIRED)
     [0, 3]: (-0.05430199152776785-0.3457619032168209j) (ACTUAL), (0.015472718919928984-0.34965782555124497j) (DESIRED)
     [0, 4]: (0.12400419533780445-0.38029325465832764j) (ACTUAL), (0.1970849737715246-0.3480768781655534j) (DESIRED)
    Max absolute difference among violations: 0.17970015
    Max relative difference among violations: 0.19966683
     ACTUAL: array([[ 0.141337+0.141506j, -0.199651+0.150464j, -0.048206+0.296102j,
            -0.054302-0.345762j,  0.124004-0.380293j],
           [-0.315293+0.321077j, -0.499726-0.016538j, -0.238013+0.495833j,...
     DESIRED: array([[ 0.110406+0.166765j, -0.225564+0.107801j, -0.106072+0.280622j,
             0.015473-0.349658j,  0.197085-0.348077j],
           [-0.372796+0.252038j, -0.486479-0.115489j, -0.331775+0.438663j,...
C:\holographiclab\tests\test_gerchberg_saxton.py:103: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.14133650141079776+0.14150616018023937j) (ACTUAL), (0.11040624711534748+0.16676468630350022j) (DESIRED)
     [0, 1]: (-0.19965091637944044+0.15046431998600093j) (ACTUAL), (-0.22556383613901887+0.10780053722616527j) (DESIRED)
     [0, 2]: (-0.04820648290793026+0.2961015619777232j) (ACTUAL), (-0.10607186189882412+0.2806220948416514j) (DESIRED)
     [0, 3]: (-0.05430199152776785-0.3457619032168209j) (ACTUAL), (0.015472718919928984-0.34965782555124497j) (DESIRED)
     [0, 4]: (0.12400419533780445-0.38029325465832764j) (ACTUAL), (0.1970849737715246-0.3480768781655534j) (DESIRED)
    Max absolute difference among violations: 0.17970015
    Max relative difference among violations: 0.19966683
     ACTUAL: array([[ 0.141337+0.141506j, -0.199651+0.150464j, -0.048206+0.296102j,
            -0.054302-0.345762j,  0.124004-0.380293j],
           [-0.315293+0.321077j, -0.499726-0.016538j, -0.238013+0.495833j,...
     DESIRED: array([[ 0.110406+0.166765j, -0.225564+0.107801j, -0.106072+0.280622j,
             0.015473-0.349658j,  0.197085-0.348077j],
           [-0.372796+0.252038j, -0.486479-0.115489j, -0.331775+0.438663j,...
C:\holographiclab\tests\test_gerchberg_saxton.py:103: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.14133650141079776+0.14150616018023937j) (ACTUAL), (0.11040624711534748+0.16676468630350022j) (DESIRED)
     [0, 1]: (-0.19965091637944044+0.15046431998600093j) (ACTUAL), (-0.22556383613901887+0.10780053722616527j) (DESIRED)
     [0, 2]: (-0.04820648290793026+0.2961015619777232j) (ACTUAL), (-0.10607186189882412+0.2806220948416514j) (DESIRED)
     [0, 3]: (-0.05430199152776785-0.3457619032168209j) (ACTUAL), (0.015472718919928984-0.34965782555124497j) (DESIRED)
     [0, 4]: (0.12400419533780445-0.38029325465832764j) (ACTUAL), (0.1970849737715246-0.3480768781655534j) (DESIRED)
    Max absolute difference among violations: 0.17970015
    Max relative difference among violations: 0.19966683
     ACTUAL: array([[ 0.141337+0.141506j, -0.199651+0.150464j, -0.048206+0.296102j,
            -0.054302-0.345762j,  0.124004-0.380293j],
           [-0.315293+0.321077j, -0.499726-0.016538j, -0.238013+0.495833j,...
     DESIRED: array([[ 0.110406+0.166765j, -0.225564+0.107801j, -0.106072+0.280622j,
             0.015473-0.349658j,  0.197085-0.348077j],
           [-0.372796+0.252038j, -0.486479-0.115489j, -0.331775+0.438663j,...
C:\holographiclab\tests\test_gerchberg_saxton.py:103: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.1532961741158394+0.12845342736356338j) (ACTUAL), (0.1247207003092147+0.15634815929322307j) (DESIRED)
     [0, 1]: (-0.19428527883865307+0.15733159386018697j) (ACTUAL), (-0.22166947082145386+0.11559691045065443j) (DESIRED)
     [0, 2]: (-0.03135623263668217+0.29835681100795114j) (ACTUAL), (-0.09000554359532514+0.2861800169860049j) (DESIRED)
     [0, 3]: (-0.09754457790963089-0.3361324966742013j) (ACTUAL), (-0.028820962486123633-0.34881134173271006j) (DESIRED)
     [0, 4]: (0.15766507207070599-0.36761627418945847j) (ACTUAL), (0.22755634681202297-0.3289652094455679j) (DESIRED)
    Max absolute difference among violations: 0.17970015
    Max relative difference among violations: 0.19966683
     ACTUAL: array([[ 0.153296+0.128453j, -0.194285+0.157332j, -0.031356+0.298357j,
            -0.097545-0.336132j,  0.157665-0.367616j],
           [-0.320892+0.315482j, -0.497342+0.051483j, -0.318164+0.448633j,...
     DESIRED: array([[ 0.124721+0.156348j, -0.221669+0.115597j, -0.090006+0.28618j ,
            -0.028821-0.348811j,  0.227556-0.328965j],
           [-0.377172+0.245442j, -0.497657-0.04835j , -0.400951+0.376481j,...
C:\holographiclab\tests\test_gerchberg_saxton.py:103: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.014895381784643362+0.1994445476855402j) (ACTUAL), (-0.025025048968095754+0.19842819085035376j) (DESIRED)
     [0, 1]: (-0.1637162700607768+0.1889364520609689j) (ACTUAL), (-0.19798872302914391+0.15264490018762153j) (DESIRED)
     [0, 2]: (-0.08717569531312234+0.28705469539213896j) (ACTUAL), (-0.142466949611599+0.2640135759167815j) (DESIRED)
     [0, 3]: (-0.08643418948978943-0.33915944758659333j) (ACTUAL), (-0.01733067981688822-0.3495706617224685j) (DESIRED)
     [0, 4]: (0.1564978718027719-0.3681146779486023j) (ACTUAL), (0.22651143038106825-0.3296855652083095j) (DESIRED)
    Max absolute difference among violations: 0.17970015
    Max relative difference among violations: 0.19966683
     ACTUAL: array([[ 0.014895+0.199445j, -0.163716+0.188936j, -0.087176+0.287055j,
            -0.086434-0.339159j,  0.156498-0.368115j],
           [-0.396175+0.213413j, -0.496107+0.062275j, -0.42219 +0.352499j,...
     DESIRED: array([[-0.025025+0.198428j, -0.197989+0.152645j, -0.142467+0.264014j,
            -0.017331-0.349571j,  0.226511-0.329686j],
           [-0.430677+0.130451j, -0.49859 -0.037527j, -0.483805+0.261597j,...
C:\holographiclab\tests\test_gerchberg_saxton.py:103: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.14133650141079776+0.1415061601802394j) (ACTUAL), (0.11040624711534748+0.16676468630350022j) (DESIRED)
     [0, 1]: (-0.19965091637944044+0.15046431998600093j) (ACTUAL), (-0.22556383613901887+0.10780053722616527j) (DESIRED)
     [0, 2]: (-0.04820648290793026+0.2961015619777232j) (ACTUAL), (-0.10607186189882412+0.2806220948416514j) (DESIRED)
     [0, 3]: (-0.05430199152776785-0.3457619032168209j) (ACTUAL), (0.015472718919928984-0.34965782555124497j) (DESIRED)
     [0, 4]: (0.12400419533780445-0.38029325465832764j) (ACTUAL), (0.1970849737715246-0.3480768781655534j) (DESIRED)
    Max absolute difference among violations: 0.17970015
    Max relative difference among violations: 0.19966683
     ACTUAL: array([[ 0.141337+0.141506j, -0.199651+0.150464j, -0.048206+0.296102j,
            -0.054302-0.345762j,  0.124004-0.380293j],
           [-0.315293+0.321077j, -0.499726-0.016538j, -0.238013+0.495833j,...
     DESIRED: array([[ 0.110406+0.166765j, -0.225564+0.107801j, -0.106072+0.280622j,
             0.015473-0.349658j,  0.197085-0.348077j],
           [-0.372796+0.252038j, -0.486479-0.115489j, -0.331775+0.438663j,...
C:\holographiclab\tests\test_gerchberg_saxton.py:103: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.15069901398451988+0.13149071139853755j) (ACTUAL), (0.1215718952805438+0.15880892379805517j) (DESIRED)
     [0, 1]: (-0.2079172121263884+0.13881798479156227j) (ACTUAL), (-0.23135158670385966+0.09474409390355955j) (DESIRED)
     [0, 2]: (0.03811106815985593+0.29756939776078256j) (ACTUAL), (-0.021766528968919743+0.29920932174089293j) (DESIRED)
     [0, 3]: (-0.18925529116342268-0.29441880844580576j) (ACTUAL), (-0.1269907979014759-0.32614925609043854j) (DESIRED)
     [0, 4]: (0.18634349879064702-0.35394364022886493j) (ACTUAL), (0.25294678130614945-0.3098675940250271j) (DESIRED)
    Max absolute difference among violations: 0.17970015
    Max relative difference among violations: 0.19966683
     ACTUAL: array([[ 0.150699+0.131491j, -0.207917+0.138818j,  0.038111+0.297569j,
            -0.189255-0.294419j,  0.186343-0.353944j],
           [-0.30782 +0.328249j, -0.49194 +0.089414j, -0.421377+0.35347j ,...
     DESIRED: array([[ 0.121572+0.158809j, -0.231352+0.094744j, -0.021767+0.299209j,
            -0.126991-0.326149j,  0.252947-0.309868j],
           [-0.366897+0.260551j, -0.499898-0.010102j, -0.483202+0.26271j ,...
C:\holographiclab\tests\test_gerchberg_saxton.py:103: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (-0.12010980014875686+0.15991759099056518j) (ACTUAL), (-0.1494863215814415+0.1328677525212565j) (DESIRED)
     [0, 1]: (-0.014241788773050337+0.24959401325461278j) (ACTUAL), (-0.0635445767688888+0.24178934377524333j) (DESIRED)
     [0, 2]: (-0.10445137155707515+0.2812292854235594j) (ACTUAL), (-0.15824093220783844+0.25487213926593527j) (DESIRED)
     [0, 3]: (-0.1029858781776275-0.33450546915705703j) (ACTUAL), (-0.0344770394868019-0.34829776592482686j) (DESIRED)
     [0, 4]: (0.2391789752179576-0.32061412603578093j) (ACTUAL), (0.29810751359641086-0.2667056623646482j) (DESIRED)
    Max absolute difference among violations: 0.17970015
    Max relative difference among violations: 0.19966683
     ACTUAL: array([[-0.12011 +0.159918j, -0.014242+0.249594j, -0.104451+0.281229j,
            -0.102986-0.334505j,  0.239179-0.320614j],
           [-0.445348+0.064537j, -0.467251+0.177979j, -0.509784+0.206447j,...
     DESIRED: array([[-0.149486+0.132868j, -0.063545+0.241789j, -0.158241+0.254872j,
            -0.034477-0.348298j,  0.298108-0.266706j],
           [-0.449292-0.025226j, -0.493296+0.081603j, -0.540637+0.101054j,...
C:\holographiclab\tests\test_gerchberg_saxton.py:103: AssertionError:
E   AssertionError: 
    Not equal to tolerance rtol=1e-12, atol=9e-14
    
    Mismatched elements: 15 / 15 (100%)
    First 5 mismatches are at indices:
     [0, 0]: (0.14133650141079776+0.1415061601802394j) (ACTUAL), (0.11040624711534748+0.16676468630350022j) (DESIRED)
     [0, 1]: (-0.19965091637944044+0.15046431998600093j) (ACTUAL), (-0.22556383613901887+0.10780053722616527j) (DESIRED)
     [0, 2]: (-0.04820648290793026+0.2961015619777232j) (ACTUAL), (-0.10607186189882412+0.2806220948416514j) (DESIRED)
     [0, 3]: (-0.05430199152776785-0.3457619032168209j) (ACTUAL), (0.015472718919928984-0.34965782555124497j) (DESIRED)
     [0, 4]: (0.12400419533780445-0.38029325465832764j) (ACTUAL), (0.1970849737715246-0.3480768781655534j) (DESIRED)
    Max absolute difference among violations: 0.17970015
    Max relative difference among violations: 0.19966683
     ACTUAL: array([[ 0.141337+0.141506j, -0.199651+0.150464j, -0.048206+0.296102j,
            -0.054302-0.345762j,  0.124004-0.380293j],
           [-0.315293+0.321077j, -0.499726-0.016538j, -0.238013+0.495833j,...
     DESIRED: array([[ 0.110406+0.166765j, -0.225564+0.107801j, -0.106072+0.280622j,
             0.015473-0.349658j,  0.197085-0.348077j],
           [-0.372796+0.252038j, -0.486479-0.115489j, -0.331775+0.438663j,...
C:\holographiclab\tests\test_gerchberg_saxton.py:103: AssertionError:
=========================== short test summary info ===========================
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[0-0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[0--0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[0-0.0]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[1-0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[1--0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[1-0.0]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[4-0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[4--0.0002]
FAILED tests/test_gerchberg_saxton.py::test_gs_returned_phase_rebuilds_actual_reconstruction_and_loss[4-0.0]
9 failed in 0.19s
NEGATIVE CONTROL VERIFIED: True; pytest exit=1; assertion call failures=9; other failures=0
SOURCE/TEST HASHES UNCHANGED: True; files=27
DRIVER CHILD EXIT: 0
ALL SEVEN MUTATIONS VERIFIED: True
~~~

## Full suite after negative controls

Command, exit 0:

~~~powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --basetemp .pytest_cache/m3-final-20260916-a
~~~

Exact output:

~~~text
........................................................................ [ 10%]
........................................................................ [ 21%]
........................................................................ [ 32%]
........................................................................ [ 43%]
........................................................................ [ 53%]
........................................................................ [ 64%]
........................................................................ [ 75%]
........................................................................ [ 86%]
........................................................................ [ 97%]
....................                                                     [100%]
668 passed in 4.00s
~~~

| Coverage | Cases |
|---|---:|
| Accepted baseline, existing tests unchanged | 491 |
| New public contract/operator/fixture/PNG cases, `test_gerchberg_saxton.py` | 160 |
| New independent complete-cycle/fixed-point/analytic cases, `test_gerchberg_saxton_reference.py` | 17 |
| New cases | 177 |
| Total | 668 |

Counts were also checked by pytest collection after the final run. There was
no test-count quota. Existing architecture and RNG guards scanned the new
algorithm source without changes. Development-focused runs progressed from
160 passing cases to 168, then 177 after phase/result, cutoff-rejection and
exact-grazing regressions; the final full suite includes all of them.

## Current fixture, PNG and analytic phase-sampling evidence

Command, exit 0:

~~~powershell
.\.venv\Scripts\python.exe -B scripts\probe_m3_evidence.py
~~~

The committed script preserves the exact original fixture definitions and
prints every raw history value, not only selected iterations. All twelve
cases pass both predeclared improvement criteria. Rebuilding each source
from the returned phase, propagating with the public pad_factor=1 ASM and
recomputing the final residual checks the actual returned field.

The PNG route is exercised independently for all three fixtures at seed zero:
synthetic design -> uint8 codes -> PNG -> M2 decoder -> M3. Decoded intensities,
amplitudes and deterministic solver results match the quantized array route
exactly. Continuous prequantization targets differ; the records state their
intensity/amplitude/power/reconstruction differences and separate outcomes.
They are not replacement acceptance fixtures.

For phase sampling, the script uses strictly increasing `fx_centered` along
axis 1 (columns, x) and `fy_centered` along axis 0 (rows, y). It forms the
analytic unwrapped `Theta=2*pi*sqrt(1/lambda**2-fx**2-fy**2)*z` on that sorted
mesh and computes `max(abs(diff(Theta,axis=1)))` and the axis-0 counterpart.
Only adjacent physical samples are compared; endpoints are not joined. No
`unwrap(angle(H))` is used. Results concern these tested discrete periodic
configurations, not general sampling adequacy or isolated free-space accuracy.

Exact canonical full-probe output, including all 51-entry histories,
performance batches and separate memory processes:

~~~text
{"record": "environment", "python": "3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]", "executable": "C:\\holographiclab\\.venv\\Scripts\\python.exe", "numpy": "2.4.6", "scipy": "1.17.1", "pillow": "12.3.0", "platform": "Windows-10-10.0.26100-SP0", "processor": "Intel64 Family 6 Model 198 Stepping 2, GenuineIntel", "logical_cpu_count": 24, "predeclared_seeds": [0, 1, 2, 3], "iterations": 50, "cases": [["smooth_spot_64", 64, 64, 8e-06, 8e-06, "spot"], ["two_features_64", 64, 64, 8e-06, 8e-06, "two"], ["two_features_rect", 48, 64, 1e-05, 8e-06, "two"]], "residual_definition": "sum((abs(Pz(U_k))-A_target)**2)/sum(A_target**2), complete grid, k=0..N", "comparison_tolerances": {"rtol": 1e-12, "atol": 1e-14}, "measurements": "Current shipped solver; historical planning measurements remain separately identified."}
{"record": "geometry", "case": "smooth_spot_64", "shape": [64, 64], "dx_m": 8e-06, "dy_m": 8e-06, "wavelength_m": 6.33e-07, "distance_m": 0.005, "frequency_order": "ascending physical cycles/m; fx axis 1, fy axis 0", "phase_calculation": "Theta=(2*pi*sqrt(1/lambda**2-fx**2-fy**2))*z; diff on adjacent sorted samples, never unwrap(angle(H))", "fx_range_cycles_per_m": [-62500.0, 60546.875], "fy_range_cycles_per_m": [-62500.0, 60546.875], "dfx_cycles_per_m": 1953.125, "dfy_cycles_per_m": 1953.125, "evanescent_samples": 0, "max_adjacent_theta_step_x_rad": 2.393285706457391, "max_adjacent_theta_step_y_rad": 2.393285706457391, "max_derivative_bin_phase_x_rad": 2.4313330813134106, "max_derivative_bin_phase_y_rad": 2.4313330813134106, "source_amplitude": 0.2934627167379122, "target_power_au_m2": 2.257593725490196e-08, "source_power_au_m2": 2.2575937254901972e-08, "relative_power_mismatch": 4.834322623263567e-16, "target_intensity_range": [0.0, 1.0], "limitation": "Evidence for these periodic discrete configurations, not a general sampling or isolated-aperture guarantee."}
{"record": "shipped_solve", "case": "smooth_spot_64", "seed": 0, "iterations": 50, "elapsed_s": 0.046043200010899454, "residual_initial": 0.9910541811762894, "residual_30": 0.02098299396074039, "residual_final": 0.017125299052456723, "residual_min": 0.017125299052456723, "residual_max": 0.9910541811762894, "residual_final_over_initial": 0.01727988174383219, "positive_steps_above_1e_minus_14": 0, "raw_residual_history": [0.9910541811762894, 0.1437679962956028, 0.0900064975675525, 0.07158851960354001, 0.06073872617008647, 0.05314435689991588, 0.04769892053582202, 0.04357916064078261, 0.04029484768657584, 0.03761633094706487, 0.03538025505409393, 0.03351356412735434, 0.031956632470481444, 0.030644225541849642, 0.029525075144618766, 0.02855881691568828, 0.027718906177233552, 0.02698706458690125, 0.026342183227687527, 0.025761147395421118, 0.025226923827462958, 0.024727838028144777, 0.024255225917780024, 0.02380224326208477, 0.02336280445931128, 0.022932060724870165, 0.022508637314047574, 0.022096166579815103, 0.02170130905711262, 0.021329707231235794, 0.02098299396074039, 0.020658606105831364, 0.020353109531579188, 0.020066004303078606, 0.019798104688804587, 0.019548279773577183, 0.01931360722972629, 0.019093432469206924, 0.018888822455564978, 0.018698548298226716, 0.018520261493543966, 0.018351932537638414, 0.018192428264639335, 0.018041193892909122, 0.017897466926766175, 0.01776004326787646, 0.017627545867884495, 0.017498711215387014, 0.017372524117898212, 0.01724823193198827, 0.017125299052456723], "independent_final_residual": 0.017125299052456723, "max_source_amplitude_error": 5.551115123125783e-17, "max_relative_source_amplitude_error": 1.8915912674806364e-16, "relative_reconstruction_power_error": 0.0, "reforward_phase_max_complex_error": 3.510833468576701e-16, "reconstruction_intensity_range": [3.432465455912773e-06, 1.0513181064993404], "acceptance": "rho50 < 0.05 and rho50 < 0.1*rho0; only these declared fixtures/seeds"}
{"record": "shipped_solve", "case": "smooth_spot_64", "seed": 1, "iterations": 50, "elapsed_s": 0.02531889994861558, "residual_initial": 0.9976028872437503, "residual_30": 0.01957804028761438, "residual_final": 0.01669478454111809, "residual_min": 0.01669478454111809, "residual_max": 0.9976028872437503, "residual_final_over_initial": 0.01673489998334272, "positive_steps_above_1e_minus_14": 0, "raw_residual_history": [0.9976028872437503, 0.15958692447274028, 0.09446830680531808, 0.07101193141161796, 0.05768768973431525, 0.04911554331043986, 0.04323165420872556, 0.03903683781847888, 0.03590808623453255, 0.033474318156816396, 0.031463059407671, 0.029778628491445157, 0.028377086145151026, 0.027212793676130612, 0.026230895582872858, 0.025391828639647583, 0.024666601450032678, 0.02403060130897616, 0.023464205405295775, 0.02295207472050284, 0.022484054744791857, 0.0220547506146321, 0.02166215261506861, 0.02130571354509917, 0.020984280505868896, 0.020695237012053173, 0.02043458059059066, 0.020197428754923447, 0.019978648457125457, 0.019773472531278667, 0.01957804028761438, 0.019389596614418133, 0.01920634822467759, 0.01902741891767553, 0.018852853159286802, 0.018683275441732088, 0.01851935031777434, 0.018361420874737546, 0.018209424442917673, 0.01806299524553221, 0.017921638510981656, 0.01778487469782996, 0.01765229272118463, 0.017523519312775047, 0.017398157020725013, 0.017275747283958465, 0.01715579935478807, 0.017037887181773292, 0.01692175652735401, 0.016807358648597632, 0.01669478454111809], "independent_final_residual": 0.01669478454111809, "max_source_amplitude_error": 1.1102230246251565e-16, "max_relative_source_amplitude_error": 3.783182534961273e-16, "relative_reconstruction_power_error": 1.465596937506406e-16, "reforward_phase_max_complex_error": 3.554447978966673e-16, "reconstruction_intensity_range": [2.822601864182322e-07, 1.021788758276366], "acceptance": "rho50 < 0.05 and rho50 < 0.1*rho0; only these declared fixtures/seeds"}
{"record": "shipped_solve", "case": "smooth_spot_64", "seed": 2, "iterations": 50, "elapsed_s": 0.026958199974615127, "residual_initial": 0.9996235768274039, "residual_30": 0.017968888732406294, "residual_final": 0.014344758005132971, "residual_min": 0.014344758005132971, "residual_max": 0.9996235768274039, "residual_final_over_initial": 0.01435015973778873, "positive_steps_above_1e_minus_14": 0, "raw_residual_history": [0.9996235768274039, 0.1588465765996683, 0.09307683977490533, 0.06991251027032165, 0.05751851806531702, 0.05011367856072277, 0.04503528838506469, 0.04130791698644476, 0.0384251459087212, 0.03608144005013227, 0.03410705692091466, 0.03239493289919687, 0.030870593036391558, 0.02949444265813888, 0.0282454409212084, 0.02710252195585538, 0.026050403480382973, 0.025084630325966487, 0.02420122937351457, 0.02339310601414233, 0.022655322595330332, 0.02198477482380041, 0.02137941771922646, 0.02083601088358126, 0.020345462593807172, 0.019893005558635893, 0.019464146050866743, 0.019056068826074968, 0.01867078352289575, 0.018307996008257978, 0.017968888732406294, 0.017654882188295952, 0.01736536079147016, 0.01709745863665426, 0.01684792479677787, 0.016614385972800204, 0.016394426602939133, 0.01618580233772401, 0.01598845359205129, 0.015802562960447814, 0.015628541766340997, 0.015466262556469752, 0.015314244171432415, 0.015170821679926574, 0.015034641711546021, 0.014904823670227177, 0.01478100827710135, 0.014663182395701128, 0.014551360800652426, 0.014445359244457941, 0.014344758005132971], "independent_final_residual": 0.014344758005132971, "max_source_amplitude_error": 5.551115123125783e-17, "max_relative_source_amplitude_error": 1.8915912674806364e-16, "relative_reconstruction_power_error": 1.465596937506406e-16, "reforward_phase_max_complex_error": 3.510833468576701e-16, "reconstruction_intensity_range": [5.056126595495403e-07, 1.0460706929311085], "acceptance": "rho50 < 0.05 and rho50 < 0.1*rho0; only these declared fixtures/seeds"}
{"record": "shipped_solve", "case": "smooth_spot_64", "seed": 3, "iterations": 50, "elapsed_s": 0.026639799994882196, "residual_initial": 1.003722437198692, "residual_30": 0.019775021033596095, "residual_final": 0.015919803568154665, "residual_min": 0.015919803568154665, "residual_max": 1.003722437198692, "residual_final_over_initial": 0.01586076287443125, "positive_steps_above_1e_minus_14": 0, "raw_residual_history": [1.003722437198692, 0.16038608031766122, 0.09626859762470029, 0.07315754846502083, 0.06093396459714222, 0.05315682432775263, 0.04763714606276127, 0.04357628861164635, 0.04042289806051953, 0.03789424277996774, 0.03580961435206651, 0.03402471129431181, 0.032451427585671336, 0.031051782563609336, 0.029810829406432947, 0.02871440364005181, 0.02773739264778572, 0.02684617973419694, 0.026015201891157982, 0.025243039928897683, 0.02453580127272249, 0.02389127492776127, 0.023301540450333624, 0.022757584388095446, 0.02225245655746101, 0.021781709435845467, 0.021340867211446804, 0.02092370889027742, 0.02052433175473131, 0.02014073159335052, 0.019775021033596095, 0.019430337968063986, 0.01910860552188873, 0.0188099190090983, 0.018533259966451627, 0.018277359887664768, 0.018040723938757195, 0.017821521390979644, 0.017617185408230367, 0.01742496254677142, 0.01724480340358885, 0.017077891366242288, 0.016923390007591486, 0.01677922618781609, 0.016643019512458158, 0.016512508022910738, 0.016385974429480556, 0.016262706173949967, 0.016143150760620683, 0.016028476981883578, 0.015919803568154665], "independent_final_residual": 0.015919803568154665, "max_source_amplitude_error": 5.551115123125783e-17, "max_relative_source_amplitude_error": 1.8915912674806364e-16, "relative_reconstruction_power_error": 1.465596937506406e-16, "reforward_phase_max_complex_error": 4.47545209131181e-16, "reconstruction_intensity_range": [2.3679699301519556e-07, 1.094521707958609], "acceptance": "rho50 < 0.05 and rho50 < 0.1*rho0; only these declared fixtures/seeds"}
{"record": "png_and_quantization", "case": "smooth_spot_64", "seed": 0, "png_vs_array_intensity_max_error": 0.0, "png_vs_array_source_max_error": 0.0, "png_vs_array_history_max_error": 0.0, "continuous_vs_decoded_intensity_max_error": 0.0019597838818094238, "continuous_vs_decoded_amplitude_max_error": 0.04337908884761734, "continuous_power_au_m2": 2.26185441986991e-08, "decoded_power_au_m2": 2.257593725490196e-08, "continuous_final_residual": 0.013530212963340673, "decoded_final_residual": 0.017125299052456723, "continuous_vs_decoded_final_intensity_max_difference": 0.17619023267460532, "planning_source_amplitude": 0.2934627167379122, "demo_source_amplitude": 0.2934627167379122, "demo_minus_planning_amplitude": 0.0, "demo_minus_planning_amplitude_ulps": 0.0, "interpretation": "PNG matches uint8-array route exactly. Continuous design is a different target; its solve is separate evidence, not a replacement acceptance fixture."}
{"record": "geometry", "case": "two_features_64", "shape": [64, 64], "dx_m": 8e-06, "dy_m": 8e-06, "wavelength_m": 6.33e-07, "distance_m": 0.005, "frequency_order": "ascending physical cycles/m; fx axis 1, fy axis 0", "phase_calculation": "Theta=(2*pi*sqrt(1/lambda**2-fx**2-fy**2))*z; diff on adjacent sorted samples, never unwrap(angle(H))", "fx_range_cycles_per_m": [-62500.0, 60546.875], "fy_range_cycles_per_m": [-62500.0, 60546.875], "dfx_cycles_per_m": 1953.125, "dfy_cycles_per_m": 1953.125, "evanescent_samples": 0, "max_adjacent_theta_step_x_rad": 2.393285706457391, "max_adjacent_theta_step_y_rad": 2.393285706457391, "max_derivative_bin_phase_x_rad": 2.4313330813134106, "max_derivative_bin_phase_y_rad": 2.4313330813134106, "source_amplitude": 0.17110175886663148, "target_power_au_m2": 7.674478431372549e-09, "source_power_au_m2": 7.674478431372552e-09, "relative_power_mismatch": 3.555269755095013e-16, "target_intensity_range": [0.0, 0.6509803921568628], "limitation": "Evidence for these periodic discrete configurations, not a general sampling or isolated-aperture guarantee."}
{"record": "shipped_solve", "case": "two_features_64", "seed": 0, "iterations": 50, "elapsed_s": 0.029459300043527037, "residual_initial": 1.219365444359764, "residual_30": 0.04149576258671334, "residual_final": 0.03611691872197391, "residual_min": 0.03611691872197391, "residual_max": 1.219365444359764, "residual_final_over_initial": 0.029619437625557236, "positive_steps_above_1e_minus_14": 0, "raw_residual_history": [1.219365444359764, 0.17440747728957523, 0.11796601524061053, 0.09720452973519478, 0.08577473570818826, 0.07834149453280999, 0.0729117470139922, 0.06871400125485062, 0.06527585843481212, 0.062402598540724254, 0.059898768699096064, 0.057753858995881854, 0.0559246721315273, 0.05432389941732325, 0.05290887382355787, 0.0516401547473206, 0.0504768030003294, 0.049395457623529905, 0.04839846194209394, 0.04750095018140438, 0.046697852807209374, 0.04596941019557415, 0.04530101110337143, 0.044682905914508735, 0.044110667704473305, 0.04358753671913964, 0.043110326287894414, 0.042670391653321434, 0.04225940303243157, 0.04187033304196576, 0.04149576258671334, 0.04112524757050638, 0.040748254587064436, 0.0403635386022022, 0.039983275217412934, 0.03962255546057595, 0.03928928177359293, 0.038984961944461986, 0.038706142268297244, 0.038446656904114765, 0.03820028059638582, 0.03796236621312903, 0.037730467755579, 0.03750420785259145, 0.03728451857593522, 0.03707257943728138, 0.036868948088598946, 0.036673175262664115, 0.036483878468740766, 0.03629911714965702, 0.03611691872197391], "independent_final_residual": 0.03611691872197391, "max_source_amplitude_error": 5.551115123125783e-17, "max_relative_source_amplitude_error": 3.2443355111578397e-16, "relative_reconstruction_power_error": 2.1556660037549665e-16, "reforward_phase_max_complex_error": 2.237726045655905e-16, "reconstruction_intensity_range": [8.488604428927762e-09, 0.6653453232207227], "acceptance": "rho50 < 0.05 and rho50 < 0.1*rho0; only these declared fixtures/seeds"}
{"record": "shipped_solve", "case": "two_features_64", "seed": 1, "iterations": 50, "elapsed_s": 0.02450850000604987, "residual_initial": 1.205476068810247, "residual_30": 0.040460156812121506, "residual_final": 0.036612380296920814, "residual_min": 0.036612380296920814, "residual_max": 1.205476068810247, "residual_final_over_initial": 0.030371718895303875, "positive_steps_above_1e_minus_14": 0, "raw_residual_history": [1.205476068810247, 0.1708011300664939, 0.11527465177272299, 0.09553874344818042, 0.08495225709091292, 0.07745507345626648, 0.07183368343045189, 0.06743297823594266, 0.0637387038303677, 0.06054254957090722, 0.057951835540660426, 0.055784329937458195, 0.05396226657013143, 0.05242012816700615, 0.05109059233237359, 0.049895331977515216, 0.04877798989685935, 0.04773731947659118, 0.04678555064234414, 0.04592708614235103, 0.04515526140049604, 0.044459933629500806, 0.043833395154194967, 0.04327088819377576, 0.04276639139782062, 0.04230958449807757, 0.04188812613422861, 0.04149230963835263, 0.04111992394352392, 0.04077513427850747, 0.040460156812121506, 0.040172445998832275, 0.039907817707355416, 0.03966256840002284, 0.03943377871052277, 0.03921895615705689, 0.03901575204784661, 0.03882199836216538, 0.0386359011278598, 0.03845612691930308, 0.03828164942191179, 0.03811142832702587, 0.03794416914371743, 0.03777842590497367, 0.03761308603321662, 0.03744778972624151, 0.03728267867782121, 0.03711768704061644, 0.0369520745253747, 0.03678434566306311, 0.036612380296920814], "independent_final_residual": 0.036612380296920814, "max_source_amplitude_error": 5.551115123125783e-17, "max_relative_source_amplitude_error": 3.2443355111578397e-16, "relative_reconstruction_power_error": 0.0, "reforward_phase_max_complex_error": 2.2887833992611187e-16, "reconstruction_intensity_range": [5.003198994220744e-07, 0.6708103341884275], "acceptance": "rho50 < 0.05 and rho50 < 0.1*rho0; only these declared fixtures/seeds"}
{"record": "shipped_solve", "case": "two_features_64", "seed": 2, "iterations": 50, "elapsed_s": 0.029348100011702627, "residual_initial": 1.2125652885224496, "residual_30": 0.04277413298193753, "residual_final": 0.03894152258585046, "residual_min": 0.03894152258585046, "residual_max": 1.2125652885224496, "residual_final_over_initial": 0.032114990388106834, "positive_steps_above_1e_minus_14": 0, "raw_residual_history": [1.2125652885224496, 0.18007444069517217, 0.12089278711064645, 0.09977957337328128, 0.08728812005959655, 0.07921634110000159, 0.07367370154269365, 0.06927913155879596, 0.06554222079016665, 0.06235686589366325, 0.059716956793683745, 0.05761357857325359, 0.055942128658400606, 0.054564787895141145, 0.05337073474760563, 0.05229126227228802, 0.051278723220088106, 0.05030130864016979, 0.04936208738479424, 0.04848145016827629, 0.0476808388452593, 0.04696704852910779, 0.04633295580325462, 0.0457666278004286, 0.04525462303617061, 0.04478334344452497, 0.044340840264319316, 0.0439192459355503, 0.04351655590528796, 0.043133866247206984, 0.04277413298193753, 0.04244303270687281, 0.04214217561950836, 0.04186947842401527, 0.04162245060536183, 0.041399042460499025, 0.041197283064546474, 0.0410146701644348, 0.04084796816593513, 0.04069341372400237, 0.0405468936994629, 0.04040389919465173, 0.04025948816108846, 0.040108792351072085, 0.03994849647826675, 0.03977864000083319, 0.03960292105325673, 0.03942690819185339, 0.039255837527385234, 0.03909341015940312, 0.03894152258585046], "independent_final_residual": 0.03894152258585046, "max_source_amplitude_error": 5.551115123125783e-17, "max_relative_source_amplitude_error": 3.2443355111578397e-16, "relative_reconstruction_power_error": 0.0, "reforward_phase_max_complex_error": 2.3263411494723067e-16, "reconstruction_intensity_range": [8.516960492184987e-08, 0.6964975026016038], "acceptance": "rho50 < 0.05 and rho50 < 0.1*rho0; only these declared fixtures/seeds"}
{"record": "shipped_solve", "case": "two_features_64", "seed": 3, "iterations": 50, "elapsed_s": 0.024580300028901547, "residual_initial": 1.2105930187246314, "residual_30": 0.03903763680100714, "residual_final": 0.03415165073458957, "residual_min": 0.03415165073458957, "residual_max": 1.2105930187246314, "residual_final_over_initial": 0.028210678738729702, "positive_steps_above_1e_minus_14": 0, "raw_residual_history": [1.2105930187246314, 0.17235022302356906, 0.11402818202653488, 0.09337149379781731, 0.08218698670377547, 0.07464714704794517, 0.06881781260744683, 0.06428175392334569, 0.0607864406116056, 0.0579739709713097, 0.05557203161877278, 0.05340899896132463, 0.051515447088157744, 0.04990408512344128, 0.04848373922921775, 0.04729666776003474, 0.046332474972557706, 0.04553626020306622, 0.044852480566385675, 0.04423712061081583, 0.04365892484483806, 0.04309883211844356, 0.042552108142197634, 0.04202508155108485, 0.04152370939867765, 0.041048850823348866, 0.040601050927107855, 0.04018082432486376, 0.039784468131155604, 0.039405336625206226, 0.03903763680100714, 0.03867796670406669, 0.038324892032090815, 0.03797857394908521, 0.03764159209529309, 0.03731894412238542, 0.037015434668534804, 0.036732928814035705, 0.03647001289976811, 0.036223530905250115, 0.035990235553312974, 0.03576765894225327, 0.035554319444365975, 0.03534962137277972, 0.03515360446083662, 0.03496655710452126, 0.03478856490274994, 0.034619164651864064, 0.03445729200593646, 0.034301688863722146, 0.03415165073458957], "independent_final_residual": 0.03415165073458956, "max_source_amplitude_error": 5.551115123125783e-17, "max_relative_source_amplitude_error": 3.2443355111578397e-16, "relative_reconstruction_power_error": 0.0, "reforward_phase_max_complex_error": 2.482534153247273e-16, "reconstruction_intensity_range": [1.569670281453768e-07, 0.6399806910324948], "acceptance": "rho50 < 0.05 and rho50 < 0.1*rho0; only these declared fixtures/seeds"}
{"record": "png_and_quantization", "case": "two_features_64", "seed": 0, "png_vs_array_intensity_max_error": 0.0, "png_vs_array_source_max_error": 0.0, "png_vs_array_history_max_error": 0.0, "continuous_vs_decoded_intensity_max_error": 0.0019567813270121026, "continuous_vs_decoded_amplitude_max_error": 0.044112307314132425, "continuous_power_au_m2": 7.690610403827597e-09, "decoded_power_au_m2": 7.674478431372549e-09, "continuous_final_residual": 0.030479387367240575, "decoded_final_residual": 0.03611691872197391, "continuous_vs_decoded_final_intensity_max_difference": 0.09871382040997284, "planning_source_amplitude": 0.17110175886663148, "demo_source_amplitude": 0.17110175886663148, "demo_minus_planning_amplitude": 0.0, "demo_minus_planning_amplitude_ulps": 0.0, "interpretation": "PNG matches uint8-array route exactly. Continuous design is a different target; its solve is separate evidence, not a replacement acceptance fixture."}
{"record": "geometry", "case": "two_features_rect", "shape": [48, 64], "dx_m": 8e-06, "dy_m": 1e-05, "wavelength_m": 6.33e-07, "distance_m": 0.005, "frequency_order": "ascending physical cycles/m; fx axis 1, fy axis 0", "phase_calculation": "Theta=(2*pi*sqrt(1/lambda**2-fx**2-fy**2))*z; diff on adjacent sorted samples, never unwrap(angle(H))", "fx_range_cycles_per_m": [-62500.0, 60546.875], "fy_range_cycles_per_m": [-49999.99999999999, 47916.66666666666], "dfx_cycles_per_m": 1953.125, "dfy_cycles_per_m": 2083.333333333333, "evanescent_samples": 0, "max_adjacent_theta_step_x_rad": 2.3926096373106702, "max_adjacent_theta_step_y_rad": 2.030898355813406, "max_derivative_bin_phase_x_rad": 2.4306462311638377, "max_derivative_bin_phase_y_rad": 2.0741514505931407, "source_amplitude": 0.17672252747085265, "target_power_au_m2": 7.67529411764706e-09, "source_power_au_m2": 7.67529411764706e-09, "relative_power_mismatch": 0.0, "target_intensity_range": [0.0, 0.6509803921568628], "limitation": "Evidence for these periodic discrete configurations, not a general sampling or isolated-aperture guarantee."}
{"record": "shipped_solve", "case": "two_features_rect", "seed": 0, "iterations": 50, "elapsed_s": 0.020898599992506206, "residual_initial": 1.192628191648109, "residual_30": 0.04202642694611501, "residual_final": 0.03765171966877544, "residual_min": 0.03765171966877544, "residual_max": 1.192628191648109, "residual_final_over_initial": 0.031570375354572175, "positive_steps_above_1e_minus_14": 0, "raw_residual_history": [1.192628191648109, 0.19373761780068588, 0.1258083258669411, 0.10088616305071367, 0.08733523078819795, 0.07884332768680116, 0.07281470136937418, 0.06802071290861372, 0.06420739600378621, 0.06120354230737914, 0.05875080718009737, 0.05663998425818795, 0.05481595364033492, 0.05327789585138887, 0.05197285109275072, 0.05084815949260302, 0.04985084172793982, 0.04893497299855716, 0.04806709231326071, 0.04723912666363544, 0.04646657777987901, 0.04576396339640676, 0.04513400311122879, 0.04457405780693919, 0.044079943273145995, 0.04364460385009091, 0.043258222670039086, 0.04291039928646907, 0.04259227687880072, 0.04229835666355277, 0.04202642694611501, 0.041773970297739355, 0.0415347255487743, 0.04129932869663253, 0.04106123221413028, 0.04082388795073777, 0.04059607651877043, 0.04038111760501434, 0.04017681030349947, 0.03997967689924685, 0.03978667494849868, 0.039595304469844377, 0.03940335583950882, 0.039208697446133894, 0.03900924919641358, 0.0388031852247038, 0.03858924674175837, 0.03836689350432825, 0.03813602529747214, 0.037896718928524926, 0.03765171966877544], "independent_final_residual": 0.03765171966877544, "max_source_amplitude_error": 5.551115123125783e-17, "max_relative_source_amplitude_error": 3.1411474261770867e-16, "relative_reconstruction_power_error": 0.0, "reforward_phase_max_complex_error": 3.3306690738754696e-16, "reconstruction_intensity_range": [6.844897007409594e-07, 0.6697157982624318], "acceptance": "rho50 < 0.05 and rho50 < 0.1*rho0; only these declared fixtures/seeds"}
{"record": "shipped_solve", "case": "two_features_rect", "seed": 1, "iterations": 50, "elapsed_s": 0.021796800021547824, "residual_initial": 1.1840781177155155, "residual_30": 0.041549222939937396, "residual_final": 0.036637075285440794, "residual_min": 0.036637075285440794, "residual_max": 1.1840781177155155, "residual_final_over_initial": 0.0309414343000663, "positive_steps_above_1e_minus_14": 0, "raw_residual_history": [1.1840781177155155, 0.1932416408498257, 0.12305457376474742, 0.0975029066614517, 0.08458934855235015, 0.07683364065077959, 0.07154194165948193, 0.06766673939989383, 0.06451325480086127, 0.061759054446938064, 0.05927884798367679, 0.05705881200208716, 0.05511310223571308, 0.05339097690637448, 0.051843752820010545, 0.050469547304442926, 0.049279398676472054, 0.048258961530516786, 0.04737776882808625, 0.0466069013335542, 0.04592307388409116, 0.045303844856935935, 0.04473303987112275, 0.04420340393656819, 0.04371386909913804, 0.043264934110397966, 0.04285560627468674, 0.04248331257128539, 0.04214448133048168, 0.04183476758472509, 0.041549222939937396, 0.041282493812407006, 0.04102906502904826, 0.04078353736918057, 0.04054111913327251, 0.04029810881369613, 0.0400517482865496, 0.03980023120446378, 0.03954313917776162, 0.03928027533089106, 0.03900942166783723, 0.03872676488058849, 0.03843244341102538, 0.03813682430243697, 0.03785552685662244, 0.03759789104086513, 0.037365054357073664, 0.03715467853299394, 0.03696427147120292, 0.03679212776906246, 0.036637075285440794], "independent_final_residual": 0.036637075285440794, "max_source_amplitude_error": 5.551115123125783e-17, "max_relative_source_amplitude_error": 3.1411474261770867e-16, "relative_reconstruction_power_error": 0.0, "reforward_phase_max_complex_error": 2.2887833992611187e-16, "reconstruction_intensity_range": [3.025884416965968e-07, 0.6264206079795192], "acceptance": "rho50 < 0.05 and rho50 < 0.1*rho0; only these declared fixtures/seeds"}
{"record": "shipped_solve", "case": "two_features_rect", "seed": 2, "iterations": 50, "elapsed_s": 0.021002800029236823, "residual_initial": 1.1842858363557385, "residual_30": 0.03893577610890519, "residual_final": 0.03467224833685901, "residual_min": 0.03467224833685901, "residual_max": 1.1842858363557385, "residual_final_over_initial": 0.02927692561413365, "positive_steps_above_1e_minus_14": 0, "raw_residual_history": [1.1842858363557385, 0.19580404340808577, 0.12378630162810564, 0.09984978455884637, 0.08769865154419353, 0.07987435040909399, 0.07359620818103815, 0.06837656745593262, 0.06418876384425225, 0.060913728185322605, 0.058394796250248, 0.0563963217714531, 0.05468886297311881, 0.053133736710188784, 0.05169221529369678, 0.05034923945826732, 0.049079681150430356, 0.04786874027229081, 0.04673056586552741, 0.045691107261398814, 0.04474926875037302, 0.04387674857353583, 0.04305257990034014, 0.04228921653075803, 0.0416058775128147, 0.04100723951414347, 0.040487653700128315, 0.040034733306634415, 0.039633442589604585, 0.03927037426313949, 0.03893577610890519, 0.03862361651041149, 0.03833064045935619, 0.03805508281828376, 0.0377956183280853, 0.03755076277895281, 0.03731868164285955, 0.03709735371984627, 0.036884910366790404, 0.03667989275307144, 0.03648128421841204, 0.03628833160477334, 0.03610025309896882, 0.03591600214645315, 0.03573438528476171, 0.035554679267836044, 0.03537699064051576, 0.035201427500525996, 0.03502695862521994, 0.03485132760350421, 0.03467224833685901], "independent_final_residual": 0.03467224833685901, "max_source_amplitude_error": 5.551115123125783e-17, "max_relative_source_amplitude_error": 3.1411474261770867e-16, "relative_reconstruction_power_error": 0.0, "reforward_phase_max_complex_error": 3.376611507232129e-16, "reconstruction_intensity_range": [2.366582611412551e-07, 0.6429743709198817], "acceptance": "rho50 < 0.05 and rho50 < 0.1*rho0; only these declared fixtures/seeds"}
{"record": "shipped_solve", "case": "two_features_rect", "seed": 3, "iterations": 50, "elapsed_s": 0.02276950003579259, "residual_initial": 1.1568588931942665, "residual_30": 0.03890301953338171, "residual_final": 0.031786333196884356, "residual_min": 0.031786333196884356, "residual_max": 1.1568588931942665, "residual_final_over_initial": 0.027476413401739404, "positive_steps_above_1e_minus_14": 0, "raw_residual_history": [1.1568588931942665, 0.192102164196181, 0.12787136005832506, 0.10515968998874806, 0.09127744646419374, 0.08140889830155429, 0.07389947079585589, 0.06792054632933617, 0.06312355924271644, 0.05934566337256023, 0.05627912299179451, 0.05372873501464121, 0.0516179263047198, 0.04989228667419237, 0.04848630019761894, 0.04733754873303556, 0.046386067400944295, 0.045577232653864805, 0.04486839784183234, 0.044229631011488905, 0.04364184295348695, 0.04309383797740355, 0.042578981123751206, 0.04209251697405995, 0.041629927934591235, 0.041186609703602, 0.04075854913687267, 0.04033839915030979, 0.03988328081012062, 0.039390582587320054, 0.03890301953338171, 0.03843310061317827, 0.03799100445879722, 0.03757250525671972, 0.03716452707426889, 0.036760786005896474, 0.03636277314772007, 0.03597187119239331, 0.0355847981256494, 0.0351942496990459, 0.034793695431001845, 0.034387117577586994, 0.033991861728649354, 0.033625182499621944, 0.03329379613137853, 0.03299570956595512, 0.03272502764262729, 0.03247472827872159, 0.03223780265998263, 0.0320088133201456, 0.031786333196884356], "independent_final_residual": 0.03178633319688436, "max_source_amplitude_error": 5.551115123125783e-17, "max_relative_source_amplitude_error": 3.1411474261770867e-16, "relative_reconstruction_power_error": 0.0, "reforward_phase_max_complex_error": 2.2473876566261383e-16, "reconstruction_intensity_range": [3.667903060275457e-07, 0.6811860016093116], "acceptance": "rho50 < 0.05 and rho50 < 0.1*rho0; only these declared fixtures/seeds"}
{"record": "png_and_quantization", "case": "two_features_rect", "seed": 0, "png_vs_array_intensity_max_error": 0.0, "png_vs_array_source_max_error": 0.0, "png_vs_array_history_max_error": 0.0, "continuous_vs_decoded_intensity_max_error": 0.0019567813270121026, "continuous_vs_decoded_amplitude_max_error": 0.04403354188308833, "continuous_power_au_m2": 7.690608625440926e-09, "decoded_power_au_m2": 7.67529411764706e-09, "continuous_final_residual": 0.028586272211195397, "decoded_final_residual": 0.03765171966877544, "continuous_vs_decoded_final_intensity_max_difference": 0.11100942389566043, "planning_source_amplitude": 0.17672252747085265, "demo_source_amplitude": 0.17672252747085265, "demo_minus_planning_amplitude": 0.0, "demo_minus_planning_amplitude_ulps": 0.0, "interpretation": "PNG matches uint8-array route exactly. Continuous design is a different target; its solve is separate evidence, not a replacement acceptance fixture."}
{"record": "performance", "case": "smooth_spot_64", "shape": [64, 64], "seed": 0, "iterations": 50, "repetitions": 5, "wall_seconds": {"shipped": [0.024316600000020117, 0.028422300005331635, 0.025718699966091663, 0.025674199976492673, 0.025860599998850375], "hoisted_probe": [0.022887500002980232, 0.026263699983246624, 0.023439400014467537, 0.024445699993520975, 0.02443439996568486], "unhoisted_probe": [0.04233129997737706, 0.044490500004030764, 0.03797349997330457, 0.05032249999931082, 0.048241899989079684]}, "median_seconds": {"shipped": 0.025718699966091663, "hoisted_probe": 0.02443439996568486, "unhoisted_probe": 0.044490500004030764}, "hoisted_probe_H_calls": 2, "unhoisted_probe_H_calls": 101, "unhoisted_over_hoisted_probe_median_ratio": 1.8208141008787715, "hoisted_vs_unhoisted_max_source_error": 0.0, "hoisted_vs_shipped_max_source_error": 0.0, "hoisted_vs_shipped_max_history_error": 0.0, "method": "perf_counter, same interpreter, alternating order, warmed. Paired probe kernels differ only in repeated public-H construction. Shipped solver timed separately with its validation/result construction."}
{"record": "performance", "case": "two_features_64", "shape": [64, 64], "seed": 0, "iterations": 50, "repetitions": 5, "wall_seconds": {"shipped": [0.025485700054559857, 0.026253700023517013, 0.026191000011749566, 0.030593100003898144, 0.029578000016044825], "hoisted_probe": [0.023623500019311905, 0.02426410000771284, 0.02517819998320192, 0.026162800029851496, 0.030903899983968586], "unhoisted_probe": [0.03793829999631271, 0.0410181000479497, 0.044167199986986816, 0.044248599966522306, 0.052976899954956025]}, "median_seconds": {"shipped": 0.026253700023517013, "hoisted_probe": 0.02517819998320192, "unhoisted_probe": 0.044167199986986816}, "hoisted_probe_H_calls": 2, "unhoisted_probe_H_calls": 101, "unhoisted_over_hoisted_probe_median_ratio": 1.7541841758526717, "hoisted_vs_unhoisted_max_source_error": 0.0, "hoisted_vs_shipped_max_source_error": 0.0, "hoisted_vs_shipped_max_history_error": 0.0, "method": "perf_counter, same interpreter, alternating order, warmed. Paired probe kernels differ only in repeated public-H construction. Shipped solver timed separately with its validation/result construction."}
{"record": "performance", "case": "two_features_rect", "shape": [48, 64], "seed": 0, "iterations": 50, "repetitions": 5, "wall_seconds": {"shipped": [0.030203100002836436, 0.028562700026668608, 0.029975199955515563, 0.03221490001305938, 0.034999099967535585], "hoisted_probe": [0.029437299992423505, 0.02694300003349781, 0.02757440001005307, 0.029952899960335344, 0.025980899983551353], "unhoisted_probe": [0.04788849997567013, 0.04659350001020357, 0.051215199986472726, 0.052420000021811575, 0.035821700002998114]}, "median_seconds": {"shipped": 0.030203100002836436, "hoisted_probe": 0.02757440001005307, "unhoisted_probe": 0.04788849997567013}, "hoisted_probe_H_calls": 2, "unhoisted_probe_H_calls": 101, "unhoisted_over_hoisted_probe_median_ratio": 1.7367014316979137, "hoisted_vs_unhoisted_max_source_error": 0.0, "hoisted_vs_shipped_max_source_error": 0.0, "hoisted_vs_shipped_max_history_error": 0.0, "method": "perf_counter, same interpreter, alternating order, warmed. Paired probe kernels differ only in repeated public-H construction. Shipped solver timed separately with its validation/result construction."}
{"record": "memory", "case": "smooth_spot_64", "shape": [64, 64], "kind": "traced", "seed": 0, "iterations": 50, "final_residual": 0.017125299052456723, "tracemalloc_baseline_bytes": 0, "tracemalloc_current_bytes": 1051097, "tracemalloc_additional_peak_bytes": 1610414, "method": "Fresh process, inputs built before tracing. Additional tracked peak includes allocations/lazy initialization during solve; not total process memory."}
{"record": "memory", "case": "smooth_spot_64", "shape": [64, 64], "kind": "os", "seed": 0, "iterations": 50, "final_residual": 0.017125299052456723, "before_solve": {"working_set_bytes": 36229120, "absolute_process_peak_working_set_bytes": 36229120}, "after_solve": {"working_set_bytes": 40026112, "absolute_process_peak_working_set_bytes": 40026112}, "method": "Fresh process without tracemalloc. Windows absolute lifetime peak includes interpreter, imports, inputs, and solve; it is not an incremental solver allocation peak."}
{"record": "memory", "case": "two_features_64", "shape": [64, 64], "kind": "traced", "seed": 0, "iterations": 50, "final_residual": 0.03611691872197391, "tracemalloc_baseline_bytes": 0, "tracemalloc_current_bytes": 1050841, "tracemalloc_additional_peak_bytes": 1610158, "method": "Fresh process, inputs built before tracing. Additional tracked peak includes allocations/lazy initialization during solve; not total process memory."}
{"record": "memory", "case": "two_features_64", "shape": [64, 64], "kind": "os", "seed": 0, "iterations": 50, "final_residual": 0.03611691872197391, "before_solve": {"working_set_bytes": 36073472, "absolute_process_peak_working_set_bytes": 36073472}, "after_solve": {"working_set_bytes": 40124416, "absolute_process_peak_working_set_bytes": 40124416}, "method": "Fresh process without tracemalloc. Windows absolute lifetime peak includes interpreter, imports, inputs, and solve; it is not an incremental solver allocation peak."}
{"record": "memory", "case": "two_features_rect", "shape": [48, 64], "kind": "traced", "seed": 0, "iterations": 50, "final_residual": 0.03765171966877544, "tracemalloc_baseline_bytes": 0, "tracemalloc_current_bytes": 1018073, "tracemalloc_additional_peak_bytes": 1438126, "method": "Fresh process, inputs built before tracing. Additional tracked peak includes allocations/lazy initialization during solve; not total process memory."}
{"record": "memory", "case": "two_features_rect", "shape": [48, 64], "kind": "os", "seed": 0, "iterations": 50, "final_residual": 0.03765171966877544, "before_solve": {"working_set_bytes": 35717120, "absolute_process_peak_working_set_bytes": 35794944}, "after_solve": {"working_set_bytes": 39870464, "absolute_process_peak_working_set_bytes": 39870464}, "method": "Fresh process without tracemalloc. Windows absolute lifetime peak includes interpreter, imports, inputs, and solve; it is not an incremental solver allocation peak."}
~~~

Current endpoints, all declared seeds (full histories are above):

| Fixture | Seed | rho_0 | rho_50 | rho_50/rho_0 |
|---|---:|---:|---:|---:|
| smooth_spot_64 | 0 | 0.99105418117628941 | 0.017125299052456723 | 0.017279881743832191 |
| smooth_spot_64 | 1 | 0.99760288724375035 | 0.016694784541118089 | 0.016734899983342721 |
| smooth_spot_64 | 2 | 0.99962357682740388 | 0.014344758005132971 | 0.014350159737788731 |
| smooth_spot_64 | 3 | 1.0037224371986919 | 0.015919803568154665 | 0.01586076287443125 |
| two_features_64 | 0 | 1.2193654443597639 | 0.036116918721973909 | 0.029619437625557236 |
| two_features_64 | 1 | 1.205476068810247 | 0.036612380296920814 | 0.030371718895303875 |
| two_features_64 | 2 | 1.2125652885224496 | 0.038941522585850458 | 0.032114990388106834 |
| two_features_64 | 3 | 1.2105930187246314 | 0.034151650734589568 | 0.028210678738729702 |
| two_features_rect | 0 | 1.192628191648109 | 0.037651719668775438 | 0.031570375354572175 |
| two_features_rect | 1 | 1.1840781177155155 | 0.036637075285440794 | 0.030941434300066298 |
| two_features_rect | 2 | 1.1842858363557385 | 0.034672248336859009 | 0.029276925614133649 |
| two_features_rect | 3 | 1.1568588931942665 | 0.031786333196884356 | 0.027476413401739404 |

## Shipped performance and measured precomputation benefit

The canonical full-probe command above ran after the final suite, with other
project numerical/test processes stopped. These are current shipped-solver
measurements, not planning timings. Five warmed wall-time repetitions use
perf_counter, alternating shipped/hoisted/unhoisted order. Shipped timing includes
validation, initialization, both H constructions, fifty projection cycles,
fifty-one residuals and result construction.

The two probe loops are otherwise identical: public H is constructed twice
versus 101 times. Their source, reconstruction and history arrays compare
exactly. Shipped results are compared separately with rtol=1e-12, atol=1e-14;
measured source/history differences are zero. The ratio isolates H reuse in
these probe kernels, not a whole-solver speedup over an earlier release.

| Fixture | Shipped median [s] | Unhoisted/hoisted probe ratio | Traced additional peak [bytes] | Separate OS lifetime peak [bytes] |
|---|---:|---:|---:|---:|
| smooth_spot_64 | 0.025718699966091663 | 1.8208141008787715 | 1610414 | 40026112 |
| two_features_64 | 0.026253700023517013 | 1.7541841758526717 | 1610158 | 40124416 |
| two_features_rect | 0.030203100002836436 | 1.7367014316979137 | 1438126 | 39870464 |

Each memory measurement uses a fresh child. Tracemalloc starts after input
allocation; its additional peak includes tracked allocations and lazy
initialization during the solve, not total resident memory. A separate child
without tracing reports Windows GetProcessMemoryInfo absolute lifetime
PeakWorkingSetSize, including interpreter, imports, inputs and solve. Two
working-set samples are not subtracted to infer an incremental solver peak.
CPU/load effects remain; these small-grid results do not extrapolate to
arbitrary image sizes.

The probe records Python 3.11.9, NumPy 2.4.6, SciPy 1.17.1, Pillow 12.3.0 and
Windows build 26100. The host reports Intel64 Family 6 Model 198 Stepping 2,
24 logical CPUs; no marketing CPU model is inferred.

## Actual PNG demos and committed figures

Default headless demo, exit 0:

~~~powershell
.\.venv\Scripts\python.exe -B examples\synthesize_hologram.py --no-show
~~~

Exact output:

~~~text
input: deterministic synthetic 8-bit grayscale PNG (smooth spot)
grid: shape=(64, 64), dx=8e-06 m, dy=8e-06 m
wavelength=6.33e-07 m, distance=0.005 m
seed=0, iterations=50, full-grid periodic ASM
configured uniform source amplitude: 2.93462716737912188e-01 a.u.
source power: 2.25759372549019720e-08 a.u. m^2
target power: 2.25759372549019588e-08 a.u. m^2
Illumination is configured separately for this target; target values are unchanged.
initial normalized squared amplitude residual: 9.91054181176289406e-01
final normalized squared amplitude residual: 1.71252990524567231e-02
independently recomputed final residual: 1.71252990524567231e-02
actual reconstruction intensity range: [3.43246545591277319e-06, 1.05131810649934043e+00]
shared target/reconstruction display range: [0, 1.05131810649934043e+00]
verification: returned phase -> public ASM -> reconstruction/residual passed (rtol=1e-12, atol=1e-14)
Phase is an ideal numerical visualization, not a calibrated SLM drive image.
Raw residual is not percent accuracy; arbitrary targets need not be exactly achievable.
~~~

Reproduce the explicit rectangular PNG from the committed fixture:

~~~powershell
@'
from pathlib import Path
import runpy
from PIL import Image
fixture = runpy.run_path('scripts/probe_m3_evidence.py')['planning_fixture'](2)
path = Path('runs/m3/explicit_rectangular_target.png')
path.parent.mkdir(parents=True, exist_ok=True)
with Image.fromarray(fixture.codes) as image:
    image.save(path, format='PNG')
'@ | .\.venv\Scripts\python.exe -B -
.\.venv\Scripts\python.exe -B examples\synthesize_hologram.py --input runs/m3/explicit_rectangular_target.png --ny 48 --nx 64 --dx-m 8e-6 --dy-m 10e-6 --no-show
~~~

Verified input identity:

~~~text
runs/m3/explicit_rectangular_target.png: strict uint8 grayscale PNG, shape=(48, 64), SHA256=50d2523d156bb76a6cda6caa0edd6664024afe0130f5a0a92c853554990c5798
~~~

Exact explicit-demo output, exit 0:

~~~text
input: C:\holographiclab\runs\m3\explicit_rectangular_target.png
grid: shape=(48, 64), dx=8e-06 m, dy=1e-05 m
wavelength=6.33e-07 m, distance=0.005 m
seed=0, iterations=50, full-grid periodic ASM
configured uniform source amplitude: 1.76722527470852653e-01 a.u.
source power: 7.67529411764705996e-09 a.u. m^2
target power: 7.67529411764705996e-09 a.u. m^2
Illumination is configured separately for this target; target values are unchanged.
initial normalized squared amplitude residual: 1.19262819164810896e+00
final normalized squared amplitude residual: 3.76517196687754380e-02
independently recomputed final residual: 3.76517196687754380e-02
actual reconstruction intensity range: [6.84489700740959415e-07, 6.69715798262431772e-01]
shared target/reconstruction display range: [0, 6.69715798262431772e-01]
verification: returned phase -> public ASM -> reconstruction/residual passed (rtol=1e-12, atol=1e-14)
Phase is an ideal numerical visualization, not a calibrated SLM drive image.
Raw residual is not percent accuracy; arbitrary targets need not be exactly achievable.
~~~

The demos print configured illumination and both powers. The illumination
choice is outside the solver and leaves target values unchanged. Target and
actual reconstruction share the printed maximum; the default reconstruction
exceeds one without clipping. Both demos rebuild the returned phase through
public ASM and independently verify its residual. Phase is ideal numerical
phase, not calibrated hardware drive. Headless rendering was tested;
interactive GUI/VS Code operation was not separately automated.

Figure command, run twice successfully:

~~~powershell
.\.venv\Scripts\python.exe -B scripts\make_m3_figures.py
~~~

Exact second-generation output:

~~~text
wrote docs/handoffs/milestone_3/figures/fig01_single_plane_gs.png
fig01 final residual=1.71252990524567231e-02; shared vmax=1.05131810649934043e+00
wrote docs/handoffs/milestone_3/figures/fig02_seed_histories.png
fig02 verified all 12 declared fixture/seed criteria
wrote docs/handoffs/milestone_3/figures/fig03_rectangular_case.png
fig03 final residual=3.76517196687754380e-02; shared vmax=6.69715798262431772e-01
~~~

All three figures were visually inspected: readable labels/legends, shared
intensity scales preserving overshoot, all declared seed histories, and correct
rectangular physical aspect and +y-down orientation. No visual changes were
needed. Regeneration identity and sizes:

~~~text
docs/handoffs/milestone_3/figures/fig01_single_plane_gs.png SHA256=AAC663B7536D05FAADF58DCCE11FB26E48D638FA01CFCF3CC1EBE05BE1C36BA7 bytes=219825 second_run_unchanged=True
docs/handoffs/milestone_3/figures/fig02_seed_histories.png SHA256=E99EBBE7197780CDF3F77978AB30B1435D5B7FF45410CC45B0B5997F508B195D bytes=196707 second_run_unchanged=True
docs/handoffs/milestone_3/figures/fig03_rectangular_case.png SHA256=C47D2724FE6B59C94D75E5863FED03853208C15FF62B7E86F4289465DC9EB9B7 bytes=215152 second_run_unchanged=True
~~~

Decoded dimensions/metadata:

~~~text
{"path": "docs/handoffs/milestone_3/figures/fig01_single_plane_gs.png", "size": [1830, 1455], "mode": "RGBA", "metadata": {"Software": "Open Holographic Lab - Milestone 3", "dpi": [150.01239999999999, 150.01239999999999]}}
{"path": "docs/handoffs/milestone_3/figures/fig02_seed_histories.png", "size": [2250, 825], "mode": "RGBA", "metadata": {"Software": "Open Holographic Lab - Milestone 3", "dpi": [150.01239999999999, 150.01239999999999]}}
{"path": "docs/handoffs/milestone_3/figures/fig03_rectangular_case.png", "size": [1830, 1425], "mode": "RGBA", "metadata": {"Software": "Open Holographic Lab - Milestone 3", "dpi": [150.01239999999999, 150.01239999999999]}}
~~~

## Scope preservation and publication

The complete diff was reviewed against the approved twenty-path inventory.
All existing numerical modules, loader, tests, dependency declarations,
historical evidence, AGENTS.md, CLAUDE.md and old figures are unchanged.
The root initializer differs only in its module docstring. Historical ledger
sections through M2 and the M4-and-later text are preserved.

Actual verification output:

~~~text
ALLOWLIST: exact 20 paths (4 modified, 16 created)
PROTECTED TRACKED FILES: 68 of 72 pre-existing files byte-identical
ROOT INITIALIZER: executable AST, imports, exports and version unchanged
HISTORICAL LEDGER: scaffolding through M2 byte-equivalent text, M4+ text unchanged
EXISTING NUMERICAL SOURCE, LOADER, TESTS, DEPENDENCIES, AGENTS.md, CLAUDE.md, HANDOFFS AND OLD FIGURES: unchanged
CHANGED PATHS
M README.md
A docs/handoffs/milestone_3/code_map.md
A docs/handoffs/milestone_3/figures/fig01_single_plane_gs.png
A docs/handoffs/milestone_3/figures/fig02_seed_histories.png
A docs/handoffs/milestone_3/figures/fig03_rectangular_case.png
A docs/handoffs/milestone_3/implementation_summary.md
A docs/handoffs/milestone_3/known_limitations.md
A docs/handoffs/milestone_3/math_used.md
A docs/handoffs/milestone_3/tests_and_evidence.md
A docs/handoffs/milestone_3/tutor_context.md
M docs/math_conventions.md
M docs/milestones.md
A examples/synthesize_hologram.py
A scripts/make_m3_figures.py
A scripts/probe_m3_evidence.py
M src/ohlab/__init__.py
A src/ohlab/algorithms/__init__.py
A src/ohlab/algorithms/gerchberg_saxton.py
A tests/test_gerchberg_saxton.py
A tests/test_gerchberg_saxton_reference.py
~~~

The 13 embedded driver/output blocks were checked against their complete
original captures, including exact whitespace. Verbatim negative-control
tracebacks intentionally retain NumPy's whitespace-only error lines. New prose
and source have no corresponding whitespace exception. Existing pytest 9.1.1
and matplotlib 3.11.1 were also verified; no environment change was made.
Essential probe code, parameters, raw histories, negative-control drivers and
results are preserved in the committed script/tests and this handoff rather
than being available only in temporary storage.

The approved publication is one normal commit:
`feat(m3): synthesize phase-only holograms with periodic ASM GS`, staging only
the twenty listed paths, followed by a normal push to existing origin/main.
Local HEAD, live remote main and GitHub API SHA are checked afterward, together
with a clean working tree. Their post-commit values are supplied in the final
completion report, avoiding a self-referential commit SHA in its own contents.
No branch switch, reset, clean, stash, history rewrite, force push or later
milestone is included.

The only implementation refinement discovered during review was the documented
M3-only floating-point cutoff-domain guard, within the approved requirement
to reject unusable lossless arithmetic. The model, APIs, fixture definitions,
seeds, thresholds and twenty-file scope remain as approved. No milestone
acceptance check remains unresolved. Model/coverage/platform limits remain
those in [known_limitations.md](known_limitations.md). M4 was not started.
