# V2a mathematics — ideal coherent two-path foundation

Recorded 2026-10-05. The normative contract is
[math conventions §3.18](../../math_conventions.md#318-v2a-coherent-two-path-interference).
This handoff explains it; existing M0–V1 signs and implementations are unchanged.

## Complex amplitudes, ports and reference planes

Use the negative time exponent, SI distances and radians, and ordered pairs
(0,1). The ideal first mixer is `B=[[1,i],[i,1]]/sqrt(2)` and the explicitly
chosen recombiner is `B_dagger=[[1,-i],[-i,1]]/sqrt(2)`. The diagonal coefficients
are logical transmission, the crossed coefficients logical reflection. These
are abstract port labels, not physical mirror coordinates or coating laws.
The second matrix is an inverse at declared reference planes, not a claim
about rotating an arbitrary cube.

Direct multiplication gives `B_dagger B=I`. Each sample obeys preservation of
the two-channel squared magnitude, so summing over the common grid preserves
combined sampled norm. This is an algebraic statement; it is not a calibrated
electromagnetic energy-flow model for an evanescent beam splitter.

The first mixer sends `(U,0)` to `(U/sqrt(2),i*U/sqrt(2))`. Existing public ASM
travels forward once in each local unfolded arm with `pad_factor=1`. Its
`exp(i*kz*L)` already includes the carrier, with principal-root evanescent
decay. Add `exp(i*phi)` only to arm 1 at the precombiner reference plane.
Do not reset phase or insert a second carrier.

For `A=P(L0)U` and `V=P(L1)U`, multiplying the matrices gives

```text
M = B_dagger diag(P0, exp(i*phi)*P1) B
  = [[P0+exp(i*phi)*P1, i*(P0-exp(i*phi)*P1)],
     [i*(exp(i*phi)*P1-P0), P0+exp(i*phi)*P1]]/2
U0 = (A+exp(i*phi)*V)/2
U1 = i*(exp(i*phi)*V-A)/2.
```

With equal arms W=P(L)U, use `1+exp(i*phi)=2*exp(i*phi/2)*cos(phi/2)` and
`i*(exp(i*phi)-1)=-2*exp(i*phi/2)*sin(phi/2)`. Thus output 0 is
`exp(i*phi/2)*cos(phi/2)*W`, output 1 is `-exp(i*phi/2)*sin(phi/2)*W`.
At zero phase port 0 is bright; at pi port 1 is `-i*W`. Floating-point pi
is not an exact symbolic cancellation instruction.

## Norm budgets and denominators

`N(U)=sum(abs(U)**2,dtype=float64)*dx*dy` has amplitude-unit²·m² units.
It is not watts. The five ordered pairs are input, immediately split,
after propagation, immediately precombiner after phase, and output. Derived
residuals are signed after minus before; roundoff is neither clamped nor
labelled absorption. Output fractions divide by the original total input.
Exactly zero input has undefined fractions `(None,None)` and total ratio None.

For positive input and equal arms, let tau=N(W)/N(U). Then
`eta0=tau*cos(phi/2)**2` and `eta1=tau*sin(phi/2)**2`. Bare cos²/sin² requires
tau=1. Forward evanescence generally reduces tau; normalize neither arm nor
output to conceal this. With `C=dx*dy*sum(conj(A)*V)`,
`Nout0/1=(N(A)+N(V) +/- 2*Re(exp(i*phi)*C))/4`.
Their sum is `(N(A)+N(V))/2`. Unequal spatial modes may have imperfect visibility.

Blocking one split arm removes Pin/2 at that boundary. The remaining arm yields
Pin/4 in each output, with total Pin/2. A phase on the sole survivor changes
its complex amplitude but neither output intensity. No shutter is added to
the fixed specification, and loss is not attributed to the phase operation.

Common input phase is complex covariance: both outputs rotate by that phase.
Intensity is invariant. Relative arm phase changes distribution. Equal modes
under a uniform phase produce brightness redistribution, not spatial stripes.

## Independent discrete reference

The validation script constructs centered physical coordinates
`x=(column-nx//2)*dx`, `y=(row-ny//2)*dy` and its own signed integer frequency
bins. It evaluates finite forward and inverse exponential sums with physical
sample area and reciprocal-window factors, constructs the principal axial
factor independently, and combines with literal coefficients. It calls no
production mixer/phase/ASM/grid-array helper and no FFT for expected fields.
Dense references are restricted to at most 256 samples. This is an independent
reference for the same discrete periodic model, not a continuum sampling proof.

Unequal-length DC and off-axis plane waves independently expose omitted or
double carrier. For L0=lambda/7, L1=L0+lambda/6 and phi=0, ideal fractions
are .75/.25; omitted travel phase predicts 1/0 and doubled phase .25/.75.
Full complex arrays also distinguish phases, flips and output swaps.

## Primary references and translation

Verified during planning and read again on 2026-10-05:

- MIT [Mirrors, Interferometers and Thin-Film Structures](https://live.ocw.mit.edu/courses/6-974-fundamentals-of-photonics-quantum-electronics-spring-2006/98fcc94d2216c26db424e294c28d459a_mirror_inter_thn.pdf),
  printed pp. 70–76, Eqs. (2.171)–(2.185). It uses positive time, negative
  travel phase, diagonal reflection and crossed transmission with an i factor.
  Conjugate for our time convention. With R=diag(1,-1) and Q=[[0,i],[-i,0]],
  `R*S.conj()*R=B`, `Q*S.conj()*R=B_dagger`, and our outputs are
  `i*b8.conj()` and `-i*b7.conj()`. This explicit rephasing/reordering is why
  our bright port is 0. It does not transfer MIT's physical coating model.
- Konijnenberg, Adam and Urbach [Angular Spectrum Method §6.3](https://phys.libretexts.org/Bookshelves/Optics/BSc_Optics_%28Konijnenberg_Adam_and_Urbach%29/06%3A_Scalar_diffraction_optics/6.04%3A_Angular_Spectrum_Method),
  displayed Eqs. (6)–(9), supplies negative time, positive forward propagation
  and the decaying branch. Existing M1 is reused unchanged.

Actual measured discrepancies and unchanged finite-case tolerances are in
[tests_and_evidence.md](tests_and_evidence.md). No fitted amplitude, phase
alignment, hidden normalization or universal accuracy claim is made.
