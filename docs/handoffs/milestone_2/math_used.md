# Milestone 2 — Mathematics used

Normative source: [math_conventions.md §3.12](../../math_conventions.md).
This handoff explains the selected target convention without changing the
existing field, Fourier or propagation conventions.

## Intensity is the specification

An unsigned 8-bit code is an integer `g in {0, ..., 255}`. Define

~~~text
I_target = g / 255
A_target = sqrt(I_target)
A_target**2 = I_target          up to floating-point rounding
~~~

The endpoint mapping is fixed: black is zero and code 255 is one. A blank
image remains zero. At code 128, intensity is `0.50196078431372548` and
amplitude is `0.70849190843207621` in the tested float64 environment.
At the lowest nonzero code, intensity is `1/255`; nothing thresholds it away.

These are normalized design quantities (arbitrary units), not W/m². The
mapping deliberately does not decode an image display transfer curve or
apply an ICC profile. A photograph's code values therefore become a design
pattern; they are not interpreted as a measurement of irradiance.

For images containing corresponding codes `g` and `2g` without integer
overflow, `I_2 = 2 I_1` and `A_2 = sqrt(2) A_1`. Per-image peak normalization
would destroy this inter-image brightness relation. Similarly, gamma
correction or contrast stretching would change the chosen target.

## What remains unspecified

A complex field requires `U = A exp(i phi)`. The supplied target amplitude
does not determine `phi`; infinitely many complex fields share its intensity.
A phase-only SLM pattern is a different quantity, to be designed by a later
algorithm under explicit propagation/source constraints. M2 neither creates
a field nor runs an inverse problem.

Any later algorithm needing nonzero target power must state and enforce its
own condition. Loading a zero target is not itself an error.

## Coordinates and sampling

Array shape is `(ny, nx)`. Element `[i, j]` retains coordinate
`(x[j], y[i])` with SI pitches `dx, dy`, `+y` downward and origin at
`[ny//2, nx//2]`. The image cannot alter pitch through DPI or EXIF metadata.
Exact-size rejection avoids introducing a resampling kernel or changing the
physical field of view without a separate decision.

This consistency does not establish adequate optical sampling. Nyquist
limits, periodic FFT boundaries, zero-padding trade-offs, evanescent policies
and the deferred band-limited ASM remain as recorded for M1. Sharp target
edges can contain high spatial frequencies.

## Independent numerical validation

80-digit Decimal arithmetic starts from exact integer/255 ratios for all
256 codes, then evaluates Decimal square roots before conversion to the
float64 reference. It does not call either production converter.

| Comparison | Maximum absolute error | Maximum nonzero relative error | Acceptance |
|---|---:|---:|---|
| Intensity versus Decimal reference | 0 | 0 | `rtol=2e-15, atol=0` |
| Amplitude versus Decimal reference | `1.1102230246251565e-16` | `2.1499376424746289e-16` | `rtol=2e-15, atol=0` |
| Squared amplitude versus intensity | `1.1102230246251565e-16` | `2.211772431870429e-16` | `rtol=5e-15, atol=0` |

The zero endpoint is exact and the nonzero code intensity floor is `1/255`,
so these code-sweep tests need no absolute floor. They characterize the
specified 256-code mapping, not all possible normalized float64 values or
every platform/library version. Separate tests exercise user-supplied
normalized intensities and invalid values. The demo uses
`rtol=1e-14, atol=1e-15` for its displayed amplitude-squared diagnostic;
it does not replace the tighter independent-reference tests.

The [evidence record](tests_and_evidence.md) gives the environment,
reproduction code and deliberate mutations that these tests detect.
