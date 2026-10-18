# W1 — Calculated sections and independent references

W1 preserves the existing SI, phase, Fourier, coordinate and complete-window
V0/ASM conventions. It introduces orchestration and presentation, not another
propagator or a convention change. The field is monochromatic scalar U in air,
time dependence exp(-iωt), forward spectral phase exp(+ik_z d), with nonnegative
evanescent decay and explicit `pad_factor=1`.

The supported train is exactly a Gaussian source, one circular or rectangular
aperture, one ideal thin lens and observation, in stored nondecreasing-z order.
Finite nonzero positive and negative focal lengths are supported. W1 permits
at most 128 samples on either transverse axis and 25 total sections; ordinary
Sequential retains its original limits. Unsupported trains/grids are rejected,
never resized or reordered.

## Section construction

Let aperture, lens and observation positions be z_a≤z_l≤z_o, all nonnegative.
One unchanged V0 run captures U_s at0, U_a immediately after the aperture and
U_l immediately after the lens. For a genuine interior position z:

```text
0 < z < z_a:       U(z) = ASM(U_s, z,       pad_factor=1)
z_a < z < z_l:     U(z) = ASM(U_a, z-z_a,   pad_factor=1)
z_l < z < z_o:     U(z) = ASM(U_l, z-z_l,   pad_factor=1)
```

Each call uses the actual upstream complex amplitude and phase. Optional
samples never form a chained numerical path. Before-aperture and before-lens
fields use their complete upstream interval, matching V0. After sides use V0's
actual captures. Observation uses V0's actual terminal complex field by identity;
bytes are checked before/after derivation. Separate plain-V0 tests enforce exact
terminal byte equality, while independently recomputed references use tolerances.

Required stages are ordered source, before/after aperture, before/after lens,
observation, including ties in z. IDs are `section:<event-selector>` and
`section:interior:NNN`, with NNN the submitted interior ordinal. Before/after
identities are separate even if the instantaneous intensities happen to agree.
An aperture can remove intensity at its plane; an ideal phase-only lens changes
complex phase there and changes intensity downstream through propagation.

At most19 explicit strictly increasing optional z values lie in the three open
intervals. Nineteen default slots are allocated in proportion to positive spans,
using floor plus largest fractional remainders and stable earlier-gap ties.
Positions evaluate as `start+(end-start)*j/(count+1)`. A zero span gets none;
all spans zero yields the six events. Rounded endpoints/duplicates fail.

## Intensities, norm and coordinates

The unchanged field intensity is I=Re(U)²+Im(U)² in amplitude-unit². The
authoritative canonical sampled norm is V0's sum(|U|²)·dx·dy in
amplitude-unit²m². These equivalent binary64 reductions need not agree bitwise;
the browser must not replace canonical norms with an intensity reduction.

Event records retain V0's exact previous norm, signed current-minus-previous
delta and ratio. Interior records compare to their named upstream anchor.
Signed numerical residuals are not clamped or called absorption. The aperture's
actual removed norm is distinct from propagation residual/evanescent decay.
Zero denominators produce null ratios, not epsilon division. A nonzero field
whose entire norm underflows is rejected; allowed local tails may underflow.
Error handling restores caller NumPy settings.

Array layout is `(ny,nx)`; x[j]=(j−nx//2)dx, y[i]=(i−ny//2)dy. Positive y
increases with row index. On-axis intensity is the actual sample at
`[ny//2,nx//2]`, the physical origin for even/odd grids, not necessarily the
off-center Gaussian peak. No resampling or spatial intensity interpolation
creates additional authoritative data. Display curtains use nearest returned
meridional samples within each event-bounded segment and never bridge an
aperture jump. Display magnification/amber opacity are presentation only.

## Independent checks and explicit bounds

`scripts/validate_w1_wave_field.py` constructs dense physical-coordinate DFT
matrices from independently written center coordinates and signed integer
frequency bins. It constructs source, inclusive physical masks, signed lens
phase and principal-root transfer values independently. No production FFT,
source, transmission, grid-array or section-plan helper builds that reference.
Test-only observation captures each transient complete complex field before
intensity derivation; shipped W1 does not retain the full complex stack.

Across eight mixed-parity/asymmetric circular/rectangular matrices and all25
sections, maximum unfitted relative complex L2 is1.8348661564757353e-12.
Predeclared acceptance is relative L2≤2e-11 plus component rtol2e-11,
atol2e-11 times incident peak amplitude. There is no unit floor, phase fitting
or amplitude rescaling. Tests also exercise both focal signs, inclusive hand
masks, exact coordinates, zero/co-located/dark cases and forward evanescence.

The independent free Gaussian uses real beam width, curvature, Gouy phase and
carrier. At30/60/120mm the complete complex errors are1.1463e-7/2.2930e-7/
4.5857e-7 versus the1e-6 fixture bound. The centered unapertured lens reference
keeps the complete prefactor: if U=C exp(-a r²), lens updates
`a→a+i k/(2f)`, then distance d gives
`C exp(ikd)/(1+2ida/k) exp[-a r²/(1+2ida/k)]`.
Both ±80mm cases have worst relative complex L2 5.8137e-6 versus5e-5.
No fitted phase or power normalization enters either comparison.

Thin-lens pointwise intensity and hand complex action use rtol2e-14 and an
explicit incident-intensity/amplitude-scaled atol; tiny signed norm roundoff is
retained. A nondegenerate positive lens has a Gaussian radius minimum at
`f/(1+(f/z_R)²)`, not assumed exactly f; tests compare neighboring samples.
That Gaussian radius interpretation is restricted to the unapertured fixture.

For the fixed128² clean260µm aperture example, separate pitch refinement and
window enlargement give detector intensity relative L2 differences0.00662303
and0.00605808, each below the0.01 fixture bound. The80µm hard-clipping128² case
instead gives0.162646 and0.158519. A free220mm Gaussian has complex discrepancy
1.78728e-5. These retained counterexamples preclude a universal convergence or
isolated-optics badge. Earlier planning measurements remain historical and are
not overwritten by these different-grid results.

These values come from the source-identified
`runs/w1_implementation_01/core/validation_final_01/report.json`, not the earlier
feasibility report. Exact commands, source hashes, raw outputs and product
acceptance boundaries are recorded in [tests_and_evidence.md](tests_and_evidence.md).
