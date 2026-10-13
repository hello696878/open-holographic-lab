# V2f mathematics and independent references

Normative API and exact domains are in math_conventions.md3.20 and
[implementation_summary.md](implementation_summary.md). Measured current
discrepancies belong in [tests_and_evidence.md](tests_and_evidence.md), separately
from the earlier planning compositions and historical V2a/V2c evidence.

## Two indices and complete complex phase

For the ordered vector (p0.x,p0.y,p1.x,p1.y), the ideal splitter is

```text
B4 = [[1,0,i,0],[0,1,0,i],[i,0,1,0],[0,i,0,1]]/sqrt(2).
```

Its adjoint has crossed -i. These are port-space coefficients with identity
polarization action. Their unitarity is a finite matrix identity, not a coating
law. Keep exp(-i*omega*t) and the stipulated aligned basis/coordinates.

For Pj the same scalar ASM applied to both components and Jj the product of
terminal Jones actions (last action leftmost), define G0=J0P0,
G1=exp(i*phi)J1P1. Independently multiplying blocks gives

```text
B4_dagger diag(G0,G1) B4 =
  [[G0+G1, i*(G0-G1)], [i*(G1-G0), G0+G1]]/2.
```

For port0 input E and zero second port, use UNSCALED reference arm fields
A=J0P0E and V=J1P1E, giving F0=(A+exp(i*phi)V)/2 and
F1=i*(exp(i*phi)V-A)/2. Actual post-split checkpoint fields already include
the splitter coefficient. Never insert another 1/sqrt(2) into this reference.

Uniform V2c actions use e=(cos(theta),sin(theta)),p=(-sin(theta),cos(theta)),
P=e e.T and W=e e.T+exp(+i*delta)p p.T. Selected axis phase0/perpendicular
+delta is the declared reference. No exp(-i*delta/2), representative-state
normalization or arm phase fitting is permitted. A HWP axis pi/2 maps x to -x
in the ideal limit, preserving isolated polarization shape while shifting
relative-arm interference. Floating pi retains its actual ordinary residuals.
Terminal actions remain ordered; uniformity does not make P and W commute.

## Norm and overlap

N(F)=sum(abs(Fx)^2+abs(Fy)^2,float64)*dx*dy, evaluated left-to-right. It is
amplitude-unit²*m², not calibrated power. Define
C=dx*dy*sum(conj(Ax)Vx+conj(Ay)Vy). Expanding both squared component sums gives

```text
N(F0/1)=[N(A)+N(V) +/- 2 Re(exp(i*phi)C)]/4.
N(F0)+N(F1)=[N(A)+N(V)]/2.
```

Matched lossless normalized REFERENCE states j0/j1 have
gamma=conj(j0).T@j1 and original-input fractions
(1 +/- Re(exp(i*phi)gamma))/2. Production fields are never normalized to use
this special formula. Complex gamma's argument shifts response; abs(gamma)
cannot replace it. The hand anchor j0=(1,i)/sqrt2,j1=(1,1)/sqrt2 has gamma=(1-i)/2,
giving (3/4,1/4) at phi=pi/2. Omitted conjugation gives the reversed response.
An x-versus-QWP fixture alone cannot detect missing conjugation of real x.

For x/y orthogonal matched arms, raw fractions are half/half. Separate equal
45-degree analyzer projections give ((1+cos(phi))/4,(1-cos(phi))/4) and retain
half of ORIGINAL input. Record raw/post-analyzer norms and signed removal
separately. For x input and arm1 P(pi/3), raw fractions are
5/16 +/- cos(phi)/8 and retain5/8, with3/8 removed at the arm element. These
are no-loss matched-spatial or explicitly lossy fixtures, not arbitrary-case
visibility claims. Finite sampled extrema do not certify continuous visibility.

## Independent discrete propagation

Expected tiny arrays use centered coordinates xj=(j-Nx//2)dx,yi=(i-Ny//2)dy
and literal signed frequency bins m/(Nx*dx),l/(Ny*dy), with even Nyquist on
the negative branch. No production grid-frequency helper or FFT supplies
expected values. The physical forward sum has sample-area factor dx*dy and
negative exponential; synthesis has opposite exponential and
1/(Nx*Ny*dx*dy). Centered-origin phases cancel in the same-grid composition.
The reference forms principal kz=2*pi*sqrt(1/lambda²-fx²-fy²) and H=exp(+i*kz*L)
through bounded finite sums. Public ASM includes the same carrier once.

Expected port mixing is literal4x4 algebra; expected Jones action expands
its scalar coefficients independently. Dense references cap spatial samples
at64. Odd/even mixed parity, anisotropic pitches, different complex x/y data
and unequal arm lengths compare all four output arrays, without fitted phase,
renormalization or a generic tolerance fallback. Direct sums verify the chosen
discrete model; they do not establish continuum sampling or vector accuracy.

## Physical approximation and source translation

The new composition is an aligned homogeneous polarization-independent,
low-angle Jones-envelope model. It is not V2c secretly becoming a vector
propagator. Scalar ASM retains its full kernel at explicit pad1; arbitrary
high-angle spectra and omitted longitudinal fields are outside the physical
claim. Inherited forward evanescent arithmetic does not calibrate vector energy.

[TU Delft Scalar Diffraction Optics, Eqs.374–378](https://interactivetextbooks.tudelft.nl/interactive-optics/content/Chap6_Diffraction/DiffractiveOptics_2022_01Clean.html)
explains component propagation with physically consistent electromagnetic
data and the divergence constraint. V2f intentionally keeps only the bounded
two-envelope interpretation. Its
[Polarisation, Eqs.263–264 and rotated Jones matrices](https://interactivetextbooks.tudelft.nl/interactive-optics/content/Chap4_Polarisation/Polarization_2022_01Clean.html)
supplies negative time and a plane Jones description. Existing V2a source
translation and V2c eigenaxis phase references remain unchanged; no coating or
material common-path phase is inferred. The formulas above are independently
expanded for this exact repository convention.

Ordinary input-scaled and focused near-dark bounds are defined in3.20. Weak
references expand sine/cosine at Decimal.from_float(actual_phase),80digits,
rather than treating an offset squared as exact. Positive selected fractions
and a much smaller lost quadrature have separate claims; no arbitrary dynamic
range or every-quadrature relative-accuracy guarantee follows.
