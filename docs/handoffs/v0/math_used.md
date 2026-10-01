# V0 — Mathematical model and independent references

Normative contract: [math conventions §3.17](../../math_conventions.md#317-v0-aligned-sequential-optics--api-and-schema-contract).
The following derivations specify what the code and independent references
mean; their actual numerical agreement is in [tests and evidence](tests_and_evidence.md).

## Coordinates and propagation

Use SI metres, `(ny,nx)` arrays, `x_j=(j-nx//2)dx`,
`y_i=(i-ny//2)dy`, and time convention `exp(-iωt)`. A positive-z plane wave has
spatial phase `exp(+ikz z)`, with `Im(kz)>=0` for forward decay. Existing M1
ASM remains unchanged and is called with `pad_factor=1` on every derived
nonnegative interval, including the observation interval. This is one complete
periodic window, without intermediate crop or repeated embedding.

The inspected TU Delft [angular-spectrum section](https://phys.libretexts.org/Bookshelves/Optics/BSc_Optics_%28Konijnenberg_Adam_and_Urbach%29/06%3A_Scalar_diffraction_optics/6.04%3A_Angular_Spectrum_Method)
explicitly gives this time convention, forward exponential and positive square
root. Evanescent components decay; only propagating components preserve modulus.
The independent small direct-DFT reference constructs indices, physical
coordinates, FFT-ordered signed frequency integers, factors, masks/lens phases
and ordered updates independently, using direct matrix sums rather than NumPy
FFT or production coordinate/frequency helpers.

## Gaussian source and full lens-transformed field

Define w0 as 1/e amplitude radius (1/e² intensity radius), A0 as waist peak
amplitude, s=z-z_waist, zR=πw0²/λ and r²=(x-cx)²+(y-cy)². The source is sampled
at z=0 from

```text
b = 1 + i*s/zR
U = A0/b * exp[-r²/(w0²*b)] * exp[i*(k*s+φ0)].
```

An independent implementation uses separate amplitude, curvature, Gouy and
carrier terms:

```text
w(s) = w0*sqrt(1+(s/zR)²)
1/R(s) = s/(s²+zR²)
ψ(s) = atan(s/zR)
U = A0*w0/w(s) * exp[-r²/w(s)²]
    * exp{i[k*s + φ0 + k*r²/(2R(s)) - ψ(s)]}.
```

The waist curvature term is zero. This reference checks s<0, s=0 and s>0,
including nonzero center and initial phase. It does not call production source
sampling. Image-design Gaussian pixel widths are unrelated.

For the centered Gaussian define q=s-i*zR, so
`1/q=1/R+i*λ/(πw²)` and the spatial factor is `exp(i*k*r²/(2q))`.
At a lens, `q_plus=1/(1/q_minus-1/f)`. The full amplitude/phase immediately
before and after the lens share the same on-axis coefficient C_L. After travel
d from that lens:

```text
U(r,L+d) = C_L * q_plus/(q_plus+d) * exp(i*k*d)
           * exp[i*k*r²/(2*(q_plus+d))].
```

Here `C_L=A0*w0/w(L-z_waist)*exp[i*(k*(L-z_waist)+φ0-ψ(L-z_waist))]`.
The prefactor enforces on-axis amplitude and phase continuity through the lens;
width agreement alone is not a complex-field reference. No fitted global phase
or amplitude is permitted. This particular lens reference is for a centered,
unapertured beam; the clipped Gaussian is validated by separate convergence.

The independently inspected [MIT Gaussian-beam notes](https://ocw.mit.edu/courses/6-974-fundamentals-of-photonics-quantum-electronics-spring-2006/e9852c138493233bc2813f683da5b199_gaussian_bem_res.pdf)
give ABCD propagation and the thin-lens inverse-q update in Eqs. (2.259)–(2.263),
printed pp. 104–105. Their Eq. (2.260) uses the opposite complex-field sign with
waist q=+i*zR (also stated on printed p. 106); conjugation translates that
reference to the repository's q=-i*zR. Previously cited equations from material
not present in that excerpt are not claimed independently inspected here.

For a lens exactly at the original waist, the new minimum is
`z_min=f/(1+(f/zR)²)`, not generally f. The declared w0=100 µm, λ=633 nm,
f=20 mm fixture gives 17.205882758 mm. Both signs of f and neighboring planes
are separately checked. Gaussian/lens expressions are paraxial models; exact
ASM versus paraxial-reference differences have fixture-specific floors.

## Apertures and lens action

Circle transmission is `1[x²+y²<=a²]`; rectangle transmission is
`1[abs(x)<=w/2 and abs(y)<=h/2]`. Both use metres on each physical axis, including
anisotropic pitches. Dimensions are positive, boundaries inclusive and samples
are centers. No smoothing, epsilon edge expansion or renormalization occurs.
The slit is a finite rectangle, not infinite in its long axis.

The ideal thin lens applies `exp[-i*k*(x²+y²)/(2f)]`, with signed finite
nonzero f and no implicit aperture/constant phase adjustment. The inspected
TU Delft [Fourier-optics treatment §6.8.1](https://phys.libretexts.org/Bookshelves/Optics/BSc_Optics_%28Konijnenberg_Adam_and_Urbach%29/06%3A_Scalar_diffraction_optics/6.09%3A_Fourier_Optics)
derives this quadratic phase by expanding the spherical path. V0 separates its
clear aperture from phase action; its inclusive sampled edge is an explicit
discrete choice, rather than an assertion about a continuous boundary's measure.

## Continuous rectangular Fresnel reference

The physical reference aperture remains 80×120 µm at z=0, uniform incident
amplitude one, λ=633 nm, terminal z=5 mm. For each transverse coordinate x,
define `u±=sqrt(2/(λz))*(±width/2-x)` and

```text
Jx = sqrt(λz/2)*[(C(u+)-C(u-))+i*(S(u+)-S(u-))]
Jy analogous using height
Uref(x,y,z) = exp(i*k*z)/(i*λ*z) * Jx * Jy.
```

The code uses SciPy's `fresnel`, whose outputs are S then C, without changing
the aperture to its sampled area. The carrier, complex prefactor and amplitude
are retained. The inspected TU Delft [Fresnel section §6.5.1](https://phys.libretexts.org/Bookshelves/Optics/BSc_Optics_%28Konijnenberg_Adam_and_Urbach%29/06%3A_Scalar_diffraction_optics/6.07%3A_Fresnel_and_Fraunhofer_Approximations)
provides the sign-matched kernel and its paraxial interpretation. The inspected
[UT Austin rectangle treatment, Eqs. (10.119)–(10.124)](https://farside.ph.utexas.edu/teaching/315/Waveshtml/node101.html)
provides separability and C/S integrals; its intensity expression alone is not
used as a full complex-phase reference.

The ROI selects centers satisfying `abs(x)<=100e-6 AND abs(y)<=100e-6`,
inclusive, on each tested grid. Its metric is exactly

```text
sqrt(sum_ROI(abs(U_numeric-U_reference)**2)
     / sum_ROI(abs(U_reference)**2)).
```

The approved bound is <=0.035 only for the declared finest 2048²/1-µm case.
It is relative complex L2, not intensity error, worst-pixel accuracy or a
universal tolerance. There is no fitted scaling, global-phase alignment, peak
normalization or altered ROI. Physical area 9.6e-9 m² and sampled area are
recorded separately. All five declared pitch/window cases remain visible.

The Fresnel phase drops the quartic path term; its magnitude at the extremal
aperture-to-ROI displacement is estimated separately, alongside the denominator
approximation. Neither that local model estimate nor observed convergence is a
rigorous universal total-error bound for discontinuous apertures.

## Norm, zero fields and arithmetic

Sampled norm is `sum(abs(U)**2)*dx*dy` in amplitude-unit²·m², rectangular
quadrature on the complete window. Before/after records and signed differences
identify aperture removal without calling every tiny lens difference absorption.
Propagation conservation requires the complete periodic window and propagating
spectrum; evanescent decay can reduce norm. A selected display-region norm is a
separate quantity. No unexplained escaped-power accounting is invented.

Source amplitude zero and a valid aperture fully blocking constructed incident
support are valid. Incident-zero transmission ratio is undefined (`None`), not
zero/one efficiency. All geometry and other parameters are validated first.

Numerical tail underflow is permitted only in the documented local Gaussian
decay, bounded transmission products, squared-magnitude norm reduction and
forward decay paths. Overflow, invalid operations, unusable geometry and a
nonzero field whose complete norm underflows fail explicitly. Local contexts
restore caller floating-point settings. No blanket all-errors-raise context
changes M1's supported evanescent decay.

Reference web pages and the cited MIT excerpt were accessed 2026-10-01. The
equations above are independently translated/derived, not copied production
propagation code or an attribution to an inaccessible textbook.
