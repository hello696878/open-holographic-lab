# Milestone 3 — Mathematics used

The normative contract is [math_conventions.md §3.13](../../math_conventions.md#313-single-plane-phase-only-gerchbergsaxton-synthesis),
version 0.6, dated 2026-09-16. Earlier Fourier signs, grids and propagation
conventions are unchanged.

## Alternating amplitude constraints

The complex source is `U=A_s exp(i phi)`. A phase-only design varies phi while
preserving the supplied amplitude A_s, which need not be uniform. The desired
target amplitude is A_t. For a complex sample w, the amplitude projection is
`Q_A(w)=A exp(i theta(w))`: retain direction in the complex plane and impose
the required magnitude. At exact zero every phase is equally close, so M3
chooses zero deterministically. There is no threshold near zero.

With `P=P_z`, one cycle is `U_(k+1)=Q_As(P_(-z)(Q_At(P(U_k))))`.
The target projection is an intermediate constraint, not the reconstructed
field. The measured field is always the unconstrained `V_k=P(U_k)`.

Gerchberg–Saxton's alternating-transform/amplitude-replacement structure is
described in Fienup, *Phase retrieval algorithms: a comparison*, Applied Optics
21, 2758–2769 (1982), §II, equations 6–9
([DOI](https://doi.org/10.1364/AO.21.002758),
[author-hosted paper](https://sites.rochester.edu/fienup/wp-content/uploads/2019/07/AO82_PRComparison.pdf)).
M3 applies that structure to the explicitly selected periodic ASM operator.
The citation does not establish our software's correctness or arbitrary target
feasibility; those require the stated model and independent validation.

## Why backward propagation is the inverse here

Write `P_z=F^-1 diag(H_z) F`. F is the unnormalized forward DFT, with inverse
factor `1/(nx*ny)`. Since every sampled kz is real, `H_z=exp(+i kz z)` has
unit magnitude and `H_(-z)=conj(H_z)=1/H_z`. Therefore
`P_(-z) P_z = I` and `P_z^*=P_(-z)` under the spatial inner product
`<u,v>=dx*dy*sum(conj(u)*v)`. The common pixel area does not change the adjoint.

An adjoint is defined by `<Pu,v>=<u,P*v>`; an inverse undoes an operator.
They coincide for this unitary periodic model. Forward P_z generally differs
from both. For embedding E and cropping E*, the cropped propagator is
`T=E*P_zE`; its adjoint is `E*P_(-z)E`, but cropping has lost information,
so the adjoint generally is not T's inverse. M3 does not use that model.

## Power compatibility and residual

Lossless propagation preserves `sum(abs(U)**2)`. Prescribed source and target
energies must therefore agree. The common pixel area converts both to power
and cancels in the symmetric comparison. A relative tolerance of `1e-12`
with absolute zero admits roundoff-scale RMS illumination construction while
rejecting mismatches at arbitrarily small usable power. It is an input
compatibility tolerance, separate from the numerical reference tolerances.

The recorded residual is

```text
rho_k = sum((abs(P_z(U_k))-A_t)**2) / sum(A_t**2).
```

It uses every pixel, including zeros. For exactly equal energies S,
expansion gives `rho=2-2*sum(abs(V)*A_t)/S`; nonnegativity and Cauchy–Schwarz
bound it between zero and two in exact arithmetic. Finite histories are
reported raw, never clipped. This is a squared amplitude discrepancy and
has no direct interpretation as percent accuracy or diffraction efficiency.
Zero target power is rejected so this normalization remains defined.

The two amplitude sets are nonconvex. Equal power is necessary but does not
make their intersection nonempty, identify a unique phase, or promise a
particular residual for arbitrary images. M3 runs an explicit finite cycle
count and returns its last iterate. The twelve specified improvement cases
are regression evidence, not a universal convergence theorem.

## Sampling and independent references

The scalar direct reference constructs signed frequency bins and centered
physical coordinates independently, evaluates the negative-kernel forward
sum with dx*dy, multiplies a scalar analytic H, and evaluates the positive-
kernel inverse sum with `1/(nx*ny*dx*dy)`. It does not call FFT, the production
transfer function or the solver's projection helpers. Complete iterations
on asymmetric small grids check more than an operator round trip.

The diagnostic script computes analytic unwrapped `Theta=kz*z`, sorts the
frequency axes in increasing physical frequency, and takes adjacent differences
along columns (x) and rows (y). It does not use `unwrap(angle(H))` or bridge
the sorted endpoints. Measured increments describe the tested configurations;
they do not establish general sampling adequacy or isolated free-space accuracy.
No production sampling-diagnostic API is added.
