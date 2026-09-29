# Milestone 6 — Mathematical interpretation of the interface

M6 adds no mathematical convention. The normative reference remains
[math conventions, version 0.8](../../math_conventions.md). The interface
displays saved M2–M5 data and exposes their existing assumptions.

## Fixed target samples and units

The built-in 64×64 target uses the existing quantized smooth-spot raster,
with width 7.5 pixels. Its centre is row/column 32. Pixel codes are mapped by
M2 as `I_target = g/255`, then `A_target = sqrt(I_target)`. The raster remains
fixed when physical pitch changes: 7.5 pixels corresponds to 60 micrometres
at 8-micrometre pitch, and a different physical width at another pitch.

An uploaded PNG supplies its own unchanged grayscale samples. M2 accepts a
strict static 8-bit grayscale subset with exact supplied grid shape. Design
intensity is not a calibrated camera measurement; metadata does not add
radiometric, gamma or orientation corrections.

The controller converts display units once: nm to metres by `1e-9`,
micrometres by `1e-6`, and mm by `1e-3`. Saved settings remain SI. Rows and
columns retain the grid convention: `x` follows columns, `y` follows rows,
and positive `y` is downward in the displayed raster.

## Explicit illumination

For new runs the controller chooses uniform prescribed source amplitude

```text
A_source = sqrt(sum(A_target**2) / number_of_pixels)
```

before calling M5. This matches total discrete source/target amplitude energy
within M3's existing arithmetic. It configures illumination separately for
each target; it does not normalize the target inside the solver or demonstrate
fixed illumination for arbitrary images.

Displayed prescribed source and target-amplitude powers are
`sum(A**2) * dx * dy`, in arbitrary intensity units times square metres.
The summaries use saved amplitude arrays. Squaring rounded target amplitude
need not recover saved target-intensity bits, so the two roles are not silently
interchanged. Loaded source amplitudes can be nonuniform; the UI reports their
actual range and does not replace them with the new-run prescription.

## What the four views mean

- **Target intensity:** saved design samples.
- **Actual reconstruction intensity:** saved squared magnitude of M3's actual
  forward reconstruction, not its target-amplitude projection.
- **Ideal numerical source phase:** saved phase in radians. The display axis
  is fixed at `[-pi,+pi]`, while the existing phase convention is `(-pi,+pi]`.
  This heatmap is not calibrated SLM drive data, and its brightness does not
  represent target intensity.
- **Residual history:** every saved M3 sample, including initialization at
  index zero. For `N` cycles there are `N+1` values.

Target and reconstruction use one color range from zero through the larger
saved peak. Values above one remain visible; there is no independent contrast
normalization or clipping. A degenerate all-zero inspected pair uses a 0–1
color axis only to avoid a singular display range; its arrays remain zero.
The color range is unrelated to the saved PSNR reference range.

M3's residual is normalized squared amplitude error:

```text
rho_k = sum((abs(P_z(U_k)) - A_target)**2) / sum(A_target**2)
```

It is distinct from intensity NMSE, is not percent accuracy and carries no
universal convergence guarantee. M6 neither clips nor smooths history and
does not alter the solver to supply iteration-progress percentages.

## Saved metrics and parameters

New runs request intensity MSE, intensity NMSE and explicit-range PSNR.
The UI displays M5's saved values rather than evaluating another metric path.
MSE has squared-intensity units, NMSE is dimensionless and PSNR is in dB.
PSNR `data_range` is a declared reference scale, not an observed image maximum
or a bound on reconstruction. Exact-match positive infinity remains `+∞`.

Loaded bundles may contain any supported M5 metric subset. Regional metrics
retain the exact saved mask reference and selected-pixel count. A Gaussian's
intended falloff is not labeled poor uniformity; population CV has a uniformity
interpretation only for a region intended to have flat brightness. No region
is selected from the reconstruction to improve a score.

## Three different verification statements

Artifact integrity means that M5 accepted the schema/typed files and their
hashes against the retained unsigned manifest. It is not physical correctness
or authorship. Qualification requires M5's exact clean-source/environment
policy. Numerical comparison is a separate actual replay with exact saved
array/scalar checks; it is not an approximate visual match.

A readable older M5 bundle can therefore pass integrity, remain unqualified
under M6 and have strict comparison `not_run`. Explicit diagnostic comparison
may pass without changing that qualification. Foreign-byte-order arrays can
be inspected, but comparisons that were not executed remain `not_run`.

M6 introduces no new numerical tolerance. Presentation tests can check exact
axis bounds, displayed values, sample counts and preserved input bytes; they
do not establish additional optical accuracy. Controller, AppTest and browser
evidence have their own scopes in [tests and evidence](tests_and_evidence.md).
