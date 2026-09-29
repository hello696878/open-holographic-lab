# Milestone 5 — Mathematics and exactness

Recorded 2026-09-23. M5 adds persistence and replay, not a new optical model.
The [normative conventions](../../math_conventions.md) retain M2's mapping,
M3's complete periodic lossless ASM synthesis, and M4's metric definitions.
Their existing physical and numerical limitations still apply.

## Quantities preserved

For a grayscale design code `g`, M2 computes

    T = float64(g)/255
    A_target = sqrt(T)

Schema v1 also accepts an already prepared float64 design intensity in `[0,1]`.
The example explicitly chooses uniform source amplitude

    A_source = sqrt(sum(A_target**2) / (ny*nx))

This is a per-target illumination choice outside the solver. It does not
normalize the target or change M3's power-compatibility test. With uniform
pixel area, modeled power is `sum(A**2)*dx*dy` in the existing arbitrary units
times square metres.

The saved source and reconstruction are the actual complex arrays returned
by M3. Phase and reconstruction intensity are derived from them. Rebuilding
`A*exp(i*phase)` can introduce roundoff and cannot replace the original complex
source as a bit-preserving storage method. Saving both fields preserves the
values actually computed.

M3 history still contains all `iterations+1` values of

    rho_k = sum((abs(V_k)-A_target)**2) / sum(A_target**2)

This is normalized squared amplitude error, not intensity error or percent
accuracy. M4 evaluates the persisted actual reconstruction intensity `R`:

    intensity_mse = sum((R-T)**2)/N
    intensity_nmse = sum((R-T)**2)/sum(T**2)
    intensity_psnr = 20*log10(data_range) - 10*log10(intensity_mse)
    signal_region_power_fraction = sum(R[signal_mask])/sum(R)
    regional_intensity_cv = std(R[cv_mask], ddof=0)/mean(R[cv_mask])

Only requested quantities are computed. Each regional metric retains its own
mask, and PSNR retains its declared range. MSE has squared-intensity units;
PSNR is in dB; the others are dimensionless. A fraction is mathematically
between zero and one, but the artifact boundary preserves M4's actual finite
roundoff result without imposing an additional upper bound. Neither a fraction
nor CV is an aggregate accuracy score. A desired Gaussian is not a flat-field
uniformity fixture.

## Three different comparisons

For artifact bytes `B`, the manifest records `SHA256(B)` and byte length.
Verification recomputes both from the saved file. This includes the NPY header,
not just its numerical payload. The manifest itself is excluded from hashing
to avoid circularity. A matching digest establishes agreement with that
manifest; someone able to replace both file and manifest can create a new
matching pair. No signature or author identity follows.

Source/environment qualification compares recorded metadata with current
runtime information and independently supplied or detected current source
provenance. Matching metadata determines whether the requested replay is
qualified under this policy. It is not a mathematical proof that every
execution on every machine will produce identical bits.

Numerical replay actually calls M3 again from the saved input amplitudes,
settings and original initialization mode. It compares saved and new arrays
using all three conditions:

    dtype.str_saved == dtype.str_replayed
    shape_saved == shape_replayed
    tobytes(order="C")_saved == tobytes(order="C")_replayed

The compared outputs are source field, phase, reconstruction field,
reconstruction intensity and residual history. Replay also checks the saved
target-amplitude, phase and intensity derivations. It recomputes metrics once
from saved intensity and separately from the new reconstruction. Finite metric
values compare by their binary64 bits. No relative/absolute tolerance or
automatic approximate fallback belongs to this exact replay criterion.

## Serialization and signed zero

Owned C-order snapshots preserve dtype and logical element bits from C-,
Fortran- or strided input storage. Original strides and memory layout are not
scientific artifacts; logical element representation is. Float64/complex128
NPY payloads preserve that representation, including signed zeros.
Reductions can depend on memory layout, so M5 computes metrics from its saved
C-order intensity snapshot. This fixes the wrapper's capture contract without
altering M4's implementation or promising that every caller layout reduces in
the same order.

Supported finite scalar settings use ordinary Python JSON numbers. Their
binary64 round trip, including `-0.0`, is tested explicitly rather than assumed
from decimal appearance. Strict JSON cannot use a bare `Infinity` token.
Validated exact-match PSNR therefore uses the string `"+inf"` in metrics JSON
and restores Python positive infinity when loading. Other nonfinite metric
representations are rejected.

M4's numerical equality for exact-match PSNR intentionally treats signed zeros
as equal. Artifact/replay byte equality can distinguish them. These contracts
answer different questions and neither changes the existing field or metric
semantics.

Seed mode records the actual seed and environment and calls unchanged M3 again.
Explicit mode preserves the actual initial-phase array. M5 neither duplicates
the RNG algorithm nor asserts that a future RNG/library version will reproduce
the same phase. See [tests and evidence](tests_and_evidence.md) for measured
same-environment comparisons, scalar/array round trips and independent failure
controls. Explanatory diagrams do not establish these numerical results.
