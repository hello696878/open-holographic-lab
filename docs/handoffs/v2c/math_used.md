# V2c mathematics and convention translation

Recorded 2026-10-06. Normative contract:
[math_conventions.md §3.19](../../math_conventions.md#319-v2c-ideal-jones-polarization-at-one-reference-plane).
This handoff explains ideal deterministic, fully coherent monochromatic
Jones components at one common transverse reference plane. It introduces
neither vector propagation nor reflected/tilted coordinate frames.

## Components, basis and physical time

Write the actual complex transverse vector as `U=(Ux,Uy).T`, with both
components at the same sampled coordinates and vacuum wavelength. Its real
time-dependent value at this plane is

```text
E(t) = Re(U * exp(-i*omega*t)).
```

Common phase multiplies both components and shifts their time reference;
relative phase changes the vector's trajectory and analyzer response. The
constructor preserves both. These are polarization components at each point,
not V2a optical ports. Future polarized interference requires separate indices
for optical port and polarization component.

For an ideal uniform element axis theta in radians, choose

```text
e_theta = (c,s).T,        e_perp = (-s,c).T
c = cos(theta),          s = sin(theta)
R = [e_theta,e_perp] = [[c,-s],[s,c]].
```

This real orthonormal basis has `R^-1=R.T`. Passive conversion from lab
components into element coordinates is `R.T*U`; conversion back is `R`.
Changing theta rotates physical element axes, distinct from changing the basis
used to describe the same vector. A later viewing-camera rotation changes
presentation, not the Jones action. Positive theta turns algebraically from
+x toward +y. Since +y displays downward in this repository, it appears
clockwise on screen.

Angles are evaluated from their supplied binary64 values without modulo
wrapping or snapping. Floating pi/2 and pi are nearby binary64 numbers and
retain ordinary trigonometric/phase residuals. Exactly +/-0 retardance is
allowed as a validated fresh-copy identity; signed zero has no separate
physical optical meaning.

## Ideal linear polarizer

A linear analyzer retains `a=e_theta.T*U` and removes the orthogonal
component. Its returned vector is `e_theta*a`, giving

```text
P(theta) = e_theta e_theta.T = [[c*c,c*s],[c*s,s*s]]
Ux_out = c*c*Ux + c*s*Uy
Uy_out = c*s*Ux + s*s*Uy.
```

This projection acts on complex field amplitude. For unit x-polarized
incident amplitude, output components are `(c*c,c*s)`. Their total intensity
is `c^4+c^2*s^2=c^2`, giving Malus law. Multiplying field amplitude by
cos-squared would square this loss again and is incorrect.

The real projector obeys `P^2=P`; its eigenvalues are one and zero, so ideal
projection cannot increase vector norm. Explicit fixtures are
`P(0)(1,1)=(1,0)` and `P(pi/4)(1,1)=(1,1)`. The latter has intensity
two because the analyzer combines the vector components before intensity.

For already x-polarized unit-norm light,

```text
P(pi/2) P(0) (1,0) = (0,0)                 [ideal real-angle identity]
P(pi/2) P(pi/4) P(0) (1,0) = (0,1/2)     [sampled norm ratio 1/4].
```

The numerical pi/2 case retains a finite represented residual. The measured
crossed ratio was `3.749399456654644e-33`; the middle-polarizer ratio was
`0.25000000000000006`. These fixtures do not describe unpolarized illumination.

## Ideal retarder and the selected common phase

Choose the axis component reference phase zero and give its perpendicular
component phase +delta. In element coordinates the action is
`diag(1,exp(i*delta))`; conversion back gives

```text
W(theta,delta) = R diag(1,exp(i*delta)) R.T
              = e_theta e_theta.T + exp(i*delta) e_perp e_perp.T.

q = exp(i*delta)
Ux_out = (c*c+q*s*s)*Ux + (1-q)*c*s*Uy
Uy_out = (1-q)*c*s*Ux + (s*s+q*c*c)*Uy.
```

The source applies axis projections; independent expectations use these
expanded scalar coefficients and literal complex fixtures. For real delta,
`abs(q)=1` mathematically, so `W.conj().T*W=I` and
`W(theta,-delta)*W(theta,delta)=I`. These properties are checked through
public basis-field actions and inverse composition within explicit tolerance.

Quarter-wave and half-wave cases use delta=pi/2 and pi:

```text
W(0,pi/2) (1,1)/sqrt(2) = (1,i)/sqrt(2)
W(pi/8,pi) (1,0) = (1,1)/sqrt(2)
W(pi/4,pi/2) (1,0) = ((1+i)/2,(1-i)/2).
```

The last fixture includes its selected common phase. Replacing it with
`(1,-i)/sqrt(2)` silently removes exp(i*pi/4). Likewise multiplying every
retarder output by exp(-i*delta/2) preserves isolated intensity but violates
this returned complex-field reference. Its actual isolated negative control
was detected. No comparison phase-aligns, normalizes or makes a component real.

Retardance is supplied as an ideal parameter at the stated wavelength. It
does not predict thickness, material dispersion, walk-off, coating behavior
or physical absolute optical-path phase. Fast/slow labels are avoided because
the eigenaxis phase prescription is the explicit model definition.

For `(1,+/-i)/sqrt(2)`, real components are
`(cos(tau),+/-sin(tau))/sqrt(2)`, with tau=omega*t dimensionless.
The plus-i state moves initially toward +y, downward in the display; the
minus-i state moves initially toward -y. Component labels and this direction
replace ambiguous right/left circular labels. Demo ellipses use actual
complex center samples and `Re([Ux,Uy]*exp(-i*tau))`, equal component-axis
scales and no amplitude normalization or fitted ellipse.

Element order matters. For unit x input,

```text
W(pi/4,pi/2) P(0) (1,0) = ((1+i)/2,(1-i)/2), norm 1
P(0) W(pi/4,pi/2) (1,0) = ((1+i)/2,0),       norm 1/2.
```

These independent literal outputs distinguish order directly, including
selected complex phase.

## Intensity, norm, construction and ratios

Define polarization-insensitive total intensity and sampled norm as

```text
I = abs(Ux)**2 + abs(Uy)**2                       [amplitude-unit^2]
N = sum(I,dtype=float64) * dx * dy                [amplitude-unit^2*m^2]
T = N_transmitted / N_incident                   [dimensionless].
```

The norm expression is evaluated left-to-right. These are relative field
units, not calibrated irradiance or watts. Orthogonal components contribute
separately: `(1,1)` and `(1,i)` both have intensity two. `abs(Ux+Uy)**2`
would introduce an incorrect scalar cross term. Analyzer intensity instead
comes from the actual projected Jones vector, whose response depends on
relative component phase.

Arbitrary finite coefficients construct `Ux=cx*U`, `Uy=cy*U`, with the
mathematical gain/loss factor `abs(cx)**2+abs(cy)**2`. There is no implicit
unit-vector normalization. The field-pair ratio does not establish a causal
optical transformation: a compatible independently supplied field with twice
the amplitude gives four. Finite ratios greater than one are returned.
Passive polarizer contraction and retarder norm preservation are separate
scientific assertions. Exactly zero incident norm gives `None` only after
validating both fields and exact metadata; no epsilon denominator is used.

Usable positive pixel area, finite complex128 components and combined norm
are required. Individual products or squared tails may underflow; a tiny
orthogonal component remains valid beside a usable one. A represented nonzero
combined field whose entire norm rounds to zero is rejected, as are overflow,
invalid arithmetic and unusable reductions/intermediate products. Ratio
division locally raises on NumPy-reported underflow, including an inexact
positive subnormal result; positive rounding-to-zero is separately rejected.
Caller error settings are restored. No propagation-frequency or wavenumber
bounds, global warning changes, rescaling or arbitrary-precision fallback
are applied to these same-plane uniform operations.

## Independent finite-case comparisons

Let Ain be maximum incident component amplitude and Nin the independently
calculated combined incident norm. Shipped comparisons retain these bounds:

| Quantity | rtol | atol |
|---|---:|---:|
| Public-basis matrix unitarity | 0 | 2e-15 |
| Complex components | 2e-14 | 2e-14*Ain |
| Intensity | 2e-13 | 2e-13*Ain^2 |
| Sampled norm | 2e-13 | 2e-13*Nin |
| Ratio | 2e-13 | 2e-13 |
| Selected weak components/intensity/ratio | 2e-14 | 1e-48 |
| Selected weak sampled norm | 2e-14 | 1e-48*Nin |

Ordinary input-scaled floors near darkness do not prove retention of a
1e-18 signal. The five declared offsets `[-1e-6,-1e-9,0,1e-9,1e-6]`
around pi/2 therefore also use direct sin/cos Taylor sums at
`Decimal.from_float(actual_angle)`, with 80-digit arithmetic. The reference
does not use a rounded pi subtraction or simply epsilon^2. It checks each
actual complex component, intensity, sampled norm and ratio separately;
positive weak signals must remain positive. The two deliberate weak
intensity/ratio truncation controls failed the intended scientific assertions.
Exact dark-input cases are distinct.

All thirteen Malus degree values
`[-90,-75,-60,-45,-30,-15,0,15,30,45,60,75,90]` and converted radians are
recorded by the preserved validation/demo scripts. Actual finite-case maxima
were `2.479436791899844e-16` input-scaled complex error,
`4.440892098500626e-16` matrix unitarity error,
`4.640716422278097e-16` relative retarder norm error and
`2.0194839179460514e-16` selected weak relative error. These are measurements,
not universal error bounds, arbitrary-dynamic-range guarantees, or proofs of
full-vector physical accuracy.

## Primary references and explicit translation

- R. Clark Jones, [A New Calculus for the Treatment of Optical Systems,
  JOSA 31, 488-493 (1941)](https://opg.optica.org/josa/abstract.cfm?uri=josa-31-7-488)
  is the primary origin of the matrix calculus. The original reference does
  not override the explicit present time/basis/phase choices.
- Konijnenberg, Adam and Urbach, TU Delft,
  [Polarisation, Eqs. 263, 275, 278-284, 285 and 288](https://interactivetextbooks.tudelft.nl/interactive-optics/content/Chap4_Polarisation/Polarization_2022_01Clean.html),
  provides negative-time complex fields, ideal amplitude polarizers, rotated
  matrices and phase retarders. Its rotated action is R*M*R^-1 and its
  selected diagonal QWP is (1,i). We retain those algebraic signs, translate
  visual rotation into the repository's +y-down display and explicitly
  select the factored phase reference. An omitted common material path phase
  is not inferred. Textual fast/slow and handedness labels are not copied
  without their frame/view/time qualifications.

The normative section and validation script preserve these definitions and
their translation. Full results/provenance and reproduction commands are
in [tests_and_evidence.md](tests_and_evidence.md). Reflected/tilted frames,
partial/unpolarized statistics, Stokes/Mueller analysis, polarized propagation
or recombination, material instruments and V2d remain outside V2c.
