# V2d mathematics and presentation conventions

Recorded 2026-10-12. Normative scientific definitions remain unchanged in
docs/math_conventions.md section3.19 and the V2c handoff. V2d orchestrates and
displays those public operations; it adds no scientific solver/convention.

## Public numerical boundary

Uniform/Gaussian-at-waist scalar sampling is public V0 source-plane sampling
with an empty train and observation at zero. Fixing Gaussian waist_z_m=0 is a
V2d input restriction only. It adds no free-space journey, longitudinal scene,
carrier phase or plate path. Source geometry viability remains the public
sampler's separate restriction.

Construct Ux=cx*U, Uy=cy*U only through JonesField.from_scalar. Arbitrary finite
coefficients retain amplitude and common/relative phase; no normalization.
The constructed incident Jones field is the denominator for all original-input
transmissions. A doubled x coefficient gives four times norm mathematically;
this is coefficient preparation, not amplification by a passive polarizer.
Both-zero coefficients and dark source are valid after required validation.

Each ideal element is an actual call to the public linear polarizer/retarder.
Positive angle is +x toward +y. The retarder selected axis has phase reference
zero, perpendicular +delta; QWP/HWP assign actual delta=pi/2 or pi. Preserve
the returned common phase, including floating pi/2/pi residuals. No angle
wrapping, snapping, phase alignment or plate-material model.

Actual public intensity is polarization-insensitive total intensity; public
sampled_norm uses the unchanged left-to-right reduction. App/frontend do not
reimplement either expression or integrate texture values. The norm unit is
amplitude-unit^2*m^2, not watts. Both ratios call public transmission_ratio:
adjacent previous->output and original incident->output. Exactly zero incident
denominator gives null, without epsilon. Signed norm deltas retain floating
residuals; a ratio/delta alone authenticates neither causality nor efficiency.

## One allowed frontend relation

From a returned sample pair, display:

```text
Re([Ux,Uy] exp(-i*tau))
x(tau)=Re(Ux) cos(tau)+Im(Ux) sin(tau)
y(tau)=Re(Uy) cos(tau)+Im(Uy) sin(tau)
```

This is presentation evaluation, not an optical transformation or ellipse fit.
Use +x right, +y down, declared view along +z, equal component-axis scales and
one shared dimensionless tau across stages. Increasing positive physical axis
angle appears clockwise; a Three marker uses (cos(theta),-sin(theta),0).
Mesh spacing/housing and viewing camera have no optical action.

Independent fixed-tau reference: u=(1,i)/sqrt(2) and
u_shifted=exp(i*pi/4)*u have the same circular locus. At tau=0 their vectors
are (1/sqrt(2),0) and (1/2,-1/2), respectively. Expected marker positions are
evaluated independently; shape equality cannot detect a common-phase reset.
Literal (1,+i) at tau0,pi/2,pi,3pi/2 gives (1,0),(0,1),(-1,0),(0,-1)
within an explicit display tolerance, while (1,-i) reverses direction.

Darkness requires all four returned real/imaginary parts numerically zero.
Selected nonzero values can have intensity rounded to zero while other pixels
keep the complete field norm usable. Such a selected sample remains nonzero;
display limitations are disclosed, not repaired optically. No arbitrary weak
visibility/dynamic-range or arbitrary-precision claim follows. Manual gain
changes display only; invalid derived coordinates fail presentation separately.

## Independent numerical checks

Direct-public adapter/transport comparisons can be exact for identical captured
computations; they prove fidelity, not independent scientific correctness.
Separate literal/expanded/Decimal references retain V2c bounds:

| Quantity | rtol | atol |
|---|---:|---:|
| Complex components | 2e-14 | 2e-14*Ain |
| Intensity | 2e-13 | 2e-13*Ain^2 |
| Sampled norm | 2e-13 | 2e-13*Nin |
| Ratio | 2e-13 | 2e-13 |
| Public-basis unitarity | 0 | 2e-15 |
| Selected weak components/intensity/ratio | 2e-14 | 1e-48 |
| Selected weak norm | 2e-14 | 1e-48*Nin |

Ain/Nin refer to incident amplitude/independently evaluated norm. The five weak
offsets [-1e-6,-1e-9,0,1e-9,1e-6] are applied to the actual float pi/2 and
compared to unchanged 80-digit Decimal.from_float direct-angle references;
represented weak components/diagnostics must remain positive. No tolerance is
loosened or general relative-accuracy promise inferred.

Checks include QWP changing complex polarization at unchanged total intensity,
HWP, retained common phase, noncommuting order, contraction without normalized
loss and dark inputs. Crossed/three-polarizer fixtures use already x-polarized
input; ideal three-polarizer norm fraction is1/4, not an unpolarized experiment.

The sweep restarts the same incident Jones field for each actual transmitted
angle and performs every element in order. No cumulative across-point state,
cos-squared simulated values, deduplicated endpoints or analytic overlay is
introduced. Only real completed scalar prefixes survive failures.
