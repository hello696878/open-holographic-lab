# V2g mathematics and unchanged numerical boundary

The normative science is `docs/math_conventions.md`, especially the public
V2c Jones operations and V2f polarized two-path composition. V2g changes no
numerical source, public numerical export, tolerance or mathematical convention.
The application contract is in `implementation_summary.md`.

An incident scalar envelope is sampled once at z=0 using the public complete
source specification. Both complex coefficients enter `JonesField.from_scalar`
without normalization. A Gaussian's signed waist position and transverse center
remain effective; the same-plane V2d application restriction is not inherited.

V2f mixes corresponding x/y components across ports with its ideal B splitter,
propagates four scalar envelopes with public ASM at pad factor 1, applies zero
to two ordered terminal Jones actions per arm, multiplies both arm-1 components
by the same common phase, and recombines with B_dagger. Action order and the
retarder's full complex phase matter. Drawn housing sizes and lane/screen gaps
are cosmetic and introduce no propagation or aperture.

The two raw outputs are immutable measurement inputs. An enabled common linear
analyzer is applied separately to each raw Jones field by the public V2c
operation. Intensity is the public sum of squared component magnitudes. Norms
are sampled amplitude-unit squared times square metres, not calibrated watts.
Removed norm is the signed raw norm minus analyzed norm. Original-input ratios
and raw-output transmission ratios use different denominators. The public
undefined zero-denominator result is null. Ratios and residuals are not clamped.
The analyzed total original-input ratio sums the two public fractions, preserving
that arithmetic association. Disabled analysis preserves its finite angle but
has no analyzed arrays, port measurements or totals.

Six V2f checkpoint pairs, short after-action histories and their public
diagnostics are serialized directly. Full raw/analyzed images and shared axes
retain their original float64 values in little-endian C order. The frontend's
one joint explicit display range changes colors only; readouts retain original
values. Shared maxima and saturation are disclosed.

The 17 declared phases k*pi/8 include independently computed 0 and 2*pi. A sweep
samples the source and constructs incident Jones once, then calls V2f once per
point and the analyzer twice per enabled point. It returns genuine scalar rows,
not image stacks or a substituted cosine. A failed point contributes no row.
Finite sampled extrema are not a continuous visibility measurement.

Independent references are kept distinct from identical-public-call checks.
The latter compare complete arrays and scalar records exactly on this same
platform and library versions. Literal Jones/port matrices and bounded finite
DFT references use the unchanged V2f tolerances: complex rtol 2e-14 and atol
2e-14*Ain; norm/intensity rtol 2e-13 and input-scaled atol 2e-13; fraction
rtol=atol 2e-13; bounded direct sums 1e-11; selected near-dark fraction
rtol 2e-13, atol 1e-40. The inherited smaller-quadrature limitation is preserved.
No exactness claim crosses different floating-point reduction associations.

Validation checks static public domains without sampling or executing optics.
A statically valid request can fail later in the strict supported scalar/Jones
intersection. In particular, a successful V2f solve can be followed by genuine
analyzer underflow. That requested measurement fails atomically; V2g performs no
component deletion, rescaling, raw-only success or automatic replay.
