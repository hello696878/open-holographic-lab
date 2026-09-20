# Milestone 4 — Reconstruction intensity quality

Implemented from accepted baseline `52865300ef197bb55e606c550ca163c40cb74b74`
under the approved 15-path scope: five metrics, independent validation, a
standalone example, two figures, six handoff documents, one milestone commit
and a normal push. Normative contract: version 0.7, §3.14, dated 2026-09-20.

## Public API

Import explicitly from `ohlab.metrics`; root exports are unchanged.

```python
intensity_mse(*, target_intensity: NDArray[np.float64],
              reconstruction_intensity: NDArray[np.float64]) -> float
intensity_nmse(*, target_intensity: NDArray[np.float64],
               reconstruction_intensity: NDArray[np.float64]) -> float
intensity_psnr(*, target_intensity: NDArray[np.float64],
               reconstruction_intensity: NDArray[np.float64],
               data_range: float) -> float
signal_region_power_fraction(*, reconstruction_intensity: NDArray[np.float64],
                             signal_mask: NDArray[np.bool_]) -> float
regional_intensity_cv(*, intensity: NDArray[np.float64],
                      mask: NDArray[np.bool_]) -> float
```

For target T, reconstruction R, pixel count N and explicit region M:

| Metric | Definition | Units |
|---|---|---|
| MSE | `sum((R-T)**2)/N` | Squared intensity units |
| NMSE | `sum((R-T)**2)/sum(T**2)` | Dimensionless |
| PSNR | `20*log10(data_range)-10*log10(MSE)` | dB |
| Signal-region fraction | `sum(R[M])/sum(R)` | Dimensionless |
| Regional CV | `std(I[M],ddof=0)/mean(I[M])` | Dimensionless |

NMSE's denominator is a squared intensity norm, not optical power; its value
is not NRMSE or M3's amplitude residual. Uniform pixel area cancels in the power
fraction, whose denominator is the full supplied reconstruction window. It is
not an unqualified diffraction-efficiency measure. CV describes population
variation inside a region and can exceed one. Its uniformity interpretation
requires intended flat brightness.

## Validation, ownership and numerical behavior

Inputs are plain native float64 nonempty 2-D intensity arrays, finite and
nonnegative, with exact matching comparison shapes. Values above one are
accepted. Masks are plain Boolean arrays with the exact intensity shape.
Read-only and noncontiguous arrays are accepted without mutation or retention.
All five outputs are built-in Python floats. Types/dtypes fail with TypeError;
invalid shapes/domains and unusable arithmetic fail with contextual ValueError.

No conversion, image alignment, resizing, clipping, normalization, inferred
range/mask or epsilon denominator is introduced. The exact policies are:

- Zero-target MSE is valid; zero target squared norm makes NMSE undefined.
- PSNR validates both arrays and positive finite non-Boolean data_range before
  numerical equality returns +infinity. Signed zeros compare equal. There is
  no approximate-match threshold; negative scores remain negative.
- Fractions require positive usable full-window power. Empty selection gives
  zero, all-window selection one. Zero total power always raises.
- CV rejects empty/zero-mean regions. Exactly constant positive regions,
  including one pixel, return exact zero before unnecessary variance arithmetic.
- Local strict NumPy error handling and explicit checks reject unusable squares,
  sums, variance and ratios. Caller error settings are restored on success and
  failure. Underflow of nonzero error cannot yield perfect-match PSNR.

Finite inputs do not guarantee all required arithmetic is usable. PSNR avoids
unnecessary range-square/ratio overflow, but no general rescaling or precision
fallback is implemented. See `known_limitations.md` for supported interpretations.

## M3 integration and example

M4 evaluates `result.reconstruction.intensity`. The integration check rebuilds
the returned source phase with its prescribed amplitude, forwards it through
public ASM using pad_factor=1, compares against independent scalar references,
and snapshots source/reconstruction/target/mask/history bytes. M3 code, private
residual calculation, stopping policy and historical evidence are unchanged.

`examples/evaluate_reconstruction.py` uses the approved 64x64 smooth spot,
8-micrometre pitches, 633-nm wavelength, 5-mm distance, seed 0 and 50 cycles.
It fixes its radius-15-pixel signal disk before solving, then compares exact
target, twice target and actual reconstruction with declared data_range=1.
The exact target fraction is below one because the disk excludes target tails.
Three separate flat-region fixtures explain CV and leakage. Shared scales
retain overshoot; M3's amplitude residual is printed separately.

Run headlessly from the repository root:

```powershell
.\.venv\Scripts\python.exe -B examples\evaluate_reconstruction.py --no-show
.\.venv\Scripts\python.exe -B scripts\make_m4_figures.py
```

The six-document handoff and two figures record the implementation and its
finite validation. `tests_and_evidence.md` contains exact outputs, independent
reference errors, measured tolerances, seven mutation detections and figure
reproduction. No teaching completion is inferred. M5, M6 and deferred
enhancements are not started.
